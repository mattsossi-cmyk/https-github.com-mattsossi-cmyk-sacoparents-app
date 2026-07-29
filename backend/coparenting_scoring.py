"""Deterministic scoring engine for the SA CoParents 10-section Co-Parenting Assessment.

Inputs
------
answers: Dict[str, int]
    Maps question_id -> raw response value (0-4). Missing keys are treated as
    unanswered and excluded from the section average.

Outputs
-------
sections: List of per-section score dicts { id, number, name, rating, avg, answered, total }
overall_rating: str  ("Excellent Progress" | "Building Progress" | "Early Progress")
priority_focus: List[str]  section ids currently rated "Needs Improvement" (or lowest section if none)
show_communication_toolkit: bool  True if Section 1 rating is Fair or Needs Improvement
findings: dict summarising strongest and weakest sections
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from coparenting_questions import SECTIONS, find_question


RATING_EXCELLENT = "Excellent"
RATING_GOOD = "Good"
RATING_FAIR = "Fair"
RATING_NEEDS = "Needs Improvement"

# Section rating thresholds (mean of 0-4 scale, after reverse-flip)
THRESHOLD_EXCELLENT = 3.25
THRESHOLD_GOOD = 2.5
THRESHOLD_FAIR = 1.5


def _score_question(qid: str, raw_value: int) -> int:
    """Return the effective 0-4 value, flipping if the question is reverse-scored."""
    q = find_question(qid)
    if q is None:
        raise KeyError(f"Unknown question id: {qid}")
    if not isinstance(raw_value, int) or raw_value < 0 or raw_value > 4:
        raise ValueError(f"Response for {qid} must be an int 0-4, got {raw_value!r}")
    return (4 - raw_value) if q.get("reverse") else raw_value


def _rating_for_avg(avg: float) -> str:
    if avg >= THRESHOLD_EXCELLENT:
        return RATING_EXCELLENT
    if avg >= THRESHOLD_GOOD:
        return RATING_GOOD
    if avg >= THRESHOLD_FAIR:
        return RATING_FAIR
    return RATING_NEEDS


def score_section(section: Dict[str, Any], answers: Dict[str, int]) -> Dict[str, Any]:
    values: List[int] = []
    for q in section["questions"]:
        if q["id"] in answers:
            values.append(_score_question(q["id"], answers[q["id"]]))
    total = len(section["questions"])
    answered = len(values)
    if answered == 0:
        return {
            "id": section["id"],
            "number": section["number"],
            "name": section["name"],
            "rating": None,
            "avg": None,
            "answered": 0,
            "total": total,
        }
    avg = sum(values) / answered
    return {
        "id": section["id"],
        "number": section["number"],
        "name": section["name"],
        "rating": _rating_for_avg(avg),
        "avg": round(avg, 3),
        "answered": answered,
        "total": total,
    }


def _overall_rating(section_scores: List[Dict[str, Any]]) -> str:
    rated = [s for s in section_scores if s["rating"] is not None]
    if not rated:
        return "Not enough data"
    excellent = sum(1 for s in rated if s["rating"] == RATING_EXCELLENT)
    good = sum(1 for s in rated if s["rating"] == RATING_GOOD)
    needs = sum(1 for s in rated if s["rating"] == RATING_NEEDS)
    if excellent >= 6:
        return "Excellent Progress"
    if needs >= 4 or (excellent + good) < len(rated) / 2:
        return "Early Progress"
    return "Building Progress"


def compute_scores(answers: Dict[str, int]) -> Dict[str, Any]:
    """Compute the full report scoring result from a dict of answers."""
    section_scores: List[Dict[str, Any]] = [score_section(s, answers) for s in SECTIONS]

    overall = _overall_rating(section_scores)

    # Priority focus areas — any section currently Needs Improvement.
    # If none are Needs Improvement, priority is the section with the LOWEST avg
    # (still rated Fair or Good), so parents always see something to work on.
    rated = [s for s in section_scores if s["rating"] is not None]
    needs_sections = [s["id"] for s in rated if s["rating"] == RATING_NEEDS]
    if needs_sections:
        priority_focus = needs_sections
    elif rated:
        lowest = min(rated, key=lambda s: s["avg"])
        priority_focus = [lowest["id"]]
    else:
        priority_focus = []

    # Communication Toolkit surfaces when Section 1 is Fair or Needs Improvement.
    s1 = next((s for s in section_scores if s["id"] == "s1"), None)
    show_toolkit = bool(
        s1 and s1["rating"] in (RATING_FAIR, RATING_NEEDS)
    )

    # Strongest and weakest sections (for the report banner)
    strongest: List[str] = []
    weakest: List[str] = []
    if rated:
        top_avg = max(s["avg"] for s in rated)
        strongest = [s["id"] for s in rated if s["avg"] == top_avg]
        low_avg = min(s["avg"] for s in rated)
        weakest = [s["id"] for s in rated if s["avg"] == low_avg]

    return {
        "sections": section_scores,
        "overall_rating": overall,
        "priority_focus": priority_focus,
        "show_communication_toolkit": show_toolkit,
        "strongest_section_ids": strongest,
        "weakest_section_ids": weakest,
    }


def validate_answers(answers: Dict[str, int]) -> Tuple[bool, str]:
    """Return (ok, error_msg). Ensures all keys refer to known questions and values are 0-4."""
    if not isinstance(answers, dict):
        return False, "answers must be a dict of {question_id: value}"
    for qid, val in answers.items():
        q = find_question(qid)
        if q is None:
            return False, f"Unknown question id: {qid}"
        if not isinstance(val, int) or val < 0 or val > 4:
            return False, f"Value for {qid} must be an int 0-4"
    return True, ""
