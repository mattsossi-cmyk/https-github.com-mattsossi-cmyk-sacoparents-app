"""iter136 — Contract test for endpoints the JointAlignmentPromoCard depends on.

The promo card renders `waiting` vs `ready` based on:
  - GET /api/snc2/compare/dashboard/highlights  (drives `ready`)
  - GET /api/invites/coparent                   (drives `alreadyInvited`)

If either endpoint breaks or its response shape changes, the card would
silently degrade. This test locks the surface.
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
    from server import app as _app
    # iter134 may have replaced state.db with a fake; restore a real binding.
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


def _new_user_token(client: TestClient) -> str:
    email = f"iter136_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter136 User"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["access_token"]


def test_promo_card_snc_highlights_shape(client: TestClient) -> None:
    """GET /snc2/compare/dashboard/highlights — schema the promo card reads.

    A fresh account with no Compare share must return a shape whose `ready`
    flag is falsy, so the card falls through to the "waiting" state.
    """
    token = _new_user_token(client)
    r = client.get(
        "/api/snc2/compare/dashboard/highlights",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # `ready` must exist (bool or falsy) — the card branches on this.
    assert "ready" in body
    assert not body["ready"], "fresh account should NOT show ready state"


def test_promo_card_invites_list_shape(client: TestClient) -> None:
    """GET /invites/coparent — shape the promo card reads to gate its
    'invite already sent' UI. Must return an `invites` array."""
    token = _new_user_token(client)
    r = client.get(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "invites" in body
    assert isinstance(body["invites"], list)
    # Fresh account has no invites → card renders the email input.
    assert body["invites"] == []


def test_promo_card_invite_flow_transitions_state(client: TestClient) -> None:
    """After an invite exists in the DB, the /invites/coparent list must
    include an entry whose status is 'pending' — the card uses this to flip
    to its 'invite already sent' subview.

    We seed the invite directly (rather than POSTing) because Resend rejects
    ``example.com`` addresses in the sandbox, and this test targets the
    read-shape the promo card consumes."""
    import asyncio
    from datetime import datetime, timezone

    token = _new_user_token(client)
    # Grab the user_id we just created so we can seed a matching invite row.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    async def _seed() -> None:
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db.coparent_invites.insert_one({
                "invite_id": f"inv_{uuid.uuid4().hex[:10]}",
                "inviter_user_id": user_id,
                "email": f"iter136_invitee_{uuid.uuid4().hex[:6]}@example.com",
                "status": "pending",
                "token": uuid.uuid4().hex,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            c.close()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_seed())

    r = client.get(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    invites = r.json()["invites"]
    assert len(invites) >= 1
    statuses = {inv.get("status") for inv in invites}
    assert statuses & {"pending", "opened", "signed_up"}, statuses
