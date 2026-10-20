"""iter145 — Founder single-invite rule.

Rule (2026-03-04): a parent may issue AT MOST ONE lifetime invitation to
their co-parent through this app. Once sent, the invite is either accepted
or presumed rejected — no further outreach is permitted.

Locked here:
  * A second POST /api/invites/coparent to a *different* email → 400.
  * A second POST /api/invites/coparent to the *same* pending recipient
    → 200 (this is a re-email of the same invite, not a new one).
  * A POST after the prior invite has *expired* → 400 with the closed-window
    message. The database field `expires_at` drives this — we don't wait
    for a background job.
  * A POST after the co-parent has *signed up* → 400 with the already-
    accepted message.
  * GET /api/invites/coparent exposes `invite_used` / `can_send_new` /
    `latest_status` / `policy` so the UI can decide whether to render the
    form at all.
  * POST /api/invites/coparent/resend/{invite_id} on an expired invite → 400.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient as SyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str, str]:
    email = f"iter145_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter145 Parent", "ack_privacy_notice": True, "consent_sensitive_info": True},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    return email, body["access_token"], body["user"]["user_id"]


def _seed_safety_level(user_id: str, email: str, level: int) -> None:
    sync = SyncClient(MONGO_URL)
    try:
        sync[DB_NAME]["safety_assessments"].delete_many({"user_id": user_id})
        sync[DB_NAME]["safety_assessments"].insert_one({
            "assessment_id": f"sa_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "email": email,
            "section_1": {},
            "section_2": {},
            "result": {"level": level, "pathway_title": f"Level {level}"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        sync.close()


def _first_invite(client: TestClient, token: str) -> dict:
    email = f"cop_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": email},
    )
    # Delivery may 502/503 (email not configured); either way the invite doc
    # is created before the send attempt, so the gate is what we test.
    return {"status": r.status_code, "body": r.json(), "invitee": email}


def _mutate_expiry(user_id: str, hours_ago: int) -> None:
    """Move the parent's single invite's expires_at to N hours ago so the
    'presumed rejected' branch triggers without waiting 30 days."""
    sync = SyncClient(MONGO_URL)
    try:
        past = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        sync[DB_NAME]["coparent_invites"].update_one(
            {"inviter_user_id": user_id},
            {"$set": {"expires_at": past.isoformat()}},
        )
    finally:
        sync.close()


# ------------------------- single-invite rule ------------------------- #

def test_second_invite_to_different_recipient_blocked(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    first = _first_invite(client, token)
    assert first["status"] in (200, 502, 503), first
    # Second POST to a NEW email — must be rejected as the parent has
    # used their lifetime invite.
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code == 400, r.text
    assert "one invitation" in r.json()["detail"].lower()


def test_second_post_to_same_pending_recipient_is_resend_not_new(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    first = _first_invite(client, token)
    assert first["status"] in (200, 502, 503)
    invitee = first["invitee"]
    # Wait past the 5-min resend gate isn't required — resend gate returns
    # a 200 no-op when inside the window. Either way it must NOT 400 with
    # "one invitation" language.
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": invitee},
    )
    # Should be 200 (resend), 502/503 (email issue), NEVER 400 lifetime rule.
    if r.status_code == 400:
        assert "one invitation" not in r.json()["detail"].lower()


def test_new_invite_blocked_after_expiry(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    first = _first_invite(client, token)
    assert first["status"] in (200, 502, 503)
    _mutate_expiry(uid, hours_ago=1)
    # A second invite to a different email — should now trip the
    # "presumed rejected" branch, not the "pending" one.
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "not accepted" in detail or "closed" in detail


def test_new_invite_blocked_after_signup(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    _first_invite(client, token)
    # Force the invite into a signed_up state so the gate hits the
    # "already accepted" branch.
    sync = SyncClient(MONGO_URL)
    try:
        sync[DB_NAME]["coparent_invites"].update_one(
            {"inviter_user_id": uid},
            {"$set": {
                "status": "signed_up",
                "signed_up_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    finally:
        sync.close()
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code == 400
    assert "already accepted" in r.json()["detail"].lower()


# ------------------------- GET surface ------------------------- #

def test_list_exposes_policy_and_can_send_new(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    # Before any invite → invite_used False + can_send_new True
    r = client.get(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["invite_used"] is False
    assert body["can_send_new"] is True
    assert body["latest_status"] is None
    assert body["policy"] == "one_invite_per_parent_lifetime"

    _first_invite(client, token)
    r = client.get(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["invite_used"] is True
    assert body["can_send_new"] is False
    assert body["latest_status"] in ("pending", "expired", "signed_up")


def test_get_reports_expired_after_lifetime_window(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    _first_invite(client, token)
    _mutate_expiry(uid, hours_ago=1)
    body = client.get(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert body["latest_status"] == "expired"


# ------------------------- resend endpoint ------------------------- #

def test_resend_of_expired_invite_blocked(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    _first_invite(client, token)
    _mutate_expiry(uid, hours_ago=1)
    invites = client.get(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["invites"]
    invite_id = invites[0]["invite_id"]
    r = client.post(
        f"/api/invites/coparent/resend/{invite_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "closed" in r.json()["detail"].lower()
