"""Iteration 66 tests — Wall Cheer Digest.

Backend contract:
* ``wall_utils.build_weekly_cheer_digest`` returns
  ``{opted_in, cheers_received, community_pulse, week_start}``.
* The Sunday weekly email (`/api/dashboard/weekly-email/preview` and
  `/api/dashboard/weekly-email/send`) surfaces:
    - ``cheers_received`` — anonymised cheer counts on the parent's OWN
      badges this week, only when the parent is opted-in to the wall.
    - ``community_pulse`` — up to three most-cheered ANONYMOUS badges
      earned by other parents this week; shown to opted-in AND
      opted-out parents alike, so opted-out parents see momentum too.
    - ``cheers_received_total`` — sum across ``cheers_received``.
    - ``wall_opted_in`` — bool for the UI header label.
* Cheerer identity is NEVER exposed (respects the anonymity model).

The tests seed wall events + cheers directly in Mongo so we don't have
to reach through the compare/deep-dive flows just to earn badges.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1, PARENT2,
    _client, _ensure_account, _run,
    MONGO_URL, DB_NAME,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
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


def _reset_wall():
    async def _r():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["wall_events"].delete_many({})
            await db["wall_cheers"].delete_many({})
            await db["wall_opt_in"].delete_many({})
            await db["weekly_progress_email_log"].delete_many({})
            await db["weekly_progress_email_notes"].delete_many({})
        finally:
            c.close()
    _run(_r())


@pytest.fixture(autouse=True)
def _cleanup():
    _reset_wall()
    yield
    _reset_wall()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _user_id(client):
    r = client.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


def _week_start(dt=None):
    now = dt or datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )


def _seed_event(user_id: str, user_hash: str, badge_type: str,
                created_at: datetime) -> str:
    event_id = f"wall_{uuid.uuid4().hex[:12]}"
    async def _s():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["wall_events"].insert_one({
                "event_id": event_id,
                "user_id": user_id,
                "user_hash": user_hash,
                "badge_type": badge_type,
                "created_at": created_at.isoformat(),
            })
        finally:
            c.close()
    _run(_s())
    return event_id


def _seed_cheer(event_id: str, cheerer_user_id: str,
                created_at: datetime) -> None:
    async def _s():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["wall_cheers"].insert_one({
                "event_id": event_id,
                "user_id": cheerer_user_id,
                "created_at": created_at.isoformat(),
            })
        finally:
            c.close()
    _run(_s())


# ---------------------------------------------------------------------------
# 1. Direct helper unit tests
# ---------------------------------------------------------------------------
class TestBuildWeeklyCheerDigest:

    def test_empty_state_returns_empty_lists(self, p1_client):
        from wall_utils import build_weekly_cheer_digest
        uid = _user_id(p1_client)
        async def _r():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                return await build_weekly_cheer_digest(
                    c[DB_NAME], uid, _week_start(),
                )
            finally:
                c.close()
        digest = _run(_r())
        assert digest["opted_in"] is False
        assert digest["cheers_received"] == []
        assert digest["community_pulse"] == []
        assert "week_start" in digest

    def test_cheers_received_only_when_opted_in(self, p1_client, p2_client):
        from wall_utils import build_weekly_cheer_digest, anon_hash
        p1 = _user_id(p1_client)
        p2 = _user_id(p2_client)
        # p1 has a Foundation Ready badge from 3 days ago; p2 cheered it today.
        ws = _week_start()
        ev = _seed_event(p1, anon_hash(p1), "foundation_ready",
                         ws + timedelta(days=1))
        _seed_cheer(ev, p2, ws + timedelta(days=2))

        # p1 is NOT opted-in yet — cheers_received should be empty for privacy.
        async def _read():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                return await build_weekly_cheer_digest(c[DB_NAME], p1, ws)
            finally:
                c.close()
        d1 = _run(_read())
        assert d1["opted_in"] is False
        assert d1["cheers_received"] == []

        # Opt p1 in and re-read — now they see the cheer.
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=15)
        d2 = _run(_read())
        assert d2["opted_in"] is True
        assert len(d2["cheers_received"]) == 1
        row = d2["cheers_received"][0]
        assert row["badge_type"] == "foundation_ready"
        assert row["cheer_count"] == 1
        assert "foundation" in row["badge_label"].lower()
        # cheerer identity must NEVER leak — no user_id/user_hash on the row.
        assert "user_id" not in row
        assert "cheerer_user_id" not in row

    def test_community_pulse_excludes_own_events(
            self, p1_client, p2_client):
        from wall_utils import build_weekly_cheer_digest, anon_hash
        p1 = _user_id(p1_client)
        p2 = _user_id(p2_client)
        ws = _week_start()
        # p1's own event, cheered a bunch — should NOT appear in community_pulse
        own = _seed_event(p1, anon_hash(p1), "communication_master",
                          ws + timedelta(days=1))
        _seed_cheer(own, p2, ws + timedelta(days=1, hours=1))
        _seed_cheer(own, "some-other-user", ws + timedelta(days=1, hours=2))
        # p2's event, cheered less — should appear
        other = _seed_event(p2, anon_hash(p2), "high_alignment_90",
                            ws + timedelta(days=2))
        _seed_cheer(other, p1, ws + timedelta(days=2, hours=1))

        async def _read():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                return await build_weekly_cheer_digest(c[DB_NAME], p1, ws)
            finally:
                c.close()
        d = _run(_read())
        badge_types = [r["badge_type"] for r in d["community_pulse"]]
        assert "high_alignment_90" in badge_types
        assert "communication_master" not in badge_types  # own event filtered

    def test_pre_week_cheers_are_excluded(self, p1_client, p2_client):
        """A cheer landed BEFORE the current week must not count."""
        from wall_utils import build_weekly_cheer_digest, anon_hash
        p1 = _user_id(p1_client)
        p2 = _user_id(p2_client)
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=15)
        ws = _week_start()
        ev = _seed_event(p1, anon_hash(p1), "foundation_ready",
                         ws - timedelta(days=10))
        _seed_cheer(ev, p2, ws - timedelta(days=3))    # last week -> excluded
        _seed_cheer(ev, "another", ws + timedelta(hours=2))  # this week -> counts

        async def _read():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                return await build_weekly_cheer_digest(c[DB_NAME], p1, ws)
            finally:
                c.close()
        d = _run(_read())
        assert len(d["cheers_received"]) == 1
        assert d["cheers_received"][0]["cheer_count"] == 1

    def test_cheers_received_sorted_desc_by_count(
            self, p1_client, p2_client):
        from wall_utils import build_weekly_cheer_digest, anon_hash
        p1 = _user_id(p1_client)
        p2 = _user_id(p2_client)
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=15)
        ws = _week_start()
        # low-cheer badge earned earlier
        low = _seed_event(p1, anon_hash(p1), "foundation_ready",
                          ws + timedelta(days=1))
        _seed_cheer(low, p2, ws + timedelta(days=1, hours=1))
        # high-cheer badge earned later
        high = _seed_event(p1, anon_hash(p1), "communication_master",
                           ws + timedelta(days=2))
        for i in range(3):
            _seed_cheer(high, f"cheer-{i}", ws + timedelta(days=2, hours=i + 1))

        async def _read():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                return await build_weekly_cheer_digest(c[DB_NAME], p1, ws)
            finally:
                c.close()
        d = _run(_read())
        assert d["cheers_received"][0]["badge_type"] == "communication_master"
        assert d["cheers_received"][0]["cheer_count"] == 3
        assert d["cheers_received"][1]["badge_type"] == "foundation_ready"


# ---------------------------------------------------------------------------
# 2. Weekly-email preview endpoint carries the digest
# ---------------------------------------------------------------------------
class TestPreviewEndpointCarriesDigest:

    def test_preview_includes_all_digest_fields(
            self, p1_client, p2_client):
        from wall_utils import anon_hash
        p1 = _user_id(p1_client)
        p2 = _user_id(p2_client)
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=15)
        ws = _week_start()
        ev = _seed_event(p1, anon_hash(p1), "week_streak_7",
                         ws + timedelta(days=1))
        _seed_cheer(ev, p2, ws + timedelta(days=1, hours=3))

        r = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/preview", timeout=15,
        )
        assert r.status_code == 200, r.text
        preview = r.json()["preview"]
        assert preview["wall_opted_in"] is True
        assert preview["cheers_received_total"] >= 1
        assert isinstance(preview["cheers_received"], list)
        assert isinstance(preview["community_pulse"], list)
        # Cheerer identity never surfaces on the wire.
        for row in preview["cheers_received"]:
            assert "user_id" not in row
            assert "cheerer_user_id" not in row

    def test_preview_omits_digest_for_opted_out_when_no_activity(
            self, p1_client):
        """Opted-out AND no community pulse → empty lists, still safe."""
        r = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/preview", timeout=15,
        )
        assert r.status_code == 200
        preview = r.json()["preview"]
        assert preview["wall_opted_in"] is False
        assert preview["cheers_received"] == []
        assert preview["community_pulse"] == []
        assert preview["cheers_received_total"] == 0


# ---------------------------------------------------------------------------
# 3. Weekly-email send endpoint returns digest counts
# ---------------------------------------------------------------------------
class TestSendEndpointReturnsDigestCounts:

    def test_send_response_carries_totals(self, p1_client, p2_client):
        from wall_utils import anon_hash
        p1 = _user_id(p1_client)
        p2 = _user_id(p2_client)
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=15)
        ws = _week_start()
        ev = _seed_event(p1, anon_hash(p1), "foundation_ready",
                         ws + timedelta(days=1))
        _seed_cheer(ev, p2, ws + timedelta(days=1, hours=2))
        _seed_cheer(ev, "another", ws + timedelta(days=1, hours=3))

        r = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={"force": True}, timeout=30,
        )
        # 503 = Resend not configured in local pytest — that's expected in
        # this env. What we care about is that the endpoint's response
        # (whether 200 or 503) doesn't blow up on the new digest fields.
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            body = r.json()
            assert body["cheers_received_total"] >= 2
            assert body["community_pulse_count"] >= 0


# ---------------------------------------------------------------------------
# 4. Email service unit test — HTML + plain both include cheer block
# ---------------------------------------------------------------------------


def test_weekly_progress_email_has_no_details():
    import email_service
    from unittest.mock import patch
    with patch.object(email_service, "_send") as m:
        email_service.send_weekly_progress_summary(
            to_email="p@example.com", user_name="Sam", completed_count=3, total=8, streak_days=4,
            milestones_this_week=["Secret milestone"], alignment_pct=71, dashboard_url="https://e/dash",
            personal_note="private note", cheers_received=[{"badge_label": "Badge X", "count": 2}],
        )
    body = m.call_args.kwargs["html"] + m.call_args.kwargs["text"]
    for leaked in ("Secret milestone", "71", "private note", "Badge X"):
        assert leaked not in body
    assert "https://e/dash" in body
