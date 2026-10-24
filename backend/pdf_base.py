"""Leaf module: shared low-level PDF helpers used by every SA CoParents
report builder (`edu_deep_report`, `psych_deep_report`, `journey_pdf`,
`deep_dive_narrative`, …).

This module intentionally has ZERO project imports so it can sit at the
bottom of the import graph and be pulled in from anywhere without
forming a cycle.

Exports:
    LOGO_PATH        — absolute path to the branded logo used in headers.
    _safe(text)      — Latin-1-safe normaliser for fpdf2 output.
    _section_break(pdf)
                     — draw a subtle horizontal rule with vertical spacing.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")


def _safe(t: Any) -> str:
    """Return `t` coerced to a Latin-1-safe string. fpdf2's Helvetica
    core-font renderer only accepts Latin-1, so smart quotes / em-dashes /
    other Unicode gotchas would otherwise raise. We do a targeted
    replace of the common offenders then encode with `replace` errors
    to guarantee no crash on unexpected input."""
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


def _section_break(pdf) -> None:
    """Draw a subtle horizontal rule between logical sections of a
    report. Accepts any fpdf2 PDF instance — no type dep on `_PDF`."""
    pdf.ln(1.5)
    pdf.set_draw_color(220, 214, 232); pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(1.5)


_COPYRIGHT_URL = "https://sacoparentsapp.online"


def _copyright_line() -> str:
    """Copyright line with the current UTC year. "\u00a9" and "\u00b7" are Latin-1, so core fonts render them."""
    return f"\u00a9 {datetime.now(timezone.utc).year} SA CoParents \u00b7 sacoparentsapp.online \u00b7 All rights reserved."


def render_pdf_copyright(pdf) -> None:
    """
    Render the global copyright strip at the very bottom of the
    current PDF page. Called from every report's `footer()` method
    so it appears on EVERY page of EVERY generated report.

    Sits at 6mm from the bottom edge — under any existing footer
    text — in tiny italic grey. The centred text is overlaid with a
    clickable `pdf.link(...)` rectangle so on-screen PDF viewers
    (Preview, Acrobat, Chrome) open sacoparentsapp.online in a new
    tab when a reader clicks the line.
    """
    pdf._sacp_copyright_calls = getattr(pdf, "_sacp_copyright_calls", 0) + 1
    try:
        pdf.set_y(-6)
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(133, 126, 156)   # #857E9C
        safe_text = _safe(_copyright_line())
        # Snapshot the row's Y before we render so we can compute the
        # clickable rectangle *after* fpdf2 has centred the text.
        y_before = pdf.get_y()
        pdf.cell(0, 3, safe_text, align="C", ln=1)
        # Overlay a link rectangle covering the actual text width,
        # horizontally centred like the cell we just wrote. Width
        # is measured with fpdf2's `get_string_width` under the
        # same font state we just used.
        try:
            text_w = pdf.get_string_width(safe_text)
        except Exception:  # noqa: BLE001
            text_w = 90.0
        page_w = pdf.w - pdf.l_margin - pdf.r_margin
        link_x = pdf.l_margin + max(0.0, (page_w - text_w) / 2)
        pdf.link(link_x, y_before, text_w, 3, _COPYRIGHT_URL)
    except Exception:  # noqa: BLE001 — footer must never crash a report
        pass


def _install_copyright_on_every_page() -> None:
    """Safety net: any fpdf2 page whose footer didn't draw the copyright line gets it after the footer runs."""
    try:
        from fpdf import FPDF
    except ImportError:  # pragma: no cover
        return
    original = getattr(FPDF, "_render_footer", None)
    if original is None or getattr(original, "_sacp_wrapped", False):
        return

    def _render_footer(self):
        # Counted per footer call (not per page): a dry-run layout pass can render a footer whose output is discarded.
        calls_before = getattr(self, "_sacp_copyright_calls", 0)
        original(self)
        if getattr(self, "_sacp_copyright_calls", 0) == calls_before:
            self.in_footer = True
            try:
                render_pdf_copyright(self)
            finally:
                self.in_footer = False

    _render_footer._sacp_wrapped = True
    FPDF._render_footer = _render_footer


_install_copyright_on_every_page()

COPYRIGHT_MARK = "SA CoParents \u00b7 sacoparentsapp.online"


def stamp_copyright_on_pdf(pdf_bytes: bytes) -> bytes:
    """Overlay the copyright line (with its link) on every page of a finished PDF that doesn't already carry it.
    For PDFs not drawn with fpdf2 (image-made certificates, static downloads)."""
    import io
    from fpdf import FPDF
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject

    pt_per_mm = 72 / 25.4
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf_bytes)))
    stamped = 0
    for page in writer.pages:
        try:
            if COPYRIGHT_MARK in (page.extract_text() or ""):
                continue
        except Exception:  # noqa: BLE001 — image-only pages have no text layer
            pass
        box = page.mediabox
        left, bottom, width, height = float(box.left), float(box.bottom), float(box.width), float(box.height)
        overlay = FPDF(unit="pt", format=(width, height))
        overlay.set_auto_page_break(False)
        overlay.add_page()
        overlay.set_font("Helvetica", "I", 6.5)
        overlay.set_text_color(133, 126, 156)
        text = _copyright_line()
        text_w = overlay.get_string_width(text)
        overlay.set_xy(0, height - 6 * pt_per_mm)
        overlay.cell(width, 3 * pt_per_mm, text, align="C")
        overlay._sacp_copyright_calls = 1
        overlay.footer = lambda: setattr(overlay, "_sacp_copyright_calls", overlay._sacp_copyright_calls + 1)
        page.merge_translated_page(PdfReader(io.BytesIO(bytes(overlay.output()))).pages[0], left, bottom, over=True)
        x0, y0 = left + (width - text_w) / 2, bottom + 3 * pt_per_mm
        writer.add_annotation(page, DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (x0, y0, x0 + text_w, y0 + 3 * pt_per_mm)]),
            NameObject("/Border"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(0)]),
            NameObject("/A"): DictionaryObject({
                NameObject("/S"): NameObject("/URI"),
                NameObject("/URI"): TextStringObject(_COPYRIGHT_URL),
            }),
        }))
        stamped += 1
    if not stamped:
        return pdf_bytes
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
