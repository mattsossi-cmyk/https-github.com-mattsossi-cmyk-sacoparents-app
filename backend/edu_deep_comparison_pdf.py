"""Branded neutral Educational Deep Dive comparison PDF renderer."""
from __future__ import annotations

import os
from typing import Any, Dict, List

from fpdf import FPDF


LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")
ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"

ALIGNMENT_COLORS = {
    "aligned":        (31, 92, 59),
    "both_responded": (31, 92, 59),
    "close":          (61, 26, 120),
    "one_only":       (140, 90, 44),
    "divergent":      (176, 42, 42),
    "insufficient":   (133, 126, 156),
}


def _safe(t: Any) -> str:
    if t is None:
        return ""
    s = str(t)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _PDF(FPDF):
    def __init__(self, header_subtitle: str = "Educational Deep Dive Co-Parent Comparison"):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 30, 15)
        self.alias_nb_pages()
        self.compress = False
        self._header_subtitle = header_subtitle

    def header(self):
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=4, w=14, h=14)
            except Exception:
                pass
        self.set_xy(30, 5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(61, 26, 120)
        self.cell(0, 5, _safe(f"{ORG_NAME}  ·  {self._header_subtitle}"), ln=1)
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
        self.cell(0, 4, _safe(f"Neutral Co-Parent Comparison  ·  Page {self.page_no()} of {{nb}}"), align="C")

    def h1(self, t: str):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 9, _safe(t))
        self.ln(1)

    def h2(self, t: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 6, _safe(t))
        self.ln(1)

    def para(self, t: str, size: int = 10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(50, 40, 80)
        self.multi_cell(self.epw, 5, _safe(t))
        self.ln(1)

    def alignment_pill(self, alignment: str, label: str):
        color = ALIGNMENT_COLORS.get(alignment, (133, 126, 156))
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        w = self.get_string_width(_safe(label)) + 6
        self.cell(w, 5, _safe(label), fill=True, align="C")
        self.set_text_color(30, 24, 54)


def _render_item(pdf: _PDF, item: Dict[str, Any], labels: Dict[str, str],
                 parent_a: str, parent_b: str) -> None:
    align = item.get("alignment", "insufficient")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 5, _safe(item.get("prompt") or ""))
    pdf.alignment_pill(align, labels.get(align, align))
    pdf.ln(4)

    a = (item.get("parent_a") or {}).get("value")
    b = (item.get("parent_b") or {}).get("value")

    def _fmt(v: Any) -> str:
        if v is None or v == "":
            return "(no response)"
        if isinstance(v, list):
            return ", ".join(str(x) for x in v) if v else "(no response)"
        return str(v)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(pdf.epw / 2, 5, _safe(parent_a), ln=0)
    pdf.cell(pdf.epw / 2, 5, _safe(parent_b), ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 40, 80)
    x_left = pdf.get_x()
    y_start = pdf.get_y()
    pdf.multi_cell(pdf.epw / 2 - 2, 4.5, _safe(_fmt(a)))
    y_after_a = pdf.get_y()
    pdf.set_xy(x_left + pdf.epw / 2, y_start)
    pdf.multi_cell(pdf.epw / 2 - 2, 4.5, _safe(_fmt(b)))
    y_after_b = pdf.get_y()
    pdf.set_y(max(y_after_a, y_after_b) + 2)


def build_comparison_pdf(*, comparison: Dict[str, Any], safety_notice: str,
                         product_title: str = "Educational Deep Dive Comparison",
                         header_subtitle: str = "Educational Deep Dive Co-Parent Comparison") -> bytes:
    pdf = _PDF(header_subtitle=header_subtitle)
    pdf.add_page()

    parent_a = comparison.get("parent_a_name") or "Parent A"
    parent_b = comparison.get("parent_b_name") or "Parent B"
    labels = comparison.get("alignment_labels") or {}

    pdf.h1(product_title)
    pdf.para(f"A neutral side-by-side look at how {parent_a} and {parent_b} answered this "
             "deep dive. This document does not favour either parent. Use it as a starting "
             "point for a conversation with a mediator, teacher, or family professional.")

    summary = comparison.get("summary") or {}
    pdf.h2("At a glance")
    pdf.para(
        f"Total items compared: {summary.get('total_items', 0)}  ·  "
        f"Aligned: {summary.get('aligned_pct', 0)}%  ·  "
        f"Different views: {summary.get('divergent_pct', 0)}%"
    )

    highlights: List[Dict[str, Any]] = comparison.get("highlights") or []
    if highlights:
        pdf.ln(2)
        pdf.h2("5 things you already agree on")
        for h in highlights[:5]:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 24, 54)
            pdf.multi_cell(pdf.epw, 5, _safe(
                f"Section {h.get('section_number')}. {h.get('section_name', '')}"
            ))
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(60, 50, 90)
            pdf.multi_cell(pdf.epw, 4.5, _safe(h.get("prompt") or ""))
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(31, 92, 59)
            pdf.multi_cell(pdf.epw, 4.5, _safe(h.get("summary") or ""))
            pdf.ln(1.5)

    def _mediation_list(title: str, rows: List[Dict[str, Any]], color: tuple,
                        intro: str, render_extra=None):
        if not rows:
            return
        pdf.ln(2)
        pdf.h2(title)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(110, 100, 130)
        pdf.multi_cell(pdf.epw, 4.5, _safe(intro))
        pdf.ln(1)
        for r in rows:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*color)
            pdf.multi_cell(pdf.epw, 4.5, _safe(f"Section {r.get('section_number')}. {r.get('section_name', '')}"))
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(30, 24, 54)
            pdf.multi_cell(pdf.epw, 4.5, _safe(r.get("prompt") or r.get("question") or ""))
            if render_extra:
                render_extra(r)
            pdf.ln(1)

    _mediation_list("Shared Priorities", comparison.get("shared_priorities") or [], (31, 92, 59),
                    "What both parents already flagged as important.",
                    render_extra=lambda r: (pdf.set_font("Helvetica", "I", 8.5),
                                            pdf.set_text_color(31, 92, 59),
                                            pdf.multi_cell(pdf.epw, 4, _safe(r.get("reason") or ""))))
    _mediation_list("Points for Discussion", comparison.get("discussion_points") or [], (61, 26, 120),
                    "Close-but-not-identical items to sync on together.",
                    render_extra=lambda r: (pdf.set_font("Helvetica", "I", 8.5),
                                            pdf.set_text_color(61, 26, 120),
                                            pdf.multi_cell(pdf.epw, 4, _safe(r.get("reason") or ""))))
    _mediation_list("Questions for Mediation", comparison.get("mediation_questions") or [], (140, 90, 44),
                    "Divergent items, neutralized as questions. Neither parent is labelled right or wrong.")

    for sec in comparison.get("sections") or []:
        pdf.ln(2)
        pdf.h2(f"Section {sec.get('number')}. {sec.get('name', '')}")
        if sec.get("purpose"):
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(110, 100, 130)
            pdf.multi_cell(pdf.epw, 4.5, _safe(sec["purpose"]))
            pdf.ln(1)
        for item in sec.get("items") or []:
            _render_item(pdf, item, labels, parent_a, parent_b)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(110, 100, 130)
    pdf.multi_cell(pdf.epw, 4, _safe(safety_notice))

    # "How this report was built" — provenance for the recipient.
    from pdf_provenance import render_provenance_footer
    render_provenance_footer(pdf, variant="comparison")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1", errors="replace")
    return bytes(out)
