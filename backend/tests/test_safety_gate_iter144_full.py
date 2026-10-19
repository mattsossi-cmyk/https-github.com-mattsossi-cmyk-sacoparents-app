# Iter144 live regression: Safety Gate webhook signing/timestamps/versioning/lock, real two-parent join flow,
# plan options, no notifications, admin align-status / self-test / align-ping / link-health.
# The webhook secret is loaded via dotenv only and is never printed.
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
BASE_URL = FE["REACT_APP_BACKEND_URL"].rstrip("/")
SECRET = BE.get("ALIGN_WEBHOOK_SECRET")
if not SECRET:
    pytest.skip("webhook off", allow_module_level=True)
DB = MongoClient(BE["MONGO_URL"].strip('"'))[BE["DB_NAME"].strip('"')]
URL = f"{BASE_URL}/api/internal/safety-status"
BANNED = ["safety", "screening", "violence", "risk", "restricted", "structured", "auto_red", "professional_name"]
PRO_NAME = "Dr TESTPRO Zed"
BANNER = "Some features are set by your professional for this case."
LIMITED_OFF = ["free_form_messaging", "calls_video", "addresses_visible", "gps_checkins", "read_receipts", "last_seen", "typing_indicators"]
STATE = {}


def leaks(text):
    return bool(SECRET) and SECRET in text


def sign(raw):
    return hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()


def post_raw(raw, headers):
    return requests.post(URL, data=raw, headers={"Content-Type": "application/json", **headers})


def send(b, prefix=""):
    raw = json.dumps(b).encode()
    return post_raw(raw, {"X-Align-Signature": prefix + sign(raw)})


def body(version, **kw):
    b = {"case_id": STATE["case_id"], "safety_mode": "restricted", "set_by": "auto_red", "professional_name": PRO_NAME,
         "referral": "parallel_parenting", "screening_offered": True, "version": version, "timestamp": int(time.time())}
    b.update(kw)
    return b


def register(tag):
    s = requests.Session()
    email = f"test_sg144_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": f"TEST {tag}",
                                                     "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    tok = r.json().get("access_token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    uid = s.get(f"{BASE_URL}/api/auth/me").json()["user_id"]
    return s, uid, email


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    if r.json().get("access_token"):
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def footprint(uids, emails):
    skip = {"users", "joint_alignment_cases", "plan_option_picks", "safety_audit_log", "user_sessions", "sessions",
            "login_attempts", "refresh_tokens", "auth_events"}
    q = {"$or": [{"user_id": {"$in": uids}}, {"email": {"$in": emails}}, {"to": {"$in": emails}},
                 {"recipient": {"$in": emails}}, {"recipient_user_id": {"$in": uids}}]}
    return {c: DB[c].count_documents(q) for c in DB.list_collection_names() if c not in skip}


def settings(s):
    r = s.get(f"{BASE_URL}/api/case-settings")
    assert r.status_code == 200
    return r


@pytest.fixture(scope="module", autouse=True)
def linked():
    pro, upro, epro = register("pro")
    a, ua, ea = register("a")
    b, ub, eb = register("b")
    r = pro.post(f"{BASE_URL}/api/professional/joint-alignment/cases", json={
        "assessment_type": "co-parenting", "parents": [{"email": ea, "name": "TEST A"}, {"email": eb, "name": "TEST B"}],
        "professional_name": PRO_NAME})
    assert r.status_code in (200, 201), r.text
    case_id = r.json()["case_id"]
    STATE.update(case_id=case_id, a=a, b=b, ua=ua, ub=ub, ea=ea, eb=eb, real_flow=True)
    for s in (a, b):
        j = s.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": case_id})
        assert j.status_code == 200, j.text
    yield
    DB.joint_alignment_cases.delete_many({"case_id": case_id})
    DB.case_safety.delete_many({"case_id": case_id})
    DB.safety_audit_log.delete_many({"case_id": case_id})
    DB.plan_option_picks.delete_many({"user_id": {"$in": [ua, ub]}})
    DB.users.delete_many({"email": {"$in": [ea, eb, epro]}})


class TestWebhook:
    def test_case_linked_both_parents(self):
        doc = DB.joint_alignment_cases.find_one({"case_id": STATE["case_id"]})
        assert STATE["case_id"].startswith("SA-")
        assert {p.get("user_id") for p in doc["parents"]} == {STATE["ua"], STATE["ub"]}

    def test_default_identical(self):
        ra, rb = settings(STATE["a"]), settings(STATE["b"])
        assert ra.content == rb.content
        assert "no-store" in ra.headers.get("cache-control", "")

    def test_bad_signatures_and_headers(self):
        b = body(1)
        raw = json.dumps(b).encode()
        good = sign(raw)
        for h in ({"X-Align-Signature": "deadbeef"}, {"X-Align-Signature": ""}, {},
                  {"X-Align-Signature": hmac.new(b"wrong", raw, hashlib.sha256).hexdigest()},
                  {"X-Signature": good}, {"X-Hub-Signature": good}, {"X-Hub-Signature-256": "sha256=" + good},
                  {"Authorization": good}, {"Authorization": f"Bearer {good}"}):
            assert post_raw(raw, h).status_code == 401, h.keys()
        assert DB.case_safety.find_one({"case_id": STATE["case_id"]}) is None

    def test_reserialised_body_fails(self):
        b = body(1)
        signed = json.dumps(b).encode()
        other = json.dumps(b, separators=(",", ":")).encode()
        assert other != signed
        assert post_raw(other, {"X-Align-Signature": sign(signed)}).status_code == 401
        assert DB.case_safety.find_one({"case_id": STATE["case_id"]}) is None

    def test_old_and_future_timestamps(self):
        now = time.time()
        bad = [int(now) - 400, int(now) + 400, int((now - 400) * 1000), str(int(now) - 400),
               (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat(),
               datetime.now(timezone.utc).replace(tzinfo=None).isoformat(), "garbage", True]
        for ts in bad:
            r = send(body(1, timestamp=ts))
            assert r.status_code in (401, 422), (ts, r.status_code)
        assert DB.case_safety.find_one({"case_id": STATE["case_id"]}) is None

    def test_timestamp_formats_accepted(self):
        # structured/professional updates with increasing versions, each format must apply
        fmts = [int(time.time()), int(time.time() * 1000), str(int(time.time())),
                datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")]
        for i, ts in enumerate(fmts, start=1):
            r = send(body(i, safety_mode="structured", set_by="professional", referral="none", timestamp=ts),
                     prefix="sha256=" if i % 2 else "")
            assert r.status_code == 200, (ts, r.text)
            assert DB.case_safety.find_one({"case_id": STATE["case_id"]})["version"] == i

    def test_restricted_auto_red_both_identical(self):
        before = footprint([STATE["ua"], STATE["ub"]], [STATE["ea"], STATE["eb"]])
        STATE["fp_before"] = before
        bd = body(20)
        assert send(bd).status_code == 200
        assert send(bd).status_code == 409
        ra, rb = settings(STATE["a"]), settings(STATE["b"])
        assert ra.content == rb.content
        d = ra.json()
        assert d["banner"] == BANNER and d["plan_options"] is True
        assert all(d["features"][k] is False for k in LIMITED_OFF)
        assert d["features"]["file_metadata"] == "all_removed"
        low = ra.text.lower()
        assert PRO_NAME.lower() not in low and "testpro" not in low
        assert not any(w in low for w in BANNED), [w for w in BANNED if w in low]

    def test_stale_equal_and_lower(self):
        before = settings(STATE["a"]).content
        assert send(body(20, safety_mode="standard", set_by="professional", referral="none")).status_code == 200
        assert send(body(4, safety_mode="standard", set_by="professional", referral="none")).status_code == 200
        assert settings(STATE["a"]).content == before == settings(STATE["b"]).content
        assert DB.case_safety.find_one({"case_id": STATE["case_id"]})["version"] == 20

    @pytest.mark.parametrize("v,mode,set_by", [(21, "standard", "default"), (22, "structured", "default"),
                                               (23, "restricted", "default"), (24, "standard", "auto_red"),
                                               (25, "structured", "auto_red")])
    def test_lock(self, v, mode, set_by):
        before = settings(STATE["a"]).content
        assert send(body(v, safety_mode=mode, set_by=set_by, referral="none")).status_code == 200
        assert settings(STATE["a"]).content == before == settings(STATE["b"]).content
        assert DB.case_safety.find_one({"case_id": STATE["case_id"]})["version"] == 20

    def test_auto_red_resend_keeps_restricted_applies(self):
        assert send(body(26, note_review=True)).status_code == 200
        assert DB.case_safety.find_one({"case_id": STATE["case_id"]})["version"] == 26
        ra, rb = settings(STATE["a"]), settings(STATE["b"])
        assert ra.content == rb.content and ra.json()["features"]["template_note_review"] is True

    def test_plan_options(self):
        a, b = STATE["a"], STATE["b"]
        ra, rb = a.get(f"{BASE_URL}/api/plan-options"), b.get(f"{BASE_URL}/api/plan-options")
        assert ra.status_code == 200 and ra.content == rb.content
        ids = [o["id"] for c in ra.json()["categories"] for o in c["options"]]
        assert ids and "comm_flexible_dm" not in ids
        r = a.put(f"{BASE_URL}/api/plan-options/picks", json={"picks": [ids[0], "comm_flexible_dm", "nope"]})
        assert r.status_code == 200 and r.json()["picks"] == [ids[0]]
        assert b.get(f"{BASE_URL}/api/plan-options/picks").json()["picks"] == []

    def test_professional_lifts_then_no_notifications(self):
        assert send(body(30, safety_mode="standard", set_by="professional", referral="none")).status_code == 200
        ra, rb = settings(STATE["a"]), settings(STATE["b"])
        assert ra.content == rb.content and ra.json()["banner"] is None and ra.json()["plan_options"] is False
        full = STATE["a"].get(f"{BASE_URL}/api/plan-options").json()
        assert "comm_flexible_dm" in [o["id"] for c in full["categories"] for o in c["options"]]
        after = footprint([STATE["ua"], STATE["ub"]], [STATE["ea"], STATE["eb"]])
        diff = {k: (STATE["fp_before"].get(k, 0), v) for k, v in after.items() if v != STATE["fp_before"].get(k, 0)}
        assert diff == {}, diff


class TestAdmin:
    @pytest.fixture(scope="class")
    def adm(self):
        return login("mattsossi@bsossi.com", "AdminPass123!")

    def test_align_status(self, adm):
        r = adm.get(f"{BASE_URL}/api/admin/safety-audit-log/align-status")
        assert r.status_code == 200 and "no-store" in r.headers.get("cache-control", "")
        d = r.json()
        assert d["webhook_on"] is True
        assert d["last_update"]["result"] in ("applied", "ignored")
        assert set(d["rejected_30d"]) == {"bad_signature", "old_timestamp", "invalid_body", "replay", "webhook_off"}
        assert d["rejected_30d"]["bad_signature"] > 0 and d["rejected_30d"]["replay"] > 0
        assert not leaks(r.text)

    def test_self_test_ok(self, adm):
        r = adm.post(f"{BASE_URL}/api/admin/safety-audit-log/self-test")
        assert r.status_code == 200 and r.json()["ok"] is True, r.json().get("reason")
        assert not leaks(r.text)

    def test_align_ping_not_configured(self, adm):
        r = adm.post(f"{BASE_URL}/api/admin/safety-audit-log/align-ping")
        assert r.status_code == 200 and r.json() == {"configured": False}

    def test_link_health(self, adm):
        r = adm.get(f"{BASE_URL}/api/admin/safety-audit-log/link-health")
        assert r.status_code == 200 and "no-store" in r.headers.get("cache-control", "")
        assert r.json()["ok"] is False  # refusals in last 24h
        p = login("parent1@test.com", "TestPass123!")
        for path in ("link-health", "align-status", "export"):
            assert p.get(f"{BASE_URL}/api/admin/safety-audit-log/{path}").status_code == 403
        assert p.post(f"{BASE_URL}/api/admin/safety-audit-log/self-test").status_code == 403
        assert requests.get(f"{BASE_URL}/api/admin/safety-audit-log/link-health").status_code in (401, 403)
