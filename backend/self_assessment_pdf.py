"""Branded PDF for the Self Journey Self-Assessment (v2).

Render-only: every label comes from `self_assessment_content.json` so the
PDF says exactly what the parent saw on screen.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fpdf import FPDF

try:
    from pdf_copyright import render_pdf_copyright  # type: ignore
except Exception:  # pragma: no cover
    def render_pdf_copyright(_pdf):
        return

PURPLE = (76, 40, 137)
PURPLE_LIGHT = (243, 239, 254)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
EMERALD = (31, 122, 77)
# Mirrors SERIES_COLORS in frontend selfAssessment/content.js.
SERIES_RGB = {
    "overall": (76, 40, 137),
    "child_focus": (64, 160, 64),
    "self_awareness": (139, 92, 246),
    "communication": (2, 132, 199),
    "differences": (230, 126, 34),
}
ROSE = (176, 52, 70)


def _safe(text: Optional[str]) -> str:
    s = "" if text is None else str(text)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-", "\u2192": "->",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _parse(iso: Optional[str]) -> datetime:
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def entry_label(entries: List[Dict[str, Any]], i: int) -> str:
    """'May 2026', or 'May 12, 2026' when two entries share a month."""
    d = _parse(entries[i].get("completed_at"))
    month = d.strftime("%B %Y")
    clash = sum(1 for e in entries if _parse(e.get("completed_at")).strftime("%B %Y") == month) > 1
    return f"{d.strftime('%B')} {d.day}, {d.year}" if clash else month


def chart_label(entries: List[Dict[str, Any]], i: int) -> str:
    """'May 2026', or 'May 12' when two entries share a month (mirrors chartLabel)."""
    d = _parse(entries[i].get("completed_at"))
    full = entry_label(entries, i)
    return f"{d.strftime('%b')} {d.day}" if "," in full else d.strftime("%b %Y")


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


def _boxed(pdf: _SAPDF, label: str, body: str, fill=PURPLE_LIGHT) -> None:
    pdf.set_fill_color(*fill)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(pdf.epw, 5.5, _safe(f"  {label}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.epw, 5, _safe(body), fill=True, padding=(0, 3, 2.5, 3), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _overall(pdf: _SAPDF, scores: Dict[str, Any], band_for: Callable) -> None:
    band = band_for(scores["overall"])
    y = pdf.get_y()
    pdf.set_fill_color(*PURPLE_LIGHT)
    pdf.set_draw_color(216, 199, 251)
    pdf.rect(pdf.l_margin, y, pdf.epw, 18 if band else 14, "DF")
    pdf.set_xy(pdf.l_margin + 4, y + 3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 7, _safe(f"Overall score: {scores['overall']} / 100"), new_x="LMARGIN", new_y="NEXT")
    if band:
        pdf.set_x(pdf.l_margin + 4)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, _safe(band["label"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y + (21 if band else 17))


def _section_bar(pdf: _SAPDF, label: str, score: int, band_for: Callable) -> None:
    y0 = pdf.get_y()
    band = band_for(score)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*INK)
    pdf.cell(120, 5, _safe(label + (f"  ·  {band['label']}" if band else "")))
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 5, _safe(f"{score} / 100"), align="R", new_x="LMARGIN", new_y="NEXT")
    bar_y = pdf.get_y() + 0.5
    pdf.set_fill_color(238, 233, 242)
    pdf.rect(pdf.l_margin, bar_y, pdf.epw, 2.4, "F")
    if score > 0:
        pdf.set_fill_color(*PURPLE)
        pdf.rect(pdf.l_margin, bar_y, pdf.epw * min(1.0, score / 100), 2.4, "F")
    pdf.set_y(y0 + 10)


def _chart(pdf: _SAPDF, content: Dict[str, Any], history: List[Dict[str, Any]]) -> None:
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, _safe(content["chart"]["title"]), new_x="LMARGIN", new_y="NEXT")
    x0, y0 = pdf.l_margin + 9, pdf.get_y() + 2
    w, h = pdf.epw - 14, 48
    pdf.set_font("Helvetica", "", 7)
    pdf.set_line_width(0.15)
    for tick in (0, 25, 50, 75, 100):
        y = y0 + h - h * tick / 100
        pdf.set_draw_color(226, 220, 245)
        pdf.line(x0, y, x0 + w, y)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(pdf.l_margin, y - 2)
        pdf.cell(8, 4, str(tick), align="R")
    n = len(history)
    xs = [x0 + (w * i / (n - 1) if n > 1 else w / 2) for i in range(n)]
    step = max(1, (n + 7) // 8)
    for i, x in enumerate(xs):
        if i % step == 0 or i == n - 1:
            pdf.set_xy(x - 12, y0 + h + 1)
            pdf.cell(24, 4, _safe(chart_label(history, i)), align="C")
    series = [("overall", content["chart"]["overall_label"])] + [
        (s["key"], s["score_label"]) for s in content["sections"]
    ]
    for key, _label in reversed(series):
        vals = [h_["scores"]["overall"] if key == "overall" else h_["scores"]["sections"][key] for h_ in history]
        pts = [(x, y0 + h - h * v / 100) for x, v in zip(xs, vals)]
        pdf.set_draw_color(*SERIES_RGB[key])
        pdf.set_fill_color(*SERIES_RGB[key])
        pdf.set_line_width(0.9 if key == "overall" else 0.45)
        for a, b in zip(pts, pts[1:]):
            pdf.line(a[0], a[1], b[0], b[1])
        r = 1.1 if key == "overall" else 0.7
        for x, y in pts:
            pdf.ellipse(x - r, y - r, 2 * r, 2 * r, "F")
    pdf.set_line_width(0.2)
    pdf.set_xy(pdf.l_margin, y0 + h + 7)
    for key, label in series:
        pdf.set_fill_color(*SERIES_RGB[key])
        pdf.rect(pdf.get_x(), pdf.get_y() + 1.3, 2.4, 2.4, "F")
        pdf.set_x(pdf.get_x() + 3.2)
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B" if key == "overall" else "", 7.5)
        pdf.cell(pdf.get_string_width(_safe(label)) + 5, 5, _safe(label))
    pdf.ln(8)


def _progress(pdf: _SAPDF, content: Dict[str, Any], history: List[Dict[str, Any]]) -> None:
    _heading(pdf, "Your Progress")
    pdf.set_font("Helvetica", "", 9.5)
    for i, h in enumerate(history):
        pdf.set_text_color(*INK)
        pdf.cell(60, 5.5, _safe(entry_label(history, i)))
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*PURPLE)
        pdf.cell(0, 5.5, _safe(f"{h['scores']['overall']}/100"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9.5)
    if len(history) > 1:
        pdf.ln(2)
        if pdf.get_y() > 190:
            pdf.add_page()
        _chart(pdf, content, history)
        first, latest = history[0]["scores"]["sections"], history[-1]["scores"]["sections"]
        for s in content["sections"]:
            delta = latest[s["key"]] - first[s["key"]]
            pdf.set_text_color(*INK)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.cell(60, 5.5, _safe(f"{s['score_label']}:"))
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*(EMERALD if delta > 0 else ROSE if delta < 0 else MUTED))
            pdf.cell(0, 5.5, _safe(f"{first[s['key']]} → {latest[s['key']]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _responses(pdf: _SAPDF, content: Dict[str, Any], entry: Dict[str, Any]) -> None:
    labels = {s["value"]: s["label"] for s in content["scale"]}
    answers = entry.get("answers") or {}
    for s in content["sections"]:
        if pdf.get_y() > 235:
            pdf.add_page()
        pdf.set_fill_color(*PURPLE)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6.5, _safe(f"  {s['number']}. {s['title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        for i, q in enumerate(s["questions"]):
            if pdf.get_y() > 250:
                pdf.add_page()
            v = answers.get(f"{s['key']}_{i + 1}")
            y0 = pdf.get_y()
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(140, 4.4, _safe(q), align="L", new_x="LMARGIN", new_y="NEXT")
            y_q = pdf.get_y()
            pdf.set_xy(pdf.l_margin + 142, y0)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*(PURPLE if v else MUTED))
            pdf.multi_cell(0, 4.4, _safe(f"{v} — {labels[v]}" if v else "Not answered"), align="R",
                           new_x="LMARGIN", new_y="NEXT")
            pdf.set_y(max(pdf.get_y(), y_q) + 1.2)
        pdf.ln(1.5)

    r = content["reflection"]
    if pdf.get_y() > 220:
        pdf.add_page()
    pdf.set_fill_color(*PURPLE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6.5, _safe(f"  {r['number']}. {r['title']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)
    reflections = entry.get("reflections") or {}
    for q in r["questions"]:
        if pdf.get_y() > 245:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*INK)
        pdf.multi_cell(pdf.epw, 4.8, _safe(q["prompt"]), new_x="LMARGIN", new_y="NEXT")
        body = (reflections.get(q["key"]) or "").strip()
        pdf.set_font("Helvetica", "" if body else "I", 9)
        pdf.set_text_color(*(INK if body else MUTED))
        pdf.multi_cell(pdf.epw, 4.8, _safe(body or "Skipped"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)


def build_self_assessment_pdf(
    *,
    content: Dict[str, Any],
    entry: Dict[str, Any],
    history: List[Dict[str, Any]],
    band_for: Callable[[int], Optional[Dict[str, Any]]],
) -> bytes:
    pdf = _SAPDF(content["title"], content["disclaimer"])
    pdf.add_page()
    scores = entry["scores"]
    completed = _parse(entry.get("completed_at"))

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 9, _safe(content["title"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9.5)
    pdf.set_text_color(*MUTED)
    who = entry.get("parent_name") or "a parent"
    pdf.cell(0, 5, _safe(f"Prepared for {who}  ·  {completed.strftime('%B')} {completed.day}, {completed.year}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    _overall(pdf, scores, band_for)
    for s in content["sections"]:
        _section_bar(pdf, s["score_label"], scores["sections"][s["key"]], band_for)
    pdf.ln(1)

    if history:
        _progress(pdf, content, history)
    _boxed(pdf, "Remember", content["central_message"])
    goal = (entry.get("goal") or "").strip()
    if goal:
        _boxed(pdf, content["goal"]["label"], goal, fill=(234, 247, 234))

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(pdf.epw, 5, _safe("  →  ".join(content["cycle"])), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    _heading(pdf, "Your responses")
    _responses(pdf, content, entry)

    return bytes(pdf.output())
