"""Iter 91 — Dispute Resolution Pathway Report.

Covers the deterministic scoring engine in `pathway_report.py`. The
priority test is #1 (safety hard-lock never mutualises abuse) — the
whole product commitment rides on it.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")

from pathway_report import (  # noqa: E402
    DualPartyContext, PATHWAYS, PATHWAY_ORDER, SinglePartyContext,
    score_pathway_dual, score_pathway_single,
)


def _neutral_party(**overrides) -> SinglePartyContext:
    """Baseline: mostly-functional parent with no red flags."""
    defaults = dict(
        safety_level=5,                         # least restrictive
        safety_pathway_title="Cooperative",
        safety_coercive_trigger=False,
        safety_physical_trigger=False,
        dim2_communication_tier="aligned",
        dim3_emotional_reg_tier="aligned",
        dim4_executive_fn_tier="aligned",
        nd_risk_tier="low",
        nd_risk_score=2,
        compliance_streak_weeks=3,
        compliance_current_pct=90.0,
    )
    defaults.update(overrides)
    return SinglePartyContext(**defaults)


# ---------------------------------------------------------------------------
# 1. Safety hard-lock — the ETHICAL ANCHOR of this feature.
# ---------------------------------------------------------------------------

def test_hard_lock_coercive_control_forces_litigation_only():
    p = _neutral_party(safety_coercive_trigger=True)
    r = score_pathway_single(p)
    assert r.primary_key == "litigation"
    # Mediation-shaped options must be explicitly NOT indicated.
    assert r.suitability["mediation"] == "not_indicated"
    assert r.suitability["child_centered_mediation"] == "low"
    assert r.suitability["collaborative_law"] == "low"
    assert r.suitability["litigation"] == "high"
    assert r.hard_locked_by
    # Reasoning surfaces the coercive-control trigger.
    joined = " ".join(r.factors + r.hard_locked_by).lower()
    assert "coercive" in joined


def test_hard_lock_physical_trigger_forces_litigation_only():
    p = _neutral_party(safety_physical_trigger=True)
    r = score_pathway_single(p)
    assert r.primary_key == "litigation"
    assert r.suitability["mediation"] == "not_indicated"
    assert any("physical" in x.lower() for x in r.hard_locked_by)


def test_hard_lock_safety_level_1_forces_litigation_only():
    p = _neutral_party(safety_level=1)
    r = score_pathway_single(p)
    assert r.primary_key == "litigation"
    assert r.suitability["mediation"] == "not_indicated"


def test_dual_party_hard_lock_from_either_side_forces_litigation():
    """The safest party's data must NEVER cancel out the at-risk party's
    trigger — hard-lock activates if EITHER parent tripped it."""
    ctx = DualPartyContext(
        parent_a=_neutral_party(),                              # safe side
        parent_b=_neutral_party(safety_coercive_trigger=True),  # coercive
        compare_alignment_pct=95.0,                             # even high align
        child_centered_alignment=95.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key == "litigation"
    assert r.suitability["mediation"] == "not_indicated"


def test_hard_lock_dual_is_survivor_safe_when_survivor_is_parent_a():
    """Same guarantee regardless of which position the survivor holds."""
    ctx = DualPartyContext(
        parent_a=_neutral_party(safety_coercive_trigger=True),
        parent_b=_neutral_party(),
        compare_alignment_pct=95.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key == "litigation"


# ---------------------------------------------------------------------------
# 2. Happy paths for each of the four pathways.
# ---------------------------------------------------------------------------

def test_pathway_mediation_when_everything_is_aligned_and_safe():
    ctx = DualPartyContext(
        parent_a=_neutral_party(),
        parent_b=_neutral_party(),
        compare_alignment_pct=88.0,
        child_centered_alignment=90.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key == "mediation"
    assert r.suitability["mediation"] == "high"


def test_pathway_child_centered_mediation_when_communication_or_emotional_strain():
    """Neither parent tripped a safety lock, but communication OR emotional
    reactivity is strained on one side — CCRM is the sweet spot."""
    ctx = DualPartyContext(
        parent_a=_neutral_party(dim2_communication_tier="strained"),
        parent_b=_neutral_party(dim3_emotional_reg_tier="strained"),
        compare_alignment_pct=55.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key == "child_centered_mediation"
    # Language guardrail — sample factor from the user's brief.
    joined = " ".join(r.factors).lower()
    assert "structured" in joined or "child-focused" in joined or "child focused" in joined


def test_pathway_collaborative_law_when_complexity_but_still_participatory():
    """Executive-function strain + high ND-risk on one side (still not
    critical) + moderate safety + high compare alignment (so CCRM's
    'reduced alignment' trigger doesn't fire) = collaborative law."""
    ctx = DualPartyContext(
        parent_a=_neutral_party(
            dim4_executive_fn_tier="strained",
            nd_risk_tier="high",
            nd_risk_score=10,
            safety_level=3,
        ),
        parent_b=_neutral_party(safety_level=3),
        compare_alignment_pct=80.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key == "collaborative_law"
    assert r.suitability["collaborative_law"] == "high"


def test_pathway_litigation_when_nd_critical_but_no_safety_lock():
    """ND-risk critical still routes to litigation even without a safety
    hard-lock (critical ND indicates coordination that a consensual
    process can't reliably handle)."""
    ctx = DualPartyContext(
        parent_a=_neutral_party(nd_risk_tier="critical", nd_risk_score=15,
                                dim3_emotional_reg_tier="strained"),
        parent_b=_neutral_party(),
        compare_alignment_pct=45.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key == "litigation"
    # NOT hard-locked — the reasoning is a soft signal, not a trigger.
    assert r.hard_locked_by == []


# ---------------------------------------------------------------------------
# 3. Structure / language guarantees.
# ---------------------------------------------------------------------------

def test_result_always_returns_all_four_pathways_in_stable_order():
    r = score_pathway_single(_neutral_party())
    d = r.to_public_dict()
    keys = [row["key"] for row in d["suitability_profile"]]
    assert keys == PATHWAY_ORDER
    for row in d["suitability_profile"]:
        assert row["suitability"] in {"high", "moderate", "low", "not_indicated"}


def test_single_party_result_flags_itself_as_preview():
    r = score_pathway_single(_neutral_party())
    assert r.is_dual_party is False
    joined = " ".join(r.considerations).lower()
    assert "preview" in joined
    assert "both parents" in joined


def test_dual_party_result_flags_itself_as_full():
    ctx = DualPartyContext(parent_a=_neutral_party(), parent_b=_neutral_party(),
                           compare_alignment_pct=80.0)
    r = score_pathway_dual(ctx)
    assert r.is_dual_party is True


def test_language_never_uses_prescriptive_you_should():
    """The product commitment: never say "you should mediate". Sweep every
    string field for the phrase."""
    forbidden = ("you should", "we recommend litigating", "you must",
                 "you are required")
    for setup in (
        _neutral_party(),
        _neutral_party(safety_coercive_trigger=True),
        _neutral_party(dim2_communication_tier="strained"),
        _neutral_party(nd_risk_tier="critical"),
    ):
        r = score_pathway_single(setup)
        blob = " ".join(
            r.factors + r.considerations + r.goals + r.hard_locked_by
            + [PATHWAYS[r.primary_key]["one_liner"]]
        ).lower()
        for phrase in forbidden:
            assert phrase not in blob, f"prescriptive phrase '{phrase}' found for {r.primary_key}"


def test_ties_break_toward_least_adversarial():
    """When two pathways tie, the algorithm must NOT nudge toward more
    adversarial territory than the data supports."""
    # Construct a case where mediation and ccrm tie on 'moderate' — the
    # tie-breaker should pick mediation (least adversarial).
    ctx = DualPartyContext(
        parent_a=_neutral_party(dim2_communication_tier="stretch"),
        parent_b=_neutral_party(dim2_communication_tier="stretch"),
        compare_alignment_pct=62.0,
    )
    r = score_pathway_dual(ctx)
    assert r.primary_key in {"mediation", "child_centered_mediation"}
    # If mediation is "moderate", it must win the tie.
    if r.suitability["mediation"] == r.suitability["child_centered_mediation"]:
        assert r.primary_key == "mediation"


# ---------------------------------------------------------------------------
# 4. Missing-data behaviour — conservative but never crashes.
# ---------------------------------------------------------------------------

def test_no_data_at_all_still_returns_valid_result():
    r = score_pathway_single(SinglePartyContext())
    # No safety data → algorithm defaults to safe-side treatment (worst_safety=5)
    d = r.to_public_dict()
    assert d["primary_pathway_key"] in PATHWAY_ORDER
    assert d["primary_pathway_label"]
    assert len(d["suitability_profile"]) == 4
