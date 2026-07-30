"""Regression tests for Phase 2 — selective section sharing on reports.

Covers:
  - Section catalog endpoint returns each report type's schema.
  - clean_excluded strips unknown + locked keys and returns a sorted list.
  - PDF filter helpers zero out excluded blocks (via signature inspection).
  - JWT share token carries `ex` payload when excluded_sections is provided.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import pytest

from report_visibility import (
    REPORT_SECTIONS,
    SAFETY_LOCKED_SECTIONS,
    clean_excluded,
    filter_summary,
    filter_agreement,
    filter_sn_report,
    valid_keys,
)


def test_report_types_present():
    assert set(REPORT_SECTIONS.keys()) == {"summary", "agreement", "sn_report", "safety", "cp_report"}
    for report_type, sections in REPORT_SECTIONS.items():
        # Every section has stable key + human-readable label
        for s in sections:
            assert s["key"] and s["label"] and s["description"]


def test_clean_excluded_strips_unknown_and_locked():
    # Unknown keys dropped
    assert clean_excluded("summary", ["top_concerns", "bogus_key"]) == ["top_concerns"]
    # Locked safety keys dropped
    assert clean_excluded("safety", ["section_1", "pathway", "texas_resources"]) == ["section_1"]
    # Deterministic order (sorted)
    assert clean_excluded("summary", ["notes_for_mediator", "top_concerns"]) == ["notes_for_mediator", "top_concerns"]
    # None + empty → []
    assert clean_excluded("summary", None) == []
    assert clean_excluded("summary", []) == []


def test_safety_lock_covers_hotlines_and_pathway():
    assert "pathway" in SAFETY_LOCKED_SECTIONS
    assert "texas_resources" in SAFETY_LOCKED_SECTIONS


def test_filter_summary_zeroes_excluded_blocks():
    summary = {
        "top_concerns": ["a", "b"],
        "priority_agenda": [{"rank": 1, "topic": "x"}],
        "notes_for_mediator": "Please keep it kid-focused.",
        "communication_goals": ["gentle", "clear"],
        "changes_since_last": "we grew",
    }
    filtered = filter_summary(summary, ["top_concerns", "notes_for_mediator", "changes_since_last"])
    assert filtered["top_concerns"] == []
    assert filtered["notes_for_mediator"] == ""
    assert filtered["changes_since_last"] == ""
    # Untouched
    assert filtered["priority_agenda"] == [{"rank": 1, "topic": "x"}]
    assert filtered["communication_goals"] == ["gentle", "clear"]


def test_filter_agreement_zeroes_arrays():
    ag = {
        "communication": [{"area": "texts", "agreement": "biff"}],
        "shared_goals": ["safety"],
        "closing_note": "we're aligned",
    }
    filtered = filter_agreement(ag, ["communication", "closing_note"])
    assert filtered["communication"] == []
    assert filtered["closing_note"] == ""
    assert filtered["shared_goals"] == ["safety"]


def test_filter_sn_report_zeroes_blocks():
    rpt = {
        "child_profile": {"summary": "s"},
        "agreement_areas": [{"title": "x", "detail": "y"}],
        "coordination_gaps": [{"title": "a", "detail": "b"}],
        "priorities": {"immediate": ["stuff"]},
        "structure_reasoning": "cooperative",
        "action_plan": [{"need": "n"}],
    }
    filtered = filter_sn_report(rpt, ["coordination_gaps", "structure"])
    assert filtered["coordination_gaps"] == []
    assert filtered["structure_reasoning"] == ""
    assert filtered["agreement_areas"] == [{"title": "x", "detail": "y"}]
    assert filtered["action_plan"] == [{"need": "n"}]


def test_valid_keys():
    assert "top_concerns" in valid_keys("summary")
    assert "communication" in valid_keys("agreement")
    assert "child_profile" in valid_keys("sn_report")
    assert "section_1" in valid_keys("safety")


def test_share_token_carries_excluded():
    from auth import create_share_token, decode_share_token
    tok = create_share_token("summary", "sum_x", "user_y", excluded_sections=["top_concerns", "priority_agenda"])
    payload = decode_share_token(tok)
    assert payload is not None
    assert payload["doc_type"] == "summary"
    assert payload["ex"] == ["priority_agenda", "top_concerns"]  # sorted

    # No excluded → no "ex" key
    tok2 = create_share_token("agreement", "agr_x", "user_y")
    payload2 = decode_share_token(tok2)
    assert payload2 is not None
    assert "ex" not in payload2


def test_pdf_builders_accept_excluded_kwarg():
    """Smoke test: the PDF builders should accept the excluded_sections kwarg
    and still emit a non-empty PDF."""
    from pdf_service import build_summary_pdf, build_agreement_pdf
    from safety_assessment_pdf import build_safety_assessment_pdf

    summary = {
        "readiness_label": "Preparing",
        "readiness_score": 60,
        "child_goals_summary": "safety first",
        "top_concerns": ["a"],
        "priority_agenda": [{"rank": 1, "topic": "x", "category": "c"}],
        "flexibility_areas": ["a"],
        "communication_goals": ["b"],
        "notes_for_mediator": "note",
    }
    pdf_full = build_summary_pdf("Parent", summary)
    pdf_min = build_summary_pdf(
        "Parent",
        summary,
        excluded_sections=["top_concerns", "notes_for_mediator", "priority_agenda"],
    )
    assert pdf_full.startswith(b"%PDF-") and pdf_min.startswith(b"%PDF-")
    assert len(pdf_min) < len(pdf_full)  # smaller when sections skipped

    agreement = {
        "shared_goals": ["a"],
        "communication": [{"area": "x", "agreement": "y"}],
        "child_needs": [],
        "household_rules": [],
        "priority_items": [],
        "closing_note": "z",
    }
    ap_full = build_agreement_pdf("Parent", agreement)
    ap_min = build_agreement_pdf("Parent", agreement, excluded_sections=["communication", "closing_note"])
    assert ap_full.startswith(b"%PDF-") and ap_min.startswith(b"%PDF-")

    sn_report = {
        "child_profile": {"summary": "s", "strengths": ["ok"], "what_helps": [], "support_needs": []},
        "agreement_areas": [{"title": "t", "detail": "d"}],
        "coordination_gaps": [{"title": "t", "detail": "d"}],
        "priorities": {"immediate": ["x"], "thirty_day": [], "longer_term": []},
        "structure_reasoning": "cooperative",
        "action_plan": [{"need": "n", "action": "a", "responsible": "r", "channel": "c", "review": "r"}],
        "disclaimer": "Not clinical advice.",
    }
    _ = sn_report  # kept for future rebuild; no PDF assertion right now.

    safety = build_safety_assessment_pdf(
        user_name="Friend",
        generated_at="2026-01-01T00:00:00",
        result={"level": 2, "pathway_tone": "info", "pathway_title": "Structured", "pathway_summary": "sum"},
        section_1_rows=[{"text": "q1", "answer": "no"}],
        section_2_rows=[{"text": "q1", "answer": "yes"}],
        texas_resource_block="988 · 800-799-7233 · 911",
        excluded_sections=["section_1"],
    )
    assert safety.startswith(b"%PDF-")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
