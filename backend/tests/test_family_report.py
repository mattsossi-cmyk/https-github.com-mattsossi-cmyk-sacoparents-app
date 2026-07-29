"""Unit tests for family_report_content + family_report_pdf (rebuild)."""
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

SN_DOC = {
    "report_id": "sn_x",
    "generated_at": "2026-02-02T00:00:00Z",
    "report": {
        "overall_rating": "Excellent Progress",
        "overall_summary": "SN summary.",
        "strengths": [{"section_id": "p5", "title": "Diagnosis knowledge", "detail": "solid"}],
        "growth_areas": [],
        "show_communication_toolkit": False,
        "communication_toolkit": [],
        "sections": [
            {"id": "p5", "number": 5, "name": "Diagnosis Knowledge", "rating": "Excellent", "avg": 4.0,
             "findings": ["knows well"], "recommendations": ["share reports"]},
        ],
        "next_steps": ["Attend next IEP"],
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
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=CP_DOC, sn_doc=SN_DOC, safety_doc=SAFETY_DOC)
    # Full CP + SN report embedded
    assert r["coparenting"]["report"]["sections"] == CP_DOC["report"]["sections"]
    assert r["coparenting"]["report"]["strengths"] == CP_DOC["report"]["strengths"]
    assert r["coparenting"]["report"]["growth_areas"] == CP_DOC["report"]["growth_areas"]
    assert r["coparenting"]["report"]["communication_toolkit"] == CP_DOC["report"]["communication_toolkit"]
    assert r["special_needs"]["report"]["sections"] == SN_DOC["report"]["sections"]
    # Safety summarised (identifiers stripped)
    assert r["safety"]["level"] == 3
    assert "high_concern_hits" not in r["safety"]
    assert "coercive_hits" not in r["safety"]
    # Combined next steps present with source tags
    steps = r["combined_next_steps"]
    assert steps[0]["source"] == "Safety"
    assert {s["source"] for s in steps} == {"Safety", "Co-Parenting", "Special Needs"}


def test_family_report_partial_sources():
    r = fc.build_family_report(parent_name=None, cp_doc=None, sn_doc=SN_DOC, safety_doc=None)
    assert r["included_sources"] == ["Special Needs Assessment"]
    assert "Missing from this report" in r["overall_summary"]
    assert r["coparenting"] is None
    assert r["safety"] is None


def test_family_report_pdf_bytes_and_size():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=CP_DOC, sn_doc=SN_DOC, safety_doc=SAFETY_DOC)
    pdf = fp.build_family_pdf(user_name="Sam Parent", report=r)
    assert pdf[:4] == b"%PDF"
    # Full-detail version — bigger than a "no sources" empty PDF.
    assert len(pdf) > 3000


def test_family_report_safety_only_still_renders():
    r = fc.build_family_report(parent_name="Sam Parent", cp_doc=None, sn_doc=None, safety_doc=SAFETY_DOC)
    pdf = fp.build_family_pdf(user_name="Sam Parent", report=r)
    assert pdf[:4] == b"%PDF"
