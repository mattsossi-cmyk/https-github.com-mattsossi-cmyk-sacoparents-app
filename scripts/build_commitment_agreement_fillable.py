"""Interactive fillable version of the SA CoParents Co-Parenting
Commitment Agreement template.

Uses reportlab's AcroForm API so each blank line becomes a real editable
text field and each checkbox square becomes a real clickable widget in
Adobe Acrobat, macOS Preview, Chrome PDF viewer, and any other reader
that supports AcroForms.

Run:
    python3 /app/scripts/build_commitment_agreement_fillable.py

Output:
    /app/frontend/public/downloads/coparent-commitment-agreement-fillable.pdf
"""
from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ---------------------------------------------------------------------------
# Palette + layout constants
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = A4
MARGIN_L = 18 * mm
MARGIN_R = 18 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 20 * mm

INK = HexColor("#1A1330")
INK_DIM = HexColor("#4B4567")
ACCENT = HexColor("#3D1A78")
ACCENT_LIGHT = HexColor("#F5F1FB")
RULE = HexColor("#D6CFE8")
FIELD_BORDER = HexColor("#B8AED0")
FIELD_BG = HexColor("#FBFAFD")


class Form:
    """Thin wrapper around reportlab canvas that maintains a y-cursor and
    a monotonic field-name counter (AcroForm requires unique names)."""

    def __init__(self, out_path: str) -> None:
        self.c = canvas.Canvas(out_path, pagesize=A4)
        self.c.setTitle("SA CoParents  Co-Parenting Commitment Agreement")
        self.c.setAuthor("SA CoParents")
        self.c.setSubject("Fillable child-focused co-parenting agreement template")
        self.y = PAGE_H - MARGIN_TOP
        self.page = 1
        self._field_counter = 0

    # Field-name factory (AcroForm rejects duplicate names)
    def _fname(self, base: str) -> str:
        self._field_counter += 1
        return f"{base}_{self._field_counter}"

    # ------------------------------------------------------------------
    # Cursor + page management
    # ------------------------------------------------------------------
    def need_space(self, min_mm: float) -> None:
        if self.y - (min_mm * mm) < MARGIN_BOTTOM:
            self.new_page()

    def ln(self, mm_gap: float) -> None:
        self.y -= mm_gap * mm

    def new_page(self) -> None:
        self._page_footer()
        self.c.showPage()
        self.page += 1
        self.y = PAGE_H - MARGIN_TOP
        self._page_header()

    def _page_header(self) -> None:
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(INK_DIM)
        self.c.drawString(MARGIN_L, PAGE_H - 12 * mm,
                         "SA CoParents  Co-Parenting Commitment Agreement")
        self.c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 12 * mm,
                               f"Page {self.page}")
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.3)
        self.c.line(MARGIN_L, PAGE_H - 14 * mm,
                    PAGE_W - MARGIN_R, PAGE_H - 14 * mm)

    def _page_footer(self) -> None:
        self.c.setFont("Helvetica-Oblique", 7.5)
        self.c.setFillColor(INK_DIM)
        self.c.drawCentredString(
            PAGE_W / 2, 10 * mm,
            "This template is a child-focused planning document. "
            "It is not a court order or binding legal agreement. "
            "Consult a qualified family-law attorney where required.",
        )

    # ------------------------------------------------------------------
    # Text primitives
    # ------------------------------------------------------------------
    def h1(self, text: str) -> None:
        self.need_space(20)
        self.c.setFont("Helvetica-Bold", 20)
        self.c.setFillColor(ACCENT)
        self.c.drawString(MARGIN_L, self.y, text)
        self.ln(10)

    def h2(self, text: str) -> None:
        self.need_space(14)
        self.ln(2)
        self.c.setFont("Helvetica-Bold", 13)
        self.c.setFillColor(ACCENT)
        self.c.drawString(MARGIN_L, self.y, text)
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.4)
        self.c.line(MARGIN_L, self.y - 2, MARGIN_L + 40 * mm, self.y - 2)
        self.ln(7)

    def h3(self, text: str) -> None:
        self.need_space(8)
        self.ln(1)
        self.c.setFont("Helvetica-Bold", 10.5)
        self.c.setFillColor(INK)
        self.c.drawString(MARGIN_L, self.y, text)
        self.ln(5.5)

    def body(self, text: str, italic: bool = False) -> None:
        font = "Helvetica-Oblique" if italic else "Helvetica"
        self.c.setFont(font, 10)
        self.c.setFillColor(INK)
        for line in _wrap(text, MARGIN_L, PAGE_W - MARGIN_R, self.c, font, 10):
            self.need_space(6)
            self.c.drawString(MARGIN_L, self.y, line)
            self.ln(5)
        self.ln(0.5)

    def hint(self, text: str) -> None:
        self.c.setFont("Helvetica-Oblique", 9)
        self.c.setFillColor(INK_DIM)
        for line in _wrap(text, MARGIN_L, PAGE_W - MARGIN_R,
                          self.c, "Helvetica-Oblique", 9):
            self.need_space(5)
            self.c.drawString(MARGIN_L, self.y, line)
            self.ln(4.5)
        self.c.setFillColor(INK)

    def callout(self, text: str) -> None:
        self.ln(1)
        wrapped = _wrap(text, MARGIN_L + 4 * mm, PAGE_W - MARGIN_R - 4 * mm,
                        self.c, "Helvetica", 9.5)
        h_mm = 4 + len(wrapped) * 4.5
        self.need_space(h_mm + 3)
        top = self.y + 2
        self.c.setFillColor(ACCENT_LIGHT)
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.3)
        self.c.rect(MARGIN_L, top - h_mm * mm,
                   PAGE_W - MARGIN_L - MARGIN_R, h_mm * mm,
                   stroke=1, fill=1)
        self.c.setFillColor(INK)
        self.c.setFont("Helvetica", 9.5)
        y = top - 4 * mm
        for line in wrapped:
            self.c.drawString(MARGIN_L + 4 * mm, y, line)
            y -= 4.5 * mm
        self.y = top - h_mm * mm - 2 * mm

    # ------------------------------------------------------------------
    # AcroForm widgets
    # ------------------------------------------------------------------
    def _draw_field(self, x_mm: float, y_mm: float, w_mm: float,
                    h_mm: float, name: str, multiline: bool = False,
                    tooltip: str = "") -> None:
        self.c.acroForm.textfield(
            name=name,
            tooltip=tooltip or name,
            x=x_mm, y=y_mm,
            width=w_mm, height=h_mm,
            borderStyle="inset",
            borderColor=FIELD_BORDER,
            fillColor=FIELD_BG,
            textColor=INK,
            forceBorder=True,
            fieldFlags="multiline" if multiline else "",
            fontSize=10,
        )

    def fill_line(self, label: str, field_w_mm: float = 90,
                  full_width: bool = False, tooltip: str = "") -> None:
        """Label + inline single-line text field."""
        self.need_space(9)
        self.c.setFont("Helvetica", 10)
        self.c.setFillColor(INK)
        label_w = self.c.stringWidth(label, "Helvetica", 10) + 2
        self.c.drawString(MARGIN_L, self.y, label)
        # Field
        field_x = MARGIN_L + label_w
        field_h = 6 * mm
        if full_width:
            field_end = PAGE_W - MARGIN_R
        else:
            field_end = min(PAGE_W - MARGIN_R, field_x + field_w_mm * mm)
        field_w = field_end - field_x
        self._draw_field(
            x_mm=field_x,
            y_mm=self.y - 1.5 * mm,
            w_mm=field_w,
            h_mm=field_h,
            name=self._fname(label.strip(":").strip().replace(" ", "_") or "field"),
            tooltip=tooltip or label.strip(":").strip(),
        )
        self.ln(8)

    def multi_line_field(self, label: str, lines: int = 3,
                         tooltip: str = "") -> None:
        """Labelled multiline text area."""
        self.h3(label)
        h_mm = lines * 6
        self.need_space(h_mm + 2)
        self._draw_field(
            x_mm=MARGIN_L,
            y_mm=self.y - h_mm * mm,
            w_mm=PAGE_W - MARGIN_L - MARGIN_R,
            h_mm=h_mm * mm,
            name=self._fname(label.strip(":").strip().replace(" ", "_") or "notes"),
            multiline=True,
            tooltip=tooltip or label.strip(":").strip(),
        )
        self.ln(h_mm + 1.5)

    def checkbox(self, label: str, indent_mm: float = 0,
                 tooltip: str = "") -> None:
        """A real clickable checkbox + label."""
        self.need_space(7)
        size = 3.5 * mm
        x = MARGIN_L + indent_mm * mm
        y = self.y - 0.5 * mm
        self.c.acroForm.checkbox(
            name=self._fname("cb"),
            tooltip=tooltip or label,
            x=x, y=y - size + 1 * mm,
            size=size,
            borderColor=ACCENT,
            fillColor=None,
            textColor=ACCENT,
            borderStyle="solid",
            borderWidth=1,
            forceBorder=True,
            checked=False,
        )
        self.c.setFont("Helvetica", 10)
        self.c.setFillColor(INK)
        wrap_x = x + size + 3 * mm
        for i, line in enumerate(_wrap(label, wrap_x, PAGE_W - MARGIN_R,
                                       self.c, "Helvetica", 10)):
            if i > 0:
                self.need_space(5)
            self.c.drawString(wrap_x, self.y, line)
            if i < 999:
                self.y -= 4.8 * mm if i == 0 else 4.5 * mm
                # only shift for wrap lines beyond the first
                if i > 0 and line == "":
                    break
        # normalise the y drop to 6mm total for single-line, more for wrapped
        # simpler: recompute total drop
        # Reset y based on how many wrap lines rendered
        # For simplicity we already stepped in loop; add a small breath
        self.ln(0.5)

    def checkbox_row_two(self, left: str, right: str) -> None:
        """Two checkboxes on a single row for compact list layouts."""
        self.need_space(7)
        col_w = (PAGE_W - MARGIN_L - MARGIN_R) / 2
        size = 3.5 * mm
        row_y = self.y - 0.5 * mm
        for i, label in enumerate([left, right]):
            if not label:
                continue
            x = MARGIN_L + i * col_w
            self.c.acroForm.checkbox(
                name=self._fname("cb"),
                tooltip=label,
                x=x, y=row_y - size + 1 * mm,
                size=size,
                borderColor=ACCENT,
                fillColor=None,
                textColor=ACCENT,
                borderStyle="solid",
                borderWidth=1,
                forceBorder=True,
                checked=False,
            )
            self.c.setFont("Helvetica", 10)
            self.c.setFillColor(INK)
            # Wrap label into column width
            available = col_w - size - 4 * mm
            lines = _wrap_width(label, available, self.c, "Helvetica", 10)
            y = self.y
            for line in lines[:2]:
                self.c.drawString(x + size + 3 * mm, y, line)
                y -= 4.5 * mm
        # advance
        max_lines = max(
            len(_wrap_width(left, col_w - size - 4 * mm, self.c, "Helvetica", 10)),
            len(_wrap_width(right, col_w - size - 4 * mm, self.c, "Helvetica", 10)) if right else 1,
        )
        self.ln(max(5.5, max_lines * 4.5 + 1))

    def checkbox_grid(self, items) -> None:
        """Two-column checkbox grid."""
        i = 0
        while i < len(items):
            left = items[i]
            right = items[i + 1] if i + 1 < len(items) else ""
            self.checkbox_row_two(left, right)
            i += 2

    # ------------------------------------------------------------------
    # Tables — each cell is an editable text field
    # ------------------------------------------------------------------
    def table(self, headers, rows: int, col_widths_mm,
              row_height_mm: float = 10) -> None:
        """Bordered table: coloured header row, then N rows of editable
        text fields, one per cell."""
        total_w = sum(col_widths_mm)
        h_mm = row_height_mm
        # Header
        self.need_space(h_mm + rows * h_mm + 4)
        header_top = self.y
        x = MARGIN_L
        self.c.setFillColor(ACCENT)
        self.c.setStrokeColor(ACCENT)
        self.c.rect(MARGIN_L, header_top - 6.5 * mm,
                   total_w * mm, 6.5 * mm, stroke=1, fill=1)
        self.c.setFillColor(HexColor("#FFFFFF"))
        self.c.setFont("Helvetica-Bold", 9.5)
        for i, header in enumerate(headers):
            self.c.drawString(x + 2 * mm, header_top - 4.5 * mm, header)
            x += col_widths_mm[i] * mm
        self.ln(6.5)
        # Body — editable text fields
        for r in range(rows):
            self.need_space(h_mm + 1)
            x = MARGIN_L
            row_y = self.y - h_mm * mm
            for i, w in enumerate(col_widths_mm):
                self.c.acroForm.textfield(
                    name=self._fname(f"cell_r{r}c{i}"),
                    tooltip=headers[i],
                    x=x, y=row_y,
                    width=w * mm, height=h_mm * mm,
                    borderStyle="inset",
                    borderColor=FIELD_BORDER,
                    fillColor=None,
                    textColor=INK,
                    forceBorder=True,
                    fieldFlags="multiline",
                    fontSize=9.5,
                )
                x += w * mm
            self.ln(h_mm)
        self.ln(1)

    def signature_block(self, role: str) -> None:
        """A dedicated signature block with real fields for name, signature
        (a text field — reportlab doesn't offer freehand ink signatures in
        AcroForm), and date."""
        self.need_space(35)
        self.c.setFont("Helvetica-Bold", 11)
        self.c.setFillColor(ACCENT)
        self.c.drawString(MARGIN_L, self.y, role)
        self.ln(7)
        for label, key, w in [
            ("Name:",      "sig_name",      110),
            ("Signature:", "sig_signature", 110),
            ("Date:",      "sig_date",      60),
        ]:
            self.need_space(8)
            self.c.setFont("Helvetica", 10)
            self.c.setFillColor(INK)
            self.c.drawString(MARGIN_L, self.y, label)
            self._draw_field(
                x_mm=MARGIN_L + 24 * mm,
                y_mm=self.y - 1.5 * mm,
                w_mm=w * mm,
                h_mm=6 * mm,
                name=self._fname(f"{role.replace(' ', '_')}_{key}"),
                tooltip=f"{role} {label.rstrip(':')}",
            )
            self.ln(8)
        self.ln(3)

    # ------------------------------------------------------------------
    def save(self) -> None:
        self._page_footer()
        self.c.save()


# ---------------------------------------------------------------------------
# Text wrapping utilities (single-column body copy)
# ---------------------------------------------------------------------------
def _wrap(text: str, x_start_pt: float, x_end_pt: float,
          c: canvas.Canvas, font: str, size: float):
    max_w = x_end_pt - x_start_pt
    return _wrap_width(text, max_w, c, font, size)


def _wrap_width(text: str, max_w_pt: float,
                c: canvas.Canvas, font: str, size: float):
    if not text:
        return [""]
    out = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for w in words:
            candidate = f"{line} {w}".strip()
            if c.stringWidth(candidate, font, size) <= max_w_pt or not line:
                line = candidate
            else:
                out.append(line)
                line = w
        if line:
            out.append(line)
    return out or [""]


# ===========================================================================
# Content
# ===========================================================================
def build() -> str:
    out_path = "/app/frontend/public/downloads/coparent-commitment-agreement-fillable.pdf"
    f = Form(out_path)
    f._page_header()

    # ---------- Cover ----------
    f.ln(20)
    f.c.setFont("Helvetica-Bold", 26)
    f.c.setFillColor(ACCENT)
    f.c.drawString(MARGIN_L, f.y, "SA CoParents")
    f.ln(11)
    f.c.setFont("Helvetica-Bold", 22)
    f.c.drawString(MARGIN_L, f.y, "Co-Parenting Commitment Agreement")
    f.ln(12)
    f.body(
        "A child-focused planning document that converts both parents' shared goals, "
        "concerns, and priorities into practical, day-to-day commitments."
    )
    f.body(
        "This template follows completion of both parents' Foundation Statements. "
        "Shared priorities flow into commitments; unresolved issues stay clearly "
        "labelled as items still requiring discussion or mediation. Completing this "
        "form does not create a court order or binding legal agreement.",
        italic=True,
    )
    f.ln(3)
    f.callout(
        "How to use this template alongside a Foundation Statement:\n"
        "1. Complete a Foundation Statement for each parent separately.\n"
        "2. Fill in sections 1 to 15 of this form together, or reconcile section "
        "by section from each parent's Foundation Statement.\n"
        "3. Only items that both parents accept flow into the final Reconciled "
        "Summary on the last page. Everything else stays labelled as 'requires "
        "discussion' or 'requires mediation'."
    )
    f.ln(4)
    f.fill_line("Prepared for: ", full_width=True)
    f.fill_line("Date prepared: ", field_w_mm=80)

    # ---------- 1. Family Information ----------
    f.new_page(); f.h1("1. Family Information")
    f.fill_line("Parent 1: ", full_width=True)
    f.fill_line("Parent 2: ", full_width=True)
    f.ln(2)
    f.h3("Child or children")
    f.table(
        ["Child's name", "Age", "School / grade", "Important needs"],
        rows=4, col_widths_mm=[45, 15, 45, 69], row_height_mm=10,
    )
    f.fill_line("Date prepared: ", field_w_mm=80)
    f.ln(2)
    f.h3("Purpose of this agreement")
    f.checkbox("Improve everyday co-parenting")
    f.checkbox("Prepare for mediation")
    f.checkbox("Address a specific parenting concern")
    f.checkbox("Create greater consistency between homes")
    f.checkbox("Support a child with educational, medical, or psychological needs")
    f.checkbox("Other")
    f.fill_line("Other:", full_width=True)

    # ---------- 2. Our Shared Foundation ----------
    f.new_page(); f.h1("2. Our Shared Foundation")
    f.h3("Our shared goal for our child")
    f.body(
        "We agree that our primary goal is to support our child's safety, stability, "
        "healthy development, and continuing relationship with each parent when appropriate."
    )
    f.multi_line_field("Our additional shared goals", lines=3)
    f.h3("What our child needs most from us")
    f.hint("Select the needs identified in both parents' Foundation Statements.")
    f.checkbox_grid([
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
    ])
    f.checkbox("Other")
    f.fill_line("Other:", full_width=True)
    f.ln(1)
    f.h3("Our child-focused commitment")
    f.callout(
        "Even when we disagree, we will make reasonable efforts to keep our child's needs "
        "at the centre of our decisions. We will not ask our child to carry messages, choose "
        "sides, gather information, or manage adult conflict."
    )

    # ---------- 3. Areas of Alignment ----------
    f.new_page(); f.h1("3. Areas of Alignment")
    f.hint("Tick the priorities that appear in BOTH Foundation Statements.")
    f.h3("We agree on the following")
    f.checkbox_grid([
        "Our child's immediate needs",
        "Educational priorities",
        "Medical priorities",
        "Emotional or psychological needs",
        "Daily routines",
        "Activities and special events",
        "Important relationships",
        "Communication expectations",
    ])
    f.checkbox("Other")
    f.fill_line("Other:", full_width=True)
    f.ln(1)
    f.multi_line_field("Our strongest areas of agreement are", lines=3)
    f.multi_line_field("We want our child to experience", lines=3)

    # ---------- 4. Areas Requiring Further Discussion ----------
    f.new_page(); f.h1("4. Areas Requiring Further Discussion")
    f.body(
        "These subjects are important but are not yet fully resolved. They do NOT flow into "
        "the Reconciled Summary unless the status is later changed to 'Agreement reached'."
    )
    f.ln(1)
    f.table(
        ["Topic", "Parent 1's concern", "Parent 2's concern", "Child-focused question"],
        rows=5, col_widths_mm=[36, 45, 45, 48], row_height_mm=14,
    )
    f.h3("Status of each issue")
    f.checkbox("Agreement reached")
    f.checkbox("Temporary solution selected")
    f.checkbox("More information needed")
    f.checkbox("Professional guidance needed")
    f.checkbox("Refer to mediation")
    f.checkbox("Refer to attorneys or the court")

    # ---------- 5. Parent Communication Agreement ----------
    f.new_page(); f.h1("5. Parent Communication Agreement")
    f.h3("Communication method")
    f.body("We will ordinarily communicate through:")
    f.checkbox_grid([
        "Co-parenting application",
        "Email",
        "Text message",
        "Telephone",
        "Scheduled meeting",
        "Communication through an agreed professional",
    ])
    f.checkbox("Other")
    f.fill_line("Other:", full_width=True)
    f.ln(1)
    f.h3("Expected response time")
    f.fill_line("Routine matters: within ", field_w_mm=30)
    f.fill_line("Time-sensitive child matters: within ", field_w_mm=30)
    f.body("Emergencies: as soon as reasonably possible.")
    f.ln(1)
    f.h3("Communication commitments")
    f.body("We agree to:")
    f.checkbox("Keep messages brief, informative, focused, and respectful.")
    f.checkbox("Discuss the child rather than past relationship grievances.")
    f.checkbox("Clearly identify requests, deadlines, and proposed solutions.")
    f.checkbox("Share important information within a reasonable time.")
    f.checkbox("Avoid insults, threats, excessive messaging, and hostile language.")
    f.checkbox("Pause a non-urgent conversation if it becomes unproductive.")
    f.checkbox("Preserve emergency communication for genuine emergencies.")
    f.multi_line_field("Additional communication boundaries", lines=3)

    # ---------- 6. Parenting-Time Transitions ----------
    f.new_page(); f.h1("6. Parenting-Time Transitions")
    f.h3("Regular exchange arrangements")
    f.fill_line("Location: ", full_width=True)
    f.fill_line("Time: ", full_width=True)
    f.fill_line("Transportation responsibility: ", full_width=True)
    f.fill_line("Authorised pickup persons: ", full_width=True)
    f.ln(1)
    f.h3("We agree to")
    f.checkbox("Prepare the child and necessary belongings on time.")
    f.checkbox("Keep exchanges calm and focused on the child.")
    f.checkbox("Avoid discussing disputed issues during exchanges.")
    f.checkbox("Notify the other parent promptly about significant delays.")
    f.checkbox("Never use the child to communicate complaints or schedule changes.")
    f.multi_line_field("Special safety or transition arrangements", lines=3)

    # ---------- 7. Education Agreement ----------
    f.new_page(); f.h1("7. Education Agreement")
    f.body("We agree to:")
    f.checkbox("Share report cards, school notices, schedules, and important communications.")
    f.checkbox("Notify one another of parent-teacher conferences, ARD meetings, IEP or 504 meetings, disciplinary concerns, and significant academic changes.")
    f.checkbox("Permit both parents to participate in school matters when allowed.")
    f.checkbox("Support homework, attendance, tutoring, and agreed educational services.")
    f.checkbox("Avoid placing the child between different parental expectations.")
    f.ln(1)
    f.fill_line("Primary school contact: ", full_width=True)
    f.multi_line_field("Educational priorities", lines=3)
    f.multi_line_field("Decisions requiring joint discussion", lines=3)

    # ---------- 8. Medical and Psychological Care ----------
    f.new_page(); f.h1("8. Medical and Psychological Care")
    f.body("We agree to share reasonably necessary information concerning:")
    f.checkbox_grid([
        "Appointments",
        "Diagnoses",
        "Prescriptions and medication changes",
        "Treatment recommendations",
        "Insurance information",
        "Significant injuries or illnesses",
        "Counselling or psychological services",
        "Follow-up instructions",
    ])
    f.ln(1)
    f.h3("Current providers")
    f.table(
        ["Type of provider", "Provider's name", "Contact information"],
        rows=4, col_widths_mm=[50, 55, 69], row_height_mm=10,
    )
    f.multi_line_field("Medication-sharing plan", lines=2)
    f.multi_line_field("Emergency notification plan", lines=2)
    f.multi_line_field("Decisions requiring consultation", lines=2)

    # ---------- 9. Activities and Special Events ----------
    f.new_page(); f.h1("9. Activities and Special Events")
    f.body("We will make reasonable efforts to share information about:")
    f.checkbox_grid([
        "Sports and extracurricular activities",
        "School programmes",
        "Performances",
        "Religious or cultural events",
        "Birthdays and celebrations",
        "Graduations and awards",
        "Travel affecting the child's schedule",
    ])
    f.ln(1)
    f.fill_line("How expenses will be discussed: ", full_width=True)
    f.fill_line("How schedule conflicts will be handled: ", full_width=True)
    f.h3("Conduct at shared events")
    f.callout(
        "We will remain respectful, avoid confrontation, and allow our child to enjoy "
        "important events without feeling responsible for parental tension."
    )

    # ---------- 10. Consistency Between Homes ----------
    f.new_page(); f.h1("10. Consistency Between Homes")
    f.body(
        "We agree that our homes do not have to be identical. When practical, we will seek "
        "consistency concerning:"
    )
    f.checkbox_grid([
        "School attendance and homework",
        "Bedtime and daily routines",
        "Medication",
        "Screen time",
        "Discipline and behavioural expectations",
        "Dietary or allergy needs",
        "Therapy recommendations",
        "Transportation safety",
    ])
    f.checkbox("Other")
    f.fill_line("Other:", full_width=True)
    f.multi_line_field("The three areas where consistency matters most are", lines=3)

    # ---------- 11. Problem-Solving Process ----------
    f.new_page(); f.h1("11. Problem-Solving Process")
    f.body("When a disagreement occurs, we will:")
    steps = [
        "Identify the specific issue.",
        "Exchange relevant information.",
        "State the child's needs or interests.",
        "Offer reasonable options.",
        "Select an option, temporary plan, or next step.",
        "Record the agreement in writing.",
        "Review the outcome when appropriate.",
    ]
    for i, step in enumerate(steps, start=1):
        f.body(f"  {i}.  {step}")
    f.ln(1)
    f.h3("If we cannot reach agreement, we will consider")
    f.checkbox("A scheduled co-parenting discussion")
    f.checkbox("Consultation with the child's provider")
    f.checkbox("Parent coordination or facilitation")
    f.checkbox("Mediation")
    f.checkbox("Consultation with attorneys")
    f.checkbox("Another process")
    f.fill_line("Another process: ", full_width=True)
    f.fill_line("Agreed professional or mediator: ", full_width=True)

    # ---------- 12. Safety and Conflict Boundaries ----------
    f.new_page(); f.h1("12. Safety and Conflict Boundaries")
    f.callout(
        "If direct communication is unsafe or subject to court restrictions, the safety plan "
        "or court order controls this agreement. This section does not require either parent "
        "to disclose confidential safety information to the other parent."
    )
    f.ln(1)
    f.h3("Appropriate alternatives may include")
    f.checkbox("Written-only communication")
    f.checkbox("A co-parenting application")
    f.checkbox("Neutral exchange locations")
    f.checkbox("Third-party exchanges")
    f.checkbox("Communication through professionals")
    f.checkbox("Supervised exchanges or parenting time")
    f.checkbox("Separate participation in meetings or mediation")
    f.multi_line_field("Applicable safety boundaries", lines=3)

    # ---------- 13. Specific Action Plan ----------
    f.new_page(); f.h1("13. Specific Action Plan")
    f.hint("Turn shared commitments into concrete actions. One row per commitment.")
    f.table(
        ["Commitment", "Parent", "Deadline", "Confirmed by"],
        rows=8, col_widths_mm=[70, 30, 34, 40], row_height_mm=11,
    )

    # ---------- 14. Review Date ----------
    f.new_page(); f.h1("14. Review Date")
    f.body("We will review this agreement:")
    f.checkbox("In 30 days")
    f.checkbox("In 60 days")
    f.checkbox("In 90 days")
    f.checkbox("At the beginning of each school year")
    f.checkbox("After a significant change in the child's needs")
    f.checkbox("On a specific date")
    f.fill_line("On:", full_width=True)
    f.h3("At the review, we will consider")
    for q in [
        "What is working?",
        "What is not working?",
        "Has our child's situation changed?",
        "Does any commitment need clarification?",
        "Is professional assistance needed?",
    ]:
        f.body(f" - {q}")

    # ---------- 15. Parent Acknowledgment ----------
    f.new_page(); f.h1("15. Parent Acknowledgment")
    f.body(
        "This agreement reflects our present intentions and our commitment to child-focused "
        "co-parenting. Completing or signing this form does not replace an existing court order. "
        "We understand that legal provisions should be reviewed by qualified attorneys and, when "
        "required, approved by the court."
    )
    f.ln(4)
    f.signature_block("Parent 1")
    f.signature_block("Parent 2")

    # ---------- Reconciled Summary ----------
    f.new_page(); f.h1("Reconciled Summary")
    f.body(
        "This is the polished output of the agreement. Only items that BOTH parents have accepted "
        "appear in the first three sections. Everything unresolved stays clearly labelled below in "
        "'What still requires mediation' - the agreement should never make unresolved issues appear "
        "to be agreements."
    )
    f.multi_line_field(
        "What We Agree On", lines=6,
        tooltip="Shared items ticked across §3, §5-§11.",
    )
    f.multi_line_field(
        "What Our Child Needs", lines=6,
        tooltip="Shared child-needs from §2 plus child-specific priorities from both Foundation Statements.",
    )
    f.multi_line_field(
        "What Each Parent Will Do", lines=6,
        tooltip="One commitment per line from §13 Specific Action Plan.",
    )
    f.multi_line_field(
        "What Still Requires Mediation", lines=6,
        tooltip="Section 4 rows whose status is NOT 'Agreement reached', plus any §11 escalation triggers.",
    )

    f.save()
    return out_path


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p}")
