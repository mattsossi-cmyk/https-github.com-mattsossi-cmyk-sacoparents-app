"""Tests for the redesigned Special Needs Assessment scoring (2026 framework)."""
from __future__ import annotations

from sn_v3_questions import DOMAINS, total_question_count
from sn_v3_scoring import (
    compute_scores,
    CAT_STRENGTH, CAT_DEVELOP, CAT_PRIORITY, CAT_PROFESSIONAL, CAT_SAFETY,
    OVERALL_STRENGTH, OVERALL_PRIORITY, OVERALL_SAFETY,
)


def _forward_answers(v: int) -> dict:
    """Set every non-safety question to `v` and every safety (reverse) question
    to the value that keeps it at 'no concern' (i.e. Strongly disagree = 0)."""
    a = {}
    for d in DOMAINS:
        for q in d["questions"]:
            if q.get("safety_flag"):
                a[q["id"]] = 0  # no safety concern
            else:
                a[q["id"]] = v
    return a


def test_all_strong_produces_strength_overall_and_no_safety():
    a = _forward_answers(4)
    s = compute_scores(a)
    assert s["safety_triggered"] is False
    assert s["overall_rating"] == OVERALL_STRENGTH
    non_safety = [d for d in s["domains"] if d["id"] != "d10"]
    assert all(d["category"] == CAT_STRENGTH for d in non_safety)


def test_all_weak_produces_priority_overall():
    a = _forward_answers(0)
    s = compute_scores(a)
    assert s["safety_triggered"] is False
    assert s["overall_rating"] == OVERALL_PRIORITY
    non_safety = [d for d in s["domains"] if d["id"] != "d10"]
    assert all(d["category"] == CAT_PRIORITY for d in non_safety)
    assert s["show_communication_toolkit"] is True


def test_safety_reverse_item_triggers_safety_overall():
    a = _forward_answers(3)
    # A single reverse-scored safety item at "Agree" (raw 3) should trigger.
    a["d10_q3"] = 3
    s = compute_scores(a)
    assert s["safety_triggered"] is True
    assert s["overall_rating"] == OVERALL_SAFETY
    safety_domain = next(d for d in s["domains"] if d["id"] == "d10")
    assert safety_domain["category"] == CAT_SAFETY


def test_meta_safety_flag_alone_triggers_safety():
    a = _forward_answers(4)
    s = compute_scores(a, meta={"d6_q1": {"safety": True}})
    assert s["safety_triggered"] is True
    assert s["overall_rating"] == OVERALL_SAFETY


def test_meta_want_help_two_hits_elevates_to_professional():
    a = _forward_answers(3)  # would normally be Developing
    s = compute_scores(a, meta={
        "d3_q1": {"want_help": True},
        "d3_q4": {"want_help": True},
    })
    d3 = next(d for d in s["domains"] if d["id"] == "d3")
    assert d3["category"] == CAT_PROFESSIONAL
    assert d3["want_help_hits"] == 2


def test_na_items_are_excluded_from_average():
    a = _forward_answers(3)
    # Mark two D3 items N/A — remaining items still average to 3.0 → Developing
    s = compute_scores(a, meta={"d3_q1": {"na": True}, "d3_q6": {"na": True}})
    d3 = next(d for d in s["domains"] if d["id"] == "d3")
    assert d3["na_count"] == 2
    assert d3["answered"] == 4
    assert d3["category"] == CAT_DEVELOP


def test_total_question_count_matches_domains():
    assert total_question_count() == sum(len(d["questions"]) for d in DOMAINS)
    assert total_question_count() == 60  # 10 domains × 6


def test_priority_focus_ids_populated():
    a = _forward_answers(1)  # Disagree everywhere → priority
    s = compute_scores(a)
    assert len(s["priority_focus_ids"]) >= 3
