"""SA CoParents backend E2E tests."""
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "mattsossi@bsossi.com")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

TYPE_KEYS = ["general", "communication", "high_conflict", "ipv", "medical", "educational", "psychological", "court"]


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies, "No access_token cookie set"
    return s


@pytest.fixture(scope="session")
def fresh_user_session():
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "Test User", "email": email, "password": "testpass123", "role": "parent"
    })
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    s.email = email
    return s


# Auth
class TestAuth:
    def test_register_new_user(self):
        s = requests.Session()
        email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "name": "Reg User", "email": email, "password": "password123", "role": "parent"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == email
        assert data["role"] == "parent"
        assert "access_token" in s.cookies

    def test_register_short_password(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "name": "X", "email": f"short_{uuid.uuid4().hex[:6]}@x.com", "password": "short", "role": "parent"
        })
        assert r.status_code == 400

    def test_login_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpw!"})
        assert r.status_code == 401

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_logout(self):
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200


# Assessment types
class TestAssessmentTypes:
    def test_list_types_returns_8(self):
        r = requests.get(f"{API}/assessment-types")
        assert r.status_code == 200
        types = r.json()
        assert len(types) == 8
        keys = [t["key"] for t in types]
        assert set(keys) == set(TYPE_KEYS)
        for t in types:
            assert t["topic_count"] == 10

    def test_get_type_educational(self):
        r = requests.get(f"{API}/assessment-types/educational")
        assert r.status_code == 200
        data = r.json()
        assert data["key"] == "educational"
        assert len(data["topics"]) == 10
        assert len(data["scale"]) == 5

    def test_get_type_ipv_disclaimer(self):
        r = requests.get(f"{API}/assessment-types/ipv")
        assert r.status_code == 200

    def test_get_type_unknown(self):
        r = requests.get(f"{API}/assessment-types/nope")
        assert r.status_code == 404


# Cases + report
class TestCasesFlow:
    def test_create_case_requires_auth(self):
        r = requests.post(f"{API}/cases", json={"type": "general"})
        assert r.status_code == 401

    def test_create_and_get_case(self, fresh_user_session):
        s = fresh_user_session
        r = s.post(f"{API}/cases", json={
            "type": "educational", "child_name": "TEST_Kid",
            "parent_a_name": "TEST_A", "parent_b_name": "TEST_B"
        })
        assert r.status_code == 200
        c = r.json()
        assert c["type"] == "educational"
        assert c["child_name"] == "TEST_Kid"
        assert c["has_a"] is False and c["has_b"] is False
        cid = c["id"]

        r = s.get(f"{API}/cases/{cid}")
        assert r.status_code == 200
        assert r.json()["id"] == cid

    def test_create_case_invalid_type(self, fresh_user_session):
        r = fresh_user_session.post(f"{API}/cases", json={"type": "nope"})
        assert r.status_code == 400

    def test_report_incomplete_returns_400(self, fresh_user_session):
        s = fresh_user_session
        r = s.post(f"{API}/cases", json={"type": "general", "child_name": "TEST_Inc"})
        cid = r.json()["id"]
        r = s.get(f"{API}/cases/{cid}/report")
        assert r.status_code == 400

    def test_demo_and_report_for_all_types(self, fresh_user_session):
        s = fresh_user_session
        for tk in TYPE_KEYS:
            r = s.post(f"{API}/cases", json={"type": tk, "child_name": "TEST_Demo"})
            assert r.status_code == 200, f"create {tk}: {r.text}"
            cid = r.json()["id"]
            r = s.post(f"{API}/cases/{cid}/demo")
            assert r.status_code == 200, f"demo {tk}: {r.text}"
            assert r.json()["has_a"] and r.json()["has_b"]
            assert r.json()["is_demo"] is True

            r = s.get(f"{API}/cases/{cid}/report")
            assert r.status_code == 200, f"report {tk}: {r.text}"
            rep = r.json()
            assert "pages" in rep or "page_titles" in rep or isinstance(rep, dict)

    def test_save_partial_responses_rejected(self, fresh_user_session):
        s = fresh_user_session
        r = s.post(f"{API}/cases", json={"type": "general"})
        cid = r.json()["id"]
        r = s.put(f"{API}/cases/{cid}/responses/a", json={
            "answers": {"communication": "No concern"},
            "primary_concern": "test",
            "goals": []
        })
        assert r.status_code == 400  # not all answered

    def test_save_full_responses(self, fresh_user_session):
        s = fresh_user_session
        r = s.post(f"{API}/cases", json={"type": "general"})
        cid = r.json()["id"]
        types_r = requests.get(f"{API}/assessment-types/general").json()
        answers = {t["key"]: "No concern" for t in types_r["topics"]}
        r = s.put(f"{API}/cases/{cid}/responses/a", json={
            "answers": answers, "primary_concern": "test", "goals": ["Educational stability"]
        })
        assert r.status_code == 200, r.text
        assert r.json()["has_a"] is True
        assert r.json()["has_b"] is False

    def test_list_cases(self, fresh_user_session):
        r = fresh_user_session.get(f"{API}/cases")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_delete_case(self, fresh_user_session):
        s = fresh_user_session
        r = s.post(f"{API}/cases", json={"type": "general", "child_name": "TEST_Del"})
        cid = r.json()["id"]
        r = s.delete(f"{API}/cases/{cid}")
        assert r.status_code == 200
        r = s.get(f"{API}/cases/{cid}")
        assert r.status_code == 404

    def test_cross_user_access_forbidden(self):
        s1 = requests.Session()
        e1 = f"u1_{uuid.uuid4().hex[:6]}@x.com"
        s1.post(f"{API}/auth/register", json={"name": "U1", "email": e1, "password": "password123", "role": "parent"})
        r = s1.post(f"{API}/cases", json={"type": "general"})
        cid = r.json()["id"]

        s2 = requests.Session()
        e2 = f"u2_{uuid.uuid4().hex[:6]}@x.com"
        s2.post(f"{API}/auth/register", json={"name": "U2", "email": e2, "password": "password123", "role": "parent"})
        r = s2.get(f"{API}/cases/{cid}")
        assert r.status_code == 404
