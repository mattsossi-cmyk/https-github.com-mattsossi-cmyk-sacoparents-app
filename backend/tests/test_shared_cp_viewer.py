"""End-to-end backend test for the public shared Co-Parenting report viewer contract.
Login -> bulk answer 67 questions -> complete -> generate report -> create share link -> fetch shared JSON/PDF.
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].strip().rstrip("/")
                break

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def token():
    # Try login; if fails, register.
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        requests.post(f"{BASE_URL}/api/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": "Sam Parent"})
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def schema():
    r = requests.get(f"{BASE_URL}/api/coparenting/schema")
    assert r.status_code == 200
    return r.json()


def test_bulk_answer_and_complete(auth_headers, schema):
    # Reset first for a clean run
    requests.delete(f"{BASE_URL}/api/coparenting/me", headers=auth_headers)
    qids = []
    for sec in schema["sections"]:
        for q in sec["questions"]:
            qids.append(q["id"])
    assert len(qids) == 67
    answers = {qid: (i % 5) for i, qid in enumerate(qids)}
    r = requests.post(f"{BASE_URL}/api/coparenting/answers/bulk", json={"answers": answers}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["answered"] == 67

    r = requests.post(f"{BASE_URL}/api/coparenting/complete", headers=auth_headers)
    assert r.status_code == 200, r.text


def test_generate_and_share(auth_headers):
    r = requests.post(f"{BASE_URL}/api/coparenting/report/generate", headers=auth_headers)
    assert r.status_code == 200, r.text
    report_id = r.json()["report_id"]
    assert report_id

    # Share with exclusion of next_steps
    r = requests.post(
        f"{BASE_URL}/api/coparenting/report/{report_id}/share-link",
        json={"excluded": ["next_steps"]},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "token" in body
    assert "path" in body
    assert "viewer_path" in body
    assert body["viewer_path"].startswith("/shared/coparenting/")
    assert body["excluded"] == ["next_steps"]

    token = body["token"]
    # public JSON fetch — no auth
    r = requests.get(f"{BASE_URL}/api/coparenting/report/shared/{token}?format=json")
    assert r.status_code == 200
    j = r.json()
    assert j["shared_by"]
    assert j["excluded_sections"] == ["next_steps"]
    assert "next_steps" not in (j["report"] or {}) or not j["report"].get("next_steps")
    assert j["report"]["overall_rating"]

    # public PDF fetch — no auth
    r = requests.get(f"{BASE_URL}/api/coparenting/report/shared/{token}?format=pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"

    # Persist token for frontend test
    with open("/tmp/share_token.txt", "w") as f:
        f.write(token)


def test_invalid_token():
    r = requests.get(f"{BASE_URL}/api/coparenting/report/shared/INVALID_TOKEN?format=json")
    assert r.status_code == 404
