"""PDF renderer for the Special Needs Co-Parenting **neutral comparison**.

Consumes the payload returned by ``snc_comparison.compare_reports()`` and
writes an FPDF side-by-side that follows the same SA CoParents branded
aesthetic as the individual parent report.

Design guardrails (also enforced by the caller in ``snc_comparison.py``):
  * Section 11 (Family Violence & Communication Safety) never appears.
  * Verbatim narrative/open-text responses never appear.
  * Neither parent is labelled correct, incorrect, or a "winner".
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from fpdf import FPDF


LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")
ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"


BUCKET_TITLES = {
    "agreement":               "Where you agree",
    "different_observations":  "Where you see it differently",
    "missing_information":     "Where more information would help",
}
BUCKET_ORDER = ["agreement", "different_observations", "missing_information"]


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


class _SNCComparisonPDF(FPDF):
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
        self.cell(0, 5, _safe(f"{ORG_NAME}  ·  Special Needs Co-Parenting Comparison"), ln=1)
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
        self.cell(0, 4, _safe(f"Neutral Side-by-Side  ·  Page {self.page_no()} of {{nb}}"),
                  align="C")

    # ----- typographic helpers ---------------------------------------
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

    def body(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 5.2, _safe(text))
        self.ln(0.5)

    def small(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8.5)
        self.set_text_color(110, 100, 130)
        self.multi_cell(self.epw, 4.5, _safe(text))
        self.ln(0.5)

    def bullets(self, items: Iterable[str]):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 24, 54)
        wrote = False
        for it in items:
            if not str(it).strip():
                continue
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 5.2, _safe(f"  -  {it}"))
            wrote = True
        if not wrote:
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 5.2, "  -  None recorded.")
        self.ln(0.5)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _fmt_score(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, (int, float)):
        return f"{v:.2f}"
    return str(v)


def _render_cover(pdf: _SNCComparisonPDF, cmp: Dict[str, Any]) -> None:
    pdf.add_page()
    pdf.ln(4)
    pdf.h1("Special Needs Co-Parenting")
    pdf.h1("Neutral Side-by-Side")

    parents = cmp.get("parents") or {}
    a = (parents.get("a") or {}).get("name") or "Parent A"
    b = (parents.get("b") or {}).get("name") or "Parent B"
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 6, _safe(f"Comparing: {a}  vs.  {b}"))
    pdf.ln(0.5)

    generated_at = cmp.get("generated_at")
    if generated_at:
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(110, 100, 130)
        pdf.multi_cell(pdf.epw, 5, _safe(f"Generated: {generated_at}"))

    pdf.ln(3)
    pdf.h2("Purpose")
    pdf.body(
        "This document places each parent's own Special Needs Co-Parenting "
        "report side-by-side. It never names one parent as right or wrong, "
        "does not diagnose the child, and does not determine parental fitness."
    )
    pdf.ln(1)

    pdf.h2("Safety notice")
    pdf.small(cmp.get("safety_notice") or "")


def _render_counts(pdf: _SNCComparisonPDF, cmp: Dict[str, Any]) -> None:
    pdf.add_page()
    pdf.h2("At a glance")
    counts = cmp.get("counts") or {}
    lines = [
        ("Categories compared",       counts.get("total_categories", 0)),
        ("Where you agree",           counts.get("agreement", 0)),
        ("Where you see it differently", counts.get("different_observations", 0)),
        ("Where more information would help", counts.get("missing_information", 0)),
    ]
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 24, 54)
    for label, value in lines:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(pdf.epw, 5.5, _safe(f"{label}: {value}"))
    pdf.ln(2)


def _render_category_bucket(
    pdf: _SNCComparisonPDF, cmp: Dict[str, Any], bucket_key: str,
) -> None:
    ids = ((cmp.get("buckets") or {}).get(bucket_key)) or []
    categories = cmp.get("categories") or []
    by_id = {c.get("id"): c for c in categories}
    parents = cmp.get("parents") or {}
    a = (parents.get("a") or {}).get("name") or "Parent A"
    b = (parents.get("b") or {}).get("name") or "Parent B"

    pdf.h2(BUCKET_TITLES.get(bucket_key, bucket_key.replace("_", " ").title()))
    if not ids:
        pdf.body("None in this bucket.")
        return
    for cid in ids:
        row = by_id.get(cid)
        if not row:
            continue
        pdf.h3(row.get("name") or cid)
        pdf.body(row.get("note") or "")

        a_side = row.get("a") or {}
        b_side = row.get("b") or {}
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(61, 26, 120)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5.2, _safe(a))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 24, 54)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5.2, _safe(
            f"  {a_side.get('classification', 'Not enough data')}  ·  Score {_fmt_score(a_side.get('score'))}"
        ))
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(61, 26, 120)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5.2, _safe(b))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 24, 54)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5.2, _safe(
            f"  {b_side.get('classification', 'Not enough data')}  ·  Score {_fmt_score(b_side.get('score'))}"
        ))
        pdf.ln(1)


def _render_professional_questions(pdf: _SNCComparisonPDF, cmp: Dict[str, Any]) -> None:
    pdf.h2("Professional questions to explore")
    pdf.small(
        "These are questions raised by either parent's report. They are worth "
        "bringing to a treating professional, mediator, or Parenting Facilitator."
    )
    pdf.bullets(((cmp.get("buckets") or {}).get("professional_questions")) or [])


def _render_coordination_areas(pdf: _SNCComparisonPDF, cmp: Dict[str, Any]) -> None:
    pdf.h2("Practical coordination areas")
    pdf.small(
        "Concrete opportunities to align routines, communication, and support "
        "across both homes."
    )
    pdf.bullets(((cmp.get("buckets") or {}).get("coordination_areas")) or [])


def _render_disclaimer(pdf: _SNCComparisonPDF, cmp: Dict[str, Any]) -> None:
    pdf.ln(2)
    pdf.small(cmp.get("disclaimer") or "")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_snc_comparison_pdf(*, comparison: Dict[str, Any]) -> bytes:
    """Render the neutral side-by-side to PDF bytes."""
    pdf = _SNCComparisonPDF()
    _render_cover(pdf, comparison)
    _render_counts(pdf, comparison)
    for bucket_key in BUCKET_ORDER:
        _render_category_bucket(pdf, comparison, bucket_key)
    _render_professional_questions(pdf, comparison)
    _render_coordination_areas(pdf, comparison)
    _render_disclaimer(pdf, comparison)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
