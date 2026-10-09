"""Journey Summary PDF: one parent's five Self Journey assessments in a single document."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fpdf import FPDF

from child_needs_pdf import render_notices
from pdf_base import _safe, render_pdf_copyright

PURPLE = (76, 40, 137)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
EMERALD = (56, 161, 105)
AMBER = (180, 98, 6)
LINE = (236, 232, 245)
DISCLAIMER = "Prepared from this parent's own answers. General information, not legal advice."
SAFETY = "If you have safety concerns, speak with a qualified professional before sharing this document."
NOT_YET = "Not completed yet."
NEEDS_ORDER = ["educational", "medical", "psychological"]


class _SummaryPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 4, _safe(DISCLAIMER), align="C")
        render_pdf_copyright(self)


def _date(iso: Optional[str]) -> str:
    try:
        return f"{datetime.fromisoformat(iso):%b %d, %Y}"
    except (TypeError, ValueError):
        return ""


def _room(pdf: FPDF, need: float) -> None:
    if pdf.get_y() + need > pdf.h - 22:
        pdf.add_page()


def _header(pdf: FPDF, parent_name: str, done: int) -> None:
    pdf.set_fill_color(*PURPLE)
    pdf.rect(0, 0, pdf.w, 25, "F")
    pdf.set_xy(16, 6.5)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "Journey Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(16)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(221, 214, 254)
    pdf.cell(0, 5, _safe("SA CoParents  ·  Self Journey assessments"))
    pdf.set_xy(16, 30)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.cell(0, 5, _safe(f"Parent: {parent_name}     Prepared: {datetime.now():%b %d, %Y}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5, f"Progress: {done} of 5 assessments completed", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _notice(pdf: FPDF, text: str) -> None:
    pdf.set_fill_color(242, 235, 252)
    pdf.set_draw_color(203, 196, 222)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(0, 4.4, _safe(text), border=1, fill=True, padding=2.2, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _section(pdf: FPDF, n: int, title: str, completed_at: Optional[str]) -> None:
    _room(pdf, 24)
    pdf.ln(3)
    pdf.set_draw_color(*LINE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 6.5, _safe(f"{n}. {title}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*(EMERALD if completed_at else AMBER))
    status = f"Completed {_date(completed_at)}".strip() if completed_at else NOT_YET
    pdf.cell(0, 4.6, _safe(status), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _row(pdf: FPDF, label: str, value: str) -> None:
    _room(pdf, 10)
    pdf.set_font("Helvetica", "B", 8.8)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 4.5, _safe(label), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.5, _safe(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.2)


def _score(pdf: FPDF, label: str, value: str) -> None:
    _room(pdf, 7)
    y = pdf.get_y()
    pdf.set_font("Helvetica", "", 8.8)
    pdf.set_text_color(*INK)
    pdf.cell(pdf.epw - 48, 5.4, _safe(label))
    pdf.set_font("Helvetica", "B", 8.8)
    pdf.set_text_color(*PURPLE)
    pdf.cell(48, 5.4, _safe(value), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*LINE)
    pdf.line(pdf.l_margin, y + 5.6, pdf.w - pdf.r_margin, y + 5.6)
    pdf.ln(0.6)


def _self(pdf: FPDF, history: List[Dict[str, Any]], content: Dict[str, Any], band_for: Callable) -> None:
    entry = history[-1] if history else None
    _section(pdf, 1, "Self-Assessment", entry and entry.get("completed_at"))
    if not entry:
        return
    scores = entry.get("scores") or {}
    band = band_for(scores.get("overall", 0))
    overall = f"{scores.get('overall', 0)}/100" + (f"  ·  {band['label']}" if band else "")
    _row(pdf, "Overall score", f"{overall}  (completed {len(history)} time{'s' if len(history) != 1 else ''})")
    for s in content["sections"]:
        if s["key"] in scores.get("sections", {}):
            _score(pdf, s["title"], f"{scores['sections'][s['key']]}/100")
    if entry.get("goal"):
        pdf.ln(1.5)
        _row(pdf, "My goal", entry["goal"])


def _coparent(pdf: FPDF, doc: Optional[Dict[str, Any]]) -> None:
    _section(pdf, 2, "Co-Parenting Relationship Assessment", doc and (doc.get("completed_at") or doc.get("updated_at")))
    if not doc:
        return
    scores = doc["scores"]
    _row(pdf, "Overall", scores.get("overall_rating") or "Not enough data")
    for s in scores.get("sections", []):
        _score(pdf, f"Section {s['number']}: {s['name']}", s.get("rating") or "Not answered")


def _needs(pdf: FPDF, n: int, category: Dict[str, Any], answers: Dict[str, str], completed_at: Optional[str]) -> None:
    _section(pdf, n, category["form_title"], completed_at)
    if not completed_at:
        return
    for f in category["fields"]:
        if (answers.get(f["id"]) or "").strip():
            _row(pdf, f["label"], answers[f["id"]])


def build_journey_summary_pdf(
    *,
    parent_name: str,
    sa_history: List[Dict[str, Any]],
    sa_content: Dict[str, Any],
    band_for: Callable,
    cp_doc: Optional[Dict[str, Any]],
    needs_content: Dict[str, Any],
    needs_state: Dict[str, Any],
) -> bytes:
    completed = needs_state.get("completed_at") or {}
    answers = needs_state.get("answers") or {}
    done = int(bool(sa_history)) + int(bool(cp_doc)) + sum(1 for k in NEEDS_ORDER if completed.get(k))
    pdf = _SummaryPDF(format="Letter")
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()
    _header(pdf, parent_name, done)
    _notice(pdf, SAFETY)
    _self(pdf, sa_history, sa_content, band_for)
    _coparent(pdf, cp_doc)
    cats = {c["key"]: c for c in needs_content["categories"]}
    _room(pdf, 60)
    pdf.ln(3)
    render_notices(pdf, needs_content["notices"])
    for i, key in enumerate(NEEDS_ORDER, start=3):
        _needs(pdf, i, cats[key], answers.get(key) or {}, completed.get(key))
    return bytes(pdf.output())
