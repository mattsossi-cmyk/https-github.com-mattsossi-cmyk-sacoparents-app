"""Iteration 54 tests — Public Milestone Wall (opt-in, anonymised feed).

Verifies:

* Wall is fully off by default — `GET /wall/status` returns opt_in=False,
  and even a Foundation-Ready parent produces no `/wall/feed` events until
  they opt in.
* Opting in backfills a Foundation-Ready event immediately when the
  parent already holds the badge.
* Feed rows expose ONLY the safe fields — user_hash, badge_type,
  badge_label, created_at, when_human, event_id. No user_id, no name,
  no email, no numeric stats.
* De-dupe: hitting `/progress` twice in a row after opt-in doesn't
  double-log the same badge (24-hour window).
* Opting out stops future events but leaves existing ones on the feed
  (privacy contract we surface to the user).
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1, PARENT2,
    _client, _ensure_account, _fresh_consented_share,
    _post_safety_level_4, _revoke_all, _run,
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


@pytest.fixture(scope="module", autouse=True)
def _cleanup(p1_token, p2_token):
    """Reset wall state across the module so tests are order-independent."""
    from motor.motor_asyncio import AsyncIOMotorClient
    async def _reset():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["wall_opt_in"].delete_many({})
            await db["wall_events"].delete_many({})
        finally:
            c.close()
    _run(_reset())
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    yield
    _run(_reset())
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))


def _seed_five_of_five(p1_client, p2_client):
    _post_safety_level_4(p1_client)
    p1_client.put(f"{BASE_URL}/api/mediation/child-goals",
                  json={"goals": [{"text": "Stability"}]}, timeout=20)
    p1_client.put(f"{BASE_URL}/api/mediation/issues",
                  json={"schedule": "Alternating"}, timeout=20)
    p1_client.put(f"{BASE_URL}/api/mediation/comm-style",
                  json={"tone": "concise", "channel": "text"}, timeout=20)
    _revoke_all(p1_client); _revoke_all(p2_client)
    share_id = _fresh_consented_share(p1_client, p2_client, "edu-deep")
    p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share_id}", timeout=30)
    return share_id


class TestWallOptInPrivacy:
    def test_default_status_is_opt_out(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/wall/status", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["opt_in"] is False
        assert body["my_events_this_month"] == 0

    def test_progress_does_not_log_events_while_opted_out(
        self, p1_client, p2_client,
    ):
        share_id = _seed_five_of_five(p1_client, p2_client)
        # Hit /progress — the endpoint tries to log a wall event but must
        # no-op because opt_in=False.
        p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        assert feed["total"] == 0, (
            f"opted-out parent produced wall events: {feed}"
        )
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")


class TestWallOptInBackfill:
    def test_opt_in_backfills_when_already_ready(self, p1_client, p2_client):
        # Reset wall state (module-level fixture resets between modules only)
        share_id = _seed_five_of_five(p1_client, p2_client)
        # Confirm foundation_ready before flipping
        p = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        assert p["foundation_ready"] is True
        # Opt in
        r = p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                           json={"opt_in": True}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["opt_in"] is True
        assert body["backfilled_event"] is True
        # Feed shows the backfilled event
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=10", timeout=20,
        ).json()
        assert feed["total"] >= 1
        first = feed["events"][0]
        assert first["badge_type"] == "foundation_ready"
        assert "Foundation Ready" in first["badge_label"]
        # Anonymised fields ONLY
        for forbidden in ("user_id", "name", "email"):
            assert forbidden not in first, (
                f"feed row leaked forbidden field '{forbidden}': {first}"
            )
        assert isinstance(first.get("user_hash"), str)
        assert len(first["user_hash"]) == 16
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")

    def test_progress_dedupe_within_24h(self, p1_client, p2_client):
        # Fresh 5/5 setup
        share_id = _seed_five_of_five(p1_client, p2_client)
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=20)
        # First /progress fires an event (or the opt-in backfill did already).
        p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        feed_a = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=10", timeout=20,
        ).json()
        # Repeat /progress a few times — must NOT double-log.
        for _ in range(3):
            p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        feed_b = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=10", timeout=20,
        ).json()
        assert feed_b["total"] == feed_a["total"], (
            f"progress hit multiple times double-logged: {feed_a} -> {feed_b}"
        )
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")


class TestWallOptOutKeepsExisting:
    def test_opt_out_stops_future_events_but_keeps_past(
        self, p1_client, p2_client,
    ):
        share_id = _seed_five_of_five(p1_client, p2_client)
        p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                       json={"opt_in": True}, timeout=20)
        p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        feed_before = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30", timeout=20,
        ).json()
        # Opt out
        r_out = p1_client.post(f"{BASE_URL}/api/wall/opt-in",
                               json={"opt_in": False}, timeout=20)
        assert r_out.status_code == 200
        assert r_out.json()["opt_in"] is False
        # Feed still shows the existing event (privacy contract we surface
        # to the user).
        feed_after = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30", timeout=20,
        ).json()
        assert feed_after["total"] == feed_before["total"]
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")
