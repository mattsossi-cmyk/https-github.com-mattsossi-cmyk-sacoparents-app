"""Iteration 55 tests — Cheer Reactions + more badge types on the Wall.

New badge types
---------------
* `first_compare`         — logged when a compare share transitions to fully
                            consented (`status == "active"`). Lifetime badge:
                            only ever fires once per parent.
* `high_alignment_90`     — logged when a compare snapshot's aligned_pct ≥ 90.
                            24-hour de-dupe so viewing the same compare many
                            times doesn't spam the wall.
* `communication_master`  — logged when all 6 mediation-prep sections saved.
                            Lifetime badge.

Cheer reactions
---------------
* Only opted-in parents can cheer (mutual-consent contract).
* Self-cheer blocked (400).
* Feed returns `cheer_count` + `i_cheered` per event.
* Toggle: second POST removes the cheer and drops the count.
* Non-existent event returns 404.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from motor.motor_asyncio import AsyncIOMotorClient

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


def _reset_wall_state():
    async def _reset():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["wall_opt_in"].delete_many({})
            await db["wall_events"].delete_many({})
            await db["wall_cheers"].delete_many({})
        finally:
            c.close()
    _run(_reset())


@pytest.fixture(scope="module", autouse=True)
def _cleanup(p1_token, p2_token):
    _reset_wall_state()
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    yield
    _reset_wall_state()
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))


def _opt_in_both(p1_client, p2_client):
    p1_client.post(f"{BASE_URL}/api/wall/opt-in", json={"opt_in": True})
    p2_client.post(f"{BASE_URL}/api/wall/opt-in", json={"opt_in": True})


# ===========================================================================
# NEW BADGE TYPES
# ===========================================================================
class TestNewBadgeTypes:
    def test_first_compare_and_high_alignment_and_comm_master(
        self, p1_client, p2_client,
    ):
        _reset_wall_state()
        _revoke_all(p1_client); _revoke_all(p2_client)
        _opt_in_both(p1_client, p2_client)
        # Prep sections — all 6 for Communication Master
        _post_safety_level_4(p1_client)
        p1_client.put(f"{BASE_URL}/api/mediation/child-goals",
                      json={"goals": [{"text": "Stability"}]}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/issues",
                      json={"schedule": "Alternating"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/priority",
                      json={"top": ["schedule"]}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/comm-style",
                      json={"tone": "concise", "channel": "text"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/readiness",
                      json={"confidence": "high"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/reflection",
                      json={"open": "I want a calm room."}, timeout=20)
        # Consented compare → first_compare + snapshot → high_alignment (98%)
        share_id = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share_id}", timeout=30)
        # Progress → foundation_ready + communication_master
        p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        p2_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=30,
        ).json()
        seen = {ev["badge_type"] for ev in feed["events"]}
        for expected in ("first_compare", "high_alignment_90",
                         "foundation_ready", "communication_master"):
            assert expected in seen, (
                f"expected badge {expected} on the wall; got {sorted(seen)}"
            )
        # Labels populated for every event.
        for ev in feed["events"]:
            assert isinstance(ev.get("badge_label"), str)
            assert ev["badge_label"] and ev["badge_label"] != ev["badge_type"]
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")

    def test_first_compare_is_lifetime_badge(self, p1_client, p2_client):
        """After earning first_compare, revoking and re-consenting must NOT
        re-log the badge for the same parent."""
        _reset_wall_state()
        _revoke_all(p1_client); _revoke_all(p2_client)
        _opt_in_both(p1_client, p2_client)
        share_a = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        # Count events before second round.
        f_a = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=30,
        ).json()
        first_compare_count_a = sum(
            1 for e in f_a["events"] if e["badge_type"] == "first_compare"
        )
        assert first_compare_count_a >= 2, (
            f"expected first_compare badges for both parents; got {first_compare_count_a}"
        )
        # Revoke and re-consent
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_a}/revoke")
        share_b = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        f_b = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=30,
        ).json()
        first_compare_count_b = sum(
            1 for e in f_b["events"] if e["badge_type"] == "first_compare"
        )
        assert first_compare_count_b == first_compare_count_a, (
            "first_compare re-fired on a subsequent consent — should be a "
            f"lifetime badge. Before: {first_compare_count_a}, After: {first_compare_count_b}"
        )
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_b}/revoke")


# ===========================================================================
# CHEER REACTIONS
# ===========================================================================
class TestCheerReactions:
    def _get_event_from_other_parent(self, p1_client):
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        # Return the first event that isn't parent1's — parent1 self-cheer
        # blocks with 400 so we detect the "not mine" event that way.
        for ev in feed["events"]:
            r = p1_client.post(
                f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
            )
            if r.status_code == 200:
                # Un-cheer to leave state clean.
                p1_client.post(
                    f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
                )
                return ev
        return None

    def test_opted_out_parent_cannot_cheer(self, p1_client, p2_client):
        _reset_wall_state()
        _opt_in_both(p1_client, p2_client)
        share = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share}", timeout=30)
        # Grab one event
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        assert feed["events"], "expected at least one event"
        ev = feed["events"][0]
        # Opt p1 OUT and try to cheer — must 403 regardless of ownership.
        p1_client.post(f"{BASE_URL}/api/wall/opt-in", json={"opt_in": False})
        r = p1_client.post(
            f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share}/revoke")

    def test_self_cheer_blocked(self, p1_client, p2_client):
        _reset_wall_state()
        _opt_in_both(p1_client, p2_client)
        share = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share}", timeout=30)
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        # Find an event authored by p1 (self-cheer must 400). We detect it
        # by iterating until we hit a 400.
        got_self_400 = False
        for ev in feed["events"]:
            r = p1_client.post(
                f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
            )
            if r.status_code == 400:
                got_self_400 = True
                break
            # Not p1's — undo the cheer.
            p1_client.post(
                f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
            )
        assert got_self_400, "expected at least one self-cheer 400"
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share}/revoke")

    def test_cheer_toggles_count_and_i_cheered(self, p1_client, p2_client):
        _reset_wall_state()
        _opt_in_both(p1_client, p2_client)
        share = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share}", timeout=30)
        ev = self._get_event_from_other_parent(p1_client)
        assert ev is not None, "couldn't find an event owned by the other parent"
        # First cheer → cheered=True, count=1
        r1 = p1_client.post(
            f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
        ).json()
        assert r1 == {"ok": True, "cheered": True, "cheer_count": 1}
        # Feed reflects it
        feed = p1_client.get(
            f"{BASE_URL}/api/wall/feed?days=30&limit=50", timeout=20,
        ).json()
        target = next(e for e in feed["events"] if e["event_id"] == ev["event_id"])
        assert target["cheer_count"] == 1
        assert target["i_cheered"] is True
        # Second cheer toggles OFF
        r2 = p1_client.post(
            f"{BASE_URL}/api/wall/cheer/{ev['event_id']}", timeout=15,
        ).json()
        assert r2 == {"ok": True, "cheered": False, "cheer_count": 0}
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share}/revoke")

    def test_cheer_unknown_event_returns_404(self, p1_client, p2_client):
        _reset_wall_state()
        _opt_in_both(p1_client, p2_client)
        r = p1_client.post(
            f"{BASE_URL}/api/wall/cheer/wall_does_not_exist", timeout=15,
        )
        assert r.status_code == 404
