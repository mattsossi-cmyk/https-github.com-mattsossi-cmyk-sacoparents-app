"""Iter241 · One-page Co-Parenting Preview Profile PDF.

Sister artefact to `cp_progress_pdf.py` — but for the 40-question
8-domain preview form (`/coparenting-self-assessment-preview.html`)
instead of the thorough 70-question report. Parents who complete
the free preview can download a branded one-page profile and share
it the same way they share a Progress Snapshot.

Contract: the HTML form posts the already-computed 8-domain scores
and 3 reflection fields; this module only renders. No scoring
logic here, so copy stays in lockstep with the HTML's own labels.

No PII beyond what the parent typed into the three reflection
textareas and the metadata fields.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

try:
    from pdf_base import render_pdf_copyright  # type: ignore
except Exception:  # pragma: no cover
    def render_pdf_copyright(_pdf):
        return


# Mirrors the exact bands + labels used by `getProfileLabel()` in
# the HTML form. Any band tweak in one place MUST be mirrored here
# to keep the parent's screen and the shared PDF saying the same
# thing.
BANDS: List[tuple] = [
    (4.25, "Current Strength",             (31, 92, 59)),   # emerald
    (3.5,  "Generally Working",            (63, 123, 71)),  # emerald-700
    (2.75, "Opportunity for Growth",       (178, 122, 24)), # amber
    (2.0,  "Needs Attention",              (203, 128, 53)), # amber-500
    (0.0,  "Priority Area for Discussion", (159, 69, 69)),  # red
]


def _band_for(score: float) -> tuple:
    for cutoff, label, rgb in BANDS:
        if score >= cutoff:
            return (label, rgb)
    return BANDS[-1][1], BANDS[-1][2]


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


class _ProfilePDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 18, 15)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(79, 40, 121)
        self.cell(0, 6, "SA CoParents  ·  Co-Parenting Preview Profile", ln=1)
        self.set_draw_color(221, 212, 231)
        self.line(15, 26, 195, 26)
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(108, 101, 113)
        self.cell(
            0, 5,
            "Educational reflection tool - not legal, custody, or clinical advice.",
            align="C",
        )
        render_pdf_copyright(self)


def _draw_domain_row(pdf: _ProfilePDF, idx: int, name: str, score: float) -> None:
    """One progress-bar row per domain."""
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    pdf.set_x(x0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(47, 41, 51)
    pdf.cell(100, 5, _safe(f"{idx + 1}. {name[:48]}"))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(79, 40, 121)
    pdf.cell(20, 5, _safe(f"{score:.1f} / 5"), align="R")
    band_label, rgb = _band_for(score)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*rgb)
    pdf.cell(0, 5, _safe(band_label), align="R", ln=1)
    # bar
    bar_x = x0
    bar_y = pdf.get_y() + 0.5
    bar_w = pdf.epw
    bar_h = 2.4
    pdf.set_fill_color(238, 233, 242)
    pdf.rect(bar_x, bar_y, bar_w, bar_h, "F")
    used = min(1.0, max(0.0, score / 5.0)) * bar_w
    pdf.set_fill_color(111, 63, 160)  # SA CoParents purple
    pdf.rect(bar_x, bar_y, used, bar_h, "F")
    pdf.set_y(y0 + 9.5)


def build_preview_profile_pdf(
    *,
    parent_name: str,
    scores: List[Dict[str, Any]],
    reflection: Dict[str, Any],
    completed_at: Optional[str] = None,
) -> bytes:
    """Render the one-page profile. `scores` is a list of
    `{"domain": str, "score": float}` in display order (as the HTML
    form emits them). `reflection` has the three textarea fields.
    """
    pdf = _ProfilePDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 19, 48)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 8, _safe("Your Co-Parenting Profile"))
    pdf.ln(0.5)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(108, 101, 113)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.epw, 5,
        _safe(
            f"Prepared for {parent_name}"
            + (f"  ·  completed {completed_at}" if completed_at else "")
        ),
    )
    pdf.ln(2)

    # Overall card (average of 8 domains)
    valid_scores = [float(s.get("score") or 0) for s in scores if s]
    overall = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 0.0
    band, rgb = _band_for(overall)
    pdf.set_fill_color(*[int(c + (255 - c) * 0.88) for c in rgb])
    pdf.set_draw_color(*[int(c + (255 - c) * 0.5) for c in rgb])
    y_card = pdf.get_y()
    pdf.rect(pdf.l_margin, y_card, pdf.epw, 14, "DF")
    pdf.set_xy(pdf.l_margin + 3, y_card + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*rgb)
    pdf.cell(0, 5, _safe(f"Overall:  {band}  ·  {overall:.1f} / 5"), ln=1)
    pdf.set_x(pdf.l_margin + 3)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(47, 41, 51)
    pdf.cell(
        0, 4,
        _safe(f"Averaged across {len(scores)} domains  ·  40 self-reflection prompts"),
        ln=1,
    )
    pdf.set_y(y_card + 16)

    # Per-domain progress bars
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(79, 40, 121)
    pdf.cell(0, 5, _safe("Where you land, domain by domain"), ln=1)
    pdf.ln(1.5)
    for i, row in enumerate(scores):
        _draw_domain_row(
            pdf,
            i,
            str(row.get("domain") or ""),
            float(row.get("score") or 0),
        )

    # Strengths + attention summary (same logic as the HTML form)
    ordered = sorted(scores, key=lambda r: float(r.get("score") or 0), reverse=True)
    strengths = [str(r.get("domain") or "") for r in ordered[:3]]
    attention = [str(r.get("domain") or "") for r in ordered[-3:][::-1]]
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(79, 40, 121)
    pdf.cell(0, 5, _safe("Profile Summary"), ln=1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(47, 41, 51)
    pdf.cell(0, 5, _safe("Areas currently showing strength:"), ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 4.6, _safe("  -  " + "  -  ".join(strengths)))
    pdf.ln(0.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _safe("Areas that may benefit from additional attention:"), ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 4.6, _safe("  -  " + "  -  ".join(attention)))

    # Optional reflection
    r_working = (reflection.get("whats_working") or "").strip()
    r_improve = (reflection.get("to_improve") or "").strip()
    r_change = (reflection.get("one_change") or "").strip()
    if any([r_working, r_improve, r_change]):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(79, 40, 121)
        pdf.cell(0, 5, _safe("Parent reflection"), ln=1)
        for label, body in [
            ("What is currently working well for my child", r_working),
            ("What I would most like to improve",            r_improve),
            ("One change I could make now",                   r_change),
        ]:
            if not body:
                continue
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(47, 41, 51)
            pdf.cell(0, 5, _safe(label), ln=1)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 4.6, _safe(body))
            pdf.ln(0.3)

    return bytes(pdf.output(dest="S"))
