"""Tests for the Special Needs report content + PDF (9-section framework)."""
from __future__ import annotations

from sn_v3_questions import SECTIONS
from sn_v3_scoring import compute_scores
import sn_v3_report_content as rc
import sn_v3_report_pdf as rp


def _answers(v: int) -> dict:
    a = {}
    for s in SECTIONS:
        for q in s["questions"]:
            a[q["id"]] = v
    return a


def test_report_shape_all_strong():
    a = _answers(4)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a, parent_name="Sam Parent")
    assert r["prepared_by"] == "Sam Parent"
    assert r["overall_rating"] == "Excellent Progress"
    assert r["framework"].startswith("SA CoParents Special Needs")
    assert len(r["sections"]) == 9
    # `domains` alias mirrors sections
    assert r["domains"] == r["sections"]
    assert all(sec["rating"] == "Excellent" for sec in r["sections"])
    assert r["strengths"], "strong ratings should surface strengths"


def test_report_early_progress_when_all_weak():
    a = _answers(0)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a)
    assert r["overall_rating"] == "Early Progress"
    # Communication toolkit surfaces because Section 6 is Needs Improvement.
    assert r["show_communication_toolkit"] is True
    assert r["communication_toolkit"], "toolkit should be non-empty when shown"
    assert r["growth_areas"], "weak sections should surface priority focus"


def test_no_safety_content_in_report():
    a = _answers(0)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a)
    # Nothing safety-related in the report
    assert "safety_triggered" not in r
    joined = " ".join(r["next_steps"]).lower()
    assert "safety" not in joined
    joined_summary = (r["overall_summary"] or "").lower()
    assert "safety" not in joined_summary


def test_report_pdf_renders_bytes():
    a = _answers(2)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a, parent_name="Test Parent")
    pdf = rp.build_special_needs_pdf(user_name="Test Parent", report=r)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 3000


def test_intake_flows_through_to_report():
    a = _answers(3)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a, intake={"child_age": 8, "diagnoses": "ADHD"})
    assert r["intake"]["child_age"] == 8
    assert r["intake"]["diagnoses"] == "ADHD"
