"""
Shared court-report disclaimer renderer.

Emits the same six-caveat block that the frontend
`<CourtReportDisclaimer />` component renders — but as PDF content,
so mediators / attorneys / judges see identical language whether
they open the artefact in-app or as a downloaded PDF.

The six caveats (per 2026-03-06 product review):
  1. Who completed it — the parent named above.
  2. Answers self-reported, not verified.
  3. One-parent vs. two-parent participation.
  4. Not a custody evaluation.
  5. Scores are not clinical findings.
  6. No best-interest recommendation.

Usage — anywhere in a court-facing PDF, ideally on the first page
or immediately after the cover:

    from court_report_disclaimer import draw_court_report_disclaimer
    draw_court_report_disclaimer(
        pdf,
        author_name="Jane Doe",
        both_parents=False,
    )
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from safety_assessment_pdf import _safe

# Muted amber palette — matches the frontend disclaimer's amber tone
# so print + on-screen readers see a consistent "read this first" cue.
AMBER_BG = (255, 246, 234)
AMBER_BORDER = (241, 217, 183)
AMBER_TEXT = (90, 60, 16)
AMBER_ACCENT = (138, 70, 16)

# ---------------------------------------------------------------------------
# Filed-PDF watermark — subtle bottom-of-page footer stamped on every page
# ---------------------------------------------------------------------------
# Used when a professional downloads a court-facing PDF from the /mine
# console. Marks each page with the caller's firm name + download
# timestamp so a downstream recipient (co-counsel, judge, opposing
# party) can verify which copy they were handed. Rendered in a very
# muted grey so it never fights with the primary content, and always
# includes the neutral "Downloaded by" prefix so it's clearly
# provenance metadata — NOT a court seal or party endorsement.


_WATERMARK_GREY = (140, 140, 155)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def apply_professional_watermark(
    pdf,
    firm_name: Optional[str],
    downloaded_at_iso: Optional[str] = None,
) -> None:
    """
    Stamp a small provenance footer on every rendered page of `pdf`.
    Call AFTER the builder has finished adding all pages but BEFORE
    `pdf.output(...)` is invoked — the function walks `pages_count`
    and writes into each page's canvas.

    Silently no-ops if:
      * `firm_name` is falsy (empty / None) — nothing to stamp.
      * `pdf` doesn't expose fpdf2's page navigation API.

    Never raises: watermarking is a nice-to-have, never a blocker
    for the download itself.
    """
    if not firm_name:
        return
    firm = str(firm_name).strip()
    if not firm:
        return
    if not (hasattr(pdf, "set_font") and hasattr(pdf, "text")):
        return
    pages_count = getattr(pdf, "pages_count", None)
    if not pages_count:
        return

    stamp_text = _safe(
        f"Downloaded by {firm} on {downloaded_at_iso or _iso_now()} · SA CoParents"
    )

    original_page = getattr(pdf, "page", None)
    try:
        page_w = getattr(pdf, "w", 210) or 210
        page_h = getattr(pdf, "h", 297) or 297
        # Save current font/colour state so restoring later doesn't
        # break the caller's context (we're being called AFTER build
        # completes, so this is defensive rather than strictly needed).
        prev_font_family = getattr(pdf, "font_family", "helvetica")
        prev_font_style = getattr(pdf, "font_style", "")
        prev_font_size = getattr(pdf, "font_size_pt", 10) or 10

        for i in range(1, pages_count + 1):
            try:
                pdf.page = i  # jump into page i's canvas
                pdf.set_font("Helvetica", "I", 7.5)
                pdf.set_text_color(*_WATERMARK_GREY)
                # Bottom-right anchor — 8mm from right, 6mm from bottom.
                # fpdf2's `text()` is left-anchored, so we must subtract
                # the rendered string width to actually sit against the
                # right margin. Without this, long firm names get
                # clipped past the page edge and the provenance stamp
                # disappears — defeating the traceability contract.
                stamp_width = 0.0
                try:
                    stamp_width = pdf.get_string_width(stamp_text)
                except Exception:  # noqa: BLE001
                    stamp_width = 0.0
                pdf.text(
                    x=page_w - 8 - stamp_width,
                    y=page_h - 6,
                    txt=stamp_text,
                )
            except Exception:  # noqa: BLE001
                # A specific page's canvas can't be replayed (mixed
                # engine / fpdf legacy compat) — skip that page rather
                # than fail the whole watermark.
                continue

        # Restore state
        try:
            pdf.set_text_color(0, 0, 0)
            if prev_font_family:
                pdf.set_font(prev_font_family, prev_font_style, prev_font_size)
        except Exception:  # noqa: BLE001
            pass
    finally:
        # Return `page` to whatever the caller had. Setting page beyond
        # the last one triggers fpdf2 to create a fresh page, which we
        # DO NOT want after watermarking.
        if original_page is not None:
            try:
                pdf.page = original_page
            except Exception:  # noqa: BLE001
                pass


def _bullets(author_name: Optional[str], both_parents: bool) -> list[str]:
    who = (
        f"Completed by {author_name} — the parent named above filled in every answer themselves."
        if author_name
        else "Completed by the parent named above — they filled in every answer themselves."
    )
    participation = (
        "Both parents participated — this is a joint reflection built from two separate private inputs."
        if both_parents
        else "Only one parent completed this reflection — the other parent's perspective is not included."
    )
    return [
        who,
        "Answers are self-reported and not verified by a licensed clinician, court officer, or independent evaluator.",
        participation,
        "This is not a custody evaluation and is not intended to replace one.",
        "Scores and dimensions are educational reflections — they are not clinical findings, diagnoses, or risk determinations.",
        "Nothing in this document is a recommendation about the child's best interest. Best-interest decisions are for the parents, their professionals, and — where appropriate — the court.",
    ]


def draw_court_report_disclaimer(
    pdf,
    *,
    author_name: Optional[str] = None,
    both_parents: bool = False,
    heading: str = "Before this document is used in a court, mediation, or legal setting",
) -> None:
    """
    Draw the six-caveat court-report disclaimer block on the current
    page. Advances the y-cursor past the block; does NOT add its own
    page break — callers decide whether the disclaimer sits on the
    cover page, its own page, or above a specific section.

    Silently no-ops if the fpdf object doesn't expose the standard
    fpdf2 API (defensive — makes it safe to import from unit tests
    that don't provide a real PDF).
    """
    if not hasattr(pdf, "set_fill_color"):
        return

    left = pdf.get_x() if hasattr(pdf, "get_x") else 15
    top = pdf.get_y() if hasattr(pdf, "get_y") else 30
    page_w = getattr(pdf, "w", 210) or 210
    right_m = getattr(pdf, "r_margin", 15) or 15
    left_m = getattr(pdf, "l_margin", 15) or 15
    content_w = page_w - left_m - right_m

    bullets = _bullets(author_name, both_parents)

    # Draw the amber outer box. Height is measured after we render the
    # body, so first compute how tall the text will actually be with
    # multi_cell dry-runs — fpdf2 has no proper measure, so we lay it
    # out at a temporary y, measure, roll y back, then paint the box.
    # Simpler alternative used here: estimate 5.6mm per bullet line +
    # heading padding; over-estimate slightly so nothing overflows.
    total_lines = 1  # heading line
    for text in bullets:
        # Rough wrap estimate: 90 chars per line at 9pt / 170mm width.
        approx_lines = max(1, (len(text) + 89) // 90)
        total_lines += approx_lines
    box_height = total_lines * 5.4 + 12  # padding

    pdf.set_fill_color(*AMBER_BG)
    pdf.set_draw_color(*AMBER_BORDER)
    pdf.set_line_width(0.6)
    pdf.rect(left_m, top, content_w, box_height, "DF")
    pdf.set_line_width(0.2)  # restore default-ish

    # Heading strip
    pdf.set_xy(left_m + 4, top + 3.5)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*AMBER_ACCENT)
    heading_text = heading.upper()
    pdf.cell(content_w - 8, 4.5, _safe(heading_text), ln=1)

    # Body bullets
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*AMBER_TEXT)
    y_cursor = top + 9.5
    for text in bullets:
        pdf.set_xy(left_m + 4, y_cursor)
        # Bullet glyph
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(3.5, 5, "-")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(left_m + 8, y_cursor)
        pdf.multi_cell(content_w - 12, 4.6, _safe(text))
        # Advance y_cursor to just past what we drew.
        y_cursor = pdf.get_y() + 0.6

    # Move the caller's cursor past the block.
    pdf.set_xy(left_m, max(top + box_height + 3, y_cursor + 2))
    # Reset colour defaults so subsequent content doesn't inherit amber.
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)
