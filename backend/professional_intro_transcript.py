"""3-Minute Introduction to SA CoParents (for Professionals).

Static explainer document included as a companion PDF when a parent
emails a joint artefact (Report or Agreement) to a mediator, attorney,
therapist, or PFAL. Also downloadable directly from the Joint
Professional Report page.

Rationale for centralising the copy here:
  * Single source of truth for the transcript.
  * Both the PDF renderer AND the frontend explainer surface can import
    the same paragraphs, so the spoken/printed versions never drift.
  * When the copy changes, the PDF regenerates automatically.

The document is deliberately generic — it carries no user data, does
not require an active Compare share, and can be downloaded before any
consent is exchanged.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, INFO, OK,
    ORG_NAME, ORG_TAGLINE, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe,
)


PAGE_W = 210
LEFT_M = 15
RIGHT_M = 15
CONTENT_W = PAGE_W - LEFT_M - RIGHT_M


TITLE = "A 3-Minute Introduction to SA CoParents"
SUBTITLE = "For mediators, attorneys, therapists, and other professionals"

# Ordered list of paragraphs. Each entry is either a plain paragraph or a
# (heading, body) tuple used to render a bold callout heading above the
# body. Keeping this as data (not one big string) lets both the PDF and
# any future HTML surface iterate consistently.
PARAGRAPHS: List = [
    (
        None,
        "Hello. Thank you for the time. This short overview explains "
        "what SA CoParents is, how the documents in front of you were "
        "assembled, and — just as importantly — what they are not.",
    ),
    (
        "What SA CoParents is",
        "SA CoParents is a preparation platform for co-parents. It is "
        "not a custody evaluation service, a forensic assessment tool, "
        "or a substitute for legal or clinical advice. Its purpose is "
        "narrower and simpler: to help each parent organise their "
        "thinking about their child before they walk into your office, "
        "so the time you spend with them is more focused and more "
        "child-centred.",
    ),
    (
        "How parents use it",
        "Each parent works through the platform independently. They "
        "answer structured, guided prompts across areas such as "
        "communication, priorities, and household rhythms — and, where "
        "relevant, complete the Special Needs Co-Parenting Assessment "
        "covering their child's medical, educational (IEP / 504), and "
        "psychological needs. The platform then produces a private, "
        "individual set of insights for that parent, including a "
        "personal Foundation Statement, a Mediation Readiness profile, "
        "and an individual Co-Parenting Agreement draft. Nothing is "
        "shared with the other parent automatically.",
    ),
    (
        "How the joint views unlock",
        "Comparison views only unlock when both parents have actively "
        "consented to share through the app's Compare flow. That "
        "mutual consent — recorded, revocable, and time-stamped — is "
        "the gate that allows any joint artefact to exist.",
    ),
    (
        "The three joint artefacts",
        "First, the Shared Special Needs Report — a step-by-step "
        "side-by-side of both parents' answers across the pathways "
        "they selected, with an overall alignment percentage and the "
        "specific items where they align, differ, or need to fill gaps."
        "\n\nSecond, the Joint Co-Parenting Summary for Professional "
        "Review. It organises both parents' responses into neutral "
        "sections: shared child-centred priorities, medical needs, "
        "educational and IEP needs, psychological needs, consistency "
        "between households, communication concerns, areas of "
        "agreement, areas where perceptions differ, and topics that "
        "may benefit from professional discussion. Every row is "
        "phrased in neutral language."
        "\n\nThird, the Joint Co-Parenting Agreement Draft — a "
        "deterministic merger of both parents' individual agreement "
        "drafts. Clause by clause it shows what both parents already "
        "proposed and what only one parent proposed. Their exact "
        "wording is preserved on both sides.",
    ),
    (
        "Safety-screen privacy",
        "Where a parent has completed the Trauma-Informed Safety and "
        "Functioning Lens, only Finding 3 — Parenting-Plan "
        "Implications — is ever included in the joint artefacts. The "
        "underlying family-violence and trauma findings remain private "
        "to the parent who completed the screen.",
    ),
    (
        "In short",
        "These documents reflect what the parents said, not what "
        "SA CoParents or any professional has concluded. They are meant "
        "to accelerate your conversation, not replace it. Thank you.",
    ),
]

DISCLAIMER = (
    "SA CoParents is not a custody evaluation service, forensic "
    "assessment, clinical diagnosis, expert opinion, or recommendation "
    "to any court. The joint artefacts summarise the parents' own "
    "self-reported answers and are provided as preparation material only."
)


class _IntroPDF(FPDF):
    def __init__(self, *, generated_at: str):
        super().__init__()
        self._generated_at = generated_at
        self._is_cover = False

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        if self._is_cover:
            return
        self.set_fill_color(*SAND)
        self.rect(0, 0, PAGE_W, 22, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=3, w=16, h=16)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(32, 5)
        self.cell(0, 5, "SA CoParents - Introduction for Professionals", ln=1)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_MID)
        self.set_x(32)
        self.cell(0, 4, f"{ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(26)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            "Preparation resource - Not a custody evaluation, diagnosis, or "
            f"recommendation to any court - Generated {self._generated_at}",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


def build_professional_intro_pdf() -> bytes:
    """Render the 3-minute intro as a branded PDF and return raw bytes."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pdf = _IntroPDF(generated_at=now)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Title + subtitle.
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 8, TITLE)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(CONTENT_W, 5, SUBTITLE)
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(4)

    # Body paragraphs.
    for heading, body in PARAGRAPHS:
        if heading:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*INFO)
            pdf.set_x(LEFT_M)
            pdf.cell(0, 5, heading, ln=1)
            pdf.set_draw_color(*INFO)
            y = pdf.get_y()
            pdf.line(LEFT_M, y, LEFT_M + 30, y)
            pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(LEFT_M)
        # Split explicit \n\n boundaries so paragraph gaps render cleanly.
        for chunk in body.split("\n\n"):
            pdf.multi_cell(CONTENT_W, 5, chunk)
            pdf.ln(1)

    # Disclaimer callout.
    pdf.ln(3)
    pdf.set_fill_color(252, 237, 235)
    pdf.set_draw_color(*DANGER)
    pdf.set_line_width(0.4)
    banner_y = pdf.get_y()
    pdf.rect(LEFT_M, banner_y, CONTENT_W, 30, "DF")
    pdf.set_xy(LEFT_M + 4, banner_y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*DANGER)
    pdf.cell(0, 5, "Universal disclaimer", ln=1)
    pdf.set_xy(LEFT_M + 4, banner_y + 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(CONTENT_W - 8, 4.5, DISCLAIMER)

    # Trailing sign-off line.
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*OK)
    pdf.set_x(LEFT_M)
    pdf.multi_cell(
        CONTENT_W, 4.5,
        "Approximately 3 minutes read aloud - Same source of truth as "
        "the on-screen intro shown to parents in the app.",
    )
    pdf.set_text_color(*TEXT_DARK)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out


PROFESSIONAL_INTRO_FILENAME = "sacoparents-professional-intro.pdf"
