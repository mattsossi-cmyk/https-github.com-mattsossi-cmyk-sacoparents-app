"""Branded PDF for the Parallel Parenting Option Builder (render-only)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fpdf import FPDF

from pdf_base import _safe, render_pdf_copyright

PURPLE = (74, 37, 116)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
LAVENDER = (244, 240, 250)
GREEN = (56, 142, 60)


class _PPPDF(FPDF):
    def __init__(self, disclaimer: str):
        super().__init__(format="Letter")
        self._disclaimer = disclaimer
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*PURPLE)
        self.cell(0, 6, _safe("SA CoParents  ·  Parallel Parenting Plan"), new_x="LMARGIN", new_y="NEXT")
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


def _box(pdf: _PPPDF, label: str, body: str, rgb=LAVENDER) -> None:
    pdf.set_fill_color(*rgb)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 5.5, _safe(f"  {label}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.epw, 4.8, _safe(body), fill=True, padding=(0.5, 3, 2.5, 3), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _day(iso: str) -> str:
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _intro(pdf: _PPPDF, content: Dict[str, Any], parent_name: str, made: int, total: int, saved_on: Optional[str]) -> None:
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 10, "Your Parallel Parenting Plan", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, _safe(content["banner_title"]), new_x="LMARGIN", new_y="NEXT")
    when = f"Version saved {_day(saved_on)}" if saved_on else _day(datetime.now(timezone.utc).isoformat())
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    meta = f"Prepared for {parent_name or 'you'}  ·  {when}  ·  {made} of {total} choices made"
    pdf.cell(0, 6, _safe(meta), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.multi_cell(pdf.epw, 5, _safe(content["pdf_intro"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _changes(pdf: _PPPDF, note: Dict[str, Any]) -> None:
    if not note["since"]:
        _box(pdf, "Changes since your last version", "This is the first saved version of your plan.", (238, 242, 255))
        return
    lines = [c.replace("→", "->") for c in note["changes"]] or ["No changes since your last version."]
    body = "\n".join(f"-  {c}" for c in lines)
    _box(pdf, f"Changes since your last version ({_day(note['since'])})", body, (238, 242, 255))


def _step(pdf: _PPPDF, step: Dict[str, Any], plan: Dict[str, Any]) -> None:
    if pdf.get_y() > 215:
        pdf.add_page()
    pdf.set_fill_color(*PURPLE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 7.5, _safe(f"  Step {step['number']}  ·  {step['title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    answers = plan.get("answers") or {}
    for q in step["questions"]:
        if pdf.get_y() > 245:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*INK)
        pdf.multi_cell(pdf.epw, 4.8, _safe(q["text"]), new_x="LMARGIN", new_y="NEXT")
        opt = next((o for o in q["options"] if o["id"] == answers.get(q["id"])), None)
        pdf.set_x(pdf.l_margin + 4)
        if opt:
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*GREEN)
            pdf.multi_cell(pdf.epw - 4, 5, _safe(f"{opt['label']}  -  {opt['desc']}"), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(pdf.epw - 4, 5, "Not chosen yet", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
    note = ((plan.get("notes") or {}).get(step["key"]) or "").strip()
    tip = ((plan.get("tips") or {}).get(step["key"]) or "").strip()
    if note:
        _box(pdf, "My notes", note)
    if tip:
        _box(pdf, "Tip from your Guide", tip, (236, 253, 243))
    pdf.ln(2)


def _checklist(pdf: _PPPDF, check: Dict[str, Any], plan: Dict[str, Any]) -> None:
    if pdf.get_y() > 215:
        pdf.add_page()
    pdf.set_fill_color(*PURPLE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 7.5, _safe(f"  Quick check  ·  {check['title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    if check.get("note"):
        _box(pdf, "Please note", check["note"], (255, 247, 237))
    ticked = set((plan.get("checks") or {}).get(check["key"]) or [])
    for item in check["items"]:
        if pdf.get_y() > 250:
            pdf.add_page()
        on = item["id"] in ticked
        pdf.set_font("Helvetica", "B" if on else "", 9.5)
        pdf.set_text_color(*(GREEN if on else MUTED))
        pdf.multi_cell(pdf.epw, 5.2, _safe(f"{'[x]' if on else '[  ]'}  {item['label']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)
    note = ((plan.get("notes") or {}).get(check["key"]) or "").strip()
    if note:
        pdf.ln(1)
        _box(pdf, "My notes", note)
    pdf.ln(3)


AMBER = (180, 98, 6)


def _status_row(pdf: _PPPDF, label: str, matched: bool) -> None:
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*(GREEN if matched else AMBER))
    pdf.cell(36, 5.2, "Matches my order" if matched else "Still to check")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.epw - 36, 5.2, _safe(label), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(236, 232, 245)
    pdf.line(pdf.l_margin, max(pdf.get_y(), y + 5.2) + 0.8, pdf.w - pdf.r_margin, max(pdf.get_y(), y + 5.2) + 0.8)
    pdf.ln(1.8)


def _heading(pdf: _PPPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 7, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.5)


def build_court_notes_pdf(content: Dict[str, Any], plan: Dict[str, Any], parent_name: str) -> bytes:
    """One-page Court-Order Notes: the court-order self-check, notes and topics for professional review."""
    lists = {c["key"]: c for c in content["checklists"]}
    court, review = lists["court_check"], lists["professional_review"]
    checks = plan.get("checks") or {}
    notes = plan.get("notes") or {}
    matched = set(checks.get("court_check") or [])
    topics = [i for i in review["items"] if i["id"] in set(checks.get("professional_review") or [])]
    pdf = _PPPDF(content["disclaimer"])
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 9, "Court-Order Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    today = datetime.now(timezone.utc).isoformat()
    pdf.cell(0, 5, _safe(f"Prepared by {parent_name} on {_day(today)}  ·  To bring to a family law attorney or mediator"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2.5)
    _box(pdf, "Please note", court["note"], (255, 247, 237))
    _heading(pdf, f"Texas Court-Order Compatibility Check  ·  {len(matched)} of {len(court['items'])} match my order")
    for item in court["items"]:
        _status_row(pdf, item["label"], item["id"] in matched)
    pdf.ln(1.5)
    if (notes.get("court_check") or "").strip():
        _box(pdf, "My notes", notes["court_check"].strip())
    _heading(pdf, "Topics for professional review")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*(INK if topics else MUTED))
    for t in topics or [{"label": "None ticked yet."}]:
        pdf.multi_cell(pdf.epw, 5.2, _safe(f"-  {t['label']}"), new_x="LMARGIN", new_y="NEXT")
    if (notes.get("professional_review") or "").strip():
        pdf.ln(1.5)
        _box(pdf, "More to discuss", notes["professional_review"].strip())
    pdf.ln(2)
    _box(pdf, "Next step", "Bring this page and a copy of your current court order to your appointment so a professional can confirm what fits.")
    return bytes(pdf.output())


def build_pp_pdf(
    content: Dict[str, Any],
    plan: Dict[str, Any],
    parent_name: str,
    change_note: Optional[Dict[str, Any]] = None,
    saved_on: Optional[str] = None,
) -> bytes:
    total = sum(len(s["questions"]) for s in content["steps"])
    pdf = _PPPDF(content["disclaimer"])
    pdf.add_page()
    _intro(pdf, content, parent_name, len(plan.get("answers") or {}), total, saved_on)
    if change_note:
        _changes(pdf, change_note)
        pdf.ln(2)
    for step in content["steps"]:
        _step(pdf, step, plan)
    for check in content["checklists"]:
        _checklist(pdf, check, plan)
    if pdf.get_y() > 240:
        pdf.add_page()
    _box(pdf, "Before you rely on this plan", content["pdf_closing"], (255, 247, 237))
    return bytes(pdf.output())
