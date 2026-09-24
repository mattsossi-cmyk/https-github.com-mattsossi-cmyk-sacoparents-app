"""Foundation Statement PDF — visually redesigned per user request
(Iter208) to match the "Professional Report" visual family.

Rendered on-demand when a parent taps "Download PDF" on the
Reflection or My Plan pages. This is a preparation resource — not
a legal filing.

Design brief:
  * Purple hero banner ("SA CoParents" wordmark + "Foundation
    Statement" subtitle · right-side report-type label).
  * "SA CoParents Parent Report" eyebrow + serif H1 hero.
  * Three-card info grid — Parent, Statement Date, Prompts Completed.
  * Teal-accented Purpose panel.
  * Every reflection prompt renders as its own numbered section with
    a purple circle badge + serif Times heading + panel-styled body.
  * Signature grid + full SA CoParents address footer on the last
    page.
  * Existing court-report disclaimer + provenance watermark preserved
    from the previous single-page version.

fpdf2 constraints — no true CSS gradients, no rounded corners for
filled rects, no drop shadows. The mockup's gradients are approximated
with solid deep-purple fills; card corners are rendered square. Every
other element (colored panels, section-number circles, teal accent
bars, wordmark) is drawn to scale.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF

from court_report_disclaimer import (
    apply_professional_watermark,
    draw_court_report_disclaimer,
)
from pdf_base import render_pdf_copyright
from safety_assessment_pdf import _safe


# --------------------------------------------------------------------- #
# Reflection prompts (data contract — unchanged from the previous
# builder). Canonical prompts render first; legacy prompts appear
# only when a pre-2026 reflection still holds them, so old sends
# don't come out empty.
# --------------------------------------------------------------------- #
_CANONICAL_PROMPTS: List[Tuple[str, str]] = [
    ("child_lens", "Through my child's eyes"),
    ("own_part", "My own part"),
    ("best_outcome", "My best-case outcome"),
    ("coparent_feedback", "Through my co-parent's eyes"),
]
_LEGACY_PROMPTS: List[Tuple[str, str]] = [
    ("worry", "What I'm worried about"),
    ("triggers", "My triggers"),
    ("calm_strategy", "How I stay calm"),
    ("appreciation", "What I appreciate"),
    ("release", "What I'm releasing"),
]


# --------------------------------------------------------------------- #
# Brand palette — mirrors the mockup's CSS variables so the fpdf2
# output visually belongs to the same family as the marketing site.
# --------------------------------------------------------------------- #
PURPLE = (75, 42, 123)          # --purple   #4b2a7b
PURPLE_DARK = (47, 23, 79)      # --purple-dark #2f174f
PURPLE_LIGHT = (244, 240, 250)  # --purple-light #f4f0fa
LAVENDER = (236, 228, 246)      # --lavender #ece4f6
TEAL = (21, 154, 156)           # --teal     #159a9c
TEAL_LIGHT = (234, 247, 247)    # --teal-light #eaf7f7
TEAL_INK = (17, 125, 127)       # deeper teal for "Purpose" heading
TEXT = (45, 45, 52)             # --text     #2d2d34
MUTED = (109, 104, 117)         # --muted    #6d6875
BORDER = (221, 215, 230)        # --border   #ddd7e6
PANEL_BG = (250, 249, 252)      # --text-panel bg
WHITE = (255, 255, 255)

# Letter page geometry (mm). fpdf2 uses mm; the mockup's px sizes were
# translated proportionally.
PAGE_W = 215.9   # 8.5 in
PAGE_H = 279.4   # 11 in
MARGIN = 15.0
CONTENT_W = PAGE_W - 2 * MARGIN


class _FoundationPDF(FPDF):
    """FPDF subclass that runs `_safe(...)` on every text cell so
    en-dashes, em-dashes and smart quotes never escape latin-1.
    Also disables the built-in header/footer so we can draw a fully
    custom banner + footer per page.
    """

    # Populated by the builder before render. Used inside header() /
    # footer() to draw context-aware chrome (which "chip" label goes
    # on the top-right, which page number goes on the bottom).
    banner_right_label: str = "Child-Focused\nParent Report"
    total_pages: int = 1

    def cell(self, w=0, h=0, txt="", *args, **kwargs):  # type: ignore[override]
        # Some fpdf2 internal paths pass `text` in kwargs. Prefer that
        # over the positional `txt` if present, and always sanitize.
        if "text" in kwargs:
            txt = kwargs.pop("text")
        return super().cell(w, h, text=_safe(txt), *args, **kwargs)

    def multi_cell(self, w, h=None, txt="", *args, **kwargs):  # type: ignore[override]
        if "text" in kwargs:
            txt = kwargs.pop("text")
        return super().multi_cell(w, h, text=_safe(txt), *args, **kwargs)

    def header(self) -> None:  # noqa: D401 — fpdf hook
        # Deep-purple hero banner (approx of the mockup's CSS gradient
        # — fpdf2 has no gradient primitives, so we settle for the
        # darker end of the gradient which reads well in print).
        self.set_fill_color(*PURPLE_DARK)
        self.rect(0, 0, PAGE_W, 24.0, style="F")

        # Wordmark — the user asked for a text-only "SA CoParents"
        # mark, no logo image.
        self.set_text_color(*WHITE)
        self.set_font("Times", "B", 15)
        self.set_xy(MARGIN, 5.5)
        self.cell(80, 6, "SA CoParents")
        # Subtitle beneath the wordmark, spaced-caps mini-label.
        self.set_font("Helvetica", "", 7)
        self.set_xy(MARGIN, 12.5)
        # Set text color to a lighter tint of white by drawing at 85% alpha.
        # fpdf2 has no alpha for text — settle for a mid-lavender tint.
        self.set_text_color(220, 210, 235)
        self.cell(80, 4, "FOUNDATION STATEMENT")

        # Right-side report-type chip (small, spaced caps).
        self.set_font("Helvetica", "", 7)
        for i, line in enumerate(self.banner_right_label.split("\n")):
            self.set_xy(PAGE_W - MARGIN - 60, 6.5 + i * 4)
            self.cell(60, 4, line.upper(), align="R")

        # Reset ink for the body.
        self.set_text_color(*TEXT)
        # Leave a comfortable gap under the banner.
        self.set_y(30.0)

    def footer(self) -> None:  # noqa: D401 — fpdf hook
        # Page counter — matches the mockup's "Page X of N" style.
        # `{nb}` is substituted by fpdf2 with the real page count on
        # output (see `alias_nb_pages` in the builder), so the count
        # is correct even on page 1's already-rendered footer.
        self.set_y(-14.0)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(
            0, 4,
            f"PAGE {self.page_no()} OF {{nb}}",
            align="C",
        )
        # Copyright / brand line beneath the page counter.
        self.set_y(-9.0)
        render_pdf_copyright(self)


# --------------------------------------------------------------------- #
# Drawing helpers.
# --------------------------------------------------------------------- #
def _iso_utc(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _human_date(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.astimezone(timezone.utc).strftime("%B %-d, %Y")


def _sections(reflection: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return ordered (label, text) pairs for the prompts the parent
    actually filled in — canonical first, then any legacy prompts."""
    out: List[Tuple[str, str]] = []
    for key, label in _CANONICAL_PROMPTS + _LEGACY_PROMPTS:
        v = reflection.get(key)
        if isinstance(v, str) and v.strip():
            out.append((label, v.strip()))
    return out


def _draw_info_card(
    pdf: FPDF,
    *,
    x: float, y: float, w: float, h: float,
    label: str, value: str,
) -> None:
    """A single card in the 3-column info grid (Parent / Statement
    Date / Prompts Completed). Lavender-tinted background + tiny
    label + serif value."""
    pdf.set_fill_color(*PURPLE_LIGHT)
    pdf.set_draw_color(230, 224, 240)
    pdf.rect(x, y, w, h, style="FD")
    # Label — spaced caps in brand purple.
    pdf.set_xy(x + 4, y + 3.5)
    pdf.set_text_color(*PURPLE)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.cell(w - 8, 3.5, label.upper())
    # Value — serif, dark ink.
    pdf.set_xy(x + 4, y + 8.5)
    pdf.set_text_color(*TEXT)
    pdf.set_font("Times", "", 12)
    pdf.multi_cell(w - 8, 5, value)


def _draw_purpose_panel(pdf: FPDF, y: float, body: str) -> float:
    """Teal-accented purpose panel — mirrors the mockup's
    .purpose-panel. Returns the Y coordinate below the panel."""
    left_bar_w = 2.0
    pad_x = 5.0
    pad_y = 4.0
    inner_w = CONTENT_W - left_bar_w - pad_x * 2
    # Measure body height using multi_cell in "measure" mode by
    # temporarily writing off-page.
    pdf.set_font("Helvetica", "", 9)
    lines = pdf.multi_cell(
        inner_w, 4.4, body, dry_run=True, output="LINES",
    )
    body_h = max(len(lines) * 4.4, 8.0)
    total_h = body_h + pad_y * 2 + 6  # +6 for the bold title line

    # Background.
    pdf.set_fill_color(*TEAL_LIGHT)
    pdf.set_draw_color(*TEAL_LIGHT)
    pdf.rect(MARGIN, y, CONTENT_W, total_h, style="F")
    # Left accent bar.
    pdf.set_fill_color(*TEAL)
    pdf.rect(MARGIN, y, left_bar_w, total_h, style="F")
    # Title.
    pdf.set_xy(MARGIN + left_bar_w + pad_x, y + pad_y - 0.5)
    pdf.set_text_color(*TEAL_INK)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(inner_w, 5, "Purpose of this Statement")
    # Body.
    pdf.set_xy(MARGIN + left_bar_w + pad_x, y + pad_y + 5)
    pdf.set_text_color(*TEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(inner_w, 4.4, body)

    return y + total_h + 4


def _draw_section_heading(
    pdf: FPDF, *, number: int, title: str,
) -> None:
    """Purple circle badge + serif heading + faint underline rule.
    Mirrors .section-heading in the mockup."""
    y = pdf.get_y()
    # Circle badge — 9 mm diameter.
    diam = 9.0
    pdf.set_fill_color(*PURPLE)
    pdf.ellipse(MARGIN, y, diam, diam, style="F")
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_xy(MARGIN, y + 2.4)
    pdf.cell(diam, 4, str(number), align="C")
    # Title — serif, deep purple, slight vertical offset.
    pdf.set_text_color(*PURPLE_DARK)
    pdf.set_font("Times", "B", 15)
    pdf.set_xy(MARGIN + diam + 4, y + 1.2)
    pdf.cell(CONTENT_W - diam - 4, 6, title)
    # Underline rule.
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.2)
    pdf.line(MARGIN, y + 12.0, MARGIN + CONTENT_W, y + 12.0)
    pdf.set_y(y + 14.0)


def _draw_text_panel(pdf: FPDF, text: str) -> None:
    """Rounded-square panel used for reflection bodies. Same as
    .text-panel in the mockup — soft grey background + thin border."""
    pdf.set_font("Helvetica", "", 10.5)
    inner_w = CONTENT_W - 10
    lines = pdf.multi_cell(
        inner_w, 5.0, text, dry_run=True, output="LINES",
    )
    h = max(len(lines) * 5.0, 8.0) + 8
    y = pdf.get_y()
    pdf.set_fill_color(*PANEL_BG)
    pdf.set_draw_color(*BORDER)
    pdf.rect(MARGIN, y, CONTENT_W, h, style="FD")
    pdf.set_xy(MARGIN + 5, y + 4)
    pdf.set_text_color(*TEXT)
    pdf.multi_cell(inner_w, 5.0, text)
    pdf.set_y(y + h + 4)


def _need_new_page(pdf: FPDF, needed_h: float) -> None:
    """Manual page-break helper: if the remaining space below the
    current cursor is less than `needed_h`, start a new page. Used
    to keep section headings and their first line together."""
    remaining = PAGE_H - 18.0 - pdf.get_y()   # 18 = auto-break margin
    if remaining < needed_h:
        pdf.add_page()


def _draw_signature_and_footer(
    pdf: FPDF, *, author_name: str,
) -> None:
    """Signature grid + full SA CoParents address block. Renders on
    the last page just above the disclaimer + watermark."""
    y = pdf.get_y() + 6
    # Signature grid — two columns.
    col_w = (CONTENT_W - 12) / 2
    pdf.set_draw_color(80, 80, 90)
    pdf.set_line_width(0.35)
    # Parent Signature.
    pdf.line(MARGIN, y + 14, MARGIN + col_w, y + 14)
    pdf.set_xy(MARGIN, y + 15)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*MUTED)
    pdf.cell(col_w, 4, "PARENT SIGNATURE")
    pdf.set_xy(MARGIN, y + 19)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT)
    pdf.cell(col_w, 4, author_name)
    # Date.
    dx = MARGIN + col_w + 12
    pdf.line(dx, y + 14, dx + col_w, y + 14)
    pdf.set_xy(dx, y + 15)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*MUTED)
    pdf.cell(col_w, 4, "DATE")
    pdf.set_xy(dx, y + 19)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT)
    pdf.cell(col_w, 4, _human_date())

    pdf.set_y(y + 28)


# --------------------------------------------------------------------- #
# Public builder.
# --------------------------------------------------------------------- #
def build_foundation_statement_pdf(
    *,
    author_name: str,
    reflection: Dict[str, Any],
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Render the Foundation Statement PDF and return the raw bytes.

    Raises `ValueError` when the reflection contains no usable prompt
    content — callers should guard against empty sends so parents
    don't email a hollow document by accident.
    """
    sections = _sections(reflection or {})
    if not sections:
        raise ValueError("Reflection is empty — nothing to render.")

    pdf = _FoundationPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(MARGIN, 30, MARGIN)   # 30 mm top gap for the banner
    # Enable the {nb} substitution used by the footer's "PAGE X OF N"
    # counter — fpdf2 replaces the token with the final page count at
    # output time, so page 1's footer no longer reads "1 OF 1".
    pdf.alias_nb_pages("{nb}")
    pdf.add_page()

    # --- Hero (title + subtitle) ------------------------------------
    pdf.set_xy(MARGIN, pdf.get_y() + 2)
    pdf.set_text_color(*TEAL)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(CONTENT_W, 5, "SA COPARENTS PARENT REPORT")
    pdf.set_xy(MARGIN, pdf.get_y() + 6)
    pdf.set_text_color(*PURPLE_DARK)
    pdf.set_font("Times", "B", 24)
    pdf.cell(CONTENT_W, 10, "Child-Focused Foundation Statement")
    pdf.set_xy(MARGIN, pdf.get_y() + 11)
    pdf.set_text_color(*MUTED)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        CONTENT_W, 5,
        "A parent's statement of goals, priorities, concerns and "
        "commitments for their child.",
    )

    # --- 3-card info grid (Parent / Statement Date / Prompts) -------
    pdf.set_y(pdf.get_y() + 4)
    grid_y = pdf.get_y()
    card_gap = 4.0
    card_w = (CONTENT_W - card_gap * 2) / 3
    card_h = 17.0
    _draw_info_card(
        pdf, x=MARGIN, y=grid_y, w=card_w, h=card_h,
        label="Parent", value=author_name,
    )
    _draw_info_card(
        pdf, x=MARGIN + card_w + card_gap, y=grid_y,
        w=card_w, h=card_h,
        label="Statement Date", value=_human_date(generated_at),
    )
    _draw_info_card(
        pdf, x=MARGIN + (card_w + card_gap) * 2, y=grid_y,
        w=card_w, h=card_h,
        label="Prompts Completed",
        value=f"{len(sections)} of {len(_CANONICAL_PROMPTS)}",
    )
    pdf.set_y(grid_y + card_h + 6)

    # --- Purpose panel ---------------------------------------------
    new_y = _draw_purpose_panel(
        pdf, pdf.get_y(),
        "A short reflection I wrote to prepare for our conversation. "
        "It captures how I'm thinking about our co-parenting right "
        "now — from my child's perspective, from my co-parent's "
        "perspective, and from my own. It is not a set of demands "
        "and it is not a court filing.",
    )
    pdf.set_y(new_y)

    # --- Numbered reflection sections ------------------------------
    for i, (label, text) in enumerate(sections, start=1):
        # Reserve enough space for the heading + a first line of body
        # so we don't orphan the heading at the bottom of a page.
        _need_new_page(pdf, needed_h=32.0)
        _draw_section_heading(pdf, number=i, title=label)
        _draw_text_panel(pdf, text)

    # --- Signature + address footer + disclaimer -------------------
    _need_new_page(pdf, needed_h=68.0)
    _draw_signature_and_footer(pdf, author_name=author_name)

    # Court-report disclaimer (one parent → both_parents=False).
    draw_court_report_disclaimer(
        pdf,
        author_name=author_name,
        both_parents=False,
    )

    # Provenance watermark on every page.
    apply_professional_watermark(
        pdf,
        firm_name=author_name,
        downloaded_at_iso=_iso_utc(generated_at),
    )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


def foundation_statement_has_content(reflection: Optional[Dict[str, Any]]) -> bool:
    """Cheap guard for API endpoints: returns True iff the reflection
    holds at least one non-empty prompt string. Callers use this to
    reject empty send/download requests before spinning up the PDF."""
    if not isinstance(reflection, dict):
        return False
    for key, _label in _CANONICAL_PROMPTS + _LEGACY_PROMPTS:
        v = reflection.get(key)
        if isinstance(v, str) and v.strip():
            return True
    return False
