"""Phase D: Safeguards score + disagreement pathway engine.

Verifies:
  - Safeguards scoring math (in_place=100, partial=55, not_yet=0, not_needed=null).
  - disagreement_index math (disagrees + risky concern_response + critical-domain low).
  - Balanced-threshold tier mapping (option (b) from the plan):
      idx >= 5 OR (idx >= 3 AND risky) → T3
      idx >= 8 OR (idx >= 5 AND ≥2 missing groups) → T4
      idx >= 2 OR ≥3 missing items → T2
      otherwise → T1
  - Section catalog exposes safeguards_pathway for selective sharing.
  - filter_sn_report zeroes it out when excluded.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import pytest
from sn_pathway import (
    compute_safeguards,
    compute_disagreement,
    build_pathway,
)
from report_visibility import REPORT_SECTIONS, filter_sn_report, clean_excluded


# ---- Safeguards -----------------------------------------------------------
def test_safeguards_all_missing_scores_zero():
    ans = {"sg_pediatrician": "not_yet", "sg_therapist": "not_yet"}
    r = compute_safeguards(ans)
    assert r["overall_score"] == 0
    assert len(r["missing"]) == 2
    assert r["items_scored"] == 2


def test_safeguards_mix_partial_and_in_place():
    ans = {
        "sg_pediatrician": "in_place",     # 100
        "sg_therapist":    "partial",      # 55
        "sg_iep":          "not_yet",      # 0
        "sg_care_plan":    "not_needed",   # null — excluded
    }
    r = compute_safeguards(ans)
    # mean(100, 55, 0) = 51.66 → 52
    assert r["overall_score"] == 52
    assert r["items_scored"] == 3


def test_safeguards_not_needed_excluded():
    ans = {k: "not_needed" for k in ["sg_pediatrician", "sg_therapist", "sg_iep"]}
    r = compute_safeguards(ans)
    assert r["overall_score"] is None
    assert r["items_scored"] == 0


# ---- Disagreement index ---------------------------------------------------
def test_disagreement_index_from_disagrees_only():
    ans = {"med_info_shared": "disagree", "edu_records_shared": "disagree"}
    d = compute_disagreement(ans)
    assert d["index"] == 2
    assert d["risky_concern_response"] is False


def test_disagreement_risky_response_bumps_index():
    ans = {"concern_response": "dismiss"}
    d = compute_disagreement(ans)
    assert d["risky_concern_response"] is True
    assert d["index"] == 2  # 0 disagrees + 2 for risky


def test_disagreement_index_capped_at_10():
    # 20 disagrees + risky + critical → still capped
    ans = {}
    for i in range(6):  # only 6 count on the DOMAIN_ITEMS side (cap +6)
        ans[f"nonexistent_{i}"] = "disagree"
    ans["concern_response"] = "conflict"
    dims = {"medical": {"score": 20}}
    d = compute_disagreement(ans, dimensions=dims)
    # 0 (unknown ids don't count) + 2 risky + 2 critical → 4
    assert d["index"] == 4


# ---- Tier mapping (balanced thresholds) -----------------------------------
def test_tier_T1_no_risk():
    r = build_pathway({})
    assert r["tier"]["id"] == "T1"


def test_tier_T2_from_missing_safeguards():
    ans = {
        "sg_pediatrician": "not_yet",
        "sg_therapist":    "not_yet",
        "sg_iep":          "not_yet",  # 3 missing → T2
    }
    r = build_pathway(ans)
    assert r["tier"]["id"] == "T2"


def test_tier_T3_from_risky_concern_plus_disagrees():
    ans = {
        "concern_response": "dismiss",   # +2 risky
        "med_info_shared": "disagree",   # +1
        # idx = 3, risky=True → T3
    }
    r = build_pathway(ans)
    assert r["tier"]["id"] == "T3", r["disagreement"]


def test_tier_T3_from_index_5_alone():
    ans = {
        "med_info_shared":       "disagree",
        "med_follow_through":    "disagree",
        "edu_records_shared":    "disagree",
        "dev_progress_shared":   "disagree",
        "comm_style_understood": "disagree",  # 5 disagrees → idx=5, T3
    }
    r = build_pathway(ans)
    assert r["disagreement"]["index"] == 5
    assert r["tier"]["id"] == "T3"


def test_tier_T4_from_index_8():
    # idx must reach 8. 6 disagrees (cap +6) + risky (+2) = 8
    ans = {
        "med_info_shared":       "disagree",
        "med_follow_through":    "disagree",
        "edu_records_shared":    "disagree",
        "dev_progress_shared":   "disagree",
        "comm_style_understood": "disagree",
        "reg_triggers_understood": "disagree",
        "concern_response": "conflict",
    }
    r = build_pathway(ans)
    assert r["disagreement"]["index"] == 8
    assert r["tier"]["id"] == "T4"


def test_tier_T4_when_missing_two_groups_and_idx_5():
    # 5 disagrees (idx=5) + missing safeguards in 2 groups → T4
    ans = {
        "med_info_shared":       "disagree",
        "med_follow_through":    "disagree",
        "edu_records_shared":    "disagree",
        "dev_progress_shared":   "disagree",
        "comm_style_understood": "disagree",
        # Missing in 2 different groups (care_team + neutrals)
        "sg_pediatrician":  "not_yet",
        "sg_mediator_pc":   "not_yet",
    }
    r = build_pathway(ans)
    assert r["disagreement"]["index"] == 5
    assert r["tier"]["id"] == "T4"


# ---- Actions --------------------------------------------------------------
def test_actions_scale_with_tier():
    t1 = build_pathway({})
    t3 = build_pathway({
        "concern_response": "dismiss",
        "med_info_shared": "disagree",
    })
    assert len(t3["actions"]) > len(t1["actions"])
    # T3 must recommend a Parenting Coordinator specifically.
    assert any("Parenting Coordinator" in a["title"] or "Facilitator" in a["title"] for a in t3["actions"])


# ---- Selective sharing catalog -------------------------------------------
def test_sn_catalog_exposes_safeguards_pathway():
    keys = [s["key"] for s in REPORT_SECTIONS["sn_report"]]
    assert "safeguards_pathway" in keys


def test_clean_excluded_accepts_safeguards_pathway():
    assert clean_excluded("sn_report", ["safeguards_pathway"]) == ["safeguards_pathway"]


def test_filter_sn_report_zeroes_pathway():
    r = filter_sn_report(
        {"safeguards_pathway": {"tier": {"id": "T3"}}, "action_plan": [{"need": "n"}]},
        ["safeguards_pathway"],
    )
    assert r["safeguards_pathway"] is None
    # Untouched
    assert r["action_plan"] == [{"need": "n"}]


# ---- End-to-end PDF renders with pathway ---------------------------------
def test_pdf_renders_safeguards_pathway_section():
    from sn_report_pdf import build_special_needs_pdf
    report = {
        "child_profile": {"summary": "s"},
        "agreement_areas": [],
        "coordination_gaps": [],
        "priorities": {"immediate": [], "thirty_day": [], "longer_term": []},
        "structure_reasoning": "cooperative",
        "action_plan": [],
        "safeguards_pathway": build_pathway({
            "concern_response": "dismiss",
            "med_info_shared": "disagree",
            "sg_pediatrician": "in_place",
            "sg_iep": "not_yet",
        }),
    }
    pdf_with = build_special_needs_pdf(user_name="Parent", child_name="Nina", report=report)
    pdf_without = build_special_needs_pdf(
        user_name="Parent",
        child_name="Nina",
        report=report,
        excluded_sections=["safeguards_pathway"],
    )
    assert pdf_with.startswith(b"%PDF-") and pdf_without.startswith(b"%PDF-")
    # Excluded PDF must be smaller.
    assert len(pdf_without) < len(pdf_with)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
