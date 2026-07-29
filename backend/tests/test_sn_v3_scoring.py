"""Deterministic tests for the Special Needs 10-Principle scoring engine."""
from __future__ import annotations
import pytest

from sn_v3_questions import SECTIONS, all_question_ids, total_question_count
from sn_v3_scoring import (RATING_EXCELLENT, RATING_FAIR, RATING_GOOD, RATING_NEEDS,
                            compute_scores, validate_answers)


def test_schema_shape():
    assert len(SECTIONS) == 10
    assert 55 <= total_question_count() <= 70
    ids = all_question_ids()
    assert len(ids) == len(set(ids))
    # verify principle-based ids
    assert any(s["id"] == "p3" for s in SECTIONS)
    reverse_ids = [q["id"] for s in SECTIONS for q in s["questions"] if q.get("reverse")]
    assert "p3q6" in reverse_ids
    assert "p7q5" in reverse_ids


def test_validate_answers():
    ok, _ = validate_answers({"p1q1": 4, "p3q1": 2})
    assert ok
    ok, err = validate_answers({"p1q1": 9})
    assert not ok and "0-4" in err
    ok, err = validate_answers({"badid": 2})
    assert not ok and "Unknown" in err


def test_all_never_needs_improvement_p3_triggers_toolkit():
    answers = {qid: 0 for qid in all_question_ids()}
    result = compute_scores(answers)
    assert result["overall_rating"] == "Early Progress"
    p3 = next(s for s in result["sections"] if s["id"] == "p3")
    assert p3["rating"] == RATING_NEEDS
    assert result["show_communication_toolkit"] is True


def test_sample_scenario_matches_report():
    """Reproduce the ratings shown in the sample Special Needs report:
    P1=Fair · P2=Good · P3=Needs · P4=Fair · P5=Excellent · P6=Good
    P7=Fair · P8=Good · P9=Good · P10=Excellent
    """
    plan = {"p1": 2, "p2": 3, "p3": ("low",), "p4": 2, "p5": 4,
            "p6": 3, "p7": 2, "p8": 3, "p9": 3, "p10": 4}
    answers = {}
    for s in SECTIONS:
        v = plan[s["id"]]
        for q in s["questions"]:
            if v == ("low",):
                answers[q["id"]] = 1 if not q.get("reverse") else 4
            else:
                # for reverse Q at Fair (v=2), keep 2 either way (avg stays 2)
                if q.get("reverse"): answers[q["id"]] = 4 - v
                else: answers[q["id"]] = v
    result = compute_scores(answers)
    by_id = {s["id"]: s for s in result["sections"]}
    assert by_id["p1"]["rating"] == RATING_FAIR
    assert by_id["p2"]["rating"] == RATING_GOOD
    assert by_id["p3"]["rating"] == RATING_NEEDS
    assert by_id["p5"]["rating"] == RATING_EXCELLENT
    assert by_id["p10"]["rating"] == RATING_EXCELLENT
    assert result["show_communication_toolkit"] is True
    assert result["priority_focus"] == ["p3"]
    assert "p5" in result["strongest_section_ids"] or "p10" in result["strongest_section_ids"]
