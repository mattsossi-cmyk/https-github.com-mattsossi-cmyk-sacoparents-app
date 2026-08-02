"""Subtle diagonal "REVIEW BEFORE SHARING" watermark shared by every PDF.

The watermark sits BEHIND content (drawn during `header()`) so text and
tables stay perfectly readable while a very light-grey diagonal reminder
runs across each page. Purpose: any recipient of a stray PDF sees at a
glance that the report should be reviewed before being relied upon.

Design goals:
  * Absolutely no interference with report content — pale grey text only.
  * No effect on page numbering or margins — uses `set_xy`, restores state.
  * Works with every FPDF subclass in this backend (Summary, Agreement,
    SNC, all Deep Dive journeys, both compares) via a single `stamp_watermark`.
  * Skips cover pages if the caller asks — set `pdf._skip_watermark = True`
    on the page before drawing (used by poster covers so the branding
    isn't cluttered).
"""
from __future__ import annotations

from typing import Any


_WATERMARK_TEXT = "REVIEW BEFORE SHARING"

# Very light grey — visible enough to notice, transparent-feeling enough
# to sit under normal body text without competing for attention.
_WATERMARK_GREY = (215, 210, 220)


def stamp_watermark(pdf: Any, text: str = _WATERMARK_TEXT) -> None:
    """Draw the diagonal watermark centred on the current page.

    Call from a PDF class's ``header()`` so it renders BEFORE content.
    Safe to call multiple times — always restores font, colour, XY.
    """
    if getattr(pdf, "_skip_watermark", False):
        return

    # Snapshot state we're going to touch.
    prev_x, prev_y = pdf.get_x(), pdf.get_y()
    prev_font_family = pdf.font_family
    prev_font_style = pdf.font_style
    prev_font_size = pdf.font_size_pt
    # Text colour tuple varies; setting a fresh colour is enough — callers
    # who need a specific ink already re-set it right before drawing.

    # A4 default: page W ~= 210mm, H ~= 297mm. Use pdf.w / pdf.h for safety.
    cx = pdf.w / 2.0
    cy = pdf.h / 2.0

    # ~48pt bold ish for A4; scales gently if page is smaller.
    size_pt = max(28.0, min(52.0, pdf.w * 0.22))

    pdf.set_font("Helvetica", "B", size_pt)
    pdf.set_text_color(*_WATERMARK_GREY)

    # Draw rotated. fpdf2's `rotation` context manager rotates around a point.
    # We use `text()` (not `cell()`) because at large font sizes cell can
    # get clipped by page boundaries even after rotation.
    with pdf.rotation(angle=30, x=cx, y=cy):
        try:
            tw = pdf.get_string_width(text)
        except Exception:  # noqa: BLE001
            tw = size_pt * 0.6 * len(text) * 0.352
        # `text()` uses the baseline as y anchor.
        pdf.text(cx - tw / 2.0, cy + size_pt * 0.15, text)

    # Restore prior state.
    pdf.set_xy(prev_x, prev_y)
    if prev_font_family:
        pdf.set_font(prev_font_family, prev_font_style or "", prev_font_size or 10)
    pdf.set_text_color(0, 0, 0)
