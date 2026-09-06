"""iter143 — Admin professionals editor.

Locks the admin-only surface added to `professionals_routes.py`:

  * GET   /api/admin/professionals            — admin JWT
  * POST  /api/admin/professionals            — admin JWT
  * PATCH /api/admin/professionals/{id}       — admin JWT

Guarantees:
  * Non-admin users are refused (403).
  * The initial roster is visible to admins via the admin listing.
  * `POST /admin/professionals` inserts a new row + slugifies the
    professional_id from the name.
  * `PATCH` supports partial updates including the deactivation
    toggle (`{"active": false}`). Deactivated rows disappear from
    the public GET but remain visible to the admin.
  * The public GET (`/api/professionals`) auto-refreshes the
    canonical initial-roster fields on read — e.g. an updated
    zip in `_INITIAL_ROSTER` propagates without a manual DB touch.
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
import analytics_routes  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# The admin email needs to be resolvable — either as one of the seeded
# ADMIN_EMAILS from analytics_routes, or as one we inject for the test.
# We create the test user with an ADMIN_EMAILS-eligible address.
ADMIN_EMAIL = "iter143_admin@example.com"


@pytest.fixture(scope="module")
def client():
    from pymongo import MongoClient as SyncClient
    sync = SyncClient(MONGO_URL)
    sync[DB_NAME]["professionals"].delete_many({})
    sync.close()

    # Grant admin rights to our test user in-process.
    analytics_routes.ADMIN_EMAILS.add(ADMIN_EMAIL.lower())

    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c

    analytics_routes.ADMIN_EMAILS.discard(ADMIN_EMAIL.lower())


def _register(client: TestClient, email: str | None = None) -> tuple[str, str]:
    email = email or f"iter143_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter143"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


# ------------------------- admin listing ------------------------- #

def test_admin_list_forbids_non_admins(client: TestClient) -> None:
    _, token = _register(client)
    r = client.get(
        "/api/admin/professionals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_admin_list_returns_active_flag_and_sort_order(client: TestClient) -> None:
    # Fresh admin email — module-level ADMIN_EMAIL was already used
    # by the initial fixture registration in earlier test runs.
    admin_email = f"iter143_admin_{uuid.uuid4().hex[:6]}@example.com"
    import analytics_routes as _ar
    _ar.ADMIN_EMAILS.add(admin_email.lower())
    try:
        _, admin_token = _register(client, admin_email)
        r = client.get(
            "/api/admin/professionals",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        professionals = r.json()["professionals"]
        matt = next(p for p in professionals if p["professional_id"] == "matt-sossi")
        assert "active" in matt
        assert matt["active"] is True
        assert "sort_order" in matt
    finally:
        _ar.ADMIN_EMAILS.discard(admin_email.lower())


# ------------------------- admin create ------------------------- #

def test_admin_create_slugifies_id(client: TestClient) -> None:
    _, admin_token = _register(client, f"iter143_{uuid.uuid4().hex[:6]}@example.com")
    # Grant this ad-hoc admin
    email = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    ).json()["email"]
    analytics_routes.ADMIN_EMAILS.add(email.lower())
    try:
        r = client.post(
            "/api/admin/professionals",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Jane R. Smith LPC",
                "credentials": "Family Therapist",
                "email": "jane.smith@example.com",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["professional_id"] == "jane-r-smith-lpc"
        assert body["name"] == "Jane R. Smith LPC"
        assert body["active"] is True
    finally:
        analytics_routes.ADMIN_EMAILS.discard(email.lower())


def test_admin_patch_deactivates_professional(client: TestClient) -> None:
    _, admin_token = _register(client, f"iter143_{uuid.uuid4().hex[:6]}@example.com")
    email = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    ).json()["email"]
    analytics_routes.ADMIN_EMAILS.add(email.lower())
    try:
        # Create
        r = client.post(
            "/api/admin/professionals",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Deactivate Me LPC",
                "credentials": "Test",
                "email": "deactivate@example.com",
            },
        )
        assert r.status_code == 200
        pid = r.json()["professional_id"]

        # Public directory sees it
        pub = client.get("/api/professionals").json()["professionals"]
        assert any(p["professional_id"] == pid for p in pub)

        # Deactivate via PATCH
        r2 = client.patch(
            f"/api/admin/professionals/{pid}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"active": False},
        )
        assert r2.status_code == 200
        assert r2.json()["active"] is False

        # Now hidden from the public directory
        pub2 = client.get("/api/professionals").json()["professionals"]
        assert not any(p["professional_id"] == pid for p in pub2)

        # But still visible to admin
        adm = client.get(
            "/api/admin/professionals",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()["professionals"]
        assert any(p["professional_id"] == pid and p["active"] is False for p in adm)
    finally:
        analytics_routes.ADMIN_EMAILS.discard(email.lower())


def test_admin_patch_404_for_unknown_id(client: TestClient) -> None:
    _, admin_token = _register(client, f"iter143_{uuid.uuid4().hex[:6]}@example.com")
    email = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    ).json()["email"]
    analytics_routes.ADMIN_EMAILS.add(email.lower())
    try:
        r = client.patch(
            "/api/admin/professionals/not-a-real-id",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"active": False},
        )
        assert r.status_code == 404
    finally:
        analytics_routes.ADMIN_EMAILS.discard(email.lower())


def test_admin_create_forbids_non_admins(client: TestClient) -> None:
    _, token = _register(client)
    r = client.post(
        "/api/admin/professionals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "X",
            "credentials": "Y",
            "email": "hacker@example.com",
        },
    )
    assert r.status_code == 403


# ------------------------- seed refresh ------------------------- #

def test_public_read_refreshes_canonical_seed_fields(client: TestClient) -> None:
    """
    Simulate a stale DB (old zip in address) and ensure the public
    GET refreshes the address_lines back to the canonical value from
    _INITIAL_ROSTER.
    """
    from pymongo import MongoClient as SyncClient
    sync = SyncClient(MONGO_URL)
    try:
        # Set a wrong zip in the DB
        sync[DB_NAME]["professionals"].update_one(
            {"professional_id": "matt-sossi"},
            {"$set": {"address_lines": ["16607 Blanco #703", "San Antonio, Texas 00000"]}},
        )
        # Now hit the public endpoint — seeder should refresh the value
        r = client.get("/api/professionals")
        matt = next(
            p for p in r.json()["professionals"] if p["professional_id"] == "matt-sossi"
        )
        assert any("78232" in line for line in matt["address_lines"])
    finally:
        sync.close()
