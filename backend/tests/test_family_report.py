"""Unit tests for family_report_content + family_report_pdf.

The Family Report stitches CP + SN v3 + Safety findings into one document.
"""
from __future__ import annotations

import family_report_content as fc
import family_report_pdf as fp


CP_REPORT_DOC = {
    "report_id": "cp_x",
    "generated_at": "2026-02-01T00:00:00Z",
    "report": {
        "overall_rating": "Building Progress",
        "overall_summary": "CP summary.",
        "strengths": [{"section_id": "s3", "title": "Educational Needs", "detail": "Both homes align."}],
        "growth_areas": [{"section_id": "s1", "title": "Communication", "rating": "Fair", "why_it_matters": "gaps", "first_step": "shared app"}],
        "show_communication_toolkit": True,
        "next_steps": ["Set weekly check-in", "Move to shared app"],
    },
}

SN_REPORT_DOC = {
    "report_id": "sn_x",
    "generated_at": "2026-02-02T00:00:00Z",
    "report": {
        "overall_rating": "Excellent Progress",
        "overall_summary": "SN summary.",
        "strengths": [{"section_id": "p5", "title": "Diagnosis knowledge", "detail": "solid"}],
        "growth_areas": [],
        "show_communication_toolkit": False,
        "next_steps": ["Attend next IEP"],
    },
}

SAFETY_DOC = {
    "level": 3,
    "pathway_title": "Written communication recommended",
    "pathway_headline": "Move to a shared parenting app",
    "pathway_summary": "Direct conversation is possible but written channels reduce friction.",
    "recommendations": ["Use a shared parenting app", "BIFF-style messages", "Weekly check-in"],
    "high_concern_hits": ["s1_q3"],       # MUST be stripped in composed output
    "coercive_hits": ["s1_q6"],           # MUST be stripped
    "section_1_yes_count": 2,             # MUST be stripped
    "section_2_concern_count": 3,         # MUST be stripped
    "created_at": "2026-02-03T00:00:00Z",
}


def test_family_report_all_three_sources():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=CP_REPORT_DOC, sn_doc=SN_REPORT_DOC, safety_doc=SAFETY_DOC)
    assert r["prepared_by"] == "Sam Parent"
    assert set(r["included_sources"]) == {"Co-Parenting Assessment", "Special Needs Assessment", "Family Violence & Communication Safety"}
    assert r["missing_sources"] == []
    assert r["coparenting"]["overall_rating"] == "Building Progress"
    assert r["special_needs"]["overall_rating"] == "Excellent Progress"
    assert r["safety"]["level"] == 3
    # Safety must NOT leak identifiers
    safety_out = r["safety"]
    assert "high_concern_hits" not in safety_out
    assert "coercive_hits" not in safety_out
    assert "section_1_yes_count" not in safety_out
    # Combined next steps: safety-first, then interleaved
    steps = r["combined_next_steps"]
    assert steps[0]["source"] == "Safety"
    sources = {s["source"] for s in steps}
    assert sources == {"Safety", "Co-Parenting", "Special Needs"}
    assert len(steps) <= 7


def test_family_report_partial_sources():
    r = fc.build_family_report(parent_name=None, cp_doc=None, sn_doc=SN_REPORT_DOC, safety_doc=None)
    assert r["included_sources"] == ["Special Needs Assessment"]
    assert set(r["missing_sources"]) == {"Co-Parenting Assessment", "Family Violence & Communication Safety"}
    assert r["coparenting"] is None
    assert r["safety"] is None
    assert r["special_needs"]["overall_rating"] == "Excellent Progress"
    assert "Not yet completed" not in r["overall_summary"]  # missing text appears via a slightly different phrase
    assert "Missing from this report" in r["overall_summary"]


def test_family_report_pdf_bytes():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=CP_REPORT_DOC, sn_doc=SN_REPORT_DOC, safety_doc=SAFETY_DOC)
    pdf = fp.build_family_pdf(user_name="Sam Parent", report=r)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 3000


def test_family_report_safety_only_still_renders():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=None, sn_doc=None, safety_doc=SAFETY_DOC)
    pdf = fp.build_family_pdf(user_name="Sam Parent", report=r)
    assert pdf[:4] == b"%PDF"
