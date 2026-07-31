"""Regenerate every publicly-served SNC v2 sample PDF.

Outputs to /app/frontend/public/downloads/ so they're reachable at
`/downloads/<file>.pdf` from the preview URL.

Files produced:
  * snc-sample-assessment.pdf                         - blank branded workbook
  * snc-sample-individual-report-medical.pdf          - filled report, medical-only
  * snc-sample-individual-report-educational.pdf      - filled report, educational-only
  * snc-sample-individual-report-psychological.pdf    - filled report, psychological-only
  * snc-sample-individual-report.pdf                  - convenience alias for medical
  * snc-sample-comparison-report.pdf                  - filled neutral co-parent comparison
"""
from __future__ import annotations

import os
import sys

# Sibling backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF

from snc2_comparison import build_comparison
from snc2_comparison_pdf import build_comparison_pdf, _safe as _safe_txt
from snc2_questions import (
    PATHWAYS, RESPONSE_SCALE, _apply_pathway, _TEMPLATE, qid, resolve_pathways,
)
from snc2_report_content import build_report
from snc2_report_pdf import LOGO_PATH, build_snc2_pdf

from edu_deep_report import build_deep_dive_pdf as build_edu_pdf, build_deep_dive_report as build_edu_report
from psych_deep_report import build_deep_dive_pdf as build_psych_pdf, build_deep_dive_report as build_psych_report
from med_deep_report import build_deep_dive_pdf as build_med_pdf, build_deep_dive_report as build_med_report

from edu_deep_questions import public_schema as edu_public_schema
from psych_deep_questions import public_schema as psych_public_schema
from med_deep_questions import public_schema as med_public_schema


PATHWAY_IDS = ["medical", "educational", "psychological"]


def _out_dir() -> str:
    d = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "frontend", "public", "downloads",
    ))
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# 1) BLANK ASSESSMENT WORKBOOK
# ---------------------------------------------------------------------------

class _Workbook(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(14, 24, 14)
        self.alias_nb_pages()
        self.compress = False

    def header(self):
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 18, "F")
        if os.path.exists(LOGO_PATH):
            try: self.image(LOGO_PATH, x=11, y=3, w=12, h=12)
            except Exception: pass
        self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe_txt("SA CoParents  ·  Special Needs Assessment Workbook"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe_txt("Relational Mediation Prep"), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe_txt(f"Blank Assessment Workbook  ·  Page {self.page_no()} of {{nb}}"), align="C")


def _wb_write_option_list(pdf: _Workbook, options, symbol="[ ]"):
    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(30, 24, 54)
    for opt in options or []:
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(pdf.epw - 3, 4.4, _safe_txt(f"{symbol}  {opt}"))


def _wb_write_likert(pdf: _Workbook):
    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(30, 24, 54)
    pdf.set_x(pdf.l_margin + 3)
    pdf.multi_cell(pdf.epw - 3, 4.4,
        _safe_txt("(  ) 1 Strongly disagree   (  ) 2 Disagree   (  ) 3 Unsure   "
                  "(  ) 4 Agree   (  ) 5 Strongly agree   (  ) N/A"))


def _wb_write_lines(pdf: _Workbook, n=3):
    pdf.set_draw_color(200, 195, 220); pdf.set_line_width(0.2)
    for _ in range(n):
        y = pdf.get_y() + 4
        pdf.line(pdf.l_margin + 3, y, pdf.w - pdf.r_margin, y)
        pdf.set_y(y + 1)


def build_blank_workbook() -> bytes:
    pdf = _Workbook()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16); pdf.set_text_color(26, 19, 48)
    pdf.multi_cell(pdf.epw, 7, _safe_txt("Special Needs Co-Parenting Assessment")); pdf.ln(1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 4.6, _safe_txt(
        "A printable workbook you can fill in on paper before completing the "
        "online assessment. Every question is optional — you can leave anything "
        "blank. Children's needs do not always fit one category, so you may "
        "address more than one area."
    ))
    pdf.ln(2)

    # Needs categories opener
    pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(61, 26, 120)
    pdf.multi_cell(pdf.epw, 5.5, _safe_txt("What type of need are you addressing?"))
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 4.4, _safe_txt("Select every area that applies. If more than one applies, choose all of them."))
    _wb_write_option_list(pdf, [p["name"] for p in PATHWAYS])
    pdf.ln(2)

    # Steps 1-8 (one page per step block to keep the workbook writable)
    for step in _TEMPLATE:
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 5.8, _safe_txt(f"Step {step['number']}. {step['name']}"))
        for item in step["items"]:
            # Render prompt per pathway for pathway-templated items.
            if item.get("pathway") or item.get("pathway_options") or item.get("prompt_template"):
                for pid in PATHWAY_IDS:
                    resolved = _apply_pathway(item, pid)
                    pdf.ln(1)
                    pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
                    pathway_name = next(p["name"] for p in PATHWAYS if p["id"] == pid)
                    pdf.multi_cell(pdf.epw, 4.6, _safe_txt(f"{pathway_name} - {resolved.get('prompt') or ''}"))
                    _render_wb_item(pdf, resolved)
            else:
                resolved = _apply_pathway(item, "medical")  # for cross-cutting options ref
                pdf.ln(1)
                pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
                pdf.multi_cell(pdf.epw, 4.6, _safe_txt(resolved.get("prompt") or ""))
                _render_wb_item(pdf, resolved)
        pdf.ln(2)

    pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(110, 100, 130)
    pdf.multi_cell(pdf.epw, 4, _safe_txt(
        "This workbook is for co-parent preparation and mediation. It is not "
        "legal advice, does not determine parental fitness, and does not "
        "diagnose. Complete the online assessment to receive your personalised "
        "9-section polished report."
    ))
    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


def _render_wb_item(pdf: _Workbook, item):
    t = item.get("type")
    if t == "likert":
        _wb_write_likert(pdf)
    elif t in ("single", "multi"):
        symbol = "( )" if t == "single" else "[ ]"
        _wb_write_option_list(pdf, item.get("options") or [], symbol=symbol)
    else:  # textarea / text
        _wb_write_lines(pdf, n=3)


class _PathwayWorkbook(_Workbook):
    """Workbook branded to a single pathway (medical / educational / psychological)."""

    def __init__(self, pathway_name: str):
        self._pathway_name = pathway_name
        super().__init__()

    def header(self):  # noqa: D401
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 18, "F")
        if os.path.exists(LOGO_PATH):
            try: self.image(LOGO_PATH, x=11, y=3, w=12, h=12)
            except Exception: pass
        self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe_txt(f"SA CoParents  ·  {self._pathway_name} Needs Assessment"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe_txt("Special Needs Co-Parenting · Blank Workbook"), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):  # noqa: D401
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe_txt(f"{self._pathway_name} Needs Workbook  ·  Page {self.page_no()} of {{nb}}"), align="C")


def build_pathway_workbook(pathway_id: str) -> bytes:
    """Blank assessment workbook filtered to a single pathway.

    Only questions applicable to the chosen pathway are printed. Cross-cutting
    (non-pathway) questions are printed once. Prompts use the pathway's own
    wording via _apply_pathway().
    """
    pathway = next(p for p in PATHWAYS if p["id"] == pathway_id)
    pdf = _PathwayWorkbook(pathway_name=pathway["name"])
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16); pdf.set_text_color(26, 19, 48)
    pdf.multi_cell(pdf.epw, 7, _safe_txt(f"{pathway['name']} Needs — Assessment Workbook"))
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 4.6, _safe_txt(
        f"A printable workbook covering the eight-step Special Needs "
        f"assessment scoped to {pathway['name'].lower()} needs. Fill it in on "
        "paper before completing the online assessment. Every question is "
        "optional and you can leave anything blank."
    ))
    pdf.ln(2)

    for step in _TEMPLATE:
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 5.8, _safe_txt(f"Step {step['number']}. {step['name']}"))
        for item in step["items"]:
            if item.get("pathway") or item.get("pathway_options") or item.get("prompt_template"):
                # Pathway-specific question — only render for the chosen pathway
                resolved = _apply_pathway(item, pathway_id)
                if not resolved:
                    continue
            else:
                # Cross-cutting question — render once
                resolved = _apply_pathway(item, pathway_id)
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
            pdf.multi_cell(pdf.epw, 4.6, _safe_txt(resolved.get("prompt") or ""))
            _render_wb_item(pdf, resolved)
        pdf.ln(2)

    pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(110, 100, 130)
    pdf.multi_cell(pdf.epw, 4, _safe_txt(
        "This workbook is for co-parent preparation and mediation. It is not "
        "legal, medical, or psychological advice, does not determine parental "
        "fitness, and does not diagnose. Complete the online assessment to "
        "receive your personalised 9-section polished report."
    ))
    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


# ---------------------------------------------------------------------------
# 2) INDIVIDUAL REPORT SAMPLES (per pathway)
# ---------------------------------------------------------------------------

_LIKERT_SEED = {
    "step1_{p}_current_impact": 4,
    "step3_{p}_recs_understand": 4,
    "step4_{p}_same_info": 4, "step4_{p}_attend_appts": 3,
    "step4_{p}_discuss_openly": 3, "step4_{p}_shared_language": 4,
    "step4_{p}_believe_understood": 4,
    "step5_{p}_routines_consistent": 3, "step5_{p}_follow_recs": 4,
    "step5_{p}_share_updates": 3, "step5_{p}_carry_over_supplies": 4,
    "step5_{p}_handoffs_reliable": 4,
}


def _pathway_seed(pid: str) -> dict:
    common = {k.format(p=pid): v for k, v in _LIKERT_SEED.items()}
    common[qid("step1", pid, "duration")] = "1 to 3 years"
    common[qid("step1", pid, "urgency")] = "Ongoing / stable"
    common[qid("step3", pid, "recs_written")] = "Yes"
    common[qid("step6", pid, "biggest_gap")] = "Different priorities"
    common[qid("step8", pid, "next_meeting")] = "Within 2 weeks"
    common[qid("step8", pid, "top_priority")] = "Schedule the next professional appointment"
    common[qid("step8", pid, "concerns_about_plan")] = "No concerns"

    if pid == "medical":
        common[qid("step1", "medical", "concern")] = (
            "Ari has moderate persistent asthma and needs a daily controller inhaler."
        )
        common[qid("step2", "medical", "current_needs")] = [
            "Chronic medical condition", "Medication schedule", "Specialist appointments",
        ]
        common[qid("step2", "medical", "additional_areas")] = ["Sleep or fatigue issues"]
        common[qid("step3", "medical", "professionals_seen")] = ["Paediatrician", "Specialist physician"]
        common[qid("step3", "medical", "recommendation_types")] = [
            "Daily medication", "As-needed / rescue medication", "Follow-up testing or imaging",
        ]
        common[qid("step6", "medical", "agree_areas")] = "Both parents agree the daily inhaler is non-negotiable."
        common[qid("step6", "medical", "disagree_areas")] = "How to handle sleepovers at friends' houses."
        common[qid("step7", "medical", "practical_selected")] = [
            "Shared calendar for medical appointments",
            "Emergency-care instructions posted in both homes",
        ]
        common[qid("step7", "medical", "additional_practical")] = ["Written communication log"]
        common[qid("step8", "medical", "professional_next")] = "Specialist physician"
    elif pid == "educational":
        common[qid("step1", "educational", "concern")] = (
            "Ari has an IEP for dyslexia and reads below grade level."
        )
        common[qid("step2", "educational", "current_needs")] = [
            "IEP or Section 504 services", "Tutoring or academic support", "Classroom accommodations",
        ]
        common[qid("step2", "educational", "additional_areas")] = ["Family stress affecting the child"]
        common[qid("step3", "educational", "professionals_seen")] = ["Teacher", "IEP or 504 team"]
        common[qid("step3", "educational", "recommendation_types")] = [
            "Special-education services (IEP)", "Tutoring or academic support",
            "Classroom accommodations",
        ]
        common[qid("step6", "educational", "agree_areas")] = "Both parents attend IEP meetings."
        common[qid("step6", "educational", "disagree_areas")] = "Whether tutoring should continue over summer."
        common[qid("step7", "educational", "practical_selected")] = [
            "Both parents on the school contact list", "Both parents attend IEP or 504 meetings",
        ]
        common[qid("step7", "educational", "additional_practical")] = ["Regular parent-only check-ins"]
        common[qid("step8", "educational", "professional_next")] = "IEP or 504 coordinator"
    else:  # psychological
        common[qid("step1", "psychological", "concern")] = (
            "Ari has diagnosed anxiety and needs weekly therapy plus a coordinated bedtime routine."
        )
        common[qid("step2", "psychological", "current_needs")] = [
            "Anxiety-related supports", "Emotional-regulation strategies", "Counselling or psychotherapy",
        ]
        common[qid("step2", "psychological", "additional_areas")] = ["Sleep or fatigue issues"]
        common[qid("step3", "psychological", "professionals_seen")] = ["Psychologist", "Therapist or counsellor"]
        common[qid("step3", "psychological", "recommendation_types")] = [
            "Weekly therapy or counselling", "Sleep or daily-routine changes",
            "Coping-skills tools",
        ]
        common[qid("step6", "psychological", "agree_areas")] = "Both parents believe therapy is important."
        common[qid("step6", "psychological", "disagree_areas")] = "How much to talk about therapy content with each other."
        common[qid("step7", "psychological", "practical_selected")] = [
            "Consistent bedtime and morning routines in both homes",
            "Shared coping-skills toolkit that travels with the child",
        ]
        common[qid("step7", "psychological", "additional_practical")] = ["Regular parent-only check-ins"]
        common[qid("step8", "psychological", "professional_next")] = "Child therapist or counsellor"
    return common


def build_individual_sample(pid: str) -> bytes:
    r = build_report(
        parent_name="Alex Rivera",
        child_name="Ari Rivera",
        selected_pathways=[pid],
        answers=_pathway_seed(pid),
        safety_level=None,
    )
    return build_snc2_pdf(report=r)


# ---------------------------------------------------------------------------
# 3) NEUTRAL CO-PARENT COMPARISON SAMPLE
# ---------------------------------------------------------------------------

def build_comparison_sample() -> bytes:
    alex = {}
    jordan = {}
    for pid in PATHWAY_IDS:
        alex.update(_pathway_seed(pid))
        # Jordan differs on some likert answers to seed alignment variety.
        seed = _pathway_seed(pid)
        seed[qid("step1", pid, "current_impact")] = 3
        seed[qid("step4", pid, "attend_appts")] = 5
        seed[qid("step5", pid, "routines_consistent")] = 5
        seed[qid("step5", pid, "handoffs_reliable")] = 3
        jordan.update(seed)
    comparison = build_comparison(
        parent_a_name="Alex Rivera",
        parent_b_name="Jordan Rivera",
        a_pathways=PATHWAY_IDS,
        b_pathways=PATHWAY_IDS,
        a_answers=alex,
        b_answers=jordan,
    )
    return build_comparison_pdf(
        comparison=comparison,
        safety_notice=(
            "Safety notice: this is a synthetic sample. If either parent's "
            "circumstances change, revisit the Family Violence & Communication "
            "Safety Assessment before continuing to share detailed information."
        ),
    )


# ---------------------------------------------------------------------------
# 4) DEEP DIVE REPORT SAMPLES (Educational / Psychological / Medical)
# ---------------------------------------------------------------------------

def _edu_deep_sample_responses():
    return {
        "s1_diagnoses": ["Dyslexia", "ADHD"],
        "s2_state": "Texas",
        "s2_grade": "Grade 3-5",
        "s2_teacher_communication": "Sometimes",
        "s2_school_updates_both": "Rarely",
        "s3_ard_meetings_attended": "One parent attends",
        "s3_ard_communication": "Sometimes",
        "s3_ard_understand_plan": 3,
        "s4_iep_status": "Active IEP",
        "s4_iep_meetings": "One parent attends",
        "s4_iep_goals_both_know": "Rarely",
        "s4_iep_accommodations_used": "Sometimes Consistent",
        "s5_504_status": "Not applicable",
        "s6_counsellor_involved": "No",
        "s7_homework_consistent": "Rarely Consistent",
        "s7_supplies_between_homes": "Rarely",
        "s7_who_helps_homework": "Mother",
        "s8_tutoring": "Yes",
        "s8_tutoring_communication": "Rarely",
        "s9_teacher_updates_both": "Rarely",
        "s10_school_events_both_attend": "Rarely",
        "s11_educational_decisions_agree": "Sometimes Agree",
        "s11_change_school_agree": "Rarely Agree",
        "s12_notes": "",
    }


def _psych_deep_sample_responses():
    return {
        "s1_diagnoses": ["Anxiety Disorder", "ADHD"],
        "s2_provider_types": ["Child Psychologist"],
        "s2_both_know_provider": "Usually",
        "s2_attend_appointments": "Sometimes",
        "s2_both_receive_updates": "Sometimes",
        "s2_communicate_recs": "Sometimes",
        "s2_follow_recs_consistent": "Sometimes",
        "s3_provider_understands": "Confident",
        "s3_confidence_plan": "Confident",
        "s3_trust_recommendations": "Confident",
        "s3_both_confident": "Neutral",
        "s3_discuss_respectfully": 4,
        "s4_has_medication": "Yes",
        "s4_prescriber": "Psychiatrist",
        "s4_understand_areas": ["Medication purpose", "Dosage", "Administration schedule"],
        "s4_administered_consistent": 3,
        "s4_communicate_changes": 3,
        "s4_refills_coordinated": 3,
        "s4_side_effects_discussed": 3,
        "s4_concerns_reported": 3,
        "s6_attends_therapy": "Yes",
        "s6_attendance_consistency": "Usually",
        "s6_who_transports": "Mother",
        "s6_who_communicates": "Mother",
        "s6_therapist_homework": "Yes",
        "s6_homework_completed": 3,
        "s6_strategies_reinforced": 3,
        "s7_anxiety": "Sometimes Consistent",
        "s7_emotional_regulation": "Sometimes Consistent",
        "s7_meltdowns": "Rarely Consistent",
        "s7_anger": "Sometimes Consistent",
        "s7_transitions": "Rarely Consistent",
        "s7_social_interactions": "Usually Consistent",
        "s7_school_stress": "Sometimes Consistent",
        "s7_peer_relationships": "Usually Consistent",
        "s7_self_esteem": "Usually Consistent",
        "s8_planned_areas": ["Severe anxiety", "Panic attacks"],
        "s8_know_emergency_contacts": "Yes",
        "s8_know_crisis_procedures": "Partial",
        "s8_plan_in_writing": "Partial",
        "s9_appointments": "Usually",
        "s9_medication_changes": "Sometimes",
        "s9_behaviour_changes": "Usually",
        "s9_school_concerns": "Sometimes",
        "s9_treatment_recs": "Sometimes",
        "s9_therapy_progress": "Sometimes",
        "s9_new_diagnoses": "Usually",
        "s9_symptom_changes": "Sometimes",
        "s10_start_therapy": "Usually Agree",
        "s10_change_therapist": "Sometimes Agree",
        "s10_medication": "Usually Agree",
        "s10_medication_adjustments": "Sometimes Agree",
        "s10_psych_testing": "Sometimes Agree",
        "s10_neuropsych_eval": "Sometimes Agree",
        "s10_behaviour_plans": "Usually Agree",
        "s10_school_mh_services": "Sometimes Agree",
        "s10_alternative_treatments": "Sometimes Agree",
        "s10_family_therapy": "Sometimes Agree",
        "s11_routines": "Usually Consistent",
        "s11_emotional_support": "Usually Consistent",
        "s11_positive_reinforcement": "Usually Consistent",
        "s11_calm_environment": "Sometimes Consistent",
        "s11_safe_expression": "Usually Consistent",
        "s11_consistent_expectations": "Sometimes Consistent",
        "s11_healthy_coping": "Sometimes Consistent",
        "s11_stress_reduction": "Sometimes Consistent",
    }


def _med_deep_sample_responses():
    return {
        "s1_med_categories": [
            "Daily maintenance medication",
            "Rescue / emergency medication (e.g., inhaler, EpiPen, glucagon)",
            "Controlled substance (e.g., stimulant, benzodiazepine, opioid)",
        ],
        "s1_prescriber_types": ["Paediatrician", "Psychiatrist"],
        "s1_shared_info": [
            "Medication name(s)", "Dose / strength", "Purpose / condition treated",
            "Administration schedule (times, with/without food)",
            "Side effects to watch for",
        ],
        "s1_written_med_list": "Partial",
        "s1_list_updated": "Sometimes",
        "s1_both_receive_new_rx": "Sometimes",
        "s1_notes": "Ari uses a daily inhaler plus a stimulant for ADHD.",
        "s2_who_picks_up": "Mother",
        "s2_pickup_issues": [
            "Delay of one or more days after prescription written",
            "Confusion about who was picking up",
        ],
        "s2_pickup_delays": "Sometimes",
        "s2_clear_assignment": "Sometimes",
        "s2_confirmation": "Rarely",
        "s3_supply_each_home": "Sometimes",
        "s3_backup_supply": "Partial",
        "s3_refill_coordination": "Sometimes",
        "s3_runs_out_frequency": "Once",
        "s3_emergency_med_available": "Only one home",
        "s3_expired_check": "Sometimes",
        "s4_who_administers": "Mother",
        "s4_same_schedule": "Usually Consistent",
        "s4_missed_doses_freq": "Sometimes",
        "s4_dose_log": "Partial",
        "s4_handoff_dose": "Sometimes",
        "s4_child_involved": "Sometimes",
        "s5_new_prescriptions": "Sometimes",
        "s5_dose_changes": "Sometimes",
        "s5_missed_doses": "Sometimes",
        "s5_side_effects": "Sometimes",
        "s5_refill_needs": "Sometimes",
        "s5_emergency_use": "Sometimes",
        "s5_stopping_med": "Sometimes",
        "s5_provider_visits": "Usually",
        "s6_same_pharmacy": "Usually",
        "s6_both_authorized": "Yes",
        "s6_pharmacy_has_contacts": "Partial",
        "s6_pharmacist_alignment": "Sometimes",
        "s6_delivery_pickup": "No",
        "s7_financial_issues": ["Copay is a barrier"],
        "s7_cost_split_clear": "Partial",
        "s7_reimbursement": "Usually",
        "s7_insurance_current": "Yes",
        "s7_affordability": "Neutral",
        "s8_has_controlled": "Yes",
        "s8_controlled_type": "Stimulant (ADHD medication)",
        "s8_protections": [
            "Medication stored in a locked location",
            "Only the parent administers doses (never the child alone)",
        ],
        "s8_count_tracking": "Partial",
        "s8_diversion_concerns": "Mild concerns",
        "s8_provider_agreement": "Partial",
        "s9_school_meds": "Yes",
        "s9_school_items": [
            "School nurse has the current prescription order",
            "Emergency plan (e.g., asthma or anaphylaxis) is on file",
            "PRN (as-needed) medication is authorised and stocked",
        ],
        "s9_both_on_paperwork": "Partial",
        "s9_school_updates": "Sometimes",
        "s9_field_trip_ready": "Partial",
        "s10_whether_to_use": "Usually Agree",
        "s10_which_medication": "Usually Agree",
        "s10_dosing": "Usually Agree",
        "s10_side_effects": "Sometimes Agree",
        "s10_brand_vs_generic": "Sometimes Agree",
        "s10_stopping_med": "Sometimes Agree",
        "s10_as_needed_use": "Usually Agree",
        "s10_controlled_use": "Usually Agree",
    }


def build_edu_deep_sample() -> bytes:
    r = build_edu_report(parent_name="Alex Rivera", child_name="Ari Rivera",
                         responses=_edu_deep_sample_responses())
    return build_edu_pdf(report=r)


def build_psych_deep_sample() -> bytes:
    r = build_psych_report(parent_name="Alex Rivera", child_name="Ari Rivera",
                           responses=_psych_deep_sample_responses())
    return build_psych_pdf(report=r)


def build_med_deep_sample() -> bytes:
    r = build_med_report(parent_name="Alex Rivera", child_name="Ari Rivera",
                         responses=_med_deep_sample_responses())
    return build_med_pdf(report=r)


# ---------------------------------------------------------------------------
# 5) BLANK DEEP-DIVE ASSESSMENT WORKBOOKS
# ---------------------------------------------------------------------------

class _DeepDiveWorkbook(_Workbook):
    """Reuses _Workbook layout but with a deep-dive-specific title in the header footer."""

    def __init__(self, product_name: str, footer_name: str):
        self._product_name = product_name
        self._footer_name = footer_name
        super().__init__()

    def header(self):  # noqa: D401
        self.set_fill_color(245, 240, 232)
        self.rect(0, 0, self.w, 18, "F")
        if os.path.exists(LOGO_PATH):
            try: self.image(LOGO_PATH, x=11, y=3, w=12, h=12)
            except Exception: pass
        self.set_xy(26, 4); self.set_font("Helvetica", "B", 10); self.set_text_color(61, 26, 120)
        self.cell(0, 4.4, _safe_txt(f"SA CoParents  ·  {self._product_name}"), ln=1)
        self.set_x(26); self.set_font("Helvetica", "", 8); self.set_text_color(110, 100, 130)
        self.cell(0, 3.6, _safe_txt("Optional companion assessment · Blank workbook"), ln=1)
        self.set_draw_color(220, 214, 232); self.set_line_width(0.3)
        self.line(14, 19, self.w - 14, 19)
        self.set_y(22); self.set_text_color(30, 24, 54)

    def footer(self):  # noqa: D401
        self.set_y(-11); self.set_font("Helvetica", "I", 7.5); self.set_text_color(133, 126, 156)
        self.cell(0, 4, _safe_txt(f"{self._footer_name}  ·  Page {self.page_no()} of {{nb}}"), align="C")


def _render_deep_dive_item(pdf, item):
    t = item.get("type")
    if t == "likert":
        _wb_write_likert(pdf)
    elif t in ("single", "multi"):
        symbol = "( )" if t == "single" else "[ ]"
        _wb_write_option_list(pdf, item.get("options") or [], symbol=symbol)
    else:  # textarea / text
        _wb_write_lines(pdf, n=3)


def _build_deep_dive_workbook(*, product_name: str, footer_name: str,
                              intro: str, schema: dict, gate_notes: dict | None = None) -> bytes:
    pdf = _DeepDiveWorkbook(product_name=product_name, footer_name=footer_name)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16); pdf.set_text_color(26, 19, 48)
    pdf.multi_cell(pdf.epw, 7, _safe_txt(product_name)); pdf.ln(1)
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(30, 24, 54)
    pdf.multi_cell(pdf.epw, 4.6, _safe_txt(intro))
    pdf.ln(2)

    gate_notes = gate_notes or {}
    for s in schema.get("sections", []):
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(61, 26, 120)
        pdf.multi_cell(pdf.epw, 5.8, _safe_txt(f"Section {s['number']}. {s['name']}"))
        if s.get("purpose"):
            pdf.set_font("Helvetica", "I", 8.5); pdf.set_text_color(110, 100, 130)
            pdf.multi_cell(pdf.epw, 4, _safe_txt(s["purpose"]))
        gate = s.get("gate")
        if gate:
            note = gate_notes.get(s["id"]) or (
                f"Only complete this section if you answered "
                f"'{gate.get('value')}' to the '{gate.get('item')}' question."
            )
            pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(176, 42, 42)
            pdf.multi_cell(pdf.epw, 4, _safe_txt(f"Conditional: {note}"))
        pdf.set_text_color(30, 24, 54)

        for item in s.get("items", []):
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(30, 24, 54)
            pdf.multi_cell(pdf.epw, 4.6, _safe_txt(item.get("prompt") or ""))
            _render_deep_dive_item(pdf, item)
        pdf.ln(2)

    pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(110, 100, 130)
    pdf.multi_cell(pdf.epw, 4, _safe_txt(
        "This is an optional printable workbook. It does not diagnose, "
        "provide legal or medical advice, or determine parental fitness. "
        "Complete the online deep dive to receive your personalised report."
    ))
    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)


def build_edu_deep_workbook() -> bytes:
    return _build_deep_dive_workbook(
        product_name="Educational Needs — Deep Dive Assessment",
        footer_name="Educational Deep Dive Workbook",
        intro=(
            "A printable version of every question in the twelve-section optional "
            "Educational Needs deep dive. Complete it on paper first if you like, "
            "then enter your answers online to receive your personalised report. "
            "Every question is optional."
        ),
        schema=edu_public_schema(),
        gate_notes={
            "s3": "Only complete if the child's school is in Texas (ARD questions).",
        },
    )


def build_psych_deep_workbook() -> bytes:
    return _build_deep_dive_workbook(
        product_name="Psychological / Behavioural Needs — Deep Dive Assessment",
        footer_name="Psychological Deep Dive Workbook",
        intro=(
            "A printable version of every question in the eleven-section optional "
            "Psychological / Behavioural deep dive. Complete it on paper first if "
            "you like, then enter your answers online to receive your personalised "
            "report. Every question is optional."
        ),
        schema=psych_public_schema(),
        gate_notes={
            "s4": "Only complete this section if your child currently takes a psychiatric medication.",
            "s6": "Only complete this section if your child currently attends therapy.",
        },
    )


def build_med_deep_workbook() -> bytes:
    return _build_deep_dive_workbook(
        product_name="Medical · Prescription & Medication Coordination — Deep Dive Assessment",
        footer_name="Medical Deep Dive Workbook",
        intro=(
            "A printable version of every question in the ten-section optional "
            "Medical / Prescription Sharing & Medication Coordination deep dive. "
            "Complete it on paper first if you like, then enter your answers "
            "online to receive your personalised report. Every question is optional."
        ),
        schema=med_public_schema(),
        gate_notes={
            "s8": "Only complete this section if your child takes a controlled substance.",
            "s9": "Only complete this section if your child takes medication at school or before/after care.",
        },
    )


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    out = _out_dir()

    workbook = build_blank_workbook()
    open(os.path.join(out, "snc-sample-assessment.pdf"), "wb").write(workbook)
    print(f"  wrote snc-sample-assessment.pdf ({len(workbook):,} bytes)")

    for pid in PATHWAY_IDS:
        wb = build_pathway_workbook(pid)
        open(os.path.join(out, f"snc-sample-assessment-{pid}.pdf"), "wb").write(wb)
        print(f"  wrote snc-sample-assessment-{pid}.pdf ({len(wb):,} bytes)")

    for pid in PATHWAY_IDS:
        pdf = build_individual_sample(pid)
        open(os.path.join(out, f"snc-sample-individual-report-{pid}.pdf"), "wb").write(pdf)
        print(f"  wrote snc-sample-individual-report-{pid}.pdf ({len(pdf):,} bytes)")

    # Keep a stable alias for the primary in-app sample.
    default_pdf = build_individual_sample("medical")
    open(os.path.join(out, "snc-sample-individual-report.pdf"), "wb").write(default_pdf)
    print(f"  wrote snc-sample-individual-report.pdf (alias, {len(default_pdf):,} bytes)")

    comparison = build_comparison_sample()
    open(os.path.join(out, "snc-sample-comparison-report.pdf"), "wb").write(comparison)
    print(f"  wrote snc-sample-comparison-report.pdf ({len(comparison):,} bytes)")

    # Deep-dive samples
    edu = build_edu_deep_sample()
    open(os.path.join(out, "snc-sample-educational-deep-dive.pdf"), "wb").write(edu)
    print(f"  wrote snc-sample-educational-deep-dive.pdf ({len(edu):,} bytes)")
    psych = build_psych_deep_sample()
    open(os.path.join(out, "snc-sample-psychological-deep-dive.pdf"), "wb").write(psych)
    print(f"  wrote snc-sample-psychological-deep-dive.pdf ({len(psych):,} bytes)")
    med = build_med_deep_sample()
    open(os.path.join(out, "snc-sample-medical-deep-dive.pdf"), "wb").write(med)
    print(f"  wrote snc-sample-medical-deep-dive.pdf ({len(med):,} bytes)")

    # Blank deep-dive assessment workbooks (printable question list)
    edu_wb = build_edu_deep_workbook()
    open(os.path.join(out, "snc-sample-educational-deep-dive-assessment.pdf"), "wb").write(edu_wb)
    print(f"  wrote snc-sample-educational-deep-dive-assessment.pdf ({len(edu_wb):,} bytes)")
    psych_wb = build_psych_deep_workbook()
    open(os.path.join(out, "snc-sample-psychological-deep-dive-assessment.pdf"), "wb").write(psych_wb)
    print(f"  wrote snc-sample-psychological-deep-dive-assessment.pdf ({len(psych_wb):,} bytes)")
    med_wb = build_med_deep_workbook()
    open(os.path.join(out, "snc-sample-medical-deep-dive-assessment.pdf"), "wb").write(med_wb)
    print(f"  wrote snc-sample-medical-deep-dive-assessment.pdf ({len(med_wb):,} bytes)")

    print("\nDone. Files are served at /downloads/<filename>.")


if __name__ == "__main__":
    main()
