"""iter149 - public-URL regression: Safety Gate correction + legacy assessment restored + case_id check-in link."""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient


def _base():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL="):
                url = line.split("=", 1)[1].strip()
    return url.rstrip("/")


BASE = _base() + "/api"
ADMIN = ("mattsossi@bsossi.com", "AdminPass123!")
LINK_A = ("test_linkdemo_a@example.com", "Str0ng!Pass99")
LINK_B = ("test_linkdemo_b@example.com", "Str0ng!Pass99")


def _env(key):
    for line in open("/app/backend/.env"):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(_env("MONGO_URL"))
    yield c[_env("DB_NAME")]
    c.close()


def _login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


created = []


def _register():
    email = f"test_iter149_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST Iter149",
                                                     "ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=30)
    assert r.status_code in (200, 201), r.text
    b = r.json()
    created.append(b["user"]["user_id"])
    return {"Authorization": f"Bearer {b['access_token']}"}, b["user"]["user_id"]


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo):
    yield
    if created:
        mongo.users.delete_many({"user_id": {"$in": created}})
        mongo.safety_assessments.delete_many({"user_id": {"$in": created}})
        mongo.joint_alignment_cases.delete_many({"case_id": {"$regex": "^SA-T149"}})


# --- admin auto-restricted count
class TestAutoRestricted:
    def test_admin_count(self):
        r = requests.get(f"{BASE}/admin/safety-audit-log/auto-restricted", headers=_login(*ADMIN), timeout=30)
        assert r.status_code == 200
        assert list(r.json().keys()) == ["count"] and isinstance(r.json()["count"], int)
        print("auto-restricted count:", r.json()["count"])
        assert "no-store" in r.headers.get("cache-control", "")

    def test_parent_403(self):
        h, _ = _register()
        assert requests.get(f"{BASE}/admin/safety-audit-log/auto-restricted", headers=h, timeout=30).status_code == 403

    def test_unauth(self):
        assert requests.get(f"{BASE}/admin/safety-audit-log/auto-restricted", timeout=30).status_code in (401, 403)


# --- webhook off
@pytest.mark.parametrize("body", [b"{}", b"not json", b'{"case_id":"SA-X","set_by":"auto_red","safety_mode":"restricted"}'])
def test_webhook_503(body):
    r = requests.post(f"{BASE}/internal/safety-status", data=body, headers={"Content-Type": "application/json", "X-Align-Signature": "ab"}, timeout=30)
    assert r.status_code == 503 and r.json() == {"detail": "Unavailable."}


# --- new linked case defaults to standard + check-in link
class TestNewCase:
    def test_new_case_standard_and_link(self, mongo):
        ha, ua = _register()
        hb, ub = _register()
        assert requests.get(f"{BASE}/family-checkin/link", headers=ha, timeout=30).json() == {"case_id": None}
        cid = f"SA-T149{uuid.uuid4().hex[:4].upper()}"
        now = datetime.now(timezone.utc)
        mongo.joint_alignment_cases.insert_one({"case_id": cid, "created_at": now, "align_ref": "ar_should_not_leak",
                                                "parents": [{"parent_slot": "A", "user_id": ua, "accepted_at": now},
                                                            {"parent_slot": "B", "user_id": ub, "accepted_at": now}]})
        for h in (ha, hb):
            s = requests.get(f"{BASE}/case-settings", headers=h, timeout=30).json()
            assert s["features"]["free_form_messaging"] is True and s["banner"] is None
            r = requests.get(f"{BASE}/family-checkin/link", headers=h, timeout=30)
            assert r.json() == {"case_id": cid}
            assert "align_ref" not in r.text and "no-store" in r.headers.get("cache-control", "")

    def test_link_unauth(self):
        assert requests.get(f"{BASE}/family-checkin/link", timeout=30).status_code == 401

    def test_linkdemo_pair_same_case(self):
        a = requests.get(f"{BASE}/family-checkin/link", headers=_login(*LINK_A), timeout=30).json()
        b = requests.get(f"{BASE}/family-checkin/link", headers=_login(*LINK_B), timeout=30).json()
        print("linkdemo:", a, b)
        assert a == b and a["case_id"].startswith("SA-")


# --- legacy assessment restored
@pytest.mark.skip(reason="The old in-app Safety Assessment is hidden (Align safety step); see test_align_safety_step.py.")
class TestLegacyAssessment:
    def test_full_flow(self):
        h, _ = _register()
        q = requests.get(f"{BASE}/safety-assessment/questions", timeout=30)
        assert q.status_code == 200
        qs = q.json()
        assert len(qs["section_1"]) > 0 and len(qs["section_2"]) > 0
        # incomplete -> 400
        assert requests.post(f"{BASE}/safety-assessment", json={"section_1": {}, "section_2": {}}, headers=h, timeout=30).status_code == 400
        body = {"section_1": {x["id"]: "no" for x in qs["section_1"]}, "section_2": {x["id"]: "no" for x in qs["section_2"]}}
        r = requests.post(f"{BASE}/safety-assessment", json=body, headers=h, timeout=60)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert "_id" not in doc and isinstance(doc["result"]["level"], int)
        aid = doc["assessment_id"]
        me = requests.get(f"{BASE}/safety-assessment/me", headers=h, timeout=30).json()
        assert me["assessment_id"] == aid
        pdf = requests.get(f"{BASE}/safety-assessment/{aid}/pdf", headers=h, timeout=60)
        assert pdf.status_code == 200 and "application/pdf" in pdf.headers["content-type"] and pdf.content[:4] == b"%PDF"
        for ep in ("one-pager", "court-report"):
            x = requests.get(f"{BASE}/safety-assessment/{aid}/{ep}", headers=h, timeout=60)
            print(ep, x.status_code, x.headers.get("content-type"))
            assert x.status_code == 200
        # other user cannot read
        h2, _ = _register()
        assert requests.get(f"{BASE}/safety-assessment/{aid}/pdf", headers=h2, timeout=30).status_code in (403, 404)

    def test_invite_gate_levels(self, mongo):
        h, uid = _register()
        g = requests.get(f"{BASE}/invites/coparent/gate", headers=h, timeout=30).json()
        print("gate no screen:", g)
        r = requests.post(f"{BASE}/invites/coparent", json={"email": f"test_iter149_co_{uuid.uuid4().hex[:6]}@example.com"}, headers=h, timeout=30)
        assert r.status_code == 403
        for lvl, allowed in ((1, False), (2, False), (3, True), (4, True)):
            mongo.safety_assessments.delete_many({"user_id": uid})
            mongo.safety_assessments.insert_one({"assessment_id": f"sa_{uuid.uuid4().hex[:12]}", "user_id": uid,
                                                  "result": {"level": lvl}, "created_at": datetime.now(timezone.utc).isoformat()})
            g = requests.get(f"{BASE}/invites/coparent/gate", headers=h, timeout=30).json()
            print(lvl, g)
            assert bool(g.get("clear")) == allowed
