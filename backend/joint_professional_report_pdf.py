"""PDF renderer for the Joint Co-Parenting Summary for Professional Review.

Layout:
  * Cover page: title, both parents' names, generated date, and the
    NOT-A-CUSTODY-EVALUATION disclaimer front and center.
  * Section pages: each of the 9 sections gets its own heading + a
    Parent A | Parent B | Alignment | Child's Need | Issue-for-discussion
    table. Neutral language only.
  * Footer on every page: "Preparation resource — Not a custody
    evaluation" + generated date.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

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

# Alignment pill colours — tuned to convey neutrality (not judgement).
_PILL = {
    "aligned":         (39, 122, 62),
    "close":           (140, 110, 20),
    "divergent":       (176, 42, 42),
    "one_only":        (110, 100, 130),
    "insufficient":    (110, 100, 130),
    "both_responded":  (61, 26, 120),
}


class _JointReportPDF(FPDF):
    def __init__(self, *, generated_at: str, share_id: str, footer_disclaimer: str):
        super().__init__()
        self._generated_at = generated_at
        self._share_id = share_id
        self._footer_disclaimer = footer_disclaimer
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
        self.cell(0, 5, "Joint Co-Parenting Summary for Professional Review", ln=1)
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
            f"{self._footer_disclaimer} - Generated {self._generated_at} - "
            f"Share {self._share_id[:10]}",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


        render_pdf_copyright(self)
def _body(pdf: _JointReportPDF, text: str, *, size: int = 9, italic: bool = False):
    pdf.set_font("Helvetica", "I" if italic else "", size)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.6, text)


def _section_heading(pdf: _JointReportPDF, title: str, colour):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*colour)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 6, title, ln=1)
    pdf.set_draw_color(*colour)
    y = pdf.get_y()
    pdf.line(LEFT_M, y, LEFT_M + 30, y)
    pdf.set_text_color(*TEXT_DARK)


def _pill(pdf: _JointReportPDF, label: str, alignment: str):
    r, g, b = _PILL.get(alignment, TEXT_MID)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7.5)
    # Height matches the pill body; width grows with the label.
    text = label[:22]
    w = max(24, pdf.get_string_width(text) + 6)
    pdf.cell(w, 4.5, text, ln=0, align="C", fill=True)
    pdf.set_text_color(*TEXT_DARK)


def _row(pdf: _JointReportPDF, row: Dict[str, Any], parent_a_name: str, parent_b_name: str):
    """Render a single Parent A | Parent B | Alignment | Need | Issue block."""
    topic = row.get("topic") or ""
    pathway = row.get("pathway_label")
    pdf.ln(1.2)
    # Topic line.
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.6, topic + (f"  ({pathway})" if pathway else ""))
    # Alignment pill.
    pdf.set_x(LEFT_M)
    _pill(pdf, row.get("alignment_label") or "Not enough data",
          row.get("alignment") or "insufficient")
    pdf.ln(5)

    # Parent A / Parent B in a two-column strip.
    col_w = (CONTENT_W - 4) / 2
    y_top = pdf.get_y()
    a_text = (row.get("parent_a") or {}).get("summary") or "No response"
    b_text = (row.get("parent_b") or {}).get("summary") or "No response"

    # Parent A cell
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_xy(LEFT_M, y_top)
    pdf.cell(col_w, 4, parent_a_name)
    pdf.set_xy(LEFT_M + col_w + 4, y_top)
    pdf.cell(col_w, 4, parent_b_name)
    pdf.ln(4.5)

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

    # Child's need + issue.
    need = row.get("childs_need")
    if need:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*INFO)
        pdf.set_x(LEFT_M)
        pdf.cell(28, 4.2, "Child's need:")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(CONTENT_W - 28, 4.2, need)
    issue = row.get("issue_for_discussion")
    if issue:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WARN)
        pdf.set_x(LEFT_M)
        pdf.cell(40, 4.2, "For discussion:")
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(CONTENT_W - 40, 4.2, issue)

    # Divider.
    pdf.set_draw_color(230, 226, 240)
    pdf.set_line_width(0.2)
    y = pdf.get_y() + 1
    pdf.line(LEFT_M, y, PAGE_W - RIGHT_M, y)
    pdf.ln(1.5)


def _section(
    pdf: _JointReportPDF, section: Dict[str, Any], colour, parent_a_name: str, parent_b_name: str,
):
    _section_heading(pdf, section.get("title") or "", colour)
    desc = section.get("description")
    if desc:
        _body(pdf, desc, size=8.5, italic=True)
    rows = section.get("rows") or []
    if not rows:
        empty = section.get("empty_reason") or "No data available."
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*TEXT_MID)
        pdf.set_x(LEFT_M)
        pdf.multi_cell(CONTENT_W, 4.4, empty)
        pdf.set_text_color(*TEXT_DARK)
        return
    for row in rows:
        _row(pdf, row, parent_a_name, parent_b_name)


def _cover_page(pdf: _JointReportPDF, payload: Dict[str, Any]):
    pdf._is_cover = True
    pdf.add_page()
    # Big sand banner.
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
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, f"Prepared for professional review", ln=1)
    pdf.set_text_color(*TEXT_DARK)

    # Parents block.
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(LEFT_M)
    pdf.cell(35, 5, "Parent A:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, payload.get("parent_a_name") or "-", ln=1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(LEFT_M)
    pdf.cell(35, 5, "Parent B:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, payload.get("parent_b_name") or "-", ln=1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(LEFT_M)
    pdf.cell(35, 5, "Generated:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, pdf._generated_at, ln=1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(LEFT_M)
    pdf.cell(35, 5, "Share ID:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, payload.get("share_id") or "-", ln=1)

    # NOT a custody evaluation banner — big and prominent.
    pdf.ln(6)
    pdf.set_fill_color(252, 237, 235)
    pdf.set_draw_color(*DANGER)
    pdf.set_line_width(0.5)
    banner_y = pdf.get_y()
    pdf.rect(LEFT_M, banner_y, CONTENT_W, 60, "DF")
    pdf.set_xy(LEFT_M + 4, banner_y + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*DANGER)
    pdf.cell(0, 5, "This is not a custody evaluation.", ln=1)
    pdf.set_xy(LEFT_M + 4, banner_y + 10)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(CONTENT_W - 8, 4.2, payload.get("disclaimer") or "")

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.2, payload.get("neutral_language_note") or "")

    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.2, payload.get("safety_step") or "Safety step: not started")
    pdf.set_text_color(*TEXT_DARK)

    pdf._is_cover = False


def build_joint_report_pdf(payload: Dict[str, Any]) -> bytes:
    """Render the joint report PDF and return raw bytes."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    footer_disclaimer = "Preparation resource - Not a custody evaluation, diagnosis, or recommendation to any court"
    pdf = _JointReportPDF(
        generated_at=now,
        share_id=payload.get("share_id") or "-",
        footer_disclaimer=footer_disclaimer,
    )
    pdf.set_auto_page_break(auto=True, margin=18)

    _cover_page(pdf, payload)

    # Court-report disclaimer — six-bullet block on its own page right
    # after the cover so any mediator or judge opening the PDF sees
    # the "what this document is / is not" caveats before section
    # content. `both_parents=True` because the joint report always
    # combines two parents' inputs.
    pdf.add_page()
    parent_a = payload.get("parent_a_name") or ""
    parent_b = payload.get("parent_b_name") or ""
    author_label = " & ".join(n for n in (parent_a, parent_b) if n) or None
    draw_court_report_disclaimer(
        pdf,
        author_name=author_label,
        both_parents=True,
    )

    pdf.add_page()
    section_colours = {
        "shared_priorities":                    INFO,
        "medical":                              DANGER,
        "educational":                          INFO,
        "psychological":                        OK,
        "household_consistency":                WARN,
        "communication_concerns":               WARN,
        "areas_of_agreement":                   OK,
        "areas_where_perceptions_differ":       DANGER,
        "issues_for_professional_discussion":   WARN,
    }
    order: List[str] = [
        "shared_priorities",
        "medical",
        "educational",
        "psychological",
        "household_consistency",
        "communication_concerns",
        "areas_of_agreement",
        "areas_where_perceptions_differ",
        "issues_for_professional_discussion",
    ]
    a_name = payload.get("parent_a_name") or "Parent A"
    b_name = payload.get("parent_b_name") or "Parent B"
    for key in order:
        section = (payload.get("sections") or {}).get(key)
        if not section:
            continue
        _section(pdf, section, section_colours.get(key, INFO), a_name, b_name)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
