"""Unit tests for family_report_content + family_report_pdf.

Special Needs is intentionally not part of the Family Report right now
(it is being reworked into a new framework).
"""
from __future__ import annotations

import family_report_content as fc
import family_report_pdf as fp


CP_DOC = {
    "report_id": "cp_x",
    "generated_at": "2026-02-01T00:00:00Z",
    "report": {
        "overall_rating": "Building Progress",
        "overall_summary": "CP summary.",
        "strengths": [{"section_id": "s3", "title": "Educational Needs", "detail": "Both homes align."}],
        "growth_areas": [{"section_id": "s1", "title": "Communication", "rating": "Fair",
                          "why_it_matters": "gaps", "first_step": "shared app"}],
        "show_communication_toolkit": True,
        "communication_toolkit": [{"title": "BIFF", "detail": "Brief, Informative, Friendly, Firm."}],
        "sections": [
            {"id": "s1", "number": 1, "name": "Communication", "rating": "Fair", "avg": 2.0,
             "goal": "Share information reliably.", "findings": ["gap"], "recommendations": ["shared app"]},
            {"id": "s3", "number": 3, "name": "Education", "rating": "Good", "avg": 3.0,
             "findings": ["aligned"], "recommendations": ["keep going"]},
        ],
        "next_steps": ["Set weekly check-in", "Move to shared app"],
    },
}

SAFETY_DOC = {
    "result": {
        "level": 3,
        "pathway_title": "Assisted Problem-Solving",
        "pathway_headline": "Move to written channels.",
        "pathway_summary": "Direct conversation is possible but written is safer.",
        "recommendations": ["Use a shared parenting app", "BIFF messages", "Weekly check-in"],
    },
    "high_concern_hits": ["s1_q3"],
    "coercive_hits": ["s1_q6"],
    "section_1_yes_count": 2,
    "created_at": "2026-02-03T00:00:00Z",
}


def test_family_report_embeds_full_source_content():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=CP_DOC, safety_doc=SAFETY_DOC)
    assert r["coparenting"]["report"]["sections"] == CP_DOC["report"]["sections"]
    assert r["coparenting"]["report"]["strengths"] == CP_DOC["report"]["strengths"]
    assert r["safety"]["level"] == 3
    # Identifying detail stripped from safety
    assert "high_concern_hits" not in r["safety"]
    assert "coercive_hits" not in r["safety"]
    # Combined next steps only from Safety + Co-Parenting
    steps = r["combined_next_steps"]
    assert steps[0]["source"] == "Safety"
    assert {s["source"] for s in steps} == {"Safety", "Co-Parenting"}


def test_family_report_partial_sources_cp_only():
    r = fc.build_family_report(parent_name=None, cp_doc=CP_DOC, safety_doc=None)
    assert r["included_sources"] == ["Co-Parenting Assessment"]
    assert "Missing from this report" in r["overall_summary"]
    assert r["safety"] is None


def test_family_report_pdf_bytes_and_size():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=CP_DOC, safety_doc=SAFETY_DOC)
    pdf = fp.build_family_pdf(user_name="Sam Parent", report=r)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 3000


def test_family_report_safety_only_still_renders():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=None, safety_doc=SAFETY_DOC)
    pdf = fp.build_family_pdf(user_name="Sam Parent", report=r)
    assert pdf[:4] == b"%PDF"
