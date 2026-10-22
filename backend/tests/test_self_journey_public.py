# Self Journey API regression via public URL (auth, isolation, validation, unknown keys, concern rule)
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _register():
    s = requests.Session()
    email = f"test_sj_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST SJ",
                                                       "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def a():
    return _register()


@pytest.fixture(scope="module")
def b():
    return _register()


def test_unauth_401():
    assert requests.get(f"{BASE_URL}/api/self-journey/me").status_code == 401
    assert requests.put(f"{BASE_URL}/api/self-journey/me", json={}).status_code == 401


def test_new_parent_empty(a):
    r = a.get(f"{BASE_URL}/api/self-journey/me")
    assert r.status_code == 200 and r.json()["progress"] is None


def test_save_reload_unknown_keys_dropped(a):
    body = {"maxStepReached": 2, "safety": {"status": "clear"},
            "situation": {"currentSituation": "TEST_note", "hacker": "x"},
            "mediation": {"issues": "TEST_issue", "bogus": "y"}, "extraTop": 1}
    r = a.put(f"{BASE_URL}/api/self-journey/me", json=body)
    assert r.status_code == 200
    p = a.get(f"{BASE_URL}/api/self-journey/me").json()["progress"]
    assert p["maxStepReached"] == 2 and p["safety"]["status"] == "clear"
    assert p["situation"] == {"currentSituation": "TEST_note"}
    assert p["mediation"] == {"issues": "TEST_issue"}
    assert "extraTop" not in p


@pytest.mark.parametrize("bad", [{"maxStepReached": 8}, {"maxStepReached": -1}, {"safety": {"status": "maybe"}},
                                 {"coparenting": {"approach": "x"}}])
def test_validation_422(a, bad):
    assert a.put(f"{BASE_URL}/api/self-journey/me", json=bad).status_code == 422


def test_concern_drops_cooperative(a):
    r = a.put(f"{BASE_URL}/api/self-journey/me", json={"safety": {"status": "concern"}, "coparenting": {"approach": "cooperative"}})
    assert r.status_code == 200 and r.json()["progress"]["coparenting"]["approach"] is None
    assert a.get(f"{BASE_URL}/api/self-journey/me").json()["progress"]["coparenting"]["approach"] is None


def test_isolation(a, b):
    assert b.get(f"{BASE_URL}/api/self-journey/me").json()["progress"] is None
