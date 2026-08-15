"""PDF renderer for the Joint Co-Parenting Agreement Draft.

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
from typing import Any, Dict, List

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, WARN, INFO, OK,
    ORG_NAME, ORG_TAGLINE, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe,
)


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
        self.cell(0, 5, "Joint Co-Parenting Agreement Draft", ln=1)
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


def _body(pdf: _JointAgreementPDF, text: str, *, size: int = 9, italic: bool = False):
    pdf.set_font("Helvetica", "I" if italic else "", size)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 4.6, text)


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
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.cell(0, 5, "Draft compiled from both parents' individual drafts", ln=1)
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

    pdf._is_cover = False


def build_joint_agreement_pdf(payload: Dict[str, Any]) -> bytes:
    """Render the joint agreement PDF and return raw bytes."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pdf = _JointAgreementPDF(
        generated_at=now,
        share_id=payload.get("share_id") or "-",
    )
    pdf.set_auto_page_break(auto=True, margin=18)

    _cover_page(pdf, payload)

    pdf.add_page()
    parent_a = payload.get("parent_a_name") or "Parent A"
    parent_b = payload.get("parent_b_name") or "Parent B"
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

    # Next-step callout at the very end.
    next_step = payload.get("next_step") or ""
    if next_step:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*INFO)
        pdf.set_x(LEFT_M)
        pdf.cell(0, 5, "SUGGESTED NEXT STEP", ln=1)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_x(LEFT_M)
        pdf.multi_cell(CONTENT_W, 4.5, next_step)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
