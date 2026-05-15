"""PDF generation for the Mediation Prep Summary using fpdf2."""
import os
from io import BytesIO
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF


SAGE = (132, 157, 142)
TERRA = (194, 135, 113)
SAND = (245, 243, 233)
TEXT_DARK = (42, 54, 49)
TEXT_MID = (92, 107, 100)

# Org branding shown in every PDF
ORG_NAME = "SA Coparents"
ORG_TAGLINE = "Relational Mediation Prep"
ORG_ADDRESS = "16607 Blanco #703, San Antonio, Texas 78232"
ORG_PHONE = "210-224-1667"
ORG_EMAIL = "mattsossi@bsossi.com"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")


# fpdf2's built-in Helvetica is a latin-1 font and can't encode characters like
# em-dashes, curly quotes, ellipses, or unicode bullets that AI output sometimes
# contains. We replace them with ASCII equivalents before drawing.
_UNICODE_REPLACEMENTS = {
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201C": '"',   # left double quote
    "\u201D": '"',   # right double quote
    "\u2026": "...", # ellipsis
    "\u2022": "*",   # bullet
    "\u00A0": " ",   # nbsp
}


def _safe(text: Any) -> str:
    """Return a latin-1 safe representation of any text for fpdf2 built-in fonts."""
    if text is None:
        return ""
    s = str(text)
    for ch, repl in _UNICODE_REPLACEMENTS.items():
        s = s.replace(ch, repl)
    # Fallback: strip anything still outside latin-1 so we never crash a PDF render.
    return s.encode("latin-1", "replace").decode("latin-1")


class PrepSummaryPDF(FPDF):
    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        # Soft sand band
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 38, "F")
        # Logo on the left (24mm square block, vertically centered in the band)
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=7, w=24, h=24)
            except Exception:
                pass
        # Title + tagline (offset right of the logo)
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 17)
        self.set_xy(42, 9)
        self.cell(0, 8, "Mediation Preparation Summary", ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_MID)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_NAME} - {ORG_TAGLINE}", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_ADDRESS}", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(44)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Confidential - Prepared for mediation. {ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}",
            align="C",
            ln=1,
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


def _render_meta(pdf: "PrepSummaryPDF", user_name: str, mediation_date: str | None) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Prepared for: {user_name}", ln=1)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=1)
    if mediation_date:
        pdf.cell(0, 6, f"Mediation date: {mediation_date}", ln=1)
    pdf.set_text_color(*TEXT_DARK)


def _render_readiness_banner(pdf: "PrepSummaryPDF", summary: Dict[str, Any]) -> None:
    pdf.ln(3)
    pdf.set_fill_color(*SAND)
    pdf.set_font("Helvetica", "B", 12)
    label = summary.get("readiness_label", "")
    score = summary.get("readiness_score", 0)
    pdf.cell(0, 10, f"Readiness: {label}  ({score}/100)", ln=1, fill=True)


def _render_priority_agenda(pdf: "PrepSummaryPDF", agenda: list) -> None:
    pdf.section_title("Priority Agenda")
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


def _render_child_goals(
    pdf: "PrepSummaryPDF",
    summary: Dict[str, Any],
    child_goals: Dict[str, Any] | None,
) -> None:
    pdf.section_title("Child-Centered Goals")
    pdf.body_text(summary.get("child_goals_summary", ""))
    if child_goals and child_goals.get("selected_goals"):
        pdf.bullet_list(child_goals["selected_goals"])


def build_summary_pdf(
    user_name: str,
    summary: Dict[str, Any],
    child_goals: Dict[str, Any] | None = None,
    mediation_date: str | None = None,
) -> bytes:
    pdf = PrepSummaryPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 44, 15)
    pdf.add_page()

    _render_meta(pdf, user_name, mediation_date)
    _render_readiness_banner(pdf, summary)

    if summary.get("changes_since_last"):
        pdf.section_title("What's Changed Since Last Time")
        pdf.body_text(summary["changes_since_last"])

    _render_child_goals(pdf, summary, child_goals)

    pdf.section_title("Top Concerns")
    pdf.bullet_list(summary.get("top_concerns", []))

    _render_priority_agenda(pdf, summary.get("priority_agenda", []))

    pdf.section_title("Flexibility Areas")
    pdf.bullet_list(summary.get("flexibility_areas", []))

    pdf.section_title("Communication Goals")
    pdf.bullet_list(summary.get("communication_goals", []))

    pdf.section_title("Notes for the Mediator")
    pdf.body_text(summary.get("notes_for_mediator", ""))

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


# ============ Co-Parenting Agreement PDF ============
class AgreementPDF(FPDF):
    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 38, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=7, w=24, h=24)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 17)
        self.set_xy(42, 9)
        self.cell(0, 8, "Co-Parenting Agreement - Draft", ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_MID)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_NAME} - A starting point for discussion", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_ADDRESS}", ln=1)
        self.set_x(42)
        self.cell(0, 5, f"{ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(44)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Draft only - not a legal document. {ORG_NAME} - {ORG_PHONE} - {ORG_EMAIL}",
            align="C",
            ln=1,
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
        self.multi_cell(0, 6, text)
        self.ln(1)

    def clause_list(self, items: list) -> None:
        """Render a list of {area, agreement} dicts as labelled clauses."""
        self.set_font("Helvetica", "", 11)
        for it in items:
            area = it.get("area", "")
            clause = it.get("agreement", "")
            self.set_x(18)
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 6, area, ln=1)
            self.set_x(22)
            self.set_font("Helvetica", "", 11)
            self.multi_cell(0, 6, clause)
            self.ln(0.5)

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 11)
        for item in items:
            self.set_x(18)
            self.cell(4, 6, chr(149))
            self.multi_cell(0, 6, str(item))
            self.ln(0.5)
        self.ln(1)


def _agreement_section(pdf: AgreementPDF, title: str, items: list) -> None:
    if not items:
        return
    pdf.section_title(title)
    pdf.clause_list(items)


def _agreement_meta(
    pdf: AgreementPDF, user_name: str, mediation_date: str | None
) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Drafted by: {user_name}", ln=1)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=1)
    if mediation_date:
        pdf.cell(0, 6, f"Mediation date: {mediation_date}", ln=1)
    pdf.set_text_color(*TEXT_DARK)


def _agreement_overview(pdf: AgreementPDF, overview: str | None) -> None:
    if not overview:
        return
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.multi_cell(0, 6, overview)
    pdf.set_text_color(*TEXT_DARK)


def _agreement_priority_items(pdf: AgreementPDF, priorities: list) -> None:
    if not priorities:
        return
    pdf.section_title("Priority Topics to Discuss")
    pdf.set_font("Helvetica", "", 11)
    for it in priorities:
        rank = it.get("rank", "?")
        topic = it.get("topic", "")
        cat = it.get("category", "")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(10, 6, f"{rank}.")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f"{topic}  [{cat}]")
    pdf.ln(2)


def _agreement_signature_lines(pdf: AgreementPDF) -> None:
    pdf.ln(8)
    pdf.set_draw_color(*TEXT_MID)
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.line(120, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_xy(20, pdf.get_y() + 1)
    pdf.cell(70, 5, "Parent A signature / date")
    pdf.set_xy(120, pdf.get_y())
    pdf.cell(70, 5, "Parent B signature / date")


def build_agreement_pdf(
    user_name: str,
    agreement: Dict[str, Any],
    mediation_date: str | None = None,
) -> bytes:
    pdf = AgreementPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 44, 15)
    pdf.add_page()

    _agreement_meta(pdf, user_name, mediation_date)
    _agreement_overview(pdf, agreement.get("overview"))

    if agreement.get("changes_since_last"):
        pdf.section_title("Updates from the Previous Draft")
        pdf.body_text(agreement["changes_since_last"])

    if agreement.get("shared_goals"):
        pdf.section_title("Shared Goals for Our Child")
        pdf.bullet_list(agreement["shared_goals"])

    _agreement_section(pdf, "Communication", agreement.get("communication", []))
    _agreement_section(pdf, "Child Needs", agreement.get("child_needs", []))
    _agreement_section(pdf, "Household Rules", agreement.get("household_rules", []))
    _agreement_priority_items(pdf, agreement.get("priority_items", []))

    if agreement.get("open_for_discussion"):
        pdf.section_title("Open for Discussion")
        pdf.bullet_list(agreement["open_for_discussion"])

    if agreement.get("closing_note"):
        pdf.section_title("A Note from the Draft")
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, agreement["closing_note"])

    _agreement_signature_lines(pdf)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
