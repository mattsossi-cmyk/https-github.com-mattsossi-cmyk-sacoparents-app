"""Unit tests for the Co-Parenting report content + PDF builders."""
from __future__ import annotations

import pytest

from coparenting_questions import SECTIONS
from coparenting_scoring import compute_scores
import cp_report_content
import cp_report_pdf


def _answers_all(value: int) -> dict:
    return {q["id"]: value for s in SECTIONS for q in s["questions"]}


def test_build_report_all_excellent_top_level_shape():
    answers = _answers_all(4)
    # Adjust reverse-scored items (raw 0 = best when reverse) so ratings stay Excellent.
    for s in SECTIONS:
        for q in s["questions"]:
            if q.get("reverse"):
                answers[q["id"]] = 0
    scores = compute_scores(answers)
    r = cp_report_content.build_report(scores=scores, answers=answers, parent_name="Sam Parent")

    assert r["overall_rating"] == "Excellent Progress"
    assert r["prepared_by"] == "Sam Parent"
    assert r["overall_summary"]
    assert len(r["sections"]) == 10
    # No toolkit when Section 1 is Excellent
    assert r["show_communication_toolkit"] is False
    assert r["communication_toolkit"] == []
    # Every section carries findings + recommendations
    for sec in r["sections"]:
        assert sec["rating"] == "Excellent"
        assert sec["findings"]
        assert sec["recommendations"]


def test_build_report_needs_improvement_triggers_toolkit_and_priority():
    # All zeros on forward-scored items => everything Needs Improvement,
    # including Section 1 which triggers the communication toolkit.
    answers = _answers_all(0)
    # Keep reverse-scored items also at effective 0 (raw 4 flips to 0).
    for s in SECTIONS:
        for q in s["questions"]:
            if q.get("reverse"):
                answers[q["id"]] = 4
    scores = compute_scores(answers)
    r = cp_report_content.build_report(scores=scores, answers=answers, parent_name=None)

    assert r["show_communication_toolkit"] is True
    assert len(r["communication_toolkit"]) == 5
    assert r["overall_rating"] == "Early Progress"
    # priority focus should surface at least the first few sections
    assert len(r["growth_areas"]) >= 3
    # Next steps deduped and non-empty
    assert len(r["next_steps"]) >= 1
    assert len(r["next_steps"]) == len({s for s in r["next_steps"]})


def test_build_pdf_returns_valid_bytes():
    answers = _answers_all(2)
    scores = compute_scores(answers)
    r = cp_report_content.build_report(scores=scores, answers=answers, parent_name="Test Parent")
    pdf = cp_report_pdf.build_coparenting_pdf(user_name="Test Parent", report=r)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    # ~5 KB minimum for the composed report
    assert len(pdf) > 3000


def test_filter_cp_report_selective_visibility():
    answers = _answers_all(2)
    scores = compute_scores(answers)
    r = cp_report_content.build_report(scores=scores, answers=answers, parent_name="X")
    filtered = cp_report_pdf.filter_cp_report(r, ["strengths", "next_steps"])
    assert filtered["strengths"] == []
    assert filtered["next_steps"] == []
    # Unmodified sections still present
    assert filtered["overall_rating"] == r["overall_rating"]
    assert filtered["sections"] == r["sections"]


def test_partial_answers_still_produce_report():
    # Only answer Section 1 completely; leave the rest untouched.
    answers = {q["id"]: 3 for q in SECTIONS[0]["questions"]}
    scores = compute_scores(answers)
    r = cp_report_content.build_report(scores=scores, answers=answers, parent_name=None)
    # Should not crash; overall may be "Not enough data" or a low tier.
    assert r["sections"][0]["rating"] in ("Good", "Excellent", "Fair", "Needs Improvement")
    for sec in r["sections"][1:]:
        assert sec["rating"] is None
        assert sec["answered"] == 0
