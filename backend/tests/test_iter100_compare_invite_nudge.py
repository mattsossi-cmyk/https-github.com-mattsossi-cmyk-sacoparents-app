"""Iter 100 — Compare Invite Nudge Reminder (weekly cron).

Locks the suppression rules of `send_compare_invite_nudges()` so the
sweep can never silently spam parents. All tests hit a live Mongo but
use a private, uuid-prefixed share_id so they never touch real data.

Coverage:
    * Fresh share (< 7 days old) → skipped.
    * Stale awaiting-consent share → nudge fires, send row recorded.
    * Dedupe: second sweep in the same window → suppressed.
    * Partner already consented (status != awaiting_partner_consent) → skipped.
    * Creator email is @demo.local / missing → skipped.
    * Windows: outside Monday 08-22 UTC → whole sweep short-circuits
      (unless force_window=True).
    * Feature flag: default off (loop stays idle).
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from compare_invite_nudge import (  # noqa: E402
    SENDS_COLLECTION, _enabled, _in_send_window, _looks_like_real_email,
    send_compare_invite_nudges,
)


# ---------------------------------------------------------------------------
# Mongo helpers.
# ---------------------------------------------------------------------------

def _mongo():
    with open("/app/backend/.env") as fh:
        env: Dict[str, str] = {}
        for ln in fh:
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    client = AsyncIOMotorClient(env["MONGO_URL"])
    return client, client[env.get("DB_NAME", "test_database")]


def _fake_share(**over) -> Dict[str, Any]:
    """Return a stale, awaiting-partner-consent share row that would
    normally trigger a nudge. Callers override any field to construct
    scenarios."""
    now = datetime.now(timezone.utc)
    base = {
        "share_id":         f"tst_iter100_{uuid.uuid4().hex[:12]}",
        "user_pair":        ["userA", "userB"],
        "creator_user_id":  "userA",
        "creator_name":     "Test Creator",
        "creator_email":    f"iter100_{uuid.uuid4().hex[:8]}@iter100test.com",
        "partner_user_id":  "userB",
        "partner_name":     "Test Partner",
        "partner_email":    "partner@iter100test.com",
        "creator_consent":  True,
        "partner_consent":  False,
        "status":           "awaiting_partner_consent",
        "created_at":       (now - timedelta(days=10)).isoformat(),
        "updated_at":       (now - timedelta(days=10)).isoformat(),
    }
    base.update(over)
    return base


async def _run_sweep(db, *, dry_run=True, now=None, force_window=True):
    return await send_compare_invite_nudges(
        db, dry_run=dry_run, now=now, force_window=force_window,
    )


async def _cleanup(db, share_id: str):
    for coll in (
        "edu_deep_shares", "psych_deep_shares", "med_deep_shares", "snc2_shares",
    ):
        await db[coll].delete_many({"share_id": share_id})
    await db[SENDS_COLLECTION].delete_many({"share_id": share_id})


# ---------------------------------------------------------------------------
# Unit-level: pure helpers.
# ---------------------------------------------------------------------------

def test_looks_like_real_email_rejects_demo_and_guest():
    assert _looks_like_real_email("parent@example.com") is True
    assert _looks_like_real_email("parent@demo.local") is False
    assert _looks_like_real_email("parent@guest.local") is False
    assert _looks_like_real_email("") is False
    assert _looks_like_real_email(None) is False
    assert _looks_like_real_email("not-an-email") is False


def test_send_window_is_monday_08_to_22_utc():
    monday_9am  = datetime(2026, 2, 9, 9,  0, tzinfo=timezone.utc)   # Mon
    monday_21pm = datetime(2026, 2, 9, 21, 30, tzinfo=timezone.utc)  # Mon
    tuesday_9am = datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc)
    monday_5am  = datetime(2026, 2, 9, 5,  0, tzinfo=timezone.utc)
    monday_11pm = datetime(2026, 2, 9, 23, 0, tzinfo=timezone.utc)
    assert _in_send_window(monday_9am)  is True
    assert _in_send_window(monday_21pm) is True
    assert _in_send_window(tuesday_9am) is False
    assert _in_send_window(monday_5am)  is False
    assert _in_send_window(monday_11pm) is False


def test_feature_flag_defaults_off():
    """Env var must be explicitly set for the loop to activate.
    Prevents accidental prod send on rollout."""
    prev = os.environ.pop("COMPARE_INVITE_NUDGE_ENABLED", None)
    try:
        assert _enabled() is False
    finally:
        if prev is not None:
            os.environ["COMPARE_INVITE_NUDGE_ENABLED"] = prev


# ---------------------------------------------------------------------------
# Sweep behaviour (live Mongo, dry-run).
# ---------------------------------------------------------------------------

def test_sweep_outside_window_short_circuits_without_touching_mongo():
    """If we're not in the send window and force_window is False, the
    sweep returns immediately with `skipped=outside_send_window`."""
    async def scenario():
        client, db = _mongo()
        try:
            tuesday = datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc)
            got = await send_compare_invite_nudges(
                db, dry_run=True, now=tuesday, force_window=False,
            )
            assert got["skipped"] == "outside_send_window"
            assert got["results"] == []
        finally:
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())


def test_sweep_nudges_a_stale_awaiting_share_and_dedupes_the_second_pass():
    async def scenario():
        client, db = _mongo()
        share = _fake_share()
        sid = share["share_id"]
        try:
            await db.edu_deep_shares.insert_one(share)

            # First sweep should nudge this share (dry_run so no real email).
            r1 = await _run_sweep(db)
            first = [x for x in r1["results"] if x.get("share_id") == sid]
            assert len(first) == 1, "our share should be in the results"
            assert first[0]["sent"] is True
            assert first[0].get("dry_run") is True
            # A dedupe row must have landed.
            recorded = await db[SENDS_COLLECTION].count_documents({"share_id": sid})
            assert recorded == 1

            # Second sweep should be deduped.
            r2 = await _run_sweep(db)
            second = [x for x in r2["results"] if x.get("share_id") == sid]
            assert len(second) == 1
            assert second[0]["sent"] is False
            assert "dedupe" in (second[0].get("reason") or "")
            # No second row.
            recorded_again = await db[SENDS_COLLECTION].count_documents({"share_id": sid})
            assert recorded_again == 1
        finally:
            await _cleanup(db, sid)
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())


def test_sweep_skips_fresh_share_under_7_days_old():
    async def scenario():
        client, db = _mongo()
        # Only 3 days old — should not be picked up by the stale query.
        share = _fake_share(
            created_at=(datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        )
        sid = share["share_id"]
        try:
            await db.edu_deep_shares.insert_one(share)
            r = await _run_sweep(db)
            found = [x for x in r["results"] if x.get("share_id") == sid]
            assert found == [], "fresh share should not be nudged"
        finally:
            await _cleanup(db, sid)
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())


def test_sweep_skips_share_that_partner_has_consented():
    async def scenario():
        client, db = _mongo()
        share = _fake_share(
            partner_consent=True,
            status="active",
        )
        sid = share["share_id"]
        try:
            await db.psych_deep_shares.insert_one(share)
            r = await _run_sweep(db)
            found = [x for x in r["results"] if x.get("share_id") == sid]
            assert found == [], "already-consented share should not be nudged"
        finally:
            await _cleanup(db, sid)
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())


def test_sweep_skips_share_with_demo_email_creator():
    async def scenario():
        client, db = _mongo()
        share = _fake_share(creator_email="not_real@demo.local")
        sid = share["share_id"]
        try:
            await db.med_deep_shares.insert_one(share)
            r = await _run_sweep(db)
            found = [x for x in r["results"] if x.get("share_id") == sid]
            assert len(found) == 1
            assert found[0]["sent"] is False
            assert found[0]["reason"] == "creator_email_not_real"
            # No send row recorded for demo emails — dedupe collection stays clean.
            recorded = await db[SENDS_COLLECTION].count_documents({"share_id": sid})
            assert recorded == 0
        finally:
            await _cleanup(db, sid)
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())


def test_sweep_finds_shares_across_every_registered_collection():
    """A stale share landing in ANY of the registered share collections
    should be nudged — proves the tuple `SHARE_COLLECTIONS` is
    iterated correctly."""
    async def scenario():
        client, db = _mongo()
        shares = [
            (_fake_share(), "edu_deep_shares"),
            (_fake_share(), "psych_deep_shares"),
            (_fake_share(), "med_deep_shares"),
            (_fake_share(), "snc2_shares"),
        ]
        sids = [s["share_id"] for s, _ in shares]
        try:
            for share, coll in shares:
                await db[coll].insert_one(share)
            r = await _run_sweep(db)
            hits = [x for x in r["results"] if x.get("share_id") in sids]
            assert len(hits) == 4, f"expected all 4 collections to fire, got: {hits}"
            assert all(h["sent"] for h in hits)
        finally:
            for sid in sids:
                await _cleanup(db, sid)
            client.close()

    asyncio.get_event_loop().run_until_complete(scenario())
