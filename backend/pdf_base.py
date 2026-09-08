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


_COPYRIGHT_LINE = "(c) 2026 sacoparentsalign.com - All rights reserved."
_COPYRIGHT_URL = "https://sacoparentsalign.com"


def render_pdf_copyright(pdf) -> None:
    """
    Render the global copyright strip at the very bottom of the
    current PDF page. Called from every report's `footer()` method
    so it appears on EVERY page of EVERY generated report.

    Sits at 6mm from the bottom edge — under any existing footer
    text — in tiny italic grey. The centred text is overlaid with a
    clickable `pdf.link(...)` rectangle so on-screen PDF viewers
    (Preview, Acrobat, Chrome) open sacoparentsalign.com in a new
    tab when a reader clicks the line.
    """
    try:
        pdf.set_y(-6)
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(133, 126, 156)   # #857E9C
        safe_text = _safe(_COPYRIGHT_LINE)
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
