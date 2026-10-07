"""Branded PDF for the Self Journey Co-Parenting Self-Assessment.

Render-only: every label comes from `self_assessment_content.json` so the
PDF says exactly what the parent saw on screen.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fpdf import FPDF

try:
    from pdf_copyright import render_pdf_copyright  # type: ignore
except Exception:  # pragma: no cover
    def render_pdf_copyright(_pdf):
        return

PURPLE = (76, 40, 137)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
TIER_RGB = [(31, 122, 77), (178, 122, 24), (203, 105, 35), (176, 52, 70)]


def _safe(text: Optional[str]) -> str:
    s = "" if text is None else str(text)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _SAPDF(FPDF):
    def __init__(self, title: str, disclaimer: str):
        super().__init__(format="Letter")
        self._title = title
        self._disclaimer = disclaimer
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PURPLE)
        self.cell(0, 6, _safe(f"SA CoParents  ·  {self._title}"), new_x="LMARGIN", new_y="NEXT")
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


def _heading(pdf: _SAPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.5)


def _meta_block(pdf: _SAPDF, meta: Dict[str, Any]) -> None:
    rows = [
        ("Parent name", meta.get("parent_name")),
        ("Date", meta.get("date")),
        ("Child(ren)", meta.get("child")),
        ("Case / Reference", meta.get("case_ref")),
    ]
    pdf.set_font("Helvetica", "", 9)
    for label, value in rows:
        pdf.set_text_color(*MUTED)
        pdf.cell(35, 5, _safe(label))
        pdf.set_text_color(*INK)
        pdf.cell(0, 5, _safe(value or "-"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _overall_card(pdf: _SAPDF, content: Dict[str, Any], scores: Dict[str, Any]) -> None:
    tier = scores["tier"]
    idx = content["tiers"].index(tier) if tier else None
    rgb = TIER_RGB[idx] if idx is not None and idx < len(TIER_RGB) else MUTED
    y = pdf.get_y()
    pdf.set_fill_color(*[int(c + (255 - c) * 0.88) for c in rgb])
    pdf.set_draw_color(*[int(c + (255 - c) * 0.5) for c in rgb])
    pdf.rect(pdf.l_margin, y, pdf.epw, 20, "DF")
    pdf.set_xy(pdf.l_margin + 4, y + 2.5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*rgb)
    pdf.cell(0, 6, _safe(f"Total score: {scores['total']} / {scores['max']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "B", 9)
    pending = content["tier_pending"].format(n=scores["question_count"])
    pdf.cell(0, 5, _safe(tier["title"] if tier else pending),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    pdf.cell(0, 5, _safe(tier["body"] if tier else ""), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y + 23)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 4, _safe(f"{scores['answered']} of {scores['question_count']} questions answered"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _section_row(pdf: _SAPDF, row: Dict[str, Any]) -> None:
    y0 = pdf.get_y()
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*INK)
    pdf.cell(150, 5, _safe(f"Section {row['key']} - {row['label']}"))
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 5, _safe(f"{row['score']} / {row['max']}"), align="R", new_x="LMARGIN", new_y="NEXT")
    bar_y = pdf.get_y() + 0.5
    pdf.set_fill_color(238, 233, 242)
    pdf.rect(pdf.l_margin, bar_y, pdf.epw, 2.4, "F")
    if row["score"] > 0:
        pdf.set_fill_color(*PURPLE)
        pdf.rect(pdf.l_margin, bar_y, pdf.epw * min(1.0, row["score"] / row["max"]), 2.4, "F")
    pdf.set_y(y0 + 10)


def _responses(pdf: _SAPDF, content: Dict[str, Any], answers: Dict[str, int]) -> None:
    labels = {s["value"]: s["label"] for s in content["scale"]}
    for s in content["sections"]:
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_fill_color(*PURPLE)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6.5, _safe(f"  Section {s['key']} - {s['label']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        for i, q in enumerate(s["questions"]):
            v = answers.get(f"{s['key']}{i + 1}")
            if pdf.get_y() > 250:
                pdf.add_page()
            y0 = pdf.get_y()
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(135, 4.4, _safe(f"{s['key']}{i + 1}. {q}"), align="L", new_x="LMARGIN", new_y="NEXT")
            y_q = pdf.get_y()
            pdf.set_xy(pdf.l_margin + 137, y0)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*(PURPLE if v else MUTED))
            pdf.multi_cell(0, 4.4, _safe(f"{v} = {labels[v]}" if v else "Not answered"), align="R",
                           new_x="LMARGIN", new_y="NEXT")
            pdf.set_y(max(pdf.get_y(), y_q) + 1.2)
        pdf.ln(1.5)


def _foundation(pdf: _SAPDF, content: Dict[str, Any], foundation: Dict[str, Any]) -> None:
    f = content["foundation"]
    blocks = [
        (f["going_well"], [x for x in foundation.get("going_well", []) if (x or "").strip()]),
        (f["improve"], [x for x in foundation.get("improve", []) if (x or "").strip()]),
        (f["shared_goals"], [foundation.get("shared_goals")] if (foundation.get("shared_goals") or "").strip() else []),
    ]
    if not any(items for _, items in blocks):
        return
    if pdf.get_y() > 220:
        pdf.add_page()
    _heading(pdf, f["heading"])
    for label, items in blocks:
        if not items:
            continue
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*INK)
        pdf.cell(0, 5, _safe(label), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for n, item in enumerate(items, 1):
            prefix = f"{n}. " if len(items) > 1 or label != f["shared_goals"] else ""
            pdf.multi_cell(pdf.epw, 4.8, _safe(f"{prefix}{item.strip()}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)


def build_self_assessment_pdf(*, content: Dict[str, Any], state: Dict[str, Any], scores: Dict[str, Any]) -> bytes:
    pdf = _SAPDF(content["title"], content["disclaimer"])
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 9, _safe(content["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(pdf.epw, 5, _safe(content["subtitle"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, _safe(f"Generated {datetime.now(timezone.utc).strftime('%b %d, %Y')}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    _meta_block(pdf, state.get("meta") or {})
    _overall_card(pdf, content, scores)

    _heading(pdf, "Your reflection summary")
    for row in scores["sections"]:
        _section_row(pdf, row)

    pdf.ln(1)
    pdf.set_fill_color(224, 242, 254)
    pdf.set_text_color(12, 74, 110)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.multi_cell(pdf.epw, 4.6, _safe(f"How to use this assessment: {content['how_to_use']}"),
                   fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    _heading(pdf, "Your responses")
    _responses(pdf, content, state.get("answers") or {})
    _foundation(pdf, content, state.get("foundation") or {})

    return bytes(pdf.output())
