"""Shared pytest fixtures for SA Coparents Mediation Prep backend tests."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass


@pytest.fixture(scope="session")
def base_url():
    assert BASE_URL, "REACT_APP_BACKEND_URL not configured"
    return BASE_URL


@pytest.fixture
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def test_user(base_url):
    """Register a unique test user and return user info + token."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_parent_{suffix}@test.com"
    payload = {
        "email": email,
        "password": "TestPass123!",
        "name": "Sam Parent",
        "children": [{"name": "Kid A", "age": 7}],
        "custody_situation": "50/50 shared",
        "mediation_date": "2026-03-15",
    }
    r = requests.post(f"{base_url}/api/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    return {
        "email": email,
        "password": "TestPass123!",
        "name": "Sam Parent",
        "token": data["access_token"],
        "user": data["user"],
    }


@pytest.fixture
def auth_client(test_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_user['token']}",
    })
    return s
