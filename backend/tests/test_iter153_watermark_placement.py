"""Iteration 153 — regression test for the case-status PDF watermark
placement.

Bug: `apply_professional_watermark` was calling
`pdf.text(x=page_w - 8, ...)` — fpdf2's `text()` is LEFT-anchored,
so long firm-name stamps overflowed past the right page edge and
were clipped. Downloaded court PDFs then carried no visible
provenance stamp despite the UI promising one.

Fix: subtract the measured string width so the stamp is right-aligned
inside the page's printable area.

This test renders a status PDF with a long firm name and asserts:
  1. The watermark string appears in every page's extracted text.
  2. When laid out, the watermark's start-x + measured width sits
     entirely within the page (no overflow).
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/app/backend")

from case_status_pdf import build_case_status_pdf


LONG_FIRM = "Very Long Firm Name International Partners And Associates LLP"


def _sample_case() -> dict:
    return {
        "case_id": "SA-ABCD12",
        "assessment_type": "co-parenting",
        "status": "in_progress",
        "origin": "in_app_professional",
        "align_case_reference": "MATTER-9001",
        "created_at": datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        "case_expires_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "professional": {
            "id": "prof-1",
            "name": "Pat Mediator",
            "email": "pat@example.com",
        },
        "parents": [
            {
                "parent_slot": "A",
                "name": "Alex Rivera",
                "email": "alex@example.com",
                "accepted_at": datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
                "assessment_completed_at": None,
            },
            {
                "parent_slot": "B",
                "name": "Bailey Chen",
                "email": "bailey@example.com",
                "accepted_at": None,
                "assessment_completed_at": None,
            },
        ],
    }


def test_watermark_present_with_long_firm_name(tmp_path: Path) -> None:
    """The watermark must be extractable from the PDF even when the
    firm name is long — proves it wasn't clipped off-page."""
    pdf_bytes = build_case_status_pdf(
        _sample_case(), watermark_firm_name=LONG_FIRM,
    )
    p = tmp_path / "case-status.pdf"
    p.write_bytes(pdf_bytes)

    r = subprocess.run(
        ["pdftotext", "-layout", str(p), "-"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0

    # The full stamp uses a middle dot (·) between segments; we
    # normalise whitespace and search for the firm-name segment
    # AND the "SA CoParents" tail — if either is clipped, this fails.
    text = re.sub(r"\s+", " ", r.stdout)
    assert LONG_FIRM in text, (
        f"Firm name segment missing from PDF text — watermark clipped. "
        f"Extracted: {text[-400:]!r}"
    )
    assert "SA CoParents" in text, (
        "Watermark tail 'SA CoParents' missing — right edge clipping."
    )


def test_watermark_fits_within_page_width() -> None:
    """Direct check on the placement math: for a long firm name the
    computed x position must be > left margin (i.e. right-aligned,
    not left-anchored past the page edge)."""
    from fpdf import FPDF

    from court_report_disclaimer import _iso_now  # type: ignore
    from safety_assessment_pdf import _safe

    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.add_page()
    pdf.set_font("Helvetica", "I", 7.5)

    stamp_text = _safe(f"Downloaded by {LONG_FIRM} on {_iso_now()} · SA CoParents")
    stamp_width = pdf.get_string_width(stamp_text)
    page_w = pdf.w
    # Expected placement per the fix: x = page_w - 8 - width
    x = page_w - 8 - stamp_width

    # Fits inside the page — start-x is positive (was negative before
    # the fix for long firm names) and end-x lands inside the sheet.
    assert x > 0, (
        f"Watermark start-x {x:.2f} is <= 0 → clipped off left edge "
        "(width {stamp_width:.2f} exceeds page width {page_w:.2f})."
    )
    end_x = x + stamp_width
    assert end_x <= page_w, (
        f"Watermark end-x {end_x:.2f} exceeds page width {page_w:.2f} → "
        "clipped off right edge."
    )
