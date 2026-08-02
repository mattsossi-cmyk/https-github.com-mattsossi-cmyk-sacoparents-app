"""Branded PDF renderer for the 9-section Special Needs Co-Parenting v2 report."""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable

from fpdf import FPDF


LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")
ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"


STATUS_COLORS = {
    "Strength":                          (31, 92, 59),
    "Developing":                        (61, 26, 120),
    "Needs Attention":                   (140, 90, 44),
    "Priority Concern":                  (176, 42, 42),
    "Professional Guidance Recommended": (61, 26, 120),
}


def _safe(t: Any) -> str:
    if t is None: return ""
    s = str(t)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _PDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(14, 24, 14)
        self.alias_nb_pages()
        self.compress = False

    def header(self):
        # Subtle diagonal "REVIEW BEFORE SHARING" watermark behind content.
        from pdf_watermark import stamp_watermark
        stamp_watermark(self)
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 18, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=11, y=3, w=12, h=12)
            except Exception:
                pass
        self.set_xy(26, 4)
        self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe(f"{ORG_NAME}  ·  Special Needs Co-Parenting Report"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe(ORG_TAGLINE), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe(f"Individual Parent Report  ·  Page {self.page_no()} of {{nb}}"), align="C")

    def h1(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 17); self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 7.5, _safe(t)); self.ln(0.5)
    def h2(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 11.5); self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 5.8, _safe(t)); self.ln(0.2)
    def h3(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 9.5); self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 4.8, _safe(t))
    def body(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "", 9.3); self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 4.4, _safe(t)); self.ln(0.2)
    def small(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "I", 8); self.set_text_color(110, 100, 130)
        self.multi_cell(self.epw, 3.8, _safe(t)); self.ln(0.2)
    def bullets(self, items: Iterable[str]):
        self.set_font("Helvetica", "", 9.3); self.set_text_color(30, 24, 54)
        w = False
        for it in items:
            s = str(it or "").strip()
            if not s: continue
            self.set_x(self.l_margin); self.multi_cell(self.epw, 4.4, _safe(f"  -  {s}"))
            w = True
        if not w:
            self.set_x(self.l_margin); self.multi_cell(self.epw, 4.4, "  -  None recorded.")
        self.ln(0.2)
    def status_pill(self, status: str):
        color = STATUS_COLORS.get(status, (110, 100, 130))
        self.set_font("Helvetica", "B", 8.5); self.set_text_color(*color)
        self.set_x(self.l_margin); self.multi_cell(self.epw, 4.4, _safe(f"Status: {status}"))
        self.set_text_color(30, 24, 54); self.ln(0.2)


def _render_cover(pdf: _PDF, report: Dict[str, Any]) -> None:
    pdf.add_page(); pdf.ln(4)
    intro = report.get("intro") or {}
    pdf.h1(intro.get("title") or "Your Special Needs Co-Parenting Report")
    cover = report.get("cover") or {}
    for label, key in [("Parent completing assessment", "parent_name"),
                       ("Child", "child_name"),
                       ("Assessment date", "assessment_date")]:
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(30, 24, 54)
        pdf.multi_cell(pdf.epw, 5.5, _safe(label))
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(pdf.epw, 5.5, _safe(cover.get(key) or "-")); pdf.ln(0.3)
    pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(pdf.epw, 5.5, _safe("Needs categories addressed"))
    pdf.bullets([p["name"] for p in (cover.get("selected_pathways") or [])])
    pdf.ln(2)
    pdf.body(intro.get("body") or "")


def _section_break(pdf: _PDF) -> None:
    """Small visual break between sections so we don't force a new page each time."""
    pdf.ln(2)
    pdf.set_draw_color(220, 214, 232); pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _render_family_situation(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("2. Your Family Situation")
    pdf.body(f"Child: {s.get('child_name') or '-'}")
    pdf.h3("Identified needs")
    for block in s.get("identified_needs_by_pathway") or []:
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 4.4, _safe(block.get("name")))
        pdf.bullets(block.get("needs") or [])
    pdf.h3("Professionals currently involved")
    pdf.bullets(s.get("professionals_involved") or [])
    pdf.h3("Primary concerns you reported")
    pdf.bullets(s.get("primary_concerns") or [])
    pdf.h3("Decisions that need to be made")
    pdf.bullets(s.get("decisions_needed") or [])
    pdf.h3("Areas of agreement")
    pdf.bullets(s.get("agreements") or [])
    pdf.h3("Areas of disagreement")
    pdf.bullets(s.get("disagreements") or [])
    _section_break(pdf)


def _render_areas_of_need(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("3. Areas of Need")
    for b in s.get("blocks") or []:
        pdf.h3(b.get("name") or b.get("id"))
        if b.get("concern"):
            pdf.body(f"Concern as described: {b['concern']}")
        meta = []
        if b.get("duration"): meta.append(f"Duration: {b['duration']}")
        if b.get("urgency"): meta.append(f"Urgency: {b['urgency']}")
        if meta: pdf.small(" · ".join(meta))
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 4.4, _safe("Current needs"))
        pdf.bullets(b.get("current_needs") or [])
        if b.get("professional_summary"):
            pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
            pdf.multi_cell(pdf.epw, 4.4, _safe("Professional recommendation summary"))
            pdf.body(b["professional_summary"])
    _section_break(pdf)


def _render_strengths(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("4. Your Co-Parenting Strengths")
    pdf.small("What is already helping your child today.")
    pdf.bullets(s.get("items") or [])
    _section_break(pdf)


def _render_challenges(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("5. Co-Parenting Challenges")
    items = s.get("items") or []
    if not items:
        pdf.body("Your responses do not surface any pathway-level challenges above the concern threshold.")
        _section_break(pdf); return
    for c in items:
        pdf.h3(f"{c['pathway_name']}: {c['title']}")
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 4.4, _safe("What you reported"))
        pdf.body(c.get("reported") or "")
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 4.4, _safe("Why this may matter to your child"))
        pdf.body(c.get("why_it_matters") or "")
        pdf.status_pill(c.get("concern_level") or "Needs Attention")
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 4.4, _safe("Options to consider"))
        pdf.bullets(c.get("options") or [])
    _section_break(pdf)


def _render_child_impact(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("6. Child Impact Summary")
    pdf.small("Possible effects of the current pattern - not assigning blame.")
    pdf.bullets(s.get("possible_effects") or [])
    _section_break(pdf)


def _render_detailed_findings(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("7. Detailed Findings by Category")
    for row in s.get("categories") or []:
        pdf.h3(row.get("name"))
        pdf.status_pill(row.get("status") or "Developing")
        pdf.body(row.get("explanation") or "")
        if row.get("strengths"):
            pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
            pdf.multi_cell(pdf.epw, 4.4, _safe("Existing strengths")); pdf.bullets(row["strengths"])
        if row.get("concerns"):
            pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
            pdf.multi_cell(pdf.epw, 4.4, _safe("Specific concerns")); pdf.bullets(row["concerns"])
        if row.get("actions"):
            pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
            pdf.multi_cell(pdf.epw, 4.4, _safe("Recommended parent actions")); pdf.bullets(row["actions"])
        if row.get("resources"):
            pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(61, 26, 120)
            pdf.multi_cell(pdf.epw, 4.4, _safe("Professional resources to consider")); pdf.bullets(row["resources"])
    _section_break(pdf)


def _render_parent_alignment(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("8. Parent Alignment Summary")
    pdf.bullets(s.get("resolved_labels") or [])
    pdf.small(s.get("note") or "")
    _section_break(pdf)


def _render_recommended_structure(pdf: _PDF, s: Dict[str, Any]) -> None:
    pdf.h2("9. Recommended Co-Parenting Structure")
    pdf.h3(s.get("structure_name") or "-")
    pdf.body(s.get("rationale") or "")
    pdf.h3("Safeguards to consider")
    pdf.bullets(s.get("safeguards") or [])
    pdf.small(s.get("safety_notice") or "")


def build_snc2_pdf(*, report: Dict[str, Any]) -> bytes:
    pdf = _PDF()
    _render_cover(pdf, report)
    _render_family_situation(pdf, report.get("family_situation") or {})
    _render_areas_of_need(pdf, report.get("areas_of_need") or {})
    _render_strengths(pdf, report.get("strengths") or {})
    _render_challenges(pdf, report.get("challenges") or {})
    _render_child_impact(pdf, report.get("child_impact") or {})
    _render_detailed_findings(pdf, report.get("detailed_findings") or {})
    _render_parent_alignment(pdf, report.get("parent_alignment") or {})
    _render_recommended_structure(pdf, report.get("recommended_structure") or {})
    # "How this report was built" — provenance for the recipient.
    from pdf_provenance import render_provenance_footer
    render_provenance_footer(pdf, variant="snc")
    pdf.ln(2); pdf.small(report.get("disclaimer") or "")
    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
