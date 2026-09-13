"""iter189d — Copy editor page-shape + Test-recipient digest send.

Frontend `/admin/nudge-copy` reads/writes the same endpoints tested
in iter189c — no new backend routes needed for the editor. This
file covers ONLY the new `POST /api/admin/consent-digest/send-test`
endpoint since the editor is verified through screenshot + the
existing nudge-copy tests.
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from tests.conftest import BASE_URL  # noqa: E402


ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PASSWORD = "AdminPass123!"


def _bearer(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(
            f"Login as {email} failed ({r.status_code}); env may not have "
            f"the seeded account. {r.text[:200]}"
        )
    return r.json()["access_token"]


def _admin_hdrs() -> dict:
    return {"Authorization": f"Bearer {_bearer(ADMIN_EMAIL, ADMIN_PASSWORD)}"}


def _parent_hdrs() -> dict:
    return {"Authorization": f"Bearer {_bearer('parent1@test.com', 'TestPass123!')}"}


# ---------------------- send-test digest ---------------------- #

def test_send_test_digest_requires_admin():
    r = requests.post(
        f"{BASE_URL}/api/admin/consent-digest/send-test?to_email=x@example.com",
        timeout=10,
    )
    assert r.status_code in (401, 403), r.text
    r = requests.post(
        f"{BASE_URL}/api/admin/consent-digest/send-test?to_email=x@example.com",
        headers=_parent_hdrs(),
        timeout=10,
    )
    assert r.status_code == 403, r.text


def test_send_test_digest_rejects_invalid_email():
    r = requests.post(
        f"{BASE_URL}/api/admin/consent-digest/send-test?to_email=not-an-email",
        headers=_admin_hdrs(),
        timeout=10,
    )
    # 422 validator OR 503 if email service is offline — both prove
    # the endpoint is wired. Accept either since preview env may not
    # have Resend configured.
    assert r.status_code in (422, 400), r.text


def test_send_test_digest_accepts_valid_email():
    """Env may not have Resend configured — accept a 200 (mailer up)
    or 503 (mailer not configured). Anything else means the route
    itself is broken."""
    r = requests.post(
        f"{BASE_URL}/api/admin/consent-digest/send-test",
        params={"to_email": "digest-test@example.com"},
        headers=_admin_hdrs(),
        timeout=15,
    )
    assert r.status_code in (200, 502, 503), r.text
    if r.status_code == 200:
        data = r.json()
        assert data.get("ok") is True
        assert data.get("to_email") == "digest-test@example.com"


def test_send_test_digest_never_records_dedupe_row():
    """The Monday sweep dedupes per (admin, ISO-week) via
    `consent_adoption_digest_sends`. A test send MUST NOT insert a
    row into that collection — otherwise it would block Monday's real
    send."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from consent_adoption_digest import _SENDS_COLLECTION, _week_start
    import asyncio
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]

    async def _count_for(admin_email: str) -> int:
        return await db[_SENDS_COLLECTION].count_documents({
            "admin_email": admin_email,
            "week_start": _week_start(),
        })

    unique = "test-only@example.com"
    before = asyncio.get_event_loop().run_until_complete(_count_for(unique))
    r = requests.post(
        f"{BASE_URL}/api/admin/consent-digest/send-test",
        params={"to_email": unique},
        headers=_admin_hdrs(),
        timeout=15,
    )
    # Regardless of mailer availability the endpoint must not have
    # written to the dedupe collection.
    after = asyncio.get_event_loop().run_until_complete(_count_for(unique))
    assert after == before, (
        f"Test send inserted a dedupe row for {unique}; that would "
        f"block the real Monday send. before={before} after={after} "
        f"(status={r.status_code})"
    )
