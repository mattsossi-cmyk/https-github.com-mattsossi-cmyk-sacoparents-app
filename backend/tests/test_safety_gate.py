"""Safety Gate acceptance tests (backend). Test 9 (Quick exit) is checked in the browser."""
import asyncio
import hashlib
import hmac
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
import uuid
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from PIL import Image
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import case_safety as cs  # noqa: E402
from media_scrub import UnsupportedFile, scrub_upload  # noqa: E402

API = "http://localhost:8001/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
PASSWORD = "Str0ng!Pass99"
SECRET = os.environ.get("ALIGN_WEBHOOK_SECRET")

if not SECRET:
    pytest.skip("ALIGN_WEBHOOK_SECRET is not set: the webhook is off", allow_module_level=True)
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails, _cases = [], []
LIMITED = ("free_form_messaging", "calls_video", "addresses_visible", "gps_checkins")
COOPERATIVE = {"comm_flexible_dm", "comm_joint_meetings", "ex_flexible_home", "sch_shared_events", "dec_joint_everyday", "sched_flexible"}
FORBIDDEN_WORDS = ("safety", "screening", "violence", "abuse", "auto_red", "restricted", "disclos")


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    ids = [u["user_id"] for u in db.users.find({"email": {"$in": _emails}}, {"user_id": 1})]
    db.users.delete_many({"email": {"$in": _emails}})
    for coll in ("privacy_consents", "legal_acknowledgments", "plan_option_picks"):
        db[coll].delete_many({"user_id": {"$in": ids}})
    db.joint_alignment_cases.delete_many({"case_id": {"$in": _cases}})
    db[cs.COLL].delete_many({"case_id": {"$in": _cases}})
    db[cs.AUDIT].delete_many({"case_id": {"$in": _cases}})


def _user():
    email = f"test_gate_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": PASSWORD, "name": "Gate Test", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    uid = db.users.find_one({"email": email})["user_id"]
    return uid, {"Authorization": f"Bearer {r.json()['access_token']}"}


def _case():
    """A joint case with two linked parents. Returns (case_id, headers A, headers B)."""
    case_id = f"SA-T{uuid.uuid4().hex[:6].upper()}"
    _cases.append(case_id)
    (ua, ha), (ub, hb) = _user(), _user()
    db.joint_alignment_cases.insert_one({
        "case_id": case_id, "status": "pending", "created_at": cs.now_iso(),
        "parents": [{"parent_slot": "A", "user_id": ua}, {"parent_slot": "B", "user_id": ub}],
    })
    return case_id, ha, hb


def _body(case_id, version, *, mode="standard", set_by="professional", referral="none", offered=True, ts=None, **extra):
    return json.dumps({
        "case_id": case_id, "safety_mode": mode, "set_by": set_by, "professional_name": "Dr. Reviewer",
        "referral": referral, "screening_offered": offered, "version": version,
        "timestamp": int(time.time()) if ts is None else ts, **extra,
    }).encode()


def _sign(raw, secret=SECRET):
    return hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def _send(raw, sig="__auto__"):
    headers = {"Content-Type": "application/json"}
    if sig == "__auto__":
        sig = _sign(raw)
    if sig is not None:
        headers["X-Align-Signature"] = sig
    return httpx.post(f"{API}/internal/safety-status", content=raw, headers=headers, timeout=20)


def _flags(h, case_id=None):
    r = httpx.get(f"{API}/case-settings", params={"case_id": case_id} if case_id else None, headers=h, timeout=20)
    assert r.status_code == 200, r.text
    return r


def _stored(case_id):
    return db[cs.COLL].find_one({"case_id": case_id}, {"_id": 0})


# 1. restricted / auto_red -> both parents lose free-form messaging, calls, address view and GPS on the next load.
def test_auto_red_limits_both_parents_on_next_load():
    case_id, ha, hb = _case()
    assert _send(_body(case_id, 1)).status_code == 200
    for h in (ha, hb):
        f = _flags(h).json()["features"]
        assert all(f[k] for k in LIMITED)
    r = _send(_body(case_id, 2, mode="restricted", set_by="auto_red"))
    assert r.status_code == 200 and r.json() == {"ok": True}
    for h in (ha, hb):
        body = _flags(h).json()
        assert not any(body["features"][k] for k in LIMITED)
        assert body["banner"] == "Some features are set by your professional for this case."
    # Stays restricted until a professional changes it.
    assert _send(_body(case_id, 3, mode="standard", set_by="default")).status_code == 200
    assert not _flags(ha).json()["features"]["free_form_messaging"]
    assert _send(_body(case_id, 4, mode="structured", set_by="auto_red")).status_code == 200
    assert not _flags(ha).json()["features"]["free_form_messaging"]
    assert _send(_body(case_id, 5, mode="restricted", set_by="auto_red", referral="parallel_parenting")).status_code == 200
    assert _send(_body(case_id, 6, mode="standard", set_by="professional")).status_code == 200
    assert _flags(ha).json()["features"]["free_form_messaging"]


# 2. Byte-identical responses for both parents of the same case.
def test_flag_responses_are_byte_identical():
    case_id, ha, hb = _case()
    for v, mode in ((1, "structured"), (2, "restricted"), (3, "standard")):
        _send(_body(case_id, v, mode=mode, referral="parallel_parenting" if v == 2 else "none"))
        assert _flags(ha).content == _flags(hb).content
        assert _flags(ha, case_id).content == _flags(hb, case_id).content
    text = _flags(ha).text.lower()
    assert "dr. reviewer" not in text and not any(w in text for w in FORBIDDEN_WORDS)


# 3. No push, email or SMS for any mode or referral change (in-process, every email path patched).
def test_no_notifications_on_mode_or_referral_change(monkeypatch):
    import smtplib

    import email_service
    import server

    calls = []
    monkeypatch.setattr(email_service, "_send", lambda *a, **k: calls.append(("resend", a, k)))
    monkeypatch.setattr(smtplib.SMTP, "send_message", lambda *a, **k: calls.append(("smtp", a, k)), raising=False)
    monkeypatch.setattr(smtplib.SMTP, "sendmail", lambda *a, **k: calls.append(("smtp", a, k)), raising=False)
    case_id, ha, hb = _case()

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://t") as c:
            for v, mode, ref in ((1, "structured", "none"), (2, "restricted", "parallel_parenting"), (3, "standard", "none")):
                raw = _body(case_id, v, mode=mode, referral=ref, set_by="auto_red" if mode == "restricted" else "professional")
                r = await c.post("/api/internal/safety-status", content=raw, headers={"X-Align-Signature": _sign(raw)})
                assert r.status_code == 200
                for h in (ha, hb):
                    assert (await c.get("/api/case-settings", headers=h)).status_code == 200
                    assert (await c.get("/api/plan-options", headers=h)).status_code == 200

    asyncio.run(run())
    assert calls == []
    source = (ROOT / "case_safety.py").read_text() + (ROOT / "case_safety_routes.py").read_text()
    assert not any(w in source for w in ("email_service", "send_", "push", "sms", "twilio"))


# 4. Photos uploaded in structured or restricted carry no EXIF/GPS.
def _photo_with_gps():
    img = Image.new("RGB", (40, 30), (200, 80, 40))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    exif[0x0132] = "2026:01:02 03:04:05"
    exif[0x8825] = {1: "N", 2: (29.0, 25.0, 1.0), 3: "W", 4: (98.0, 29.0, 1.0)}
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif)
    raw = out.getvalue()
    assert Image.open(io.BytesIO(raw)).getexif().get_ifd(0x8825)
    return raw


@pytest.mark.parametrize("mode", ["structured", "restricted"])
def test_uploaded_photo_has_no_exif_or_gps(mode):
    level = cs.scrub_level(cs.FEATURES[mode])
    clean = scrub_upload(_photo_with_gps(), level)
    with Image.open(io.BytesIO(clean)) as img:
        exif = img.getexif()
        assert len(exif) == 0 and not exif.get_ifd(0x8825)
        assert "exif" not in img.info and img.size == (40, 30)
    assert b"PhoneMaker" not in clean and b"Exif" not in clean


def test_restricted_strips_png_text_and_pdf_info():
    from PIL import PngImagePlugin
    from pypdf import PdfReader, PdfWriter

    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Parent Name")
    out = io.BytesIO()
    Image.new("RGB", (8, 8)).save(out, format="PNG", pnginfo=info)
    assert b"Parent Name" not in scrub_upload(out.getvalue(), "all")
    w = PdfWriter()
    w.add_blank_page(100, 100)
    w.add_metadata({"/Author": "Parent Name", "/Title": "Home address"})
    pdf = io.BytesIO()
    w.write(pdf)
    meta = PdfReader(io.BytesIO(scrub_upload(pdf.getvalue(), "all"))).metadata or {}
    assert "/Author" not in meta and "/Title" not in meta
    with pytest.raises(UnsupportedFile):
        scrub_upload(b"PK\x03\x04 not an image", "location")
    assert scrub_upload(b"anything", "none") == b"anything"


# 5. Unsigned or wrongly signed -> 401, nothing changes.
@pytest.mark.parametrize("sig", [None, "", "deadbeef", "__wrong_secret__"])
def test_bad_signature_rejected(sig):
    case_id, ha, _ = _case()
    raw = _body(case_id, 5, mode="standard")
    if sig == "__wrong_secret__":
        sig = _sign(raw, "not-the-secret")
    assert _send(raw, sig).status_code == 401
    assert _stored(case_id) is None
    assert not _flags(ha).json()["features"]["free_form_messaging"]


# 6. Old timestamp, replay, or a version that isn't higher -> nothing changes.
def test_stale_timestamp_replay_and_old_version_change_nothing():
    case_id, ha, _ = _case()
    assert _send(_body(case_id, 1, ts=int(time.time()) - 301)).status_code == 401
    assert _send(_body(case_id, 1, ts="2020-01-01T00:00:00+00:00")).status_code == 401
    assert _stored(case_id) is None
    raw = _body(case_id, 3, mode="standard")
    assert _send(raw).status_code == 200
    assert _send(raw).status_code == 409
    before = _stored(case_id)
    for v in (3, 2):
        assert _send(_body(case_id, v, mode="restricted", set_by="auto_red")).status_code == 200
    assert _stored(case_id) == before
    assert _flags(ha).json()["features"]["free_form_messaging"]


# 7. With a parallel_parenting referral, no cooperative options for either parent.
def test_referral_hides_cooperative_options_for_both():
    case_id, ha, hb = _case()
    full = httpx.get(f"{API}/plan-options", headers=ha, timeout=20).json()
    assert COOPERATIVE <= {o["id"] for c in full["categories"] for o in c["options"]}
    _send(_body(case_id, 1, mode="structured", referral="parallel_parenting"))
    bodies = [httpx.get(f"{API}/plan-options", headers=h, timeout=20) for h in (ha, hb)]
    assert bodies[0].content == bodies[1].content
    ids = {o["id"] for c in bodies[0].json()["categories"] for o in c["options"]}
    assert ids and not (ids & COOPERATIVE)
    assert {"comm_no_direct", "comm_templates", "ex_supervised", "ex_safe_site", "ex_staggered", "sch_separate"} <= ids
    for h in (ha, hb):
        assert _flags(h).json()["plan_options"] is True
    r = httpx.put(f"{API}/plan-options/picks", json={"picks": ["comm_flexible_dm", "ex_staggered"]}, headers=ha, timeout=20)
    assert r.json()["picks"] == ["ex_staggered"]


# 8. Schedule, health, school and expense templates send in every mode.
def test_templates_always_allowed():
    case_id, ha, _ = _case()
    for v, mode in ((1, "standard"), (2, "structured"), (3, "restricted")):
        _send(_body(case_id, v, mode=mode, set_by="auto_red" if mode == "restricted" else "professional"))
        body = _flags(ha).json()
        assert body["features"]["template_messages"] is True
        assert body["template_categories"] == ["schedule", "health", "school", "expenses"]
        for cat in body["template_categories"]:
            assert cs.message_allowed(body["features"], "template", cat, "x" * 280)
        assert not cs.message_allowed(body["features"], "template", "schedule", "x" * 281)
        assert cs.message_allowed(body["features"], "free_form") is (mode == "standard")


# 10. Nothing parent-visible records a mode change, referral change or Get help visit.
def test_no_parent_visible_trace():
    case_id, ha, _ = _case()
    _send(_body(case_id, 1, mode="restricted", set_by="auto_red", referral="parallel_parenting"))
    assert httpx.get(f"{API}/help/local-services", timeout=20).status_code == 200
    for path in ("/me/export", "/me/access-log", "/portal/state", "/plan-options/picks"):
        r = httpx.get(f"{API}{path}", headers=ha, timeout=30)
        assert r.status_code in (200, 404), path
        text = r.text.lower()
        assert case_id.lower() not in text and "case_safety" not in text and "help_local" not in text
        assert "parallel_parenting" not in text and "safety_mode" not in text and "safety_audit" not in text


# 11. A new case is structured until screening_offered is true.
def test_new_case_structured_until_screening_offered():
    case_id, ha, hb = _case()
    body = _flags(ha).json()
    assert body["features"] == cs.FEATURES["structured"]
    assert body["banner"] == "Some features are limited until your case setup is complete."
    _, lone = _user()
    assert _flags(lone).json()["features"] == cs.FEATURES["structured"]
    _send(_body(case_id, 1, mode="standard", offered=False))
    assert _flags(ha).json()["features"]["free_form_messaging"] is False
    _send(_body(case_id, 2, mode="structured", set_by="default", offered=True))
    for h in (ha, hb):
        b = _flags(h).json()
        assert b["features"]["free_form_messaging"] is True and b["banner"] is None


def test_record_encrypted_and_audited():
    case_id, ha, _ = _case()
    _send(_body(case_id, 1, mode="restricted", set_by="professional"))
    doc = _stored(case_id)
    assert set(doc) == {"case_id", "version", "enc", "updated_at"}
    assert "restricted" not in doc["enc"] and "Reviewer" not in doc["enc"]
    assert cs.decrypt(doc["enc"])["professional_name"] == "Dr. Reviewer"
    _flags(ha)
    actions = [(r["actor_type"], r["action"]) for r in db[cs.AUDIT].find({"case_id": case_id})]
    assert ("system", "write") in actions and ("user", "read") in actions


def test_audit_export_admin_only_and_logged():
    _, h = _user()
    assert httpx.get(f"{API}/admin/safety-audit-log/export", headers=h, timeout=20).status_code == 403
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    admin = {"Authorization": f"Bearer {r.json()['access_token']}"}
    before = db[cs.AUDIT].count_documents({"action": "export"})
    e = httpx.get(f"{API}/admin/safety-audit-log/export", headers=admin, timeout=30)
    assert e.status_code == 200 and e.text.startswith("at,actor_type,actor_id,action,case_id")
    assert db[cs.AUDIT].count_documents({"action": "export"}) == before + 1


def test_daily_counts_admin_only_counts_only():
    _, h = _user()
    assert httpx.get(f"{API}/admin/safety-audit-log/daily-counts", headers=h, timeout=20).status_code == 403
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    admin = {"Authorization": f"Bearer {r.json()['access_token']}"}
    url = f"{API}/admin/safety-audit-log/daily-counts"
    today = lambda resp: resp.json()["days"][0]  # noqa: E731
    before = today(httpx.get(url, headers=admin, timeout=20))
    case_id, _, _ = _case()
    assert _send(_body(case_id, 1)).status_code == 200
    assert _send(_body(case_id, 1, mode="structured")).status_code == 200
    httpx.get(f"{API}/admin/safety-audit-log/export", headers=admin, timeout=30)
    resp = httpx.get(url, headers=admin, timeout=20)
    assert "no-store" in resp.headers.get("cache-control", "")
    days, after = resp.json()["days"], today(resp)
    assert len(days) == 30 and set(after) == {"date", "applied", "ignored", "downloads", "rejected"}
    assert (after["applied"], after["ignored"], after["downloads"]) == (before["applied"] + 1, before["ignored"] + 1, before["downloads"] + 1)
    assert case_id not in resp.text


def test_align_silence_status_rule():
    now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    assert cs.silence_status(None, now) == {"threshold_days": 7, "days_since": None, "warn": True}
    almost = cs.silence_status("2026-10-10T12:00:01+00:00", now)
    assert almost["days_since"] == 6 and almost["warn"] is False
    seven = cs.silence_status("2026-10-10T12:00:00+00:00", now)
    assert seven == {"threshold_days": 7, "days_since": 7, "warn": True}


def test_timestamp_formats_seconds_ms_and_quoted():
    now = int(time.time())
    for i, ts in enumerate([now, now * 1000, str(now), str(now * 1000), f"{now}.5", datetime.now(timezone.utc).isoformat()]):
        case_id, _, _ = _case()
        assert _send(_body(case_id, 1, ts=ts)).status_code == 200, (i, ts)
    for ts in [(now - 3600) * 1000, str(now - 3600), "2026-01-01T00:00:00", "soon", True]:
        case_id, _, _ = _case()
        assert _send(_body(case_id, 1, ts=ts)).status_code in (401, 422), ts
        assert db[cs.COLL].count_documents({"case_id": case_id}) == 0


def _admin():
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_align_status_last_update_and_refusals():
    _, h = _user()
    status_url = f"{API}/admin/safety-audit-log/align-status"
    assert httpx.get(status_url, headers=h, timeout=20).status_code == 403
    admin = _admin()
    counts_url = f"{API}/admin/safety-audit-log/daily-counts"
    before = httpx.get(status_url, headers=admin, timeout=20).json()["rejected_30d"]
    before_day = httpx.get(counts_url, headers=admin, timeout=20).json()["days"][0]["rejected"]
    case_id, _, _ = _case()
    assert _send(_body(case_id, 1), sig="deadbeef").status_code == 401
    assert _send(_body(case_id, 1, ts=int(time.time()) - 3600)).status_code == 401
    assert _send(_body(case_id, 1)).status_code == 200
    s = httpx.get(status_url, headers=admin, timeout=20)
    assert "no-store" in s.headers.get("cache-control", "")
    body = s.json()
    assert body["last_update"]["result"] == "applied" and body["last_applied_at"] == body["last_update"]["at"]
    assert body["rejected_30d"]["bad_signature"] == before["bad_signature"] + 1
    assert body["rejected_30d"]["old_timestamp"] == before["old_timestamp"] + 1
    assert body["last_rejected"]["reason"] == "old_timestamp"
    assert body["silence"] == {"threshold_days": 7, "days_since": 0, "warn": False}
    assert case_id not in s.text
    assert _send(_body(case_id, 1, mode="structured")).status_code == 200
    assert httpx.get(status_url, headers=admin, timeout=20).json()["last_update"]["result"] == "ignored"
    assert httpx.get(counts_url, headers=admin, timeout=20).json()["days"][0]["rejected"] == before_day + 2
    for doc in db[cs.REJECTS].find({}).sort("at", -1).limit(2):
        assert set(doc) == {"_id", "at", "reason", "created"}



def test_signed_test_message_never_changes_a_case():
    case_id, ha, _ = _case()
    assert _send(_body(case_id, 1, mode="restricted", set_by="professional")).status_code == 200
    before_cases = db[cs.COLL].count_documents({})
    before_writes = db[cs.AUDIT].count_documents({"action": {"$in": ["write", "write_ignored_stale_version", "write_ignored_until_professional"]}})
    flags = httpx.get(f"{API}/case-settings", headers=ha, timeout=20).content
    tid = f"t-{uuid.uuid4().hex}"
    raw = json.dumps({"test": True, "test_id": tid, "timestamp": int(time.time())}).encode()
    assert _send(raw, sig="deadbeef").status_code == 401
    assert _send(json.dumps({"test": True, "test_id": tid, "timestamp": int(time.time()) - 3600}).encode()).status_code == 401
    assert db[cs.TESTS].find_one({"_id": tid}) is None
    assert _send(raw).status_code == 200
    assert _send(raw).status_code == 409
    doc = db[cs.TESTS].find_one({"_id": tid})
    assert doc["source"] == "align" and doc["received_at"] and set(doc) <= {"_id", "received_at", "round_trip_ms", "source", "created"}
    assert db[cs.COLL].count_documents({}) == before_cases
    assert db[cs.AUDIT].count_documents({"action": {"$in": ["write", "write_ignored_stale_version", "write_ignored_until_professional"]}}) == before_writes
    assert httpx.get(f"{API}/case-settings", headers=ha, timeout=20).content == flags
    bad = json.dumps({"test": True, "test_id": "has spaces!", "timestamp": int(time.time())}).encode()
    assert _send(bad).status_code == 422


def test_self_test_and_align_ping_admin_only():
    _, h = _user()
    base = f"{API}/admin/safety-audit-log"
    assert httpx.post(f"{base}/self-test", headers=h, timeout=20).status_code == 403
    assert httpx.post(f"{base}/align-ping", headers=h, timeout=20).status_code == 403
    admin = _admin()
    r = httpx.post(f"{base}/self-test", headers=admin, timeout=30)
    assert "no-store" in r.headers.get("cache-control", "")
    body = r.json()
    assert body["ok"] is True and body["status_code"] == 200 and body["webhook_url"].endswith("/api/internal/safety-status"), body
    status = httpx.get(f"{base}/align-status", headers=admin, timeout=20).json()
    assert status["last_test"]["source"] == "self" and status["last_test"]["round_trip_ms"] is not None
    if not os.environ.get("ALIGN_PING_URL"):
        assert httpx.post(f"{base}/align-ping", headers=admin, timeout=20).json() == {"configured": False}
    assert httpx.get(f"{base}/test-status/self-{'0' * 32}", headers=admin, timeout=20).status_code == 404
    assert httpx.get(f"{base}/test-status/../etc", headers=admin, timeout=20).status_code in (404, 422)
    assert httpx.get(f"{base}/test-status/self-{'0' * 32}", headers=h, timeout=20).status_code == 403


def test_align_ping_round_trip_with_simulated_align(monkeypatch):
    """Align is simulated: it checks our signature, then sends a signed test message to the real webhook."""
    from types import SimpleNamespace

    from motor.motor_asyncio import AsyncIOMotorClient

    import align_ping

    monkeypatch.setenv("ALIGN_PING_URL", "https://align.example/api/internal/parents-test-ping")
    calls, real_post = [], httpx.AsyncClient.post

    async def fake_post(self, url, content=None, headers=None, **kw):
        if not url.startswith("https://align.example"):
            return await real_post(self, url, content=content, headers=headers, **kw)
        calls.append((url, content, headers))
        if headers.get("X-SACO-Signature") != _sign(content):
            return httpx.Response(401)
        back = json.dumps({"test": True, "test_id": json.loads(content)["test_id"], "timestamp": int(time.time())}).encode()
        await real_post(self, f"{API}/internal/safety-status", content=back, headers={"Content-Type": "application/json", "X-Align-Signature": _sign(back)})
        return httpx.Response(202)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    async def run():
        adb = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        await adb[cs.TESTS].delete_many({"_id": {"$regex": "^align-"}, "received_at": {"$exists": False}})
        await adb[cs.TESTS].update_many({"_id": {"$regex": "^align-"}}, {"$set": {"created": datetime(2000, 1, 1, tzinfo=timezone.utc)}})
        return json.loads((await align_ping.align_ping(current=SimpleNamespace(user_id="pytest-admin"), db=adb)).body)

    res = asyncio.run(run())
    assert res["configured"] is True and res["accepted"] is True and res["status_code"] == 202, res
    url, content, _ = calls[0]
    sent = json.loads(content)
    assert set(sent) == {"test_id", "timestamp", "callback_url"} and sent["callback_url"].endswith("/api/internal/safety-status")
    doc = db[cs.TESTS].find_one({"_id": res["test_id"]})
    assert doc["source"] == "align" and doc["received_at"] and doc["round_trip_ms"] is not None


def test_support_sees_mode_only_and_parents_cannot():
    case_id, ha, _ = _case()
    _send(_body(case_id, 1, mode="restricted", set_by="auto_red", referral="parallel_parenting"))
    assert httpx.get(f"{API}/support/case-settings/{case_id}", headers=ha, timeout=20).status_code == 403
    r = httpx.post(f"{API}/auth/login", json={"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}, timeout=20)
    if r.status_code != 200:
        pytest.skip("admin test account not available")
    s = httpx.get(f"{API}/support/case-settings/{case_id}", headers={"Authorization": f"Bearer {r.json()['access_token']}"}, timeout=20)
    assert s.json() == {"case_id": case_id, "safety_mode": "restricted"}


def test_other_case_not_readable():
    case_id, _, _ = _case()
    _, outsider = _user()
    r = httpx.get(f"{API}/case-settings", params={"case_id": case_id}, headers=outsider, timeout=20)
    assert r.status_code == 404


def test_internal_endpoint_hidden_from_docs():
    paths = httpx.get("http://localhost:8001/openapi.json", timeout=20).json()["paths"]
    assert not any("internal" in p for p in paths)


# Family check-in status: same for both parents, only "case setup complete" (screening_offered) is exposed.
def test_family_checkin_status_same_for_both_parents():
    case_id, ha, hb = _case()
    assert all(_flags(h).json()["setup_complete"] is False for h in (ha, hb))
    assert _send(_body(case_id, 1, set_by="default", offered=False)).status_code == 200
    assert all(_flags(h).json()["setup_complete"] is False for h in (ha, hb))
    assert _send(_body(case_id, 2, set_by="default", offered=True)).status_code == 200
    a, b = _flags(ha), _flags(hb)
    assert a.content == b.content and a.json()["setup_complete"] is True
    item = lambda h: next(i for i in httpx.post(f"{API}/court-path/checklist", json={}, headers=h, timeout=20).json()["items"] if i["key"] == "family_checkin")  # noqa: E731
    assert item(ha) == item(hb) and item(ha)["status"] == "done"


# "Thanks, your check-in is done" shows once per parent account, only after the case is set up.
def test_checkin_thanks_once_per_account():
    case_id, ha, hb = _case()
    url = f"{API}/family-checkin/thanks"
    show = lambda h: httpx.get(url, headers=h, timeout=20).json()["show"]  # noqa: E731
    assert show(ha) is False and show(hb) is False
    assert _send(_body(case_id, 1, set_by="default", offered=True)).status_code == 200
    assert show(ha) is True and show(hb) is True
    assert httpx.post(f"{url}/seen", headers=ha, timeout=20).json() == {"ok": True}
    assert httpx.post(f"{url}/seen", headers=ha, timeout=20).status_code == 200
    assert show(ha) is False and show(hb) is True
    assert "no-store" in httpx.get(url, headers=hb, timeout=20).headers.get("cache-control", "")
    assert httpx.get(url, timeout=20).status_code == 401


# Check-in link: both parents in one case get the same case number; no case -> null (main Align site).
def test_checkin_link_case_number():
    case_id, ha, hb = _case()
    url = f"{API}/family-checkin/link"
    a, b = httpx.get(url, headers=ha, timeout=20), httpx.get(url, headers=hb, timeout=20)
    assert a.json() == b.json() == {"case_id": case_id}
    assert "no-store" in a.headers.get("cache-control", "")
    assert httpx.get(url, timeout=20).status_code == 401


# Reminder: a week after the case was linked, still not done; closing hides it for a week; never once done.
def test_checkin_reminder_week_rule():
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    case_id, ha, hb = _case()
    url = f"{API}/family-checkin/reminder"
    show = lambda h: httpx.get(url, headers=h, timeout=20).json()["show"]  # noqa: E731

    def age_case(days):
        when = _dt.now(_tz.utc) - _td(days=days)
        db.joint_alignment_cases.update_one({"case_id": case_id}, {"$set": {"created_at": when, "parents.$[].accepted_at": when}})

    age_case(3)
    assert show(ha) is False and show(hb) is False
    age_case(8)
    assert show(ha) is True and show(hb) is True
    assert httpx.post(f"{url}/dismiss", headers=ha, timeout=20).json() == {"ok": True}
    assert show(ha) is False and show(hb) is True
    uid = httpx.get(f"{API}/auth/me", headers=ha, timeout=20).json()["user_id"]
    db.family_checkin_reminder.update_one({"user_id": uid}, {"$set": {"dismissed_at": (_dt.now(_tz.utc) - _td(days=8)).isoformat()}})
    assert show(ha) is True
    assert _send(_body(case_id, 1, set_by="default", offered=True)).status_code == 200
    assert show(ha) is False and show(hb) is False
    assert "no-store" in httpx.get(url, headers=ha, timeout=20).headers.get("cache-control", "")
    assert httpx.get(url, timeout=20).status_code == 401
