"""iter106 — Court agreement alerts + 'Add to Step 4' Foundation PDF intent wording.

Covers:
- Backend alerts queueing/sending, 6h window, same-area de-dupe,
  undo doesn't queue, safety-flagged never receives, cron flush.
- Email content lines + intent notice + HTML escape (monkeypatch _send).
- Foundation PDF prints INTENT_NOTICE under box when co_values has an '(agreed):' line.
"""
import asyncio
import importlib
import os
import re
import subprocess
import sys
import time
import zlib
from datetime import datetime, timedelta, timezone

import pytest
import requests

sys.path.insert(0, "/app/backend")


def _env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.strip().startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].strip('"').strip("'")
    except Exception:
        return None


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _env() or "").rstrip("/")
API = f"{BASE}/api"
PWD = "TestPass123!"
UID3 = "user_f6130bc2835f"
UID4 = "user_888a80257d90"
UID1 = "user_5ce04f1049a4"  # parent1 safety-flagged
QUEUE = "court_agreement_alerts"


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _reseed():
    subprocess.run(
        ["python", "-c",
         "from dotenv import load_dotenv; load_dotenv('.env'); "
         "from seed_court_compare_pair import run; import asyncio; print(asyncio.run(run()))"],
        cwd="/app/backend", check=True, capture_output=True,
    )


def _mongo():
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    cli = MongoClient(os.environ["MONGO_URL"])
    return cli[os.environ["DB_NAME"]]


def _cron_secret():
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    return os.environ["WEBHOOK_CRON_SECRET"]


# ---------- helpers to drive agreement/note area resolution dynamically ----------

def _first_diff_area(tok):
    r = requests.get(f"{API}/court-path/compare", headers=_h(tok), timeout=20).json()
    assert r.get("state") == "ready", r
    diffs = r.get("difference") or []
    assert diffs, "no differing areas after reseed"
    # 'key' = '<source>|<area>' for mark/note; 'area' is the plain label used in alerts
    return diffs[0]["key"], diffs[0]["area"], diffs


@pytest.fixture(scope="module")
def setup():
    _reseed()
    db = _mongo()
    db[QUEUE].delete_many({})
    p3 = _login("parent3@test.com")
    p4 = _login("parent4@test.com")
    # Both share -> ready
    requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": True}, timeout=20)
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(p4), json={"shared": True}, timeout=20).json()
    assert r.get("state") == "ready"
    yield {"p3": p3, "p4": p4, "db": db}
    _reseed()


# =========================================================
# Backend alerts
# =========================================================

def test_agree_sends_immediately_to_coparent(setup):
    db = setup["db"]
    key_full, _area_label, _diffs = _first_diff_area(setup["p3"])
    # parent3 marks agreed -> queue_alert triggers flush_one for parent4
    r = requests.post(f"{API}/court-path/compare/agree", headers=_h(setup["p3"]),
                      json={"area": key_full, "agreed": True}, timeout=20)
    assert r.status_code == 200, r.text

    # Wait for background send to run
    last_sent = None
    for _ in range(20):
        time.sleep(0.5)
        doc = db[QUEUE].find_one({"user_id": UID4}) or {}
        if doc.get("last_sent_at"):
            last_sent = doc.get("last_sent_at")
            break
    assert last_sent, f"no last_sent_at for parent4; doc={db[QUEUE].find_one({'user_id': UID4})}"
    doc = db[QUEUE].find_one({"user_id": UID4})
    assert doc.get("pending") in (None, []), f"pending not cleared: {doc.get('pending')}"


def test_note_within_window_queues_and_dedupes_same_area(setup):
    db = setup["db"]
    _k, area_label, diffs = _first_diff_area(setup["p3"])
    key_full = diffs[0]["key"]
    doc_before = db[QUEUE].find_one({"user_id": UID4}) or {}
    sent_at_before = doc_before.get("last_sent_at")
    assert sent_at_before, "precondition: last_sent_at should be set"

    # parent3 adds a note on same area -> within 6h window, should queue only
    r = requests.put(f"{API}/court-path/compare/agree/note", headers=_h(setup["p3"]),
                     json={"area": key_full, "note": "Handoffs at 3:15."}, timeout=20)
    assert r.status_code == 200, r.text

    pending = None
    for _ in range(20):
        time.sleep(0.3)
        doc = db[QUEUE].find_one({"user_id": UID4}) or {}
        pending = doc.get("pending") or []
        if pending:
            break
    assert len(pending) == 1, f"expected 1 pending note; got {pending}"
    assert pending[0]["kind"] == "note"
    assert pending[0]["area"] == area_label
    assert pending[0]["note"] == "Handoffs at 3:15."
    doc_after = db[QUEUE].find_one({"user_id": UID4})
    assert doc_after.get("last_sent_at") == sent_at_before, "last_sent_at must not change within window"

    # Second note on same area REPLACES pending entry (not duplicated)
    r = requests.put(f"{API}/court-path/compare/agree/note", headers=_h(setup["p3"]),
                     json={"area": key_full, "note": "Updated note."}, timeout=20)
    assert r.status_code == 200, r.text
    time.sleep(1.0)
    doc = db[QUEUE].find_one({"user_id": UID4})
    pending = doc.get("pending") or []
    notes = [p for p in pending if p["kind"] == "note" and p["area"] == area_label]
    assert len(notes) == 1, f"same-area note should de-dupe; got {pending}"
    assert notes[0]["note"] == "Updated note."


def test_undo_agreed_does_not_queue(setup):
    db = setup["db"]
    _k, _al, diffs = _first_diff_area(setup["p3"])
    key_full = diffs[0]["key"]
    doc_before = db[QUEUE].find_one({"user_id": UID4}) or {}
    pending_before = list(doc_before.get("pending") or [])

    r = requests.post(f"{API}/court-path/compare/agree", headers=_h(setup["p3"]),
                      json={"area": key_full, "agreed": False}, timeout=20)
    assert r.status_code == 200
    time.sleep(1.5)
    doc_after = db[QUEUE].find_one({"user_id": UID4}) or {}
    assert (doc_after.get("pending") or []) == pending_before, "undo must not add to queue"


def test_cron_flush_sends_after_window_expires(setup):
    db = setup["db"]
    # Force last_sent_at 7h in the past, keep a pending item
    seven_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    # Ensure there's at least one pending item (re-agree + note)
    _k, _al, diffs = _first_diff_area(setup["p3"])
    key_full = diffs[0]["key"]
    requests.post(f"{API}/court-path/compare/agree", headers=_h(setup["p3"]),
                  json={"area": key_full, "agreed": True}, timeout=20)
    time.sleep(1.0)
    # Note within fresh 6h window -> queued, not sent
    requests.put(f"{API}/court-path/compare/agree/note", headers=_h(setup["p3"]),
                 json={"area": key_full, "note": "Final hand-off at 3:15."}, timeout=20)
    time.sleep(1.0)
    # Now backdate last_sent_at so cron flush will fire
    db[QUEUE].update_one({"user_id": UID4}, {"$set": {"last_sent_at": seven_hours_ago}})
    # Confirm pending exists
    doc = db[QUEUE].find_one({"user_id": UID4}) or {}
    assert doc.get("pending"), "test precondition: there should be at least one pending item"

    # Call cron with correct auth
    r = requests.post(f"{API}/cron/self-assessment-reminders",
                      headers={"Authorization": f"Bearer {_cron_secret()}"}, timeout=20)
    assert r.status_code == 200, r.text
    # Wait for background flush
    for _ in range(20):
        time.sleep(0.5)
        doc = db[QUEUE].find_one({"user_id": UID4}) or {}
        if (doc.get("last_sent_at") != seven_hours_ago) and not (doc.get("pending") or []):
            break
    assert doc.get("last_sent_at") != seven_hours_ago, "cron should have updated last_sent_at"
    assert not (doc.get("pending") or []), f"cron should clear pending; got {doc.get('pending')}"


def test_cron_bad_auth_returns_401():
    r = requests.post(f"{API}/cron/self-assessment-reminders", timeout=15)
    assert r.status_code == 401
    r = requests.post(f"{API}/cron/self-assessment-reminders",
                      headers={"Authorization": "Bearer not-the-real-secret"}, timeout=15)
    assert r.status_code == 401


def test_stop_sharing_clears_pending_without_sending(setup):
    db = setup["db"]
    # Make sure both are sharing again fresh for this test
    requests.post(f"{API}/court-path/compare/share", headers=_h(setup["p3"]), json={"shared": True}, timeout=20)
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(setup["p4"]), json={"shared": True}, timeout=20).json()
    assert r.get("state") == "ready"

    _k, _al, diffs = _first_diff_area(setup["p3"])
    key_full = diffs[0]["key"]
    requests.post(f"{API}/court-path/compare/agree", headers=_h(setup["p3"]),
                  json={"area": key_full, "agreed": True}, timeout=20)
    time.sleep(1.0)
    # Set last_sent_at fresh so note queues (not sends)
    now_iso = datetime.now(timezone.utc).isoformat()
    db[QUEUE].update_one({"user_id": UID4}, {"$set": {"last_sent_at": now_iso}})
    requests.put(f"{API}/court-path/compare/agree/note", headers=_h(setup["p3"]),
                 json={"area": key_full, "note": "Queued note"}, timeout=20)
    time.sleep(0.5)
    assert db[QUEUE].find_one({"user_id": UID4}, {"pending": 1}).get("pending"), "precondition failed: no pending"

    # parent4 stops sharing
    requests.post(f"{API}/court-path/compare/share", headers=_h(setup["p4"]), json={"shared": False}, timeout=20)

    # Backdate last_sent_at so flush_one proceeds past the window check and
    # reaches the "pair no longer sharing -> clear pending" branch.
    seven_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    db[QUEUE].update_one({"user_id": UID4}, {"$set": {"last_sent_at": seven_hours_ago}})

    # Flush — should clear pending without sending
    from court_agreement_alerts import flush_one
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")

    async def _flush():
        cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
        return await flush_one(cli[os.environ["DB_NAME"]], UID4)

    sent = asyncio.get_event_loop().run_until_complete(_flush()) if False else asyncio.new_event_loop().run_until_complete(_flush())
    assert sent is False
    doc = db[QUEUE].find_one({"user_id": UID4}) or {}
    assert not (doc.get("pending") or []), f"pending should be cleared on broken pair; got {doc.get('pending')}"

    # Restore for other tests
    requests.post(f"{API}/court-path/compare/share", headers=_h(setup["p4"]), json={"shared": True}, timeout=20)


def test_safety_flagged_parent_never_receives(setup):
    """parent1 is safety-flagged. parent1/parent2 never reach ready, so no alert doc for parent1."""
    db = setup["db"]
    assert not db[QUEUE].find_one({"user_id": UID1})


# =========================================================
# Email content (unit-level via monkeypatch)
# =========================================================

def test_send_agreement_update_alert_content(monkeypatch):
    import email_service
    captured = {}

    def fake_send(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(email_service, "_send", fake_send)
    items = [
        {"area": "Pick-Up, Drop-Off & Transitions", "kind": "agreed", "note": ""},
        {"area": "Communication & Conflict", "kind": "note", "note": 'Say "Hi" & be nice <ok>'},
    ]
    notice = "By marking an area as agreed, the parties have evidenced their intent to make an agreement. This document does not reflect a binding agreement on the parties."
    email_service.send_agreement_update_alert(
        to_email="x@test.com", user_name="Casey Parent",
        link_url="https://example.test/dashboard", items=items, notice=notice,
    )
    assert captured["subject"] == "Your co-parent updated your agreements"
    body = captured["text"] + captured["html"]
    # Privacy: areas and notes stay on the Court page, never in the email.
    assert "Pick-Up" not in body and "Say" not in body and "Communication & Conflict" not in body
    assert notice in captured["text"]
    assert "evidenced their intent" in captured["html"]
    assert "https://example.test/dashboard" in body


# =========================================================
# Foundation PDF intent wording under co_values
# =========================================================

def _pdf_text(body: bytes) -> str:
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S):
        try:
            out.append(zlib.decompress(m.group(1)).decode("latin-1", errors="ignore"))
        except Exception:
            pass
    return "\n".join(out)


def test_foundation_pdf_includes_intent_when_co_values_has_agreed_line():
    tok = _login("parent3@test.com")
    payload = {"fields": {"co_values": "Pick-Up, Drop-Off & Transitions (agreed): Handoffs at 3:15."}}
    r = requests.post(f"{API}/foundation-builder/pdf", headers=_h(tok), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF")
    text = _pdf_text(r.content)
    assert "evidenced their intent" in text
    assert "binding agreement" in text


def test_foundation_pdf_omits_intent_when_no_agreed_line():
    tok = _login("parent3@test.com")
    payload = {"fields": {"co_values": "Mutual respect, patience and shared decisions."}}
    r = requests.post(f"{API}/foundation-builder/pdf", headers=_h(tok), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    text = _pdf_text(r.content)
    assert "evidenced their intent" not in text
