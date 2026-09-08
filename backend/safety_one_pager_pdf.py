"""For-Your-Professional One-Pager PDF.

A very short branded PDF the parent can hand to their lawyer,
DV advocate, or family counsellor. Its purpose is to translate the
Trauma-Informed Safety and Functioning Lens (TISFL) framing into a
concrete handoff artifact.

The one-pager:
  * Names what this tool IS and IS NOT (universal self-reflection
    disclaimer at the top).
  * Summarises the four findings at a glance (headlines only — no
    raw Section-1 behavioural language).
  * Lists the specific questions the professional should now explore
    with the parent, tuned to whichever finding surfaced concerns.
  * Includes assessment_id + generated date + a footer line marking
    it as non-forensic.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF

from safety_assessment_pdf import (
    SAND, TEXT_DARK, TEXT_MID, DANGER, WARN, INFO, OK,
    ORG_NAME, ORG_TAGLINE, ORG_PHONE, ORG_EMAIL, LOGO_PATH,
    _safe,
)
from trauma_lens import LENS_NAME, SELF_REFLECTION_DISCLAIMER
from pdf_base import render_pdf_copyright


# ---------- Recommended-questions bank ----------
#
# Keyed by the finding domain that surfaced the concern. The
# professional receives a targeted list, not a generic checklist.

_QUESTIONS_BY_DOMAIN: Dict[str, List[str]] = {
    "pattern": [
        "What behaviours have you experienced from the other parent in the past 12 months? Can you describe the most recent incident?",
        "Do you feel free to disagree with or say no to the other parent without fear of retaliation?",
        "Are you aware of any protective orders, restraining orders, or safety agreements — in force, sought, or declined?",
        "Do you or the children have a current safety plan? Is anyone else aware of it?",
    ],
    "trauma": [
        "Are you sleeping? Are you eating? What has your body been telling you lately?",
        "Do you find yourself rehearsing messages to the other parent, or avoiding notifications from them?",
        "Do you have someone you can call at 3am if you need to? What does your support scaffold look like?",
        "Have you been offered — or accessed — trauma-informed counselling since the events began?",
    ],
    "plan": [
        "What arrangement structure would you actually feel safe with — cooperative, structured, parallel, supervised exchanges, supervised contact, or a pause?",
        "What written communication tools are you willing to use? Which are non-starters?",
        "Are there review points built into your current plan? What would trigger stepping up or down a tier?",
        "Who are the trusted adults the children can turn to independent of either parent?",
    ],
    "child": [
        "How are the children showing distress right now — sleep, appetite, school, behaviour, play?",
        "Does any child have a safe, consistent adult outside the parents to talk to?",
        "Have any of the children spontaneously described feeling unsafe with the other parent?",
        "Are the children being asked to carry messages, keep secrets, or hide their feelings about one parent from the other?",
    ],
    "general": [
        "What outcome are you hoping this professional consultation will help you reach in the next 30 / 90 / 365 days?",
        "What do you need from a professional right now that you're not currently getting?",
        "What decisions must be made in the next 4 weeks?",
        "What resources — legal, financial, community — do you have available or need to access?",
    ],
}


class _OnePagerPDF(FPDF):
    def __init__(self, assessment_id: str, generated_at: str):
        super().__init__()
        self._assessment_id = assessment_id
        self._generated_at = generated_at

    def cell(self, w=0, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, _safe(txt), *args, **kwargs)

    def multi_cell(self, w, h, txt="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(txt), *args, **kwargs)

    def header(self):
        self.set_fill_color(*SAND)
        self.rect(0, 0, 210, 26, "F")
        if os.path.exists(LOGO_PATH):
            try:
                self.image(LOGO_PATH, x=12, y=4, w=18, h=18)
            except Exception:
                pass
        self.set_text_color(*TEXT_DARK)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(34, 6)
        self.cell(0, 6, "For your professional", ln=1)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT_MID)
        self.set_x(34)
        self.cell(0, 3.5, f"One-page handoff from {ORG_NAME}", ln=1)
        self.set_x(34)
        self.cell(0, 3.5, f"{ORG_PHONE} - {ORG_EMAIL}", ln=1)
        self.set_text_color(*TEXT_DARK)
        self.set_y(30)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*TEXT_MID)
        self.cell(
            0, 4,
            f"Assessment {self._assessment_id} - Generated {self._generated_at} - "
            f"Non-forensic self-report screen. Not a substitute for professional evaluation.",
            align="C", ln=1,
        )
        self.set_text_color(*TEXT_DARK)


        render_pdf_copyright(self)
def _section_heading(pdf: _OnePagerPDF, text: str, colour):
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*colour)
    pdf.set_x(15)
    pdf.cell(0, 5.5, text.upper(), ln=1)
    pdf.set_draw_color(*colour)
    y = pdf.get_y()
    pdf.line(15, y, 45, y)
    pdf.set_text_color(*TEXT_DARK)


def _small_body(pdf: _OnePagerPDF, text: str, italic: bool = False):
    pdf.set_font("Helvetica", "I" if italic else "", 9)
    pdf.set_x(15)
    pdf.multi_cell(180, 4.6, text)


def _pick_questions(lens: Dict[str, Any]) -> List[str]:
    """Pick a targeted set of professional questions based on the lens
    findings actually present. Always includes the 'general' bank at
    the end. Keeps the list at <=10 items so the page stays a page."""
    findings = (lens or {}).get("findings") or {}
    picks: List[str] = []
    seen: set = set()

    def _extend(bank_key: str, limit: int) -> None:
        for q in _QUESTIONS_BY_DOMAIN.get(bank_key, []):
            if q in seen:
                continue
            picks.append(q)
            seen.add(q)
            if len([p for p in picks if p in _QUESTIONS_BY_DOMAIN[bank_key]]) >= limit:
                break

    fvp = findings.get("family_violence_pattern") or {}
    if "coercive" in (fvp.get("headline") or "").lower() or fvp.get("pattern_typology"):
        _extend("pattern", 3)
    trauma = findings.get("trauma_impact") or {}
    if trauma.get("domain_signals") or "impact" in (trauma.get("headline") or "").lower():
        _extend("trauma", 2)
    plan = findings.get("parenting_plan_implications") or {}
    if plan.get("feasibility_tier"):
        _extend("plan", 2)
    child = findings.get("child_experience") or {}
    if child:
        _extend("child", 2)
    _extend("general", 2)
    return picks[:10]


def build_one_pager_pdf(
    *,
    user_name: str,
    generated_at: str,
    assessment_id: str,
    result: Dict[str, Any],
) -> bytes:
    """Render the one-page handoff PDF."""
    lens = (result or {}).get("lens") or {}
    findings = lens.get("findings") or {}
    try:
        pretty = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).strftime(
            "%B %d, %Y"
        )
    except Exception:
        pretty = str(generated_at or "")
    pdf = _OnePagerPDF(assessment_id=assessment_id, generated_at=pretty)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # 1. WHAT THIS IS (self-reflection disclaimer)
    _section_heading(pdf, "What this is", INFO)
    _small_body(pdf, SELF_REFLECTION_DISCLAIMER)

    # 2. WHO THIS IS FOR
    _section_heading(pdf, "How to use this handoff", INFO)
    _small_body(
        pdf,
        "The parent named below completed a structured self-reflection screen "
        "under the {lens} (TISFL). This one-pager summarises what surfaced so "
        "you can decide, in your professional judgement, what to explore next. "
        "It is not a forensic evaluation and should not be treated as one.".format(lens=LENS_NAME),
        italic=True,
    )

    # 3. PARENT + META
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(15)
    pdf.cell(30, 5, "Parent:")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 5, user_name or "-", ln=1)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.set_x(15)
    pdf.cell(30, 5, "Level:")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_DARK)
    lvl = int((result or {}).get("level") or 4)
    pdf.cell(0, 5, f"{lvl} of 4", ln=1)

    # 4. FOUR FINDINGS — headlines only (never raw behavioural language)
    _section_heading(pdf, "Findings at a glance", DANGER)
    finding_order = [
        ("family_violence_pattern", "1 - Family-Violence Pattern"),
        ("trauma_impact", "2 - Trauma Impact"),
        ("parenting_plan_implications", "3 - Parenting-Plan Implications"),
        ("child_experience", "4 - Child Experience"),
    ]
    for key, label in finding_order:
        block = findings.get(key)
        if not block:
            continue
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(15)
        pdf.cell(0, 4.6, label, ln=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(15)
        pdf.multi_cell(180, 4.4, str(block.get("headline") or ""))
        # Feasibility tier for Finding 3.
        tier = block.get("feasibility_tier")
        if tier:
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_text_color(*INFO)
            pdf.set_x(15)
            pdf.multi_cell(
                180, 4.2,
                f"Recommended tier: {tier.get('label')} (review in {tier.get('review_point_days')} days)",
            )
            pdf.set_text_color(*TEXT_DARK)
        pdf.ln(0.2)

    # 5. QUESTIONS FOR YOU TO EXPLORE
    _section_heading(pdf, "Questions to explore with this parent", OK)
    _small_body(
        pdf,
        "These are the areas the parent's answers suggest a professional could most helpfully open up. Use them as prompts, not as a checklist.",
        italic=True,
    )
    pdf.ln(0.5)
    questions = _pick_questions(lens)
    pdf.set_font("Helvetica", "", 9)
    for i, q in enumerate(questions, start=1):
        pdf.set_x(15)
        pdf.multi_cell(180, 4.6, f"{i}. {q}")
        pdf.ln(0.3)

    # 6. WHAT THIS TOOL IS NOT
    _section_heading(pdf, "What this tool is NOT", WARN)
    _small_body(
        pdf,
        "This tool is not a clinical, forensic, legal, or professional evaluation. "
        "It does not diagnose either parent, adjudicate abuse, replace a court-appointed "
        "family-violence evaluator, or produce evidence admissible without corroboration. "
        "Please verify anything critical with independent evidence.",
        italic=True,
    )

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", "replace")
    if isinstance(out, bytearray):
        return bytes(out)
    return out
