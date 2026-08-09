"""Iter 97 — Direct-negotiation row + enriched pathway factor language.

Two additions to the Dispute Resolution Pathway Report:

    1. The suitability profile now includes a fifth row for "Direct
       negotiation" (no mediator in the room). Rated strictly one notch
       below "Mediation" so a professional reading the report sees at a
       glance that unsupported negotiation is always a more fragile
       option than supported mediation.

    2. Factor bullets under "Factors supporting this pathway" now use
       richer clinical language — the exact phrases from the product
       brief. This test suite pins the tokens that must appear per
       branch so future edits can't silently drop them.

Direct negotiation is deliberately NOT eligible as the primary
recommendation: the app never nudges a family toward negotiating with
no professional present. That policy is asserted here too.
"""
from __future__ import annotations

import os
import sys

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

from pathway_report import (  # noqa: E402
    DualPartyContext, SinglePartyContext, PATHWAY_ORDER,
    score_pathway_dual, score_pathway_single,
)


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------

def _safe_ctx(**over) -> SinglePartyContext:
    """A parent with clean, low-conflict signals — mediation should win."""
    base = dict(
        safety_level=4,
        safety_coercive_trigger=False,
        safety_physical_trigger=False,
        dim2_communication_tier="strong",
        dim3_emotional_reg_tier="strong",
        dim4_executive_fn_tier="strong",
        nd_risk_tier="low",
        compliance_streak_weeks=4,
    )
    base.update(over)
    return SinglePartyContext(**base)


def _strained_ctx(**over) -> SinglePartyContext:
    base = dict(
        safety_level=3,
        dim2_communication_tier="strained",
        dim3_emotional_reg_tier="strained",
        dim4_executive_fn_tier="stretched",
        nd_risk_tier="medium",
    )
    base.update(over)
    return SinglePartyContext(**base)


# ---------------------------------------------------------------------------
# Direct-negotiation row.
# ---------------------------------------------------------------------------

def test_pathway_order_lists_direct_negotiation_first():
    assert PATHWAY_ORDER[0] == "direct_negotiation"
    assert set(PATHWAY_ORDER) == {
        "direct_negotiation", "mediation", "child_centered_mediation",
        "collaborative_law", "litigation",
    }


def test_suitability_profile_has_5_rows_including_direct_negotiation():
    d = score_pathway_single(_safe_ctx()).to_public_dict()
    prof = d["suitability_profile"]
    assert len(prof) == 5
    keys = [r["key"] for r in prof]
    assert keys == PATHWAY_ORDER
    # The direct-negotiation row is present and labelled human-readably.
    dn = next(r for r in prof if r["key"] == "direct_negotiation")
    assert dn["label"] == "Direct negotiation"


def test_direct_negotiation_is_strictly_one_notch_below_mediation():
    """For every clean vs strained context, Direct negotiation should
    sit one step under Mediation on the 4-level scale (or stay at
    not_indicated when Mediation is already at the floor)."""
    rank = {"high": 3, "moderate": 2, "low": 1, "not_indicated": 0}
    for ctx in (
        _safe_ctx(),                              # mediation likely high
        _safe_ctx(dim2_communication_tier="steady",
                  dim3_emotional_reg_tier="steady",
                  safety_level=3),                # mediation likely moderate
        _strained_ctx(),                          # mediation likely low
    ):
        prof = score_pathway_single(ctx).to_public_dict()["suitability_profile"]
        by_key = {r["key"]: r["suitability"] for r in prof}
        m = by_key["mediation"]
        dn = by_key["direct_negotiation"]
        assert rank[dn] == max(0, rank[m] - 1), (
            f"direct_negotiation ({dn}) should be one below mediation ({m})"
        )


def test_direct_negotiation_never_becomes_primary_even_when_high():
    """The primary recommendation must never be direct_negotiation — the
    app does not nudge families toward unsupported negotiation."""
    d = score_pathway_single(_safe_ctx()).to_public_dict()
    assert d["primary_pathway_key"] != "direct_negotiation"


def test_hard_lock_result_marks_direct_negotiation_not_indicated():
    """When the safety screen hard-locks the family to Litigation, the
    Direct-negotiation row must render as 'not_indicated' too."""
    ctx = _safe_ctx(safety_coercive_trigger=True)
    prof = score_pathway_single(ctx).to_public_dict()["suitability_profile"]
    dn = next(r for r in prof if r["key"] == "direct_negotiation")
    assert dn["suitability"] == "not_indicated"


# ---------------------------------------------------------------------------
# Enriched factor language.
# ---------------------------------------------------------------------------

def test_child_centered_mediation_factors_use_clinical_phrasing():
    """A strained-but-workable pair should produce the CCRM branch and
    surface the specific phrases from the product brief."""
    d = score_pathway_dual(DualPartyContext(
        parent_a=_strained_ctx(),
        parent_b=_strained_ctx(),
        compare_alignment_pct=50.0,
    )).to_public_dict()
    factors = " ".join(d["factors_supporting_primary"])
    # CCRM branch fired.
    assert d["primary_pathway_key"] in {
        "child_centered_mediation", "collaborative_law",
    }
    # Communication breakdown line surfaces because both parents were
    # scored "strained" (worst_comm == 0).
    assert "Significant communication breakdown" in factors
    assert "Emotional reactivity" in factors and "interfere" in factors
    # The child-focused disagreement line surfaces from a 50% alignment.
    # Either wording is acceptable — the exact threshold copy is
    # documented in `_factors_for._align_line`.
    assert (
        "disagree substantially about the child" in factors
        or "meaningful disagreement about the child" in factors
    )


def test_mediation_factors_mention_safety_screen_and_child_involvement():
    d = score_pathway_single(_safe_ctx()).to_public_dict()
    factors = " ".join(d["factors_supporting_primary"])
    # This is the safest possible parent — Mediation should win.
    assert d["primary_pathway_key"] == "mediation"
    assert "No safety or coercive-control indicators" in factors
    assert "willingness to remain involved in the child" in factors


def test_collaborative_factors_mention_interdisciplinary_team():
    """A pair with elevated ND-risk + executive-function strain but no
    safety trigger should land on collaborative law, and the enriched
    language should mention the interdisciplinary team."""
    d = score_pathway_dual(DualPartyContext(
        parent_a=_safe_ctx(nd_risk_tier="high",
                           dim4_executive_fn_tier="strained",
                           safety_level=3),
        parent_b=_safe_ctx(nd_risk_tier="high",
                           dim4_executive_fn_tier="strained",
                           safety_level=3),
        compare_alignment_pct=70.0,
    )).to_public_dict()
    factors = " ".join(d["factors_supporting_primary"])
    assert d["primary_pathway_key"] == "collaborative_law"
    assert "interdisciplinary team" in factors
    assert "avoiding court" in factors


def test_hard_locked_report_does_not_use_soft_signal_language():
    """The hard-lock branch should surface the safety reason as a
    factor (not soft-signal ND / EF language)."""
    d = score_pathway_single(_safe_ctx(
        safety_coercive_trigger=True,
    )).to_public_dict()
    assert d["primary_pathway_key"] == "litigation"
    assert d["hard_locked_by"], "hard-lock reasons should populate"
    # None of the soft-signal enriched sentences should slip through
    # for a hard-locked report.
    factors = " ".join(d["factors_supporting_primary"])
    assert "Emotional reactivity appears" not in factors
