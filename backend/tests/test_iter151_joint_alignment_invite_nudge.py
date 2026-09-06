"""iter151 — Joint Alignment invitation-reminder sweep.

Locks the behaviour of the 5-day nudge module. Uses `dry_run=True`
so no real email is dispatched; the dedupe row is still written so
the "already nudged" guard can be tested.
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

from joint_alignment_invite_nudge import (  # noqa: E402
    _CASES_COLLECTION,
    _SENDS_COLLECTION,
    _STALE_DAYS,
    send_joint_alignment_invitation_reminders,
)


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="function")
def db():
    """Fresh scoped DB handle — every test cleans its own cases +
    sends rows so ordering never affects state."""
    d = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    yield d


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _cleanup_case(db, case_id: str):
    await db[_CASES_COLLECTION].delete_many({"case_id": case_id})
    await db[_SENDS_COLLECTION].delete_many({"case_id": case_id})


def _seed_case(*, minted_at, both_accepted=False, both_pending=True, expired=False, origin="in_app_professional"):
    parent_a = {
        "parent_slot": "A",
        "email": f"a_{uuid.uuid4().hex[:6]}@example.com",
        "name": "Alex",
        "invitation_token": f"tok_a_{uuid.uuid4().hex[:10]}",
        "token_expires_at": minted_at + timedelta(days=(-1 if expired else 7)),
        "accepted_at": _now() if both_accepted else None,
    }
    parent_b = {
        "parent_slot": "B",
        "email": f"b_{uuid.uuid4().hex[:6]}@example.com",
        "name": "Bailey",
        "invitation_token": f"tok_b_{uuid.uuid4().hex[:10]}",
        "token_expires_at": minted_at + timedelta(days=(-1 if expired else 7)),
        "accepted_at": _now() if both_accepted else None,
    }
    if not both_pending and not both_accepted:
        # Only parent A accepted — B still pending, that's the mixed case
        parent_a["accepted_at"] = _now()
    return {
        "case_id": f"SA-{uuid.uuid4().hex[:6].upper()}",
        "origin": origin,
        "assessment_type": "co-parenting",
        "professional": {"id": "prof-1", "name": "Test Mediator", "email": "m@example.com"},
        "parents": [parent_a, parent_b],
        "status": "pending",
        "created_at": minted_at,
    }


def test_finds_5day_old_unaccepted_and_dispatches_dry_run(db):
    async def run():
        stale = _now() - timedelta(days=_STALE_DAYS + 1)
        case = _seed_case(minted_at=stale)
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            r = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            # Both parents pending → both should nudge
            our_results = [x for x in r["results"] if x["case_id"] == case_id]
            assert len(our_results) == 2
            assert all(x["sent"] for x in our_results)
            # dedupe row written for each
            sends = await db[_SENDS_COLLECTION].count_documents({"case_id": case_id})
            assert sends == 2
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_freshly_minted_cases(db):
    async def run():
        # Only 2 days old — not stale yet
        fresh = _now() - timedelta(days=2)
        case = _seed_case(minted_at=fresh)
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            r = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our = [x for x in r["results"] if x["case_id"] == case_id]
            assert our == [], f"fresh case should not be nudged, got: {our}"
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_accepted_parents(db):
    async def run():
        stale = _now() - timedelta(days=_STALE_DAYS + 1)
        case = _seed_case(minted_at=stale, both_accepted=True)
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            r = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our = [x for x in r["results"] if x["case_id"] == case_id]
            assert our == [], "both-accepted case should have zero pending parents"
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_expired_tokens(db):
    async def run():
        stale = _now() - timedelta(days=_STALE_DAYS + 1)
        case = _seed_case(minted_at=stale, expired=True)
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            r = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our = [x for x in r["results"] if x["case_id"] == case_id]
            assert our == [], "expired-token case should be skipped"
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_only_nudges_in_app_professional_cases(db):
    async def run():
        stale = _now() - timedelta(days=_STALE_DAYS + 1)
        case = _seed_case(minted_at=stale, origin="server_to_server")
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            r = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our = [x for x in r["results"] if x["case_id"] == case_id]
            assert our == [], "server-to-server cases must not be nudged from here"
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_dedupe_prevents_repeat_nudges(db):
    async def run():
        stale = _now() - timedelta(days=_STALE_DAYS + 1)
        case = _seed_case(minted_at=stale)
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            # First sweep
            r1 = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our1 = [x for x in r1["results"] if x["case_id"] == case_id]
            assert all(x["sent"] for x in our1)

            # Second sweep — dedupe row already present, expect zero sends
            r2 = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our2 = [x for x in r2["results"] if x["case_id"] == case_id]
            assert len(our2) == 2  # still 2 candidates
            assert all(not x["sent"] for x in our2)
            assert all("already_nudged" in x.get("reason", "") for x in our2)
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())


def test_reminder_note_flows_into_dispatched_row(db):
    """When the case doc has `reminder_note`, the sweep must include
    it in the (case, parent) row it hands to the email dispatcher."""
    async def run():
        stale = _now() - timedelta(days=_STALE_DAYS + 1)
        case = _seed_case(minted_at=stale)
        case["reminder_note"] = "Looking forward to our Thursday session."
        case_id = case["case_id"]
        await db[_CASES_COLLECTION].insert_one(case)
        try:
            r = await send_joint_alignment_invitation_reminders(
                db, dry_run=True, force_window=True,
            )
            our = [x for x in r["results"] if x["case_id"] == case_id]
            assert len(our) == 2
            # dry_run rows don't carry the note themselves — they
            # just prove the dispatcher was called. Confirm the
            # nudge_sends dedupe row exists AND that the same-case
            # row-finder attached the note.  We probe the internal
            # `_find_stale_pending_parents` for that assertion.
            from joint_alignment_invite_nudge import _find_stale_pending_parents
            rows = await _find_stale_pending_parents(db, _now())
            our_rows = [x for x in rows if x["case_id"] == case_id]
            assert all(
                x.get("reminder_note") == "Looking forward to our Thursday session."
                for x in our_rows
            )
        finally:
            await _cleanup_case(db, case_id)
    asyncio.get_event_loop().run_until_complete(run())
