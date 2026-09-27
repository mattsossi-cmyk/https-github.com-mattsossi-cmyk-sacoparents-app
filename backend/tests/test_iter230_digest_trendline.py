"""iter230 — Guided-draft digest week-over-week trendline.

Ensures compute_digest emits previous_window_* + trend_delta_pct +
trend_direction ('up' / 'down' / 'flat' / 'new') based on the prior
7-day window (21d–14d ago) vs the current window (14d–7d ago).
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, "/app/backend")


@pytest.fixture(scope="module")
def db_users():
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv

    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    loop = asyncio.new_event_loop()

    async def _find(email):
        return await db.users.find_one({"email": email})

    u1 = loop.run_until_complete(_find("parent1@test.com"))
    u2 = loop.run_until_complete(_find("parent2@test.com"))
    assert u1 and u2, "seed users missing"
    uid1 = u1.get("user_id") or u1.get("id")
    uid2 = u2.get("user_id") or u2.get("id")

    async def _cleanup():
        await db.guided_draft_nudges.delete_many({"user_id": {"$in": [uid1, uid2]}})
        await db.portal_state.update_one(
            {"user_id": uid1}, {"$set": {"guided_drafts": None}}, upsert=True
        )
        await db.portal_state.update_one(
            {"user_id": uid2}, {"$set": {"guided_drafts": None}}, upsert=True
        )

    loop.run_until_complete(_cleanup())
    yield db, uid1, uid2, loop
    loop.run_until_complete(_cleanup())
    client.close()
    loop.close()


def _ms_days_ago(days: float) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)


def _iso_days_ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def _seed_nudge(db, user_id, topic, days_ago):
    await db.guided_draft_nudges.insert_one({
        "user_id": user_id,
        "topic": topic,
        "sent_at": _iso_days_ago(days_ago),
        "week_key": f"trend-{topic}-{days_ago}",
        "days_since_update": 7,
        "days_left": 7,
    })


async def _set_draft(db, user_id, topic, updated_days_ago):
    doc = await db.portal_state.find_one({"user_id": user_id}, {"guided_drafts": 1})
    if not doc or not isinstance(doc.get("guided_drafts"), dict):
        await db.portal_state.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "guided_drafts": {}}},
            upsert=True,
        )
    await db.portal_state.update_one(
        {"user_id": user_id},
        {"$set": {f"guided_drafts.{topic}": {
            "topic": topic,
            "answers": [{"q": "Q", "a": "A"}],
            "updated_at": _ms_days_ago(updated_days_ago),
        }}},
    )


async def _reset(db, uid1, uid2):
    await db.guided_draft_nudges.delete_many({"user_id": {"$in": [uid1, uid2]}})
    await db.portal_state.update_one({"user_id": uid1}, {"$set": {"guided_drafts": None}}, upsert=True)
    await db.portal_state.update_one({"user_id": uid2}, {"$set": {"guided_drafts": None}}, upsert=True)


class TestTrendlineFields:
    def test_new_when_no_prior_data(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users
        loop.run_until_complete(_reset(db, uid1, uid2))

        async def _seed():
            # Current window (10d ago = 14d–7d bucket): 1 sent, 1 finished
            await _seed_nudge(db, uid1, "foundation", 10)
            # Draft cleared (guided_drafts is null) -> counts as finished
        loop.run_until_complete(_seed())

        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 1
        assert digest["total_finished"] == 1
        assert digest["conversion_pct"] == 100.0
        assert digest["previous_total_sent"] == 0
        assert digest["previous_total_finished"] == 0
        assert digest["previous_conversion_pct"] == 0.0
        assert digest["trend_direction"] == "new"
        assert digest["trend_delta_pct"] == 0.0
        # Window ISO fields present
        assert digest["previous_window_start"]
        assert digest["previous_window_end"]
        loop.run_until_complete(_reset(db, uid1, uid2))

    def test_up_trend(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users
        loop.run_until_complete(_reset(db, uid1, uid2))

        async def _seed():
            # Current window: 2 sent, 2 finished => 100%
            await _seed_nudge(db, uid1, "foundation", 10)  # cleared -> finished
            await _seed_nudge(db, uid2, "medical", 10)     # cleared -> finished
            # Previous window (21–14d ago), e.g. 17d ago: 2 sent, 0 finished => 0%
            await _seed_nudge(db, uid1, "safety", 17)
            await _set_draft(db, uid1, "safety", 25)  # draft BEFORE nudge, so not finished
            await _seed_nudge(db, uid2, "educational", 17)
            await _set_draft(db, uid2, "educational", 25)
        loop.run_until_complete(_seed())

        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 2
        assert digest["total_finished"] == 2
        assert digest["conversion_pct"] == 100.0
        assert digest["previous_total_sent"] == 2
        assert digest["previous_total_finished"] == 0
        assert digest["previous_conversion_pct"] == 0.0
        assert digest["trend_delta_pct"] == 100.0
        assert digest["trend_direction"] == "up"
        loop.run_until_complete(_reset(db, uid1, uid2))

    def test_down_trend(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users
        loop.run_until_complete(_reset(db, uid1, uid2))

        async def _seed():
            # Current: 2 sent, 0 finished => 0%
            await _seed_nudge(db, uid1, "foundation", 10)
            await _set_draft(db, uid1, "foundation", 20)  # draft older than nudge -> not finished
            await _seed_nudge(db, uid2, "medical", 10)
            await _set_draft(db, uid2, "medical", 20)
            # Previous: 1 sent, 1 finished => 100%
            await _seed_nudge(db, uid1, "safety", 17)
            # draft cleared -> finished. Need to clear guided_drafts.safety only
            # (foundation/medical still present with old updated_at)
        loop.run_until_complete(_seed())

        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 2, digest
        assert digest["total_finished"] == 0, digest
        assert digest["conversion_pct"] == 0.0
        assert digest["previous_total_sent"] == 1
        assert digest["previous_total_finished"] == 1
        assert digest["previous_conversion_pct"] == 100.0
        assert digest["trend_delta_pct"] == -100.0
        assert digest["trend_direction"] == "down"
        loop.run_until_complete(_reset(db, uid1, uid2))

    def test_flat_trend_within_half_point(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users
        loop.run_until_complete(_reset(db, uid1, uid2))

        async def _seed():
            # Both windows: 1 sent, 1 finished => 100% vs 100% -> flat (delta=0)
            await _seed_nudge(db, uid1, "foundation", 10)  # cleared -> finished
            await _seed_nudge(db, uid2, "medical", 17)     # cleared -> finished
        loop.run_until_complete(_seed())

        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 1
        assert digest["total_finished"] == 1
        assert digest["previous_total_sent"] == 1
        assert digest["previous_total_finished"] == 1
        assert digest["trend_delta_pct"] == 0.0
        assert digest["trend_direction"] == "flat"
        loop.run_until_complete(_reset(db, uid1, uid2))
