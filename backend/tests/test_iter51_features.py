"""Iteration 51 tests — Progress Dashboard + AI Personal Coach.

Progress Dashboard  (GET /api/dashboard/progress)
-------------------------------------------------
Verifies the endpoint returns 5 pills with the correct signals for:
  * foundation_completed
  * child_needs_identified
  * communication_readiness
  * mediation_readiness
  * conflict_reduced

AI Personal Coach (POST /api/{prefix}/section/{section_id}/coach)
-----------------------------------------------------------------
Verifies:
  * Endpoint returns 200 with the correct 4-list JSON shape
  * Repeated calls with the same answers return `cached: True`
  * `force=True` bypasses the cache and re-generates
  * Unknown section_id returns 404

The coach test hits the real Claude API (via EMERGENT_LLM_KEY) — same
approach ai_summary already uses in existing regression tests. If the
LLM key isn't configured in the test environment we skip the coach
tests gracefully.
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1, PARENT2,
    _all_schema_keys, _bulk_and_complete, _client, _ensure_account,
    _fresh_consented_share, _post_safety_level_4, _revoke_all,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def p1_token():
    tok = _ensure_account(PARENT1)
    from ai_ready import accept_ai_notice
    accept_ai_notice(f"{BASE_URL}/api", {"Authorization": f"Bearer {tok}"})
    return tok


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
# PROGRESS DASHBOARD
# ===========================================================================
class TestProgressDashboardShape:
    """Shape + defaults."""

    def test_returns_all_five_pills(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("total") == 5
        pills = body.get("pills") or []
        assert len(pills) == 5
        expected_ids = {
            "foundation_completed", "child_needs_identified",
            "communication_readiness", "mediation_readiness",
            "conflict_reduced",
        }
        got_ids = {p["id"] for p in pills}
        assert got_ids == expected_ids, f"pill ids diverged: {got_ids}"
        # Every pill must be a boolean and carry a non-empty detail line.
        for p in pills:
            assert isinstance(p.get("done"), bool), f"pill {p['id']} done not bool"
            assert isinstance(p.get("label"), str) and p["label"]
            assert isinstance(p.get("detail"), str) and p["detail"]
        # completed_count matches
        assert body["completed_count"] == sum(1 for p in pills if p["done"])
        # Threshold constant surfaced
        assert body.get("alignment_threshold") == 60

    def test_foundation_and_readiness_after_setup(self, p1_client):
        """After posting the level-4 safety assessment + saving 3 prep
        sections, the corresponding pills should light up."""
        _post_safety_level_4(p1_client)
        # Save 3 prep sections so mediation_readiness lights up
        p1_client.put(f"{BASE_URL}/api/mediation/child-goals",
                      json={"goals": [{"text": "Stability across homes"}]}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/issues",
                      json={"schedule": "Alternating weeks"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/comm-style",
                      json={"tone": "concise", "channel": "text"}, timeout=20)
        r = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        body = r.json()
        by_id = {p["id"]: p for p in body["pills"]}
        assert by_id["foundation_completed"]["done"] is True, "safety+profile => foundation done"
        assert by_id["communication_readiness"]["done"] is True, "comm_style saved"
        assert by_id["mediation_readiness"]["done"] is True, "3+ sections saved"

    def test_conflict_reduced_flips_after_high_alignment_snapshot(
        self, p1_client, p2_client,
    ):
        """Seed both parents with identical answers, consent, view compare
        (which creates a snapshot). The pill should now report ≥60% and
        turn ✓."""
        share_id = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        # Fetch the comparison so a snapshot is stamped
        r = p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share_id}", timeout=30)
        assert r.status_code == 200, r.text
        r2 = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        body = r2.json()
        by_id = {p["id"]: p for p in body["pills"]}
        assert by_id["conflict_reduced"]["done"] is True, (
            f"identical answers should push alignment >=60%; got: {body}"
        )
        assert body.get("alignment_pct") is not None
        assert body.get("alignment_pct") >= 60
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")


# ===========================================================================
# AI PERSONAL COACH — Deep Dive sections
# ===========================================================================
_HAS_LLM_KEY = bool(os.environ.get("EMERGENT_LLM_KEY"))


@pytest.mark.skipif(not _HAS_LLM_KEY,
                    reason="EMERGENT_LLM_KEY not configured; skipping coach tests")
class TestSectionCoach:
    """Shape + cache + force refresh, driven over the real HTTP surface."""

    @pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep", "med-deep"])
    def test_coach_returns_four_lists(self, p1_client, prefix):
        # Ensure at least a couple of answers exist on section s1 so the
        # coach has something to reflect on. `_all_schema_keys` only covers
        # likert / single, so we top up with multi/text answers by hitting
        # the schema directly.
        r = p1_client.get(f"{BASE_URL}/api/{prefix}/schema", timeout=20)
        assert r.status_code == 200
        schema = r.json()
        # Educational / Psychological now use p1..p5 sections with 0-4 alignment items; Medical keeps s1.
        sid = schema["sections"][0]["id"]
        s1 = {}
        for s in schema.get("sections", []):
            if s.get("id") != sid:
                continue
            for item in s.get("items", []):
                key = f"{sid}_{item['id']}"
                t = item.get("type")
                if t in ("likert", "alignment"):
                    s1[key] = max(item.get("scale") or [5])
                elif t == "single":
                    opts = item.get("options") or []
                    if opts: s1[key] = opts[0]
                elif t == "multi":
                    opts = item.get("options") or []
                    if opts: s1[key] = [opts[0]]
                elif t == "text":
                    s1[key] = "Working on it."
        assert s1, f"{prefix}: no s1 answers seeded"
        _bulk_and_complete(p1_client, prefix, s1)
        r = p1_client.post(
            f"{BASE_URL}/api/{prefix}/section/{sid}/coach", json={}, timeout=120,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("section_id") == sid
        coach = body.get("coach") or {}
        for key in ("doing_well", "coordination_gaps", "next_steps", "resources"):
            assert key in coach, f"{prefix}: missing {key}"
            assert isinstance(coach[key], list), f"{prefix}: {key} not a list"
            # Per-item cap of 3 enforced
            assert len(coach[key]) <= 3, f"{prefix}: {key} exceeded cap"
        # Cache hash + timestamp populated on the fresh call
        assert body.get("answer_hash")
        assert body.get("generated_at")
        assert body.get("cached") in (True, False)

    def test_cache_hits_on_second_call(self, p1_client):
        r1 = p1_client.post(
            f"{BASE_URL}/api/edu-deep/section/p1/coach", json={}, timeout=120,
        )
        assert r1.status_code == 200
        r2 = p1_client.post(
            f"{BASE_URL}/api/edu-deep/section/p1/coach", json={}, timeout=30,
        )
        assert r2.status_code == 200
        assert r2.json().get("cached") is True, (
            f"expected cached=True on second call; got: {r2.json()}"
        )
        # Answer hashes must match between the two calls
        assert r1.json().get("answer_hash") == r2.json().get("answer_hash")

    def test_force_true_bypasses_cache(self, p1_client):
        r_cached = p1_client.post(
            f"{BASE_URL}/api/edu-deep/section/p1/coach", json={}, timeout=30,
        )
        assert r_cached.status_code == 200
        r_forced = p1_client.post(
            f"{BASE_URL}/api/edu-deep/section/p1/coach",
            json={"force": True}, timeout=120,
        )
        assert r_forced.status_code == 200
        assert r_forced.json().get("cached") is False, (
            f"expected cached=False when force=True; got: {r_forced.json()}"
        )

    def test_unknown_section_id_returns_404(self, p1_client):
        r = p1_client.post(
            f"{BASE_URL}/api/edu-deep/section/s9999/coach", json={}, timeout=30,
        )
        assert r.status_code == 404
