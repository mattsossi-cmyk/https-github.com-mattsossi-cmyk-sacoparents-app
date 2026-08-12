"""Court-facing Trauma-Informed Safety and Functioning Lens (TISFL)
Report PDF.

This variant of the safety-assessment PDF is intended for filing with
a court, mediator, or family-violence review body. Compared to the
standard parent-facing PDF it:

    * Puts the two interpretation rules on the very first page, above
      any findings, so the court sees the framing before the content.
    * Prints the three findings verbatim from the lens block (Pattern,
      Trauma Impact, Parenting-Plan Implications) with each finding on
      its own page for filing / annotation.
    * Adds a "Limits of use" and "Methodology" section that names this
      is a structured self-report screen, not a forensic evaluation.
    * Adds a signature block for the parent and (optionally) a
      qualified reviewer.
    * Includes the assessment_id + generation timestamp on every page
      footer so a filed copy is unambiguous.
    * Excludes the raw Section 1 answers by default (they contain
      graphic behavioural language). The parent can opt-in to include
      them via the `include_raw_answers` flag.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, WARN, INFO, OK,
    ORG_NAME, ORG_TAGLINE, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe, _TONE_COLORS,
)
from trauma_lens import (
    LENS_NAME, INTERPRETATION_RULES,
    COURT_REPORT_LIMITS_STATEMENT, COURT_REPORT_METHODOLOGY,
)


class _CourtReportPDF(FPDF):
    def __init__(self, assessment_id: str, generated_at: str):
        super().__init__()
        self._assessment_id = assessment_id
        self._generated_at = generated_at

    def cell(self, w=0, h=0, txt="", *args, **kwargs):  # noqa: D401
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):  # noqa: D401
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 32, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=5, w=22, h=22)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 14)
        self.set_xy(40, 7)
        self.cell(0, 7, LENS_NAME, ln=1)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*TEXT_MID)
        self.set_x(40)
        self.cell(0, 4, "Court Report - Structured Self-Report Screen", ln=1)
        self.set_x(40)
        self.cell(0, 4, f"{ORG_NAME} - {ORG_TAGLINE} - {ORG_PHONE}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(36)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Assessment {self._assessment_id} - Generated {self._generated_at} - "
            f"Not a forensic evaluation. Page {self.page_no()}",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


def _title(pdf: _CourtReportPDF, text: str, colour=None):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*(colour or INFO))
    pdf.cell(0, 8, text, ln=1)
    pdf.set_draw_color(*(colour or INFO))
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(15, y, 60, y)
    pdf.ln(2)
    pdf.set_text_color(*TEXT_DARK)


def _body(pdf: _CourtReportPDF, text: str, italic: bool = False):
    pdf.set_font("Helvetica", "I" if italic else "", 10.5)
    pdf.set_text_color(*(TEXT_MID if italic else TEXT_DARK))
    pdf.multi_cell(0, 5.8, text)
    pdf.ln(0.5)
    pdf.set_text_color(*TEXT_DARK)


def _kv(pdf: _CourtReportPDF, label: str, value: str):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(45, 6, f"{label}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_DARK)
    # Trim to a single line for the cover — assessment_id / date etc.
    # are one-liners. multi_cell was crashing on some fpdf2 builds when
    # the preceding cell() had already advanced x.
    pdf.cell(0, 6, str(value), ln=1)


def _render_cover(pdf: _CourtReportPDF, user_name: str, level: int, assessment_id: str):
    pdf.add_page()
    _title(pdf, "Court report - overview")
    _kv(pdf, "Parent name", user_name or "-")
    _kv(pdf, "Assessment id", assessment_id)
    _kv(pdf, "Generated (UTC)", pdf._generated_at)
    _kv(pdf, "Level", f"{level} of 4")
    _kv(pdf, "Lens", LENS_NAME)
    pdf.ln(3)
    _title(pdf, "How to read this report")
    for i, rule in enumerate(INTERPRETATION_RULES, start=1):
        pdf.set_font("Helvetica", "", 10.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(15)
        pdf.multi_cell(180, 6, f"{i}. {rule}")
        pdf.ln(0.5)
    pdf.ln(1)
    _title(pdf, "Limits of use", colour=DANGER)
    _body(pdf, COURT_REPORT_LIMITS_STATEMENT)
    _title(pdf, "Methodology")
    _body(pdf, COURT_REPORT_METHODOLOGY, italic=True)


def _render_finding_page(
    pdf: _CourtReportPDF,
    number: int,
    title: str,
    core_question: str,
    headline: str,
    summary: str,
    colour,
    extra_lines: List[str] | None = None,
):
    pdf.add_page()
    _title(pdf, title, colour=colour)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(0, 5.5, f"Core question: {core_question}")
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 6, headline)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, summary)
    pdf.ln(1)
    for line in extra_lines or []:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*TEXT_MID)
        pdf.multi_cell(0, 5.5, line)
        pdf.set_text_color(*TEXT_DARK)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Finding {number} of 3.", ln=1)
    pdf.set_text_color(*TEXT_DARK)


def _render_procedural_safeguards(pdf: _CourtReportPDF, safeguards: List[str]):
    pdf.add_page()
    _title(pdf, "Procedural safeguards")
    _body(
        pdf,
        "The following safeguards apply to how this assessment was completed. "
        "They are surfaced here so the court can assess whether the conditions "
        "under which the parent responded were appropriate.",
        italic=True,
    )
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 10.5)
    for item in safeguards:
        pdf.set_x(15)
        pdf.multi_cell(180, 6, f"- {item}")
        pdf.ln(0.5)
    pdf.ln(2)


def _render_signature_block(pdf: _CourtReportPDF, user_name: str, reviewer_name: str = ""):
    _title(pdf, "Signatures")
    _body(
        pdf,
        "The parent named above attests that the answers provided reflect their "
        "recollection at the time of completion. A qualified reviewer (mediator, "
        "family counsellor, or family-violence practitioner) may co-sign to "
        "acknowledge that they have discussed the findings with the parent. "
        "Neither signature is a forensic finding.",
        italic=True,
    )
    pdf.ln(6)
    _sig_line(pdf, "Parent", user_name)
    pdf.ln(6)
    _sig_line(pdf, "Reviewer (optional)", reviewer_name or "")
    pdf.ln(6)
    _sig_line(pdf, "Date", "")


def _sig_line(pdf: _CourtReportPDF, label: str, printed_name: str):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(35, 6, f"{label}:")
    pdf.set_draw_color(*TEXT_MID)
    y = pdf.get_y() + 5
    pdf.line(50, y, 195, y)
    if printed_name:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_xy(52, y - 5)
        pdf.cell(0, 5, f"Printed: {printed_name}", ln=1)
    pdf.set_text_color(*TEXT_DARK)


def build_court_report_pdf(
    *,
    user_name: str,
    generated_at: str,
    assessment_id: str,
    result: Dict[str, Any],
    safeguards: List[str],
    reviewer_name: str = "",
) -> bytes:
    """Render the TISFL Court Report PDF. Uses only the lens layer +
    interpretation rules + methodology — never the raw section-1
    behavioural answers by default so the document is safe to file.
    """
    lens = (result or {}).get("lens") or {}
    findings = lens.get("findings") or {}
    level = int((result or {}).get("level") or 4)
    try:
        pretty = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).strftime(
            "%B %d, %Y"
        )
    except Exception:
        pretty = str(generated_at or "")

    pdf = _CourtReportPDF(assessment_id=assessment_id, generated_at=pretty)
    pdf.set_auto_page_break(auto=True, margin=20)

    _render_cover(pdf, user_name=user_name, level=level, assessment_id=assessment_id)

    finding_meta = [
        ("family_violence_pattern", 1, DANGER, []),
        ("trauma_impact", 2, WARN, []),
        (
            "parenting_plan_implications",
            3,
            OK,
            [],
        ),
    ]
    for key, num, colour, extras_seed in finding_meta:
        block = findings.get(key)
        if not block:
            continue
        extras = list(extras_seed)
        if block.get("non_diagnostic_note"):
            extras.append(block["non_diagnostic_note"])
        if block.get("arrangement_spectrum"):
            extras.append(
                f"Recommended parenting-plan structure: {block['arrangement_spectrum']}."
            )
        _render_finding_page(
            pdf,
            number=num,
            title=block.get("title") or f"Finding {num}",
            core_question=block.get("core_question") or "",
            headline=block.get("headline") or "",
            summary=block.get("summary") or "",
            colour=colour,
            extra_lines=extras,
        )

    _render_procedural_safeguards(pdf, safeguards or [])

    pdf.add_page()
    _render_signature_block(pdf, user_name=user_name, reviewer_name=reviewer_name)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
