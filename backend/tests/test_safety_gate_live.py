# Live (public URL) regression tests for Safety Gate: webhook, /case-settings, plan options, help services, admin gating
import hashlib
import hmac
import json
import os
import time
import uuid

import pytest
pytestmark = pytest.mark.skip(reason="Built for the removed auto_red rule (2026-10-19); covered by test_safety_gate.py and test_safety_gate_correction.py.")
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
BASE_URL = FE["REACT_APP_BACKEND_URL"].rstrip("/")
SECRET = BE.get("ALIGN_WEBHOOK_SECRET")

if not SECRET or BE.get("WEBHOOKS_ENABLED") != "true":
    pytest.skip("ALIGN_WEBHOOK_SECRET is not set: the webhook is off", allow_module_level=True)
DB = MongoClient(BE["MONGO_URL"].strip('"'))[BE["DB_NAME"].strip('"')]
CASE_ID = "SA-T" + uuid.uuid4().hex[:5].upper()
BANNED = ["safety", "screening", "violence", "risk", "restricted", "structured", "auto_red", "professional_name"]


def send(body, secret=SECRET, sig=None):
    raw = json.dumps(body).encode()
    s = sig if sig is not None else hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return requests.post(f"{BASE_URL}/api/internal/safety-status", data=raw,
                         headers={"Content-Type": "application/json", "X-Align-Signature": s})


def body(version, **kw):
    b = {"case_id": CASE_ID, "safety_mode": "restricted", "set_by": "auto_red", "professional_name": "Dr TEST",
         "referral": "parallel_parenting", "screening_offered": True, "version": version, "timestamp": int(time.time())}
    b.update(kw)
    return b


def register(tag):
    s = requests.Session()
    email = f"test_sg_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": f"TEST {tag}",
                                                     "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    uid = r.json().get("user", r.json()).get("user_id") or s.get(f"{BASE_URL}/api/auth/me").json()["user_id"]
    return s, uid, email


@pytest.fixture(scope="module")
def parents():
    a, ua, ea = register("a")
    b, ub, eb = register("b")
    DB.joint_alignment_cases.insert_one({"case_id": CASE_ID, "status": "pending",
                                         "parents": [{"parent_slot": "A", "user_id": ua}, {"parent_slot": "B", "user_id": ub}]})
    yield a, b
    DB.joint_alignment_cases.delete_many({"case_id": CASE_ID})
    DB.case_safety.delete_many({"case_id": CASE_ID})
    DB.safety_audit_log.delete_many({"case_id": CASE_ID})
    DB.plan_option_picks.delete_many({"user_id": {"$in": [ua, ub]}})
    DB.users.delete_many({"email": {"$in": [ea, eb]}})


def login(email):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "TestPass123!" if "bsossi" not in email else "AdminPass123!"})
    assert r.status_code == 200, r.text
    return s


class TestSafetyGateLive:
    def test_default_structured_banner(self, parents):
        a, b = parents
        ra, rb = a.get(f"{BASE_URL}/api/case-settings"), b.get(f"{BASE_URL}/api/case-settings")
        assert ra.status_code == 200 and ra.content == rb.content
        d = ra.json()
        assert d["banner"] == "Some features are limited until your case setup is complete."
        assert d["plan_options"] is False
        assert not any(w in ra.text.lower() for w in BANNED)

    def test_bad_signature_401(self, parents):
        assert send(body(1), sig="deadbeef").status_code == 401
        assert send(body(1), sig="").status_code == 401
        assert send(body(1), secret="wrong").status_code == 401
        assert DB.case_safety.find_one({"case_id": CASE_ID}) is None

    def test_old_timestamp_401(self, parents):
        assert send(body(1, timestamp=int(time.time()) - 400)).status_code == 401
        assert DB.case_safety.find_one({"case_id": CASE_ID}) is None

    def test_auto_red_applies_and_replay_409(self, parents):
        a, b = parents
        bd = body(5)
        assert send(bd).status_code == 200
        assert send(bd).status_code == 409
        ra, rb = a.get(f"{BASE_URL}/api/case-settings"), b.get(f"{BASE_URL}/api/case-settings")
        assert ra.content == rb.content
        d = ra.json()
        assert d["banner"] == "Some features are set by your professional for this case."
        assert d["plan_options"] is True
        assert d["features"]["file_metadata"] == "all_removed"
        assert "Dr TEST" not in ra.text and not any(w in ra.text.lower() for w in BANNED)

    def test_stale_version_ignored(self, parents):
        a, _ = parents
        before = a.get(f"{BASE_URL}/api/case-settings").content
        assert send(body(5, safety_mode="standard", set_by="professional", referral="none")).status_code == 200
        assert send(body(3, safety_mode="standard", set_by="professional", referral="none")).status_code == 200
        assert a.get(f"{BASE_URL}/api/case-settings").content == before

    def test_auto_red_lock_default_ignored(self, parents):
        a, _ = parents
        before = a.get(f"{BASE_URL}/api/case-settings").content
        assert send(body(6, safety_mode="standard", set_by="default", referral="none")).status_code == 200
        assert a.get(f"{BASE_URL}/api/case-settings").content == before

    def test_auto_red_lock_auto_red_standard_ignored(self, parents):
        # Spec: auto_red+restricted stays until set_by=professional
        a, _ = parents
        before = a.get(f"{BASE_URL}/api/case-settings").content
        assert send(body(7, safety_mode="standard", set_by="auto_red", referral="none")).status_code == 200
        assert a.get(f"{BASE_URL}/api/case-settings").content == before

    def test_plan_options_parallel_only_and_picks(self, parents):
        a, b = parents
        ra, rb = a.get(f"{BASE_URL}/api/plan-options"), b.get(f"{BASE_URL}/api/plan-options")
        assert ra.status_code == 200 and ra.json() == rb.json()
        ids = [o["id"] for c in ra.json()["categories"] for o in c["options"]]
        assert ids and "comm_flexible_dm" not in ids
        r = a.put(f"{BASE_URL}/api/plan-options/picks", json={"picks": [ids[0], "comm_flexible_dm"]})
        assert r.status_code == 200 and r.json()["picks"] == [ids[0]]
        assert a.get(f"{BASE_URL}/api/plan-options/picks").json()["picks"] == [ids[0]]
        assert b.get(f"{BASE_URL}/api/plan-options/picks").json()["picks"] == []

    def test_professional_can_lift(self, parents):
        a, _ = parents
        assert send(body(10, safety_mode="standard", set_by="professional", referral="none")).status_code == 200
        d = a.get(f"{BASE_URL}/api/case-settings").json()
        assert d["banner"] is None and d["plan_options"] is False


class TestHelpAndAdmin:
    def test_public_local_services_seeded_tx(self):
        r = requests.get(f"{BASE_URL}/api/help/local-services")
        assert r.status_code == 200
        assert len([s for s in r.json()["services"] if s["state"] == "TX"]) >= 3

    def test_admin_crud_and_parent_refused(self):
        adm = login("mattsossi@bsossi.com")
        p = login("parent1@test.com")
        assert p.get(f"{BASE_URL}/api/admin/help-services").status_code == 403
        assert p.get(f"{BASE_URL}/api/admin/safety-audit-log/export").status_code == 403
        r = adm.post(f"{BASE_URL}/api/admin/help-services", json={"state": "vt", "name": "TEST_Service", "phone": "802-555-0100"})
        assert r.status_code == 200 and r.json()["state"] == "VT"
        sid = r.json()["id"]
        assert adm.put(f"{BASE_URL}/api/admin/help-services/{sid}", json={"state": "VT", "name": "TEST_Service2"}).status_code == 200
        pub = requests.get(f"{BASE_URL}/api/help/local-services").json()["services"]
        assert any(s["id"] == sid and s["name"] == "TEST_Service2" for s in pub)
        assert adm.post(f"{BASE_URL}/api/admin/help-services", json={"state": "Texas", "name": "x"}).status_code == 422
        assert adm.post(f"{BASE_URL}/api/admin/help-services", json={"state": "TX", "name": "x", "url": "javascript:alert(1)"}).status_code == 422
        assert adm.delete(f"{BASE_URL}/api/admin/help-services/{sid}").status_code == 200
        assert adm.delete(f"{BASE_URL}/api/admin/help-services/{sid}").status_code == 404
        exp = adm.get(f"{BASE_URL}/api/admin/safety-audit-log/export")
        assert exp.status_code == 200 and exp.text.startswith("at,actor_type")
