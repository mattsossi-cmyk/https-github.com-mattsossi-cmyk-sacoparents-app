"""Iter 110 — Coparenting Feasibility Spectrum (Phase 2).

Locks the 6-tier arrangement recommender on Finding 3. Explicit
threshold cases the test suite must protect:

    * Level 4 with no gap items + no typology       -> cooperative
    * Level 3 with no gap items                     -> structured
    * Level 2 (coercive_hits)                       -> parallel
    * Level 2 + coercive_controlling typology        -> parallel (floor)
    * violent_resistance typology                    -> parallel (never lower —
      structure is shaped by the underlying coercive pattern the answering
      parent is being protected FROM, not by their defensive conduct)
    * Level 1 (any high_concern hit)                 -> supervised_contact
    * s1_q19 strangulation pattern                   -> at least supervised_contact
    * s1_q22 digital surveillance                    -> at least supervised_exchanges
    * s1_q25 distinct homicide threat                -> suspended_contact
    * ce_q1 child directly harmed                    -> suspended_contact
    * Every tier includes a review-point cadence + escalation-triggers list
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/app/backend")

from feasibility_spectrum import recommend_tier, TIER_ORDER, TIER_META  # noqa: E402


def test_tier_metadata_shape():
    """Every tier has label + narrative + structure_words + order."""
    assert set(TIER_META.keys()) == set(TIER_ORDER)
    for name, meta in TIER_META.items():
        assert meta.get("label")
        assert meta.get("narrative")
        assert meta.get("structure_words")
        assert isinstance(meta.get("order"), int)


def test_cooperative_when_no_signals():
    r = recommend_tier(level=4, section_1={}, child_experience={}, pattern_typology="unclear")
    assert r["tier"] == "cooperative_coparenting"
    assert r["order"] == 6
    assert r["triggers"] == []
    assert r["review_point_days"] == 365


def test_structured_baseline_from_level_3():
    r = recommend_tier(level=3, section_1={}, pattern_typology="situational")
    assert r["tier"] == "structured_coparenting"


def test_parallel_when_level_2():
    r = recommend_tier(level=2, section_1={})
    assert r["tier"] == "parallel_parenting"


def test_coercive_controlling_typology_forces_parallel_floor():
    """Even if the base level would be 3 (structured), a
    coercive_controlling typology floors the tier at parallel."""
    r = recommend_tier(level=3, section_1={}, pattern_typology="coercive_controlling")
    assert r["tier"] == "parallel_parenting"
    assert r["typology_floor"] == "parallel_parenting"


def test_violent_resistance_defaults_to_parallel_never_lower():
    r = recommend_tier(level=4, section_1={}, pattern_typology="violent_resistance")
    assert r["tier"] == "parallel_parenting"
    # And a caveat explains the reframing.
    joined = " ".join(r["caveats"]).lower()
    assert "violent-resistance" in joined or "self-protective" in joined
    assert "defensive" in joined or "answering parent" in joined


def test_strangulation_pattern_pushes_supervised_contact():
    r = recommend_tier(level=4, section_1={"s1_q19": "yes"})
    assert r["tier"] == "supervised_contact"
    assert "s1_q19" in r["triggers"]


def test_digital_surveillance_pushes_supervised_exchanges():
    r = recommend_tier(level=4, section_1={"s1_q22": "yes"})
    assert r["tier"] == "supervised_exchanges"
    assert "s1_q22" in r["triggers"]


def test_homicide_threat_suspends_contact():
    r = recommend_tier(level=4, section_1={"s1_q25": "yes"})
    assert r["tier"] == "suspended_contact"
    assert "s1_q25" in r["triggers"]
    assert r["review_point_days"] == 30


def test_child_direct_harm_suspends_contact():
    r = recommend_tier(level=4, section_1={}, child_experience={"ce_q1": "yes"})
    assert r["tier"] == "suspended_contact"
    assert "ce_q1" in r["triggers"]


def test_multiple_triggers_pick_most_structured():
    """When several triggers fire, the MOST structured tier wins."""
    r = recommend_tier(
        level=2,
        section_1={"s1_q22": "yes", "s1_q19": "yes", "s1_q25": "yes"},
        pattern_typology="coercive_controlling",
    )
    assert r["tier"] == "suspended_contact"
    assert set(r["triggers"]) >= {"s1_q19", "s1_q22", "s1_q25"}


def test_tier_order_is_stable_from_most_to_least_restrictive():
    assert TIER_ORDER[0] == "suspended_contact"
    assert TIER_ORDER[-1] == "cooperative_coparenting"


def test_recommend_tier_returns_review_days_matching_tier():
    """Review-point cadence: tighter tier -> shorter window."""
    tighter = recommend_tier(level=1, section_1={"s1_q25": "yes"})
    looser = recommend_tier(level=4, section_1={})
    assert tighter["review_point_days"] < looser["review_point_days"]
