"""Shared "How this report was built" provenance footer for every branded PDF.

Mirrors the on-screen `ReportProvenanceFooter.jsx` React component so
recipients of the PDF (mediators, therapists, attorneys) see the same
honest breakdown: which sections come from deterministic rule-based
scoring and which are drafted with technology assistance.

Consumers only need to pass in the FPDF instance and a variant. Callers
may override the section list per report if they want more granularity.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple


ORIGIN_RULE = "rule"
ORIGIN_GEN = "generative"

# Colour tokens (RGB). Match the on-screen pills.
_GREEN_TEXT = (31, 92, 59)     # #1F5C3B — rule-based text
_GREEN_FILL = (241, 249, 244)  # #F1F9F4 — rule-based pill fill
_GREEN_LINE = (181, 223, 197)  # #B5DFC5 — rule-based pill border

_GOLD_TEXT = (138, 107, 18)    # #8A6B12 — generative text
_GOLD_FILL = (255, 249, 235)   # #FFF9EB — generative pill fill
_GOLD_LINE = (228, 216, 184)   # #E4D8B8 — generative pill border

_BORDER = (229, 224, 238)      # #E5E0EE
_INK = (26, 19, 48)
_SUBTLE = (110, 100, 130)


_DEFAULTS = {
    "mediation": [
        ("Goals / issues / priorities capture", ORIGIN_RULE),
        ("Communication + readiness scoring", ORIGIN_RULE),
        ("Executive summary paragraph", ORIGIN_GEN),
        ("Neutral draft agreement wording", ORIGIN_GEN),
        ("Personal growth plan phrasing", ORIGIN_GEN),
    ],
    "snc": [
        ("Areas of need identification", ORIGIN_RULE),
        ("Category status (Strength / Developing / ...)", ORIGIN_RULE),
        ("Recommended co-parenting structure", ORIGIN_RULE),
        ("Report introduction paragraph", ORIGIN_GEN),
        ("Co-parenting strengths + challenges wording", ORIGIN_GEN),
        ("Child impact summary phrasing", ORIGIN_GEN),
    ],
    "deepdive": [
        ("Section-level flag detection (concern / strength)", ORIGIN_RULE),
        ("Overall risk signal aggregation", ORIGIN_RULE),
        ("Section coach cards (where visible)", ORIGIN_GEN),
        ("Final child-focused summary paragraph", ORIGIN_GEN),
    ],
    "comparison": [
        ("Alignment scoring per item (aligned / close / divergent)", ORIGIN_RULE),
        ("Shared priorities / discussion points / mediation questions grouping", ORIGIN_RULE),
        ("Overall alignment percentage", ORIGIN_RULE),
        ("Written summary paragraph (where present)", ORIGIN_GEN),
    ],
}

_EXPLAINER = (
    "Rule-based sections are deterministic: the same answers always produce "
    "the same output. Generative sections are drafted with technology "
    "assistance (Claude, via a neutral, child-focused prompt). The parent "
    "who authored this report remains responsible for reviewing every part "
    "before it is shared."
)


def _safe(t: Any) -> str:
    """Latin-1 safe encoding — mirrors the per-PDF helpers so we don't
    crash on em-dashes or curly quotes even if a caller forgets."""
    if t is None:
        return ""
    s = str(t)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def render_provenance_footer(
    pdf: Any,
    *,
    variant: str = "mediation",
    entries: Optional[List[Tuple[str, str]]] = None,
    top_margin: float = 4.0,
) -> None:
    """Render the "How this report was built" block onto the given FPDF.

    Args:
        pdf: an FPDF-compatible object. We use only the public FPDF API
             so this works with any subclass (main mediation PDF, SNC PDF,
             every deep-dive PDF, both comparison PDFs).
        variant: one of `mediation` | `snc` | `deepdive` | `comparison`.
        entries: optional [(section_label, origin), ...] overrides. `origin`
                 must be one of `rule` | `generative`.
        top_margin: vertical spacing before the block (in mm).
    """
    rows = entries or _DEFAULTS.get(variant) or _DEFAULTS["mediation"]

    # Force onto a fresh line and add a bit of breathing room.
    pdf.ln(top_margin)

    # A subtle grey outer frame — same effect as the on-screen card.
    x0 = pdf.l_margin
    w = pdf.epw
    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.25)

    # Eyebrow.
    pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(61, 26, 120)
    pdf.set_x(x0)
    pdf.cell(w, 4, _safe("HOW THIS REPORT WAS BUILT"), ln=1)
    pdf.ln(0.6)

    rule_count = sum(1 for _, origin in rows if origin == ORIGIN_RULE)
    gen_count = sum(1 for _, origin in rows if origin == ORIGIN_GEN)
    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(75, 69, 103)
    pdf.set_x(x0)
    pdf.multi_cell(
        w, 4,
        _safe(
            f"{rule_count} rule-based section"
            f"{'s' if rule_count != 1 else ''} + "
            f"{gen_count} technology-assisted section"
            f"{'s' if gen_count != 1 else ''}."
        ),
    )
    pdf.ln(0.8)

    # Per-row list. Two columns: label (left, wide), pill (right, ~28mm).
    pill_w = 28.0
    row_h = 5.0
    label_w = w - pill_w - 2.0
    for label, origin in rows:
        # Break before a row that won't fit, so label and pill stay on one page.
        if pdf.get_y() + row_h * 2 > pdf.page_break_trigger:
            pdf.add_page()
        # Snapshot Y for the pill's right-column render after multi_cell.
        y_start = pdf.get_y()
        pdf.set_x(x0)
        # Label
        pdf.set_font("Helvetica", "", 9.0); pdf.set_text_color(*_INK)
        pdf.multi_cell(label_w, row_h, _safe(label))
        y_end = pdf.get_y()
        # Pill (fixed short height, centered vertically against first line).
        if origin == ORIGIN_RULE:
            text = "RULE-BASED"
            fill = _GREEN_FILL; line = _GREEN_LINE; ink = _GREEN_TEXT
        else:
            text = "GENERATIVE"
            fill = _GOLD_FILL; line = _GOLD_LINE; ink = _GOLD_TEXT
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(*line)
        pdf.set_text_color(*ink)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_xy(x0 + label_w + 2.0, y_start)
        pdf.cell(pill_w, 4.4, _safe(text), border=1, align="C", fill=True)
        # Move cursor back below the row so subsequent rows stack cleanly.
        pdf.set_xy(x0, max(y_end, y_start + 4.6))
        pdf.set_draw_color(*_BORDER)
    pdf.ln(1.2)

    # Explainer paragraph in italic subtle grey.
    pdf.set_font("Helvetica", "I", 7.8); pdf.set_text_color(*_SUBTLE)
    pdf.set_x(x0)
    pdf.multi_cell(w, 3.8, _safe(_EXPLAINER))
    pdf.set_text_color(*_INK)  # reset for downstream renderers
