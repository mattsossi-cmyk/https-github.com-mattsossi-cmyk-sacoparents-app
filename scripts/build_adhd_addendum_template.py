"""Interactive fillable "Special Education & ADHD Addendum" template.

This is the companion to the Co-Parenting Commitment Agreement — a shorter,
sharper document designed to be attached to an existing parenting plan
whenever the child has an IEP, ARD process, or ADHD medication routine.

The 25-item alignment scorer (see `edu-deep-2.0.0`) surfaces the parts of
co-parenting that are hurting the child's routine. This addendum turns
those insights into a concrete, signable list of rules both households
agree to hold.

Uses reportlab's AcroForm API so every blank line is a real editable
text field and every checkbox is a real clickable widget.

Run:
    python3 /app/scripts/build_adhd_addendum_template.py

Output:
    /app/frontend/public/downloads/coparent-adhd-addendum.pdf
"""
from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# Reuse the polished layout primitives from the commitment-agreement builder
# so both PDFs share brand voice.
import sys
sys.path.insert(0, "/app/scripts")

from build_commitment_agreement_fillable import (  # noqa: E402
    Form as CommitmentForm,
    MARGIN_L, MARGIN_R, MARGIN_BOTTOM, PAGE_W, PAGE_H,
    INK, INK_DIM, ACCENT, ACCENT_LIGHT, RULE, FIELD_BORDER, FIELD_BG,
)


class AddendumForm(CommitmentForm):
    """Override title metadata."""

    def __init__(self, out_path: str) -> None:
        super().__init__(out_path)
        self.c.setTitle("SA CoParents  Special Education & ADHD Addendum")
        self.c.setAuthor("SA CoParents")
        self.c.setSubject(
            "Fillable addendum locking in identical rules for IEP, ARD, "
            "and ADHD routines across two homes.",
        )

    def _page_header(self) -> None:
        # Rebrand the running header so it matches THIS document.
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(INK_DIM)
        self.c.drawString(MARGIN_L, PAGE_H - 12 * mm,
                         "SA CoParents  Special Education & ADHD Addendum")
        self.c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 12 * mm,
                              f"Page {self.page}")
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.3)
        self.c.line(MARGIN_L, PAGE_H - 14 * mm,
                    PAGE_W - MARGIN_R, PAGE_H - 14 * mm)


def build() -> str:
    out_path = "/app/frontend/public/downloads/coparent-adhd-addendum.pdf"
    f = AddendumForm(out_path)
    f._page_header()

    # ---------- Cover ----------
    f.ln(18)
    f.c.setFont("Helvetica-Bold", 24)
    f.c.setFillColor(ACCENT)
    f.c.drawString(MARGIN_L, f.y, "SA CoParents")
    f.ln(10)
    f.c.setFont("Helvetica-Bold", 20)
    f.c.drawString(MARGIN_L, f.y, "Special Education & ADHD")
    f.ln(9)
    f.c.drawString(MARGIN_L, f.y, "Co-Parenting Addendum")
    f.ln(12)
    f.body(
        "A short, sign-able addendum designed to attach to your existing parenting "
        "plan or commitment agreement. It locks in identical rules across both "
        "homes for the pieces of co-parenting that most affect a child with an IEP, "
        "an ADHD medication routine, or an ARD process."
    )
    f.body(
        "Fill this in AFTER completing the 25-item Educational Alignment Assessment. "
        "The parts you scored lowest are exactly the parts to prioritise here.",
        italic=True,
    )
    f.ln(2)
    f.callout(
        "This document is a planning tool between parents. It is not a court order "
        "or a binding legal agreement. If it is intended to modify a court order, "
        "have it reviewed by qualified family-law counsel and, when required, "
        "approved by the court."
    )
    f.ln(4)
    f.fill_line("Prepared for (child's name): ", full_width=True)
    f.fill_line("Date prepared: ", field_w_mm=80)
    f.fill_line("Alignment score from Part 3 (IEP/ARD): ", field_w_mm=30)
    f.fill_line("Alignment score from Part 4 (ADHD): ",   field_w_mm=30)

    # ==================================================================
    # SECTION 1 - IEP & ARD MANAGEMENT
    # ==================================================================
    f.new_page(); f.h1("1. IEP & ARD Management")
    f.body("We agree to the following operating rules for our child's IEP:")
    f.checkbox("Both parents receive the current IEP document within 24 hours of any revision.")
    f.checkbox("Both parents are notified of ARD meetings at least 10 school days in advance.")
    f.checkbox("Whenever practical, both parents attend ARD meetings together (or by video / phone) and coordinate positions in advance.")
    f.checkbox("If we disagree with a school recommendation, we discuss it BEFORE the ARD, not during.")
    f.checkbox("We share every teacher, therapist, and diagnostician email within 48 hours.")
    f.checkbox("We use a single shared digital folder (Google Drive / Dropbox / co-parenting app) for all IEP paperwork.")
    f.ln(2)
    f.h3("Shared IEP-document folder")
    f.fill_line("Location / link: ", full_width=True)
    f.fill_line("Parent 1 access confirmed by: ", field_w_mm=90)
    f.fill_line("Parent 2 access confirmed by: ", field_w_mm=90)
    f.ln(2)
    f.h3("Escalation for disagreements")
    f.body("If we cannot agree on an IEP / ARD position, we will:")
    f.checkbox("Consult the child's teacher(s) and the school counsellor first.")
    f.checkbox("Consult a private educational diagnostician or Special-Ed advocate.")
    f.checkbox("Take the disagreement to mediation before requesting a formal ARD dispute review.")
    f.multi_line_field("Named advocate / mediator (if any)", lines=2)

    # ==================================================================
    # SECTION 2 - ACCOMMODATIONS AT HOME
    # ==================================================================
    f.new_page(); f.h1("2. Accommodations Held in Both Homes")
    f.body(
        "Classroom accommodations only work if they extend into homework, "
        "downtime, and daily life. We agree to hold the following identically:"
    )
    f.checkbox_grid([
        "Extra time on written tasks",
        "Frequent movement / sensory breaks",
        "Visual schedules and checklists",
        "Written instructions given step-by-step",
        "Reduced-distraction workspace at homework time",
        "Noise-cancelling headphones or fidget tools available",
        "Consistent bedtime and wake-time on school nights",
        "Screen-time / device limits during school week",
    ])
    f.checkbox("Other accommodation")
    f.fill_line("Other:", full_width=True)
    f.multi_line_field("Homework-time rules both households will honour", lines=3)

    # ==================================================================
    # SECTION 3 - ADHD MEDICATION
    # ==================================================================
    f.new_page(); f.h1("3. ADHD Medication Coordination")
    f.callout(
        "Medication decisions are made by the prescribing clinician, not by "
        "either parent unilaterally. This section records how we coordinate "
        "what the clinician has already prescribed, not whether to prescribe."
    )
    f.ln(2)
    f.h3("Prescribing clinician")
    f.fill_line("Name: ",  full_width=True)
    f.fill_line("Phone: ", field_w_mm=60)
    f.fill_line("Email: ", full_width=True)
    f.ln(2)
    f.h3("Medication + dose")
    f.table(
        ["Medication", "Dose", "Time(s) given", "Household that fills"],
        rows=4, col_widths_mm=[45, 30, 45, 54], row_height_mm=10,
    )
    f.h3("Refill responsibility")
    f.checkbox("Parent 1 fills the prescription each month.")
    f.checkbox("Parent 2 fills the prescription each month.")
    f.checkbox("We alternate months; the parent whose fill is due notifies the other 5 days before pickup.")
    f.checkbox("Any missed or delayed dose is reported to the other parent within 12 hours.")
    f.ln(2)
    f.h3("Cross-home reporting rules")
    f.checkbox("Side effects or behaviour changes are reported between us BEFORE we report them to the doctor, so we present a unified observation.")
    f.checkbox("We never adjust the dose without the prescriber's written confirmation to both parents.")
    f.multi_line_field(
        "Side-effects watch-list (what we'll each notice and share)", lines=3,
    )

    # ==================================================================
    # SECTION 4 - TRANSITIONS
    # ==================================================================
    f.new_page(); f.h1("4. Transitions & Executive-Function Support")
    f.body(
        "Abrupt transitions can trigger ADHD dysregulation. We agree to the "
        "following transition rules for exchanges and school-to-home shifts:"
    )
    f.checkbox("A 24-hour reminder is sent before any exchange or schedule change.")
    f.checkbox("Backpack, medication, and specialised gear travel with the child at every exchange - checked visually by BOTH parents.")
    f.checkbox("Exchanges are calm and short - disputes are discussed in writing later, never in front of the child.")
    f.checkbox("If our child is dysregulated at pickup, we take 10 minutes to co-regulate before demanding compliance or homework.")
    f.ln(2)
    f.h3("Gear that must travel between homes")
    f.checkbox_grid([
        "Homework binder / school folder",
        "Fidgets, chewelry, sensory tools",
        "Noise-cancelling headphones",
        "Weekly medication tray or pillbox",
        "Preferred stuffed / comfort object",
        "IEP-linked accommodations kit",
    ])
    f.multi_line_field("Other gear / notes", lines=2)

    # ==================================================================
    # SECTION 5 - COMMUNICATION RULES
    # ==================================================================
    f.new_page(); f.h1("5. Communication Between Us")
    f.h3("Primary channel")
    f.checkbox("Text message")
    f.checkbox("Email")
    f.checkbox("Co-parenting application (name below)")
    f.fill_line("App / channel name: ", full_width=True)
    f.h3("Response times")
    f.fill_line("Routine child matters: within ",       field_w_mm=25)
    f.fill_line("Time-sensitive school matters: within ", field_w_mm=25)
    f.body("Medical / safety emergencies: as soon as reasonably possible.")
    f.h3("Content rules")
    f.checkbox("Every message names the child, not the other parent.")
    f.checkbox("Every message is brief, informative, and free of blame.")
    f.checkbox("Adult grievances are kept out of any communication that touches school or medical topics.")
    f.multi_line_field("Additional rules we want to hold", lines=3)

    # ==================================================================
    # SECTION 6 - REVIEW & SIGNATURES
    # ==================================================================
    f.new_page(); f.h1("6. Review & Signatures")
    f.body(
        "We will review this addendum together at least annually, and any time "
        "there is a significant change in medication, diagnosis, or educational "
        "placement."
    )
    f.checkbox("At the annual ARD meeting.")
    f.checkbox("Every school year in September.")
    f.checkbox("Whenever medication is added, changed, or discontinued.")
    f.checkbox("Whenever either parent requests a review in writing.")
    f.ln(4)
    f.signature_block("Parent 1")
    f.signature_block("Parent 2")

    f.save()
    return out_path


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p}")
