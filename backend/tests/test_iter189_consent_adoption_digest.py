"""iter189 — Consent Adoption Digest (Monday-morning admin email).

Locks the behaviour of `consent_adoption_digest`:
  * pure `_compute_consent_stats` — parents_consented / cases_both
    / 7-day deltas / unlock_rate_pct.
  * `_in_send_window` — Monday 09-11 America/Chicago only.
  * `_week_start` — Monday of the given date.
  * `send_consent_adoption_digest`:
      - dry_run + force_window bypasses the send window and records
        a dedupe row without dispatching email.
      - dedupes per (admin_email, ISO week).
      - `no_baseline_activity` short-circuit when nobody has
        consented yet (avoids inbox noise before feature has data).
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

from consent_adoption_digest import (  # noqa: E402
    _CASES_COLLECTION,
    _SENDS_COLLECTION,
    _compute_consent_stats,
    _in_send_window,
    _week_start,
    send_consent_adoption_digest,
)


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="function")
def db():
    yield AsyncIOMotorClient(MONGO_URL)[DB_NAME]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _cleanup(db, case_ids, admin_emails, week_start):
    if case_ids:
        await db[_CASES_COLLECTION].delete_many({"case_id": {"$in": case_ids}})
    if admin_emails and week_start:
        await db[_SENDS_COLLECTION].delete_many({
            "admin_email": {"$in": admin_emails},
            "week_start": week_start,
        })


def _seed_case(*, both_consented: bool, one_consented: bool = False,
               consent_age_days: int = 3) -> dict:
    """Manufacture a joint_alignment_cases doc with the shape the
    aggregator expects."""
    consent_at = _now() - timedelta(days=consent_age_days)
    a_consent = consent_at if (both_consented or one_consented) else None
    b_consent = consent_at if both_consented else None
    return {
        "case_id": f"SA-CONS-{uuid.uuid4().hex[:6].upper()}",
        "origin": "in_app_professional",
        "parents": [
            {"parent_slot": "A", "email": "a@example.com",
             "child_needs_share_consent_at": a_consent},
            {"parent_slot": "B", "email": "b@example.com",
             "child_needs_share_consent_at": b_consent},
        ],
        "status": "both_complete",
        "created_at": _now() - timedelta(days=30),
    }


# --- pure helpers ----

def test_in_send_window_only_monday_morning():
    monday_am = datetime(2026, 3, 2, 16, 0, tzinfo=timezone.utc)  # 10 CST
    assert _in_send_window(monday_am) is True
    tuesday = datetime(2026, 3, 3, 16, 0, tzinfo=timezone.utc)
    assert _in_send_window(tuesday) is False
    monday_pm = datetime(2026, 3, 2, 21, 0, tzinfo=timezone.utc)  # 15 CST
    assert _in_send_window(monday_pm) is False


def test_week_start_returns_monday_iso():
    wed = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)
    assert _week_start(wed) == "2026-03-02"


def test_compute_stats_counts_parents_and_cases():
    week_ago = _now() - timedelta(days=7)
    cases = [
        _seed_case(both_consented=True, consent_age_days=2),   # both this week
        _seed_case(both_consented=True, consent_age_days=20),  # both, old
        _seed_case(both_consented=False, one_consented=True,
                   consent_age_days=1),                        # 1 this week
        _seed_case(both_consented=False),                      # nobody
    ]
    stats = _compute_consent_stats(cases, week_ago)
    # Parents opted in: 2 + 2 + 1 + 0 = 5
    assert stats["parents_consented"] == 5
    # Cases where both consented: 2
    assert stats["cases_both_consented"] == 2
    assert stats["cases_total"] == 4
    assert stats["unlock_rate_pct"] == 50
    # This week: the first case has both parents consenting 2 days
    # ago → 2 opt-ins this week + 1 case newly-unlocked. The third
    # case adds 1 more parent opt-in.
    assert stats["parents_consented_delta_7d"] == 3
    assert stats["cases_both_delta_7d"] == 1


def test_compute_stats_empty_input_returns_zero():
    stats = _compute_consent_stats([], _now() - timedelta(days=7))
    assert stats == {
        "parents_consented": 0,
        "cases_both_consented": 0,
        "cases_total": 0,
        "unlock_rate_pct": 0,
        "parents_consented_delta_7d": 0,
        "cases_both_delta_7d": 0,
    }


# --- sweep pipeline ----

def test_dry_run_dispatches_and_dedupes(db):
    async def run():
        admin = f"admin_{uuid.uuid4().hex[:8]}@example.com"
        seeded = [
            _seed_case(both_consented=True, consent_age_days=1),
            _seed_case(both_consented=False, one_consented=True,
                       consent_age_days=1),
        ]
        case_ids = [c["case_id"] for c in seeded]
        await db[_CASES_COLLECTION].insert_many(seeded)
        week_start = _week_start(_now())
        try:
            r1 = await send_consent_adoption_digest(
                db,
                admin_emails=[admin],
                dry_run=True,
                force_window=True,
            )
            assert r1.get("sent_count") == 1
            ours = [x for x in r1["results"] if x["admin_email"] == admin]
            assert ours[0]["sent"] is True
            assert ours[0].get("dry_run") is True
            # Dedupe row written
            n = await db[_SENDS_COLLECTION].count_documents({
                "admin_email": admin, "week_start": week_start,
            })
            assert n == 1
            # Second run in the same week is a no-op for that admin.
            r2 = await send_consent_adoption_digest(
                db,
                admin_emails=[admin],
                dry_run=True,
                force_window=True,
            )
            ours2 = [x for x in r2["results"] if x["admin_email"] == admin]
            assert ours2[0]["sent"] is False
            assert ours2[0]["reason"] == "already_sent_this_week"
        finally:
            await _cleanup(db, case_ids, [admin], week_start)
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_outside_send_window(db):
    async def run():
        # Tuesday — outside window
        tue = datetime(2026, 3, 3, 16, 0, tzinfo=timezone.utc)
        r = await send_consent_adoption_digest(
            db,
            admin_emails=["admin@example.com"],
            dry_run=True,
            now=tue,
            force_window=False,
        )
        assert r["skipped"] == "outside_send_window"
        assert r["results"] == []
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_when_no_admin_recipients(db):
    async def run():
        r = await send_consent_adoption_digest(
            db, admin_emails=[], dry_run=True, force_window=True,
        )
        assert r["skipped"] == "no_admin_recipients"
        assert r["results"] == []
    asyncio.get_event_loop().run_until_complete(run())


def test_skips_when_no_baseline_activity(db):
    async def run():
        # Baseline check runs BEFORE the DB scan is filtered, so any
        # pre-existing consent rows in `test_database` from other
        # tests would flip this to has-baseline. To keep the test
        # hermetic we point the sweep at an isolated collection
        # namespace using a fresh DB name.
        temp_client = AsyncIOMotorClient(MONGO_URL)
        temp_db = temp_client[f"test_consent_digest_{uuid.uuid4().hex[:8]}"]
        try:
            # Seed one case with NO consent from either side so the
            # sweep sees `cases_total > 0` but baseline = 0.
            await temp_db[_CASES_COLLECTION].insert_one(
                _seed_case(both_consented=False),
            )
            r = await send_consent_adoption_digest(
                temp_db,
                admin_emails=["admin@example.com"],
                dry_run=True,
                force_window=True,
            )
            assert r["skipped"] == "no_baseline_activity"
            assert r["stats"]["parents_consented"] == 0
            assert r["stats"]["cases_both_consented"] == 0
            assert r["results"] == []
        finally:
            await temp_client.drop_database(temp_db.name)
    asyncio.get_event_loop().run_until_complete(run())


def test_second_admin_still_sends_even_after_first_deduped(db):
    """One admin already got their digest this week; a different
    admin in the same run should still receive it."""
    async def run():
        admin_a = f"admin_a_{uuid.uuid4().hex[:6]}@example.com"
        admin_b = f"admin_b_{uuid.uuid4().hex[:6]}@example.com"
        seeded = [_seed_case(both_consented=True, consent_age_days=1)]
        case_ids = [c["case_id"] for c in seeded]
        await db[_CASES_COLLECTION].insert_many(seeded)
        week_start = _week_start(_now())
        try:
            # Admin A pre-flighted first
            await send_consent_adoption_digest(
                db, admin_emails=[admin_a], dry_run=True, force_window=True,
            )
            # Then both admins in one pass
            r = await send_consent_adoption_digest(
                db,
                admin_emails=[admin_a, admin_b],
                dry_run=True,
                force_window=True,
            )
            by_email = {x["admin_email"]: x for x in r["results"]}
            assert by_email[admin_a]["sent"] is False
            assert by_email[admin_a]["reason"] == "already_sent_this_week"
            assert by_email[admin_b]["sent"] is True
            assert by_email[admin_b].get("dry_run") is True
        finally:
            await _cleanup(db, case_ids, [admin_a, admin_b], week_start)
    asyncio.get_event_loop().run_until_complete(run())
