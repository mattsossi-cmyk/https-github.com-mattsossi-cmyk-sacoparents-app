"""Interactive fillable "Co-Parenting Psychological Alignment Framework".

The paper companion to the 25-item Psychological Deep Dive v2. Same shape
as the Educational Assessment / ADHD Addendum PDFs so all three feel like
part of one family.

Run:
    python3 /app/scripts/build_psychological_alignment_framework.py

Output:
    /app/frontend/public/downloads/coparenting_psychological_alignment_framework.pdf
"""
from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

import sys
sys.path.insert(0, "/app/scripts")

from build_commitment_agreement_fillable import (  # noqa: E402
    Form as CommitmentForm,
    MARGIN_L, MARGIN_R, MARGIN_BOTTOM, PAGE_W, PAGE_H,
    INK, INK_DIM, ACCENT, ACCENT_LIGHT, RULE, FIELD_BORDER, FIELD_BG,
)


class FrameworkForm(CommitmentForm):
    def __init__(self, out_path: str) -> None:
        super().__init__(out_path)
        self.c.setTitle("SA CoParents  Co-Parenting Psychological Alignment Framework")
        self.c.setAuthor("SA CoParents")
        self.c.setSubject(
            "Fillable 25-item psychological co-parenting alignment framework "
            "with tailored next-steps by band.",
        )

    def _page_header(self) -> None:
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(INK_DIM)
        self.c.drawString(MARGIN_L, PAGE_H - 12 * mm,
                         "SA CoParents  Psychological Alignment Framework")
        self.c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 12 * mm,
                              f"Page {self.page}")
        self.c.setStrokeColor(RULE); self.c.setLineWidth(0.3)
        self.c.line(MARGIN_L, PAGE_H - 14 * mm,
                    PAGE_W - MARGIN_R, PAGE_H - 14 * mm)

    def score_row(self, prompt: str) -> None:
        """A single-line prompt + 5 tiny checkboxes (0-4) + N/A."""
        self.need_space(11)
        # prompt
        self.c.setFont("Helvetica", 10)
        self.c.setFillColor(INK)
        wrap_x = MARGIN_L
        for i, line in enumerate(_wrap_helper(prompt, PAGE_W - MARGIN_L - MARGIN_R - 60 * mm, self.c)):
            self.c.drawString(wrap_x, self.y, line)
            if i == 0:
                # First line: place the checkbox row aligned to the right
                x = PAGE_W - MARGIN_R - 56 * mm
                cbox_size = 4 * mm
                for opt in [0, 1, 2, 3, 4, "na"]:
                    self.c.acroForm.checkbox(
                        name=self._fname(f"cb_{opt}"),
                        tooltip=f"Rating: {opt}",
                        x=x, y=self.y - 1 * mm,
                        size=cbox_size,
                        borderColor=ACCENT, fillColor=None,
                        borderStyle="solid", borderWidth=1, forceBorder=True,
                        checked=False,
                    )
                    self.c.setFont("Helvetica", 8)
                    self.c.setFillColor(INK_DIM)
                    label = "N/A" if opt == "na" else str(opt)
                    self.c.drawString(x + cbox_size + 0.5 * mm,
                                     self.y - 0.5 * mm, label)
                    self.c.setFont("Helvetica", 10)
                    self.c.setFillColor(INK)
                    x += 9 * mm
            self.y -= 4.5 * mm
        self.ln(1)


def _wrap_helper(text: str, max_w: float, c) -> list:
    words = text.split(" ")
    out, line = [], ""
    for w in words:
        cand = f"{line} {w}".strip()
        if c.stringWidth(cand, "Helvetica", 10) <= max_w or not line:
            line = cand
        else:
            out.append(line); line = w
    if line:
        out.append(line)
    return out or [""]


PARTS = [
    ("1. Emotional Regulation Between Parents",
     "How well both adults manage their own emotions in the child's presence and around each other.",
     [
        "We keep our own frustration, anger, or sadness in check when we're with the children.",
        "We pause and take a breath before responding when the other parent says something that upsets us.",
        "We take responsibility for our own emotional reactions rather than blaming the other parent for how we feel.",
        "We recognise when we're too heated for a conversation and postpone it rather than pushing through in front of the child.",
        "We repair after a disagreement so the tension doesn't linger in the child's emotional atmosphere.",
     ]),
    ("2. The Child's Emotional Environment",
     "The emotional climate the child actually feels moving between homes.",
     [
        "Our child feels safe expressing sadness, worry, or anger to EITHER parent without needing to hide it.",
        "Our child never feels caught in the middle of a disagreement or asked to take sides.",
        "Our child sees adults handling stress calmly and constructively in both homes.",
        "Our child has predictable emotional routines (a listening adult, a comfort item, a bedtime wind-down) in both homes.",
        "Our child is allowed to love and enjoy time with the other parent without feeling disloyal.",
     ]),
    ("3. Therapy & Mental-Health Coordination",
     "How well both parents support and coordinate the child's counselling, therapy, and mental-health care.",
     [
        "Both parents actively support our child's therapy or counselling - attending, funding, reinforcing at home.",
        "We share therapist recommendations, session summaries, and homework between homes within a reasonable time.",
        "We hold the same house rules that the therapist recommends (reflection time, feelings vocabulary, coping toolkit) in both households.",
        "We coordinate psychiatric medication doses, timings, and refills so the child's routine never lapses between houses.",
        "We never criticise the therapist, the diagnosis, or the treatment plan in front of the child.",
     ]),
    ("4. Trauma, Grief & Attachment",
     "How we protect the child's attachment security through big transitions and any earlier losses.",
     [
        "We recognise the separation itself as a loss for our child and give them permission to grieve it.",
        "Reunions after time apart are calm, warm, and unhurried - not filled with questions about the other parent's household.",
        "We keep transitions between homes emotionally soft (goodbye hugs, a comfort object, a predictable handoff).",
        "We are alert to signs of anxiety, regression, sleep changes, or withdrawal, and we alert one another when we notice them.",
        "We DO NOT interrogate the child about the other household or use them as a source of information about the other parent.",
     ]),
    ("5. Modelling Emotional Health for the Child",
     "The emotional patterns the child sees us modelling every day - because they will inherit them.",
     [
        "We speak about the other parent with respect (or neutrally) even when the child is not obviously listening.",
        "We name our own emotions out loud (\"I'm feeling frustrated, I'm going to step outside\") so the child sees emotional literacy modelled.",
        "We each take care of our own mental health - therapy, exercise, sleep, community - so the child sees adults seeking help without shame.",
        "We celebrate the child's emotional growth (naming feelings, asking for help, apologising) in both homes.",
        "We forgive our co-parent when they slip up, the same way we want the child to learn to forgive.",
     ]),
]


def build() -> str:
    out_path = "/app/frontend/public/downloads/coparenting_psychological_alignment_framework.pdf"
    f = FrameworkForm(out_path)
    f._page_header()

    # ---------- Cover ----------
    f.ln(18)
    f.c.setFont("Helvetica-Bold", 24); f.c.setFillColor(ACCENT)
    f.c.drawString(MARGIN_L, f.y, "SA CoParents"); f.ln(10)
    f.c.setFont("Helvetica-Bold", 20)
    f.c.drawString(MARGIN_L, f.y, "Co-Parenting Psychological"); f.ln(9)
    f.c.drawString(MARGIN_L, f.y, "Alignment Framework"); f.ln(12)
    f.body(
        "A 25-item framework across five emotional-alignment parts, designed "
        "for parents whose child has therapy, trauma, attachment, medication, "
        "or mental-health needs. Each parent scores independently on a 0-4 "
        "scale; totals surface a three-band picture of the emotional climate "
        "the child feels across both homes."
    )
    f.ln(2)
    f.callout(
        "Scoring scale: 0 Never / High Conflict  ·  1 Seldom  ·  2 Sometimes  "
        "·  3 Often  ·  4 Always / Very Consistent  ·  N/A doesn't apply.\n\n"
        "Bands: 81-100 High Alignment  ·  51-80 Moderate Alignment  ·  "
        "0-50 Low Alignment.  Every item you score N/A is pro-rated out of "
        "the total, so a partial completion isn't penalised."
    )
    f.ln(4)
    f.fill_line("Prepared for (child's name): ", full_width=True)
    f.fill_line("Date completed: ", field_w_mm=80)
    f.fill_line("Completed by (parent): ", full_width=True)

    # ---------- The 25 items ----------
    for title, purpose, items in PARTS:
        f.new_page()
        f.h1(title)
        f.body(purpose, italic=True)
        f.ln(2)
        for prompt in items:
            f.score_row(prompt)

    # ---------- Results ----------
    f.new_page(); f.h1("Your Score & Interpretation")
    f.h3("Sum of each part")
    f.table(
        ["Part", "Raw score", "Items answered", "N/A count", "% aligned"],
        rows=5, col_widths_mm=[68, 25, 30, 25, 26], row_height_mm=10,
    )
    f.h3("Overall total")
    f.fill_line("Grand total (0-100): ", field_w_mm=30)
    f.fill_line("Number answered (out of 25): ", field_w_mm=30)
    f.fill_line("Overall percentage: ", field_w_mm=30)
    f.ln(2)
    f.h3("Band")
    f.checkbox("High Alignment (81-100) - Collaborative emotional co-parenting")
    f.checkbox("Moderate Alignment (51-80) - Inconsistent emotional support")
    f.checkbox("Low Alignment (0-50) - High conflict / fractured emotional environment")
    f.ln(2)
    f.h3("What we will do about it")
    f.multi_line_field("Two lowest-scoring parts we will target this month", lines=3)
    f.multi_line_field("One rule we will hold identically across both homes for 30 days", lines=2)
    f.multi_line_field("Professional we will consult (therapist / coordinator / advocate)", lines=2)

    # ---------- Sign ----------
    f.new_page(); f.h1("Sign & Review")
    f.body(
        "This framework is a planning tool between parents. Completing it "
        "does not create a court order or a binding legal agreement. "
        "Consult qualified professionals for decisions that affect your child."
    )
    f.ln(4)
    f.signature_block("Parent 1")
    f.signature_block("Parent 2")

    f.save()
    return out_path


if __name__ == "__main__":
    print(f"Wrote {build()}")
