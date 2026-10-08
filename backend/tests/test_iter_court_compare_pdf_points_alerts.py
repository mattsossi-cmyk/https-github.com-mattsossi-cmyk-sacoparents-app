"""Backend tests for Court Compare additions:
- GET /api/court-path/compare/pdf (409 before ready; PDF content/filename/names/talking points)
- POST /api/court-path/compare/talking-points (409 before ready; shared items; staleness)
- Sharing alert emails: court_compare_alerts collection weekly limit, safety guard
"""
import os
import re
import time
import uuid
import zlib
import subprocess

import pytest
import requests


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


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"{email}: {r.text}"
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


@pytest.fixture(scope="module")
def tokens():
    _reseed()
    return {
        "p1": _login("parent1@test.com"),
        "p2": _login("parent2@test.com"),
        "p3": _login("parent3@test.com"),
        "p4": _login("parent4@test.com"),
    }


# ---------- PDF ----------

def test_pdf_409_before_ready(tokens):
    # parent1 safety_off
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p1"]), timeout=20)
    assert r.status_code == 409
    assert "both parents" in r.text.lower()
    # parent2 waiting (co-parent is safety-flagged)
    requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p2"]), json={"shared": True}, timeout=20)
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p2"]), timeout=20)
    assert r.status_code == 409
    # parent3 not_shared yet
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p3"]), timeout=20)
    assert r.status_code == 409


def _pdf_text(body: bytes) -> str:
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S):
        try:
            out.append(zlib.decompress(m.group(1)).decode("latin-1", errors="ignore"))
        except Exception:
            pass
    return "\n".join(out)


def test_pdf_ready_and_content(tokens):
    # p3 share
    requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p3"]), json={"shared": True}, timeout=20)
    # p4 share
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(tokens["p4"]), json={"shared": True}, timeout=20).json()
    assert r.get("state") == "ready", r

    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p3"]), timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert "SA_CoParents_Side_by_Side_Comparison.pdf" in r.headers.get("content-disposition", "")
    assert r.content.startswith(b"%PDF")

    text = _pdf_text(r.content)
    assert "Side-by-Side Comparison" in text
    assert "Case: PAIR-DEMO-01" in text
    assert "Areas of Alignment" in text
    assert "Areas of Difference" in text
    assert "Child-Focused Needs" in text
    # Caller-first naming (parent3 = Jordan Parent)
    assert "Jordan Parent and Casey Parent" in text
    # Child answer sample
    assert "Dr. Lee" in text and "Northside Pediatrics" in text


def test_pdf_from_other_parent_caller_first(tokens):
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p4"]), timeout=30)
    assert r.status_code == 200
    text = _pdf_text(r.content)
    assert "Casey Parent and Jordan Parent" in text


def test_pdf_uses_court_legal_name(tokens):
    requests.put(f"{API}/portal/state", headers=_h(tokens["p3"]),
                 json={"court_legal_name": "Jordan Q. Legalname"}, timeout=15)
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p3"]), timeout=30)
    assert r.status_code == 200
    text = _pdf_text(r.content)
    assert "Jordan Q. Legalname" in text
    # restore
    requests.put(f"{API}/portal/state", headers=_h(tokens["p3"]),
                 json={"court_legal_name": "Jordan Parent"}, timeout=15)


# ---------- Talking points ----------

def test_talking_points_409_before_ready(tokens):
    r = requests.post(f"{API}/court-path/compare/talking-points", headers=_h(tokens["p1"]), timeout=30)
    assert r.status_code == 409


def test_talking_points_generate_shared_and_in_pdf(tokens):
    # generate as parent3
    r = requests.post(f"{API}/court-path/compare/talking-points", headers=_h(tokens["p3"]), timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    tp = data.get("talking_points")
    assert tp and isinstance(tp.get("items"), list) and len(tp["items"]) >= 1
    assert tp.get("stale") is False
    diff_areas = {d["area"] for d in data["difference"]}
    for it in tp["items"]:
        assert it["area"] in diff_areas
        assert len(it["text"]) <= 280
        assert it["text"].strip()
    assert len(tp["items"]) <= 8

    # parent4 GET /compare returns SAME items
    r4 = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p4"]), timeout=20).json()
    assert r4["state"] == "ready"
    tp4 = r4.get("talking_points")
    assert tp4 and [i["text"] for i in tp4["items"]] == [i["text"] for i in tp["items"]]

    # PDF should include 'Talking point:' lines
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p3"]), timeout=30)
    text = _pdf_text(r.content)
    assert "Talking point:" in text


def test_talking_points_become_stale_on_change(tokens):
    db = _mongo()
    uid4 = "user_888a80257d90"
    # Mutate parent4 snapshot to shift difference set
    hist = db.cp_report_history.find_one({"user_id": uid4})
    assert hist and hist["snapshots"]
    snap = hist["snapshots"][-1]
    # Change ratings substantially
    for row in snap["section_avgs"]:
        row["rating"] = "Excellent"
        row["avg"] = 3.6
    db.cp_report_history.update_one({"user_id": uid4}, {"$set": {"snapshots": [snap]}})

    r3 = requests.get(f"{API}/court-path/compare", headers=_h(tokens["p3"]), timeout=20).json()
    tp = r3.get("talking_points")
    assert tp and tp.get("stale") is True

    # PDF should omit talking points when stale
    r = requests.get(f"{API}/court-path/compare/pdf", headers=_h(tokens["p3"]), timeout=30)
    text = _pdf_text(r.content)
    assert "Talking point:" not in text

    # Re-seed to restore baseline for other tests
    _reseed()


# ---------- Alerts ----------

def test_alerts_invite_then_ready_then_weekly_limit():
    _reseed()
    db = _mongo()
    uid3 = "user_f6130bc2835f"
    uid4 = "user_888a80257d90"
    db.court_compare_alerts.delete_many({"user_id": {"$in": [uid3, uid4]}})

    p3 = _login("parent3@test.com")
    p4 = _login("parent4@test.com")

    # parent3 shares -> invite should go to parent4 (background task)
    requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": True}, timeout=20)
    # Wait for background email
    invite = None
    for _ in range(15):
        time.sleep(1)
        doc = db.court_compare_alerts.find_one({"user_id": uid4}) or {}
        if doc.get("invite_sent_at"):
            invite = doc["invite_sent_at"]
            break
    assert invite, f"invite not sent to parent4 within timeout; last doc={db.court_compare_alerts.find_one({'user_id': uid4})}"
    # parent3 should NOT have an invite doc
    p3_doc = db.court_compare_alerts.find_one({"user_id": uid3}) or {}
    assert not p3_doc.get("invite_sent_at")

    # parent4 shares -> ready for both
    requests.post(f"{API}/court-path/compare/share", headers=_h(p4), json={"shared": True}, timeout=20)
    ready3 = ready4 = None
    for _ in range(15):
        time.sleep(1)
        d3 = db.court_compare_alerts.find_one({"user_id": uid3}) or {}
        d4 = db.court_compare_alerts.find_one({"user_id": uid4}) or {}
        if d3.get("ready_sent_at") and d4.get("ready_sent_at"):
            ready3, ready4 = d3["ready_sent_at"], d4["ready_sent_at"]
            break
    assert ready3 and ready4, f"ready not sent to both; d3={db.court_compare_alerts.find_one({'user_id': uid3})}, d4={db.court_compare_alerts.find_one({'user_id': uid4})}"

    # Toggle parent3 off and on - weekly limit must prevent new timestamps
    requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": False}, timeout=20)
    time.sleep(1)
    requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": True}, timeout=20)
    time.sleep(5)
    d3b = db.court_compare_alerts.find_one({"user_id": uid3}) or {}
    d4b = db.court_compare_alerts.find_one({"user_id": uid4}) or {}
    assert d3b.get("ready_sent_at") == ready3, "ready_sent_at changed within week"
    assert d4b.get("invite_sent_at") == invite, "invite_sent_at changed within week"

    # Sharing again while already sharing: not a new share event; no changes
    requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": True}, timeout=20)
    time.sleep(2)
    d3c = db.court_compare_alerts.find_one({"user_id": uid3}) or {}
    assert d3c.get("ready_sent_at") == ready3


def test_alerts_safety_flagged_never_emailed():
    """parent2 toggling share while co-parent is safety-flagged (parent1) must never create an alert doc
    for parent1 (user_5ce04f1049a4)."""
    db = _mongo()
    flagged_uid = "user_5ce04f1049a4"
    db.court_compare_alerts.delete_one({"user_id": flagged_uid})
    p2 = _login("parent2@test.com")
    # toggle off then on
    requests.post(f"{API}/court-path/compare/share", headers=_h(p2), json={"shared": False}, timeout=20)
    time.sleep(1)
    requests.post(f"{API}/court-path/compare/share", headers=_h(p2), json={"shared": True}, timeout=20)
    time.sleep(4)
    doc = db.court_compare_alerts.find_one({"user_id": flagged_uid})
    assert not doc or (not doc.get("invite_sent_at") and not doc.get("ready_sent_at")), f"flagged parent got alert: {doc}"

    # Flagged parent cannot share
    p1 = _login("parent1@test.com")
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(p1), json={"shared": True}, timeout=20).json()
    assert r.get("state") == "safety_off"
    assert r.get("shared") is False


def test_share_response_ok_even_if_email_fails(tokens):
    # Just sanity: share returns compare payload (not 500) even if email layer errors internally.
    _reseed()
    p3 = _login("parent3@test.com")
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": True}, timeout=20)
    assert r.status_code == 200
    assert r.json().get("state") in ("waiting", "ready", "not_shared")


# Teardown: leave data seeded with both sharing ready
def test_zz_final_reseed_both_sharing():
    _reseed()
    p3 = _login("parent3@test.com")
    p4 = _login("parent4@test.com")
    requests.post(f"{API}/court-path/compare/share", headers=_h(p3), json={"shared": True}, timeout=20)
    r = requests.post(f"{API}/court-path/compare/share", headers=_h(p4), json={"shared": True}, timeout=20).json()
    assert r.get("state") == "ready"
