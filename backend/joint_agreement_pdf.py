"""PDF renderer for the Joint Alignment Report ("Step One - Alignment
Before Agreement"). Historically titled the Joint Co-Parenting Agreement
Draft; retitled in Iter190 to match sacoparentsalign.com's neutral
alignment-report framing while keeping the same underlying payload.

Layout:
  * Cover page: title, both parents' names, source-agreement IDs, and a
    prominent DRAFT-FOR-DISCUSSION disclaimer.
  * Section pages: each section (shared goals, communication, child needs,
    household rules, priority topics, still open) as three stacked blocks:
      - Both proposed  (green)
      - <Parent A> only (purple)
      - <Parent B> only (teal)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, WARN, INFO, OK,
    ORG_NAME, ORG_TAGLINE, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe,
)
from court_report_disclaimer import draw_court_report_disclaimer
from pdf_base import render_pdf_copyright


PAGE_W = 210
LEFT_M = 15
RIGHT_M = 15
CONTENT_W = PAGE_W - LEFT_M - RIGHT_M


class _JointAgreementPDF(FPDF):
    def __init__(self, *, generated_at: str, share_id: str):
        super().__init__()
        self._generated_at = generated_at
        self._share_id = share_id
        self._is_cover = False

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        if self._is_cover:
            return
        self.set_fill_color(*SAND)
        self.rect(0, 0, PAGE_W, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=3, w=16, h=16)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(32, 5)
        self.cell(0, 5, "Step One - Alignment Before Agreement", ln=1)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_MID)
        self.set_x(32)
        self.cell(0, 4, f"{ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(26)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Draft for discussion - Not a signed agreement or court order - "
            f"Generated {self._generated_at} - Share {self._share_id[:10]}",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


        render_pdf_copyright(self)
def _body(pdf: _JointAgreementPDF, text: str, *, size: int = 9, italic: bool = False):
    pdf.set_font("Helvetica", "I" if italic else "", size)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.6, text)


# ---------------------------------------------------------------------------
# 5-bucket Parent View renderers — mirrors JointAgreementParentView.jsx so
# the printed PDF matches the on-screen tone. Each bucket gets a coloured
# strip, an intro, and a list of items in the bucket-specific shape.
# ---------------------------------------------------------------------------

# Bucket accent colours (RGB) — kept in the same visual family as the
# on-screen JSX component so parents recognise the mapping.
_BUCKET_ACCENTS: Dict[str, tuple] = {
    "what_you_both_proposed":            (31, 92, 59),   # green
    "where_you_have_different_ideas":    (138, 91, 0),   # amber
    "may_need_refinement":               (176, 42, 42),  # red
    "options_to_consider":               (61, 26, 120),  # purple
    "questions_for_next_conversation":   (15, 111, 111), # teal
}


# ---------------------------------------------------------------------------
# Iter190 — Alignment Report section-flow renderers. Mirrors the
# sacoparentsalign.com 10-section layout: numbered section headings +
# colour-coded Alignment Map + neutral closing page. Kept alongside the
# 5-bucket Parent View renderers because Appendix A still uses those.
# ---------------------------------------------------------------------------

# Neutral SA CoParents brand palette for the Alignment Map colour bands.
# Chosen from the existing palette (OK / WARN / DANGER) so the map reads
# the same way as every other rating table across the platform.
_ALIGNMENT_BAND_COLOURS: Dict[str, tuple] = {
    "strong":            OK,        # green — Strong alignment
    "moderate":          WARN,      # amber — Moderate alignment
    "needs_discussion":  DANGER,    # red   — Needs discussion
    "not_enough_data":   TEXT_MID,  # grey  — Not enough data yet
}

_ALIGNMENT_BAND_LABELS: Dict[str, str] = {
    "strong":            "Strong alignment",
    "moderate":          "Moderate alignment",
    "needs_discussion":  "Needs discussion",
    "not_enough_data":   "Not enough data yet",
}


def _numbered_section_heading(
    pdf: "_JointAgreementPDF", number: int, title: str, description: str = "",
):
    """Consistent numbered section heading used across every §1..§10
    heading. Bold purple number + bold dark title + optional italic
    description on the next line. Never crosses a page break mid-heading
    — the caller controls whether to add_page() first."""
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(61, 26, 120)  # brand purple
    pdf.cell(11, 7, f"{number}.")
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 7, title, ln=1)
    if description:
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "I", 8.8)
        pdf.set_text_color(*TEXT_MID)
        pdf.multi_cell(CONTENT_W, 4.4, description)
        pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1.5)


def _render_alignment_map(
    pdf: "_JointAgreementPDF", rows: List[Dict[str, Any]],
):
    """Render the colour-coded Alignment Map — one row per merged
    section with a coloured strip, the topic label, the alignment band
    name, and a small "both/total" count in muted grey so professionals
    can see the underlying evidence at a glance."""
    if not rows:
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*TEXT_MID)
        pdf.multi_cell(
            CONTENT_W, 4.5,
            "No merged sections yet — the alignment map appears once "
            "both parents have submitted a draft.",
        )
        pdf.set_text_color(*TEXT_DARK)
        return

    row_h = 8
    strip_w = 4
    for row in rows:
        band = row.get("alignment") or "not_enough_data"
        colour = _ALIGNMENT_BAND_COLOURS.get(band, TEXT_MID)
        label = _ALIGNMENT_BAND_LABELS.get(band, band.replace("_", " ").title())
        topic = row.get("topic") or row.get("key") or "-"
        both = int(row.get("both_count") or 0)
        total = int(row.get("total_count") or 0)

        y_top = pdf.get_y()
        # Coloured strip on the left.
        pdf.set_fill_color(*colour)
        pdf.rect(LEFT_M, y_top, strip_w, row_h - 1, "F")

        # Topic label — bold, dark, centred vertically in the row.
        pdf.set_xy(LEFT_M + strip_w + 3, y_top + 0.5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(CONTENT_W * 0.55, row_h - 1, topic)

        # Alignment band label — coloured to match the strip.
        pdf.set_xy(LEFT_M + strip_w + 3 + CONTENT_W * 0.55, y_top + 0.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*colour)
        pdf.cell(CONTENT_W * 0.25, row_h - 1, label)

        # Both/total count — small, muted grey.
        pdf.set_xy(LEFT_M + strip_w + 3 + CONTENT_W * 0.80, y_top + 0.5)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*TEXT_MID)
        count_txt = f"{both} / {total}" if total else "-"
        pdf.cell(CONTENT_W * 0.20, row_h - 1, count_txt, align="R")

        pdf.set_text_color(*TEXT_DARK)
        pdf.set_y(y_top + row_h)

    # Legend row under the map — matches sacoparentsalign's colour key.
    pdf.ln(2)
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(
        CONTENT_W, 4.2,
        "Colour key: green = Strong alignment - amber = Moderate - "
        "red = Needs discussion - grey = Not enough data yet. Counts "
        "show shared clauses / total clauses in the section.",
    )
    pdf.set_text_color(*TEXT_DARK)


def _render_bullet_list(
    pdf: "_JointAgreementPDF", bullets: List[str],
):
    """Simple neutral bullet list used by §4 Child's Identified Needs
    and §10 Possible Next Steps title-only variants."""
    if not bullets:
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*TEXT_MID)
        pdf.multi_cell(CONTENT_W, 4.5, "(none)")
        pdf.set_text_color(*TEXT_DARK)
        return
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*TEXT_DARK)
    for b in bullets:
        text = (b or "").strip()
        if not text:
            continue
        pdf.set_x(LEFT_M)
        pdf.multi_cell(CONTENT_W, 4.6, "- " + text)
        pdf.ln(0.3)


def _render_potential_alignment(
    pdf: "_JointAgreementPDF", pairs: List[Dict[str, Any]],
    parent_a: str, parent_b: str,
):
    """§8 Potential Areas of Alignment. Renders near-miss pairs — one
    two-column strip per row so a mediator can see how close the
    parents already are on each topic."""
    if not pairs:
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*TEXT_MID)
        pdf.multi_cell(
            CONTENT_W, 4.5,
            "No near-match clauses in the current draft. When both "
            "parents propose something related-but-not-identical, it "
            "surfaces here as a candidate for a short conversation.",
        )
        pdf.set_text_color(*TEXT_DARK)
        return

    col_w = (CONTENT_W - 4) / 2
    for row in pairs:
        topic = (row.get("topic") or "").strip()
        a_text = (row.get("parent_a_text") or "").strip()
        b_text = (row.get("parent_b_text") or "").strip()
        if topic:
            pdf.set_x(LEFT_M)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*TEXT_MID)
            pdf.cell(0, 4.2, topic, ln=1)
            pdf.set_text_color(*TEXT_DARK)
        # Two-column strip labelled with parent names.
        y_top = pdf.get_y()
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(61, 26, 120)
        pdf.set_xy(LEFT_M, y_top)
        pdf.cell(col_w, 4, parent_a)
        pdf.set_text_color(15, 111, 111)
        pdf.set_xy(LEFT_M + col_w + 4, y_top)
        pdf.cell(col_w, 4, parent_b)
        pdf.ln(4.3)
        pdf.set_font("Helvetica", "", 8.7)
        pdf.set_text_color(*TEXT_DARK)
        a_y = pdf.get_y()
        pdf.set_xy(LEFT_M, a_y)
        pdf.multi_cell(col_w, 4.3, a_text or "-")
        end_a = pdf.get_y()
        pdf.set_xy(LEFT_M + col_w + 4, a_y)
        pdf.multi_cell(col_w, 4.3, b_text or "-")
        end_b = pdf.get_y()
        pdf.set_y(max(end_a, end_b))
        pdf.ln(1)


def _render_next_steps(
    pdf: "_JointAgreementPDF", steps: List[Dict[str, str]],
):
    """§10 Possible Next Steps. Title + one-line detail per step so
    parents can pick the ones that fit. Neutral, non-prescriptive."""
    if not steps:
        _render_bullet_list(pdf, [])
        return
    for step in steps:
        title = (step.get("title") or "").strip()
        detail = (step.get("detail") or "").strip()
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 4.4, title, ln=1)
        pdf.set_text_color(*TEXT_DARK)
        if detail:
            pdf.set_x(LEFT_M)
            pdf.set_font("Helvetica", "", 8.8)
            pdf.multi_cell(CONTENT_W, 4.3, detail)
        pdf.ln(0.5)


def _render_reflection_shared_bullets(
    pdf: "_JointAgreementPDF", analysis: Dict[str, Any],
):
    """§2 companion — verbatim "Both parents mentioned 'X'" bullets
    from the sacoparentsalign free-text reflection prompts. Renders
    NOTHING when both parents have not completed the reflection
    (analysis dict is empty). Never leaks a single parent's quotes."""
    both = (analysis or {}).get("both_parents_mentioned") or []
    if not both:
        return
    pdf.ln(3)
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(31, 92, 59)
    pdf.cell(0, 5, "Shared themes from your reflection prompts", ln=1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "", 9)
    for row in both:
        label = (row.get("prompt_label") or "").strip()
        phrase = (row.get("shared_phrase") or "").strip()
        if not label or not phrase:
            continue
        pdf.set_x(LEFT_M)
        pdf.multi_cell(
            CONTENT_W, 4.5,
            f"- Both parents mentioned \"{phrase}\" when describing "
            f"{label.lower()}.",
        )
        pdf.ln(0.3)


def _render_reflection_verbatim_quotes(
    pdf: "_JointAgreementPDF", analysis: Dict[str, Any],
):
    """§3 companion — verbatim per-prompt quotes in a two-column
    strip so a mediator can compare each parent's tone side by side.
    Renders NOTHING when reflections were not submitted by both
    parents. Truncates each quote to 320 chars so a long answer does
    not push §4 off the page."""
    diffs = (analysis or {}).get("perspectives_differ") or []
    if not diffs:
        return
    pdf.ln(3)
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(138, 91, 0)
    pdf.cell(0, 5, "Reflection quotes - in each parent's own words", ln=1)
    pdf.set_text_color(*TEXT_DARK)
    col_w = (CONTENT_W - 4) / 2
    for row in diffs:
        label = (row.get("prompt_label") or "").strip()
        a_q = (row.get("parent_a_quote") or "").strip()[:320]
        b_q = (row.get("parent_b_quote") or "").strip()[:320]
        parent_a_display = (row.get("parent_a_name") or "Parent A").strip()
        parent_b_display = (row.get("parent_b_name") or "Parent B").strip()
        if not (a_q or b_q):
            continue
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*TEXT_MID)
        pdf.cell(0, 4.2, label, ln=1)
        # Two-column strip labelled with parent names.
        y_top = pdf.get_y()
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(61, 26, 120)
        pdf.set_xy(LEFT_M, y_top)
        pdf.cell(col_w, 4, parent_a_display)
        pdf.set_text_color(15, 111, 111)
        pdf.set_xy(LEFT_M + col_w + 4, y_top)
        pdf.cell(col_w, 4, parent_b_display)
        pdf.ln(4.3)
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*TEXT_DARK)
        a_y = pdf.get_y()
        pdf.set_xy(LEFT_M, a_y)
        pdf.multi_cell(col_w, 4.3, f'"{a_q}"' if a_q else "(no answer)")
        end_a = pdf.get_y()
        pdf.set_xy(LEFT_M + col_w + 4, a_y)
        pdf.multi_cell(col_w, 4.3, f'"{b_q}"' if b_q else "(no answer)")
        end_b = pdf.get_y()
        pdf.set_y(max(end_a, end_b))
        pdf.ln(1)


def _render_alignment_before_agreement_closing(
    pdf: "_JointAgreementPDF", alignment_report: Dict[str, Any],
):
    """Closing page — mirrors sacoparentsalign's thematic Page 3.
    Large title, one-line takeaway, a pull-quote, and the SA CoParents
    tagline strip. Kept simple so the visual weight lands on the words."""
    pdf.add_page()
    pdf.ln(30)
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(61, 26, 120)
    pdf.multi_cell(CONTENT_W, 10, "Alignment Before Agreement")
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(4)
    line = (alignment_report or {}).get("closing_line") or ""
    if line:
        pdf.set_x(LEFT_M)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(*TEXT_MID)
        pdf.multi_cell(CONTENT_W, 6, line)
        pdf.set_text_color(*TEXT_DARK)
    quote = (alignment_report or {}).get("closing_quote") or ""
    if quote:
        pdf.ln(6)
        # Pull-quote treatment — italic + left rule + dark text.
        y_top = pdf.get_y()
        pdf.set_draw_color(61, 26, 120)
        pdf.set_line_width(0.8)
        pdf.line(LEFT_M, y_top, LEFT_M, y_top + 20)
        pdf.set_xy(LEFT_M + 4, y_top)
        pdf.set_font("Helvetica", "I", 12)
        pdf.multi_cell(CONTENT_W - 4, 6, f'"{quote}"')
    # SA CoParents brand strip at the bottom.
    pdf.ln(10)
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 5, ORG_NAME, ln=1)
    pdf.set_x(LEFT_M)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(CONTENT_W, 4.5, ORG_TAGLINE)
    pdf.set_text_color(*TEXT_DARK)


def _bucket_header(pdf: _JointAgreementPDF, title: str, description: str,
                   count: Any, accent: tuple):
    """Coloured strip + title + description + optional count pill."""
    pdf.ln(2)
    strip_y = pdf.get_y()
    pdf.set_fill_color(*accent)
    pdf.rect(LEFT_M, strip_y, 3, 10, "F")
    pdf.set_xy(LEFT_M + 5, strip_y)
    pdf.set_text_color(*accent)
    pdf.set_font("Helvetica", "B", 12)
    title_text = title
    if isinstance(count, int) and count > 0:
        title_text = f"{title}  ({count})"
    pdf.cell(0, 5, title_text, ln=1)
    pdf.set_x(LEFT_M + 5)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(CONTENT_W - 5, 4.2, description)
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1)


def _bucket_empty(pdf: _JointAgreementPDF, msg: str):
    pdf.set_x(LEFT_M + 5)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(CONTENT_W - 5, 4.2, msg)
    pdf.set_text_color(*TEXT_DARK)


def _render_both_proposed_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    items = data.get("items") or []
    if not items:
        _bucket_empty(
            pdf,
            "No overlapping clauses yet - as each parent finalises their "
            "draft, the shared clauses will surface here first.",
        )
        return
    pdf.set_font("Helvetica", "", 9)
    for it in items:
        area = (it.get("area") or it.get("section_title") or "").strip()
        text = (it.get("text") or "").strip()
        if area:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*TEXT_MID)
            pdf.cell(0, 4.2, area, ln=1)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M + 5)
        pdf.multi_cell(CONTENT_W - 5, 4.4, "- " + text)
        pdf.ln(0.4)


def _render_different_ideas_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any],
                                   parent_a: str, parent_b: str):
    items = data.get("items") or []
    if not items:
        _bucket_empty(
            pdf,
            "No divergent clauses - you've both proposed the same things "
            "across every section.",
        )
        return
    col_w = (CONTENT_W - 5 - 4) / 2
    for it in items:
        topic = (it.get("topic") or "").strip()
        a_text = (it.get("parent_a") or "").strip()
        b_text = (it.get("parent_b") or "").strip()
        if topic:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*TEXT_MID)
            pdf.cell(0, 4.2, topic, ln=1)
            pdf.set_text_color(*TEXT_DARK)
        # Two-column strip.
        y_top = pdf.get_y()
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(61, 26, 120)
        pdf.set_xy(LEFT_M + 5, y_top)
        pdf.cell(col_w, 4, parent_a)
        pdf.set_text_color(15, 111, 111)
        pdf.set_xy(LEFT_M + 5 + col_w + 4, y_top)
        pdf.cell(col_w, 4, parent_b)
        pdf.ln(4.3)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Helvetica", "", 8.7)
        a_y = pdf.get_y()
        pdf.set_xy(LEFT_M + 5, a_y)
        pdf.multi_cell(col_w, 4.3, a_text or "(no clause proposed)")
        end_a = pdf.get_y()
        pdf.set_xy(LEFT_M + 5 + col_w + 4, a_y)
        pdf.multi_cell(col_w, 4.3, b_text or "(no clause proposed)")
        end_b = pdf.get_y()
        pdf.set_y(max(end_a, end_b))
        pdf.ln(1)


def _render_refinement_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    items = data.get("items") or []
    if not items:
        _bucket_empty(
            pdf,
            "Nothing is currently flagged as unresolved. If a topic feels "
            "unsettled, add it to your Foundation Statement so it "
            "surfaces here.",
        )
        return
    for it in items:
        topic = (it.get("topic") or "Open item").strip()
        detail = (it.get("detail") or "").strip()
        both_flagged = bool(it.get("both_flagged"))
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*TEXT_DARK)
        prefix = topic
        if both_flagged:
            prefix = f"{topic}  [both flagged]"
        pdf.cell(0, 4.4, prefix, ln=1)
        if detail:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "", 8.8)
            pdf.set_text_color(*TEXT_MID)
            pdf.multi_cell(CONTENT_W - 5, 4.3, detail)
            pdf.set_text_color(*TEXT_DARK)
        pdf.ln(0.4)


def _render_options_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    for it in (data.get("items") or []):
        title = (it.get("title") or "").strip()
        detail = (it.get("detail") or "").strip()
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 4.4, title, ln=1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "", 8.8)
        pdf.multi_cell(CONTENT_W - 5, 4.3, detail)
        pdf.ln(0.5)


def _render_questions_bucket(pdf: _JointAgreementPDF, data: Dict[str, Any]):
    for idx, it in enumerate((data.get("items") or []), start=1):
        topic = (it.get("topic") or "").strip()
        q = (it.get("question") or "").strip()
        if topic:
            pdf.set_x(LEFT_M + 5)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(15, 111, 111)
            pdf.cell(0, 4.2, f"{idx}. {topic}", ln=1)
            pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(LEFT_M + 5)
        pdf.set_font("Helvetica", "I", 8.8)
        pdf.multi_cell(CONTENT_W - 5, 4.3, f'"{q}"')
        pdf.ln(0.5)


_BUCKET_RENDERERS = {
    "what_you_both_proposed":         "both",
    "where_you_have_different_ideas": "diff",
    "may_need_refinement":            "refine",
    "options_to_consider":            "options",
    "questions_for_next_conversation": "questions",
}


def _render_parent_view(pdf: _JointAgreementPDF, parent_view: Dict[str, Any],
                        parent_a: str, parent_b: str):
    """Render the 5-bucket parent-friendly view. Order preserved so the
    on-screen and PDF experiences march in lockstep."""
    for key in (
        "what_you_both_proposed",
        "where_you_have_different_ideas",
        "may_need_refinement",
        "options_to_consider",
        "questions_for_next_conversation",
    ):
        data = parent_view.get(key)
        if not data:
            continue
        accent = _BUCKET_ACCENTS.get(key, INFO)
        _bucket_header(
            pdf,
            data.get("title") or key.replace("_", " ").title(),
            data.get("description") or "",
            data.get("count"),
            accent,
        )
        mode = _BUCKET_RENDERERS.get(key)
        if mode == "both":
            _render_both_proposed_bucket(pdf, data)
        elif mode == "diff":
            _render_different_ideas_bucket(pdf, data, parent_a, parent_b)
        elif mode == "refine":
            _render_refinement_bucket(pdf, data)
        elif mode == "options":
            _render_options_bucket(pdf, data)
        elif mode == "questions":
            _render_questions_bucket(pdf, data)
        pdf.ln(1.5)


def _bucket(
    pdf: _JointAgreementPDF, label: str, items: List[Any], colour, *,
    parent_a: str, parent_b: str, mode: str,
):
    """Render one bucket (both_proposed / parent_a_only / parent_b_only)."""
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*colour)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, label.upper(), ln=1)
    pdf.set_draw_color(*colour)
    y = pdf.get_y()
    pdf.line(LEFT_M, y, LEFT_M + 30, y)
    pdf.set_text_color(*TEXT_DARK)

    if not items:
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*TEXT_MID)
        pdf.set_x(LEFT_M)
        pdf.multi_cell(CONTENT_W, 4.4, "(none)")
        pdf.set_text_color(*TEXT_DARK)
        return

    if mode == "both":
        for item in items:
            area = item.get("area") or ""
            a_text = item.get("parent_a_text") or ""
            b_text = item.get("parent_b_text") or ""
            if area:
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.set_text_color(*TEXT_MID)
                pdf.set_x(LEFT_M)
                pdf.cell(0, 4.2, area, ln=1)
                pdf.set_text_color(*TEXT_DARK)
            # Two-column strip.
            col_w = (CONTENT_W - 4) / 2
            y_top = pdf.get_y()
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(*TEXT_MID)
            pdf.set_xy(LEFT_M, y_top)
            pdf.cell(col_w, 4, parent_a)
            pdf.set_xy(LEFT_M + col_w + 4, y_top)
            pdf.cell(col_w, 4, parent_b)
            pdf.ln(4.3)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*TEXT_DARK)
            a_y = pdf.get_y()
            pdf.set_xy(LEFT_M, a_y)
            pdf.multi_cell(col_w, 4.3, a_text)
            end_a = pdf.get_y()
            pdf.set_xy(LEFT_M + col_w + 4, a_y)
            pdf.multi_cell(col_w, 4.3, b_text)
            end_b = pdf.get_y()
            pdf.set_y(max(end_a, end_b))
            pdf.ln(0.5)
    else:  # a_only / b_only
        pdf.set_font("Helvetica", "", 8.7)
        for item in items:
            area = item.get("area") or ""
            text = item.get("text") or ""
            pdf.set_x(LEFT_M)
            if area:
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.set_text_color(*TEXT_MID)
                pdf.cell(0, 4.2, area, ln=1)
                pdf.set_font("Helvetica", "", 8.7)
                pdf.set_text_color(*TEXT_DARK)
            pdf.set_x(LEFT_M)
            pdf.multi_cell(CONTENT_W, 4.4, "- " + text)
            pdf.ln(0.3)


def _hex_to_rgb(hex_color: Optional[str]) -> Optional[tuple]:
    """Convert a #RRGGBB or #RGB hex string to an (r, g, b) tuple.
    Returns None for empty / invalid inputs so the cover-page
    branding block can fall back to the SA CoParents purple."""
    if not hex_color:
        return None
    val = hex_color.strip().lstrip("#")
    if len(val) == 3:
        val = "".join(c * 2 for c in val)
    if len(val) != 6:
        return None
    try:
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
    except ValueError:
        return None


def _cover_page(pdf: _JointAgreementPDF, payload: Dict[str, Any]):
    pdf._is_cover = True
    pdf.add_page()
    pdf.set_fill_color(*SAND)
    pdf.rect(0, 0, PAGE_W, 60, "F")
    if os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=15, y=14, w=24, h=24)
        except Exception:
            pass
    pdf.set_xy(50, 18)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 6, ORG_NAME, ln=1)
    pdf.set_x(50)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 4, ORG_TAGLINE, ln=1)
    pdf.set_text_color(*TEXT_DARK)

    pdf.set_xy(LEFT_M, 72)
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(CONTENT_W, 8, payload.get("report_title") or "")
    pdf.ln(1)
    subtitle = payload.get("report_subtitle") or ""
    if subtitle:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(61, 26, 120)
        pdf.set_x(LEFT_M)
        pdf.cell(0, 6, subtitle, ln=1)
        pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1)
    tagline = payload.get("report_tagline") or (
        "Draft compiled from both parents' individual drafts"
    )
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 5, tagline)
    pdf.set_text_color(*TEXT_DARK)

    # Parents.
    pdf.ln(4)
    for label, value in [
        ("Parent A", payload.get("parent_a_name") or "-"),
        ("Parent B", payload.get("parent_b_name") or "-"),
        ("Generated", pdf._generated_at),
        ("Share ID", payload.get("share_id") or "-"),
    ]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(LEFT_M)
        pdf.cell(35, 5, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, value, ln=1)

    # Draft-for-discussion banner.
    pdf.ln(6)
    pdf.set_fill_color(255, 246, 216)
    pdf.set_draw_color(*WARN)
    pdf.set_line_width(0.5)
    banner_y = pdf.get_y()
    pdf.rect(LEFT_M, banner_y, CONTENT_W, 65, "DF")
    pdf.set_xy(LEFT_M + 4, banner_y + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WARN)
    pdf.cell(0, 5, "This is a draft for discussion.", ln=1)
    pdf.set_xy(LEFT_M + 4, banner_y + 10)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(CONTENT_W - 8, 4.2, payload.get("disclaimer") or "")

    # Neutral-language note.
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.2, payload.get("neutral_language_note") or "")
    pdf.set_text_color(*TEXT_DARK)

    # Convergence at a glance.
    summary = payload.get("summary") or {}
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*OK)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, "AT A GLANCE", ln=1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.5,
        f"- {summary.get('both_proposed', 0)} clauses proposed by BOTH parents\n"
        f"- {summary.get('parent_a_only', 0)} clauses proposed by "
        f"{payload.get('parent_a_name') or 'Parent A'} only\n"
        f"- {summary.get('parent_b_only', 0)} clauses proposed by "
        f"{payload.get('parent_b_name') or 'Parent B'} only\n"
        f"- Convergence: {summary.get('converged_pct', 0)}%")

    # Iter194 · optional firm branding strip. Rendered as a soft
    # bottom-of-cover footer so the un-branded sample stays visually
    # identical when no branding was supplied.
    branding = payload.get("branding") or {}
    firm = (branding.get("firm") or "").strip()
    if firm:
        pdf.ln(6)
        primary = _hex_to_rgb(branding.get("primary_color")) or (61, 26, 120)
        y = pdf.get_y()
        pdf.set_fill_color(*primary)
        pdf.rect(LEFT_M, y, CONTENT_W, 12, "F")
        pdf.set_xy(LEFT_M + 4, y + 2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 4, "PREPARED FOR", ln=1)
        pdf.set_xy(LEFT_M + 4, y + 6)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 5, firm[:80], ln=1)
        pdf.set_text_color(*TEXT_DARK)

    pdf._is_cover = False


def build_joint_agreement_pdf(payload: Dict[str, Any]) -> bytes:
    """Render the Joint Alignment Report PDF and return raw bytes.

    Iter190 flow — mirrors sacoparentsalign.com's 10-section Joint
    Alignment Report:

      * Cover page (title framed as "Step One - Alignment Before
        Agreement", parents, at-a-glance summary, disclaimer).
      * Court-report disclaimer page — six-bullet caveats block.
      * SS1..SS10 Alignment Report body — Purpose / What Both Agree /
        Where Perspectives Differ / Child's Identified Needs /
        Alignment Map (colour-coded) / Areas for Conversation /
        Options and Resources / Potential Alignment / Questions for
        the Parents / Possible Next Steps.
      * Closing thematic page: "Alignment Before Agreement" quote.
      * Appendix A - Detailed Item Breakdown (kept for attorneys /
        mediators who want to see every clause verbatim per section).
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pdf = _JointAgreementPDF(
        generated_at=now,
        share_id=payload.get("share_id") or "-",
    )
    pdf.set_auto_page_break(auto=True, margin=18)

    _cover_page(pdf, payload)

    parent_a = payload.get("parent_a_name") or "Parent A"
    parent_b = payload.get("parent_b_name") or "Parent B"

    # Court-report disclaimer — six-bullet block on its own page right
    # after the cover so the "what this document is / is not" caveats
    # are unmissable before the section flow.
    pdf.add_page()
    author_label = " & ".join(
        n for n in (payload.get("parent_a_name"), payload.get("parent_b_name")) if n
    ) or None
    draw_court_report_disclaimer(
        pdf,
        author_name=author_label,
        both_parents=True,
    )

    # ------------------------------------------------------------------
    # Alignment Report body — 10 numbered sections + closing page.
    # Every section calls `add_page()` explicitly so the numbered
    # heading + body always land on a fresh page. This mirrors the
    # sacoparentsalign layout where each section is its own visual
    # unit rather than a continuous scroll.
    # ------------------------------------------------------------------
    alignment_report = payload.get("alignment_report") or {}
    parent_view = payload.get("parent_view") or {}

    # SS1 Purpose of This Report
    pdf.add_page()
    _numbered_section_heading(
        pdf, 1, "Purpose of This Report",
        "Framed as Step One - Alignment Before Agreement.",
    )
    _body(
        pdf,
        alignment_report.get("purpose_note") or (
            "This report shows how SA CoParents compares the "
            "independently provided perspectives of both parents."
        ),
        size=10,
    )

    # SS2 What Both Parents Agree About
    pdf.add_page()
    both_bucket = parent_view.get("what_you_both_proposed") or {}
    _numbered_section_heading(
        pdf, 2, "What Both Parents Agree About",
        both_bucket.get("description") or "",
    )
    _render_both_proposed_bucket(pdf, both_bucket)
    # Iter191: When both parents completed the sacoparentsalign
    # free-text reflection, surface the shared-phrase bullets on the
    # same page so mediators see the KEYWORD alignment right next to
    # the CLAUSE alignment. Falls through cleanly when reflections
    # were not submitted.
    reflection_analysis = (payload.get("alignment_report") or {}).get(
        "reflection_analysis"
    ) or {}
    _render_reflection_shared_bullets(pdf, reflection_analysis)

    # SS3 Where the Parents See Things Differently
    pdf.add_page()
    diff_bucket = parent_view.get("where_you_have_different_ideas") or {}
    _numbered_section_heading(
        pdf, 3, "Where the Parents See Things Differently",
        diff_bucket.get("description") or "",
    )
    _render_different_ideas_bucket(pdf, diff_bucket, parent_a, parent_b)
    # Iter191: verbatim two-column quotes from the reflection prompts.
    _render_reflection_verbatim_quotes(pdf, reflection_analysis)

    # SS4 Child's Identified Needs
    pdf.add_page()
    _numbered_section_heading(
        pdf, 4, "Child's Identified Needs",
        "The neutral, child-focused needs surfaced by both parents' "
        "drafts. Backfilled with SA CoParents defaults so the section "
        "is never blank.",
    )
    _render_bullet_list(pdf, alignment_report.get("child_identified_needs") or [])

    # SS5 Alignment Map — colour-coded per section.
    pdf.add_page()
    _numbered_section_heading(
        pdf, 5, "Alignment Map",
        "Colour-coded overview across every merged section. Green = "
        "Strong. Amber = Moderate. Red = Needs discussion.",
    )
    _render_alignment_map(pdf, alignment_report.get("alignment_map") or [])

    # SS6 Areas for Conversation
    pdf.add_page()
    refine_bucket = parent_view.get("may_need_refinement") or {}
    _numbered_section_heading(
        pdf, 6, "Areas for Conversation",
        refine_bucket.get("description") or "",
    )
    _render_refinement_bucket(pdf, refine_bucket)

    # SS7 Options and Resources
    pdf.add_page()
    options_bucket = parent_view.get("options_to_consider") or {}
    _numbered_section_heading(
        pdf, 7, "Options and Resources",
        options_bucket.get("description") or "",
    )
    _render_options_bucket(pdf, options_bucket)

    # SS8 Potential Areas of Alignment
    pdf.add_page()
    _numbered_section_heading(
        pdf, 8, "Potential Areas of Alignment",
        "Clauses each parent wrote separately that are close in spirit "
        "but not yet identical. Candidates for a short conversation.",
    )
    _render_potential_alignment(
        pdf, alignment_report.get("potential_alignment") or [], parent_a, parent_b,
    )

    # SS9 Questions for the Parents
    pdf.add_page()
    questions_bucket = parent_view.get("questions_for_next_conversation") or {}
    _numbered_section_heading(
        pdf, 9, "Questions for the Parents",
        questions_bucket.get("description") or "",
    )
    _render_questions_bucket(pdf, questions_bucket)

    # SS10 Possible Next Steps
    pdf.add_page()
    _numbered_section_heading(
        pdf, 10, "Possible Next Steps",
        "Neutral, non-prescriptive options for the next conversation or "
        "next professional touchpoint.",
    )
    _render_next_steps(pdf, alignment_report.get("possible_next_steps") or [])

    # Closing thematic page — "Alignment Before Agreement".
    _render_alignment_before_agreement_closing(pdf, alignment_report)

    # ------------------------------------------------------------------
    # Appendix A - Detailed Item Breakdown (kept for professionals).
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 7, "Appendix A - Detailed Item Breakdown", ln=1)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(
        CONTENT_W, 4.5,
        "Every clause shown verbatim under the parent who proposed it, "
        "grouped by section. Intended for attorneys, mediators, and "
        "therapists reviewing the full draft.",
    )
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(2)

    for section in payload.get("sections") or []:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_x(LEFT_M)
        pdf.cell(0, 6, section.get("title") or "", ln=1)
        desc = section.get("description")
        if desc:
            _body(pdf, desc, size=8.5, italic=True)

        _bucket(pdf, "Both proposed", section.get("both_proposed") or [], OK,
                parent_a=parent_a, parent_b=parent_b, mode="both")
        _bucket(pdf, f"{parent_a} only", section.get("parent_a_only") or [], INFO,
                parent_a=parent_a, parent_b=parent_b, mode="a")
        _bucket(pdf, f"{parent_b} only", section.get("parent_b_only") or [], WARN,
                parent_a=parent_a, parent_b=parent_b, mode="b")
        pdf.ln(2)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
