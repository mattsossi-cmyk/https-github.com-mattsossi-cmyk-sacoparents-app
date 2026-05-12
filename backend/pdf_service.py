"""PDF generation for the Mediation Prep Summary using fpdf2."""
from io import BytesIO
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF


SAGE = (132, 157, 142)
TERRA = (194, 135, 113)
SAND = (245, 243, 233)
TEXT_DARK = (42, 54, 49)
TEXT_MID = (92, 107, 100)


class PrepSummaryPDF(FPDF):
    def header(self):
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 30, "F")
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 18)
        self.set_xy(15, 10)
        self.cell(0, 8, "Mediation Preparation Summary", ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_MID)
        self.set_x(15)
        self.cell(0, 5, "SA Coparents - Relational Mediation Prep", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(35)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 8,
            "Confidential - Prepared for mediation. SA Coparents.",
            align="C",
        )

    def section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*SAGE)
        self.cell(0, 8, text, ln=1)
        self.set_draw_color(*SAGE)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(15, y, 60, y)
        self.ln(3)
        self.set_text_color(*TEXT_DARK)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet_list(self, items: List[str]):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*TEXT_DARK)
        for item in items:
            self.set_x(18)
            self.cell(4, 6, chr(149))  # bullet
            self.multi_cell(0, 6, str(item))
            self.ln(0.5)
        self.ln(1)


def build_summary_pdf(
    user_name: str,
    summary: Dict[str, Any],
    child_goals: Dict[str, Any] | None = None,
    mediation_date: str | None = None,
) -> bytes:
    pdf = PrepSummaryPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 30, 15)
    pdf.add_page()

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Prepared for: {user_name}", ln=1)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=1)
    if mediation_date:
        pdf.cell(0, 6, f"Mediation date: {mediation_date}", ln=1)
    pdf.set_text_color(*TEXT_DARK)

    # Readiness banner
    pdf.ln(3)
    pdf.set_fill_color(*SAND)
    pdf.set_font("Helvetica", "B", 12)
    label = summary.get("readiness_label", "")
    score = summary.get("readiness_score", 0)
    pdf.cell(0, 10, f"Readiness: {label}  ({score}/100)", ln=1, fill=True)

    pdf.section_title("Child-Centered Goals")
    pdf.body_text(summary.get("child_goals_summary", ""))
    if child_goals and child_goals.get("selected_goals"):
        pdf.bullet_list(child_goals["selected_goals"])

    pdf.section_title("Top Concerns")
    pdf.bullet_list(summary.get("top_concerns", []))

    pdf.section_title("Priority Agenda")
    agenda = summary.get("priority_agenda", [])
    pdf.set_font("Helvetica", "", 11)
    for it in agenda:
        rank = it.get("rank", "?")
        topic = it.get("topic", "")
        cat = it.get("category", "")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(10, 6, f"{rank}.")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f"{topic}  [{cat}]")
    pdf.ln(2)

    pdf.section_title("Flexibility Areas")
    pdf.bullet_list(summary.get("flexibility_areas", []))

    pdf.section_title("Communication Goals")
    pdf.bullet_list(summary.get("communication_goals", []))

    pdf.section_title("Notes for the Mediator")
    pdf.body_text(summary.get("notes_for_mediator", ""))

    # output as bytes
    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
