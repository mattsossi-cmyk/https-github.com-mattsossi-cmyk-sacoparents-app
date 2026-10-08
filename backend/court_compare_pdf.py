"""Side-by-side Comparison PDF for both parents on a case (only built once both are sharing)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF

from pdf_base import _safe, render_pdf_copyright

PURPLE = (76, 40, 137)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
EMERALD = (56, 161, 105)
AMBER = (180, 98, 6)
LINE = (236, 232, 245)
DISCLAIMER = "Prepared from each parent's own answers. Both parents chose to share. General information, not legal advice."


class _ComparePDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 4, _safe(DISCLAIMER), align="C")
        render_pdf_copyright(self)


def _room(pdf: FPDF, need: float) -> None:
    if pdf.get_y() + need > pdf.h - 22:
        pdf.add_page()


def _header(pdf: FPDF, data: Dict[str, Any]) -> None:
    pdf.set_fill_color(*PURPLE)
    pdf.rect(0, 0, pdf.w, 25, "F")
    pdf.set_xy(16, 6.5)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "Side-by-Side Comparison", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(16)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(221, 214, 254)
    pdf.cell(0, 5, _safe("SA CoParents  ·  Start with Alignment, End with Agreement"))
    pdf.set_xy(16, 30)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    a, b = data["names"]
    pdf.cell(0, 5, _safe(f"Case: {data['case']}     Prepared: {datetime.now():%b %d, %Y}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe(f"Parents: {a} and {b}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _section(pdf: FPDF, title: str, note: str) -> None:
    _room(pdf, 20)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6.5, _safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.2, _safe(note), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _score_table(pdf: FPDF, rows: List[Dict[str, str]], names: tuple, tone: tuple, points: Dict[str, str]) -> None:
    w_area, w_val = pdf.epw - 2 * 46, 46
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(w_area, 5, "Area")
    pdf.cell(w_val, 5, _safe(names[0][:26]), align="C")
    pdf.cell(w_val, 5, _safe(names[1][:26]), align="C", new_x="LMARGIN", new_y="NEXT")
    for r in rows:
        _room(pdf, 16 + (10 if points.get(r["area"]) else 0))
        y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*INK)
        pdf.cell(w_area, 5.4, _safe(r["area"]))
        pdf.set_text_color(*tone)
        pdf.cell(w_val, 5.4, _safe(r["mine"]), align="C")
        pdf.cell(w_val, 5.4, _safe(r["theirs"]), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 3.8, _safe(r["source"]), new_x="LMARGIN", new_y="NEXT")
        tip = points.get(r["area"])
        if tip:
            pdf.set_x(pdf.l_margin + 3)
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_text_color(*PURPLE)
            pdf.multi_cell(pdf.epw - 3, 4.3, _safe(f"Talking point: {tip}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LINE)
        pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
        pdf.set_y(max(pdf.get_y(), y) + 2.4)


def _child(pdf: FPDF, cats: List[Dict[str, Any]], names: tuple) -> None:
    for c in cats:
        _room(pdf, 18)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*PURPLE)
        pdf.cell(0, 5.5, _safe(c["category"]), new_x="LMARGIN", new_y="NEXT")
        if not c["rows"]:
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(0, 4.6, "Neither parent has filled this in yet.", new_x="LMARGIN", new_y="NEXT")
        for r in c["rows"]:
            _room(pdf, 16)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*INK)
            pdf.multi_cell(0, 4.6, _safe(r["label"]), new_x="LMARGIN", new_y="NEXT")
            for name, value in ((names[0], r["mine"]), (names[1], r["theirs"])):
                pdf.set_x(pdf.l_margin + 3)
                pdf.set_font("Helvetica", "", 8.5)
                pdf.set_text_color(*(INK if value else MUTED))
                pdf.multi_cell(pdf.epw - 3, 4.3, _safe(f"{name}: {value or 'Not filled in'}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)


def build_compare_pdf(data: Dict[str, Any]) -> bytes:
    pdf = _ComparePDF(format="Letter")
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    _header(pdf, data)
    names = tuple(data["names"])
    points = {p["area"]: p["text"] for p in data.get("talking_points") or []}
    _section(pdf, "Areas of Alignment", "Where both parents' own ratings match: good starting points for agreement.")
    if data["alignment"]:
        _score_table(pdf, data["alignment"], names, EMERALD, {})
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, "No matching areas yet.", new_x="LMARGIN", new_y="NEXT")
    _section(pdf, "Areas of Difference", "Where the two parents rated things differently, with a calm opener to start talking.")
    if data["difference"]:
        _score_table(pdf, data["difference"], names, AMBER, points)
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, "No differing areas. Both parents' ratings line up.", new_x="LMARGIN", new_y="NEXT")
    _section(pdf, "Child-Focused Needs", "What each parent recorded about the child's needs, side by side.")
    if data["child"]:
        _child(pdf, data["child"], names)
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, "Appears once both parents fill in Child Needs.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
