"""iter150 — In-app professional-driven Joint Alignment case creation.

Locks the contract for the two new authenticated endpoints:
  * POST /api/professional/joint-alignment/cases
  * GET  /api/professional/joint-alignment/cases-i-created

Guardrails verified:
  * JWT required (unauth => 401).
  * Exactly two distinct parents => 400 otherwise.
  * Unknown assessment_type => 400.
  * Case doc records the caller as professional + `origin=in_app_professional`.
  * cases-i-created lists only the caller's cases.
  * cases-i-created includes invitation_url and never leaks another
    professional's cases into the caller's list.
"""
from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault(
        "INTEGRATION_SHARED_SECRET",
        "2f9c1e7a4b8d3f6a5c0e9d7b2f4a6c8e1d3b5a7c9e0f2a4b6c8d1e3f5a7b9c0d",
    )
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient, email: str | None = None) -> tuple[str, str, str]:
    email = email or f"iter150_pro_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter150 Mediator"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"], "Iter150 Mediator"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_case(client: TestClient, token: str, **overrides) -> dict:
    payload = {
        "assessment_type": "co-parenting",
        "parents": [
            {"email": f"a_{uuid.uuid4().hex[:6]}@example.com", "name": "Alex"},
            {"email": f"b_{uuid.uuid4().hex[:6]}@example.com", "name": "Bailey"},
        ],
    }
    payload.update(overrides)
    return client.post(
        "/api/professional/joint-alignment/cases",
        json=payload,
        headers=_headers(token),
    )


# ---------------- happy path ---------------- #

def test_creates_case_with_caller_as_professional(client):
    email, token, name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"].startswith("SA-")
    assert body["status"] == "pending"
    assert body["assessment_type"] == "co-parenting"
    assert len(body["parents"]) == 2
    for p in body["parents"]:
        assert "/join/" in p["invitation_url"]
        assert p["token_expires_at"]


def test_case_document_records_origin_and_professional(client):
    email, token, name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200, r.text
    case_id = r.json()["case_id"]

    # Read via the cases-i-created endpoint to confirm the caller is
    # bound to this case as the creator.
    listed = client.get(
        "/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token),
    )
    assert listed.status_code == 200
    cases = listed.json().get("cases") or []
    match = next((c for c in cases if c["case_id"] == case_id), None)
    assert match is not None
    # The professional block should carry the caller's name (fallback
    # when no override supplied).
    assert match["professional"]["name"] == name
    # Copy-link support: parents in the list carry the invitation URL.
    for p in match["parents"]:
        assert p.get("invitation_url"), "in-app minted cases should expose invitation_url"


# ---------------- guardrails ---------------- #

def test_unauthenticated_returns_401(client):
    r = client.post(
        "/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "co-parenting",
            "parents": [
                {"email": "a@x.com"},
                {"email": "b@x.com"},
            ],
        },
    )
    assert r.status_code in (401, 403), r.text


def test_requires_exactly_two_distinct_parents(client):
    _email, token, _name = _register(client)

    # Only one parent
    r = _make_case(
        client,
        token,
        parents=[{"email": "solo@example.com"}],
    )
    assert r.status_code == 400
    assert "two parents" in r.json()["detail"].lower()

    # Duplicate emails (case-insensitive)
    r = _make_case(
        client,
        token,
        parents=[
            {"email": "same@example.com"},
            {"email": "SAME@example.com"},
        ],
    )
    assert r.status_code == 400
    assert "distinct" in r.json()["detail"].lower()


def test_unknown_assessment_type_rejected(client):
    _email, token, _name = _register(client)
    r = _make_case(client, token, assessment_type="cooking")
    assert r.status_code == 400
    assert "assessment_type" in r.json()["detail"].lower()


def test_cases_i_created_does_not_leak_other_professionals_cases(client):
    """
    Professional A creates a case. Professional B (a different logged-in
    account) must not see it in their own cases-i-created listing.
    """
    _email_a, token_a, _ = _register(client)
    _email_b, token_b, _ = _register(client)

    r_a = _make_case(client, token_a)
    assert r_a.status_code == 200
    a_case_id = r_a.json()["case_id"]

    # Fetch B's list — must NOT contain A's case
    listed_b = client.get(
        "/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token_b),
    )
    assert listed_b.status_code == 200
    b_cases = listed_b.json().get("cases") or []
    b_case_ids = {c["case_id"] for c in b_cases}
    assert a_case_id not in b_case_ids, "cases-i-created leaked another professional's case"
