"""Branded neutral SNC v2 co-parent comparison PDF renderer."""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

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
            except Exception:
                pass
        self.set_xy(30, 5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(61, 26, 120)
        self.cell(0, 5, _safe(f"{ORG_NAME}  ·  Special Needs Co-Parent Comparison"), ln=1)
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
        self.cell(0, 4, _safe(
            f"Neutral Co-Parent Comparison  ·  Page {self.page_no()} of {{nb}}"
        ), align="C")

    def h1(self, t):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(26, 19, 48)
        self.multi_cell(self.epw, 9, _safe(t))
        self.ln(1)

    def h2(self, t):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 7, _safe(t))
        self.ln(0.5)

    def h3(self, t):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(61, 26, 120)
        self.multi_cell(self.epw, 5.5, _safe(t))

    def body(self, t):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 24, 54)
        self.multi_cell(self.epw, 5.2, _safe(t))
        self.ln(0.5)

    def small(self, t):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8.5)
        self.set_text_color(110, 100, 130)
        self.multi_cell(self.epw, 4.5, _safe(t))
        self.ln(0.5)

    def pill(self, text: str, key: str):
        color = ALIGNMENT_COLORS.get(key, (110, 100, 130))
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*color)
        self.cell(self.get_string_width(_safe(text)) + 6, 5,
                  _safe(text), border=1, align="C")
        self.ln(6)
        self.set_text_color(30, 24, 54)

    def two_col(self, label_a: str, val_a: str, label_b: str, val_b: str):
        col_w = (self.epw - 4) / 2
        y = self.get_y()
        # column A
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(61, 26, 120)
        self.set_xy(self.l_margin, y)
        self.multi_cell(col_w, 4.6, _safe(label_a))
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 24, 54)
        self.set_x(self.l_margin)
        self.multi_cell(col_w, 4.6, _safe(val_a or "-"))
        end_a = self.get_y()
        # column B
        self.set_xy(self.l_margin + col_w + 4, y)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(61, 26, 120)
        self.multi_cell(col_w, 4.6, _safe(label_b))
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 24, 54)
        self.set_x(self.l_margin + col_w + 4)
        self.multi_cell(col_w, 4.6, _safe(val_b or "-"))
        end_b = self.get_y()
        self.set_y(max(end_a, end_b) + 1)


def _value_text(item: Dict[str, Any], side: str) -> str:
    v = (item.get(side) or {}).get("value")
    t = item.get("type")
    if t == "likert":
        label = (item.get(side) or {}).get("label")
        if isinstance(v, int):
            return f"{v} - {label or ''}".strip(" -")
        if v == "na":
            return "Not applicable or unknown"
        return "-"
    if t == "single":
        return v or "-"
    if t == "multi":
        return ", ".join(v) if isinstance(v, list) and v else "-"
    return v or "-"


def build_comparison_pdf(*, comparison: Dict[str, Any], safety_notice: str = "") -> bytes:
    pdf = _PDF()
    pdf.add_page()

    parent_a = comparison.get("parent_a_name") or "Parent A"
    parent_b = comparison.get("parent_b_name") or "Parent B"
    pdf.h1("Special Needs Co-Parent Comparison")
    pdf.body(
        f"A neutral side-by-side view of what {parent_a} and {parent_b} reported. "
        "This report does not label either parent as correct or incorrect. It "
        "highlights where you already agree and where a coordinated conversation "
        "may be helpful."
    )
    pdf.small(
        "This document is for co-parent preparation and mediation. It is not legal "
        "advice, does not determine parental fitness, and does not diagnose."
    )
    if safety_notice:
        pdf.body(safety_notice)

    summary = comparison.get("summary") or {}
    pdf.ln(1)
    pdf.h2("At a glance")
    pdf.body(
        f"{summary.get('total_items', 0)} shared questions compared. "
        f"{summary.get('aligned_pct', 0)}% aligned. "
        f"{summary.get('divergent_pct', 0)}% show different views."
    )
    shared = comparison.get("shared_pathways") or []
    if shared:
        pdf.small("Shared pathways: " + ", ".join(shared))
    only_a = comparison.get("only_parent_a_pathways") or []
    only_b = comparison.get("only_parent_b_pathways") or []
    if only_a:
        pdf.small(f"Only {parent_a} selected: " + ", ".join(only_a))
    if only_b:
        pdf.small(f"Only {parent_b} selected: " + ", ".join(only_b))
    if comparison.get("category_filter"):
        pdf.small(f"Category filter: {comparison['category_filter']}")

    labels = comparison.get("alignment_labels") or {}
    for step in comparison.get("steps") or []:
        # Skip steps with nothing to show under the current filter
        if not any(p.get("items") for p in step.get("pathways") or []):
            continue
        pdf.ln(2)
        pdf.h2(f"Step {step.get('number')}. {step.get('name')}")
        for path in step.get("pathways") or []:
            pdf.h3(path.get("name") or "")
            for item in path.get("items") or []:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(30, 24, 54)
                pdf.multi_cell(pdf.epw, 4.6, _safe(item.get("prompt") or ""))
                # Alignment pill
                key = item.get("alignment") or "insufficient"
                pdf.pill(labels.get(key, key.title()), key)
                if item.get("type") == "multi":
                    both = item.get("both") or []
                    only_a_v = item.get("only_parent_a") or []
                    only_b_v = item.get("only_parent_b") or []
                    if both:
                        pdf.body("Both parents selected: " + ", ".join(both))
                    if only_a_v:
                        pdf.body(f"Only {parent_a} selected: " + ", ".join(only_a_v))
                    if only_b_v:
                        pdf.body(f"Only {parent_b} selected: " + ", ".join(only_b_v))
                    if not (both or only_a_v or only_b_v):
                        pdf.body("Neither parent selected any option here.")
                else:
                    pdf.two_col(
                        parent_a, _value_text(item, "parent_a"),
                        parent_b, _value_text(item, "parent_b"),
                    )

    return bytes(pdf.output(dest="S"))
