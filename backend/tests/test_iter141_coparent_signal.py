"""iter141 — Co-parent completion signal on /joint-alignment/mine.

Locks the extension shipped alongside the `CoparentCompletionToaster`
frontend:

  * `GET /api/joint-alignment/mine` now returns a `coparent`
    sub-object on every case row containing only the co-parent's
    display name and `completed_at` timestamp. Never any answers,
    never their email, never their user_id.
  * When the co-parent has not yet completed, `completed_at` is
    `None`.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

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


def _register(client: TestClient) -> tuple[str, str, str]:
    email = f"iter141_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"Iter141 {email[:6]}"},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    ).json()
    return email, body["access_token"], me["user_id"]


def _run(coro_factory):
    loop = asyncio.new_event_loop()
    try:
        client_ = AsyncIOMotorClient(MONGO_URL, io_loop=loop)
        try:
            return loop.run_until_complete(coro_factory(client_[DB_NAME]))
        finally:
            client_.close()
    finally:
        loop.close()


def _create_case(
    client: TestClient, email_a: str, email_b: str, assessment_type: str = "educational"
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
                {"email": email_a, "name": "Alex Parent"},
                {"email": email_b, "name": "Blake Parent"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _accept(client: TestClient, invitation_url: str, jwt: str) -> None:
    token = invitation_url.split("/join/")[-1]
    r = client.post(
        f"/api/joint-alignment/invitation/{token}/accept",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert r.status_code == 200, r.text


def _mine(client: TestClient, jwt: str) -> list:
    r = client.get(
        "/api/joint-alignment/mine", headers={"Authorization": f"Bearer {jwt}"}
    )
    assert r.status_code == 200, r.text
    return r.json()["cases"]


def test_mine_row_includes_coparent_name_but_not_email(client: TestClient) -> None:
    """The row exposes co-parent display name so the toast can say 'Blake finished...'
    but never their email or user_id."""
    email_a, jwt_a, _ = _register(client)
    email_b, _, _ = _register(client)
    case = _create_case(client, email_a, email_b)
    cases = _mine(client, jwt_a)
    row = next(c for c in cases if c["case_id"] == case["case_id"])
    assert "coparent" in row
    assert row["coparent"]["name"] == "Blake Parent"
    # No leakage of email / user_id
    assert "email" not in row["coparent"]
    assert "user_id" not in row["coparent"]
    # Not completed yet
    assert row["coparent"]["completed_at"] is None


def test_mine_row_reports_coparent_completed_at_after_completion(client: TestClient) -> None:
    email_a, jwt_a, _ = _register(client)
    email_b, jwt_b, uid_b = _register(client)
    case = _create_case(client, email_a, email_b)
    _accept(client, case["parents"][0]["invitation_url"], jwt_a)
    _accept(client, case["parents"][1]["invitation_url"], jwt_b)

    # B completes.
    _run(lambda db: mark_assessment_completed(db, uid_b, "educational"))

    cases_for_a = _mine(client, jwt_a)
    row = next(c for c in cases_for_a if c["case_id"] == case["case_id"])
    assert row["coparent"]["name"] == "Blake Parent"
    assert row["coparent"]["completed_at"] is not None
    # A hasn't completed; the row's my_status reflects that
    assert row["my_status"] in ("in_progress", "invited")
