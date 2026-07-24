"""Special Needs Assessment question catalogue (v2 — child-centered rebuild).

Structure (5 reframing questions):
    1. What does the child need?           → CHILD_PROFILE
    2. Where do the parents agree?          → DOMAIN_ITEMS (behaviour-based)
    3. Where is coordination breaking down? → DOMAIN_ITEMS + CONSISTENCY (Phase B)
    4. What safeguards or structures help?  → SAFEGUARDS (Phase D)
    5. What should happen next?             → derived from the coordination scores

Each item declares its type, category and (where scored) the domain it feeds.
The frontend renders items via `type`; the scorer reads `category` + `domain`.

Scored items use the shared 7-point coordination scale defined below.
"""

# ---------------------------------------------------------------------------
# Answer scales
# ---------------------------------------------------------------------------

# Shared behaviour-based scale used by every scored coordination item.
# The `weight` column feeds the deterministic scorer. Values that mean
# "no useful signal for this item" (na, dont_know, disagree) are captured
# without penalising either parent — they surface in the report as
# "unknown" or "parents disagree" tags instead of dragging the score.
COORDINATION_SCALE = [
    {"value": "almost_always", "label": "Almost always", "weight": 100},
    {"value": "usually",       "label": "Usually",       "weight": 78},
    {"value": "sometimes",     "label": "Sometimes",     "weight": 50},
    {"value": "rarely",        "label": "Rarely",        "weight": 22},
    {"value": "almost_never",  "label": "Almost never",  "weight": 0},
    {"value": "na",            "label": "Not applicable",  "weight": None},
    {"value": "dont_know",     "label": "I do not know",   "weight": None},
    {"value": "disagree",      "label": "Parents disagree about this", "weight": None},
]

# Concerns concerning-parties classification.
CONCERN_SOURCES = [
    {"value": "documented",    "label": "Documented — diagnosed or identified by a qualified professional"},
    {"value": "under_eval",    "label": "Under evaluation — a professional assessment is pending"},
    {"value": "parent_observed", "label": "Parent-observed — noticed by one or both parents but not yet evaluated"},
]

# Domains — the 7 coordination scores map 1:1 onto these keys where sensible.
# Some domains group into one coordination score (see scoring module).
DOMAINS = [
    {"id": "medical",       "label": "Medical care",        "help": "Diagnoses, medications, appointments, specialists, emergencies."},
    {"id": "development",   "label": "Development",         "help": "Speech, motor skills, learning, executive function, milestones."},
    {"id": "education",     "label": "Education",           "help": "IEP/504 plan, accommodations, attendance, homework, school communication."},
    {"id": "communication", "label": "Communication",       "help": "Verbal, nonverbal, assistive, processing time."},
    {"id": "emotional",     "label": "Emotional regulation","help": "Anxiety, transitions, sensory overload, triggers, calming strategies."},
    {"id": "daily_living",  "label": "Daily living",        "help": "Sleep, food, hygiene, toileting, equipment, personal assistance."},
    {"id": "social",        "label": "Social development",  "help": "Friendships, activities, inclusion, social supports."},
    {"id": "transitions",   "label": "Transitions between homes", "help": "Schedule changes, belongings, medication transfer, recovery time."},
]

# ---------------------------------------------------------------------------
# 1. Child Profile — begin with the child, not the diagnosis.
# ---------------------------------------------------------------------------

CHILD_PROFILE = [
    {"id": "child_name",         "type": "short_text", "prompt": "What name (or nickname) should we use for your child in this space?",
     "help": "This stays private to your account.", "required": True},
    {"id": "child_age",          "type": "short_text", "prompt": "How old is your child?"},
    {"id": "strengths",          "type": "long_text",  "prompt": "What are your child's strengths, interests, and favourite activities?",
     "help": "The report leads with this so your child isn't defined by limitations."},
    {"id": "what_helps",         "type": "long_text",  "prompt": "What helps your child feel safe, calm, understood, and successful?"},
    {"id": "child_communication","type": "long_text",  "prompt": "How does your child communicate needs, worries, or distress?"},
    {"id": "child_voice",        "type": "long_text",  "prompt": "What would your child want both parents to understand?"},
]

# ---------------------------------------------------------------------------
# 2. Concerns — documented vs under-eval vs parent-observed.
# ---------------------------------------------------------------------------

CONCERNS_ITEMS = [
    {"id": "documented_needs", "type": "long_text",
     "prompt": "Documented diagnoses or professionally identified needs (if any):",
     "help": "E.g. autism dx from a psychologist, an IEP, a paediatric epilepsy diagnosis."},
    {"id": "under_eval_needs", "type": "long_text",
     "prompt": "Currently under evaluation — professional assessment pending (if any):",
     "help": "E.g. speech evaluation booked, GP referral, IEP eligibility meeting scheduled."},
    {"id": "parent_observed_needs", "type": "long_text",
     "prompt": "Parent-observed concerns not yet evaluated (if any):",
     "help": "Something you (or the other parent) have noticed. Naming it here does not require the other parent to agree."},
]

# ---------------------------------------------------------------------------
# 3. Domain items — behaviour-based, past 6 months.
#    Each item is scored on the COORDINATION_SCALE and feeds a specific
#    coordination-score dimension via `dim`.
#
#    Coordination-score dimensions (7 total):
#      understanding    — do both parents understand the child's needs?
#      info_sharing     — is medical/school/therapy info exchanged in time?
#      follow_through   — do agreed actions actually happen?
#      consistency      — Phase B (Consistency Between Homes) feeds this
#      professional     — collaboration with professionals & records access
#      decision_making  — timely decisions when a decision is required
#      transitions      — handovers stable, med & equipment transfer intact
# ---------------------------------------------------------------------------

DOMAIN_ITEMS = [
    # Medical -----------------------------------------------------------------
    {"id": "med_info_shared", "domain": "medical", "dim": "info_sharing",
     "prompt": "During the past six months, how often did both parents receive important medical information (results, prescriptions, changes) within a reasonable time?"},
    {"id": "med_follow_through", "domain": "medical", "dim": "follow_through",
     "prompt": "How often were medications, dosages, and medical routines actually followed as prescribed across both homes?"},
    {"id": "med_decision_delayed", "domain": "medical", "dim": "decision_making", "reverse": True,
     "prompt": "Has a recommended evaluation, appointment, medication, or medical service been delayed because the parents could not reach a decision?"},

    # Development ------------------------------------------------------------
    {"id": "dev_progress_shared", "domain": "development", "dim": "info_sharing",
     "prompt": "How often did both parents receive updates on your child's developmental progress (speech, motor skills, executive function)?"},
    {"id": "dev_next_step_agreed", "domain": "development", "dim": "decision_making",
     "prompt": "When a professional recommended the next step (referral, follow-up screening), how often did both parents agree to move forward?"},

    # Education --------------------------------------------------------------
    {"id": "edu_records_shared", "domain": "education", "dim": "info_sharing",
     "prompt": "How often did both parents receive report cards, IEP/504 documents, and school communications on time?"},
    {"id": "edu_meetings_attended", "domain": "education", "dim": "professional",
     "prompt": "How often did both parents attend (in person or remotely) IEP / 504 / parent-teacher meetings?"},
    {"id": "edu_accommodations_followed", "domain": "education", "dim": "follow_through",
     "prompt": "How often were school accommodations (extra time, sensory breaks, homework supports) upheld across both homes?"},

    # Communication ----------------------------------------------------------
    {"id": "comm_style_understood", "domain": "communication", "dim": "understanding",
     "prompt": "How often does the other parent recognise and honour your child's communication style (verbal, non-verbal, assistive, processing time)?"},
    {"id": "comm_change_flagged", "domain": "communication", "dim": "info_sharing",
     "prompt": "When a change in your child's communication was noticed (regression, new signs of distress), how often was it shared between homes promptly?"},

    # Emotional regulation ---------------------------------------------------
    {"id": "reg_triggers_understood", "domain": "emotional", "dim": "understanding",
     "prompt": "How often do both parents recognise your child's known emotional triggers and calming strategies?"},
    {"id": "reg_strategy_shared", "domain": "emotional", "dim": "consistency",
     "prompt": "How often are calming strategies (sensory tools, quiet time, transitional objects) used consistently across both homes?"},

    # Daily living ----------------------------------------------------------
    {"id": "dl_routine_consistent", "domain": "daily_living", "dim": "consistency",
     "prompt": "How consistent are core daily routines (sleep, food, hygiene, screen time) across both homes when needed for your child's functioning?"},
    {"id": "dl_equipment_available", "domain": "daily_living", "dim": "follow_through",
     "prompt": "How often was necessary equipment (adaptive tools, medical devices, mobility aids) available in the right home at the right time?"},

    # Social ----------------------------------------------------------------
    {"id": "soc_activities_supported", "domain": "social", "dim": "follow_through",
     "prompt": "How often were your child's social activities (therapy groups, playdates, sports) supported by both homes?"},
    {"id": "soc_inclusion_shared", "domain": "social", "dim": "info_sharing",
     "prompt": "How often was information about your child's social experience (bullying, friendships, exclusion) shared between homes?"},

    # Transitions -----------------------------------------------------------
    {"id": "trans_belongings_intact", "domain": "transitions", "dim": "transitions",
     "prompt": "How often do your child's belongings (medications, equipment, comfort items) transfer intact between homes?"},
    {"id": "trans_recovery_time", "domain": "transitions", "dim": "transitions",
     "prompt": "How often is your child given the recovery time they need after transitions between homes?"},
    {"id": "trans_change_communicated", "domain": "transitions", "dim": "info_sharing",
     "prompt": "When a schedule change was needed, how often was it communicated between parents in a way that centred the child?"},

    # Professional collaboration --------------------------------------------
    {"id": "pro_records_shared", "domain": "medical", "dim": "professional",
     "prompt": "How often does the other parent share medical, therapy, or school records when you request them?"},
    {"id": "pro_provider_communication", "domain": "medical", "dim": "professional",
     "prompt": "How often do professionals (doctors, therapists, teachers) have accurate contact information for both parents?"},
]

# ---------------------------------------------------------------------------
# 4. Disagreement response self-reflection (single question).
# ---------------------------------------------------------------------------

DISAGREEMENT_RESPONSE = {
    "id": "concern_response",
    "type": "single_select",
    "prompt": "When the other parent raises a medical, developmental, educational, or behavioural concern about your child, how do you usually respond?",
    "help": "There are no right answers — this is a self-reflection prompt only you will see.",
    "options": [
        {"value": "review",     "label": "I review the information objectively."},
        {"value": "records",    "label": "I request records or professional input to understand it better."},
        {"value": "participate","label": "I participate in the evaluation or appointment."},
        {"value": "delay",      "label": "I delay or wait to see if it resolves on its own."},
        {"value": "dismiss",    "label": "I usually think the concern is not real."},
        {"value": "conflict",   "label": "I treat it primarily as a conflict with the other parent."},
    ],
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def all_scored_ids():
    """Ids of every item that is scored on the coordination scale."""
    return [q["id"] for q in DOMAIN_ITEMS]


def all_question_ids():
    """Every id in the assessment — used for input validation."""
    ids = [q["id"] for q in CHILD_PROFILE]
    ids += [q["id"] for q in CONCERNS_ITEMS]
    ids += [q["id"] for q in DOMAIN_ITEMS]
    ids += [DISAGREEMENT_RESPONSE["id"]]
    return ids


def get_schema():
    """The full assessment as returned to the frontend."""
    return {
        "version": 2,
        "scale": COORDINATION_SCALE,
        "concern_sources": CONCERN_SOURCES,
        "domains": DOMAINS,
        "sections": [
            {"id": "child_profile", "title": "Begin with the child", "items": CHILD_PROFILE},
            {"id": "concerns",      "title": "Diagnosed, under evaluation, or parent-observed", "items": CONCERNS_ITEMS},
            {"id": "coordination",  "title": "How you coordinate across 8 domains", "items": DOMAIN_ITEMS, "grouped_by": "domain"},
            {"id": "disagreement",  "title": "When the other parent raises a concern", "items": [DISAGREEMENT_RESPONSE]},
        ],
    }
