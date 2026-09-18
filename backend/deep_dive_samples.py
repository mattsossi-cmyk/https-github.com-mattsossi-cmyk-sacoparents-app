"""Public sample PDFs for the Educational / Medical / Psychological
deep-dive reports.

Iter204 · The landing page's Tier-2 "When your child needs more support"
cards previously had no "View sample (PDF)" parity with the three Core
Report cards. This module produces per-pathway sample PDFs on demand
using the SAME `build_deep_dive_report` + `build_deep_dive_pdf`
pipeline the real parent-facing endpoints use — so any future report
tweak automatically flows into these samples too.

Persona: fictional but plausible parent "Sam Rivera" reporting on their
9-year-old "Alex". Responses are hand-tuned so each sample PDF renders
a mix of `strength` and `flagged` sections (rather than a monochrome
report where every section is fine, which would waste the sample).

No PII, no real data. Safe to serve unauthenticated.
"""
from __future__ import annotations

from typing import Any, Dict


# --------------------------- Persona defaults --------------------------- #

SAMPLE_PARENT_NAME = "Sam Rivera"
SAMPLE_CHILD_NAME = "Alex"


# ------------------------ Edu / Psych response set --------------------- #
# Both edu and psych use identical 25-item Likert schemas
# (p1_q1..p5_q25, 0-4 point scale). The two pathways score differently
# but their response shape is the same, so we share one persona.
#
# Scoring intent:
#   Part 1 (Communication / Info-sharing)   → mostly 4s → STRENGTH
#   Part 2 (Decision-making)                → 2-3s → moderate
#   Part 3 (Consistency between homes)      → 1-2s → FLAGGED
#   Part 4 (Emotional / support signals)    → 3s   → moderate
#   Part 5 (Logistics / practicalities)     → 3-4s → moderate/strength

_EDU_PSYCH_TEMPLATE: Dict[str, int] = {
    # Part 1 — strength
    "p1_q1": 4, "p1_q2": 4, "p1_q3": 3, "p1_q4": 4, "p1_q5": 4,
    # Part 2 — moderate
    "p2_q6": 3, "p2_q7": 2, "p2_q8": 3, "p2_q9": 2, "p2_q10": 3,
    # Part 3 — flagged
    "p3_q11": 1, "p3_q12": 1, "p3_q13": 2, "p3_q14": 1, "p3_q15": 1,
    # Part 4 — moderate
    "p4_q16": 3, "p4_q17": 3, "p4_q18": 2, "p4_q19": 3, "p4_q20": 3,
    # Part 5 — moderate/strength
    "p5_q21": 3, "p5_q22": 4, "p5_q23": 3, "p5_q24": 3, "p5_q25": 4,
}


# ------------------------- Med response set ---------------------------- #
# Medical uses domain-specific KEYS + STRING values ("Always" / "Usually" /
# "Sometimes" / "Rarely" / "Never", "Yes"/"Partial"/"No", plus multi
# lists for s1_med_categories / s1_prescriber_types / s1_shared_info).
# Persona: one daily maintenance med + one PRN, shared between two
# homes with reasonable info-sharing but uneven pick-up coordination.

_MED_RESPONSES: Dict[str, Any] = {
    # Section 1 — Prescription info sharing (strong)
    "s1_med_categories": ["Daily maintenance medication",
                          "As-needed (PRN) medication"],
    "s1_prescriber_types": ["Paediatrician"],
    "s1_shared_info":     ["Medication name(s)", "Dose / strength",
                           "Purpose / condition treated"],
    "s1_written_med_list": "Yes",
    "s1_list_updated": "Usually",
    "s1_both_receive_new_rx": "Usually",
    "s1_notes": "",
    # Section 2 — Pick-up (flagged)
    "s2_who_picks_up": "Mother",
    "s2_pickup_issues": ["Delay of one or more days after prescription written"],
    "s2_pickup_delays": "Sometimes",
    "s2_clear_assignment": "Sometimes",
    "s2_confirmation": "Rarely",
    # Section 3 — Supply between homes (moderate)
    "s3_supply_each_home": "Usually",
    "s3_backup_supply": "Partial",
    "s3_refill_coordination": "Sometimes",
    "s3_runs_out_frequency": "2-3 times",
    "s3_emergency_med_available": "Only one home",
    # Section 4 — Administration (moderate)
    "s4_dose_confirmed": "Usually",
    "s4_missed_dose_communication": "Sometimes",
    "s4_double_dose_prevention": "Usually",
    "s4_admin_technique": "Usually Consistent",
    # Section 5 — Timing consistency (moderate/strength)
    "s5_same_time_both_homes": "Usually Consistent",
    "s5_missed_when_travel": "Rarely",
    "s5_documented_schedule": "Yes",
    "s5_time_zone_adjustments": "Usually",
    # Section 6 — Side effects / monitoring (moderate)
    "s6_side_effects_shared": "Usually",
    "s6_symptom_log_shared": "Sometimes",
    "s6_response_change_shared": "Usually",
    # Section 7 — Provider communication (strong)
    "s7_both_parents_access": "Yes",
    "s7_visits_attended": "Usually",
    "s7_release_signed": "Yes",
    "s7_summary_sent": "Usually",
    # Section 8 — Controlled substances (not applicable)
    "s8_has_controlled": "No",
    # Section 9 — School meds
    "s9_school_meds": "No",
    # Section 10 — Areas of disagreement (moderate)
    "s10_which_medication": "Usually Agree",
    "s10_whether_to_use": "Usually Agree",
    "s10_dosing": "Always Agree",
    "s10_side_effects": "Usually Agree",
    "s10_as_needed_use": "Sometimes Agree",
    "s10_brand_vs_generic": "Always Agree",
    "s10_stopping_med": "Usually Agree",
    "s10_controlled_use": "Always Agree",
}


# --------------------------- Public builders --------------------------- #

def build_sample_edu_pdf() -> bytes:
    """Sample Educational Deep-Dive PDF using the real report pipeline."""
    from edu_deep_report import build_deep_dive_report, build_deep_dive_pdf
    report = build_deep_dive_report(
        parent_name=SAMPLE_PARENT_NAME,
        child_name=SAMPLE_CHILD_NAME,
        responses=dict(_EDU_PSYCH_TEMPLATE),
    )
    return build_deep_dive_pdf(report=report)


def build_sample_psych_pdf() -> bytes:
    """Sample Psychological Deep-Dive PDF using the real report pipeline."""
    from psych_deep_report import build_deep_dive_report, build_deep_dive_pdf
    report = build_deep_dive_report(
        parent_name=SAMPLE_PARENT_NAME,
        child_name=SAMPLE_CHILD_NAME,
        responses=dict(_EDU_PSYCH_TEMPLATE),
    )
    return build_deep_dive_pdf(report=report)


def build_sample_med_pdf() -> bytes:
    """Sample Medical Deep-Dive PDF using the real report pipeline."""
    from med_deep_report import build_deep_dive_report, build_deep_dive_pdf
    report = build_deep_dive_report(
        parent_name=SAMPLE_PARENT_NAME,
        child_name=SAMPLE_CHILD_NAME,
        responses=dict(_MED_RESPONSES),
    )
    return build_deep_dive_pdf(report=report)


PATHWAY_BUILDERS = {
    "educational":   build_sample_edu_pdf,
    "medical":       build_sample_med_pdf,
    "psychological": build_sample_psych_pdf,
}
