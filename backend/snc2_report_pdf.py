"""Branded PDF renderer for the Special Needs Co-Parenting v2 report."""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from fpdf import FPDF


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


class _SNC2PDF(FPDF):
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
        self.cell(0, 5, _safe(f"{ORG_NAME}  ·  Special Needs Co-Parenting Report"), ln=1)
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
        self.cell(0, 4, _safe(f"Individual Parent Report  ·  Page {self.page_no()} of {{nb}}"), align="C")

    def h1(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 20); self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 9, _safe(t)); self.ln(1)

    def h2(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 13); self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 7, _safe(t)); self.ln(0.5)

    def h3(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 5.5, _safe(t))

    def body(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "", 10); self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 5.2, _safe(t)); self.ln(0.5)

    def small(self, t):
        self.set_x(self.l_margin); self.set_font("Helvetica", "I", 8.5); self.set_text_color(110, 100, 130)
        self.multi_cell(self.epw, 4.5, _safe(t)); self.ln(0.5)

    def bullets(self, items: Iterable[str]):
        self.set_font("Helvetica", "", 10); self.set_text_color(30, 24, 54)
        wrote = False
        for it in items:
            s = str(it or "").strip()
            if not s: continue
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 5.2, _safe(f"  -  {s}"))
            wrote = True
        if not wrote:
            self.set_x(self.l_margin); self.multi_cell(self.epw, 5.2, "  -  None recorded.")
        self.ln(0.5)


def _fmt_score(v: Any) -> str:
    if v is None: return "-"
    if isinstance(v, (int, float)): return f"{v:.2f}"
    return str(v)


def _render_cover(pdf: _SNC2PDF, report: Dict[str, Any]) -> None:
    cover = report.get("cover") or {}
    pdf.add_page(); pdf.ln(4)
    pdf.h1("Special Needs Co-Parenting")
    pdf.h1("Individual Parent Report")
    pdf.ln(1)

    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(30, 24, 54)
    for label, value in [
        ("Parent completing assessment", cover.get("parent_name") or "-"),
        ("Child",                        cover.get("child_name") or "-"),
        ("Assessment date",              cover.get("assessment_date") or "-"),
        ("Assessment version",           report.get("assessment_version") or "-"),
    ]:
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(pdf.epw, 5.5, _safe(label))
        pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(pdf.epw, 5.5, _safe(value)); pdf.ln(0.5)

    pdf.set_x(pdf.l_margin); pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(pdf.epw, 5.5, _safe("Needs categories addressed"))
    pdf.bullets([p["name"] for p in (cover.get("selected_pathways") or [])])

    pdf.ln(3)
    pdf.h2("Purpose")
    pdf.body(report.get("purpose") or "")


def _render_at_a_glance(pdf: _SNC2PDF, report: Dict[str, Any]) -> None:
    pdf.add_page()
    pdf.h2("At a glance")
    ag = report.get("at_a_glance") or {}
    for label, key in [
        ("Concerns as described by this parent", "concerns_by_pathway"),
        ("Top 30-day priorities",                 "top_priorities"),
        ("Pathways where coordination is working","coordination_wins"),
        ("Pathways where coordination needs work","coordination_gaps"),
    ]:
        pdf.h3(label); pdf.bullets(ag.get(key) or [])


def _render_pathway_summaries(pdf: _SNC2PDF, report: Dict[str, Any]) -> None:
    pdf.h2("Pathway scores")
    for s in report.get("pathway_summaries") or []:
        u = s.get("understanding") or {}
        c = s.get("coordination") or {}
        i = s.get("impact") or {}
        pdf.h3(s.get("name") or s.get("id"))
        pdf.body(
            f"Reported impact: {i.get('classification') or '-'}  ({_fmt_score(i.get('score'))} of 5).  "
            f"Understanding across parents: {u.get('classification') or '-'} ({_fmt_score(u.get('score'))} of 5).  "
            f"Coordination between homes: {c.get('classification') or '-'} ({_fmt_score(c.get('score'))} of 5)."
        )
    pdf.small("Scores reflect the reporting parent's answers and are never findings of fact.")


def _render_step_block(pdf: _SNC2PDF, step: Dict[str, Any]) -> None:
    pdf.add_page()
    pdf.h2(f"Step {step['number']}. {step['name']}")
    for pw in step.get("pathways") or []:
        pdf.h3(pw.get("name") or pw.get("id"))
        for label, key in [
            ("Response",     "response"),
            ("Finding",      "finding"),
            ("Child impact", "child_impact"),
            ("Suggested",    "suggested"),
            ("Action step",  "action"),
        ]:
            v = pw.get(key)
            if key == "response":
                # Compact list of key: value pairs.
                if not v: continue
                if isinstance(v, dict):
                    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(61, 26, 120)
                    pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 5.2, _safe(label))
                    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
                    for kk, vv in v.items():
                        display = ", ".join(vv) if isinstance(vv, list) else str(vv)
                        pdf.set_x(pdf.l_margin)
                        pdf.multi_cell(pdf.epw, 5.2, _safe(f"  {kk.replace('_', ' ')}: {display}"))
                    pdf.ln(0.5)
                continue
            if not v: continue
            pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(61, 26, 120)
            pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 5.2, _safe(label))
            pdf.set_font("Helvetica", "", 10); pdf.set_text_color(30, 24, 54)
            pdf.set_x(pdf.l_margin); pdf.multi_cell(pdf.epw, 5.2, _safe(str(v)))
            pdf.ln(0.5)


def build_snc2_pdf(*, report: Dict[str, Any]) -> bytes:
    pdf = _SNC2PDF()
    _render_cover(pdf, report)
    _render_at_a_glance(pdf, report)
    _render_pathway_summaries(pdf, report)
    for step in report.get("steps") or []:
        _render_step_block(pdf, step)
    pdf.ln(2)
    pdf.small(report.get("disclaimer") or "")
    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
