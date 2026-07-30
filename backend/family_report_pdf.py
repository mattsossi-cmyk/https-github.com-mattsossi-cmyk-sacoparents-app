"""PDF renderer for the SA CoParents Family Report.

Renders the FULL Co-Parenting and Special Needs reports in-line (strengths,
priority focus, communication toolkit, section-by-section detail, next steps),
plus the Safety pathway summary. Visual language matches cp_report_pdf.py and
sn_v3_report_pdf.py exactly so all three reports feel like one product family.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from fpdf import FPDF


_OVERALL_COLOR = {
    "Excellent Progress": (31, 92, 59),
    "Building Progress":  (61, 26, 120),
    "Early Progress":     (194, 72, 31),
}

_SECTION_COLOR = {
    "Excellent":         (31, 92, 59),
    "Good":              (61, 26, 120),
    "Fair":              (140, 90, 44),
    "Needs Improvement": (194, 72, 31),
}

_SAFETY_LEVEL_COLOR = {
    1: (194, 72, 31),
    2: (140, 90, 44),
    3: (61, 26, 120),
    4: (31, 92, 59),
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


class _FamilyReportPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 18, 15)
        self.alias_nb_pages()

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(61, 26, 120)
        self.cell(0, 6, "SA CoParents  ·  Family Report", ln=1)
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

    def h2(self, text: str, color=(61, 26, 120)):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*color)
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


def _render_safety(pdf: _FamilyReportPDF, safety: Dict[str, Any]) -> None:
    pdf.h2("Communication Safety")
    color = _SAFETY_LEVEL_COLOR.get(safety.get("level"), (61, 26, 120))
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*color)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 6, _safe(f"Level {safety['level']}: {safety.get('pathway_title')}"))
    if safety.get("pathway_headline"):
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(133, 126, 156)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5, _safe(safety["pathway_headline"]))
    if safety.get("pathway_summary"):
        pdf.body(safety["pathway_summary"])
    if safety.get("recommendations"):
        pdf.h3("Recommendations")
        pdf.bullets(safety["recommendations"])
    pdf.ln(1)


def _render_full_report(pdf: _FamilyReportPDF, block: Dict[str, Any], *, section_title: str, principle_prefix: str) -> None:
    """Render a full CP or SN v3 report block (strengths + priority focus +
    toolkit + all 10 sections + next steps)."""
    r = block.get("report") or {}
    pdf.h2(section_title)

    # Overall
    overall = r.get("overall_rating") or "Not enough data"
    color = _OVERALL_COLOR.get(overall, (61, 26, 120))
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*color)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 6, _safe(f"Overall: {overall}"))
    if r.get("overall_summary"):
        pdf.body(r["overall_summary"])

    # Strengths
    strengths = r.get("strengths") or []
    if strengths:
        pdf.h3("Strengths", color=(31, 92, 59))
        for s in strengths:
            title = _safe(s.get("title") or "")
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(31, 92, 59)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5.5, f"- {title}")
            if s.get("detail"):
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(52, 46, 78)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5, f"    {_safe(s['detail'])}")

    # Priority focus / growth areas
    growth = r.get("growth_areas") or []
    if growth:
        pdf.h3("Priority focus", color=(194, 72, 31))
        for g in growth:
            title = _safe(g.get("title") or "")
            rating = _safe(g.get("rating") or "")
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(194, 72, 31)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5.5, f"- {title}  ({rating})")
            if g.get("why_it_matters"):
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(52, 46, 78)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5, f"    Why it matters: {_safe(g['why_it_matters'])}")
            if g.get("first_step"):
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(52, 46, 78)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5, f"    First step: {_safe(g['first_step'])}")

    # Communication toolkit (only when the source triggered it)
    toolkit = r.get("communication_toolkit") or []
    if toolkit and r.get("show_communication_toolkit"):
        pdf.h3("Communication toolkit", color=(61, 26, 120))
        for tip in toolkit:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(61, 26, 120)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5.5, f"- {_safe(tip.get('title') or '')}")
            if tip.get("detail"):
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(52, 46, 78)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 5, f"    {_safe(tip['detail'])}")

    # Section-by-section detail
    sections = r.get("sections") or []
    if sections:
        pdf.h3(f"{principle_prefix}-by-{principle_prefix.lower()} detail")
        for sec in sections:
            title = _safe(f"{principle_prefix} {sec.get('number')}: {sec.get('name')}")
            rating = sec.get("rating") or "Not answered"
            rating_color = _SECTION_COLOR.get(rating, (133, 126, 156))
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(26, 19, 48)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5.5, title)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*rating_color)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 5, _safe(f"Rating: {rating}"), ln=1)
            if sec.get("goal"):
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(133, 126, 156)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(pdf.epw, 4.5, _safe(sec["goal"]))
            findings = sec.get("findings") or []
            recs = sec.get("recommendations") or []
            if findings:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(61, 26, 120)
                pdf.set_x(pdf.l_margin)
                pdf.cell(0, 5, "Findings", ln=1)
                pdf.bullets(findings)
            if recs:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(61, 26, 120)
                pdf.set_x(pdf.l_margin)
                pdf.cell(0, 5, "Recommendations", ln=1)
                pdf.bullets(recs)
            pdf.ln(0.5)

    # Next steps for this source
    next_steps = r.get("next_steps") or []
    if next_steps:
        pdf.h3("Recommended next steps")
        pdf.bullets(next_steps)

    pdf.ln(1)


def build_family_pdf(*, user_name: str, report: Dict[str, Any]) -> bytes:
    pdf = _FamilyReportPDF()
    pdf.add_page()

    pdf.h1("Your Family Report")
    prepared_by = (report.get("prepared_by") or user_name or "").strip()
    if prepared_by:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(133, 126, 156)
        pdf.set_x(pdf.l_margin)
        included = ", ".join(report.get("included_sources") or []) or "No completed sources"
        pdf.multi_cell(pdf.epw, 5, _safe(f"Prepared for {prepared_by}  ·  Includes: {included}"))
        pdf.ln(2)

    if report.get("overall_summary"):
        pdf.body(report["overall_summary"])

    missing = report.get("missing_sources") or []
    if missing:
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.set_text_color(140, 90, 44)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5, _safe("Not yet completed: " + ", ".join(missing)))
        pdf.ln(1)

    if report.get("safety"):
        _render_safety(pdf, report["safety"])

    if report.get("coparenting"):
        _render_full_report(pdf, report["coparenting"],
                            section_title="Co-Parenting Assessment",
                            principle_prefix="Section")

    # Combined next steps at end
    combined = report.get("combined_next_steps") or []
    if combined:
        pdf.h2("Combined next steps across your assessments")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.set_text_color(52, 46, 78)
        for step in combined:
            source = _safe(step.get("source") or "")
            text = _safe(step.get("text") or "")
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5.4, f"  - [{source}] {text}")
        pdf.ln(1)

    pdf.ln(2)
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
