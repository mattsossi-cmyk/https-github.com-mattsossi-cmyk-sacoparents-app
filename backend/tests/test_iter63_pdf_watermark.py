"""Iteration 63 tests — PDF watermark ("REVIEW BEFORE SHARING").

Runs the six live PDF generators end-to-end and asserts each produced
PDF's content stream contains the watermark literal. Some builders keep
fpdf2's default zlib compression, so we decompress each `/FlateDecode`
stream during search.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

WATERMARK = "REVIEW BEFORE SHARING"


def _pdf_contains_watermark(pdf_bytes: bytes, tmp_path: Path) -> bool:  # noqa: ARG001
    """Return True if the PDF's content stream contains the watermark.

    Two cases:
      1. Some PDF generators here disable compression (SNC, deep dives).
         In that case the literal watermark string is right in the raw
         bytes as a `(REVIEW BEFORE SHARING) Tj` operator.
      2. The Summary and Agreement builders leave fpdf2's default zlib
         compression on. We decompress each `/FlateDecode` stream and
         search inside.
    """
    if WATERMARK.encode() in pdf_bytes:
        return True
    # Fall through: try each compressed content stream.
    import re
    import zlib
    for m in re.finditer(
        rb"<<[^<]*/Filter\s*/FlateDecode[^<]*>>\s*stream\n(.+?)\nendstream",
        pdf_bytes, re.DOTALL,
    ):
        try:
            raw = zlib.decompress(m.group(1))
        except zlib.error:
            continue
        if WATERMARK.encode() in raw:
            return True
    return False


class TestPdfWatermarks:
    def test_snc_report_pdf_has_watermark(self, tmp_path):
        from snc2_report_pdf import build_snc2_pdf
        sample = {
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
        assert _pdf_contains_watermark(build_snc2_pdf(report=sample), tmp_path)

    def test_edu_deep_dive_pdf_has_watermark(self, tmp_path):
        from edu_deep_report import build_deep_dive_pdf
        sample = {
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
        assert _pdf_contains_watermark(build_deep_dive_pdf(report=sample), tmp_path)

    def test_psych_deep_dive_pdf_has_watermark(self, tmp_path):
        from psych_deep_report import build_deep_dive_pdf
        sample = {
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
        assert _pdf_contains_watermark(build_deep_dive_pdf(report=sample), tmp_path)

    def test_mediation_summary_pdf_has_watermark(self, tmp_path):
        from pdf_service import build_summary_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        assert _pdf_contains_watermark(
            build_summary_pdf("Sam", s), tmp_path,
        )

    def test_agreement_pdf_has_watermark(self, tmp_path):
        from pdf_service import build_agreement_pdf
        s = {
            "goals": "g", "agenda": "a", "issues": "i",
            "communication_style": "c", "readiness": "r",
            "notes_for_mediator": "n", "top_priorities": [],
        }
        assert _pdf_contains_watermark(
            build_agreement_pdf("Sam", s), tmp_path,
        )

    def test_snc_comparison_pdf_has_watermark(self, tmp_path):
        from snc2_comparison_pdf import build_comparison_pdf
        cmp = {
            "parent_a": "S", "parent_b": "R",
            "child": {"name": "A"}, "pathways": {}, "sections": [],
            "summary": {"aligned_pct": 50, "total_items": 0},
            "highlights": [],
        }
        assert _pdf_contains_watermark(
            build_comparison_pdf(comparison=cmp, safety_notice="safety"),
            tmp_path,
        )

    def test_edu_deep_comparison_pdf_has_watermark(self, tmp_path):
        from edu_deep_comparison_pdf import build_comparison_pdf
        cmp = {
            "parent_a_name": "S", "parent_b_name": "R",
            "sections": [], "alignment_labels": {},
        }
        assert _pdf_contains_watermark(
            build_comparison_pdf(comparison=cmp, safety_notice="safety"),
            tmp_path,
        )


class TestPdfProvenanceFooter:
    """Sanity check that iter62's provenance block still renders after the
    watermark was layered under it."""

    def test_snc_report_pdf_has_provenance(self, tmp_path):
        from snc2_report_pdf import build_snc2_pdf
        sample = {
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
        b = build_snc2_pdf(report=sample)
        p = tmp_path / "c.pdf"; p.write_bytes(b)
        r = subprocess.run(
            ["pdftotext", "-layout", str(p), "-"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        assert "HOW THIS REPORT WAS BUILT" in r.stdout
        assert "RULE-BASED" in r.stdout
        assert "GENERATIVE" in r.stdout
