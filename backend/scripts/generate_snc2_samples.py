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
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    out = _out_dir()

    workbook = build_blank_workbook()
    open(os.path.join(out, "snc-sample-assessment.pdf"), "wb").write(workbook)
    print(f"  wrote snc-sample-assessment.pdf ({len(workbook):,} bytes)")

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

    print("\nDone. Files are served at /downloads/<filename>.")


if __name__ == "__main__":
    main()
