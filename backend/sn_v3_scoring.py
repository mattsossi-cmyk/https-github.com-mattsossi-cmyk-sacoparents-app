"""Scoring engine for the Special Needs Co-Parenting Assessment.

Mirrors coparenting_scoring.py so the two products score, rate, and label
identically. The only additions kept for Special Needs are the meta-flag
outputs (na, need_info, want_help) which flow into the report but never
change section ratings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sn_v3_questions import SECTIONS, total_question_count


RATING_EXCELLENT = "Excellent"
RATING_GOOD      = "Good"
RATING_FAIR      = "Fair"
RATING_NEEDS     = "Needs Improvement"

# Section rating thresholds — identical to Co-Parenting.
THRESHOLD_EXCELLENT = 3.25
THRESHOLD_GOOD      = 2.5
THRESHOLD_FAIR      = 1.5


OVERALL_EXCELLENT  = "Excellent Progress"
OVERALL_BUILDING   = "Building Progress"
OVERALL_EARLY      = "Early Progress"


def _rating_for_avg(avg: float) -> str:
    if avg >= THRESHOLD_EXCELLENT:
        return RATING_EXCELLENT
    if avg >= THRESHOLD_GOOD:
        return RATING_GOOD
    if avg >= THRESHOLD_FAIR:
        return RATING_FAIR
    return RATING_NEEDS


def _score_section(section: Dict[str, Any], answers: Dict[str, int], meta: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
    values: List[int] = []
    na_count = 0
    want_help_hits = 0
    need_info_hits = 0
    for q in section["questions"]:
        qid = q["id"]
        m = meta.get(qid) or {}
        if m.get("na"):
            na_count += 1
            continue  # N/A items don't count toward the section average.
        if m.get("want_help"):
            want_help_hits += 1
        if m.get("need_info"):
            need_info_hits += 1
        if qid in answers:
            values.append(int(answers[qid]))
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
            "na_count": na_count,
            "want_help_hits": want_help_hits,
            "need_info_hits": need_info_hits,
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
        "na_count": na_count,
        "want_help_hits": want_help_hits,
        "need_info_hits": need_info_hits,
    }


def _overall_rating(section_scores: List[Dict[str, Any]]) -> str:
    rated = [s for s in section_scores if s["rating"] is not None]
    if not rated:
        return "Not enough data"
    excellent = sum(1 for s in rated if s["rating"] == RATING_EXCELLENT)
    good = sum(1 for s in rated if s["rating"] == RATING_GOOD)
    needs = sum(1 for s in rated if s["rating"] == RATING_NEEDS)
    if excellent >= 6:
        return OVERALL_EXCELLENT
    if needs >= 4 or (excellent + good) < len(rated) / 2:
        return OVERALL_EARLY
    return OVERALL_BUILDING


def compute_scores(
    answers: Dict[str, int] | None,
    *,
    meta: Dict[str, Dict[str, bool]] | None = None,
) -> Dict[str, Any]:
    """Compute the full scoring result.

    Args:
        answers: {question_id -> int(0-4)}. Missing keys = unanswered.
        meta:    {question_id -> {"na": bool, "need_info": bool, "want_help": bool}}
    """
    answers = answers or {}
    meta = meta or {}

    section_scores: List[Dict[str, Any]] = [_score_section(s, answers, meta) for s in SECTIONS]

    overall = _overall_rating(section_scores)

    rated = [s for s in section_scores if s["rating"] is not None]

    # Priority focus areas — any section currently Needs Improvement.
    # If none, use the lowest-avg rated section so parents always see something to work on.
    needs_sections = [s["id"] for s in rated if s["rating"] == RATING_NEEDS]
    if needs_sections:
        priority_focus = needs_sections
    elif rated:
        lowest = min(rated, key=lambda s: s["avg"])
        priority_focus = [lowest["id"]]
    else:
        priority_focus = []

    # Communication Toolkit surfaces when Section 6 (Communication) is Fair or Needs Improvement.
    d6 = next((s for s in section_scores if s["id"] == "d6"), None)
    show_toolkit = bool(d6 and d6["rating"] in (RATING_FAIR, RATING_NEEDS))

    strongest: List[str] = []
    weakest: List[str] = []
    if rated:
        top_avg = max(s["avg"] for s in rated)
        strongest = [s["id"] for s in rated if s["avg"] == top_avg]
        low_avg = min(s["avg"] for s in rated)
        weakest = [s["id"] for s in rated if s["avg"] == low_avg]

    return {
        "sections": section_scores,
        # Legacy alias kept for any existing readers.
        "domains": section_scores,
        "overall_rating": overall,
        "priority_focus": priority_focus,
        "show_communication_toolkit": show_toolkit,
        "strongest_section_ids": strongest,
        "weakest_section_ids": weakest,
        "answered_count": sum(s["answered"] for s in section_scores),
        "total_count": total_question_count(),
    }


def validate_answers(answers: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(answers, dict):
        return False, "answers must be an object"
    for qid, v in answers.items():
        if not isinstance(v, int) or v < 0 or v > 4:
            return False, f"Value for {qid} must be an int 0-4"
    return True, ""
