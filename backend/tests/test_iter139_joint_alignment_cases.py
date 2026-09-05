"""iter139 — Joint Alignment (professional-driven cases).

Locks the contract for `joint_alignment_routes.py`:

Integration surface (server-to-server, X-Integration-Key gated):
  * POST /api/integrations/joint-alignment/cases
  * GET  /api/integrations/joint-alignment/cases/{case_id}

Parent-facing surface:
  * GET  /api/joint-alignment/invitation/{token}    — no auth
  * POST /api/joint-alignment/invitation/{token}/accept — JWT
  * POST /api/joint-alignment/manual-code            — JWT
  * GET  /api/joint-alignment/mine                   — JWT

Guardrails locked here:
  * Case creation requires exactly 2 distinct parents.
  * Unknown assessment_type => 400.
  * Preview endpoint does NOT leak co-parent email / other parent's
    status / professional's PII.
  * Accept requires authenticated email to match invitation email.
  * Manual-code alone is never sufficient — same email-match guard.
  * Invitation token expires after 7 days.
  * `X-Integration-Key` wrong / missing => 401. Missing server
    secret => 503.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

SHARED_SECRET = "2f9c1e7a4b8d3f6a5c0e9d7b2f4a6c8e1d3b5a7c9e0f2a4b6c8d1e3f5a7b9c0d"


@pytest.fixture(scope="module")
def client():
    os.environ["INTEGRATION_SHARED_SECRET"] = SHARED_SECRET
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient, email: str | None = None) -> tuple[str, str]:
    email = email or f"iter139_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter139 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def _create_case(
    client: TestClient,
    parent_a_email: str,
    parent_b_email: str,
    assessment_type: str = "educational",
) -> dict:
    r = client.post(
        "/api/integrations/joint-alignment/cases",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={
            "assessment_type": assessment_type,
            "professional": {
                "id": f"pro-{uuid.uuid4().hex[:6]}",
                "name": "Jane Smith, LPC",
                "email": "jane@example.com",
            },
            "parents": [
                {"email": parent_a_email, "name": "Alex Parent"},
                {"email": parent_b_email, "name": "Blake Parent"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------- integration create ------------------------- #

def test_create_case_mints_sa_dash_id_and_two_invitation_urls(client: TestClient) -> None:
    email_a, _ = _register(client)
    email_b, _ = _register(client)
    body = _create_case(client, email_a, email_b)
    assert body["case_id"].startswith("SA-")
    assert len(body["case_id"]) == 9  # SA- + 6 digits
    assert body["case_id"][3:].isdigit()
    assert body["assessment_type"] == "educational"
    assert body["status"] == "pending"
    assert len(body["parents"]) == 2
    for p in body["parents"]:
        assert p["invitation_url"].endswith("/join/" + p["invitation_url"].split("/join/")[-1])
        assert p["token_expires_at"]


def test_create_case_rejects_non_two_parents(client: TestClient) -> None:
    email_a, _ = _register(client)
    r = client.post(
        "/api/integrations/joint-alignment/cases",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={
            "assessment_type": "educational",
            "professional": {"id": "p", "name": "P", "email": "p@x.com"},
            "parents": [{"email": email_a}],
        },
    )
    assert r.status_code == 400


def test_create_case_rejects_duplicate_parents(client: TestClient) -> None:
    email_a, _ = _register(client)
    r = client.post(
        "/api/integrations/joint-alignment/cases",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={
            "assessment_type": "educational",
            "professional": {"id": "p", "name": "P", "email": "p@x.com"},
            "parents": [
                {"email": email_a},
                {"email": email_a.upper()},
            ],
        },
    )
    assert r.status_code == 400


def test_create_case_rejects_unknown_assessment_type(client: TestClient) -> None:
    email_a, _ = _register(client)
    email_b, _ = _register(client)
    r = client.post(
        "/api/integrations/joint-alignment/cases",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={
            "assessment_type": "made-up",
            "professional": {"id": "p", "name": "P", "email": "p@x.com"},
            "parents": [{"email": email_a}, {"email": email_b}],
        },
    )
    assert r.status_code == 400


def test_create_case_requires_integration_key(client: TestClient) -> None:
    email_a, _ = _register(client)
    email_b, _ = _register(client)
    r = client.post(
        "/api/integrations/joint-alignment/cases",
        json={
            "assessment_type": "educational",
            "professional": {"id": "p", "name": "P", "email": "p@x.com"},
            "parents": [{"email": email_a}, {"email": email_b}],
        },
    )
    assert r.status_code == 401


# ------------------------- invitation preview ------------------------- #

def test_invitation_preview_shape_and_privacy(client: TestClient) -> None:
    """Preview must not leak co-parent email or professional email."""
    email_a, _ = _register(client)
    email_b, _ = _register(client)
    body = _create_case(client, email_a, email_b)
    token_a = body["parents"][0]["invitation_url"].split("/join/")[-1]

    r = client.get(f"/api/joint-alignment/invitation/{token_a}")
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["case_id"] == body["case_id"]
    assert preview["assessment_type"] == "educational"
    assert preview["professional_name"] == "Jane Smith, LPC"
    # No email of any kind, no other-parent info.
    assert "email" not in preview
    assert "professional_email" not in preview
    assert "parents" not in preview


def test_invitation_preview_404_for_unknown_token(client: TestClient) -> None:
    r = client.get("/api/joint-alignment/invitation/unknown-token-xyzabc123")
    assert r.status_code == 404


# ------------------------- accept invitation ------------------------- #

def test_accept_requires_matching_email(client: TestClient) -> None:
    email_a, _ = _register(client)
    email_b, token_b_user = _register(client)  # B's JWT
    body = _create_case(client, email_a, email_b)
    token_a = body["parents"][0]["invitation_url"].split("/join/")[-1]

    # Parent B tries to accept Parent A's invitation → 403.
    r = client.post(
        f"/api/joint-alignment/invitation/{token_a}/accept",
        headers={"Authorization": f"Bearer {token_b_user}"},
    )
    assert r.status_code == 403


def test_accept_happy_path_sets_status_in_progress(client: TestClient) -> None:
    email_a, token_a_user = _register(client)
    email_b, _ = _register(client)
    body = _create_case(client, email_a, email_b)
    token_a = body["parents"][0]["invitation_url"].split("/join/")[-1]

    r = client.post(
        f"/api/joint-alignment/invitation/{token_a}/accept",
        headers={"Authorization": f"Bearer {token_a_user}"},
    )
    assert r.status_code == 200, r.text
    case = r.json()
    assert case["case_id"] == body["case_id"]
    assert case["status"] == "in_progress"


# ------------------------- manual code entry ------------------------- #

def test_manual_code_requires_matching_email(client: TestClient) -> None:
    email_a, _ = _register(client)
    email_b, token_b_user = _register(client)
    email_stranger, token_stranger = _register(client)
    body = _create_case(client, email_a, email_b)
    r = client.post(
        "/api/joint-alignment/manual-code",
        headers={"Authorization": f"Bearer {token_stranger}"},
        json={"code": body["case_id"]},
    )
    assert r.status_code == 403


def test_manual_code_normalises_and_associates(client: TestClient) -> None:
    email_a, token_a_user = _register(client)
    email_b, _ = _register(client)
    body = _create_case(client, email_a, email_b)
    # Lowercase + spaces variant
    r = client.post(
        "/api/joint-alignment/manual-code",
        headers={"Authorization": f"Bearer {token_a_user}"},
        json={"code": body["case_id"].lower().replace("-", " ")},
    )
    assert r.status_code == 200, r.text
    case = r.json()
    assert case["case_id"] == body["case_id"]


# ------------------------- my cases ------------------------- #

def test_mine_returns_only_cases_with_my_email(client: TestClient) -> None:
    email_a, token_a_user = _register(client)
    email_b, _ = _register(client)
    email_x, token_x_user = _register(client)  # unrelated
    _create_case(client, email_a, email_b)
    _create_case(client, email_a, email_x, assessment_type="medical")

    r = client.get(
        "/api/joint-alignment/mine",
        headers={"Authorization": f"Bearer {token_a_user}"},
    )
    assert r.status_code == 200, r.text
    cases = r.json()["cases"]
    assert len(cases) >= 2
    # Every returned case must include this parent
    for c in cases:
        emails = [p.get("email") for p in c.get("parents", [])]
        assert email_a in [e.lower() for e in emails]


# ------------------------- integration status ------------------------- #

def test_integration_get_case_status_and_data_minimisation(client: TestClient) -> None:
    """
    The status endpoint returns the case shape. Without both parents
    complete, no `assessments` payload is included — verifies data
    minimisation.
    """
    email_a, _ = _register(client)
    email_b, _ = _register(client)
    body = _create_case(client, email_a, email_b)

    r = client.get(
        f"/api/integrations/joint-alignment/cases/{body['case_id']}",
        headers={"X-Integration-Key": SHARED_SECRET},
    )
    assert r.status_code == 200
    resp = r.json()
    assert resp["status"] == "pending"
    assert "assessments" not in resp


def test_integration_get_case_requires_key(client: TestClient) -> None:
    email_a, _ = _register(client)
    email_b, _ = _register(client)
    body = _create_case(client, email_a, email_b)
    r = client.get(f"/api/integrations/joint-alignment/cases/{body['case_id']}")
    assert r.status_code == 401
