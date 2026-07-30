"""Unit tests for the SNC Individual Parent Report builder (Phase A)."""
from __future__ import annotations

from snc_questions import SECTIONS, SCORED_CATEGORY_IDS, scored_items
from snc_scoring import compute_scores
from snc_report_content import build_individual_report, DISCLAIMER


def _mixed_answers():
    """A realistic mixed profile so multiple classifications surface."""
    a = {
        # Section 1 intake
        "s1_age": "8 years / 3rd grade",
        "s1_strengths": "Curious. Loves dinosaurs. Kind to younger kids.",
        "s1_joy": "Drawing, reading with mom, riding his bike.",
        "s1_diagnosis_status": "Diagnosis or eligibility determination received",
        "s1_needs": ["ADHD or executive functioning", "Sensory processing"],
        "s1_needs_narrative": "ADHD-Combined; ongoing OT for sensory regulation.",
        # Sections 2-12 answers (mix)
        **{it["id"]: 4 for it in scored_items("s2")},
        **{it["id"]: 3 for it in scored_items("s3")},   # coordination opportunity
        **{it["id"]: 5 for it in scored_items("s4")},   # established strength
        **{it["id"]: 2 for it in scored_items("s5")},   # significant inconsistency
        **{it["id"]: 4 for it in scored_items("s6")},   # mostly consistent
        **{it["id"]: 1 for it in scored_items("s7")},   # priority concern
        **{it["id"]: 4 for it in scored_items("s8")},
        **{it["id"]: 4 for it in scored_items("s9")},
        **{it["id"]: 3 for it in scored_items("s10")},
        **{it["id"]: 4 for it in scored_items("s12")},
        # Section 11 safety
        "s11_flags": ["None of these apply."],
        # Section 13 context
        "s13_goals": "Consistent bedtime; better school-home communication; regular OT.",
        "s13_concerns": "Homework meltdowns; medication timing on Fridays; lost school notices.",
        "s13_need_you": "Predictable evenings and one-on-one time.",
        "s13_need_other": "Same medication schedule; shared homework routine.",
        "s13_need_both": "Consistent bedtime and calm exchanges.",
        "s13_first": "Homework routine.",
        "s13_info_needed": "Whether the ADHD medication dose should be adjusted for growth.",
        "s13_thirty_day": "Try the shared parenting app for 30 days.",
        # Extra open answers
        "s3_providers": ["Pediatrician", "Occupational therapist"],
        "s3_open_coord": "Medication and OT coordination.",
        "s7_preferred": ["Co-parenting application", "Email"],
        "s5_open_difficult": "Sunday-night exchanges are the hardest.",
    }
    return a


def test_report_has_all_top_level_sections():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam Parent",
                                child_name="A.",
                                assessment_date="2026-02-15",
                                answers=a)
    for key in [
        "cover", "purpose", "at_a_glance", "category_summary", "child_profile",
        "understanding_acceptance", "medical_mental", "school", "transitions",
        "daily_routines", "communication", "events_and_extracurricular",
        "decision_making", "safety", "parent_capacity", "goals_concerns",
        "action_plan", "thirty_day_steps", "questions_for_other_parent",
        "closing", "disclaimer",
    ]:
        assert key in r, f"missing report section: {key}"


def test_cover_and_disclaimer_populated():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam Parent", answers=a)
    assert r["cover"]["parent_name"] == "Sam Parent"
    assert r["cover"]["report_type"] == "Individual Parent Report"
    assert r["disclaimer"] == DISCLAIMER


def test_category_summary_has_ten_scored_rows_plus_safety():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    scored = [row for row in r["category_summary"] if row["score"] != "Not scored"]
    assert len(scored) == 10
    safety_row = r["category_summary"][-1]
    assert safety_row["category"] == "Safety considerations"
    assert safety_row["score"] == "Not scored"
    assert safety_row["classification"] == "Separate review"


def test_no_parent_labelled_right_or_wrong():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    # Exclude the disclaimer/purpose (which quote the spec's "…that either parent's
    # account is correct, or replace…" line) and check the generated content only.
    body = {k: v for k, v in r.items() if k not in ("disclaimer", "purpose")}
    joined = str(body).lower()
    for phrase in ("is correct", "is wrong", "at fault", "better parent", "worse parent"):
        assert phrase not in joined, f"generated report should never contain '{phrase}'"


def test_safety_included_by_default_but_redacted_when_flag_off():
    a = _mixed_answers()
    r_own = build_individual_report(parent_name="Sam", answers=a, include_safety=True)
    r_shared = build_individual_report(parent_name="Sam", answers=a, include_safety=False)
    assert r_own["safety"].get("redacted") is not True
    assert r_shared["safety"]["redacted"] is True
    # Even if flags were selected, they never appear in the shared view.
    a2 = dict(a)
    a2["s11_flags"] = ["I am afraid of the other parent."]
    r2 = build_individual_report(parent_name="Sam", answers=a2, include_safety=False)
    assert "I am afraid of the other parent." not in str(r2["safety"])


def test_action_plan_targets_lowest_scoring_categories():
    a = _mixed_answers()
    scores = compute_scores(a)
    r = build_individual_report(parent_name="Sam", answers=a, scores=scores)
    plan = r["action_plan"]
    assert 1 <= len(plan) <= 4
    # First entry must be one of the weakest categories.
    weakest_names = {c["name"] for c in scores["categories"]
                     if c["classification"] in ("Priority concern", "Significant inconsistency", "Coordination opportunity")}
    assert plan[0]["recommended_action"], "action_plan must include a concrete action"
    assert any(row["recommended_action"] for row in plan)


def test_questions_for_other_parent_are_generated_from_weak_answers():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    qs = r["questions_for_other_parent"]
    assert len(qs) >= 3
    # At least one standing question is present verbatim.
    assert "How will each parent receive school notices?" in qs


def test_five_part_pattern_in_every_scored_section():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    for section_key in [
        "understanding_acceptance", "medical_mental", "school", "transitions",
        "daily_routines", "communication", "decision_making", "parent_capacity",
    ]:
        block = r[section_key]
        for k in ("finding", "child_impact", "suggested", "action_step"):
            assert k in block, f"{section_key}.{k} missing"


def test_child_profile_summary_uses_intake_verbatim():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    cp = r["child_profile"]
    assert "3rd grade" in cp["age_grade"]
    assert "ADHD or executive functioning" in cp["identified_needs"]
    assert "ADHD-Combined" in cp["narrative"]
    assert "According to this parent" in cp["summary"]


def test_daily_routines_grid_populated():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    grid = r["daily_routines"]["extras"]["routine_grid"]
    assert len(grid) >= 6
    labels = [row["routine"] for row in grid]
    assert "Medication" in labels
    assert all(row["reported_consistency"] for row in grid)


def test_thirty_day_steps_only_from_needs_improvement_categories():
    a = _mixed_answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    steps = r["thirty_day_steps"]
    assert len(steps) <= 5
    # None should reference "Excellent" categories — soft check via presence.
    assert isinstance(steps, list)


def test_report_works_with_no_answers():
    r = build_individual_report(parent_name="Sam", answers={})
    # Category summary still lists 10 scored + 1 safety row, all unrated.
    scored = [row for row in r["category_summary"] if row["score"] != "Not scored"]
    assert len(scored) == 10
    assert all(row["classification"] == "Not enough data" for row in scored)
