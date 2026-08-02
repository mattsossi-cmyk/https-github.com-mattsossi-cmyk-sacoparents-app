"""Iteration 64 tests — Signed & timestamped PDF downloads.

Verifies that every PDF builder respects the `signed_by` + `signed_at`
kwargs by embedding the "Signed by X | YYYY UTC" line in each generated
PDF's content stream. Also confirms that omitting the kwargs produces
an unsigned PDF (parity with iter63 watermark tests).
"""
from __future__ import annotations

import re
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/app/backend")

_SIG_MARKER = b"Signed by"


def _pdf_contains(pdf_bytes: bytes, needle: bytes) -> bool:
    """Search raw + zlib-decompressed content streams for `needle`."""
    if needle in pdf_bytes:
        return True
    for m in re.finditer(
        rb"<<[^<]*/Filter\s*/FlateDecode[^<]*>>\s*stream\n(.+?)\nendstream",
        pdf_bytes, re.DOTALL,
    ):
        try:
            if needle in zlib.decompress(m.group(1)):
                return True
        except zlib.error:
            continue
    return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_dd_report():
    return {
        "cover": {"parent_name": "Sam", "child_name": "Alex"},
        "overview": {"purpose_bullets": ["A"]},
        "support_summary": {}, "child_profile": {},
        "school_involvement": {}, "co_parenting_assessment": {},
        "support_level": {"label": "Developing"},
        "action_plan": [], "final_summary": "sum",
        "foundation_statement": "x",
        "questions_for_school_or_parent": [],
        "practical_options": [],
        "disclaimer": "D",
    }


class TestSignedSnc:
    def test_signed_off_by_default(self):
        from snc2_report_pdf import build_snc2_pdf
        sample = _snc_sample()
        assert not _pdf_contains(build_snc2_pdf(report=sample), _SIG_MARKER)

    def test_signed_on_when_requested(self):
        from snc2_report_pdf import build_snc2_pdf
        sample = _snc_sample()
        b = build_snc2_pdf(report=sample, signed_by="Sam Nkosi", signed_at=_now_iso())
        assert _pdf_contains(b, _SIG_MARKER)
        assert _pdf_contains(b, b"Sam Nkosi")


class TestSignedDeepDives:
    def test_edu_signed(self):
        from edu_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(
            report=_sample_dd_report(), signed_by="Alex Jones", signed_at=_now_iso(),
        )
        assert _pdf_contains(b, _SIG_MARKER)
        assert _pdf_contains(b, b"Alex Jones")

    def test_psych_signed(self):
        from psych_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(
            report=_sample_dd_report(), signed_by="Rin Tanaka", signed_at=_now_iso(),
        )
        assert _pdf_contains(b, _SIG_MARKER)
        assert _pdf_contains(b, b"Rin Tanaka")

    def test_med_signed(self):
        from med_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(
            report=_sample_dd_report(), signed_by="Marisol Diaz", signed_at=_now_iso(),
        )
        assert _pdf_contains(b, _SIG_MARKER)
        assert _pdf_contains(b, b"Marisol Diaz")

    def test_edu_unsigned_absent(self):
        from edu_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(report=_sample_dd_report())
        assert not _pdf_contains(b, _SIG_MARKER)


class TestSignedMediation:
    def test_summary_signed(self):
        from pdf_service import build_summary_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        b = build_summary_pdf("Sam", s, signed_by="Sam", signed_at=_now_iso())
        assert _pdf_contains(b, _SIG_MARKER)

    def test_summary_unsigned(self):
        from pdf_service import build_summary_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        b = build_summary_pdf("Sam", s)
        assert not _pdf_contains(b, _SIG_MARKER)

    def test_agreement_signed(self):
        from pdf_service import build_agreement_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        b = build_agreement_pdf("Sam", s, signed_by="Sam", signed_at=_now_iso())
        assert _pdf_contains(b, _SIG_MARKER)


class TestSignedComparisons:
    def test_snc_compare_signed(self):
        from snc2_comparison_pdf import build_comparison_pdf
        cmp = {
            "parent_a": "S", "parent_b": "R",
            "child": {"name": "A"}, "pathways": {}, "sections": [],
            "summary": {"aligned_pct": 50, "total_items": 0},
            "highlights": [],
        }
        b = build_comparison_pdf(
            comparison=cmp, safety_notice="s",
            signed_by="Sam", signed_at=_now_iso(),
        )
        assert _pdf_contains(b, _SIG_MARKER)

    def test_edu_compare_signed(self):
        from edu_deep_comparison_pdf import build_comparison_pdf
        cmp = {"parent_a_name": "S", "parent_b_name": "R",
               "sections": [], "alignment_labels": {}}
        b = build_comparison_pdf(
            comparison=cmp, safety_notice="s",
            signed_by="Sam", signed_at=_now_iso(),
        )
        assert _pdf_contains(b, _SIG_MARKER)


def _snc_sample():
    return {
        "intro": {"title": "X", "body": "y"},
        "family_situation": {}, "areas_of_need": {}, "strengths": {},
        "challenges": {}, "child_impact": {}, "detailed_findings": {},
        "parent_alignment": {},
        "recommended_structure": {
            "structure_name": "S", "rationale": "r",
            "safeguards": [], "safety_notice": "",
        },
        "disclaimer": "D",
    }
