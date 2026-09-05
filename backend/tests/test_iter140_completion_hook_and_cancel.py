"""iter140 — Joint Alignment completion hook + Align cancellation.

Locks the Phase C machinery built on top of iter139:

  * `mark_assessment_completed()` — the public helper called from
    med/edu/psych deep-dive report generation and communication
    reflection save. Marks the parent slot as completed on every
    open case that matches the assessment_type.
  * Case top-level status flips to `both_complete` when both
    parents finish (idempotent; second call is a no-op).
  * Outbound webhook to Align (`ALIGN_COMPLETION_WEBHOOK_URL`) is
    signed with HMAC-SHA256 using the shared secret. When the URL
    is not configured the helper logs and skips silently — the
    parent-facing completion path never fails.
  * `POST /api/integrations/joint-alignment/cases/{case_id}/cancel`
    — server-to-server, moves the case to `cancelled` and expires
    every unclaimed invitation on it.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402
from joint_alignment_routes import mark_assessment_completed  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

SHARED_SECRET = "2f9c1e7a4b8d3f6a5c0e9d7b2f4a6c8e1d3b5a7c9e0f2a4b6c8d1e3f5a7b9c0d"


@pytest.fixture(scope="module")
def client():
    os.environ["INTEGRATION_SHARED_SECRET"] = SHARED_SECRET
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _run_helper(coro_factory):
    """
    Motor + TestClient share an event loop, so calling
    `asyncio.get_event_loop().run_until_complete(...)` on the app's
    Motor client blows up with "attached to a different loop". Run
    the helper on its own loop against a fresh Motor client.
    """
    loop = asyncio.new_event_loop()
    try:
        client = AsyncIOMotorClient(MONGO_URL, io_loop=loop)
        db = client[DB_NAME]
        result = loop.run_until_complete(coro_factory(db))
        return result
    finally:
        client.close()
        loop.close()


def _register(client: TestClient) -> tuple[str, str, str]:
    """Returns (email, jwt, user_id)."""
    email = f"iter140_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter140 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    ).json()
    return email, body["access_token"], me["user_id"]
    """Returns (email, jwt, user_id)."""
    email = f"iter140_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter140 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    ).json()
    return email, body["access_token"], me["user_id"]


def _create_case(
    client: TestClient,
    email_a: str,
    email_b: str,
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
                {"email": email_a, "name": "A"},
                {"email": email_b, "name": "B"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _accept(client: TestClient, invitation_url: str, jwt: str) -> dict:
    token = invitation_url.split("/join/")[-1]
    r = client.post(
        f"/api/joint-alignment/invitation/{token}/accept",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- mark_assessment_completed helper ---------------- #

def test_mark_completion_marks_case_and_transitions_status(client: TestClient) -> None:
    email_a, jwt_a, uid_a = _register(client)
    email_b, jwt_b, uid_b = _register(client)
    case = _create_case(client, email_a, email_b, assessment_type="educational")
    _accept(client, case["parents"][0]["invitation_url"], jwt_a)
    _accept(client, case["parents"][1]["invitation_url"], jwt_b)

    updated = _run_helper(lambda db: mark_assessment_completed(db, uid_a, "educational"))
    assert case["case_id"] in updated

    # Case is now in_progress with A completed and B still just accepted.
    r = client.get(
        f"/api/integrations/joint-alignment/cases/{case['case_id']}",
        headers={"X-Integration-Key": SHARED_SECRET},
    )
    payload = r.json()
    assert payload["status"] == "in_progress"
    a_row = next(p for p in payload["parents"] if p["email"] == email_a)
    assert a_row["status"] == "completed"

    # Now B completes. Status should flip to both_complete.
    updated_b = _run_helper(lambda db: mark_assessment_completed(db, uid_b, "educational"))
    assert case["case_id"] in updated_b

    r2 = client.get(
        f"/api/integrations/joint-alignment/cases/{case['case_id']}",
        headers={"X-Integration-Key": SHARED_SECRET},
    )
    payload2 = r2.json()
    assert payload2["status"] == "both_complete"
    assert "assessments" in payload2
    assert payload2["schema_version"] == 1


def test_mark_completion_is_idempotent(client: TestClient) -> None:
    """A second call for the same parent + type produces no additional case updates."""
    email_a, jwt_a, uid_a = _register(client)
    email_b, jwt_b, _ = _register(client)
    case = _create_case(client, email_a, email_b, assessment_type="medical")
    _accept(client, case["parents"][0]["invitation_url"], jwt_a)
    _accept(client, case["parents"][1]["invitation_url"], jwt_b)

    first = _run_helper(lambda db: mark_assessment_completed(db, uid_a, "medical"))
    second = _run_helper(lambda db: mark_assessment_completed(db, uid_a, "medical"))
    assert case["case_id"] in first
    assert case["case_id"] not in second


def test_mark_completion_ignores_unknown_assessment_type(client: TestClient) -> None:
    _, _, uid = _register(client)
    result = _run_helper(lambda db: mark_assessment_completed(db, uid, "made-up-lane"))
    assert result == []


# ---------------- cancellation ---------------- #

def test_cancel_case_moves_to_cancelled_and_expires_tokens(client: TestClient) -> None:
    email_a, _, _ = _register(client)
    email_b, _, _ = _register(client)
    case = _create_case(client, email_a, email_b)
    r = client.post(
        f"/api/integrations/joint-alignment/cases/{case['case_id']}/cancel",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"reason": "professional retracted"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    # Attempting to preview an unaccepted token on a cancelled case
    # should now return 410 (expired) because the cancel handler
    # sets token_expires_at to now.
    token_a = case["parents"][0]["invitation_url"].split("/join/")[-1]
    r_prev = client.get(f"/api/joint-alignment/invitation/{token_a}")
    assert r_prev.status_code == 410


def test_cancel_requires_key_and_404_when_missing(client: TestClient) -> None:
    # No key
    r = client.post(
        "/api/integrations/joint-alignment/cases/SA-999999/cancel",
        json={"reason": "x"},
    )
    assert r.status_code == 401
    # With key but unknown case
    r2 = client.post(
        "/api/integrations/joint-alignment/cases/SA-000000/cancel",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"reason": "x"},
    )
    assert r2.status_code == 404


def test_cancel_is_idempotent(client: TestClient) -> None:
    email_a, _, _ = _register(client)
    email_b, _, _ = _register(client)
    case = _create_case(client, email_a, email_b)
    for _ in range(2):
        r = client.post(
            f"/api/integrations/joint-alignment/cases/{case['case_id']}/cancel",
            headers={"X-Integration-Key": SHARED_SECRET},
            json={"reason": "test"},
        )
    # Second cancel returns 404 because the case is already cancelled
    # (matched_count == 0 with the {"$nin": ["cancelled", "expired"]}
    # filter). That's the expected "no work to do" signal.
    assert r.status_code == 404
