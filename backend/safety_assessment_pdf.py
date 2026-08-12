"""PDF rendering for the IPV Communication Safety Assessment.

Uses the same fpdf2 stack and brand assets as the rest of the app so the
downloadable / emailed report looks like it belongs in the SA CoParents family.
"""
from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

from fpdf import FPDF


# Re-use brand colors and replacements from pdf_service to stay visually consistent.
SAGE = (132, 157, 142)
TERRA = (194, 135, 113)
SAND = (245, 243, 233)
TEXT_DARK = (42, 54, 49)
TEXT_MID = (92, 107, 100)
DANGER = (155, 47, 47)
WARN = (160, 92, 30)
INFO = (60, 89, 138)
OK = (60, 120, 90)

ORG_NAME = "SA CoParents"
ORG_TAGLINE = "Relational Mediation Prep"
ORG_PHONE = "210-224-1667"
ORG_EMAIL = "mattsossi@bsossi.com"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "sa_coparents_logo.png")


_UNICODE_REPLACEMENTS = {
    "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"', "\u2026": "...", "\u2022": "*",
    "\u00A0": " ",
}


def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    for ch, repl in _UNICODE_REPLACEMENTS.items():
        s = s.replace(ch, repl)
    return s.encode("latin-1", "replace").decode("latin-1")


_TONE_COLORS = {
    "danger": DANGER,
    "warning": WARN,
    "info": INFO,
    "ok": OK,
}


class SafetyAssessmentPDF(FPDF):
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
        self.set_font("Helvetica", "B", 15)
        self.set_xy(42, 9)
        self.cell(0, 7, "Trauma-Informed Safety and Functioning Lens", ln=1)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*TEXT_MID)
        self.set_x(42)
        self.cell(0, 4, "Family Violence and Communication Safety Screen (TISFL)", ln=1)
        self.set_x(42)
        self.cell(0, 4, f"{ORG_NAME} - {ORG_TAGLINE}", ln=1)
        self.set_x(42)
        self.cell(0, 4, f"{ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(44)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            "Not a diagnosis or legal advice. If in immediate danger, call 911. "
            "National DV Hotline: 800-799-7233.",
            align="C", ln=1,
        )

    def section_title(self, text: str):
        self.ln(3)
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

    def small_muted(self, text: str):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*TEXT_MID)
        self.multi_cell(0, 5, text)
        self.ln(1)
        self.set_text_color(*TEXT_DARK)

    def bullet_list(self, items: List[str]):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*TEXT_DARK)
        for item in items:
            self.set_x(18)
            self.cell(4, 6, chr(149))
            self.multi_cell(0, 6, str(item))
        self.ln(1)


def _render_ai_summary(pdf: SafetyAssessmentPDF, text: str, heading: str = "AI summary") -> None:
    """Compact italic summary block used above each section. Renders
    nothing when `text` is empty so the layout stays clean if the LLM
    call failed or wasn't run."""
    text = (text or "").strip()
    if not text:
        return
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*INFO)
    pdf.set_x(15)
    pdf.cell(0, 5, _safe(heading.upper()), ln=1)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(15)
    pdf.multi_cell(180, 5.2, _safe(text))
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(1.5)


def _render_meta(pdf: SafetyAssessmentPDF, user_name: str, generated_at: str) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, f"Prepared for: {user_name}", ln=1)
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        pretty = dt.strftime("%B %d, %Y")
    except Exception:
        pretty = generated_at
    pdf.cell(0, 6, f"Generated: {pretty}", ln=1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.ln(2)


def _render_disclaimer(pdf: SafetyAssessmentPDF) -> None:
    from trauma_lens import SELF_REFLECTION_DISCLAIMER
    pdf.section_title("Important — read this first")
    pdf.small_muted(SELF_REFLECTION_DISCLAIMER)
    pdf.small_muted(
        "In addition: if there is immediate danger, call 911. If communication with "
        "the other parent creates fear, danger, or retaliation, direct communication may not "
        "be appropriate."
    )


def _render_pathway(pdf: SafetyAssessmentPDF, result: Dict[str, Any], pathway_ai: str = "") -> None:
    level = int(result.get("level") or 4)
    tone = str(result.get("pathway_tone") or "info")
    color = _TONE_COLORS.get(tone, INFO)
    pdf.section_title(f"Recommended pathway - Level {level}")
    # Coloured rule above
    pdf.set_fill_color(*color)
    pdf.set_draw_color(*color)
    pdf.set_text_color(*color)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, str(result.get("pathway_title") or ""), ln=1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, str(result.get("pathway_summary") or ""))
    pdf.ln(2)
    _render_ai_summary(pdf, pathway_ai, heading="Why this pathway · AI summary")
    recs = result.get("recommendations") or []
    if recs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, "Recommendations", ln=1)
        pdf.bullet_list([str(r) for r in recs])


def _render_answers(
    pdf: SafetyAssessmentPDF,
    title: str,
    rows: List[Dict[str, str]],
) -> None:
    pdf.section_title(title)
    pdf.set_font("Helvetica", "", 10)
    for i, row in enumerate(rows, start=1):
        ans = (row.get("answer") or "-").strip().lower()
        label_color = TEXT_DARK
        if ans == "yes":
            label_color = DANGER
        elif ans == "no":
            label_color = OK
        # Question text
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(15)
        pdf.multi_cell(170, 5, f"{i}. {row.get('text','')}")
        # Answer chip line
        pdf.set_x(15)
        pdf.set_text_color(*label_color)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, f"Answer: {(row.get('answer') or '-').upper()}", ln=1)
        pdf.ln(1)
    pdf.set_text_color(*TEXT_DARK)


def _render_texas_block(pdf: SafetyAssessmentPDF, block: str) -> None:
    pdf.section_title("Texas safety resources")
    pdf.body_text(block)


def _render_interpretation_rules(pdf: SafetyAssessmentPDF, rules: List[str]) -> None:
    """Print the two lens interpretation rules in a bordered box. These
    must be surfaced wherever the lens's output is rendered."""
    if not rules:
        return
    pdf.section_title("Two interpretation rules")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*INFO)
    pdf.set_x(15)
    pdf.cell(0, 5, "How to read this report", ln=1)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "", 10)
    for i, rule in enumerate(rules, start=1):
        pdf.set_x(18)
        pdf.cell(6, 6, f"{i}.")
        pdf.multi_cell(0, 6, str(rule))
    pdf.ln(1)


def _render_three_findings(pdf: SafetyAssessmentPDF, lens: Dict[str, Any]) -> None:
    """Render the three separate findings (Pattern, Trauma, Plan). Kept
    intentionally separate so they aren't collapsed into a single
    coparenting score."""
    if not lens:
        return
    findings = lens.get("findings") or {}
    order = ("family_violence_pattern", "trauma_impact", "parenting_plan_implications")
    labels = {
        "family_violence_pattern": ("Finding 1 - Family-Violence Pattern", DANGER),
        "trauma_impact": ("Finding 2 - Trauma Impact (behavioural signals only)", WARN),
        "parenting_plan_implications": ("Finding 3 - Parenting-Plan Implications", INFO),
    }
    pdf.section_title("Three findings")
    for key in order:
        block = findings.get(key)
        if not block:
            continue
        title, colour = labels[key]
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*colour)
        pdf.set_x(15)
        pdf.cell(0, 6, title, ln=1)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*TEXT_MID)
        pdf.set_x(15)
        pdf.multi_cell(0, 5, f"Core question: {block.get('core_question','')}")
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_x(15)
        pdf.multi_cell(0, 5.5, str(block.get("headline") or ""))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(15)
        pdf.multi_cell(0, 5.2, str(block.get("summary") or ""))
        if block.get("non_diagnostic_note"):
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*TEXT_MID)
            pdf.set_x(15)
            pdf.multi_cell(0, 4.8, str(block.get("non_diagnostic_note")))
            pdf.set_text_color(*TEXT_DARK)
        if block.get("arrangement_spectrum"):
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*INFO)
            pdf.set_x(15)
            pdf.cell(0, 5, f"Recommended structure: {block.get('arrangement_spectrum')}", ln=1)
            pdf.set_text_color(*TEXT_DARK)
        pdf.ln(2)


def build_safety_assessment_pdf(
    *,
    user_name: str,
    generated_at: str,
    result: Dict[str, Any],
    section_1_rows: List[Dict[str, str]],
    section_2_rows: List[Dict[str, str]],
    texas_resource_block: str,
    excluded_sections: set | list | None = None,
    ai_summaries: Dict[str, str] | None = None,
) -> bytes:
    """Render the Family Violence & Communication Safety Assessment PDF.

    `ai_summaries` is optional. When present, four keys are honoured:

        * ``overall``    — one-paragraph executive summary shown at the
                           very top of the report, above the disclaimer.
        * ``pathway``    — 2-3 sentence framing shown inside the
                           "Recommended pathway" block.
        * ``section_1``  — narrative above Section 1's answer list.
        * ``section_2``  — narrative above Section 2's answer list.

    Missing / empty keys render nothing (graceful fallback when the
    LLM was unavailable). This means the PDF still produces a valid
    document if the Emergent LLM key is not configured.
    """
    ex = set(excluded_sections or [])
    ai = ai_summaries or {}
    lens = (result or {}).get("lens") or {}
    pdf = SafetyAssessmentPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    _render_meta(pdf, user_name, generated_at)
    # Executive summary sits above the disclaimer so a mediator opening
    # the file immediately sees the plain-language framing.
    if ai.get("overall"):
        pdf.section_title("Executive summary")
        _render_ai_summary(pdf, ai.get("overall") or "", heading="AI summary")
    _render_disclaimer(pdf)
    # Trauma-Informed Safety and Functioning Lens layer.
    _render_interpretation_rules(pdf, list(lens.get("interpretation_rules") or []))
    _render_three_findings(pdf, lens)
    # Pathway and Texas resources are locked-on for safety reasons.
    _render_pathway(pdf, result, pathway_ai=ai.get("pathway") or "")
    if "section_1" not in ex:
        _render_ai_summary(pdf, ai.get("section_1") or "", heading="Section 1 · AI summary")
        _render_answers(pdf, "Section 1 - Immediate safety screen (past 12 months)", section_1_rows)
    if "section_2" not in ex:
        _render_ai_summary(pdf, ai.get("section_2") or "", heading="Section 2 · AI summary")
        _render_answers(pdf, "Section 2 - Communication readiness", section_2_rows)
    _render_texas_block(pdf, texas_resource_block)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
