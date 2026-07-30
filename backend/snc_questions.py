"""SA CoParents — Special Needs Co-Parenting Assessment (SNC) framework.

Verbatim implementation of the user's 13-section spec.
See /app/memory/SPECIAL_NEEDS_REBUILD_SPEC.md for the source of truth.

Scored categories: Sections 2, 3, 4, 5, 6, 7, 8, 9, 10, 12  (ten rows).
Unscored / context: Sections 1, 11 (safety, special), 13.
Multi-select / intake fields in all sections are context, not scored.
Section 6 consistency scale is numerically mapped (see CONSISTENCY_SCALE).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# 5-point Likert plus N/A. Used by Sections 2, 3, 4, 5, 7, 8, 9, 10, 12.
RESPONSE_SCALE: List[Dict[str, Any]] = [
    {"value": 1, "label": "Strongly disagree"},
    {"value": 2, "label": "Disagree"},
    {"value": 3, "label": "Unsure"},
    {"value": 4, "label": "Agree"},
    {"value": 5, "label": "Strongly agree"},
    {"value": "na", "label": "Not applicable or unknown"},
]

# Section 6 consistency scale — mapped to numeric 1-5 for scoring parity with
# the Likert sections. "Unknown" and "Not applicable" are excluded from averages
# just like "na" on Likert items.
CONSISTENCY_SCALE: List[Dict[str, Any]] = [
    {"value": 5,        "label": "Consistent"},
    {"value": 4,        "label": "Mostly consistent"},
    {"value": 3,        "label": "Sometimes inconsistent"},
    {"value": 2,        "label": "Frequently inconsistent"},
    {"value": "unknown","label": "Unknown"},
    {"value": "na",     "label": "Not applicable"},
]


# ---------------------------------------------------------------------------
# 13 sections. Each item has: id, type ∈ {intake, likert, consistency, multi,
# text, open}. Scored items carry `scored=True`. Multi-selects and free-text
# are context-only.
# ---------------------------------------------------------------------------

SECTIONS: List[Dict[str, Any]] = [
    # -----------------------------------------------------------------------
    # Section 1 — About Your Child (all context)
    # -----------------------------------------------------------------------
    {
        "id": "s1", "number": 1, "name": "About Your Child",
        "scored": False,
        "items": [
            {"id": "s1_age",             "type": "text",     "prompt": "Child's age and current grade."},
            {"id": "s1_strengths",       "type": "textarea", "prompt": "What are your child's greatest strengths?"},
            {"id": "s1_joy",             "type": "textarea", "prompt": "What activities, interests, or relationships bring your child joy?"},
            {"id": "s1_diagnosis_status","type": "single",   "prompt": "Has your child received a diagnosis or professional evaluation?",
             "options": [
                 "No diagnosis or evaluation",
                 "Evaluation is being considered",
                 "Evaluation is scheduled",
                 "Evaluation is in progress",
                 "Diagnosis or eligibility determination received",
                 "Prefer not to answer",
             ]},
            {"id": "s1_needs", "type": "multi", "prompt": "Which needs currently apply?",
             "options": [
                 "Learning or academic", "Speech or language", "Autism-related",
                 "ADHD or executive functioning", "Intellectual or developmental",
                 "Physical or mobility", "Chronic medical", "Sensory processing",
                 "Behavioral", "Anxiety or emotional regulation", "Trauma-related",
                 "Social development", "Sleep", "Feeding or nutrition", "Other",
             ]},
            {"id": "s1_needs_narrative", "type": "textarea", "prompt": "Briefly describe your understanding of your child's needs."},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 2 — Understanding and Acceptance
    # -----------------------------------------------------------------------
    {
        "id": "s2", "number": 2, "name": "Understanding and Acceptance", "scored": True,
        "items": [
            {"id": "s2_q1", "type": "likert", "scored": True, "prompt": "I understand my child's diagnosis, suspected condition, or areas of concern."},
            {"id": "s2_q2", "type": "likert", "scored": True, "prompt": "I recognize how my child's needs affect daily life."},
            {"id": "s2_q3", "type": "likert", "scored": True, "prompt": "I can separate my concerns about the other parent from my child's actual needs."},
            {"id": "s2_q4", "type": "likert", "scored": True, "prompt": "I am willing to consider information that differs from my current understanding."},
            {"id": "s2_q5", "type": "likert", "scored": True, "prompt": "I rely on qualified professionals when medical, educational, or developmental questions arise."},
            {"id": "s2_q6", "type": "likert", "scored": True, "prompt": "I understand that my child may behave differently in each home."},
            {"id": "s2_q7", "type": "likert", "scored": True, "prompt": "I believe the other parent's observations should be considered even when they differ from mine."},
            {"id": "s2_q8", "type": "likert", "scored": True, "prompt": "Both parents generally acknowledge that our child may need additional support."},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 3 — Medical and Mental Healthcare
    # -----------------------------------------------------------------------
    {
        "id": "s3", "number": 3, "name": "Medical and Mental Healthcare", "scored": True,
        "items": [
            {"id": "s3_providers", "type": "multi", "prompt": "Does your child currently receive care from any of the following?",
             "options": [
                 "Pediatrician", "Medical specialist", "Psychiatrist", "Psychologist",
                 "Counselor or therapist", "Occupational therapist",
                 "Physical therapist", "Speech-language pathologist",
                 "Behavioral specialist", "Other provider",
             ]},
            {"id": "s3_q1", "type": "likert", "scored": True, "prompt": "I know the names and contact information of my child's providers."},
            {"id": "s3_q2", "type": "likert", "scored": True, "prompt": "I receive timely information about appointments and recommendations."},
            {"id": "s3_q3", "type": "likert", "scored": True, "prompt": "Both parents can access appropriate medical records."},
            {"id": "s3_q4", "type": "likert", "scored": True, "prompt": "Recommended appointments are scheduled and attended."},
            {"id": "s3_q5", "type": "likert", "scored": True, "prompt": "Medications are administered consistently and as prescribed."},
            {"id": "s3_q6", "type": "likert", "scored": True, "prompt": "Medication changes and side effects are promptly shared."},
            {"id": "s3_q7", "type": "likert", "scored": True, "prompt": "Therapy exercises or treatment plans are followed in my home."},
            {"id": "s3_q8", "type": "likert", "scored": True, "prompt": "I understand what to do during a medical or behavioral emergency."},
            {"id": "s3_q9", "type": "likert", "scored": True, "prompt": "The parents have a workable process for resolving disagreements about treatment."},
            {"id": "s3_open_coord",  "type": "textarea", "prompt": "What medical or mental-health needs require the greatest coordination?"},
            {"id": "s3_open_missed", "type": "textarea", "prompt": "Have appointments, medication, therapy, or treatment ever been delayed or missed? Explain."},
            {"id": "s3_open_improve","type": "textarea", "prompt": "What would improve consistency between homes?"},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 4 — Kindergarten and Elementary School
    # -----------------------------------------------------------------------
    {
        "id": "s4", "number": 4, "name": "Kindergarten and Elementary School", "scored": True,
        "items": [
            {"id": "s4_school_name", "type": "text",  "prompt": "What school does your child attend?"},
            {"id": "s4_supports",    "type": "multi", "prompt": "Does your child have any of the following?",
             "options": [
                 "Individualized Education Program (IEP)", "Section 504 Plan",
                 "Response to Intervention or MTSS support",
                 "Behavior Intervention Plan", "Individualized Health Plan",
                 "Classroom accommodations", "Informal teacher supports",
                 "Evaluation pending", "None", "Unsure",
             ]},
            {"id": "s4_q1",  "type": "likert", "scored": True, "prompt": "I understand my child's educational plan and accommodations."},
            {"id": "s4_q2",  "type": "likert", "scored": True, "prompt": "I know who to contact at the school when concerns arise."},
            {"id": "s4_q3",  "type": "likert", "scored": True, "prompt": "Both parents receive school notices, progress reports, and teacher communications."},
            {"id": "s4_q4",  "type": "likert", "scored": True, "prompt": "Both parents attend or meaningfully participate in school meetings when appropriate."},
            {"id": "s4_q5",  "type": "likert", "scored": True, "prompt": "Homework and reading expectations are reasonably consistent between homes."},
            {"id": "s4_q6",  "type": "likert", "scored": True, "prompt": "School supplies, technology, medication, and assistive devices travel reliably between homes."},
            {"id": "s4_q7",  "type": "likert", "scored": True, "prompt": "Attendance and morning routines support my child's learning."},
            {"id": "s4_q8",  "type": "likert", "scored": True, "prompt": "Both parents follow the child's educational plan."},
            {"id": "s4_q9",  "type": "likert", "scored": True, "prompt": "Teachers receive consistent and accurate information from the parents."},
            {"id": "s4_q10", "type": "likert", "scored": True, "prompt": "Educational disagreements are handled without placing the child or school staff in the middle."},
            {"id": "s4_open_most_important", "type": "textarea", "prompt": "What educational support is most important for your child?"},
            {"id": "s4_open_problem",        "type": "textarea", "prompt": "What school-related problem occurs most often?"},
            {"id": "s4_open_changes",        "type": "textarea", "prompt": "What changes would help your child succeed?"},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 5 — Transitions, Pickup, and Drop-Off
    # -----------------------------------------------------------------------
    {
        "id": "s5", "number": 5, "name": "Transitions, Pickup, and Drop-Off", "scored": True,
        "items": [
            {"id": "s5_q1",  "type": "likert", "scored": True, "prompt": "My child understands the parenting-time schedule."},
            {"id": "s5_q2",  "type": "likert", "scored": True, "prompt": "Pickup and drop-off times are predictable."},
            {"id": "s5_q3",  "type": "likert", "scored": True, "prompt": "Necessary medication, schoolwork, clothing, comfort items, and equipment accompany the child."},
            {"id": "s5_q4",  "type": "likert", "scored": True, "prompt": "Schedule changes are communicated early enough to support the child."},
            {"id": "s5_q5",  "type": "likert", "scored": True, "prompt": "Exchanges occur without exposing the child to conflict."},
            {"id": "s5_q6",  "type": "likert", "scored": True, "prompt": "Each parent understands the child's transition-related triggers."},
            {"id": "s5_q7",  "type": "likert", "scored": True, "prompt": "The child receives appropriate preparation before changing homes."},
            {"id": "s5_q8",  "type": "likert", "scored": True, "prompt": "Both homes support calming or decompression time after transitions."},
            {"id": "s5_q9",  "type": "likert", "scored": True, "prompt": "Transportation arrangements accommodate the child's physical, sensory, or behavioral needs."},
            {"id": "s5_q10", "type": "likert", "scored": True, "prompt": "The parents have a backup plan when transportation or caregiving arrangements fail."},
            {"id": "s5_open_difficult",  "type": "textarea", "prompt": "What makes transitions difficult for your child?"},
            {"id": "s5_open_items",      "type": "textarea", "prompt": "Which items must always travel with your child?"},
            {"id": "s5_open_checklist",  "type": "single",   "prompt": "Would a written transition checklist help?",
             "options": ["Yes", "No", "Unsure"]},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 6 — Daily Routines Across Homes (consistency scale, scored)
    # -----------------------------------------------------------------------
    {
        "id": "s6", "number": 6, "name": "Daily Routines Across Homes", "scored": True,
        "items": [
            *[
                {"id": f"s6_{k}", "type": "consistency", "scored": True, "prompt": label}
                for k, label in [
                    ("sleep",       "Sleep and bedtime"),
                    ("morning",     "Morning routine"),
                    ("medication",  "Medication"),
                    ("meals",       "Meals and nutrition"),
                    ("hygiene",     "Hygiene"),
                    ("homework",    "Homework and reading"),
                    ("screen_time", "Screen time"),
                    ("sensory",     "Sensory supports"),
                    ("behavioral",  "Behavioral expectations"),
                    ("therapy",     "Therapy exercises"),
                    ("devices",     "Assistive devices"),
                    ("regulation",  "Emotional-regulation strategies"),
                ]
            ],
            {"id": "s6_open_essential",  "type": "textarea", "prompt": "Which routines must remain consistent for your child to function well?"},
            {"id": "s6_open_flexibility","type": "textarea", "prompt": "Where is flexibility appropriate?"},
            {"id": "s6_open_negative",   "type": "textarea", "prompt": "Which differences between homes appear to negatively affect the child?"},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 7 — Communication and Information Sharing
    # -----------------------------------------------------------------------
    {
        "id": "s7", "number": 7, "name": "Communication and Information Sharing", "scored": True,
        "items": [
            {"id": "s7_q1", "type": "likert", "scored": True, "prompt": "Parents exchange child-related information accurately and promptly."},
            {"id": "s7_q2", "type": "likert", "scored": True, "prompt": "Communications focus on the child rather than past relationship conflict."},
            {"id": "s7_q3", "type": "likert", "scored": True, "prompt": "Each parent provides updates after significant appointments or school meetings."},
            {"id": "s7_q4", "type": "likert", "scored": True, "prompt": "Both parents can ask reasonable questions without the conversation escalating."},
            {"id": "s7_q5", "type": "likert", "scored": True, "prompt": "Important decisions are confirmed in writing."},
            {"id": "s7_q6", "type": "likert", "scored": True, "prompt": "Parents avoid using the child as a messenger."},
            {"id": "s7_q7", "type": "likert", "scored": True, "prompt": "Professionals are not asked to take sides in parental disputes."},
            {"id": "s7_q8", "type": "likert", "scored": True, "prompt": "A structured communication method would improve coordination."},
            {"id": "s7_preferred", "type": "multi", "prompt": "Preferred communication structure",
             "options": [
                 "Direct conversation", "Text message", "Email",
                 "Co-parenting application", "BIFF-style written communication",
                 "Communication through attorneys",
                 "Communication through a parenting facilitator or coordinator",
                 "Information exchanged directly through professionals",
                 "Another structured method",
             ]},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 8 — Special School Events
    # -----------------------------------------------------------------------
    {
        "id": "s8", "number": 8, "name": "Special School Events", "scored": True,
        "items": [
            {"id": "s8_events_context", "type": "multi", "prompt": "Consider (context only)",
             "options": [
                 "Parent-teacher conferences", "IEP or Section 504 meetings",
                 "School performances", "Field trips", "Awards ceremonies",
                 "Class parties", "Testing days",
                 "Therapy or intervention meetings", "School transitions",
                 "Special-education evaluations",
             ]},
            {"id": "s8_q1", "type": "likert", "scored": True, "prompt": "Both parents receive advance notice of important events."},
            {"id": "s8_q2", "type": "likert", "scored": True, "prompt": "Both parents understand who may attend."},
            {"id": "s8_q3", "type": "likert", "scored": True, "prompt": "The child can participate without worrying about parental conflict."},
            {"id": "s8_q4", "type": "likert", "scored": True, "prompt": "Parents can attend together safely and appropriately when beneficial."},
            {"id": "s8_q5", "type": "likert", "scored": True, "prompt": "Separate attendance or virtual participation is available when needed."},
            {"id": "s8_q6", "type": "likert", "scored": True, "prompt": "Parents avoid discussing disputes during the event."},
            {"id": "s8_q7", "type": "likert", "scored": True, "prompt": "A designated parent shares information when only one parent can attend."},
            {"id": "s8_q8", "type": "likert", "scored": True, "prompt": "School staff understand the appropriate communication arrangement."},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 9 — Extracurricular Activities
    # -----------------------------------------------------------------------
    {
        "id": "s9", "number": 9, "name": "Extracurricular Activities", "scored": True,
        "items": [
            {"id": "s9_activities", "type": "textarea", "prompt": "What activities does your child currently participate in?"},
            {"id": "s9_benefit",    "type": "textarea", "prompt": "Does the activity support the child's interests, development, or therapeutic needs?"},
            {"id": "s9_q1",  "type": "likert", "scored": True, "prompt": "The activity is appropriate for the child's abilities and tolerance."},
            {"id": "s9_q2",  "type": "likert", "scored": True, "prompt": "Both parents receive schedules and contact information."},
            {"id": "s9_q3",  "type": "likert", "scored": True, "prompt": "Transportation responsibilities are clear."},
            {"id": "s9_q4",  "type": "likert", "scored": True, "prompt": "Equipment and uniforms are available when needed."},
            {"id": "s9_q5",  "type": "likert", "scored": True, "prompt": "Costs and payment responsibilities are understood."},
            {"id": "s9_q6",  "type": "likert", "scored": True, "prompt": "The activity does not create an unreasonable burden for the child."},
            {"id": "s9_q7",  "type": "likert", "scored": True, "prompt": "Coaches or instructors receive necessary medical or accommodation information."},
            {"id": "s9_q8",  "type": "likert", "scored": True, "prompt": "Parents behave appropriately when attending at the same time."},
            {"id": "s9_q9",  "type": "likert", "scored": True, "prompt": "The child is not pressured to choose which parent attends."},
            {"id": "s9_q10", "type": "likert", "scored": True, "prompt": "There is a process for approving new activities."},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 10 — Decision-Making and Professional Guidance
    # -----------------------------------------------------------------------
    {
        "id": "s10", "number": 10, "name": "Decision-Making and Professional Guidance", "scored": True,
        "items": [
            {"id": "s10_q1", "type": "likert", "scored": True, "prompt": "Parents can identify when a professional opinion is needed."},
            {"id": "s10_q2", "type": "likert", "scored": True, "prompt": "Decisions are based on the child's needs rather than parental control."},
            {"id": "s10_q3", "type": "likert", "scored": True, "prompt": "Both parents have an opportunity to provide relevant information."},
            {"id": "s10_q4", "type": "likert", "scored": True, "prompt": "Professional recommendations are documented and shared."},
            {"id": "s10_q5", "type": "likert", "scored": True, "prompt": "Parents understand who has legal authority to make particular decisions."},
            {"id": "s10_q6", "type": "likert", "scored": True, "prompt": "There is a workable process for time-sensitive decisions."},
            {"id": "s10_q7", "type": "likert", "scored": True, "prompt": "The child is not asked to decide disputes that belong to the adults."},
            {"id": "s10_supports", "type": "multi", "prompt": "Possible decision-support options (context)",
             "options": [
                 "Joint consultation with the pediatrician",
                 "Educational meeting with teachers or school specialists",
                 "Neutral child therapist",
                 "Developmental or neuropsychological evaluation",
                 "Parenting facilitator or parenting coordinator",
                 "Child-focused mediation",
                 "Tie-breaking recommendation from an agreed professional",
                 "Medical tie-breaker", "Mental-health tie-breaker",
                 "Educational tie-breaker",
                 "Court clarification when legal authority is disputed",
             ]},
        ],
        "note": "A professional should not be designated as a binding tie-breaker unless the arrangement is legally permitted and clearly documented.",
    },
    # -----------------------------------------------------------------------
    # Section 11 — Family Violence and Communication Safety (UNSCORED)
    # -----------------------------------------------------------------------
    {
        "id": "s11", "number": 11, "name": "Family Violence and Communication Safety",
        "scored": False, "safety_sensitive": True,
        "note": ("This section should not produce a general co-parenting score. "
                 "Safety concerns require an individualized response. "
                 "A positive safety response should direct the parent to the "
                 "app's full Family Violence–IPV Communication Safety Assessment."),
        "items": [
            {"id": "s11_flags", "type": "multi", "prompt": "Select any that apply.",
             "options": [
                 "I am afraid of the other parent.",
                 "Communications include threats, harassment, intimidation, or degrading language.",
                 "The other parent monitors my location, devices, or accounts.",
                 "Exchanges have involved threatening or unsafe behavior.",
                 "The child has witnessed conflict, threats, or violence.",
                 "A protective order or other safety restriction exists.",
                 "Direct negotiation or joint mediation may not be safe.",
                 "The other parent interferes with medical, educational, or therapeutic care as a means of control.",
                 "None of these apply.",
                 "Prefer not to answer.",
             ]},
            {"id": "s11_safeguards", "type": "multi", "prompt": "Possible safeguards",
             "options": [
                 "BIFF communication",
                 "Parenting application with documented messages",
                 "Communication limited to child-related information",
                 "Separate arrival and departure times",
                 "Neutral or supervised exchange location",
                 "Third-party or professional exchanges",
                 "Information provided directly by schools and medical providers",
                 "Shuttle or separate-room mediation",
                 "Attorney-assisted negotiation",
                 "Separate professional consultations",
                 "Safety planning with a qualified advocate",
                 "Review by a family-law attorney",
                 "Emergency or court intervention when necessary",
             ]},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 12 — Parent Capacity and Support
    # -----------------------------------------------------------------------
    {
        "id": "s12", "number": 12, "name": "Parent Capacity and Support", "scored": True,
        "items": [
            {"id": "s12_q1",  "type": "likert", "scored": True, "prompt": "I can remain regulated when discussing my child's needs."},
            {"id": "s12_q2",  "type": "likert", "scored": True, "prompt": "I can follow detailed care instructions."},
            {"id": "s12_q3",  "type": "likert", "scored": True, "prompt": "I have reliable transportation to appointments and school events."},
            {"id": "s12_q4",  "type": "likert", "scored": True, "prompt": "I can obtain necessary medication, equipment, and supplies."},
            {"id": "s12_q5",  "type": "likert", "scored": True, "prompt": "I have family, community, or professional support."},
            {"id": "s12_q6",  "type": "likert", "scored": True, "prompt": "I ask for help when I cannot meet a need."},
            {"id": "s12_q7",  "type": "likert", "scored": True, "prompt": "I am willing to learn new caregiving skills."},
            {"id": "s12_q8",  "type": "likert", "scored": True, "prompt": "My current stress level sometimes affects my ability to follow the child's plan."},
            {"id": "s12_q9",  "type": "likert", "scored": True, "prompt": "Financial or scheduling barriers interfere with services."},
            {"id": "s12_q10", "type": "likert", "scored": True, "prompt": "I need additional training or support."},
            {"id": "s12_open_support",  "type": "textarea", "prompt": "What support would make it easier for you to meet your child's needs?"},
            {"id": "s12_open_manage",   "type": "textarea", "prompt": "What is one caregiving responsibility you believe you manage well?"},
            {"id": "s12_open_help",     "type": "textarea", "prompt": "What is one area where you need help?"},
        ],
    },
    # -----------------------------------------------------------------------
    # Section 13 — Goals, Concerns, and Priorities (all context)
    # -----------------------------------------------------------------------
    {
        "id": "s13", "number": 13, "name": "Goals, Concerns, and Priorities", "scored": False,
        "items": [
            {"id": "s13_goals",       "type": "textarea", "prompt": "List your three most important goals for your child."},
            {"id": "s13_concerns",    "type": "textarea", "prompt": "List your three greatest concerns."},
            {"id": "s13_need_you",    "type": "textarea", "prompt": "What does your child need most from you?"},
            {"id": "s13_need_other",  "type": "textarea", "prompt": "What does your child need from the other parent?"},
            {"id": "s13_need_both",   "type": "textarea", "prompt": "What does your child need both parents to do consistently?"},
            {"id": "s13_first",       "type": "textarea", "prompt": "Which issue should be addressed first?"},
            {"id": "s13_info_needed", "type": "textarea", "prompt": "What professional information is still needed?"},
            {"id": "s13_thirty_day",  "type": "textarea", "prompt": "What agreement could the parents try during the next 30 days?"},
        ],
    },
]


# IDs of the scored categories, in report order.
SCORED_CATEGORY_IDS = tuple(s["id"] for s in SECTIONS if s.get("scored"))
assert SCORED_CATEGORY_IDS == ("s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s12"), \
    "Scored category IDs must be exactly Sections 2-10 + 12 (Section 11 safety is unscored)"


def find_section(sid: str) -> Optional[Dict[str, Any]]:
    for s in SECTIONS:
        if s["id"] == sid:
            return s
    return None


def find_item(qid: str) -> Optional[Dict[str, Any]]:
    for s in SECTIONS:
        for it in s["items"]:
            if it["id"] == qid:
                return it
    return None


def scored_items(section_id: str) -> List[Dict[str, Any]]:
    sec = find_section(section_id) or {}
    return [it for it in sec.get("items", []) if it.get("scored")]


def total_scored_items() -> int:
    return sum(len(scored_items(sid)) for sid in SCORED_CATEGORY_IDS)
