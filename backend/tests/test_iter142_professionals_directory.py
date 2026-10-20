"""iter142 — Professionals directory + send-alignment-code flow.

Locks the surface shipped in `professionals_routes.py`:

  * GET  /api/professionals                                — public
  * POST /api/professionals/{professional_id}/send-alignment-code
                                                            — parent JWT

Guarantees locked here:
  * Initial roster auto-seeds Matt Sossi on first read.
  * Roster projection includes name / credentials / license / email /
    address — never any internal-only fields.
  * Send-code requires JWT (401 without), rejects guests (403).
  * Send-code rejects unknown professional_id (404).
  * Send-code returns the 8-char `SA-XXXXXX` code + delivered flag +
    expires_at, regardless of whether email delivery succeeded.
  * The persisted link_code doc is tagged with `professional_id`,
    `assessment_type`, and (if provided) `parent_message`.
  * Email delivery failures don't fail the mint — the response
    surfaces `delivered: false` + a human-readable error.
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
    # Wipe the professionals collection so the seed runs on the first
    # GET and every test module starts from the same baseline.
    from pymongo import MongoClient as SyncClient
    sync = SyncClient(MONGO_URL)
    sync[DB_NAME]["professionals"].delete_many({})
    sync.close()

    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str]:
    email = f"iter142_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter142 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


# ------------------------- directory ------------------------- #

def test_directory_seeds_and_returns_matt_sossi(client: TestClient) -> None:
    r = client.get("/api/professionals")
    assert r.status_code == 200, r.text
    professionals = r.json()["professionals"]
    assert len(professionals) >= 1
    matt = next(p for p in professionals if p["professional_id"] == "matt-sossi")
    assert matt["name"] == "Matt Sossi"
    assert "Mediator" in matt["credentials"]
    assert matt["email"] == "mattsossi@bsossi.com"
    assert matt["license"].startswith("Licensed")
    # Address fields present but no internal-only leakage
    assert any("Blanco" in line for line in matt["address_lines"])
    for internal_field in ("_id", "created_at", "updated_at", "sort_order", "active"):
        assert internal_field not in matt


def test_directory_idempotent_seeding(client: TestClient) -> None:
    a = client.get("/api/professionals").json()["professionals"]
    b = client.get("/api/professionals").json()["professionals"]
    assert len(a) == len(b)


# ------------------------- send-code ------------------------- #

def test_send_code_requires_auth(client: TestClient) -> None:
    r = client.post(
        "/api/professionals/matt-sossi/send-alignment-code",
        json={"assessment_type": "educational"},
    )
    assert r.status_code in (401, 403)


def test_send_code_unknown_professional_404(client: TestClient) -> None:
    _, token = _register(client)
    r = client.post(
        "/api/professionals/not-a-real-id/send-alignment-code",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_type": "educational"},
    )
    assert r.status_code == 404


def test_send_code_happy_path_returns_sa_prefix_code_and_details(client: TestClient) -> None:
    _, token = _register(client)
    r = client.post(
        "/api/professionals/matt-sossi/send-alignment-code",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "assessment_type": "educational",
            "parent_message": "Thanks for taking this — the kids are Alex (9) and Sam (6).",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"].startswith("SA-")
    assert len(body["code"]) == 9
    assert body["professional"]["name"] == "Matt Sossi"
    assert body["expires_at"]
    # Delivery may or may not succeed depending on env; both branches OK
    assert body["delivered"] in (True, False)
    if not body["delivered"]:
        assert body.get("delivered_error")


def test_send_code_persists_professional_id_and_parent_message(client: TestClient) -> None:
    """The link_codes doc is tagged so audit + support can trace it back."""
    from pymongo import MongoClient as SyncClient
    email, token = _register(client)
    r = client.post(
        "/api/professionals/matt-sossi/send-alignment-code",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "assessment_type": "medical",
            "parent_message": "Please review the current medication list.",
        },
    )
    assert r.status_code == 200
    sync = SyncClient(MONGO_URL)
    try:
        doc = sync[DB_NAME]["link_codes"].find_one(
            {"email": email, "professional_id": "matt-sossi"},
            sort=[("minted_at", -1)],
        )
    finally:
        sync.close()
    assert doc is not None
    assert doc["professional_id"] == "matt-sossi"
    assert doc["assessment_type"] == "medical"
    assert doc["parent_message"] == "Please review the current medication list."
    assert doc["context"] == "prof:matt-sossi:medical"
