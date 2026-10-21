# Parent dashboard (iter156): journey-path + dashboard-celebrated endpoints
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
PW = "TestPass123!"

SA_ANSWERS = {f"{s}_{i}": 3 for s in ["child_focus", "self_awareness", "communication", "differences"] for i in range(1, 6)}


def _register():
    email = f"test_dash_{uuid.uuid4().hex[:10]}@test.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": PW, "name": "TEST Dash", "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    tok = r.json().get("access_token")
    if not tok:
        tok = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PW}).json()["access_token"]
    return email, {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def fresh():
    return _register()


# ---- journey path ----
class TestJourneyPath:
    def test_me_has_no_path_initially(self, fresh):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=fresh[1])
        assert r.status_code == 200
        assert "journey_path" in r.json()
        assert r.json()["journey_path"] is None

    @pytest.mark.parametrize("p", ["court_ordered", "self_journey", "mediation_prep"])
    def test_set_valid(self, fresh, p):
        r = requests.put(f"{BASE_URL}/api/auth/journey-path", json={"path": p}, headers=fresh[1])
        assert r.status_code == 200, r.text
        assert r.json()["journey_path"] == p
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=fresh[1]).json()
        assert me["journey_path"] == p

    @pytest.mark.parametrize("body", [{"path": "bogus"}, {}, {"path": None}, {"path": "Court_Ordered"}])
    def test_invalid(self, fresh, body):
        r = requests.put(f"{BASE_URL}/api/auth/journey-path", json=body, headers=fresh[1])
        assert r.status_code == 422

    def test_unauth(self):
        r = requests.put(f"{BASE_URL}/api/auth/journey-path", json={"path": "self_journey"})
        assert r.status_code == 401

    def test_parent1_court(self):
        tok = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "parent1@test.com", "password": PW}).json()["access_token"]
        me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
        assert me["journey_path"] == "court_ordered"


# ---- dashboard celebrated ----
class TestCelebrated:
    def test_flow(self):
        _, h = _register()
        url = f"{BASE_URL}/api/journey-summary/dashboard-celebrated"
        r = requests.get(url, headers=h)
        assert r.status_code == 200 and r.json() == {"steps": None}
        # seeded with empty list
        r = requests.post(url, json={"steps": [], "seeded": True}, headers=h)
        assert r.status_code == 200 and r.json()["steps"] == {}
        assert requests.get(url, headers=h).json() == {"steps": {}}
        r = requests.post(url, json={"steps": ["communication"], "seeded": True}, headers=h)
        assert r.json()["steps"]["communication"] == "seeded"
        r = requests.post(url, json={"steps": ["selfAssessment"], "seeded": False}, headers=h)
        v = r.json()["steps"]["selfAssessment"]
        assert v != "seeded" and "T" in v
        time.sleep(1)
        r = requests.post(url, json={"steps": ["selfAssessment", "communication"], "seeded": False}, headers=h)
        assert r.json()["steps"]["selfAssessment"] == v
        assert r.json()["steps"]["communication"] == "seeded"
        g = requests.get(url, headers=h).json()["steps"]
        assert g == {"communication": "seeded", "selfAssessment": v}

    @pytest.mark.parametrize("body", [{"steps": ["checkin"]}, {"steps": "selfAssessment"}, {}, {"steps": ["foo"], "seeded": True}])
    def test_invalid(self, fresh, body):
        r = requests.post(f"{BASE_URL}/api/journey-summary/dashboard-celebrated", json=body, headers=fresh[1])
        assert r.status_code == 422

    def test_unauth(self):
        assert requests.get(f"{BASE_URL}/api/journey-summary/dashboard-celebrated").status_code == 401
        assert requests.post(f"{BASE_URL}/api/journey-summary/dashboard-celebrated", json={"steps": []}).status_code == 401

    def test_sa_complete(self, fresh):
        r = requests.post(f"{BASE_URL}/api/self-assessment/complete", json={"answers": SA_ANSWERS, "started": True, "parent_name": "X"}, headers=fresh[1])
        assert r.status_code == 200, r.text
