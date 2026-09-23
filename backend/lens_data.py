"""Legal Lens reference data: 1–10 bands, scale table, risk categories, pathways, field schema and classifiers (no FastAPI/DB dependencies)."""

TAGLINE = "SA CoParents — Starting With Alignment, Ending With Agreement"
STATUSES = ("draft", "under_review", "final", "submitted_to_court")
SAFETY_NOTE = "Safety findings may alter or override ordinary co-parenting, mediation, communication, or joint-process recommendations."
RATING_NOTE = "The rating does not automatically determine the process. Safety screening, professional judgment, court orders, and the specific needs of the child remain controlling considerations."
JOINT_OPTIONS = ("Yes", "Yes, with safeguards", "No / Not recommended at this time")
RECEIPT = ("Received", "Not Received", "Not Applicable")

INDIVIDUAL_BANDS = [
    (1, 2, "Crisis / High Conflict", ["follows some formal orders", "maintains separation when required", "participates in structured exchanges"],
     ["highly reactive communication", "poor boundaries", "repeated conflict", "child exposure to conflict", "heavy court involvement"]),
    (3, 4, "Restricted / Reactive", ["follows basic parenting schedule", "provides required child information", "participates in important child activities"],
     ["defensive communication", "delayed information sharing", "difficulty separating relationship conflict from parenting issues"]),
    (5, 6, "Business-Like / Functional", ["child-focused communication", "respects separate household boundaries", "handles routine requests appropriately"],
     ["difficulty with unexpected changes", "flexibility concerns", "occasional emotionally reactive communication"]),
    (7, 8, "Cooperative / Collaborative", ["consults on major decisions", "shares information proactively", "supports reasonable flexibility"],
     ["occasional disputes over parenting styles", "differences in household expectations"]),
    (9, 10, "Child-Centered Partnership", ["constructive communication", "supports child's relationship with other parent", "resolves disputes without involving the child"],
     ["few meaningful co-parenting difficulties"]),
]
JOINT_BANDS = [
    (1, 2, "Crisis / High Conflict", "Supervised / Strict Parallel", ["compliance with formal court orders", "structured exchanges", "maintaining physical separation"],
     ["communication collapse", "hostile exchanges", "repeated litigation", "serious safety concerns"],
     ["further court involvement", "formal orders", "highly structured communication", "supervised or structured exchanges", "separate professional support"]),
    (3, 4, "Restricted / Reactive", "Restricted Parallel Parenting", ["honoring scheduled transitions", "sharing required school and medical information", "attending child-related events"],
     ["handoff conflict", "reactive messages", "lateness", "gatekeeping minor information"],
     ["parent facilitation", "parallel-parenting structure", "BIFF", "Children in the Middle", "structured app communication", "carefully structured mediation when appropriate"]),
    (5, 6, "Business-Like / Functional", "Emerging Cooperative", ["task-focused written messages", "schedule accommodation with advance notice", "respect for separate households"],
     ["difficulty with sudden changes", "financial friction", "passive-aggressive communication"], ["traditional mediation", "child-centered mediation", "co-parenting agreement", "structured problem-solving"]),
    (7, 8, "Cooperative / Collaborative", "High Co-Parenting", ["consultation on major decisions", "flexible schedule changes", "support of extracurricular activities"],
     ["occasional parenting-style differences"], ["child-centered mediation", "collaborative problem-solving", "flexible parenting-plan modifications"]),
    (9, 10, "Child-Centered Partnership", "Unified Partnership", ["fluid communication", "active support for child's relationship with both parents", "shared problem-solving"],
     ["few meaningful co-parenting difficulties"], ["direct collaboration", "shared planning", "mediation only when needed for significant disputes"]),
]
INDIVIDUAL_BASE = ["BIFF Communication Method", "SA CoParents Communication Coach", "OurFamilyWizard / communication & tone tools", "Parenting education", "Individual professional consultation", "Therapy or counseling resources"]
JOINT_BASE = ["Children in the Middle", "Co-Parenting Agreement", "Structured communication tools", "Parent Facilitation / Coordination", "Traditional Mediation", "Child-Focused Mediation", "Educational, medical, or psychological consultation"]
INDIVIDUAL_RESOURCES = [*INDIVIDUAL_BASE, "Kelly Bernstein — Child-Focused Options Provider", "Kassandra Levay — Education Specialist", "Additional Counselor / Provider"]
JOINT_RESOURCES = ["Brad Craig — Children in the Middle", "Kelly Bernstein — Child-Focused Options Provider", "Kassandra Levay — Education Specialist", *JOINT_BASE, "Additional Expert / Provider"]

# Section 3 — Comprehensive 1–10 Co-Parenting Scale (joint & individual behaviors), verbatim from the Professional Evaluation Report form.
SCALE_TABLE = [
    {"lo": 1, "hi": 2, "label": "Crisis / High Conflict", "mode": "Supervised / Strict Parallel",
     "well": {"joint": "Adhere to legal orders; use 3rd-party sites.", "a": "Follows court boundaries.", "b": "Complies with supervised visits."},
     "poor": {"joint": "Communication collapse; hostile outbursts.", "a": "Repeated legal motions under stress.", "b": "Hostility or total refusal at handoffs."}},
    {"lo": 3, "hi": 4, "label": "Restricted / Reactive", "mode": "Restricted Parallel",
     "well": {"joint": "Honor scheduled times; share portal logs.", "a": "Keeps portal updated.", "b": "Engaged in sports/school events."},
     "poor": {"joint": "Verbal friction; reactive texts; late handoffs.", "a": "Defensive messaging; holds back info.", "b": "15-20 min late; redundant texts."}},
    {"lo": 5, "hi": 6, "label": "Business-Like / Functional", "mode": "Emerging Cooperative",
     "well": {"joint": "Task-focused messages; advance swaps (48h+).", "a": "Concise portal updates.", "b": "On time; checks portals independently."},
     "poor": {"joint": "Struggle with sudden schedule shifts.", "a": "Passive resistance to last-minute shifts.", "b": "Minor administrative lapses."}},
    {"lo": 7, "hi": 8, "label": "Cooperative / Collaborative", "mode": "High Co-Parenting",
     "well": {"joint": "Consult on health/school; informal swaps.", "a": "Proactive medical consultation.", "b": "Shares transport duties."},
     "poor": {"joint": "Clash over secondary house rules.", "a": "Pushes for single-rule priority.", "b": "Clashes over discipline styles."}},
    {"lo": 9, "hi": 10, "label": "Child-Centered Partnership", "mode": "Unified Partnership",
     "well": {"joint": "Matching rules; joint events; fluid updates.", "a": "Promotes bond with Parent B.", "b": "Complete rule alignment."},
     "poor": {"joint": "Complete absence of dysfunction.", "a": "Zero gatekeeping.", "b": "Zero transition delays."}},
]
RISK_CATEGORIES = [("coercive_control", "Coercive Control", "financial isolation, stalking, schedule monopolization"),
                   ("threats", "Threats & Intimidation", "physical threats, child abduction risk"),
                   ("hostility", "Verbal & Emotional Hostility", "intense or hostile exchanges, especially at transitions"),
                   ("child_exposure", "Child Exposure", "disagreements observed by the child")]
RISK_LEVELS = ["Not assessed", "Low Risk", "Moderate Risk", "Moderate-to-High Risk", "High Risk"]
SAFETY_ALERT = ("Important Safety Note: If high-risk IPV indicators are present, joint mediation, open messaging, and unmonitored contact are counter-indicated. "
                "In these situations, court orders, supervised exchanges, or legal safety plans take priority over standard co-parenting goals.")
PATHWAYS = [
    {"key": "direct", "lo": 8, "hi": 10, "name": "Direct structured parent discussion", "levels": "Levels 8–10", "desc": "Parents resolve the issue themselves using agreed written structure and shared calendars on SA CoParents Align."},
    {"key": "coach", "lo": 6, "hi": 10, "name": "SA CoParents Communication Coach", "levels": "Levels 6–10", "desc": "Tone-checked, BIFF-structured written communication before any escalation."},
    {"key": "facilitation", "lo": 3, "hi": 5, "name": "Parent facilitation", "levels": "Levels 3–5", "desc": "Neutral professional resolves day-to-day bumps and models child-focused communication."},
    {"key": "coordination", "lo": 2, "hi": 4, "name": "Parenting coordination", "levels": "Levels 2–4", "desc": "Structured, ongoing professional process for persistent disagreement about the parenting plan."},
    {"key": "child_centered", "lo": 5, "hi": 9, "name": "Child-focused mediation", "levels": "Levels 5–9", "desc": "Mediation focused on one specific unresolved parenting issue and the child's needs."},
    {"key": "mediation", "lo": 4, "hi": 7, "name": "Traditional mediation", "levels": "Levels 4–7", "desc": "Guided conversations to update parenting plans or schedules without court."},
    {"key": "collaborative", "lo": 4, "hi": 8, "name": "Collaborative law", "levels": "Levels 4–8", "desc": "Attorney-supported, agreement-based process with a commitment to stay out of court."},
    {"key": "therapist", "lo": 2, "hi": 7, "name": "Therapist-assisted or interdisciplinary resolution", "levels": "Levels 2–7", "desc": "Counseling-supported process where emotional or relational factors drive the dispute."},
    {"key": "consult", "lo": 1, "hi": 10, "name": "Consultation with an educational, medical, or mental-health professional", "levels": "Any level", "desc": "Subject-matter input first, followed by mediation or another structured decision-making process."},
    {"key": "expert", "lo": 1, "hi": 10, "name": "Use of an agreed neutral or subject-matter expert", "levels": "Any level", "desc": "Both parents accept one neutral expert's assessment of the disputed question."},
    {"key": "attorney", "lo": 1, "hi": 4, "name": "Attorney-assisted negotiation", "levels": "Levels 1–4", "desc": "Counsel-to-counsel negotiation where direct or facilitated processes are not appropriate."},
    {"key": "court", "lo": 1, "hi": 3, "name": "Court determination", "levels": "Levels 1–3", "desc": "When issues cannot appropriately be resolved through agreement, or a safety concern requires orders."},
]
CONFLICT_GUIDANCE = [
    ("Communication-based conflict", "Consider structured written communication using BIFF principles, a parenting communication platform, or the SA CoParents Communication Coach before escalating the dispute."),
    ("Defined parenting disagreement", "Consider child-focused mediation focused on the specific unresolved parenting issue."),
    ("Educational, medical, or psychological disagreement", "Consider consultation with an appropriate subject-matter professional followed by mediation or another structured decision-making process."),
    ("Persistent high conflict", "Consider a more structured professional process, including parent facilitation, parenting coordination, attorney-assisted negotiation, or mediation."),
    ("Safety or power-imbalance concerns", "Conflict-resolution recommendations should be considered separately and with safeguards appropriate to the circumstances."),
]
CHILD_FOCUS_CATEGORIES = [("educational", "Educational needs"), ("medical", "Medical needs"), ("psychological", "Psychological or emotional needs"), ("developmental", "Developmental needs"),
                          ("routines", "Parenting routines"), ("relationships", "Parent-child relationships"), ("communication", "Communication between parents"),
                          ("transitions", "Transitions between households"), ("special_needs", "Special needs or accommodations")]
REPORT_PRINCIPLE = ["Parents provide the information.", "SA CoParents organizes and compares the information.", "SA CoParents Align identifies potential options and pathways.", "The professional provides the judgment."]
REPORT_PURPOSE = "What do the parents' differences mean for resolving the dispute, and what options, resources, and conflict-resolution pathways may help meet the needs of the child?"
RESOURCE_CATEGORIES = ["Individual (Parent A)", "Individual (Parent B)", "Individual (Child)", "Educational Assessment", "Parent Education", "Clinical & Forensics", "Joint / Co-Parenting", "Other"]
REASSESS_INTERVALS = ["Every 90 days", "Every 90 to 180 days", "Every 180 days"]
REASSESS_UP_DEFAULT = "Move away from formal facilitators, start traditional mediation, and introduce flexible schedule swaps."
REASSESS_DOWN_DEFAULT = "Re-check safety protocols, restrict communication strictly to app logs, and bring in court oversight or clinical therapy."
INTRO_TEXT = ("The SA CoParents Align system evaluates co-parenting dynamic stability on a 1 to 10 scale. Level 1 indicates high conflict or active safety risks, while Level 10 represents a smooth, "
              "fully collaborative partnership. This report provides a complete 1–10 behavioral breakdown—identifying specific areas where co-parents and individual parents do well (strengths) "
              "and where they struggle (gaps) at every tier. It details individual placements for Parent A and Parent B, establishes a Short-Term and Long-Term Roadmap, and matches families with "
              "targeted clinical and educational resources.")

def recommended_pathway(joint_rating) -> dict | None:
    """1–2 Court · 3–4 Facilitation · 5–6 Traditional Mediation · 7–9 Child-Centered · 10 Direct Collaboration."""
    if not joint_rating:
        return None
    r = int(joint_rating)
    key = "court" if r <= 2 else "facilitation" if r <= 4 else "mediation" if r <= 6 else "child_centered" if r <= 9 else "direct"
    return next(p for p in PATHWAYS if p["key"] == key)

def resource_lists(providers: list[dict]) -> tuple[list[str], list[str]]:
    ind = [p["label"] for p in providers if "individual" in p["lists"]]
    joint = [p["label"] for p in providers if "joint" in p["lists"]]
    return [*INDIVIDUAL_BASE, *ind, "Additional Counselor / Provider"], [*joint, *JOINT_BASE, "Additional Expert / Provider"]

CONFLICT_OPTIONS = ["Further Court Hearing", "Parent Facilitation", "Traditional Mediation", "Child-Centered Mediation"]
TEXT_FIELDS = ("matter_name", "court_county", "cause_number", "professional_role", "report_date", "parent_a_name", "parent_b_name", "joint_process_appropriate", "safety_notes",
               "safety_takeaway", "parent_a_strengths", "parent_a_gaps", "parent_a_growth", "parent_a_notes", "parent_b_strengths", "parent_b_gaps", "parent_b_growth", "parent_b_notes",
               "joint_strengths", "joint_gaps", "joint_notes", "alignment_agreements", "alignment_disagreements", "partial_alignment", "alignment_summary",
               "conflict_pathway", "conflict_management_rationale", "short_term_goals", "long_term_goals", "reassess_interval", "reassess_up", "reassess_down",
               "professional_summary", "next_review_date", "signature_name", "professional_title", "fv_a_received", "fv_b_received", "shared_concerns", "sources_considered", "pathway_rationale")
LIST_FIELDS = ("parent_a_resources", "parent_b_resources", "joint_resources", "conflict_management_options", "conflict_pathways")
DICT_FIELDS = ("parent_a_provider", "parent_b_provider", "joint_provider")
INT_FIELDS = ("parent_a_rating", "parent_b_rating", "joint_rating")
ROWS_FIELDS = ("resource_rows",)
RISK_FIELDS = ("risk_screening",)
GROWTH_FIELDS = ("growth_status",)
CHILD_FIELDS = ("child_focus",)

def growth_lines(rep: dict, role: str) -> list[dict]:
    """Key Growth Areas for a parent with met-at-reassessment flags."""
    status = (rep.get("growth_status") or {}).get(role) or {}
    return [{"text": g.strip(), "met": bool(status.get(g.strip()))} for g in (rep.get(f"parent_{role}_growth") or "").split("\n") if g.strip()]

AI_MODELS = [{"key": "gemini", "label": "Gemini 3.1 Pro"}, {"key": "openai", "label": "GPT-5.4 Mini"}]

def classify_individual(rating) -> dict | None:
    if not rating:
        return None
    lo, hi, label, strengths, gaps = next(b for b in INDIVIDUAL_BANDS if b[0] <= int(rating) <= b[1])
    return {"range": f"{lo}-{hi}", "label": label, "strengths": strengths, "gaps": gaps, "row": next(i for i, r in enumerate(SCALE_TABLE) if r["lo"] <= int(rating) <= r["hi"])}


def classify_joint(rating) -> dict | None:
    if not rating:
        return None
    lo, hi, label, mode, strengths, gaps, guidance = next(b for b in JOINT_BANDS if b[0] <= int(rating) <= b[1])
    return {"range": f"{lo}-{hi}", "label": label, "mode": mode, "strengths": strengths, "gaps": gaps, "guidance": guidance,
            "row": next(i for i, r in enumerate(SCALE_TABLE) if r["lo"] <= int(rating) <= r["hi"]), "pathway": recommended_pathway(rating)}
