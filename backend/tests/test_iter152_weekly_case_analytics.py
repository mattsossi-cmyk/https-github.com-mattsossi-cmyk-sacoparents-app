"""iter152 — Weekly Case Analytics Monday digest.

Locks the behaviour of the `weekly_case_analytics_email` module:
Monday-only send window, per-week dedupe, real-email guard,
"no cases" short-circuit, dry-run stat computation.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from weekly_case_analytics_email import (  # noqa: E402
    _CASES_COLLECTION,
    _SENDS_COLLECTION,
    _USERS_COLLECTION,
    _in_send_window,
    _week_start,
    send_weekly_case_analytics,
)


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="function")
def db():
    yield AsyncIOMotorClient(MONGO_URL)[DB_NAME]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _cleanup_user(db, user_id: str):
    await db[_CASES_COLLECTION].delete_many({"professional_created_by": user_id})
    await db[_SENDS_COLLECTION].delete_many({"user_id": user_id})
    await db[_USERS_COLLECTION].delete_many({"user_id": user_id})


def _seed_user(user_id: str, email: str, name: str) -> dict:
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "created_at": _now(),
    }


def _seed_case(user_id: str, professional_email: str, professional_name: str, minted_at) -> dict:
    return {
        "case_id": f"SA-{uuid.uuid4().hex[:6].upper()}",
        "origin": "in_app_professional",
        "assessment_type": "co-parenting",
        "professional": {"id": user_id, "name": professional_name, "email": professional_email},
        "professional_created_by": user_id,
        "parents": [
            {"parent_slot": "A", "email": "a@example.com", "name": "Alex",
             "invitation_token": "tok_a", "token_expires_at": minted_at + timedelta(days=7),
             "accepted_at": None},
            {"parent_slot": "B", "email": "b@example.com", "name": "Bailey",
             "invitation_token": "tok_b", "token_expires_at": minted_at + timedelta(days=7),
             "accepted_at": None},
        ],
        "status": "pending",
        "created_at": minted_at,
    }


# --- pure helpers ----

def test_in_send_window_only_monday_morning():
    """Send window is Monday 09-11 UTC only."""
    # Monday 2026-03-02 10:00 UTC
    monday_am = datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc)
    assert _in_send_window(monday_am) is True
    # Same day, 15:00 UTC (afternoon) — outside window
    monday_pm = datetime(2026, 3, 2, 15, 0, tzinfo=timezone.utc)
    assert _in_send_window(monday_pm) is False
    # Tuesday 10:00 UTC — wrong day
    tue = datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc)
    assert _in_send_window(tue) is False


def test_week_start_returns_monday_iso():
    """Any day of a given week rolls back to Monday."""
    wed = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)  # Wednesday
    assert _week_start(wed) == "2026-03-02"  # Monday of that week


# --- sweep pipeline (dry_run + force_window) ----

def test_dispatches_dry_run_when_user_has_cases(db):
    async def run():
        user_id = f"prof-{uuid.uuid4().hex[:8]}"
        email = f"pro_{uuid.uuid4().hex[:6]}@example.com"
        await db[_USERS_COLLECTION].insert_one(_seed_user(user_id, email, "Pat Mediator"))
        await db[_CASES_COLLECTION].insert_one(
            _seed_case(user_id, email, "Pat Mediator", minted_at=_now() - timedelta(days=2))
        )
        try:
            r = await send_weekly_case_analytics(db, dry_run=True, force_window=True)
            ours = [x for x in r["results"] if x["user_id"] == user_id]
            assert len(ours) == 1
            assert ours[0]["sent"] is True
            assert ours[0].get("dry_run") is True
            stats = ours[0]["stats"]
            assert stats["total_cases"] == 1
            assert stats["active_cases"] == 1
            assert stats["new_this_week"] == 1
            # dedupe row written
            n = await db[_SENDS_COLLECTION].count_documents({"user_id": user_id})
            assert n == 1
        finally:
            await _cleanup_user(db, user_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_dedupe_prevents_second_send_same_week(db):
    async def run():
        user_id = f"prof-{uuid.uuid4().hex[:8]}"
        email = f"pro_{uuid.uuid4().hex[:6]}@example.com"
        await db[_USERS_COLLECTION].insert_one(_seed_user(user_id, email, "Pat"))
        await db[_CASES_COLLECTION].insert_one(
            _seed_case(user_id, email, "Pat", minted_at=_now() - timedelta(days=2))
        )
        try:
            r1 = await send_weekly_case_analytics(db, dry_run=True, force_window=True)
            r2 = await send_weekly_case_analytics(db, dry_run=True, force_window=True)
            ours2 = [x for x in r2["results"] if x["user_id"] == user_id]
            assert len(ours2) == 1
            assert ours2[0]["sent"] is False
            assert ours2[0]["reason"] == "already_sent_this_week"
        finally:
            await _cleanup_user(db, user_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_professionals_with_zero_cases(db):
    async def run():
        # No candidates → sweep returns zero results for our seeded user
        user_id = f"prof-{uuid.uuid4().hex[:8]}"
        try:
            r = await send_weekly_case_analytics(db, dry_run=True, force_window=True)
            ours = [x for x in r["results"] if x["user_id"] == user_id]
            assert ours == []
        finally:
            await _cleanup_user(db, user_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_when_outside_send_window(db):
    async def run():
        user_id = f"prof-{uuid.uuid4().hex[:8]}"
        email = f"pro_{uuid.uuid4().hex[:6]}@example.com"
        await db[_USERS_COLLECTION].insert_one(_seed_user(user_id, email, "Pat"))
        await db[_CASES_COLLECTION].insert_one(
            _seed_case(user_id, email, "Pat", minted_at=_now() - timedelta(days=2))
        )
        try:
            # Force a Tuesday timestamp — outside window
            tuesday = datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc)
            r = await send_weekly_case_analytics(
                db, dry_run=True, now=tuesday, force_window=False,
            )
            assert r["skipped"] == "outside_send_window"
            assert r["results"] == []
        finally:
            await _cleanup_user(db, user_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_demo_emails(db):
    async def run():
        user_id = f"prof-{uuid.uuid4().hex[:8]}"
        demo_email = "pro@demo.local"
        await db[_USERS_COLLECTION].insert_one(_seed_user(user_id, demo_email, "Demo"))
        await db[_CASES_COLLECTION].insert_one(
            _seed_case(user_id, demo_email, "Demo", minted_at=_now() - timedelta(days=2))
        )
        try:
            r = await send_weekly_case_analytics(db, dry_run=True, force_window=True)
            ours = [x for x in r["results"] if x["user_id"] == user_id]
            assert len(ours) == 1
            assert ours[0]["sent"] is False
            assert ours[0]["reason"] == "email_not_real"
        finally:
            await _cleanup_user(db, user_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_new_this_week_delta_only_counts_last_7_days(db):
    async def run():
        user_id = f"prof-{uuid.uuid4().hex[:8]}"
        email = f"pro_{uuid.uuid4().hex[:6]}@example.com"
        await db[_USERS_COLLECTION].insert_one(_seed_user(user_id, email, "Pat"))
        # One case from this week
        await db[_CASES_COLLECTION].insert_one(
            _seed_case(user_id, email, "Pat", minted_at=_now() - timedelta(days=2))
        )
        # Two cases from > 7 days ago
        for _ in range(2):
            await db[_CASES_COLLECTION].insert_one(
                _seed_case(user_id, email, "Pat", minted_at=_now() - timedelta(days=30))
            )
        try:
            r = await send_weekly_case_analytics(db, dry_run=True, force_window=True)
            ours = [x for x in r["results"] if x["user_id"] == user_id]
            stats = ours[0]["stats"]
            assert stats["total_cases"] == 3
            assert stats["new_this_week"] == 1
        finally:
            await _cleanup_user(db, user_id)
    asyncio.get_event_loop().run_until_complete(run())
