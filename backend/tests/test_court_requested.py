"""Court-ordered journey: /api/court-path/requested CRUD."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
EMAIL = "journey6@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    if r.status_code != 200:
        # fallback
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "parent1@test.com", "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


def test_unauth_requires_401():
    r = requests.get(f"{BASE_URL}/api/court-path/requested", timeout=10)
    assert r.status_code in (401, 403)


def test_get_initial(session):
    r = session.get(f"{BASE_URL}/api/court-path/requested", timeout=10)
    assert r.status_code == 200
    assert "keys" in r.json()
    assert isinstance(r.json()["keys"], list)


def test_put_valid_keys_persist(session):
    r = session.put(f"{BASE_URL}/api/court-path/requested", json={"keys": ["self", "foundation"]}, timeout=10)
    assert r.status_code == 200
    assert set(r.json()["keys"]) == {"self", "foundation"}
    # GET verifies persistence
    r2 = session.get(f"{BASE_URL}/api/court-path/requested", timeout=10)
    assert set(r2.json()["keys"]) == {"self", "foundation"}


def test_put_duplicates_collapse_and_order(session):
    r = session.put(f"{BASE_URL}/api/court-path/requested",
                    json={"keys": ["parallel", "self", "self", "coparent"]}, timeout=10)
    assert r.status_code == 200
    # order follows REQUESTABLE: coparent,self,...parallel
    assert r.json()["keys"] == ["coparent", "self", "parallel"]


def test_put_invalid_key_422(session):
    r = session.put(f"{BASE_URL}/api/court-path/requested", json={"keys": ["bogus"]}, timeout=10)
    assert r.status_code == 422


def test_put_empty_clears(session):
    r = session.put(f"{BASE_URL}/api/court-path/requested", json={"keys": []}, timeout=10)
    assert r.status_code == 200
    assert r.json()["keys"] == []
    r2 = session.get(f"{BASE_URL}/api/court-path/requested", timeout=10)
    assert r2.json()["keys"] == []
