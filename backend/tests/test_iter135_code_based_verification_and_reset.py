"""iter135 — 6-digit code flows for email verification and password reset.

Covers the four endpoints layered onto `/api/auth/`:
  - POST /auth/verify-email/send-code
  - POST /auth/verify-email/confirm-code
  - POST /auth/password-reset/request-code
  - POST /auth/password-reset/confirm-code

The link-based flows (`/verify-email/send`, `/password-reset/request`) must
continue to work — regression coverage is provided by earlier iters. This
file only exercises the new code-based surface.
"""
from __future__ import annotations

import os
import sys
import asyncio
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402
import auth as auth_mod  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def _run_async(coro):
    """Run an async coroutine from sync test code, tolerant of pytest
    fixture teardown order that may close the module-scoped event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@pytest.fixture(scope="module")
def client():
    # iter134 replaces `app.state.db` with a stripped-down fake collection
    # and doesn't restore it in its teardown. Ensure a fresh real Mongo
    # binding for this module's real HTTP round-trips.
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_ip_rate_limit():
    """Wipe TestClient-IP rate-limit rows so hitting the 5/hour cap in one
    test doesn't cascade into 429s across the rest of this module. Runs
    before every test."""
    async def _run() -> None:
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db.magic_links.delete_many({"ip": "127.0.0.1", "mode": {"$in": ["reset_code", "verify_code"]}})
            await db.magic_links.delete_many({"ip": "testclient", "mode": {"$in": ["reset_code", "verify_code"]}})
        finally:
            c.close()
    _run_async(_run())
    yield


def _register(client: TestClient, email: str, password: str = "OrigPass123!") -> None:
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "Iter135 User"},
    )
    assert r.status_code in (200, 201), r.text


def _fetch_active_code_hash(email: str, mode: str) -> str | None:
    """Read the latest active code_hash directly from Mongo (in unit tests we
    mint the plaintext ourselves via `_issue_email_code`)."""
    async def _run() -> str | None:
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            doc = await db.magic_links.find_one(
                {"email": email, "mode": mode, "used": False},
                sort=[("created_at", -1)],
            )
            return doc
        finally:
            c.close()
    return _run_async(_run())


async def _mint_code(email: str, mode: str) -> tuple[str, str]:
    """Bypass the email send and mint a plaintext code directly, returning
    (code, user_id). Uses the same helper the production endpoint uses so
    hashing / expiry logic is identical."""
    c = AsyncIOMotorClient(MONGO_URL)
    try:
        db = c[DB_NAME]
        user = await db.users.find_one({"email": email})
        assert user, f"user not found for {email}"
        code = await auth_mod._issue_email_code(
            db, mode=mode, email=email, user_id=user["user_id"], ip="127.0.0.1",
        )
        return code, user["user_id"]
    finally:
        c.close()


def _mint(email: str, mode: str) -> tuple[str, str]:
    return _run_async(_mint_code(email, mode))


# ---------------------------------------------------------------------------
# Password reset via 6-digit code
# ---------------------------------------------------------------------------

def test_password_reset_code_end_to_end(client: TestClient) -> None:
    email = f"iter135_reset_{uuid.uuid4().hex[:8]}@example.com"
    _register(client, email)

    # Request code — always 200 for privacy.
    r = client.post(
        "/api/auth/password-reset/request-code", json={"email": email},
    )
    assert r.status_code == 200

    # Mint a plaintext code we can use in tests.
    code, _uid = _mint(email, "reset_code")
    assert code.isdigit() and len(code) == 6

    # Wrong code bumps attempts and returns 400.
    r = client.post(
        "/api/auth/password-reset/confirm-code",
        json={"email": email, "code": "000000", "password": "WrongTry123!"},
    )
    assert r.status_code == 400

    # Correct code rotates password and signs the user in.
    r = client.post(
        "/api/auth/password-reset/confirm-code",
        json={"email": email, "code": code, "password": "NewSecret456!"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("access_token")
    assert body["user"]["email_verified"] is True
    assert body["user"]["email"] == email

    # Old password no longer works.
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": "OrigPass123!"},
    )
    assert r.status_code == 401

    # New password works.
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": "NewSecret456!"},
    )
    assert r.status_code == 200

    # Code is single-use.
    r = client.post(
        "/api/auth/password-reset/confirm-code",
        json={"email": email, "code": code, "password": "Another789!"},
    )
    assert r.status_code == 400


def test_password_reset_code_privacy_unknown_email(client: TestClient) -> None:
    """Requesting a reset for an email that doesn't exist must still 200."""
    r = client.post(
        "/api/auth/password-reset/request-code",
        json={"email": f"nobody_{uuid.uuid4().hex}@example.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    # Do not reveal whether the account exists.
    assert "we sent" in body["message"].lower()


def test_password_reset_code_invalidates_older_codes(client: TestClient) -> None:
    """Minting a new code must retire any previous outstanding codes."""
    email = f"iter135_replay_{uuid.uuid4().hex[:8]}@example.com"
    _register(client, email)

    old_code, _ = _mint(email, "reset_code")
    new_code, _ = _mint(email, "reset_code")
    assert old_code != new_code

    # Old code must not work any more (it was flagged used at re-mint time).
    r = client.post(
        "/api/auth/password-reset/confirm-code",
        json={"email": email, "code": old_code, "password": "AnotherPw123!"},
    )
    assert r.status_code == 400

    # New code still works.
    r = client.post(
        "/api/auth/password-reset/confirm-code",
        json={"email": email, "code": new_code, "password": "FreshPw456!"},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Email verification via 6-digit code
# ---------------------------------------------------------------------------

def test_verify_email_code_end_to_end(client: TestClient) -> None:
    email = f"iter135_verify_{uuid.uuid4().hex[:8]}@example.com"
    _register(client, email)

    r = client.post("/api/auth/verify-email/send-code", json={"email": email})
    assert r.status_code == 200

    code, uid = _mint(email, "verify_code")

    # Wrong code → 400, attempts increment.
    r = client.post(
        "/api/auth/verify-email/confirm-code",
        json={"email": email, "code": "111111"},
    )
    assert r.status_code == 400

    # Correct code marks email verified.
    r = client.post(
        "/api/auth/verify-email/confirm-code",
        json={"email": email, "code": code},
    )
    assert r.status_code == 200

    # Reflected in the users collection.
    async def _check() -> bool:
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            user = await db.users.find_one({"user_id": uid})
            return bool(user and user.get("email_verified"))
        finally:
            c.close()
    assert _run_async(_check()) is True


def test_verify_email_code_already_verified_short_circuits(client: TestClient) -> None:
    """Once the user's email is verified, request-code should say so and not
    mint another code."""
    email = f"iter135_alreadyverified_{uuid.uuid4().hex[:8]}@example.com"
    _register(client, email)

    # Flip verified directly to isolate this test.
    async def _mark() -> None:
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db.users.update_one(
                {"email": email}, {"$set": {"email_verified": True}},
            )
        finally:
            c.close()
    _run_async(_mark())

    r = client.post("/api/auth/verify-email/send-code", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body.get("already_verified") is True


# ---------------------------------------------------------------------------
# Attempt lockout
# ---------------------------------------------------------------------------

def test_reset_code_locks_out_after_max_attempts(client: TestClient) -> None:
    email = f"iter135_lockout_{uuid.uuid4().hex[:8]}@example.com"
    _register(client, email)
    code, _ = _mint(email, "reset_code")

    for _ in range(auth_mod.CODE_MAX_ATTEMPTS):
        r = client.post(
            "/api/auth/password-reset/confirm-code",
            json={"email": email, "code": "999999", "password": "BadTry123!"},
        )
        assert r.status_code == 400

    # After max attempts, even the correct code must be rejected until a
    # fresh code is requested.
    r = client.post(
        "/api/auth/password-reset/confirm-code",
        json={"email": email, "code": code, "password": "GoodTry456!"},
    )
    assert r.status_code == 400
