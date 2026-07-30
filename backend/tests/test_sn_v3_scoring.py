"""Tests for the Special Needs Assessment scoring (9-section framework)."""
from __future__ import annotations

from sn_v3_questions import SECTIONS, total_question_count
from sn_v3_scoring import (
    compute_scores,
    RATING_EXCELLENT, RATING_FAIR, RATING_NEEDS,
    OVERALL_EXCELLENT, OVERALL_EARLY,
)


def _answers(v: int) -> dict:
    """Set every question to value v (0..4)."""
    a = {}
    for s in SECTIONS:
        for q in s["questions"]:
            a[q["id"]] = v
    return a


def test_total_question_count():
    assert total_question_count() == 54  # 9 sections × 6


def test_all_strong_produces_excellent_progress():
    a = _answers(4)
    s = compute_scores(a)
    assert s["overall_rating"] == OVERALL_EXCELLENT
    assert all(sec["rating"] == RATING_EXCELLENT for sec in s["sections"])


def test_all_weak_produces_early_progress():
    a = _answers(0)
    s = compute_scores(a)
    assert s["overall_rating"] == OVERALL_EARLY
    assert all(sec["rating"] == RATING_NEEDS for sec in s["sections"])
    # Section 6 (Communication) is Needs Improvement → toolkit surfaces.
    assert s["show_communication_toolkit"] is True


def test_na_items_are_excluded_from_average():
    a = _answers(3)
    s = compute_scores(a, meta={"d3_q1": {"na": True}, "d3_q6": {"na": True}})
    d3 = next(x for x in s["sections"] if x["id"] == "d3")
    assert d3["na_count"] == 2
    assert d3["answered"] == 4
    # Remaining items still average 3.0 → Good
    assert d3["rating"] == "Good"


def test_meta_want_help_counted_but_does_not_change_rating():
    a = _answers(3)
    s = compute_scores(a, meta={"d3_q1": {"want_help": True}, "d3_q4": {"want_help": True}})
    d3 = next(x for x in s["sections"] if x["id"] == "d3")
    assert d3["want_help_hits"] == 2
    assert d3["rating"] == "Good"


def test_priority_focus_populated_when_weak():
    a = _answers(0)
    s = compute_scores(a)
    assert len(s["priority_focus"]) >= 3


def test_no_safety_keys_in_output():
    """The 9-section framework never surfaces safety-sensitive concepts."""
    s = compute_scores(_answers(2))
    assert "safety_triggered" not in s
    assert "safety_questions" not in s
    for sec in s["sections"]:
        assert "safety_hits" not in sec
        assert sec["rating"] in ("Excellent", "Good", "Fair", "Needs Improvement", None)


def test_ids_do_not_collide_with_coparenting():
    """Special Needs uses d-prefixed ids; Co-Parenting uses s-prefixed ids."""
    ids = {q["id"] for s in SECTIONS for q in s["questions"]}
    assert all(qid.startswith("d") for qid in ids)


def test_domains_alias_matches_sections():
    """Legacy consumers reading `domains` should still work."""
    s = compute_scores(_answers(3))
    assert s["domains"] is s["sections"]
