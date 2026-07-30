"""Tests for the redesigned Special Needs report content + PDF."""
from __future__ import annotations

from sn_v3_questions import DOMAINS
from sn_v3_scoring import compute_scores
import sn_v3_report_content as rc
import sn_v3_report_pdf as rp


def _answers(v: int) -> dict:
    a = {}
    for d in DOMAINS:
        for q in d["questions"]:
            a[q["id"]] = 0 if q.get("safety_flag") else v
    return a


def test_report_shape_all_strong():
    a = _answers(4)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a, parent_name="Sam Parent")
    assert r["prepared_by"] == "Sam Parent"
    assert r["overall_rating"] == "Existing Strength Overall"
    assert r["safety_triggered"] is False
    assert r["framework"].startswith("SA CoParents Special Needs")
    # All 10 domains represented; safety domain still included
    assert len(r["domains"]) == 10
    # Legacy sections alias should mirror domains
    assert r["sections"] is r["domains"]


def test_report_safety_triggered_paths():
    a = _answers(3)
    a["d10_q1"] = 4
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a)
    assert r["safety_triggered"] is True
    assert r["overall_rating"] == "Safety-Sensitive Review Recommended"
    assert r["next_steps"] and "safety" in r["next_steps"][0].lower()


def test_report_pdf_renders_bytes():
    a = _answers(2)
    s = compute_scores(a)
    r = rc.build_report(scores=s, answers=a, parent_name="Test Parent")
    pdf = rp.build_special_needs_pdf(user_name="Test Parent", report=r)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 3000
