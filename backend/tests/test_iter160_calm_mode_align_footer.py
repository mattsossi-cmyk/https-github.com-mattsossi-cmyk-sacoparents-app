# Iter160: Calm Mode API, Align share re-ask (wording v), export field names, privacy notice v9 — public URL.
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
KEY = {"X-Integration-Key": os.environ.get("INTEGRATION_SHARED_SECRET")}
SHARE = f"{API}/integrations/align-share/communication-readiness"
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_users = []


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for uid in _users:
        for coll in ("users", "prep_data", "align_links", "align_access_log", "align_share_choices", "link_codes", "portal_state"):
            _db[coll].delete_many({"user_id": uid})
        _db.joint_alignment_cases.delete_many({"parents.user_id": uid})


def _parent(linked=True):
    email = f"test_iter160_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "Iter160 Test",
                                                    "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    uid = r.json()["user"]["user_id"]
    _users.append(uid)
    if linked:
        code = requests.post(f"{API}/link-codes", headers=h, json={}).json()["code"]
        assert requests.post(f"{API}/integrations/verify-link-code", headers=KEY, json={"code": code}).status_code == 200
    return email, h, uid


COMM = {"answers": {"q1": "balanced", "q2": "balanced", "q3": "avoider"}, "free_text_sample": "TEST_ sample message"}


# --- Calm Mode ---
class TestCalmMode:
    def test_requires_auth(self):
        assert requests.put(f"{API}/auth/calm-mode", json={"on": True}).status_code == 401

    def test_toggle_and_persist(self):
        _, h, _ = _parent(linked=False)
        assert requests.get(f"{API}/auth/me", headers=h).json()["calm_mode"] is False
        r = requests.put(f"{API}/auth/calm-mode", headers=h, json={"on": True})
        assert r.status_code == 200 and r.json()["calm_mode"] is True
        assert requests.get(f"{API}/auth/me", headers=h).json()["calm_mode"] is True
        r = requests.put(f"{API}/auth/calm-mode", headers=h, json={"on": False})
        assert r.status_code == 200 and r.json()["calm_mode"] is False
        assert requests.get(f"{API}/auth/me", headers=h).json()["calm_mode"] is False

    @pytest.mark.parametrize("body", [{}, {"on": "maybe"}, {"on": [1]}, {"on": None}])
    def test_non_boolean_422(self, body):
        _, h, _ = _parent(linked=False)
        assert requests.put(f"{API}/auth/calm-mode", headers=h, json=body).status_code == 422


# --- Align share choice / re-ask / export ---
class TestAlignShare:
    def test_unlinked_cannot_set_choice(self):
        _, h, _ = _parent(linked=False)
        assert requests.put(SHARE, headers=h, json={"share": True}).status_code == 409

    def test_export_absent_without_yes(self):
        email, h, _ = _parent()
        assert requests.put(f"{API}/mediation/comm-style", headers=h, json=COMM).status_code == 200
        r = requests.get(f"{API}/integrations/export-assessments", params={"email": email}, headers=KEY)
        assert r.status_code == 200
        assert "communication_readiness" not in r.json()

    def test_yes_export_has_align_fields(self):
        email, h, _ = _parent()
        assert requests.put(f"{API}/mediation/comm-style", headers=h, json=COMM).status_code == 200
        s = requests.put(SHARE, headers=h, json={"share": True}).json()
        assert s["choice"] == "yes" and s["reask"] is False
        cr = requests.get(f"{API}/integrations/export-assessments", params={"email": email}, headers=KEY).json()["communication_readiness"]
        assert len(cr["answers"]) == 4
        for k in ("answered_at", "cr_conflict", "cr_child", "cr_direct", "cr_channel", "completed_at"):
            assert k in cr, k
        assert cr["cr_conflict"] == "Pause, then reply briefly and factually."
        assert cr["cr_channel"] == "TEST_ sample message"
        assert cr["completed_at"] == cr["answered_at"]

    def test_old_wording_yes_is_reasked_and_skip_clears(self):
        email, h, uid = _parent()
        requests.put(f"{API}/mediation/comm-style", headers=h, json=COMM)
        requests.put(SHARE, headers=h, json={"share": True})
        _db.align_share_choices.update_one({"user_id": uid}, {"$unset": {"wording_version": ""}})
        s = requests.get(SHARE, headers=h).json()
        assert s == {"choice": None, "decided_at": None, "reask": True}
        r = requests.get(f"{API}/integrations/export-assessments", params={"email": email}, headers=KEY).json()
        assert "communication_readiness" not in r
        d = requests.delete(SHARE, headers=h)
        assert d.status_code == 200 and d.json()["reask"] is False and d.json()["choice"] is None
        assert requests.get(SHARE, headers=h).json()["reask"] is False

    def test_reask_then_yes(self):
        _, h, uid = _parent()
        requests.put(SHARE, headers=h, json={"share": True})
        _db.align_share_choices.update_one({"user_id": uid}, {"$unset": {"wording_version": ""}})
        assert requests.get(SHARE, headers=h).json()["reask"] is True
        s = requests.put(SHARE, headers=h, json={"share": True}).json()
        assert s["choice"] == "yes" and s["reask"] is False

    def test_share_requires_auth(self):
        assert requests.get(SHARE).status_code == 401


# --- Privacy notice v9 ---
class TestPrivacyV9:
    def test_new_user_current_old_user_not(self):
        _, h, uid = _parent(linked=False)
        assert requests.get(f"{API}/auth/me", headers=h).json()["consent_current"] is True
        _db.users.update_one({"user_id": uid}, {"$set": {"privacy_notice_version": "2026-old-v8"}})
        assert requests.get(f"{API}/auth/me", headers=h).json()["consent_current"] is False
