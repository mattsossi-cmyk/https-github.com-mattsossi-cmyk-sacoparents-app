"""One-off generator for the Co-Parenting Commitment Agreement template.

Not part of the SA CoParents app codebase — a standalone, fillable
nine-ish-page PDF the user can hand to ChatGPT alongside both parents'
Foundation Statements to reconcile them.

Run:
    python3 /app/scripts/build_commitment_agreement_template.py

Output:
    /app/frontend/public/downloads/coparent-commitment-agreement.pdf
"""
from __future__ import annotations

from fpdf import FPDF


# ---------------------------------------------------------------------------
# Layout constants (mm, A4 assumed)
# ---------------------------------------------------------------------------
MARGIN_LR = 16
MARGIN_TOP = 18
MARGIN_BOTTOM = 20

INK = (26, 19, 48)          # near-black purple
INK_DIM = (75, 69, 103)
ACCENT = (61, 26, 120)      # SA CoParents purple
ACCENT_LIGHT = (245, 241, 251)
RULE = (214, 207, 232)
CHECKBOX_FG = (61, 26, 120)


class AgreementPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM)
        self.set_margins(MARGIN_LR, MARGIN_TOP, MARGIN_LR)
        # Fallback fonts — no external font files needed
        self._font = "Helvetica"

    # Helvetica core font is Latin-1 only. Strip curly quotes / dashes so
    # we don't need to ship an embedded Unicode TTF.
    @staticmethod
    def _latin(text: str) -> str:
        return (
            text
            .replace("\u2014", "-")    # em dash
            .replace("\u2013", "-")    # en dash
            .replace("\u2018", "'")    # left single quote
            .replace("\u2019", "'")    # right single quote
            .replace("\u201C", '"')    # left double quote
            .replace("\u201D", '"')    # right double quote
            .replace("\u2026", "...")  # ellipsis
            .replace("\u00A0", " ")    # non-breaking space
        )

    def cell(self, *args, **kwargs):  # type: ignore[override]
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = self._latin(kwargs["text"])
        elif len(args) >= 3 and isinstance(args[2], str):
            args = (args[0], args[1], self._latin(args[2]), *args[3:])
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):  # type: ignore[override]
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = self._latin(kwargs["text"])
        elif len(args) >= 3 and isinstance(args[2], str):
            args = (args[0], args[1], self._latin(args[2]), *args[3:])
        return super().multi_cell(*args, **kwargs)

    def header(self) -> None:  # noqa: D401
        if self.page_no() == 1:
            return
        self.set_y(8)
        self.set_font(self._font, "", 8)
        self.set_text_color(*INK_DIM)
        self.cell(0, 4, "SA CoParents  Co-Parenting Commitment Agreement", align="L")
        self.set_x(-MARGIN_LR - 25)
        self.cell(25, 4, f"Page {self.page_no()}", align="R")
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(MARGIN_LR, 14, self.w - MARGIN_LR, 14)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font(self._font, "I", 7.5)
        self.set_text_color(*INK_DIM)
        self.cell(0, 3.5,
                 "This template is a child-focused planning document. "
                 "It is not a court order or a binding legal agreement. "
                 "Consult a qualified family-law attorney where required.",
                 align="C")

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------
    def h1(self, text: str) -> None:
        self.ln(2)
        self.set_font(self._font, "B", 20)
        self.set_text_color(*ACCENT)
        self.multi_cell(0, 8.5, text)
        self.ln(1)

    def h2(self, text: str) -> None:
        # Add a bit of top padding, avoid ugly page-breaks
        if self.get_y() > self.h - MARGIN_BOTTOM - 25:
            self.add_page()
        self.ln(3)
        self.set_font(self._font, "B", 13)
        self.set_text_color(*ACCENT)
        self.cell(0, 6.5, text)
        self.ln(7)
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        self.line(MARGIN_LR, self.get_y() - 1.5,
                  MARGIN_LR + 40, self.get_y() - 1.5)
        self.ln(1)

    def h3(self, text: str) -> None:
        self.ln(1.5)
        self.set_font(self._font, "B", 10.5)
        self.set_text_color(*INK)
        self.multi_cell(0, 5, text)
        self.ln(0.5)

    def body(self, text: str, italic: bool = False) -> None:
        self.set_font(self._font, "I" if italic else "", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5, text)
        self.ln(0.5)

    def hint(self, text: str) -> None:
        self.set_font(self._font, "I", 9)
        self.set_text_color(*INK_DIM)
        self.multi_cell(0, 4.5, text)
        self.ln(0.5)

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------
    def checkbox(self, label: str, indent: float = 0) -> None:
        """A single left-column checkbox row."""
        if self.get_y() > self.h - MARGIN_BOTTOM - 8:
            self.add_page()
        x = MARGIN_LR + indent
        y = self.get_y() + 0.6
        # Square
        self.set_draw_color(*CHECKBOX_FG)
        self.set_line_width(0.3)
        self.rect(x, y, 3.2, 3.2)
        # Label
        self.set_xy(x + 5.2, y - 0.8)
        self.set_font(self._font, "", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5, label)
        self.ln(0.5)

    def checkbox_grid(self, items, cols: int = 2) -> None:
        """Two-column checkbox layout for compact lists."""
        # Fall back to single-column for very long labels
        col_width = (self.w - 2 * MARGIN_LR) / cols
        i = 0
        while i < len(items):
            if self.get_y() > self.h - MARGIN_BOTTOM - 8:
                self.add_page()
            y_start = self.get_y()
            row_max_lines = 1
            for c in range(cols):
                if i + c >= len(items):
                    break
                x = MARGIN_LR + c * col_width
                # square
                self.set_draw_color(*CHECKBOX_FG)
                self.set_line_width(0.3)
                self.rect(x, y_start + 0.6, 3.2, 3.2)
                self.set_xy(x + 5.0, y_start - 0.4)
                self.set_font(self._font, "", 10)
                self.set_text_color(*INK)
                # constrain to column width minus checkbox padding
                self.multi_cell(col_width - 6.5, 4.6, items[i + c])
                row_max_lines = max(
                    row_max_lines,
                    (self.get_y() - y_start) / 4.6,
                )
            i += cols
            # advance to the tallest row
            self.set_y(y_start + max(5.2, row_max_lines * 4.7 + 0.6))

    def fill_line(self, label: str, width_mm: float = None,
                  full_width: bool = False) -> None:
        """A label followed by an underlined blank for hand-writing (or a
        clear anchor for ChatGPT to slot text into)."""
        if self.get_y() > self.h - MARGIN_BOTTOM - 10:
            self.add_page()
        self.set_font(self._font, "", 10)
        self.set_text_color(*INK)
        label_w = self.get_string_width(label) + 2
        x = MARGIN_LR
        y = self.get_y() + 4
        self.set_xy(x, self.get_y())
        self.cell(label_w, 5, label)
        # Underline
        start_x = x + label_w
        end_x = (self.w - MARGIN_LR) if full_width else min(
            self.w - MARGIN_LR, start_x + (width_mm or 90),
        )
        self.set_draw_color(*RULE)
        self.set_line_width(0.35)
        self.line(start_x, y + 1, end_x, y + 1)
        self.ln(6)

    def multi_line_field(self, label: str, lines: int = 3) -> None:
        """A labelled multi-line write-in area."""
        self.set_font(self._font, "", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5, label)
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        for _ in range(lines):
            if self.get_y() > self.h - MARGIN_BOTTOM - 8:
                self.add_page()
            y = self.get_y() + 5
            self.line(MARGIN_LR, y, self.w - MARGIN_LR, y)
            self.ln(6)
        self.ln(1)

    def table(self, headers, rows: int = 4,
              col_widths=None, row_height: float = 8.0) -> None:
        """A simple bordered table with header row + N empty rows."""
        if col_widths is None:
            total = self.w - 2 * MARGIN_LR
            col_widths = [total / len(headers)] * len(headers)
        # Header
        self.set_font(self._font, "B", 9.5)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(*ACCENT)
        self.set_draw_color(*ACCENT)
        y_start = self.get_y() + 1
        self.set_y(y_start)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, "  " + h, border=1, fill=True)
        self.ln(6)
        # Body
        self.set_font(self._font, "", 9.5)
        self.set_text_color(*INK)
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(*RULE)
        for _ in range(rows):
            if self.get_y() > self.h - MARGIN_BOTTOM - row_height:
                self.add_page()
            for w in col_widths:
                self.cell(w, row_height, "", border=1)
            self.ln(row_height)
        self.ln(2)

    def callout(self, text: str) -> None:
        self.ln(1)
        y0 = self.get_y()
        self.set_fill_color(*ACCENT_LIGHT)
        self.set_draw_color(*RULE)
        self.set_line_width(0.3)
        # Reserve space then render text on top
        self.set_font(self._font, "", 9.5)
        self.set_text_color(*INK)
        # Estimate lines
        text_w = self.w - 2 * MARGIN_LR - 8
        # Draw a soft box behind
        # Compute height by measuring
        temp_x, temp_y = self.get_x(), self.get_y()
        self.set_xy(MARGIN_LR + 4, y0 + 3)
        self.multi_cell(text_w, 4.6, text)
        y1 = self.get_y() + 2
        # Draw the box behind (redraw text on top)
        self.set_xy(temp_x, temp_y)
        self.rect(MARGIN_LR, y0, self.w - 2 * MARGIN_LR, y1 - y0, style="DF")
        self.set_xy(MARGIN_LR + 4, y0 + 3)
        self.set_text_color(*INK)
        self.multi_cell(text_w, 4.6, text)
        self.set_y(y1 + 1)


# =========================================================================
# Content
# =========================================================================
def build() -> str:
    pdf = AgreementPDF()

    # ---------------- Cover ----------------
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*ACCENT)
    pdf.multi_cell(0, 11, "Co-Parenting\nCommitment Agreement")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*INK_DIM)
    pdf.multi_cell(0, 6,
                   "A child-focused planning document that converts both parents' "
                   "shared goals, concerns, and priorities into practical, day-to-day commitments.")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*INK_DIM)
    pdf.multi_cell(0, 5,
                   "This template follows completion of both parents' Foundation Statements. "
                   "It is designed to be reconciled — shared priorities flow into commitments, "
                   "unresolved issues stay clearly labelled as items still requiring discussion or mediation. "
                   "Completing this form does not create a court order or binding legal agreement.")
    pdf.ln(10)
    pdf.callout(
        "How to use this template with a Foundation Statement:\n"
        "1. Complete a Foundation Statement for each parent separately.\n"
        "2. Fill in sections 1 to 15 of this form together, or paste each parent's Foundation Statement "
        "into a shared workspace and reconcile section by section.\n"
        "3. Only items that both parents accept flow into the final agreement summary "
        "(page: 'Reconciled Summary'). Everything else stays labelled as 'requires discussion' or "
        "'requires mediation'."
    )
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 5, "Prepared for: ", ln=0)
    pdf.set_draw_color(*RULE); pdf.line(pdf.get_x(), pdf.get_y() + 5, pdf.w - MARGIN_LR, pdf.get_y() + 5)
    pdf.ln(9)
    pdf.cell(0, 5, "Date prepared: ", ln=0)
    pdf.line(pdf.get_x(), pdf.get_y() + 5, pdf.w - MARGIN_LR, pdf.get_y() + 5)

    # ---------------- 1. Family Information ----------------
    pdf.add_page()
    pdf.h1("1. Family Information")
    pdf.fill_line("Parent 1: ")
    pdf.fill_line("Parent 2: ")
    pdf.ln(2)
    pdf.h3("Child or children")
    pdf.table(
        ["Child's name", "Age", "School / grade", "Important needs"],
        rows=4,
        col_widths=[45, 15, 45, 73],
        row_height=9,
    )
    pdf.fill_line("Date prepared: ", width_mm=90)
    pdf.ln(2)
    pdf.h3("Purpose of this agreement")
    pdf.checkbox("Improve everyday co-parenting")
    pdf.checkbox("Prepare for mediation")
    pdf.checkbox("Address a specific parenting concern")
    pdf.checkbox("Create greater consistency between homes")
    pdf.checkbox("Support a child with educational, medical, or psychological needs")
    pdf.checkbox("Other:  ______________________________________________________")

    # ---------------- 2. Our Shared Foundation ----------------
    pdf.add_page()
    pdf.h1("2. Our Shared Foundation")
    pdf.h3("Our shared goal for our child")
    pdf.body(
        "We agree that our primary goal is to support our child's safety, stability, "
        "healthy development, and continuing relationship with each parent when appropriate."
    )
    pdf.multi_line_field("Our additional shared goals:", lines=3)

    pdf.h3("What our child needs most from us")
    pdf.hint("Select the needs identified in both parents' Foundation Statements.")
    pdf.checkbox_grid([
        "Safety",
        "Stability and predictable routines",
        "Freedom from parental conflict",
        "Healthy relationships with both parents",
        "Educational support",
        "Medical care",
        "Emotional or psychological support",
        "Consistent expectations between homes",
        "Support for special or developmental needs",
        "Meaningful family and community connections",
    ], cols=2)
    pdf.checkbox("Other:  ______________________________________________________")
    pdf.ln(2)
    pdf.h3("Our child-focused commitment")
    pdf.callout(
        "Even when we disagree, we will make reasonable efforts to keep our child's needs at the "
        "centre of our decisions. We will not ask our child to carry messages, choose sides, "
        "gather information, or manage adult conflict."
    )

    # ---------------- 3. Areas of Alignment ----------------
    pdf.add_page()
    pdf.h1("3. Areas of Alignment")
    pdf.hint("Fill in the priorities that appear in BOTH Foundation Statements.")
    pdf.h3("We agree on the following:")
    pdf.checkbox_grid([
        "Our child's immediate needs",
        "Educational priorities",
        "Medical priorities",
        "Emotional or psychological needs",
        "Daily routines",
        "Activities and special events",
        "Important relationships",
        "Communication expectations",
    ], cols=2)
    pdf.checkbox("Other:  ______________________________________________________")
    pdf.ln(1)
    pdf.multi_line_field("Our strongest areas of agreement are:", lines=3)
    pdf.multi_line_field("We want our child to experience:", lines=3)

    # ---------------- 4. Areas Requiring Further Discussion ----------------
    pdf.add_page()
    pdf.h1("4. Areas Requiring Further Discussion")
    pdf.body(
        "These subjects are important but are not yet fully resolved. "
        "They do NOT flow into the reconciled summary unless the status is later changed to 'Agreement reached'."
    )
    pdf.ln(1)
    pdf.table(
        ["Topic", "Parent 1's concern", "Parent 2's concern", "Child-focused question"],
        rows=5,
        col_widths=[38, 45, 45, 50],
        row_height=14,
    )
    pdf.h3("Status of each issue")
    pdf.checkbox("Agreement reached")
    pdf.checkbox("Temporary solution selected")
    pdf.checkbox("More information needed")
    pdf.checkbox("Professional guidance needed")
    pdf.checkbox("Refer to mediation")
    pdf.checkbox("Refer to attorneys or the court")

    # ---------------- 5. Parent Communication Agreement ----------------
    pdf.add_page()
    pdf.h1("5. Parent Communication Agreement")
    pdf.h3("Communication method")
    pdf.body("We will ordinarily communicate through:")
    pdf.checkbox_grid([
        "Co-parenting application",
        "Email",
        "Text message",
        "Telephone",
        "Scheduled meeting",
        "Communication through an agreed professional",
    ], cols=2)
    pdf.checkbox("Other:  ______________________________________________________")
    pdf.ln(1)
    pdf.h3("Expected response time")
    pdf.fill_line("Routine matters: within ", width_mm=20)
    pdf.fill_line("Time-sensitive child matters: within ", width_mm=20)
    pdf.body("Emergencies: as soon as reasonably possible.")
    pdf.ln(1)
    pdf.h3("Communication commitments")
    pdf.body("We agree to:")
    pdf.checkbox("Keep messages brief, informative, focused, and respectful.")
    pdf.checkbox("Discuss the child rather than past relationship grievances.")
    pdf.checkbox("Clearly identify requests, deadlines, and proposed solutions.")
    pdf.checkbox("Share important information within a reasonable time.")
    pdf.checkbox("Avoid insults, threats, excessive messaging, and hostile language.")
    pdf.checkbox("Pause a non-urgent conversation if it becomes unproductive.")
    pdf.checkbox("Preserve emergency communication for genuine emergencies.")
    pdf.ln(1)
    pdf.multi_line_field("Additional communication boundaries:", lines=3)

    # ---------------- 6. Parenting-Time Transitions ----------------
    pdf.add_page()
    pdf.h1("6. Parenting-Time Transitions")
    pdf.h3("Regular exchange arrangements")
    pdf.fill_line("Location: ", full_width=True)
    pdf.fill_line("Time: ", full_width=True)
    pdf.fill_line("Transportation responsibility: ", full_width=True)
    pdf.fill_line("Authorised pickup persons: ", full_width=True)
    pdf.ln(1)
    pdf.h3("We agree to")
    pdf.checkbox("Prepare the child and necessary belongings on time.")
    pdf.checkbox("Keep exchanges calm and focused on the child.")
    pdf.checkbox("Avoid discussing disputed issues during exchanges.")
    pdf.checkbox("Notify the other parent promptly about significant delays.")
    pdf.checkbox("Never use the child to communicate complaints or schedule changes.")
    pdf.ln(1)
    pdf.multi_line_field("Special safety or transition arrangements:", lines=3)

    # ---------------- 7. Education Agreement ----------------
    pdf.add_page()
    pdf.h1("7. Education Agreement")
    pdf.body("We agree to:")
    pdf.checkbox("Share report cards, school notices, schedules, and important communications.")
    pdf.checkbox("Notify one another of parent-teacher conferences, ARD meetings, IEP or 504 meetings, "
                 "disciplinary concerns, and significant academic changes.")
    pdf.checkbox("Permit both parents to participate in school matters when allowed.")
    pdf.checkbox("Support homework, attendance, tutoring, and agreed educational services.")
    pdf.checkbox("Avoid placing the child between different parental expectations.")
    pdf.ln(1)
    pdf.fill_line("Primary school contact: ", full_width=True)
    pdf.multi_line_field("Educational priorities:", lines=3)
    pdf.multi_line_field("Decisions requiring joint discussion:", lines=3)

    # ---------------- 8. Medical and Psychological Care ----------------
    pdf.add_page()
    pdf.h1("8. Medical and Psychological Care")
    pdf.body("We agree to share reasonably necessary information concerning:")
    pdf.checkbox_grid([
        "Appointments",
        "Diagnoses",
        "Prescriptions and medication changes",
        "Treatment recommendations",
        "Insurance information",
        "Significant injuries or illnesses",
        "Counselling or psychological services",
        "Follow-up instructions",
    ], cols=2)
    pdf.ln(1)
    pdf.h3("Current providers")
    pdf.table(
        ["Type of provider", "Provider's name", "Contact information"],
        rows=4,
        col_widths=[50, 55, 73],
        row_height=9,
    )
    pdf.multi_line_field("Medication-sharing plan:", lines=2)
    pdf.multi_line_field("Emergency notification plan:", lines=2)
    pdf.multi_line_field("Decisions requiring consultation:", lines=2)

    # ---------------- 9. Activities and Special Events ----------------
    pdf.add_page()
    pdf.h1("9. Activities and Special Events")
    pdf.body("We will make reasonable efforts to share information about:")
    pdf.checkbox_grid([
        "Sports and extracurricular activities",
        "School programmes",
        "Performances",
        "Religious or cultural events",
        "Birthdays and celebrations",
        "Graduations and awards",
        "Travel affecting the child's schedule",
    ], cols=2)
    pdf.ln(1)
    pdf.fill_line("How expenses will be discussed: ", full_width=True)
    pdf.fill_line("How schedule conflicts will be handled: ", full_width=True)
    pdf.ln(1)
    pdf.h3("Conduct at shared events")
    pdf.callout(
        "We will remain respectful, avoid confrontation, and allow our child to enjoy important events "
        "without feeling responsible for parental tension."
    )

    # ---------------- 10. Consistency Between Homes ----------------
    pdf.add_page()
    pdf.h1("10. Consistency Between Homes")
    pdf.body(
        "We agree that our homes do not have to be identical. When practical, we will seek consistency "
        "concerning:"
    )
    pdf.checkbox_grid([
        "School attendance and homework",
        "Bedtime and daily routines",
        "Medication",
        "Screen time",
        "Discipline and behavioural expectations",
        "Dietary or allergy needs",
        "Therapy recommendations",
        "Transportation safety",
    ], cols=2)
    pdf.checkbox("Other:  ______________________________________________________")
    pdf.ln(2)
    pdf.multi_line_field("The three areas where consistency matters most are:", lines=3)

    # ---------------- 11. Problem-Solving Process ----------------
    pdf.add_page()
    pdf.h1("11. Problem-Solving Process")
    pdf.body("When a disagreement occurs, we will:")
    steps = [
        "Identify the specific issue.",
        "Exchange relevant information.",
        "State the child's needs or interests.",
        "Offer reasonable options.",
        "Select an option, temporary plan, or next step.",
        "Record the agreement in writing.",
        "Review the outcome when appropriate.",
    ]
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 5.2, "\n".join(f"  {i}.  {s}" for i, s in enumerate(steps, 1)))
    pdf.ln(1)
    pdf.h3("If we cannot reach agreement, we will consider:")
    pdf.checkbox("A scheduled co-parenting discussion")
    pdf.checkbox("Consultation with the child's provider")
    pdf.checkbox("Parent coordination or facilitation")
    pdf.checkbox("Mediation")
    pdf.checkbox("Consultation with attorneys")
    pdf.checkbox("Another process:  __________________________________________")
    pdf.ln(1)
    pdf.fill_line("Agreed professional or mediator: ", full_width=True)

    # ---------------- 12. Safety and Conflict Boundaries ----------------
    pdf.add_page()
    pdf.h1("12. Safety and Conflict Boundaries")
    pdf.callout(
        "If direct communication is unsafe or subject to court restrictions, the safety plan or court "
        "order controls this agreement. This section does not require either parent to disclose "
        "confidential safety information to the other parent."
    )
    pdf.ln(1)
    pdf.h3("Appropriate alternatives may include")
    pdf.checkbox("Written-only communication")
    pdf.checkbox("A co-parenting application")
    pdf.checkbox("Neutral exchange locations")
    pdf.checkbox("Third-party exchanges")
    pdf.checkbox("Communication through professionals")
    pdf.checkbox("Supervised exchanges or parenting time")
    pdf.checkbox("Separate participation in meetings or mediation")
    pdf.ln(1)
    pdf.multi_line_field("Applicable safety boundaries:", lines=3)

    # ---------------- 13. Specific Action Plan ----------------
    pdf.add_page()
    pdf.h1("13. Specific Action Plan")
    pdf.hint("Turn shared commitments into concrete actions. One row per commitment.")
    pdf.table(
        ["Commitment", "Parent", "Deadline", "Confirmed by"],
        rows=8,
        col_widths=[70, 30, 34, 44],
        row_height=11,
    )

    # ---------------- 14. Review Date ----------------
    pdf.add_page()
    pdf.h1("14. Review Date")
    pdf.body("We will review this agreement:")
    pdf.checkbox("In 30 days")
    pdf.checkbox("In 60 days")
    pdf.checkbox("In 90 days")
    pdf.checkbox("At the beginning of each school year")
    pdf.checkbox("After a significant change in the child's needs")
    pdf.checkbox("On:  __________________________________________________________")
    pdf.ln(1)
    pdf.h3("At the review, we will consider")
    pdf.body(" What is working?")
    pdf.body(" What is not working?")
    pdf.body(" Has our child's situation changed?")
    pdf.body(" Does any commitment need clarification?")
    pdf.body(" Is professional assistance needed?")

    # ---------------- 15. Parent Acknowledgment & Signatures ----------------
    pdf.add_page()
    pdf.h1("15. Parent Acknowledgment")
    pdf.body(
        "This agreement reflects our present intentions and our commitment to child-focused co-parenting. "
        "Completing or signing this form does not replace an existing court order. We understand that legal "
        "provisions should be reviewed by qualified attorneys and, when required, approved by the court."
    )
    pdf.ln(6)

    def signature_block(role: str) -> None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*ACCENT)
        pdf.cell(0, 6, role, ln=1)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*INK)
        pdf.cell(24, 6, "Name:")
        pdf.set_draw_color(*RULE); pdf.set_line_width(0.35)
        pdf.line(pdf.get_x(), pdf.get_y() + 5, pdf.w - MARGIN_LR, pdf.get_y() + 5)
        pdf.ln(8)
        pdf.cell(24, 6, "Signature:")
        pdf.line(pdf.get_x(), pdf.get_y() + 5, pdf.w - MARGIN_LR, pdf.get_y() + 5)
        pdf.ln(8)
        pdf.cell(24, 6, "Date:")
        pdf.line(pdf.get_x(), pdf.get_y() + 5, pdf.w - MARGIN_LR, pdf.get_y() + 5)
        pdf.ln(12)

    signature_block("Parent 1")
    signature_block("Parent 2")

    # ---------------- Reconciled Summary Page ----------------
    pdf.add_page()
    pdf.h1("Reconciled Summary")
    pdf.body(
        "This is the polished output of the agreement. Only items that BOTH parents have accepted appear in the "
        "first three sections. Everything unresolved stays clearly labelled below in 'What still requires mediation' — "
        "the app should never make unresolved issues appear to be agreements."
    )
    pdf.ln(2)

    def summary_box(title: str, hint: str, lines: int = 6, tint=ACCENT_LIGHT) -> None:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 11.5)
        pdf.set_text_color(*ACCENT)
        pdf.cell(0, 6, title, ln=1)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*INK_DIM)
        pdf.multi_cell(0, 4.4, hint)
        pdf.ln(1)
        # write lines
        pdf.set_draw_color(*RULE); pdf.set_line_width(0.3)
        for _ in range(lines):
            if pdf.get_y() > pdf.h - MARGIN_BOTTOM - 6:
                pdf.add_page()
            y = pdf.get_y() + 5
            pdf.line(MARGIN_LR, y, pdf.w - MARGIN_LR, y)
            pdf.ln(6)
        pdf.ln(1)

    summary_box(
        "What We Agree On",
        "Pull from sections 3, 5-11 where BOTH parents ticked the same box or wrote compatible language.",
        lines=6,
    )
    summary_box(
        "What Our Child Needs",
        "Pull from section 2 'What our child needs most' + any child-specific priorities from both Foundation Statements.",
        lines=6,
    )
    summary_box(
        "What Each Parent Will Do",
        "Pull from section 13 (Specific Action Plan) — one commitment per row, with the responsible parent and deadline.",
        lines=6,
    )
    summary_box(
        "What Still Requires Mediation",
        "Pull ONLY from section 4 rows whose status is anything other than 'Agreement reached', "
        "plus any section 11 escalation triggers that fired.",
        lines=6,
    )

    out_path = "/app/frontend/public/downloads/coparent-commitment-agreement.pdf"
    pdf.output(out_path)
    return out_path


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p}")
