"""PDF renderer for the Co-Parenting Assessment Report.

Mirrors the FPDF style used by sn_report_pdf.py so the two dynamic reports
feel like part of the same product. Structure:

  1. Cover / overall rating banner
  2. Strengths
  3. Growth areas (priority focus)
  4. Communication Toolkit  (only when triggered)
  5. Section-by-section detail (10 sections)
  6. Recommended next steps
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Iterable, List

from fpdf import FPDF


_RATING_COLOR = {
    "Excellent":         (31, 92, 59),
    "Good":              (61, 26, 120),
    "Fair":              (140, 90, 44),
    "Needs Improvement": (194, 72, 31),
}


def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _CPReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 18, 15)
        self.alias_nb_pages()

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(61, 26, 120)
        self.cell(0, 6, "SA CoParents  ·  Co-Parenting Assessment Report", ln=1)
        self.set_draw_color(220, 214, 232)
        self.line(15, 26, 195, 26)
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(133, 126, 156)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}  ·  Educational reflection tool - not legal or clinical advice.", align="C")

    def h1(self, text: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(26, 19, 48)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 8, _safe(text))
        self.ln(1)

    def h2(self, text: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(61, 26, 120)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 7, _safe(text))
        self.ln(1)

    def h3(self, text: str, color=(26, 19, 48)):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*color)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 5.5, _safe(text))

    def body(self, text: str):
        if not text:
            return
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(52, 46, 78)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 5.4, _safe(text))
        self.ln(1)

    def bullets(self, items: Iterable[str]):
        items = [i for i in (items or []) if str(i).strip()]
        if not items:
            return
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(52, 46, 78)
        for it in items:
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 5.4, f"  - {_safe(str(it).strip())}")
        self.ln(1)

    def rating_chip(self, rating: str):
        color = _RATING_COLOR.get(rating or "", (61, 26, 120))
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*color)
        self.set_x(self.l_margin)
        self.cell(0, 5.5, _safe(f"Rating: {rating or 'Not enough data'}"), ln=1)


def build_coparenting_pdf(
    *,
    user_name: str,
    report: Dict[str, Any],
    excluded_sections: set | list | None = None,
) -> bytes:
    ex = set(excluded_sections or [])
    pdf = _CPReportPDF()
    pdf.add_page()

    # Cover + overall rating banner
    pdf.h1("Your Co-Parenting Assessment Report")
    prepared_by = (report.get("prepared_by") or user_name or "").strip()
    if prepared_by:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(133, 126, 156)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5, _safe(f"Prepared for {prepared_by}"))
        pdf.ln(2)

    if "overall" not in ex:
        overall_rating = report.get("overall_rating") or "Not enough data"
        color = _RATING_COLOR.get(overall_rating, (61, 26, 120))
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*color)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 8, _safe(f"Overall rating: {overall_rating}"))
        pdf.ln(1)
        pdf.body(report.get("overall_summary") or "")

    # Strengths
    if "strengths" not in ex:
        pdf.h2("Your strengths")
        strengths = report.get("strengths") or []
        if strengths:
            for s in strengths:
                title = _safe(s.get("title") or "")
                detail = _safe(s.get("detail") or "")
                pdf.set_font("Helvetica", "B", 10.5)
                pdf.set_text_color(31, 92, 59)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5.5, f"- {title}")
                if detail:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(52, 46, 78)
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(pdf.epw, 5, f"    {detail}")
                pdf.ln(0.5)
        else:
            pdf.body("Complete more of the assessment to surface strengths.")

    # Growth areas
    if "growth_areas" not in ex:
        pdf.h2("Priority focus areas")
        growth = report.get("growth_areas") or []
        if growth:
            for g in growth:
                title = _safe(g.get("title") or "")
                rating = _safe(g.get("rating") or "")
                pdf.set_font("Helvetica", "B", 10.5)
                pdf.set_text_color(194, 72, 31)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5.5, f"- {title}  ({rating})")
                why = g.get("why_it_matters") or ""
                first = g.get("first_step") or ""
                if why:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(52, 46, 78)
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(pdf.epw, 5, f"    Why it matters: {_safe(why)}")
                if first:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(52, 46, 78)
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(pdf.epw, 5, f"    First step: {_safe(first)}")
                pdf.ln(1)
        else:
            pdf.body("No priority areas — great work.")

    # Communication toolkit
    if "communication_toolkit" not in ex and report.get("show_communication_toolkit"):
        pdf.h2("Communication toolkit")
        pdf.body(
            "Because Section 1 (Communication & Information Sharing) is currently "
            "Fair or Needs Improvement, these tools are highlighted for you."
        )
        for tip in report.get("communication_toolkit") or []:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(61, 26, 120)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5.5, f"- {_safe(tip.get('title') or '')}")
            detail = tip.get("detail") or ""
            if detail:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(52, 46, 78)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5, f"    {_safe(detail)}")
            pdf.ln(0.5)

    # Section-by-section detail
    if "sections" not in ex:
        pdf.h2("Section-by-section detail")
        for sec in report.get("sections") or []:
            title = _safe(f"{sec.get('number')}. {sec.get('name')}")
            pdf.set_font("Helvetica", "B", 11.5)
            pdf.set_text_color(26, 19, 48)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 6, title)
            pdf.rating_chip(sec.get("rating"))
            if sec.get("goal"):
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(133, 126, 156)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 4.5, _safe(sec["goal"]))
            if sec.get("findings"):
                pdf.h3("Findings")
                pdf.bullets(sec["findings"])
            if sec.get("recommendations"):
                pdf.h3("Recommendations")
                pdf.bullets(sec["recommendations"])
            pdf.ln(1.5)

    # Next steps
    if "next_steps" not in ex:
        pdf.h2("Recommended next steps")
        steps = report.get("next_steps") or []
        if steps:
            pdf.bullets(steps)
        else:
            pdf.body("Keep going — complete more of the assessment for tailored next steps.")

    # Disclaimer
    pdf.ln(3)
    pdf.set_draw_color(220, 214, 232)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(133, 126, 156)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 4.5, _safe(report.get("disclaimer") or ""))

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


def filter_cp_report(report: Dict[str, Any], excluded: Iterable[str] | None) -> Dict[str, Any]:
    """Selective visibility helper — mirrors filter_sn_report."""
    if not excluded:
        return report
    ex = set(excluded)
    out = dict(report)
    if "overall" in ex:
        out["overall_summary"] = ""
        out["overall_rating"] = out.get("overall_rating") or ""
    if "strengths" in ex:
        out["strengths"] = []
    if "growth_areas" in ex:
        out["growth_areas"] = []
    if "communication_toolkit" in ex:
        out["communication_toolkit"] = []
        out["show_communication_toolkit"] = False
    if "sections" in ex:
        out["sections"] = []
    if "next_steps" in ex:
        out["next_steps"] = []
    return out
