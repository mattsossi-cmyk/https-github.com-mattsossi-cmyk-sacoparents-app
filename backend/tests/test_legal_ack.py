"""Tests for the server-side legal-acknowledgment audit trail."""
import asyncio
import os
import sys
import uuid

import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _purge(user_id: str):
    async def run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            await client[DB_NAME].legal_acknowledgments.delete_many({"user_id": user_id})
            await client[DB_NAME].users.delete_many({"user_id": user_id})
        finally:
            client.close()

    asyncio.run(run())


def _fetch_user_id(api_client, base_url, token: str) -> str:
    r = api_client.get(
        f"{base_url}/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


def _make_user(api_client, base_url):
    email = f"legal_{uuid.uuid4().hex[:10]}@example.com"
    r = api_client.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "name": "Legal Test", "password": "TestPass123!"},
    )
    assert r.status_code in (200, 201), r.text
    token = r.json()["access_token"]
    uid = _fetch_user_id(api_client, base_url, token)
    return email, token, uid


@pytest.fixture
def cleanup():
    uids = []

    def track(uid):
        uids.append(uid)
        return uid

    yield track
    for uid in uids:
        _purge(uid)


def test_ack_requires_auth(base_url, api_client):
    r = api_client.post(
        f"{base_url}/api/legal/acknowledge",
        json={"version": "v1"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401


def test_ack_records_row_with_metadata(base_url, api_client, cleanup):
    _, token, uid = _make_user(api_client, base_url)
    cleanup(uid)
    r = api_client.post(
        f"{base_url}/api/legal/acknowledge",
        json={"version": "v1"},
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "pytest-legal-suite/1.0",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["version"] == "v1"

    client = AsyncIOMotorClient(MONGO_URL)
    try:
        async def _get():
            return await client[DB_NAME].legal_acknowledgments.find_one(
                {"user_id": uid, "version": "v1"}, {"_id": 0}
            )
        doc = asyncio.run(_get())
    finally:
        client.close()
    assert doc is not None
    assert doc["user_id"] == uid
    assert doc["version"] == "v1"
    assert doc["acknowledged_at"]
    assert "pytest-legal-suite" in (doc.get("user_agent") or "")


def test_ack_is_idempotent_upsert(base_url, api_client, cleanup):
    _, token, uid = _make_user(api_client, base_url)
    cleanup(uid)
    headers = {"Authorization": f"Bearer {token}"}

    api_client.post(
        f"{base_url}/api/legal/acknowledge", json={"version": "v1"}, headers=headers
    )
    api_client.post(
        f"{base_url}/api/legal/acknowledge", json={"version": "v1"}, headers=headers
    )

    client = AsyncIOMotorClient(MONGO_URL)
    try:
        async def _count():
            return await client[DB_NAME].legal_acknowledgments.count_documents(
                {"user_id": uid}
            )
        n = asyncio.run(_count())
    finally:
        client.close()
    assert n == 1, "Re-acking the same version must upsert, not duplicate"


def test_admin_endpoints_require_admin(base_url, api_client, cleanup):
    _, token, uid = _make_user(api_client, base_url)
    cleanup(uid)
    r = api_client.get(
        f"{base_url}/api/legal/admin/acks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
