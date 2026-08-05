"""Iteration 52 tests — Section Coach on Report + Foundation Ready Celebration.

The Section Coach on the report is a pure frontend integration — it reuses
the existing `POST /section/{id}/coach` endpoint (already covered by iter-51
tests) plus a new frontend strip. We verify here that:

  1. The pathway schema endpoint returns the sections the strip iterates.
  2. Cached coach cards persist across pathway route calls so revisiting the
     report doesn't re-hit the LLM for sections the parent already coached
     during the assessment.

The Foundation Ready Celebration is triggered when
`GET /api/dashboard/progress` returns `completed_count == total`. We verify
that field transitions from < total to == total when a user seeds a
consented high-alignment compare, which is the last pill.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1, PARENT2,
    _client, _ensure_account, _fresh_consented_share,
    _post_safety_level_4, _revoke_all,
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
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    yield
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))


# ===========================================================================
# SECTION COACH ON THE REPORT — schema iteration + cache stability
# ===========================================================================
class TestReportSectionCoachStripSource:
    """The strip iterates `GET /api/{prefix}/schema`. Each pathway must
    return a non-empty list of sections with the fields the strip reads."""

    @pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep", "med-deep"])
    def test_schema_returns_section_list_for_strip(self, p1_client, prefix):
        r = p1_client.get(f"{BASE_URL}/api/{prefix}/schema", timeout=20)
        assert r.status_code == 200, r.text
        sections = r.json().get("sections") or []
        assert len(sections) >= 3, f"{prefix}: expected ≥3 sections"
        for s in sections:
            assert isinstance(s.get("id"), str), f"{prefix}: section missing id"
            assert isinstance(s.get("number"), int), f"{prefix}: section missing number"
            assert isinstance(s.get("name"), str) and s["name"], (
                f"{prefix}: section missing name"
            )

    def test_cached_coach_survives_repeat_call(self, p1_client):
        """Because the report strip renders one SectionCoachCard per
        section, cached coach cards must be served without re-hitting the
        LLM. Fire twice and confirm cached=True on second call."""
        # Answer a couple of p1 items so the coach has content.
        r = p1_client.get(f"{BASE_URL}/api/edu-deep/schema", timeout=20)
        sections = r.json()["sections"]
        target_section = sections[0]           # first section, whatever it is
        sid = target_section["id"]
        answers = {}
        for it in target_section["items"]:
            key = f"{sid}_{it['id']}"
            t = it.get("type")
            if t in ("likert", "alignment"):
                scale = it.get("scale") or [1, 2, 3, 4, 5]
                answers[key] = max(scale) if scale else 5
            elif t == "single" and it.get("options"): answers[key] = it["options"][0]
            elif t == "multi" and it.get("options"): answers[key] = [it["options"][0]]
            elif t == "text": answers[key] = "Working on it."
        p1_client.post(f"{BASE_URL}/api/edu-deep/answers/bulk",
                       json={"answers": answers}, timeout=20)
        # First call generates, second should be cached.
        r1 = p1_client.post(f"{BASE_URL}/api/edu-deep/section/{sid}/coach",
                            json={}, timeout=120)
        assert r1.status_code == 200
        r2 = p1_client.post(f"{BASE_URL}/api/edu-deep/section/{sid}/coach",
                            json={}, timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("cached") is True


# ===========================================================================
# FOUNDATION READY CELEBRATION — completed_count reaches total (5)
# ===========================================================================
class TestFoundationReadyTrigger:
    """The celebration fires when the progress endpoint reports
    `completed_count == total`. It's a pure frontend visual — the test
    verifies the *server-side* signal it depends on transitions to 5/5
    after a consented high-alignment compare is created."""

    def test_five_of_five_after_high_alignment_compare(
        self, p1_client, p2_client,
    ):
        # Seed the four non-compare pills.
        _post_safety_level_4(p1_client)
        p1_client.put(f"{BASE_URL}/api/mediation/child-goals",
                      json={"goals": [{"text": "Stability"}]}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/issues",
                      json={"schedule": "Alternating"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/comm-style",
                      json={"tone": "concise", "channel": "text"}, timeout=20)

        # Before the compare, ensure we're at most 4/5.
        r_before = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        body_before = r_before.json()
        # Revoke any prior compare so we're deterministic.
        _revoke_all(p1_client)
        _revoke_all(p2_client)
        # Also clear stray snapshots so alignment history doesn't pre-fire.
        from motor.motor_asyncio import AsyncIOMotorClient
        from test_iter48_features import MONGO_URL, DB_NAME, _run
        async def _reset_snaps():
            c = AsyncIOMotorClient(MONGO_URL)
            try:
                db = c[DB_NAME]
                await db["deep_dive_compare_snapshots"].delete_many({})
            finally:
                c.close()
        _run(_reset_snaps())
        r_mid = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        assert r_mid["completed_count"] < r_mid["total"], (
            f"expected < total before compare; got: {r_mid}"
        )

        # Now seed a consented high-alignment compare and snapshot.
        share_id = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share_id}", timeout=30)

        r_after = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        assert r_after["completed_count"] == r_after["total"], (
            f"expected 5/5 after high-alignment compare; got: {r_after}"
        )
        # Alignment % is exposed so the celebration copy can quote it.
        assert r_after.get("alignment_pct") is not None
        assert r_after["alignment_pct"] >= 60
        # Cleanup
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")

        # Pre-existing 4/5 sanity — before-state doesn't matter but keep so
        # the test explains itself if the seed order ever changes.
        assert body_before is not None
