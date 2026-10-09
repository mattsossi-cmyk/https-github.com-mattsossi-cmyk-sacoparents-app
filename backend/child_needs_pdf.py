"""Branded combined PDF for Your Child's Specific Needs (render-only)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fpdf import FPDF

from self_assessment_pdf import _safe

try:
    from pdf_copyright import render_pdf_copyright  # type: ignore
except Exception:  # pragma: no cover
    def render_pdf_copyright(_pdf):
        return

PURPLE = (76, 40, 137)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
THEME = {
    "medical": (2, 132, 199),
    "educational": (22, 163, 74),
    "psychological": (234, 88, 12),
}


class _CNPDF(FPDF):
    def __init__(self, title: str, tagline: str, disclaimer: str):
        super().__init__(format="Letter")
        self._title, self._tagline, self._disclaimer = title, tagline, disclaimer
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PURPLE)
        self.cell(0, 6, _safe(f"SA CoParents  ·  {self._title}"), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 3.5, _safe(self._tagline), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(216, 199, 251)
        self.line(self.l_margin, self.get_y() + 1.5, self.w - self.r_margin, self.get_y() + 1.5)
        self.ln(5)

    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, _safe(f"{self._disclaimer}   Page {self.page_no()}"), align="C")
        render_pdf_copyright(self)


HOME_TITLE = "Across both homes"


def _category(pdf: _CNPDF, cat: Dict[str, Any], answers: Dict[str, str]) -> None:
    rgb = THEME.get(cat["key"], PURPLE)
    if pdf.get_y() > 225:
        pdf.add_page()
    pdf.set_fill_color(*rgb)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, _safe(f"  {cat['form_title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    home_done = False
    for f in cat["fields"]:
        value = answers.get(f["id"])
        if not value:
            continue
        if pdf.get_y() > 245:
            pdf.add_page()
        if f.get("group") == "home" and not home_done:
            home_done = True
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*INK)
            pdf.cell(0, 6, _safe(HOME_TITLE), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*rgb)
        pdf.multi_cell(pdf.epw, 4.8, _safe(f["label"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(pdf.epw, 5, _safe(value), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.ln(3)


def render_notices(pdf, notices: Dict[str, Any]) -> None:
    """Notice of Confidentiality + Health Information Privacy Notice (also used by the Journey Summary PDF)."""
    pdf.set_fill_color(248, 246, 252)
    for key in ("confidentiality", "privacy"):
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(76, 40, 137)
        pdf.cell(0, 5, _safe(f"  {notices[key]['title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(pdf.epw, 4.2, _safe(notices[key]["body"]), fill=True, padding=(0.5, 3, 2, 3), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)


def build_child_needs_pdf(*, content: Dict[str, Any], parent_name: str, answers: Dict[str, Dict[str, str]]) -> bytes:
    pdf = _CNPDF(content["title"], content["brand_tagline"], content["disclaimer"])
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 9, _safe(content["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9.5)
    pdf.set_text_color(*MUTED)
    now = datetime.now(timezone.utc)
    who = parent_name or "a parent"
    pdf.cell(0, 5, _safe(f"Prepared for {who}  ·  {now.strftime('%B')} {now.day}, {now.year}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(pdf.epw, 5, _safe(content["subtitle"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    render_notices(pdf, content["notices"])
    pdf.ln(2)
    for cat in content["categories"]:
        if answers.get(cat["key"]):
            _category(pdf, cat, answers[cat["key"]])
    pdf.set_fill_color(243, 239, 254)
    pdf.set_text_color(*PURPLE)
    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(pdf.epw, 8, _safe(content["footer"].upper()), align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
