"""End-to-end tests for the co-parent invite flow."""
import asyncio
import os
import sys
import uuid

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _fetch_invite_token(invite_id: str) -> str:
    """Look up the raw token for a given invite_id (in real life this lives in
    the email body — but for tests we read it straight out of Mongo)."""

    async def run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            doc = await client[DB_NAME].coparent_invites.find_one(
                {"invite_id": invite_id}, {"_id": 0, "token": 1}
            )
            return doc["token"]
        finally:
            client.close()

    return asyncio.run(run())


def _purge(emails):
    async def run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            await client[DB_NAME].coparent_invites.delete_many({
                "$or": [
                    {"invitee_email": {"$in": emails}},
                    {"inviter_email": {"$in": emails}},
                ]
            })
            await client[DB_NAME].users.delete_many({"email": {"$in": emails}})
        finally:
            client.close()

    asyncio.run(run())


import pytest


@pytest.fixture
def cleanup_invites():
    test_emails = []

    def track(email):
        test_emails.append(email)
        return email

    yield track
    if test_emails:
        _purge(test_emails)


def _make_inviter(api_client, base_url):
    """Create a fresh signed-in account for the test."""
    email = f"inv_{uuid.uuid4().hex[:10]}@example.com"
    r = api_client.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "name": "Inviter", "password": "TestPass123!"},
    )
    assert r.status_code in (200, 201), r.text
    user_id = r.json()["user"]["user_id"]
    _seed_passing_safety_screen(user_id, email)
    return email, r.json()["access_token"]


def _seed_passing_safety_screen(user_id: str, email: str) -> None:
    """Founder rule (2026-03-04): a parent must have a passing IPV screen
    (Level 3 or 4) before sending co-parent invites. Legacy tests here
    assumed the older un-gated behaviour, so we seed a Level 4 assessment
    directly so they exercise the invite flow, not the gate."""
    from datetime import datetime, timezone
    from pymongo import MongoClient as SyncClient
    sync = SyncClient(MONGO_URL)
    try:
        sync[DB_NAME]["safety_assessments"].delete_many({"user_id": user_id})
        sync[DB_NAME]["safety_assessments"].insert_one({
            "assessment_id": f"sa_test_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "email": email,
            "section_1": {},
            "section_2": {},
            "result": {"level": 4, "pathway_title": "Level 4"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        sync.close()


def test_invite_requires_auth(base_url, api_client):
    r = api_client.post(
        f"{base_url}/api/invites/coparent",
        json={"email": "anybody@example.com"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401


def test_full_invite_and_accept_cycle(base_url, api_client, cleanup_invites):
    inviter_email, token = _make_inviter(api_client, base_url)
    cleanup_invites(inviter_email)
    auth = {"Authorization": f"Bearer {token}"}

    # Resend only accepts its own test inbox from the preview.
    target_email = cleanup_invites(f"delivered+cop{uuid.uuid4().hex[:10]}@resend.dev")

    # Send invite
    r = api_client.post(
        f"{base_url}/api/invites/coparent",
        json={"email": target_email},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["resent"] is False
    invite_id = body["invite"]["invite_id"]

    # List invites
    r = api_client.get(f"{base_url}/api/invites/coparent", headers=auth)
    assert r.status_code == 200
    invites = r.json()["invites"]
    assert any(i["invitee_email"] == target_email for i in invites)

    # Sending same email again returns success but doesn't create a new doc
    r = api_client.post(
        f"{base_url}/api/invites/coparent",
        json={"email": target_email},
        headers=auth,
    )
    assert r.status_code == 200

    # Public token endpoint — first call marks opened
    invite_token = _fetch_invite_token(invite_id)

    r = api_client.get(f"{base_url}/api/invites/coparent/by-token/{invite_token}")
    assert r.status_code == 200
    public = r.json()
    assert public["invitee_email"] == target_email
    assert public["inviter_name"] == "Inviter"
    assert public["already_accepted"] is False

    # Accept the invite — creates the co-parent account
    r = api_client.post(
        f"{base_url}/api/invites/coparent/accept/{invite_token}",
        json={"name": "Coparent", "password": "Coparent123!"},
    )
    assert r.status_code == 200, r.text
    new_user = r.json()["user"]
    assert new_user["email"] == target_email
    assert new_user["email_verified"] is True

    # Accepting again returns 409
    r = api_client.post(
        f"{base_url}/api/invites/coparent/accept/{invite_token}",
        json={"name": "Coparent2", "password": "Different123!"},
    )
    assert r.status_code == 409


def test_cannot_invite_self(base_url, api_client, cleanup_invites):
    inviter_email, token = _make_inviter(api_client, base_url)
    cleanup_invites(inviter_email)
    auth = {"Authorization": f"Bearer {token}"}

    r = api_client.post(
        f"{base_url}/api/invites/coparent",
        json={"email": inviter_email},
        headers=auth,
    )
    assert r.status_code == 400
    assert "own email" in r.json()["detail"].lower()


def test_invalid_token_returns_404(base_url, api_client):
    r = api_client.get(f"{base_url}/api/invites/coparent/by-token/not-a-real-token")
    assert r.status_code == 404
