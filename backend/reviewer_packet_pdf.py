"""Reviewer Packet PDF — everything an independent reviewer needs to
evaluate the SA CoParents Family Violence and Communication Safety
Screen: current questions, scoring rules, methodology summary, and a
review checklist keyed to the MASIC-S coverage gaps.
"""
from __future__ import annotations

from typing import List

from fpdf import FPDF

from pdf_base import LOGO_PATH, _safe, _section_break


REVIEW_CHECKLIST = [
    "Is each Section-1 (immediate-safety) question worded to elicit truthful disclosure without leading?",
    "Are the questions culturally, linguistically, and reading-level accessible?",
    "Should any Section-1 item be reworded to distinguish coercive control from situational violence?",
    "Is 'any single yes' as the trigger for the No-Direct-Contact pathway too broad, too narrow, or appropriate?",
    "Is Section-2 (communication readiness) safe to score for a parent whose Section-1 raised flags? Or should it be gated?",
    "Do any items risk mutualizing abuse (implying the survivor is co-responsible)?",
    "Does the recommended output (pathway + PDF) risk being over-interpreted as clinical or evidentiary?",
    "Are the four communication pathways (No-direct / Structured written / Assisted / Cooperative) safely defined?",
]

MASIC_GAPS_TO_ADDRESS = [
    "Strangulation / choking (distinct item, not folded into 'physical harm')",
    "Weapons in the home / access to firearms",
    "Sexual coercion / non-consensual sexual acts",
    "Homicide threats and suicide threats (distinct from generic threats)",
    "Digital surveillance / device monitoring / location tracking as its own item",
    "Financial control / economic abuse",
    "Post-separation escalation (timing distinction)",
    "Substance abuse / intoxication during incidents",
    "Fear of consequences for disagreeing (currently reviewer-pending)",
    "Prior court involvement / protective orders (structured field, not free text)",
]


def _mcell(pdf: FPDF, h: float, text: str) -> None:
    """Wrapper around multi_cell that always resets x to the left margin
    after writing, so the next call starts fresh. fpdf2 no longer does
    this automatically when the text fits on a single line."""
    pdf.multi_cell(0, h, _safe(text))
    pdf.set_x(pdf.l_margin)


class _PacketPDF(FPDF):
    def header(self):
        if getattr(self, "_first_page", True):
            self._first_page = False
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(133, 126, 156)
        self.set_xy(self.l_margin, 8)
        self.cell(0, 3.6, _safe("SA CoParents · Reviewer Packet · Safety Screen v1.0"), ln=1)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(133, 126, 156)
        self.cell(0, 3, _safe(
            "Confidential draft for reviewer evaluation only - not for distribution to end users."
        ), align="C")
        self.set_xy(self.l_margin, -8)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 3, _safe(f"Page {self.page_no()}"), align="C")


def _numbered_bullet(pdf: _PacketPDF, num: int, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(61, 26, 120)
    pdf.cell(8, 5, _safe(f"{num}."))
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    _mcell(pdf, 5, (text))
    pdf.ln(0.6)


def _high_concern_flag(pdf: _PacketPDF, flagged: bool) -> None:
    if not flagged:
        return
    pdf.set_x(pdf.l_margin + 8)
    pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(176, 42, 42)
    pdf.cell(0, 3.5, _safe("high-concern trigger: yes triggers No-Direct-Contact pathway"), ln=1)
    pdf.set_text_color(30, 24, 54)


def build_reviewer_packet_pdf(*, generated_at: str) -> bytes:
    # Lazy import so this module stays cheap when no packet is requested.
    from safety_assessment_routes import (
        SECTION_1_QUESTIONS,
        SECTION_2_QUESTIONS,
    )

    pdf = _PacketPDF(orientation="P", unit="mm", format="Letter")
    pdf._first_page = True
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=18, top=20, right=18)
    pdf.add_page()

    # -------- Cover --------
    try:
        pdf.image(LOGO_PATH, x=pdf.l_margin, y=pdf.get_y(), w=22)
    except Exception:
        pass
    pdf.set_y(pdf.get_y() + 26)

    pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(133, 126, 156)
    pdf.cell(0, 3.6, _safe("REVIEWER PACKET - CONFIDENTIAL"), ln=1)
    pdf.set_font("Helvetica", "B", 20); pdf.set_text_color(30, 24, 54)
    _mcell(pdf, 8, ("Family Violence and Communication Safety Screen"))
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(75, 69, 103)
    _mcell(pdf, 5, (
        "This packet contains the complete current content of the SA CoParents "
        "Safety Screen for expert review by a domestic-violence advocate, "
        "forensic psychologist, and Texas family-law attorney. The screen is a "
        "self-administered educational tool and is NOT presented to users as a "
        "validated clinical instrument. Please review with that framing in mind."
    ))
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.cell(0, 5, _safe("Version:"), ln=1)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _safe("v1.0 - February 26, 2026"), ln=1)
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5, _safe("Packet generated:"), ln=1)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _safe(generated_at[:19].replace("T", " ")), ln=1)

    _section_break(pdf)

    # -------- How the screen works --------
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("How the screen currently works"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    _mcell(pdf, 5, (
        "Two sections. Section 1 (immediate safety) contains yes/no items, some of "
        "which are flagged 'high-concern' - any single YES answer to a high-concern "
        "item triggers the No-Direct-Contact pathway regardless of Section 2 answers. "
        "Section 2 (communication readiness) contains yes/no items about the user's "
        "current capacity to communicate constructively. The screen then maps the parent "
        "to one of four pathways: No-direct contact / Structured written / Assisted / "
        "Cooperative."
    ))
    pdf.ln(1)
    _mcell(pdf, 5, (
        "For Level 1 and Level 2 (highest-concern) results the app suppresses the AI "
        "communication coach and shows an anti-mutualization notice pointing to a "
        "DV advocate. A pre-screen 'Device Safety' banner and quick-exit button are "
        "shown to every user before they begin."
    ))

    # -------- Section 1 --------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Section 1 - Immediate safety items"), ln=1)
    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(75, 69, 103)
    _mcell(pdf, 4.5, (
        "'In the past 12 months, has your co-parent...' [Yes / No / Unsure]. Any single "
        "Yes on a high-concern item forces the No-Direct-Contact pathway."
    ))
    pdf.ln(1)
    for i, q in enumerate(SECTION_1_QUESTIONS, 1):
        _numbered_bullet(pdf, i, q["text"])
        _high_concern_flag(pdf, bool(q.get("high_concern")))

    # -------- Section 2 --------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Section 2 - Communication readiness items"), ln=1)
    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(75, 69, 103)
    _mcell(pdf, 4.5, (
        "'Right now, are you able to...' [Yes / No / Unsure]. These items only contribute "
        "to pathway selection when Section 1 has no high-concern triggers."
    ))
    pdf.ln(1)
    for i, q in enumerate(SECTION_2_QUESTIONS, 1):
        _numbered_bullet(pdf, i, q["text"])

    # -------- Review checklist --------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Review checklist for you (the reviewer)"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    _mcell(pdf, 5, (
        "Please give a written yes/no + short comment on each of the following. Your "
        "answers will inform whether items are approved as-is, reworded, or added."
    ))
    pdf.ln(1)
    for i, q in enumerate(REVIEW_CHECKLIST, 1):
        _numbered_bullet(pdf, i, q)

    # -------- MASIC-S gaps --------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("MASIC-S domains flagged as GAPS in the current screen"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    _mcell(pdf, 5, (
        "The MASIC-S (Holtzworth-Munroe, Beck & Applegate) was designed specifically to "
        "screen separating parents for IPV and mediation-safety concerns. The following "
        "domains from MASIC-S are NOT yet asked (or only partially asked) in the current "
        "SA CoParents screen. Please indicate for each whether it must be added and, if "
        "so, draft one or more items in wording you would sign off on."
    ))
    pdf.ln(1)
    for i, item in enumerate(MASIC_GAPS_TO_ADDRESS, 1):
        _numbered_bullet(pdf, i, item)

    # -------- Sign-off --------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(61, 26, 120)
    pdf.cell(0, 6, _safe("Reviewer sign-off"), ln=1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    _mcell(pdf, 5, (
        "By signing below, you confirm you have reviewed the content of this packet in "
        "your professional capacity. Your name, credentials, role, and review date will "
        "be published on the SA CoParents public methodology page in the interest of "
        "transparency. Your review does not constitute a clinical, legal, or evidentiary "
        "endorsement of the tool for any specific case."
    ))
    pdf.ln(4)
    for label in [
        "Reviewer full name and credentials:",
        "Professional role (DV advocate / forensic psychologist / family-law attorney / other):",
        "Organisation (optional):",
        "Scope of review (which sections / items):",
        "Review date:",
        "Attestation for public methodology page (1-2 sentences you're happy to publish):",
    ]:
        pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
        _mcell(pdf, 5, (label))
        pdf.set_draw_color(180, 174, 204); pdf.set_line_width(0.2)
        y = pdf.get_y() + 1
        pdf.line(pdf.l_margin, y + 6, pdf.w - pdf.r_margin, y + 6)
        pdf.line(pdf.l_margin, y + 12, pdf.w - pdf.r_margin, y + 12)
        pdf.set_y(y + 16)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5, _safe("Signature:"), ln=1)
    y = pdf.get_y() + 3
    pdf.line(pdf.l_margin, y + 6, pdf.w - pdf.r_margin, y + 6)

    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)
