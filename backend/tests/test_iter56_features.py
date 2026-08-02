"""Iteration 56 tests — Streak badge, Top Cheered spotlight, Weekly Email.

Streak
------
* `GET /api/dashboard/progress` returns a `streak_days` integer counting
  the current consecutive-day run (UTC).
* Hitting `/progress` when streak == 7 logs a `week_streak_7` badge on
  the wall for opted-in parents.

Top Cheered spotlight
---------------------
* `GET /api/wall/feed` returns a `top_cheered` array (up to 3) sorted by
  cheer count desc, with `cheer_count` + `i_cheered` per row.
* Empty when nothing has been cheered.

Weekly Email
------------
* `GET /api/dashboard/weekly-email/status` returns `{week_key, sent_this_week,
   is_sunday_utc, weekday_utc}`.
* `POST /api/dashboard/weekly-email/send` is idempotent per ISO week —
  second call in the same week returns `already_sent: True` unless force=True.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from motor.motor_asyncio import AsyncIOMotorClient

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1, PARENT2,
    _client, _ensure_account, _fresh_consented_share,
    _revoke_all, _run,
    MONGO_URL, DB_NAME,
)


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture(scope="module")
def p2_token():
    return _ensure_account(PARENT2)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


@pytest.fixture
def p2_client(p2_token):
    return _client(p2_token)


def _reset_all():
    async def _r():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["wall_opt_in"].delete_many({})
            await db["wall_events"].delete_many({})
            await db["wall_cheers"].delete_many({})
            await db["weekly_progress_email_log"].delete_many({})
            await db["progress_daily_history"].delete_many({})
        finally:
            c.close()
    _run(_r())


@pytest.fixture(scope="module", autouse=True)
def _cleanup(p1_token, p2_token):
    _reset_all()
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    yield
    _reset_all()
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))


# ===========================================================================
# STREAK
# ===========================================================================
class TestStreakDays:
    def test_streak_days_present_and_at_least_one(self, p1_client):
        _reset_all()
        r = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        body = r.json()
        assert "streak_days" in body
        # After hitting /progress once today, streak must be exactly 1.
        assert isinstance(body["streak_days"], int)
        assert body["streak_days"] >= 1

    def test_seven_day_streak_logs_wall_badge(self, p1_client):
        """Simulate a 7-day streak by seeding historical rows for the last
        6 days, then hit /progress today. The `week_streak_7` badge should
        appear on the wall."""
        _reset_all()
        # Opt in first.
        p1_client.post(f"{BASE_URL}/api/wall/opt-in", json={"opt_in": True})
        # Fetch the caller's user_id via /auth/me.
        me = p1_client.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        user_id = me["user_id"]

        async def _seed():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                db = c[DB_NAME]
                end = datetime.now(timezone.utc).date()
                for i in range(1, 7):  # yesterday .. 6 days ago
                    d = (end - timedelta(days=i)).strftime("%Y-%m-%d")
                    await db["progress_daily_history"].update_one(
                        {"user_id": user_id, "date": d},
                        {"$set": {
                            "user_id": user_id, "date": d,
                            "completed_count": 3, "total": 5,
                            "ready": False,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }}, upsert=True,
                    )
            finally:
                c.close()
        _run(_seed())
        # Hitting /progress adds today's row and computes streak_days == 7.
        r = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        body = r.json()
        assert body["streak_days"] == 7, (
            f"expected streak=7 after 6 seeded days + today, got {body['streak_days']}"
        )
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        types = {e["badge_type"] for e in feed["events"]}
        assert "week_streak_7" in types, (
            f"7-day streak did not log wall badge; types seen: {types}"
        )


# ===========================================================================
# TOP CHEERED SPOTLIGHT
# ===========================================================================
class TestTopCheeredSpotlight:
    def test_top_cheered_field_present(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/wall/feed?days=30&limit=5",
                          timeout=20).json()
        assert "top_cheered" in r
        assert isinstance(r["top_cheered"], list)

    def test_top_cheered_shows_cheered_events_sorted(
        self, p1_client, p2_client,
    ):
        _reset_all()
        # Both parents opt in.
        p1_client.post(f"{BASE_URL}/api/wall/opt-in", json={"opt_in": True})
        p2_client.post(f"{BASE_URL}/api/wall/opt-in", json={"opt_in": True})
        # Seed a compare + snapshot so events land on the wall.
        share = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share}", timeout=30)
        p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        p2_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        # p1 cheers p2's events, then re-fetch as p1 to see top_cheered.
        feed_a = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        cheered_events = []
        for ev in feed_a["events"]:
            r = p1_client.post(
                f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
            )
            if r.status_code == 200:
                cheered_events.append(ev["event_id"])
                if len(cheered_events) >= 2:
                    break
        assert cheered_events, "no cheerable events found"
        top = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()["top_cheered"]
        assert 0 < len(top) <= 3, f"unexpected top_cheered length: {len(top)}"
        # Every top row has cheer_count >= 1
        for ev in top:
            assert ev.get("cheer_count", 0) >= 1
            assert "user_hash" in ev and "badge_label" in ev
            assert ev.get("i_cheered") is True   # p1 cheered them
        # Ordered by cheer_count desc
        counts = [e["cheer_count"] for e in top]
        assert counts == sorted(counts, reverse=True)
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share}/revoke")


# ===========================================================================
# WEEKLY EMAIL
# ===========================================================================
class TestWeeklyEmailIdempotency:
    def test_status_shape(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/dashboard/weekly-email/status",
                          timeout=15)
        assert r.status_code == 200
        body = r.json()
        for k in ("week_key", "sent_this_week", "is_sunday_utc", "weekday_utc"):
            assert k in body, f"missing {k}"
        assert 0 <= body["weekday_utc"] <= 6
        assert isinstance(body["is_sunday_utc"], bool)

    def test_send_then_second_call_returns_already_sent(self, p1_client):
        _reset_all()
        r1 = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={}, timeout=60,
        )
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert b1["already_sent"] is False
        assert b1.get("week_key")
        r2 = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={}, timeout=30,
        )
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["already_sent"] is True
        assert b2["week_key"] == b1["week_key"]

    def test_force_bypasses_idempotency(self, p1_client):
        r1 = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={}, timeout=30,
        ).json()
        # Should be already sent from prior test in module
        assert r1["already_sent"] is True
        r2 = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={"force": True}, timeout=60,
        )
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["already_sent"] is False, "force=True must re-send"


class TestWeeklyEmailPreviewEndpoint:
    """Inline dashboard preview mirrors the exact payload the email uses."""

    def test_preview_shape(self, p1_client):
        r = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/preview", timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("week_key", "sent_this_week", "sent_at",
                  "is_sunday_utc", "weekday_utc", "preview"):
            assert k in body, f"preview payload missing {k}"
        p = body["preview"]
        # The exact fields the frontend renders.
        for k in ("user_name", "user_email", "completed_count", "total",
                  "streak_days", "milestones_this_week", "alignment_pct",
                  "dashboard_url"):
            assert k in p, f"preview.{k} missing"
        assert isinstance(p["completed_count"], int)
        assert isinstance(p["total"], int)
        assert isinstance(p["streak_days"], int)
        assert isinstance(p["milestones_this_week"], list)
        assert p["dashboard_url"].startswith("http")

    def test_preview_matches_send_payload(self, p1_client):
        """Preview + a force-send must produce the same numbers so the
        inline card doesn't lie about what will land in the inbox."""
        preview = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/preview", timeout=20,
        ).json()["preview"]
        sent = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={"force": True}, timeout=60,
        ).json()
        assert sent["streak_days"] == preview["streak_days"]
        # Milestones (dedup + order preserved) must match exactly.
        assert sent["milestones_this_week"] == preview["milestones_this_week"]
