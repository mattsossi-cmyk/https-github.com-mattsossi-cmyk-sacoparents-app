"""Unit tests for the Special Needs v3 report content + PDF builders.

Mirrors test_cp_report.py so the two dynamic pipelines stay in lockstep.
"""
from __future__ import annotations

from sn_v3_questions import SECTIONS
from sn_v3_scoring import compute_scores
import sn_v3_report_content
import sn_v3_report_pdf


def _answers_all(value: int) -> dict:
    return {q["id"]: value for s in SECTIONS for q in s["questions"]}


def test_build_report_all_excellent_shape():
    answers = _answers_all(4)
    for s in SECTIONS:
        for q in s["questions"]:
            if q.get("reverse"):
                answers[q["id"]] = 0
    scores = compute_scores(answers)
    r = sn_v3_report_content.build_report(scores=scores, answers=answers, parent_name="Sam Parent")

    assert r["overall_rating"] == "Excellent Progress"
    assert r["prepared_by"] == "Sam Parent"
    assert r["framework"] == "10-principle special-needs co-parenting"
    assert len(r["sections"]) == 10
    assert r["show_communication_toolkit"] is False
    assert r["communication_toolkit"] == []
    for sec in r["sections"]:
        assert sec["rating"] == "Excellent"
        assert sec["findings"]
        assert sec["recommendations"]


def test_build_report_needs_improvement_triggers_toolkit_and_priority():
    answers = _answers_all(0)
    for s in SECTIONS:
        for q in s["questions"]:
            if q.get("reverse"):
                answers[q["id"]] = 4
    scores = compute_scores(answers)
    r = sn_v3_report_content.build_report(scores=scores, answers=answers, parent_name=None)

    assert r["show_communication_toolkit"] is True
    assert len(r["communication_toolkit"]) == 5
    assert r["overall_rating"] == "Early Progress"
    assert len(r["growth_areas"]) >= 3
    assert len(r["next_steps"]) >= 1
    assert len(r["next_steps"]) == len({s for s in r["next_steps"]})


def test_build_pdf_returns_valid_bytes():
    answers = _answers_all(2)
    scores = compute_scores(answers)
    r = sn_v3_report_content.build_report(scores=scores, answers=answers, parent_name="Test Parent")
    pdf = sn_v3_report_pdf.build_special_needs_pdf(user_name="Test Parent", report=r)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 3000


def test_filter_sn_v3_report_selective_visibility():
    answers = _answers_all(2)
    scores = compute_scores(answers)
    r = sn_v3_report_content.build_report(scores=scores, answers=answers, parent_name="X")
    filtered = sn_v3_report_pdf.filter_sn_v3_report(r, ["strengths", "next_steps"])
    assert filtered["strengths"] == []
    assert filtered["next_steps"] == []
    assert filtered["overall_rating"] == r["overall_rating"]
    assert filtered["sections"] == r["sections"]


def test_partial_answers_still_produce_report():
    answers = {q["id"]: 3 for q in SECTIONS[0]["questions"]}
    scores = compute_scores(answers)
    r = sn_v3_report_content.build_report(scores=scores, answers=answers, parent_name=None)
    assert r["sections"][0]["rating"] in ("Good", "Excellent", "Fair", "Needs Improvement")
    for sec in r["sections"][1:]:
        assert sec["rating"] is None
        assert sec["answered"] == 0
