"""Shared signature lines (with optional typed e-signature) + general US notary acknowledgment pages."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF

from pdf_base import _safe

INK = (30, 41, 59)
MUTED = (100, 116, 139)
PURPLE = (74, 37, 116)
GREEN = (46, 125, 50)
SIGN_NOTE = (
    "Signing or notarizing this document confirms who signed it. It does not make it a court order or a "
    "legally binding agreement unless a court approves it. Not legal advice."
)
INK_NOTE = "Print these pages and sign in ink. If you are having this notarized, sign in front of the notary."
NOTARY_NOTE = (
    "General acknowledgment form for use in any U.S. state. If your state requires different wording, "
    "the notary may attach their own state certificate instead."
)


def _when(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _title(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*PURPLE)
    pdf.cell(0, 8, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _small(pdf: FPDF, text: str, rgb=MUTED, style: str = "") -> None:
    pdf.set_font("Helvetica", style, 8.5)
    pdf.set_text_color(*rgb)
    pdf.multi_cell(pdf.epw, 4.4, _safe(text), new_x="LMARGIN", new_y="NEXT")


def _blank(pdf: FPDF, x: float, y: float, w: float, label: str, value: str = "") -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*MUTED)
    lw = pdf.get_string_width(label) + 2
    pdf.set_xy(x, y)
    pdf.cell(lw, 6, _safe(label))
    pdf.set_draw_color(*MUTED)
    pdf.line(x + lw, y + 5.6, x + w, y + 5.6)
    if value:
        pdf.set_xy(x + lw + 1, y)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*INK)
        pdf.cell(w - lw - 1, 5.4, _safe(value))


def _signer(pdf: FPDF, signer: Dict[str, Any]) -> None:
    if pdf.get_y() > pdf.h - 70:
        pdf.add_page()
    esign = signer.get("esign")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, _safe(signer["role"]), new_x="LMARGIN", new_y="NEXT")
    x, y, w = pdf.l_margin, pdf.get_y() + 2, pdf.epw
    _blank(pdf, x, y, w, "Printed full legal name:", esign["name"] if esign else "")
    _blank(pdf, x, y + 11, w * 0.62, "Signature:", f"/s/ {esign['name']}" if esign else "")
    _blank(pdf, x + w * 0.66, y + 11, w * 0.34, "Date:", _when(esign["at"]) if esign else "")
    pdf.set_xy(x, y + 20)
    if esign:
        _small(pdf, f"Typed electronic signature added in SA CoParents on {_when(esign['at'])} "
                    f"at {datetime.fromisoformat(esign['at']):%H:%M} UTC.", GREEN, "I")
    pdf.ln(2)


def _notary(pdf: FPDF, role: str) -> None:
    if pdf.get_y() > pdf.h - 112:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, _safe(f"Notary acknowledgment  ·  {role}"), new_x="LMARGIN", new_y="NEXT")
    x, y, w = pdf.l_margin, pdf.get_y() + 1, pdf.epw
    _blank(pdf, x, y, w * 0.48, "State of:")
    _blank(pdf, x + w * 0.52, y, w * 0.48, "County of:")
    pdf.set_xy(x, y + 10)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(w, 5.6, _safe(
        "On this ______ day of ____________________, 20____, before me, ____________________________ "
        "(name of notary), personally appeared ____________________________, who proved to me on the basis "
        "of satisfactory evidence to be the person whose name is signed on this document, and acknowledged "
        "that they signed it voluntarily."
    ), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 6, "WITNESS my hand and official seal.", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 2
    lw = w - 50
    _blank(pdf, x, y, lw, "Notary Public signature:")
    _blank(pdf, x, y + 10, lw, "Printed name:")
    _blank(pdf, x, y + 20, lw, "My commission expires:")
    _blank(pdf, x, y + 30, lw, "Commission number (if any):")
    pdf.set_draw_color(*MUTED)
    pdf.rect(x + w - 44, y, 44, 38)
    pdf.set_xy(x + w - 44, y + 16)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(44, 5, "Notary seal", align="C")
    pdf.set_xy(x, y + 42)


def render_sign_and_notary(pdf: FPDF, signers: List[Dict[str, Any]]) -> None:
    """Signature page (one block per signer) followed by a notary acknowledgment page (one per signer)."""
    pdf.add_page()
    _title(pdf, "Signatures")
    _small(pdf, SIGN_NOTE, INK, "B")
    pdf.ln(1)
    _small(pdf, INK_NOTE)
    for s in signers:
        _signer(pdf, s)
    pdf.add_page()
    _title(pdf, "Notary Acknowledgment")
    _small(pdf, NOTARY_NOTE)
    for s in signers:
        _notary(pdf, s["role"])
