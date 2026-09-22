"""Fictional, fully filled-in Professional Evaluation Report — public sample (no real data)."""
from legal_lens import (AI_MODELS, CONFLICT_OPTIONS, INTRO_TEXT, JOINT_OPTIONS, PATHWAYS, RATING_NOTE, REASSESS_INTERVALS, RECEIPT, RESOURCE_CATEGORIES, RISK_CATEGORIES, RISK_LEVELS,
                        SAFETY_ALERT, SAFETY_NOTE, SCALE_TABLE, STATUSES, TAGLINE, classify_individual, classify_joint)
from sample_professional_report import SAMPLE_COURT, SAMPLE_PRO

_REPORT = {
    "id": "sample-legal-lens", "case_id": "sample-case", "status": "final", "professional_name": SAMPLE_PRO["name"], "professional_role": SAMPLE_PRO["pro_role"],
    "created_at": "2026-05-04T14:00:00+00:00", "updated_at": "2026-05-29T16:10:00+00:00", "finalized_at": "2026-05-29T16:10:00+00:00", "report_date": "2026-05-29",
    "matter_name": "Co-parenting — Transitions & Communication — M. Carter (age 9)", "court_county": SAMPLE_COURT["court_name"], "cause_number": SAMPLE_COURT["cause_number"],
    "parent_a_name": "Parent A", "parent_b_name": "Parent B",
    "fv_a_received": "Received", "fv_b_received": "Received", "joint_process_appropriate": "Yes, with safeguards",
    "risk_screening": {"coercive_control": {"level": "Low Risk", "note": "No active financial isolation, stalking, or schedule monopolization."},
                       "threats": {"level": "Low Risk", "note": "No physical threats or child abduction risks reported."},
                       "hostility": {"level": "Moderate-to-High Risk", "note": "History of intense or hostile text exchanges during transitions."},
                       "child_exposure": {"level": "Moderate Risk", "note": "Disagreements observed by the child during physical transition windows."}},
    "safety_notes": "Both individual family violence screenings were received and reviewed. Safeguard applied: joint sessions are conducted with the professional present and information is exchanged in writing.",
    "safety_takeaway": "This case does not require an emergency safety override, but direct face-to-face negotiations aren't a good fit right now due to handoff tension.",
    "parent_a_rating": 4, "parent_a_strengths": "Consistently sticks to scheduled swap times and keeps medical and school records updated in the portal.",
    "parent_a_gaps": "Prefers written app messages over direct phone calls. Tends to get defensive under stress, sometimes holds back activity details, and struggles to separate past personal feelings about Parent B from Parent B's relationship with the child.",
    "parent_a_growth": "Focus on sending calm, strictly factual messages instead of reactive replies.\nShare school and extracurricular details openly and early.\nKeep personal feelings about Parent B separate from Parent B's role as a parent.",
    "parent_a_notes": "",
    "parent_b_rating": 4, "parent_b_strengths": "Very involved in the child's activities and eager to show up for school events.",
    "parent_b_gaps": "Runs 15–20 minutes late for drop-offs/pickups and sends multiple follow-up texts if Parent A doesn't reply right away. Relies on Parent A to pass along info rather than checking school portals independently.",
    "parent_b_growth": "Focus on being consistently on time for all scheduled transitions.\nKeep written messages brief, clear, and non-repetitive.\nLog into school and medical accounts directly to stay informed independently.",
    "parent_b_notes": "",
    "joint_rating": 4, "joint_strengths": "Both parents honor basic custody schedules and keep record portals updated.",
    "joint_gaps": "Physical transitions and direct messaging.",
    "joint_notes": "While both parents do well at honoring basic custody schedules and keeping record portals updated, they do poorly during physical transitions and direct messaging. "
                   "All communications should stay on SA CoParents Align with clear, independent household boundaries.",
    "short_term_goals": "Transition Handoff Protocol: Shift custodial transitions to neutral locations or school pickup/drop-off. Keep greetings brief and polite.\n"
                        "App-Only Communication Window: Move all non-emergency messaging exclusively to SA CoParents Align. Parent A replies within 24 hours without reactive language; Parent B limits messages to one concise thread per topic.\n"
                        "Transition Promptness Target (Parent B): Establish a strict 10-minute grace period for drop-offs and pickups.\n"
                        "Shared Educational Access (Parent A & Kassandra Levay): Grant Parent B direct login access to school portals and share psychoeducational reports upfront.",
    "long_term_goals": "Step Down Monitoring: Work with Parent Facilitator (Kelly Bernstein) to reduce facilitator check-ins from weekly to monthly.\n"
                       "Flexible Schedule Swaps: After 90 days of consistent promptness and calm messaging, introduce a structured Right of First Refusal policy.\n"
                       "Unified Two-Household Expectations: Complete Children in the Middle (Brad Craig) to align major household rules (bedtimes, screen time limits) across homes.\n"
                       "Independent Administration: Parent B assumes full management of medical/extracurricular calendars; Parent A steps back from monitoring Parent B's parenting time.",
    "resource_rows": [
        {"category": "Individual (Parent A)", "resource": "Individual Therapy / Counseling", "focus": "Processes divorce stress, emotional regulation, and separating partner conflict from co-parenting goals."},
        {"category": "Individual (Parent B)", "resource": "Individual Coaching / Behavioral Therapy", "focus": "Focuses on time management, healthy communication boundaries, and administrative independence."},
        {"category": "Individual (Child)", "resource": "Child Therapy", "focus": "Provides a safe, neutral space to express feelings without getting caught in the middle."},
        {"category": "Educational Assessment", "resource": "Kassandra Levay", "focus": "Specialized Psychoeducational Testing & Academic Advocacy to resolve school disputes fairly."},
        {"category": "Parent Education", "resource": "Children in the Middle (Brad Craig, LMSW-IPR, CFLE)", "focus": "Court-certified course on stopping child triangulation, managing two homes, and business messaging."},
        {"category": "Clinical & Forensics", "resource": "Kelly Bernstein, MS, LCDC, LPC (Alamo Heights Forensic & Individual Therapy)", "focus": "Court-appointed Parent Facilitation and Coordination to resolve daily schedule friction and enforcement of court orders."},
    ],
    "reassess_interval": "Every 90 to 180 days",
    "reassess_up": "When Score Moves Up (Level 5–6): Move away from formal facilitators, start traditional mediation, and introduce flexible schedule swaps.",
    "reassess_down": "When Score Drops (Level 1–2): Re-check safety protocols, restrict communication strictly to app logs, and bring in court oversight or clinical therapy.",
    "next_review_date": "2026-08-28", "conflict_pathway": "facilitation",
    "conflict_management_rationale": "Parent Facilitation & Coordination (Levels 3–5) — Level 4 Recommendation: a neutral professional (Kelly Bernstein) resolves day-to-day bumps, supported by Children in the Middle "
                                     "(Brad Craig), individual counseling, and neutral educational testing (Kassandra Levay).",
    "signature_name": SAMPLE_PRO["name"], "professional_title": "Licensed Professional Counselor · Parenting Facilitator",
}


def sample_legal_lens() -> dict:
    rep = dict(_REPORT)
    return {"is_sample": True, "title": "Sample Professional Evaluation Report — fictional data", "report": rep,
            "readiness": [{"key": "assessment_a", "label": "Parent A Assessment Received", "done": True}, {"key": "assessment_b", "label": "Parent B Assessment Received", "done": True},
                          {"key": "joint", "label": "Joint Report Received", "done": True}, {"key": "fv_a", "label": "Parent A Family Violence Assessment Received", "done": True, "na": False},
                          {"key": "fv_b", "label": "Parent B Family Violence Assessment Received", "done": True, "na": False}],
            "classification": {"parent_a": classify_individual(rep["parent_a_rating"]), "parent_b": classify_individual(rep["parent_b_rating"]), "joint": classify_joint(rep["joint_rating"])},
            "library": {"conflict_options": CONFLICT_OPTIONS, "joint_process_options": JOINT_OPTIONS, "receipt_options": RECEIPT, "statuses": STATUSES, "ai_models": AI_MODELS, "scale_table": SCALE_TABLE,
                        "risk_categories": RISK_CATEGORIES, "risk_levels": RISK_LEVELS, "pathways": PATHWAYS, "resource_categories": RESOURCE_CATEGORIES, "reassess_intervals": REASSESS_INTERVALS, "providers": []},
            "notes": {"safety": SAFETY_NOTE, "rating": RATING_NOTE, "tagline": TAGLINE, "alert": SAFETY_ALERT, "intro": INTRO_TEXT},
            "case": {"id": "sample-case", "case_code": "SA-26-TRN-000000", "child_name": "M. Carter", "subject_label": "Transitions & Communication"},
            "professional": SAMPLE_PRO, "court": SAMPLE_COURT}
