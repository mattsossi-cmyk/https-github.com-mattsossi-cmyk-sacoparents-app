"""Blank / printable version of the SNC assessment as a branded PDF.

Renders the 13-section questionnaire with response scales at the top and
empty response space for each item. Same visual identity as the individual
parent report and the neutral comparison PDF (sand header band with the
shared SA CoParents logo, purple accents, muted footer).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from fpdf import FPDF

from snc_questions import (
    CONSISTENCY_SCALE, RESPONSE_SCALE, SECTIONS, total_scored_items,
)


LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")
ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"


def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _SNCAssessmentPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 30, 15)
        self.alias_nb_pages()
        self.compress = False

    def header(self):
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=4, w=14, h=14)
            except Exception:  # noqa: BLE001
                pass
        self.set_xy(30, 5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(61, 26, 120)
        self.cell(0, 5, _safe(f"{ORG_NAME}  ·  Special Needs Co-Parenting Assessment"), ln=1)
        self.set_x(30)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(110, 100, 130)
        self.cell(0, 4, _safe(ORG_TAGLINE), ln=1)
        self.set_draw_color(220, 214, 232)
        self.set_line_width(0.3)
        self.line(15, 23, self.w - 15, 23)
        self.set_y(28)
        self.set_text_color(30, 24, 54)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe(f"Assessment Workbook  ·  Page {self.page_no()} of {{nb}}"),
                  align="C")

    # ----- typography ----------------------------------------------------
    def h1(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 9, _safe(text))
        self.ln(1)

    def h2(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 7, _safe(text))
        self.ln(0.5)

    def h3(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 5.5, _safe(text))

    def body(self, text: str, italic: bool = False):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I" if italic else "", 10)
        self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 5.2, _safe(text))
        self.ln(0.5)

    def small(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8.5)
        self.set_text_color(110, 100, 130)
        self.multi_cell(self.epw, 4.5, _safe(text))
        self.ln(0.5)

    def response_line(self, height: float = 6):
        """A short empty rule for free-text answers."""
        y = self.get_y() + 4
        self.set_draw_color(200, 194, 220)
        self.set_line_width(0.25)
        self.line(self.l_margin, y, self.l_margin + self.epw, y)
        self.set_y(y + height)

    def response_lines(self, n: int = 2):
        for _ in range(n):
            self.response_line()

    def rating_chips(self, scale: Iterable[Dict[str, Any]]):
        """Print a row of hollow chips (unfilled) so the parent can circle."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(61, 26, 120)
        self.set_draw_color(210, 200, 232)
        self.set_line_width(0.3)
        x = self.l_margin
        y = self.get_y() + 1
        chip_h = 5.5
        pad = 3
        for opt in scale:
            label = f"{opt.get('value')}. {opt.get('label')}"
            text = _safe(label)
            w = self.get_string_width(text) + pad * 2
            if x + w > self.l_margin + self.epw:
                x = self.l_margin
                y += chip_h + 1.5
            self.set_xy(x, y)
            self.cell(w, chip_h, text, border=1, align="C")
            x += w + 1.5
        self.set_y(y + chip_h + 2)

    def option_boxes(self, options: List[str]):
        """A list of empty checkboxes for single/multi-select prompts."""
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 24, 54)
        for opt in options or []:
            self.set_x(self.l_margin)
            self.set_draw_color(180, 170, 200)
            self.set_line_width(0.25)
            y = self.get_y()
            # Draw a small square box
            self.rect(self.l_margin, y + 1.0, 3.5, 3.5)
            self.set_xy(self.l_margin + 5.5, y)
            self.multi_cell(self.epw - 5.5, 5.5, _safe(opt))
            self.ln(0.5)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _render_cover(pdf: _SNCAssessmentPDF) -> None:
    pdf.add_page()
    pdf.ln(4)
    pdf.h1("Special Needs Co-Parenting")
    pdf.h1("Assessment Workbook")
    pdf.ln(2)
    pdf.body(
        "This 13-section assessment is a private planning tool. It is not a "
        "diagnosis of your child, is not a determination of parental fitness, "
        "and is not legal advice. Complete it from your own perspective — your "
        "co-parent will complete their own copy independently."
    )
    pdf.ln(1)

    pdf.h2("How to use this workbook")
    pdf.body(
        "For each rated item, circle one option from the response scale below. "
        "For multi-select items, tick every box that applies. For open-ended "
        "prompts, write your answer on the lines provided. You do not need to "
        "finish in one sitting."
    )

    pdf.h2("Response scale (Sections 2 to 12)")
    pdf.rating_chips(RESPONSE_SCALE)

    pdf.h2("Consistency scale (Section 6)")
    pdf.rating_chips(CONSISTENCY_SCALE)

    pdf.ln(2)
    pdf.small(
        "Section 11 (Family Violence & Communication Safety) is kept private "
        "to you. It is never shared automatically with your co-parent and "
        "never included in a comparison view."
    )


def _render_item(pdf: _SNCAssessmentPDF, item: Dict[str, Any]) -> None:
    itype = item.get("type")
    prompt = item.get("prompt") or ""
    # Prompt
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 5.5, _safe(prompt))
    pdf.ln(0.3)

    if itype == "likert":
        pdf.rating_chips(RESPONSE_SCALE)
    elif itype == "consistency":
        pdf.rating_chips(CONSISTENCY_SCALE)
    elif itype in ("multi", "single"):
        pdf.option_boxes(item.get("options") or [])
    elif itype == "textarea":
        pdf.response_lines(4)
    elif itype == "text":
        pdf.response_lines(1)
    else:
        pdf.response_lines(2)
    pdf.ln(1.5)


def _render_section(pdf: _SNCAssessmentPDF, section: Dict[str, Any]) -> None:
    pdf.add_page()
    number = section.get("number")
    name = section.get("name")
    pdf.h2(f"Section {number}. {name}")
    note = section.get("note")
    if note:
        pdf.small(note)
    for item in section.get("items", []):
        _render_item(pdf, item)


def build_snc_assessment_pdf() -> bytes:
    """Render the blank 13-section assessment to a printable PDF."""
    pdf = _SNCAssessmentPDF()
    _render_cover(pdf)
    for section in SECTIONS:
        _render_section(pdf, section)

    # Closing page with count summary
    pdf.add_page()
    pdf.h2("Assessment summary")
    pdf.body(
        f"This workbook contains 13 sections with {total_scored_items()} rated "
        "items plus intake, safety, and goals-and-priorities questions. When "
        "you complete this online at sacoparentsapp.online you receive an "
        "individual parent report you can share with mediators, teachers, or "
        "treating professionals — and, if your co-parent completes their own "
        "assessment, a neutral side-by-side."
    )
    pdf.small(
        "This assessment does not diagnose your child, is not a finding of "
        "fact, and does not determine parental fitness. Safety responses are "
        "always kept private."
    )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
