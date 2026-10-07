"""Iter235 · One-page "Progress Snapshot" PDF.

Mediator / attorney-facing proof-of-work artefact a parent can
email ("here's how I've changed in 60 days"). Rendered from the
same progress payload the Alignment & Tools progress tile
consumes (`cp_report_history.build_progress_payload`), so the two
surfaces always say the same thing.

One portrait page, intentionally — this is a hand-off summary,
not a full report. If the mediator wants the full 10-section
report they can still download it from the regular endpoint.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

try:
    from pdf_copyright import render_pdf_copyright  # type: ignore
except Exception:  # pragma: no cover
    def render_pdf_copyright(_pdf):
        return


# Keep in step with cp_report_history._RATING_VALUES.
_RATING_COLOURS = {
    "Needs Improvement": (182, 102, 59),   # amber-700
    "Fair":              (203, 161, 53),   # amber-500 ish
    "Good":              (63, 123, 71),    # emerald-700
    "Excellent":         (31, 92, 59),     # emerald-900
    "Building Progress": (99, 102, 241),   # indigo
    "Not enough data":   (133, 126, 156),  # slate
}


def _safe(text: Optional[str]) -> str:
    if text is None:
        return ""
    s = str(text)
    for k, v in {
        "\u2014": "-", "\u2013": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-", "\u00a0": " ",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class _ProgressPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(61, 26, 120)
        self.cell(0, 6, "SA CoParents  ·  Progress Snapshot", ln=1)
        self.set_draw_color(220, 214, 232)
        self.line(15, 26, 195, 26)
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(133, 126, 156)
        self.cell(
            0, 5,
            "Educational reflection tool - not legal or clinical advice.",
            align="C",
        )
        render_pdf_copyright(self)


def _fmt_date(iso: Optional[str]) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime(
            "%b %-d, %Y"
        )
    except Exception:
        return iso[:10]


def _draw_sparkline(pdf: _ProgressPDF, series: List[Dict[str, Any]]) -> None:
    """Compact rating sparkline, 180 x 24 mm."""
    if not series:
        return
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    w = pdf.epw
    h = 24
    pad = 3
    # Faint guide rows (1..4)
    pdf.set_draw_color(230, 225, 240)
    for band in (1, 2, 3, 4):
        y = y0 + h - pad - ((band - 0) / 4) * (h - pad * 2)
        pdf.line(x0 + pad, y, x0 + w - pad, y)
    # Line through points
    n = len(series)
    xs = [
        x0 + pad + (i * (w - pad * 2) / max(1, n - 1))
        for i in range(n)
    ]
    ys = [
        y0 + h - pad - ((p.get("value") or 0) / 4) * (h - pad * 2)
        for p in series
    ]
    pdf.set_draw_color(61, 26, 120)
    pdf.set_line_width(0.6)
    for i in range(1, n):
        pdf.line(xs[i - 1], ys[i - 1], xs[i], ys[i])
    # Dots coloured by rating band
    for i, p in enumerate(series):
        c = _RATING_COLOURS.get(p.get("rating") or "", (61, 26, 120))
        pdf.set_fill_color(*c)
        pdf.ellipse(xs[i] - 0.9, ys[i] - 0.9, 1.8, 1.8, "F")
    pdf.set_y(y0 + h + 1)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(133, 126, 156)
    pdf.cell(w / 2, 4, _safe(_fmt_date(series[0].get("submitted_at"))), align="L")
    pdf.cell(w / 2, 4, _safe(_fmt_date(series[-1].get("submitted_at"))), align="R", ln=1)


def _draw_movers(pdf: _ProgressPDF, movers: List[Dict[str, Any]], max_rows: int = 5) -> None:
    rows = movers[:max_rows]
    if not rows:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(133, 126, 156)
        pdf.cell(0, 5, _safe("Not enough history yet to show section movers."), ln=1)
        return
    x0 = pdf.l_margin
    bar_w_max = 46  # mm
    pdf.set_font("Helvetica", "", 9)
    max_delta = max((abs(m.get("delta") or 0) for m in rows), default=1) or 1
    for m in rows:
        delta = float(m.get("delta") or 0)
        direction = m.get("direction") or "flat"
        label = f"{m.get('number')}. {m.get('name') or ''}"
        delta_str = f"{'+' if delta > 0 else ''}{delta:.2f}"
        arrow = "^" if direction == "up" else "v" if direction == "down" else "-"
        pdf.set_x(x0)
        pdf.set_text_color(52, 46, 78)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(100, 5, _safe(label[:52]))
        pdf.set_font("Helvetica", "B", 9)
        if direction == "up":
            pdf.set_text_color(31, 92, 59)
        elif direction == "down":
            pdf.set_text_color(182, 102, 59)
        else:
            pdf.set_text_color(133, 126, 156)
        pdf.cell(20, 5, _safe(f"{arrow} {delta_str}"), align="R")
        # bar
        bar_x = x0 + 125
        bar_y = pdf.get_y() + 1.6
        pdf.set_draw_color(230, 225, 240)
        pdf.set_fill_color(241, 237, 248)
        pdf.rect(bar_x, bar_y, bar_w_max, 1.8, "F")
        used = (abs(delta) / max_delta) * bar_w_max
        if direction == "up":
            pdf.set_fill_color(63, 123, 71)
        elif direction == "down":
            pdf.set_fill_color(203, 128, 53)
        else:
            pdf.set_fill_color(190, 185, 205)
        pdf.rect(bar_x, bar_y, used, 1.8, "F")
        pdf.ln(6)


def _fmt_datetime(iso: Optional[str]) -> str:
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %-d, %Y  %-I:%M %p")
    except Exception:
        return iso[:16]


def _section_title(pdf: "_ProgressPDF", text: str) -> None:
    if pdf.get_y() > 235:
        pdf.add_page()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 5, _safe(text), ln=1)
    pdf.ln(0.5)


def _draw_safety_timeline(pdf: "_ProgressPDF", parent_name: str, rows: List[Dict[str, Any]]) -> None:
    _section_title(pdf, "Safety timeline (Grey-Rock mode)")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(133, 126, 156)
    pdf.multi_cell(pdf.epw, 4, _safe(f"Included by {parent_name} by choice. Shows when Grey-Rock safety mode was turned on or off."),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    if not rows:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, _safe("No safety-mode changes recorded."), ln=1)
        return
    for r in rows:
        on = r.get("event") == "on"
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(52, 46, 78)
        pdf.cell(52, 5, _safe(_fmt_datetime(r.get("at"))))
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*((182, 102, 59) if on else (63, 123, 71)))
        pdf.cell(55, 5, _safe(f"Grey-Rock mode turned {'ON' if on else 'OFF'}"))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(133, 126, 156)
        pdf.cell(0, 5, _safe(r.get("source") or ""), ln=1)


def _draw_biff_pairs(pdf: "_ProgressPDF", parent_name: str, pairs: List[Dict[str, Any]]) -> None:
    _section_title(pdf, "Recent BIFF messages")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(133, 126, 156)
    pdf.multi_cell(pdf.epw, 4, _safe(f"Included by {parent_name} by choice. Up to 5 most recent drafts and their BIFF rewrites."),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    if not pairs:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, _safe("No BIFF messages saved yet."), ln=1)
        return
    for p in pairs:
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(133, 126, 156)
        pdf.cell(0, 4.5, _safe(_fmt_datetime(p.get("saved_at"))), ln=1)
        for label, key, rgb in (("Original:", "original", (52, 46, 78)), ("BIFF rewrite:", "rewrite", (31, 92, 59))):
            text = (p.get(key) or "").strip()
            if not text:
                continue
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*rgb)
            pdf.cell(24, 4.8, _safe(label))
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(52, 46, 78)
            pdf.multi_cell(pdf.epw - 24, 4.8, _safe(text[:700] + ("..." if len(text) > 700 else "")),
                           new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)


def build_progress_pdf(
    *,
    parent_name: str,
    progress: Dict[str, Any],
    mediator_name: Optional[str] = None,
    note: Optional[str] = None,
    safety_timeline: Optional[List[Dict[str, Any]]] = None,
    biff_pairs: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """Render the single-page progress PDF.

    `progress` is the dict returned by
    `cp_report_history.build_progress_payload`.
    """
    pdf = _ProgressPDF()
    pdf.add_page()

    # Headline + prepared-for line
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 19, 48)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 8, _safe("Co-Parenting Progress Snapshot"))
    pdf.ln(0.5)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(133, 126, 156)
    header_line = f"Prepared for {mediator_name}" if mediator_name else "Progress Snapshot"
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 5, _safe(f"{header_line}  ·  from {parent_name}"))
    pdf.ln(2)

    recent = (progress or {}).get("recent") or {}
    baseline = (progress or {}).get("baseline") or {}
    snapshots = (progress or {}).get("snapshots") or []
    days_since_last = progress.get("days_since_last")
    interval = progress.get("retake_interval_days") or 60

    # Latest-rating badge card
    rating = recent.get("overall_rating") or "Not enough data"
    rating_rgb = _RATING_COLOURS.get(rating, (61, 26, 120))
    pdf.set_fill_color(*[int(c + (255 - c) * 0.88) for c in rating_rgb])
    pdf.set_draw_color(*[int(c + (255 - c) * 0.5) for c in rating_rgb])
    y_card = pdf.get_y()
    pdf.rect(pdf.l_margin, y_card, pdf.epw, 14, "DF")
    pdf.set_xy(pdf.l_margin + 3, y_card + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*rating_rgb)
    pdf.cell(0, 5, _safe(f"Latest rating:  {rating}"), ln=1)
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(52, 46, 78)
    pdf.cell(
        0, 4,
        _safe(
            f"{len(snapshots)} check-in{'s' if len(snapshots) != 1 else ''}  ·  "
            f"latest {_fmt_date(recent.get('submitted_at'))}"
            + (
                f"  ·  {days_since_last} day{'s' if days_since_last != 1 else ''} ago"
                if days_since_last is not None else ""
            )
        ),
        ln=1,
    )
    pdf.set_y(y_card + 16)

    # Trend sparkline
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 5, _safe("Rating trend over time"), ln=1)
    _draw_sparkline(pdf, progress.get("overall_series") or [])

    # Section movers
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(61, 26, 120)
    label = (
        f"Biggest movers vs ~{interval}d ago"
        if baseline else "Section ratings (baseline not available yet)"
    )
    pdf.cell(0, 5, _safe(label), ln=1)
    pdf.ln(0.5)
    _draw_movers(pdf, progress.get("section_movers") or [])

    # Section-by-section ratings table (latest + baseline)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 5, _safe("All sections — latest rating"), ln=1)
    pdf.ln(0.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(133, 126, 156)
    pdf.cell(110, 4, _safe("Section"))
    pdf.cell(35, 4, _safe("Latest"))
    pdf.cell(35, 4, _safe(f"~{interval}d ago"), ln=1)
    pdf.set_draw_color(230, 225, 240)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + pdf.epw, pdf.get_y())
    pdf.ln(1)
    base_map = {s.get("id"): s for s in (baseline.get("section_avgs") or [])}
    for row in recent.get("section_avgs") or []:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(52, 46, 78)
        name = f"{row.get('number')}. {row.get('name') or ''}"
        pdf.cell(110, 5, _safe(name[:62]))
        cur_rating = row.get("rating") or "-"
        c = _RATING_COLOURS.get(cur_rating, (52, 46, 78))
        pdf.set_text_color(*c)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(35, 5, _safe(cur_rating))
        prev = base_map.get(row.get("id"))
        prev_rating = (prev or {}).get("rating") or "-"
        pc = _RATING_COLOURS.get(prev_rating, (133, 126, 156))
        pdf.set_text_color(*pc)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(35, 5, _safe(prev_rating), ln=1)

    # Optional parent note to the mediator
    cleaned_note = (note or "").strip()
    if cleaned_note:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 5, _safe(f"Note from {parent_name}"), ln=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(52, 46, 78)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 4.6, _safe(cleaned_note))

    # Opt-in extras — None means the parent did not tick the box.
    if safety_timeline is not None:
        _draw_safety_timeline(pdf, parent_name, safety_timeline)
    if biff_pairs is not None:
        _draw_biff_pairs(pdf, parent_name, biff_pairs)

    return bytes(pdf.output(dest="S"))
