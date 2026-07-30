"""Unit tests for the SNC v2 comparison content builder."""
from __future__ import annotations

from snc2_comparison import ALIGNMENT_LABELS, build_comparison
from snc2_questions import qid


def _mk_answers(pathway: str, overrides: dict | None = None) -> dict:
    a = {
        qid("step1", pathway, "concern"): "Chronic asthma, needs daily meds.",
        qid("step1", pathway, "current_impact"): 4,
        qid("step1", pathway, "duration"): "1 to 3 years",
        qid("step1", pathway, "urgency"): "Needs attention within weeks",
        qid("step2", pathway, "current_needs"): ["Chronic medical condition", "Medication schedule"],
        qid("step2", pathway, "other_needs"): "",
        qid("step3", pathway, "professionals_seen"): ["Paediatrician"],
        qid("step3", pathway, "recommendations_text"): "Use inhaler morning + night.",
        qid("step3", pathway, "recs_written"): "Yes",
        qid("step3", pathway, "recs_understand"): 5,
        qid("step4", pathway, "same_info"): 4,
        qid("step4", pathway, "attend_appts"): 3,
        qid("step4", pathway, "discuss_openly"): 4,
        qid("step4", pathway, "shared_language"): 3,
        qid("step4", pathway, "believe_understood"): 4,
        qid("step5", pathway, "routines_consistent"): 3,
        qid("step5", pathway, "follow_recs"): 4,
        qid("step5", pathway, "share_updates"): 3,
        qid("step5", pathway, "carry_over_supplies"): 4,
        qid("step5", pathway, "handoffs_reliable"): 3,
        qid("step6", pathway, "agree_areas"): "Both agree meds are important.",
        qid("step6", pathway, "disagree_areas"): "",
        qid("step6", pathway, "biggest_gap"): "Different priorities",
        qid("step7", pathway, "practical_selected"): ["Shared calendar for medical appointments"],
        qid("step7", pathway, "practical_other"): "",
        qid("step8", pathway, "top_priority"): "Fill spacer prescription.",
        qid("step8", pathway, "next_meeting"): "Within 2 weeks",
        qid("step8", pathway, "professional_next"): "Follow up with pulmonologist.",
        qid("step8", pathway, "concerns_about_plan"): "",
    }
    if overrides:
        a.update(overrides)
    return a


def test_shared_pathways_are_intersection():
    a = _mk_answers("medical")
    b = _mk_answers("medical")
    b.update(_mk_answers("educational"))
    cmp = build_comparison(
        parent_a_name="Alice",
        parent_b_name="Ben",
        a_pathways=["medical"],
        b_pathways=["medical", "educational"],
        a_answers=a,
        b_answers=b,
    )
    assert cmp["shared_pathways"] == ["medical"]
    assert cmp["only_parent_a_pathways"] == []
    assert cmp["only_parent_b_pathways"] == ["educational"]


def test_likert_alignment_bands():
    a = _mk_answers("medical")
    b = _mk_answers("medical", {
        qid("step1", "medical", "current_impact"): 4,  # same -> aligned
        qid("step4", "medical", "same_info"): 3,       # 1 gap -> aligned
        qid("step4", "medical", "attend_appts"): 5,    # 2 gap -> close
        qid("step4", "medical", "discuss_openly"): 1,  # 3 gap -> divergent
    })
    cmp = build_comparison(
        parent_a_name="A", parent_b_name="B",
        a_pathways=["medical"], b_pathways=["medical"],
        a_answers=a, b_answers=b,
    )
    items_by_id = {}
    for step in cmp["steps"]:
        for p in step["pathways"]:
            for it in p["items"]:
                items_by_id[(step["id"], it["id"])] = it
    assert items_by_id[("step1", "current_impact")]["alignment"] == "aligned"
    assert items_by_id[("step4", "same_info")]["alignment"] == "aligned"
    assert items_by_id[("step4", "attend_appts")]["alignment"] == "close"
    assert items_by_id[("step4", "discuss_openly")]["alignment"] == "divergent"


def test_multi_intersection():
    a = _mk_answers("medical")
    b = _mk_answers("medical", {
        qid("step2", "medical", "current_needs"): ["Chronic medical condition", "Allergies or dietary restrictions"],
    })
    cmp = build_comparison(
        parent_a_name="A", parent_b_name="B",
        a_pathways=["medical"], b_pathways=["medical"],
        a_answers=a, b_answers=b,
    )
    items = {(s["id"], it["id"]): it for s in cmp["steps"] for p in s["pathways"] for it in p["items"]}
    node = items[("step2", "current_needs")]
    assert "Chronic medical condition" in node["both"]
    assert "Medication schedule" in node["only_parent_a"]
    assert "Allergies or dietary restrictions" in node["only_parent_b"]


def test_category_filter_restricts_output():
    a = _mk_answers("medical")
    a.update(_mk_answers("educational"))
    b = _mk_answers("medical")
    b.update(_mk_answers("educational"))
    cmp = build_comparison(
        parent_a_name="A", parent_b_name="B",
        a_pathways=["medical", "educational"],
        b_pathways=["medical", "educational"],
        a_answers=a, b_answers=b,
        category_filter="medical",
    )
    for step in cmp["steps"]:
        assert all(p["id"] == "medical" for p in step["pathways"])


def test_summary_counts_all_items():
    a = _mk_answers("medical")
    b = _mk_answers("medical")
    cmp = build_comparison(
        parent_a_name="A", parent_b_name="B",
        a_pathways=["medical"], b_pathways=["medical"],
        a_answers=a, b_answers=b,
    )
    total = sum(len(p["items"]) for s in cmp["steps"] for p in s["pathways"])
    assert cmp["summary"]["total_items"] == total
    # All Likert answers here match -> aligned should dominate
    assert cmp["summary"]["divergent_pct"] == 0


def test_alignment_labels_are_present():
    assert set(ALIGNMENT_LABELS.keys()) >= {
        "aligned", "close", "divergent", "both_responded", "one_only", "insufficient",
    }
