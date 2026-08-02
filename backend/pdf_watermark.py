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


# ---------------------------------------------------------------------------
# Signed report footer — parent name + timestamp printed right under the
# watermark on every content page.
# ---------------------------------------------------------------------------
_SIG_TEXT_INK = (75, 69, 103)   # #4B4567
_SIG_ACCENT = (61, 26, 120)     # #3D1A78


def stamp_signature_line(pdf: Any) -> None:
    """Print a small "Signed by X on YYYY-MM-DD HH:MM UTC" line at the
    very bottom of the current page.

    Only fires when the caller has set both `pdf._signed_by` (str) and
    `pdf._signed_at` (ISO-8601 timestamp) on the PDF instance before
    generation. Safe to call unconditionally from `footer()`; it no-ops
    when the flags are absent.

    If `pdf._signed_note` is also set, a small italic sub-line renders
    just above the signature (e.g. "Prepared for our 12 Feb mediation
    session"). We paint above the existing footer callers wrote so
    their branding isn't disrupted; a single grey rule sits between
    the two.
    """
    signed_by = getattr(pdf, "_signed_by", None)
    signed_at = getattr(pdf, "_signed_at", None)
    signed_note = getattr(pdf, "_signed_note", None)
    if not signed_by or not signed_at:
        return

    # Snapshot state.
    prev_font_family = pdf.font_family
    prev_font_style = pdf.font_style
    prev_font_size = pdf.font_size_pt

    # Format the timestamp compactly: "02 Feb 2026, 15:37 UTC".
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(str(signed_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        ts = dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:  # noqa: BLE001
        ts = str(signed_at)

    def _latin(s: str) -> str:
        for k, v in {"\u2014": "-", "\u2013": "-", "\u2018": "'",
                     "\u2019": "'", "\u201c": '"', "\u201d": '"',
                     "\u2026": "...", "\u00a0": " "}.items():
            s = s.replace(k, v)
        return s.encode("latin-1", errors="replace").decode("latin-1")

    line = _latin(f"Signed by {signed_by}  |  {ts}")
    note = _latin((signed_note or "").strip())

    # Draw a thin rule + centred signature line above the standard footer.
    # If there's a note, we push the whole block up ~3.4mm so the note
    # sits above the signature (both above the page-number footer).
    base_y = pdf.h - 6.0
    if note:
        note_y = base_y - 3.6
        pdf.set_draw_color(220, 214, 232)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, note_y - 2.6, pdf.w - pdf.r_margin, note_y - 2.6)
        pdf.set_font("Helvetica", "I", 7.0)
        pdf.set_text_color(*_SIG_TEXT_INK)
        pdf.set_xy(pdf.l_margin, note_y - 1.8)
        pdf.cell(pdf.epw, 3.4, note, align="C")
        # Signature line beneath — no additional rule (avoid double lines).
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*_SIG_ACCENT)
        pdf.set_xy(pdf.l_margin, base_y - 1.8)
        pdf.cell(pdf.epw, 3.6, line, align="C")
    else:
        pdf.set_draw_color(220, 214, 232)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, base_y - 2.6, pdf.w - pdf.r_margin, base_y - 2.6)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*_SIG_ACCENT)
        pdf.set_xy(pdf.l_margin, base_y - 1.8)
        pdf.cell(pdf.epw, 3.6, line, align="C")

    # Restore prior state so downstream footer renderers stay unaffected.
    if prev_font_family:
        pdf.set_font(prev_font_family, prev_font_style or "", prev_font_size or 10)
    pdf.set_text_color(0, 0, 0)
