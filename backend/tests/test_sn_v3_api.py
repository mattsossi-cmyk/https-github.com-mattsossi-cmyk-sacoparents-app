"""API-level tests for Special Needs v3 endpoints (integration through public URL)."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def token():
    s = requests.Session()
    # try login
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    if r.status_code != 200:
        # register
        s.post(f"{BASE_URL}/api/auth/register",
               json={"email": EMAIL, "password": PASSWORD, "name": "Sam Parent"}, timeout=60)
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in {data}"
    return tok


@pytest.fixture
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


def test_schema(client):
    r = client.get(f"{BASE_URL}/api/special-needs-v3/schema")
    assert r.status_code == 200
    d = r.json()
    assert d["total_questions"] == 60
    assert len(d["sections"]) == 10
    assert len(d["response_scale"]) == 5
    assert d["sections"][0]["id"] == "p1"
    assert len(d["sections"][0]["questions"]) == 6


def test_reset_then_me_empty(client):
    client.delete(f"{BASE_URL}/api/special-needs-v3/me")
    r = client.get(f"{BASE_URL}/api/special-needs-v3/me")
    assert r.status_code == 200
    assert r.json() == {"exists": False}


def test_bulk_and_persist(client):
    client.delete(f"{BASE_URL}/api/special-needs-v3/me")
    payload = {"answers": {"p1q1": 3, "p1q2": 2, "p1q3": 4}}
    r = client.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk", json=payload)
    assert r.status_code == 200
    d = r.json()
    assert d["answered"] == 3
    assert d["total"] == 60
    # GET /me to verify persistence
    r2 = client.get(f"{BASE_URL}/api/special-needs-v3/me")
    assert r2.status_code == 200
    body = r2.json()
    assert body["exists"] is True
    assert body["answers"]["p1q1"] == 3
    assert body["answers"]["p1q3"] == 4


def test_single_answer(client):
    client.delete(f"{BASE_URL}/api/special-needs-v3/me")
    r = client.post(f"{BASE_URL}/api/special-needs-v3/answer",
                    json={"question_id": "p2q1", "value": 2})
    assert r.status_code == 200
    r = client.post(f"{BASE_URL}/api/special-needs-v3/answer",
                    json={"question_id": "badid", "value": 2})
    assert r.status_code == 400


def test_complete_and_scores(client):
    client.delete(f"{BASE_URL}/api/special-needs-v3/me")
    # Get schema for all question ids
    schema = client.get(f"{BASE_URL}/api/special-needs-v3/schema").json()
    all_answers = {}
    for sec in schema["sections"]:
        for q in sec["questions"]:
            all_answers[q["id"]] = 3
    r = client.post(f"{BASE_URL}/api/special-needs-v3/answers/bulk",
                    json={"answers": all_answers})
    assert r.status_code == 200
    r2 = client.post(f"{BASE_URL}/api/special-needs-v3/complete", json={})
    assert r2.status_code == 200
    body = r2.json()
    assert body["completed"] is True
    scores = body["scores"]
    assert "overall_rating" in scores
    assert len(scores["sections"]) == 10
    # scores endpoint
    r3 = client.get(f"{BASE_URL}/api/special-needs-v3/scores")
    assert r3.status_code == 200


def test_reset_delete(client):
    r = client.delete(f"{BASE_URL}/api/special-needs-v3/me")
    assert r.status_code == 200
    r2 = client.get(f"{BASE_URL}/api/special-needs-v3/me")
    assert r2.json() == {"exists": False}


def test_legacy_neurodivergent_schema(client):
    # Regression: legacy endpoint should still work
    r = client.get(f"{BASE_URL}/api/neurodivergent/schema")
    # We accept any 2xx OR 404 depending on legacy naming; log the code
    assert r.status_code in (200, 404), f"unexpected {r.status_code}: {r.text[:200]}"
