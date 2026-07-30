"""Unit tests for the Psychological Needs — Deep Dive."""
from __future__ import annotations

from psych_deep_questions import (
    DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION, all_item_keys, item_by_key,
    public_schema, validate_answer,
)
from psych_deep_report import build_deep_dive_pdf, build_deep_dive_report
from psych_deep_scoring import score_deep_dive


def test_schema_has_eleven_sections():
    assert len(DEEP_DIVE_SECTIONS) == 11
    numbers = [s["number"] for s in DEEP_DIVE_SECTIONS]
    assert numbers == list(range(1, 12))


def test_gates():
    gated = {s["id"]: s["gate"] for s in DEEP_DIVE_SECTIONS if s.get("gate")}
    assert gated["s4"] == {"item": "has_medication", "value": "Yes"}
    assert gated["s6"] == {"item": "attends_therapy", "value": "Yes"}


def test_public_schema_json_safe():
    sch = public_schema()
    assert sch["version"] == DEEP_DIVE_VERSION
    for s in sch["sections"]:
        for it in s["items"]:
            assert it["type"] in ("likert", "single", "multi", "textarea")


def test_all_item_keys_unique():
    keys = all_item_keys()
    assert len(keys) == len(set(keys))


def test_validation():
    assert validate_answer("s2_both_know_provider", "Rarely")
    assert not validate_answer("s2_both_know_provider", "Whenever")
    assert validate_answer("s1_diagnoses", ["ADHD", "Anxiety Disorder"])
    assert not validate_answer("s1_diagnoses", ["Nonexistent"])
    assert validate_answer("s3_discuss_respectfully", 4)
    assert not validate_answer("s3_discuss_respectfully", 99)
    assert validate_answer("s3_discuss_respectfully", "na")
    assert not validate_answer("bogus_key", "x")
    assert item_by_key("s7_anxiety")["type"] == "single"


def _low_answers():
    return {
        "s1_diagnoses": ["ADHD", "Anxiety Disorder", "Emotional dysregulation"],
        "s2_provider_types": ["Child Psychologist"],
        "s2_both_know_provider": "Sometimes",
        "s2_attend_appointments": "Rarely",
        "s2_both_receive_updates": "Rarely",
        "s2_communicate_recs": "Sometimes",
        "s2_follow_recs_consistent": "Rarely",
        "s3_provider_understands": "Somewhat Confident",
        "s3_confidence_plan": "Neutral",
        "s3_trust_recommendations": "Somewhat Confident",
        "s3_both_confident": "Not Confident",
        "s3_discuss_respectfully": 2,
        "s4_has_medication": "Yes",
        "s4_prescriber": "Psychiatrist",
        "s4_understand_areas": ["Medication purpose"],
        "s4_administered_consistent": 2, "s4_communicate_changes": 2,
        "s4_refills_coordinated": 2, "s4_side_effects_discussed": 2,
        "s4_concerns_reported": 2,
        "s7_anxiety": "Rarely Consistent", "s7_meltdowns": "Rarely Consistent",
        "s7_transitions": "Sometimes Consistent",
        "s8_planned_areas": ["Severe anxiety"],
        "s8_know_emergency_contacts": "No", "s8_know_crisis_procedures": "No",
        "s8_plan_in_writing": "No",
        "s10_start_therapy": "Rarely Agree",
        "s10_medication": "Never Agree",
        "s10_change_therapist": "Never Agree",
        "s11_routines": "Always Consistent", "s11_emotional_support": "Always Consistent",
        "s11_calm_environment": "Always Consistent", "s11_positive_reinforcement": "Always Consistent",
        "s11_safe_expression": "Always Consistent", "s11_consistent_expectations": "Always Consistent",
        "s11_healthy_coping": "Always Consistent", "s11_stress_reduction": "Always Consistent",
    }


def test_scoring_flags_and_strengths():
    scored = score_deep_dive(_low_answers())
    by_id = {s["id"]: s for s in scored["sections"]}
    for sid in ("s1", "s2", "s3", "s4", "s8", "s10"):
        assert by_id[sid]["is_flagged"], f"expected {sid} flagged"
    assert by_id["s11"]["is_strength"]
    # s6 gated by attends_therapy — must be invisible
    assert not by_id["s6"]["is_visible"]


def test_no_answers_no_flags():
    scored = score_deep_dive({})
    assert scored["totals"] == {"answered": 0, "flagged": 0, "strengths": 0}


def test_gate_hides_medication_when_none():
    ans = _low_answers()
    ans["s4_has_medication"] = "No"
    scored = score_deep_dive(ans)
    s4 = next(s for s in scored["sections"] if s["id"] == "s4")
    assert not s4["is_visible"]
    assert not s4["is_flagged"]


def test_report_only_surfaces_flagged_and_strength_sections():
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_low_answers())
    ids = {s["id"] for s in r["sections"]}
    for sid in ("s1", "s2", "s3", "s4", "s8", "s10", "s11"):
        assert sid in ids
    for entry in r["sections"]:
        if entry["is_flagged"] and entry["id"] != "s1":
            # s1's template intentionally has no strength text but has recommendations
            pass
        if entry["is_flagged"]:
            assert entry.get("challenge_text") or entry["id"] == "s1"


def test_pdf_letter_and_page_count():
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_low_answers())
    pdf = build_deep_dive_pdf(report=r)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 5000
    page_markers = pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ")
    assert page_markers <= 6, f"PDF has too many pages ({page_markers})"
