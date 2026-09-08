"""Case Status PDF — small mediator-facing PDF summarising a Joint
Alignment Case at its current state. Downloaded from
`/professional/joint-alignment/mine` via
`GET /api/professional/joint-alignment/cases/{id}/status-report.pdf`.

Always includes:
  * Case ID, assessment lane, status, dates.
  * Professional of record (from the case doc).
  * Per-parent status (invited / accepted / completed) — without
    surfacing raw parent answers.
  * The six-caveat court-report disclaimer.
  * The firm-name + download-timestamp watermark on every page so
    the recipient can trace which copy they received.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fpdf import FPDF

from court_report_disclaimer import (
    apply_professional_watermark,
    draw_court_report_disclaimer,
)
from pdf_base import render_pdf_copyright
from safety_assessment_pdf import _safe


class _CaseStatusPDF(FPDF):
    """FPDF subclass that runs `_safe(...)` on every text cell so
    en-dashes / em-dashes / smart quotes never escape latin-1 and
    crash the render — matches the guardrail used by
    `SafetyAssessmentPDF`."""

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = _safe(kwargs["text"])
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        if "text" in kwargs:
            kwargs["text"] = _safe(kwargs["text"])
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self) -> None:  # noqa: D401 - fpdf hook
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 130)
        self.cell(0, 6, "SA CoParents - Joint Alignment Case Status", ln=1, align="R")
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:  # noqa: D401 - fpdf hook
        render_pdf_copyright(self)


def _fmt_dt(v: Any) -> str:
    if not v:
        return "-"
    try:
        if isinstance(v, str):
            return v.split("T")[0]
        return v.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return "-"


def _parent_status_label(p: Dict[str, Any]) -> str:
    if p.get("assessment_completed_at"):
        return "Assessment complete"
    if p.get("accepted_at"):
        return "Invitation accepted - assessment pending"
    return "Invitation sent - not yet accepted"


def build_case_status_pdf(
    case: Dict[str, Any],
    *,
    watermark_firm_name: Optional[str] = None,
) -> bytes:
    pdf = _CaseStatusPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(26, 19, 48)
    pdf.cell(0, 10, "Joint Alignment Case Status", ln=1)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(75, 69, 103)
    case_id = case.get("case_id") or "-"
    pdf.cell(0, 6, f"Case {case_id}", ln=1)
    pdf.ln(3)

    # Two-column meta strip
    pdf.set_font("Helvetica", "", 10)
    left_col = [
        ("Assessment", (case.get("assessment_type") or "").replace("-", " ") or "-"),
        ("Status", (case.get("status") or "pending").replace("_", " ")),
        ("Origin", case.get("origin") or "in_app_professional"),
        ("Firm reference", case.get("align_case_reference") or "-"),
    ]
    right_col = [
        ("Created", _fmt_dt(case.get("created_at"))),
        ("Case expires", _fmt_dt(case.get("case_expires_at"))),
        ("Professional",
         ((case.get("professional") or {}).get("name")) or "-"),
        ("Professional email",
         ((case.get("professional") or {}).get("email")) or "-"),
    ]
    y0 = pdf.get_y()
    for label, value in left_col:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(140, 140, 160)
        pdf.cell(38, 5, label.upper(), ln=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(26, 19, 48)
        pdf.cell(50, 5, str(value)[:60], ln=1)
    y_left = pdf.get_y()

    pdf.set_xy(15 + 90, y0)
    for label, value in right_col:
        x_cursor = pdf.get_x()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(140, 140, 160)
        pdf.cell(38, 5, label.upper(), ln=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(26, 19, 48)
        pdf.cell(60, 5, str(value)[:60], ln=1)
        pdf.set_x(x_cursor)
    pdf.set_y(max(pdf.get_y(), y_left) + 4)

    # Parents block
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 8, "Parents", ln=1)
    pdf.set_draw_color(230, 224, 238)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(15, y, 200, y)
    pdf.ln(3)

    for i, parent in enumerate(case.get("parents") or []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 19, 48)
        pdf.cell(0, 6, f"Parent {i + 1} - {parent.get('name') or parent.get('email') or '-'}", ln=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(75, 69, 103)
        pdf.cell(0, 5, f"Email: {parent.get('email') or '-'}", ln=1)
        pdf.cell(0, 5, f"Status: {_parent_status_label(parent)}", ln=1)
        pdf.cell(0, 5, f"Accepted: {_fmt_dt(parent.get('accepted_at'))}", ln=1)
        pdf.cell(0, 5, f"Completed: {_fmt_dt(parent.get('assessment_completed_at'))}", ln=1)
        pdf.ln(3)

    # Court-report disclaimer
    both = bool(
        (case.get("parents") or [{}, {}])[0].get("assessment_completed_at")
        and (case.get("parents") or [{}, {}])[1].get("assessment_completed_at")
    ) if len(case.get("parents") or []) == 2 else False
    parents_list = case.get("parents") or []
    author_label = " & ".join(
        p.get("name") for p in parents_list if p.get("name")
    ) or None
    pdf.ln(2)
    draw_court_report_disclaimer(
        pdf,
        author_name=author_label,
        both_parents=both,
    )

    # Footer
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 160)
    pdf.ln(4)
    pdf.multi_cell(
        0, 4,
        "This document is a status summary generated on request. "
        "It contains no verbatim parent answers and is not intended "
        "to be filed with a court without professional review.",
    )

    # Watermark last so the firm-name + timestamp lands on every page
    # already emitted above (title, parents, disclaimer).
    apply_professional_watermark(pdf, watermark_firm_name)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


def build_case_status_pdf_iso_now() -> str:
    """Helper for tests — returns the same timestamp format the
    watermark uses so tests can assert exact matches."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
