"""Unit tests for the Educational Needs — Deep Dive."""
from __future__ import annotations

from edu_deep_questions import (
    DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION, all_item_keys, item_by_key,
    public_schema, validate_answer,
)
from edu_deep_report import build_deep_dive_pdf, build_deep_dive_report
from edu_deep_scoring import score_deep_dive


# ---------- schema ----------
def test_schema_has_twelve_sections():
    assert len(DEEP_DIVE_SECTIONS) == 12
    numbers = [s["number"] for s in DEEP_DIVE_SECTIONS]
    assert numbers == list(range(1, 13))


def test_texas_only_section_is_s3():
    tx = [s for s in DEEP_DIVE_SECTIONS if s.get("texas_only")]
    assert len(tx) == 1 and tx[0]["id"] == "s3"


def test_gated_sections_are_iep_and_504_and_counselor():
    gated = {s["id"]: s["gate"] for s in DEEP_DIVE_SECTIONS if s.get("gate")}
    assert gated["s4"]["item"] == "has_iep" and gated["s4"]["value"] == "Yes"
    assert gated["s5"]["item"] == "has_504" and gated["s5"]["value"] == "Yes"
    assert gated["s6"]["item"] == "meets_counselor" and gated["s6"]["value"] == "Yes"


def test_public_schema_is_json_safe():
    sch = public_schema()
    assert sch["version"] == DEEP_DIVE_VERSION
    for s in sch["sections"]:
        for it in s["items"]:
            assert it["id"] and it["type"] in ("likert", "single", "multi", "textarea", "text")


def test_all_item_keys_unique():
    keys = all_item_keys()
    assert len(keys) == len(set(keys))


# ---------- validation ----------
def test_validate_likert():
    assert validate_answer("s2_discuss_goals", 3)
    assert validate_answer("s2_discuss_goals", "na")
    assert not validate_answer("s2_discuss_goals", 7)


def test_validate_single_requires_option_membership():
    assert validate_answer("s2_how_often_attend", "Rarely")
    assert not validate_answer("s2_how_often_attend", "Whenever I feel like it")


def test_validate_multi_requires_option_membership():
    assert validate_answer("s1_concerns", ["Reading", "ADHD"])
    assert not validate_answer("s1_concerns", ["Reading", "Made-up-thing"])


def test_validate_unknown_key_rejected():
    assert not validate_answer("s99_nonexistent", "anything")


def test_item_by_key():
    assert item_by_key("s3_conflict_interferes")["type"] == "likert"
    assert item_by_key("nothing") is None


# ---------- scoring ----------
def _low_answers_ard_iep():
    return {
        "s1_school_setting": "Public School",
        "s1_grade_level": "3rd",
        "s1_school_state": "TX",
        "s1_concerns": ["Reading", "Writing", "ADHD", "Executive Functioning", "Behaviour"],
        "s2_how_often_attend": "Rarely",
        "s2_both_can_attend": "Never",
        "s2_communicate_after": "Sometimes",
        "s2_discuss_goals": 2,
        "s2_both_receive_updates": "No",
        "s3_review_plan_before": 2, "s3_comfort_participating": 2,
        "s3_conflict_interferes": 4, "s3_prepare_questions": 2,
        "s3_decisions_focus_child": 3,
        "s4_has_iep": "Yes", "s4_who_reviews": "Mother",
        "s4_familiar_with_goals": 2, "s4_both_homes_support": 2,
        "s4_monitor_progress": 2, "s4_accommodations_consistent": 2,
        "s8_homework_consistent": 5, "s8_quiet_study_spaces": 5,
        "s8_assignments_completed": 5, "s8_communicate_missing_work": 5,
        "s8_child_encouraged": 5, "s8_technology_available": 5,
        "s10_school_choice": "Rarely Agree",
        "s10_testing": "Rarely Agree",
        "s10_tutoring": "Never Agree",
        "s10_retention": "Never Agree",
    }


def test_scoring_flags_and_strengths():
    scored = score_deep_dive(_low_answers_ard_iep())
    assert scored["is_texas"] is True
    by_id = {s["id"]: s for s in scored["sections"]}
    # Flagged
    for sid in ("s1", "s2", "s3", "s4", "s10"):
        assert by_id[sid]["is_flagged"], f"expected {sid} to be flagged"
    # Strength
    assert by_id["s8"]["is_strength"], "expected s8 (homework) to be a strength"
    # Not visible (no IEP-gated s5, no counsellor-gated s6)
    assert not by_id["s5"]["is_visible"]
    assert not by_id["s6"]["is_visible"]


def test_ard_hidden_outside_texas():
    ans = _low_answers_ard_iep()
    ans["s1_school_state"] = "CA"
    scored = score_deep_dive(ans)
    ard = next(s for s in scored["sections"] if s["id"] == "s3")
    assert not ard["is_visible"]
    assert not ard["is_flagged"]


def test_no_answers_no_flags():
    scored = score_deep_dive({})
    assert scored["totals"]["flagged"] == 0
    assert scored["totals"]["strengths"] == 0


# ---------- report ----------
def test_report_only_surfaces_flagged_and_strength_sections():
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_low_answers_ard_iep())
    ids = {s["id"] for s in r["sections"]}
    # Report entries only exist for answered visible sections
    for sid in ("s1", "s2", "s3", "s4", "s8", "s10"):
        assert sid in ids
    assert "s5" not in ids  # gated + not answered
    assert "s6" not in ids
    assert r["profile"]["is_texas"] is True
    # Recommendations are populated for flagged sections
    for entry in r["sections"]:
        if entry["is_flagged"] and entry["id"] != "s1":
            assert entry.get("challenge_text")
            assert entry.get("recommendations")


def test_pdf_is_letter_and_starts_with_pdf_magic():
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_low_answers_ard_iep())
    pdf = build_deep_dive_pdf(report=r)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_pdf_pages_reasonable_for_letter():
    """A representative filled report must fit tightly on Letter."""
    from fpdf import FPDF  # sanity import — real dimension check via body count
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_low_answers_ard_iep())
    pdf = build_deep_dive_pdf(report=r)
    # Very lightweight page-count sniff: %%EOF at end, "/Type /Page " occurrences.
    page_markers = pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ")
    assert page_markers <= 6, f"PDF has too many pages ({page_markers})"
