"""Self Journey completion certificate: one landscape page."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from fpdf import FPDF

from pdf_base import _safe, render_pdf_copyright

PURPLE = (74, 29, 122)
LIGHT = (201, 168, 240)
INK = (30, 41, 59)
MUTED = (100, 116, 139)
EMERALD = (16, 150, 105)
LOGO = Path(__file__).parent / "assets" / "sa_coparents_logo.png"
NOTE = (
    "Certificate of completion of the self-guided SA CoParents Self Journey. "
    "It is not a court-approved parenting course certificate and not legal advice."
)


class _CertPDF(FPDF):
    def footer(self):
        render_pdf_copyright(self)


def _centered(pdf: FPDF, y: float, text: str, style: str, size: float, color) -> None:
    pdf.set_xy(20, y)
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*color)
    pdf.cell(pdf.w - 40, size * 0.5, _safe(text), align="C")


def build_certificate_pdf(*, name: str, finished_iso: str, steps: List[str]) -> bytes:
    pdf = _CertPDF(orientation="L", unit="mm", format="Letter")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    w, h = pdf.w, pdf.h
    pdf.set_draw_color(*PURPLE)
    pdf.set_line_width(1.6)
    pdf.rect(8, 8, w - 16, h - 16)
    pdf.set_draw_color(*LIGHT)
    pdf.set_line_width(0.5)
    pdf.rect(12, 12, w - 24, h - 24)
    if LOGO.exists():
        pdf.image(str(LOGO), x=w / 2 - 22, y=15, w=44)

    _centered(pdf, 44, "CERTIFICATE OF COMPLETION", "B", 26, PURPLE)
    _centered(pdf, 58, "SA CoParents  ·  Self Journey", "", 11, MUTED)
    _centered(pdf, 72, "This certifies that", "I", 12, INK)
    _centered(pdf, 82, name, "B", 28, PURPLE)
    pdf.set_draw_color(*LIGHT)
    pdf.set_line_width(0.6)
    pdf.line(w / 2 - 75, 99, w / 2 + 75, 99)
    _centered(pdf, 104, "has completed every step of the self-guided SA CoParents Self Journey.", "", 12, INK)
    finished = datetime.fromisoformat(finished_iso)
    _centered(pdf, 113, f"Finished on {finished:%B} {finished.day}, {finished.year}", "B", 11, INK)

    col_x, top = (w / 2 - 92, w / 2 + 8), 128
    for i, step in enumerate(steps):
        x, y = col_x[i // 3], top + (i % 3) * 9
        pdf.set_draw_color(*EMERALD)
        pdf.set_line_width(0.9)
        pdf.line(x + 0.8, y + 3.8, x + 2.5, y + 5.5)
        pdf.line(x + 2.5, y + 5.5, x + 5.6, y + 1.6)
        pdf.set_xy(x + 7, y)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*INK)
        pdf.cell(78, 7, _safe(f"Step {i + 1}  ·  {step}"))

    pdf.set_xy(40, 168)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(w - 80, 4.4, _safe(NOTE), align="C")
    return bytes(pdf.output())
