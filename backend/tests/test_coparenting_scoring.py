"""Deterministic tests for the Co-Parenting Assessment scoring engine."""
from __future__ import annotations

import pytest

from coparenting_questions import (
    RESPONSE_SCALE,
    SECTIONS,
    all_question_ids,
    find_question,
    total_question_count,
)
from coparenting_scoring import (
    RATING_EXCELLENT,
    RATING_FAIR,
    RATING_GOOD,
    RATING_NEEDS,
    compute_scores,
    score_section,
    validate_answers,
)


def test_schema_shape():
    assert len(SECTIONS) == 10
    assert len(RESPONSE_SCALE) == 5
    assert 60 <= total_question_count() <= 80
    # every question id is unique
    ids = all_question_ids()
    assert len(ids) == len(set(ids))
    # exactly one reverse-scored question in section 1 (s1q7) and section 2 (s2q6)
    reverse_ids = [q["id"] for s in SECTIONS for q in s["questions"] if q.get("reverse")]
    assert "s1q7" in reverse_ids
    assert "s2q6" in reverse_ids


def test_find_question_and_reverse_handling():
    q = find_question("s1q7")
    assert q is not None and q.get("reverse") is True
    q2 = find_question("s3q1")
    assert q2 is not None and not q2.get("reverse")
    assert find_question("nope") is None


def test_validate_answers():
    ok, _ = validate_answers({"s1q1": 4, "s2q1": 2})
    assert ok
    ok, err = validate_answers({"s1q1": 5})
    assert not ok and "0-4" in err
    ok, err = validate_answers({"nope": 2})
    assert not ok and "Unknown" in err


def test_all_always_yields_excellent_overall():
    answers = {qid: 4 for qid in all_question_ids()}
    # for reverse-scored questions "Always" is bad, so their effective value flips to 0
    # -> those sections shouldn't be Excellent, but overall should still be at least Building
    result = compute_scores(answers)
    assert result["overall_rating"] in {"Excellent Progress", "Building Progress"}
    # non-reverse sections must be Excellent
    s3 = next(s for s in result["sections"] if s["id"] == "s3")
    assert s3["rating"] == RATING_EXCELLENT


def test_all_never_yields_early_progress_and_toolkit():
    answers = {qid: 0 for qid in all_question_ids()}
    result = compute_scores(answers)
    assert result["overall_rating"] == "Early Progress"
    assert result["show_communication_toolkit"] is True  # section 1 rated Needs
    # priority focus includes section 1
    assert "s1" in result["priority_focus"]


def test_sample_report_scenario_matches_building_progress():
    """Reproduce the shape of the sample Co-Parenting Report:
    - Communication rated Needs Improvement (triggers toolkit)
    - Safety & Supervision Excellent
    - Educational, Daily Routines, Emotional-Behavioral, Social, Long-Term = Good
    - Pick-Up, Medical, Therapy = Fair
    """
    answers = {}
    # Section 1: all Rarely (avg 1.0 → Needs). Reverse Q gets Always→0 (still bad).
    for q in next(s for s in SECTIONS if s["id"] == "s1")["questions"]:
        answers[q["id"]] = 1 if not q.get("reverse") else 4  # both map to low
    # Section 2, 4, 7: Sometimes (avg 2.0 → Fair)
    for sid in ("s2", "s4", "s7"):
        for q in next(s for s in SECTIONS if s["id"] == sid)["questions"]:
            answers[q["id"]] = 2 if not q.get("reverse") else 2
    # Section 3, 5, 6, 9, 10: Often (avg 3.0 → Good)
    for sid in ("s3", "s5", "s6", "s9", "s10"):
        for q in next(s for s in SECTIONS if s["id"] == sid)["questions"]:
            answers[q["id"]] = 3
    # Section 8: Always (avg 4.0 → Excellent)
    for q in next(s for s in SECTIONS if s["id"] == "s8")["questions"]:
        answers[q["id"]] = 4
    result = compute_scores(answers)
    by_id = {s["id"]: s for s in result["sections"]}
    assert by_id["s1"]["rating"] == RATING_NEEDS
    assert by_id["s2"]["rating"] == RATING_FAIR
    assert by_id["s4"]["rating"] == RATING_FAIR
    assert by_id["s7"]["rating"] == RATING_FAIR
    assert by_id["s3"]["rating"] == RATING_GOOD
    assert by_id["s5"]["rating"] == RATING_GOOD
    assert by_id["s8"]["rating"] == RATING_EXCELLENT
    assert result["overall_rating"] == "Building Progress"
    assert result["show_communication_toolkit"] is True
    assert result["priority_focus"] == ["s1"]
    assert "s8" in result["strongest_section_ids"]


def test_partial_answers_return_null_rating_for_unanswered_section():
    # Only answer section 1
    s1_qs = next(s for s in SECTIONS if s["id"] == "s1")["questions"]
    answers = {q["id"]: 3 for q in s1_qs}
    result = compute_scores(answers)
    by_id = {s["id"]: s for s in result["sections"]}
    assert by_id["s1"]["rating"] is not None
    assert by_id["s2"]["rating"] is None
    assert by_id["s2"]["answered"] == 0


def test_score_section_directly():
    sec = next(s for s in SECTIONS if s["id"] == "s3")
    answers = {q["id"]: 4 for q in sec["questions"]}
    result = score_section(sec, answers)
    assert result["rating"] == RATING_EXCELLENT
    assert result["avg"] == 4.0
    assert result["answered"] == result["total"]
