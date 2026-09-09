"""Iteration 180 — Report delivery status tracking.

Covers:
  * GET /api/report-deliveries returns null-slots for a fresh user
  * The endpoint requires auth
  * `record_email_delivery` unit test — happy path + noop paths
    (empty user_id, unknown report_type)
  * Direct DB assertion after `record_email_delivery` writes
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from typing import Tuple

import requests
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

# Load backend env vars so imports of `report_deliveries` (→ auth)
# see JWT_SECRET etc. before falling over.
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from tests.conftest import BASE_URL  # noqa: E402

MONGO_URL = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME") or "test_database"


def _headers(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _register(prefix: str) -> Tuple[str, str, str]:
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"P {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"], r.json()["user"]["user_id"]


# ---------------------------------------------------------------------
# GET endpoint contract
# ---------------------------------------------------------------------

def test_deliveries_requires_auth():
    r = requests.get(f"{BASE_URL}/api/report-deliveries", timeout=30)
    assert r.status_code == 401


def test_deliveries_null_slots_for_fresh_user():
    _e, tok, _uid = _register("del-fresh")
    r = requests.get(
        f"{BASE_URL}/api/report-deliveries",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    body = r.json()
    for rt in (
        "foundation_statement", "snc_report",
        "edu_deep", "med_deep", "psych_deep",
    ):
        assert rt in body
        assert body[rt] is None


# ---------------------------------------------------------------------
# record_email_delivery unit tests
# ---------------------------------------------------------------------

def test_record_email_delivery_writes_iso_timestamp():
    """After a direct call to `record_email_delivery`, a subsequent
    GET /report-deliveries returns a valid ISO timestamp + email."""
    email, tok, uid = _register("del-write")

    async def _write():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        from report_deliveries import record_email_delivery
        await record_email_delivery(
            db,
            user_id=uid,
            report_type="foundation_statement",
            to_email=email,
        )
        client.close()

    asyncio.new_event_loop().run_until_complete(_write())

    r = requests.get(
        f"{BASE_URL}/api/report-deliveries",
        headers=_headers(tok), timeout=30,
    )
    body = r.json()
    slot = body["foundation_statement"]
    assert slot is not None
    assert slot["last_sent_at"] is not None
    assert "T" in slot["last_sent_at"]
    assert slot["last_sent_to"] == email.lower()


def test_record_email_delivery_bumps_timestamp_on_second_write():
    """A second write updates the timestamp — parents tapping Send
    again should see the badge move forward, not stay frozen."""
    email, tok, uid = _register("del-bump")

    async def _write_twice():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        from report_deliveries import record_email_delivery
        await record_email_delivery(
            db, user_id=uid,
            report_type="snc_report", to_email=email,
        )
        first_row = await db["report_deliveries"].find_one(
            {"user_id": uid, "report_type": "snc_report"},
        )
        # Ensure the wall-clock advances by at least 1ms.
        import asyncio as _a
        await _a.sleep(0.05)
        await record_email_delivery(
            db, user_id=uid,
            report_type="snc_report", to_email=email,
        )
        second_row = await db["report_deliveries"].find_one(
            {"user_id": uid, "report_type": "snc_report"},
        )
        client.close()
        return first_row, second_row

    first, second = asyncio.new_event_loop().run_until_complete(_write_twice())
    assert second["last_sent_at"] > first["last_sent_at"]


def test_record_email_delivery_ignores_unknown_report_type():
    _e, _tok, uid = _register("del-badtype")

    async def _write():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        from report_deliveries import record_email_delivery
        await record_email_delivery(
            db, user_id=uid,
            report_type="not_a_real_report",
            to_email="x@y.com",
        )
        # Ensure NO row was created.
        row = await db["report_deliveries"].find_one({"user_id": uid})
        client.close()
        return row

    row = asyncio.new_event_loop().run_until_complete(_write())
    assert row is None


def test_record_email_delivery_ignores_empty_email():
    _e, _tok, uid = _register("del-noemail")

    async def _write():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        from report_deliveries import record_email_delivery
        await record_email_delivery(
            db, user_id=uid,
            report_type="snc_report",
            to_email="",
        )
        row = await db["report_deliveries"].find_one({"user_id": uid})
        client.close()
        return row

    row = asyncio.new_event_loop().run_until_complete(_write())
    assert row is None


# ---------------------------------------------------------------------
# End-to-end via an actual email endpoint — the SNC report path
# reaches record_email_delivery only on a 200 send, and Resend
# may or may not be configured on the preview env. We assert the
# endpoint at least responds; if Resend is configured we ALSO
# check the delivery row landed.
# ---------------------------------------------------------------------

def test_foundation_email_records_delivery_when_send_succeeds():
    email, tok, uid = _register("del-e2e")
    # Seed a Foundation Statement so the endpoint doesn't 409.
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={
            "child_lens": "A", "own_part": "B",
            "best_outcome": "C", "coparent_feedback": "D",
        },
        headers=_headers(tok), timeout=30,
    )
    r = requests.post(
        f"{BASE_URL}/api/mediation/foundation-statement/email-me",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code in (200, 502, 503)
    if r.status_code == 200:
        gr = requests.get(
            f"{BASE_URL}/api/report-deliveries",
            headers=_headers(tok), timeout=30,
        )
        slot = gr.json()["foundation_statement"]
        assert slot is not None
        assert slot["last_sent_to"] == email.lower()
