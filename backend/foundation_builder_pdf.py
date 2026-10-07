"""Branded PDF for the Card 4 Foundation Statement builder (render-only)."""
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
PILLAR_RGB = {"goals": (139, 92, 246), "child": (16, 185, 129), "values": (249, 115, 22), "path": (14, 165, 233)}


class _FBPDF(FPDF):
    def __init__(self, disclaimer: str):
        super().__init__(format="Letter")
        self._disclaimer = disclaimer
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PURPLE)
        self.cell(0, 6, _safe("SA CoParents  ·  Foundation Statement"), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 3.5, "START WITH ALIGNMENT, END WITH AGREEMENT", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(216, 199, 251)
        self.line(self.l_margin, self.get_y() + 1.5, self.w - self.r_margin, self.get_y() + 1.5)
        self.ln(5)

    def footer(self):
        self.set_y(-16)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, _safe(f"{self._disclaimer}   Page {self.page_no()}"), align="C")
        render_pdf_copyright(self)


def _pillars(pdf: _FBPDF, content: Dict[str, Any]) -> None:
    for p in content["pillars"]:
        y = pdf.get_y()
        pdf.set_fill_color(*PILLAR_RGB.get(p["key"], PURPLE))
        pdf.ellipse(pdf.l_margin, y + 0.8, 3.4, 3.4, "F")
        pdf.set_xy(pdf.l_margin + 6, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*INK)
        pdf.cell(55, 5, _safe(p["title"]))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 5, _safe(p["body"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _answers(pdf: _FBPDF, content: Dict[str, Any], fields: Dict[str, str]) -> None:
    for f in content["fields"]:
        if f["type"] != "textarea":
            continue
        if pdf.get_y() > 235:
            pdf.add_page()
        pdf.set_fill_color(*PURPLE)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, _safe(f"  {f['label']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        body = (fields.get(f["key"]) or "").strip()
        pdf.set_fill_color(243, 239, 254)
        pdf.set_text_color(*(INK if body else MUTED))
        pdf.set_font("Helvetica", "" if body else "I", 9.5)
        pdf.multi_cell(pdf.epw, 5.2, _safe(body or "Not written yet."), fill=True, padding=(2.5, 3, 2.5, 3),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)


def _signatures(pdf: _FBPDF, content: Dict[str, Any]) -> None:
    if pdf.get_y() > 225:
        pdf.add_page()
    pdf.ln(4)
    pdf.set_draw_color(*MUTED)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    for _ in range(2):
        y = pdf.get_y() + 10
        pdf.line(pdf.l_margin, y, pdf.l_margin + 110, y)
        pdf.line(pdf.l_margin + 125, y, pdf.w - pdf.r_margin, y)
        pdf.set_xy(pdf.l_margin, y + 1)
        pdf.cell(110, 4, _safe(content["signature_label"]))
        pdf.set_x(pdf.l_margin + 125)
        pdf.cell(0, 4, _safe(content["date_label"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.ln(4)


def build_foundation_builder_pdf(*, content: Dict[str, Any], fields: Dict[str, str]) -> bytes:
    pdf = _FBPDF(content["disclaimer"])
    pdf.add_page()
    pdf.set_font("Times", "BI", 12)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _safe(content["badge"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, _safe(content["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(pdf.epw, 5, _safe(content["intro"]), new_x="LMARGIN", new_y="NEXT")
    now = datetime.now(timezone.utc)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.cell(0, 6, _safe(f"Prepared {now.strftime('%B')} {now.day}, {now.year}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    by_key = {f["key"]: f for f in content["fields"]}
    for key in ("parent_names", "child_info"):
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*INK)
        pdf.cell(55, 6, _safe(by_key[key]["label"]))
        pdf.set_font("Helvetica", "", 9.5)
        pdf.cell(0, 6, _safe((fields.get(key) or "").strip() or "-"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    _pillars(pdf, content)
    _answers(pdf, content, fields)
    _signatures(pdf, content)

    pdf.set_fill_color(243, 239, 254)
    pdf.set_text_color(*PURPLE)
    pdf.set_font("Times", "BI", 13)
    pdf.cell(0, 8, _safe(content["footer_title"]), align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, _safe(content["footer_tags"].upper()), align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
