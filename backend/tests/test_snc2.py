"""Unit tests for the SNC v2 assessment framework."""
from __future__ import annotations

from snc2_questions import (
    ASSESSMENT_VERSION, PATHWAYS, build_schema, qid, resolve_pathways,
)
from snc2_scoring import compute_scores, validate_answer
from snc2_report_content import build_report
from snc2_report_pdf import build_snc2_pdf


def test_resolve_pathways_expands_multiple():
    assert resolve_pathways(["multiple"]) == ["medical", "educational", "psychological"]
    assert resolve_pathways(["medical", "educational"]) == ["medical", "educational"]
    assert resolve_pathways(["medical", "multiple"]) == ["medical", "educational", "psychological"]


def test_build_schema_returns_8_steps_per_pathway():
    schema = build_schema(["medical"])
    assert len(schema["steps"]) == 8
    assert schema["selected_pathways"] == ["medical"]
    # Step 1 pathway block has the medical-specific prompt.
    prompt = schema["steps"][0]["pathways"][0]["items"][0]["prompt"]
    assert "medical concern" in prompt.lower()


def test_build_schema_multiple_renders_all_three():
    schema = build_schema(["multiple"])
    for step in schema["steps"]:
        ids = [p["id"] for p in step["pathways"]]
        assert ids == ["medical", "educational", "psychological"]


def test_validate_answer_rules():
    assert validate_answer(qid("step4", "medical", "same_info"), 3)
    assert validate_answer(qid("step4", "medical", "same_info"), "na")
    assert not validate_answer(qid("step4", "medical", "same_info"), 7)
    assert not validate_answer(qid("step4", "medical", "same_info"), "yes")
    assert validate_answer(qid("step1", "medical", "urgency"), "Immediate / crisis")
    assert validate_answer(qid("step2", "medical", "current_needs"), ["Medication schedule"])
    assert not validate_answer("garbage_key", 1)


def _seed_answers():
    a = {}
    # Impact + coordination + understanding for medical
    a[qid("step1", "medical", "current_impact")] = 4
    for k in ("recs_understand",):
        a[qid("step3", "medical", k)] = 4
    for k in ("same_info", "attend_appts", "discuss_openly", "shared_language", "believe_understood"):
        a[qid("step4", "medical", k)] = 3
    for k in ("routines_consistent", "follow_recs", "share_updates", "carry_over_supplies", "handoffs_reliable"):
        a[qid("step5", "medical", k)] = 3
    return a


def test_scoring_produces_composite_bands():
    scores = compute_scores(["medical"], _seed_answers())
    med = scores["pathways"][0]
    assert med["understanding"]["score"] is not None
    assert med["coordination"]["score"] is not None
    assert med["impact"]["classification"] == "Notable reported impact"
    # All 3s → Coordination opportunity band
    assert med["coordination"]["classification"] == "Coordination opportunity"


def test_report_structure_matches_8_step_workflow():
    r = build_report(parent_name="P", child_name="K", selected_pathways=["medical"], answers=_seed_answers())
    assert r["assessment_version"] == ASSESSMENT_VERSION
    assert len(r["steps"]) == 8
    step_names = [s["name"] for s in r["steps"]]
    assert step_names == [
        "Understand the Concern",
        "Identify the Child's Current Needs",
        "Review Professional Recommendations",
        "Each Parent's Understanding",
        "Coordination Between Homes",
        "Agreement and Disagreement",
        "Practical Co-Parenting Options",
        "Create an Action Plan",
    ]
    # Each step has a pathway block with the 5-part pattern
    for s in r["steps"]:
        for pw in s["pathways"]:
            assert "response" in pw
            assert "finding" in pw
            assert "child_impact" in pw
            assert "suggested" in pw
            assert "action" in pw


def test_report_never_labels_a_parent_correct_or_wrong():
    r = build_report(parent_name="P", child_name=None, selected_pathways=["medical", "educational"], answers=_seed_answers())
    blob = str(r).lower()
    for bad in ("correct parent", "wrong parent", "winner", "right parent", "incorrect parent"):
        assert bad not in blob


def test_pdf_is_valid_and_contains_workflow_headers():
    r = build_report(parent_name="Sam", child_name="K", selected_pathways=["multiple"], answers=_seed_answers())
    out = build_snc2_pdf(report=r)
    assert isinstance(out, (bytes, bytearray))
    assert out[:5] == b"%PDF-"
    assert len(out) > 5000
    for phrase in (
        b"Special Needs Co-Parenting",
        b"Individual Parent Report",
        b"Step 1. Understand the Concern",
        b"Step 8. Create an Action Plan",
        b"Pathway scores",
    ):
        assert phrase in out
    # No winner language
    low = out.lower()
    for bad in (b"correct parent", b"wrong parent", b"winner", b"right parent"):
        assert bad not in low


def test_pathways_catalog_contains_all_four_options():
    ids = [p["id"] for p in PATHWAYS]
    assert ids == ["medical", "educational", "psychological", "multiple"]
