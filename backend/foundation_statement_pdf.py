"""Foundation Statement PDF — a single-page, share-friendly artefact
composed from a parent's four Reflection prompts.

Rendered on-demand when a parent taps "Download PDF" or "Send to
co-parent / mediator" on `/my-plan` or `/reflection`.

Design choices:
  * One page, calm typography — meant to be forwarded before a
    mediation or first co-parenting conversation, not filed with
    a court.
  * Each of the four canonical prompts renders as its own labelled
    section (skipped when the parent left the box empty).
  * Always includes the six-caveat court-report disclaimer so a
    downstream reader can never mistake this for a clinical or
    adjudicative finding.
  * Provenance watermark on every page — author name + ISO UTC
    timestamp — so a recipient can trace which copy they received.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF

from court_report_disclaimer import (
    apply_professional_watermark,
    draw_court_report_disclaimer,
)
from pdf_base import render_pdf_copyright
from safety_assessment_pdf import _safe


# Ordered list of the four canonical Reflection prompts + their
# on-PDF labels. Legacy keys are appended AT THE END so pre-2026
# reflections still render something meaningful (they'll show under
# their raw key label — old reflections were rare and this is a
# graceful fallback rather than a first-class rendering).
_CANONICAL_PROMPTS: List[Tuple[str, str]] = [
    ("child_lens", "Through my child's eyes"),
    ("own_part", "My own part"),
    ("best_outcome", "My best-case outcome"),
    ("coparent_feedback", "Through my co-parent's eyes"),
]
_LEGACY_PROMPTS: List[Tuple[str, str]] = [
    ("worry", "What I'm worried about"),
    ("triggers", "My triggers"),
    ("calm_strategy", "How I stay calm"),
    ("appreciation", "What I appreciate"),
    ("release", "What I'm releasing"),
]


class _FoundationPDF(FPDF):
    """FPDF subclass that runs `_safe(...)` on every text cell so
    en-dashes / em-dashes / smart quotes never escape latin-1."""

    def cell(self, w=0, h=0, txt="", *args, **kwargs):  # type: ignore[override]
        if "text" in kwargs:
            kwargs["text"] = _safe(kwargs["text"])
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):  # type: ignore[override]
        if "text" in kwargs:
            kwargs["text"] = _safe(kwargs["text"])
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self) -> None:  # noqa: D401 — fpdf hook
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 130)
        self.cell(0, 6, "SA CoParents - Foundation Statement", ln=1, align="R")
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:  # noqa: D401 — fpdf hook
        render_pdf_copyright(self)


def _iso_utc(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _sections(reflection: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return ordered (label, text) pairs for the prompts the parent
    actually filled in. Canonical prompts first, then any legacy
    prompts that still hold content (defensive — a mixed dict from
    an older reflection is rendered rather than dropped)."""
    out: List[Tuple[str, str]] = []
    for key, label in _CANONICAL_PROMPTS + _LEGACY_PROMPTS:
        v = reflection.get(key)
        if isinstance(v, str) and v.strip():
            out.append((label, v.strip()))
    return out


def build_foundation_statement_pdf(
    *,
    author_name: str,
    reflection: Dict[str, Any],
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Render a one-page Foundation Statement PDF and return the raw
    bytes. Raises `ValueError` if the reflection contains no usable
    prompt content — callers should guard against empty sends so
    parents don't email a hollow document by accident."""
    sections = _sections(reflection or {})
    if not sections:
        raise ValueError("Reflection is empty — nothing to render.")

    pdf = _FoundationPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(26, 19, 48)
    pdf.cell(0, 10, "My Foundation Statement", ln=1)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(75, 69, 103)
    pdf.cell(0, 5, f"Written by {author_name}", ln=1)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(140, 140, 160)
    pdf.cell(0, 5, f"Prepared {_iso_utc(generated_at)}", ln=1)

    # Purpose strip — mediator-facing so they know what they're
    # holding. Neutral, non-adjudicative language on purpose.
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 5, "PURPOSE", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(75, 69, 103)
    pdf.multi_cell(
        0, 4.8,
        "A short reflection I wrote to prepare for our conversation. "
        "It captures how I'm thinking about our co-parenting right "
        "now — from my child's perspective, from my co-parent's "
        "perspective, and from my own. It is not a set of demands "
        "and it is not a court filing.",
    )

    pdf.ln(6)

    # Prompt sections
    for label, text in sections:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(61, 26, 120)
        pdf.cell(0, 5, label.upper(), ln=1)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(26, 19, 48)
        pdf.multi_cell(0, 5.4, text)
        pdf.ln(3)

    # Court-report disclaimer — one parent only, so the disclaimer's
    # "both parents participated" flag is False.
    pdf.ln(2)
    draw_court_report_disclaimer(
        pdf,
        author_name=author_name,
        both_parents=False,
    )

    # Watermark stamp — reuse the same helper the case-status PDF
    # uses so provenance formatting is identical across downloads.
    apply_professional_watermark(
        pdf,
        firm_name=author_name,
        downloaded_at_iso=_iso_utc(generated_at),
    )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


def foundation_statement_has_content(reflection: Optional[Dict[str, Any]]) -> bool:
    """Cheap guard for API endpoints: returns True iff the reflection
    holds at least one non-empty prompt string. Callers use this to
    reject empty send/download requests before spinning up the PDF."""
    if not isinstance(reflection, dict):
        return False
    for key, _label in _CANONICAL_PROMPTS + _LEGACY_PROMPTS:
        v = reflection.get(key)
        if isinstance(v, str) and v.strip():
            return True
    return False
