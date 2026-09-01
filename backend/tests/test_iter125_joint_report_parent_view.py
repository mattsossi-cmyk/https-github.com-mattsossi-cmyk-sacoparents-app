"""iter125 · Joint Report parent-friendly 5-bucket view (Phase 2).

Unit test for the composition function `build_joint_report` — asserts
that the new `parent_view` block ships with 5 named buckets in the
correct order and shape, and that content flows from the underlying
clinical sections into the friendly buckets.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from joint_professional_report import build_joint_report


def _minimal_comparison():
    """A tiny SNC v2 comparison payload with a mix of aligned + divergent."""
    return {
        "shared_pathways": ["medical", "educational"],
        "steps": [],
        "highlights": [],
        "summary": {
            "total_items": 4, "aligned_pct": 50, "divergent_pct": 50,
            "counts": {"aligned": 2, "close": 0, "divergent": 2, "one_only": 0},
        },
    }


def test_parent_view_ships_five_named_buckets():
    """The `parent_view` block must contain exactly the 5 keys in the
    order the frontend renders them."""
    report = build_joint_report(
        parent_a_name="Alex", parent_b_name="Blake", share_id="sh_1",
        comparison=_minimal_comparison(),
        prep_a={"priority": {"top_items": [{"label": "consistency"}]}},
        prep_b={"priority": {"top_items": [{"label": "consistency"}]}},
    )
    pv = report["parent_view"]
    keys = list(pv.keys())
    assert keys == [
        "what_you_both_care_about",
        "where_you_see_things_differently",
        "what_may_need_attention",
        "options_to_consider",
        "questions_for_next_conversation",
    ]
    # Every bucket has the shape the frontend expects.
    for k, bucket in pv.items():
        assert "title" in bucket and bucket["title"], f"missing title on {k}"
        assert "description" in bucket, f"missing description on {k}"
        assert "items" in bucket, f"missing items on {k}"


def test_shared_priorities_flow_into_care_about_bucket():
    """Priorities both parents listed must surface in the alignment bucket."""
    report = build_joint_report(
        parent_a_name="Alex", parent_b_name="Blake", share_id="sh_2",
        comparison=_minimal_comparison(),
        prep_a={"child_goals": {"selected_goals": [
            "consistency across homes", "medical coordination",
        ]}},
        prep_b={"child_goals": {"selected_goals": [
            "consistency across homes", "medical coordination",
        ]}},
    )
    bucket = report["parent_view"]["what_you_both_care_about"]
    combined = " ".join((it.get("text") or "").lower() for it in bucket["items"])
    assert "consistency" in combined
    assert "medical" in combined
    assert bucket["shared_pathways"] == ["medical", "educational"]


def test_options_bucket_always_offers_the_generic_professional_option():
    """Even with no differences, we always offer the safe generic
    'bring this to a professional' option."""
    report = build_joint_report(
        parent_a_name="Alex", parent_b_name="Blake", share_id="sh_3",
        comparison={
            "shared_pathways": [], "steps": [], "highlights": [],
            "summary": {"total_items": 0, "aligned_pct": 0, "divergent_pct": 0, "counts": {}},
        },
        prep_a={}, prep_b={},
    )
    options = report["parent_view"]["options_to_consider"]["items"]
    titles = [o["title"].lower() for o in options]
    assert any("professional" in t for t in titles)


def test_questions_bucket_always_closes_with_a_next_step_question():
    report = build_joint_report(
        parent_a_name="Alex", parent_b_name="Blake", share_id="sh_4",
        comparison=_minimal_comparison(),
        prep_a={"priority": {"top_items": [{"label": "consistency"}]}},
        prep_b={"priority": {"top_items": [{"label": "communication"}]}},
    )
    questions = report["parent_view"]["questions_for_next_conversation"]["items"]
    assert questions, "must always include at least one question"
    assert questions[-1]["topic"].lower() == "next step"
    assert "mediator" in questions[-1]["question"].lower()


def test_sections_still_present_for_detailed_comparison_appendix():
    """The 9 clinical sections must still ship so the row-strip
    'Detailed Comparison' appendix can render below the parent view."""
    report = build_joint_report(
        parent_a_name="Alex", parent_b_name="Blake", share_id="sh_5",
        comparison=_minimal_comparison(),
        prep_a={}, prep_b={},
    )
    assert set(report["sections"].keys()) == {
        "shared_priorities", "medical", "educational", "psychological",
        "household_consistency", "communication_concerns",
        "areas_of_agreement", "areas_where_perceptions_differ",
        "issues_for_professional_discussion",
    }
