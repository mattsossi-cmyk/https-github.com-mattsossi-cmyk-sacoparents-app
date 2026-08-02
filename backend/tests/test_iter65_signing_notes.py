"""Iteration 65 tests — Signed PDFs *with an optional signing note*.

Confirms every PDF builder that already accepts `signed_by` + `signed_at`
now also honours `signed_note`, prints it inside the PDF, silently
truncates over-length notes, and leaves the note absent when not passed.
"""
from __future__ import annotations

import re
import sys
import zlib
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")


NOTE = "Prepared for our 12 Feb mediation session"
LONG_NOTE = "x" * 500  # will be truncated to 120 chars by sign_kwargs
_SIG_MARKER = b"Signed by"


def _pdf_contains(pdf_bytes: bytes, needle: bytes) -> bool:
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


def _dd_sample():
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


class TestSignKwargs:
    """`sign_kwargs` should attach or drop the note as expected."""

    def test_no_sign_returns_empty(self):
        from pdf_signing import sign_kwargs
        assert sign_kwargs(False, "Sam", "hello") == {}
        assert sign_kwargs(True, None, "hello") == {}

    def test_sign_no_note(self):
        from pdf_signing import sign_kwargs
        out = sign_kwargs(True, "Sam", "")
        assert out["signed_by"] == "Sam"
        assert "signed_at" in out
        assert "signed_note" not in out

    def test_sign_with_note(self):
        from pdf_signing import sign_kwargs
        out = sign_kwargs(True, "Sam", NOTE)
        assert out["signed_note"] == NOTE

    def test_note_truncated(self):
        from pdf_signing import sign_kwargs
        out = sign_kwargs(True, "Sam", LONG_NOTE)
        assert "signed_note" in out
        assert len(out["signed_note"]) == 120

    def test_whitespace_note_dropped(self):
        from pdf_signing import sign_kwargs
        out = sign_kwargs(True, "Sam", "   \n \t")
        assert "signed_note" not in out


class TestNoteInPdfs:
    def test_snc(self):
        from snc2_report_pdf import build_snc2_pdf
        b = build_snc2_pdf(report=_snc_sample(), signed_by="Sam",
                           signed_at=_now_iso(), signed_note=NOTE)
        assert _pdf_contains(b, _SIG_MARKER)
        assert _pdf_contains(b, NOTE.encode())

    def test_edu(self):
        from edu_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(report=_dd_sample(), signed_by="Sam",
                                signed_at=_now_iso(), signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())

    def test_psych(self):
        from psych_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(report=_dd_sample(), signed_by="Sam",
                                signed_at=_now_iso(), signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())

    def test_med(self):
        from med_deep_report import build_deep_dive_pdf
        b = build_deep_dive_pdf(report=_dd_sample(), signed_by="Sam",
                                signed_at=_now_iso(), signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())

    def test_summary(self):
        from pdf_service import build_summary_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        b = build_summary_pdf("Sam", s, signed_by="Sam",
                              signed_at=_now_iso(), signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())

    def test_agreement(self):
        from pdf_service import build_agreement_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        b = build_agreement_pdf("Sam", s, signed_by="Sam",
                                signed_at=_now_iso(), signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())

    def test_snc_compare(self):
        from snc2_comparison_pdf import build_comparison_pdf
        cmp = {
            "parent_a": "S", "parent_b": "R",
            "child": {"name": "A"}, "pathways": {}, "sections": [],
            "summary": {"aligned_pct": 50, "total_items": 0},
            "highlights": [],
        }
        b = build_comparison_pdf(comparison=cmp, safety_notice="s",
                                 signed_by="Sam", signed_at=_now_iso(),
                                 signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())

    def test_edu_compare(self):
        from edu_deep_comparison_pdf import build_comparison_pdf
        cmp = {"parent_a_name": "S", "parent_b_name": "R",
               "sections": [], "alignment_labels": {}}
        b = build_comparison_pdf(comparison=cmp, safety_notice="s",
                                 signed_by="Sam", signed_at=_now_iso(),
                                 signed_note=NOTE)
        assert _pdf_contains(b, NOTE.encode())


class TestNoteAbsentWhenNotSigned:
    def test_snc_without_signature_has_no_note(self):
        from snc2_report_pdf import build_snc2_pdf
        b = build_snc2_pdf(report=_snc_sample(), signed_note=NOTE)
        # Note kwargs alone shouldn't render because signed_by/at are missing.
        assert not _pdf_contains(b, NOTE.encode())
