"""Special Needs Co-Parenting v2 — needs-category-driven assessment schema.

The assessment starts with a category picker:
    * medical
    * educational
    * psychological  (Psychological or Behavioral Needs)
    * multiple       (opts a parent in to every pathway at once)

For each selected pathway, the parent walks through the same 8-step workflow:
    1. Understand the Concern
    2. Identify the Child's Current Needs
    3. Review Professional Recommendations
    4. Assess Each Parent's Understanding
    5. Evaluate Coordination Between Homes
    6. Areas of Agreement and Disagreement
    7. Choose Practical Co-Parenting Options
    8. Create an Action Plan

Step 9 in the user's spec ("Generate the Special Needs Co-Parenting Report") is
produced by the report content builder, not the assessment.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


ASSESSMENT_VERSION = "snc2-2026-1"


# 5-point Likert with N/A used across steps 4 & 5.
RESPONSE_SCALE: List[Dict[str, Any]] = [
    {"value": 1, "label": "Strongly disagree"},
    {"value": 2, "label": "Disagree"},
    {"value": 3, "label": "Unsure"},
    {"value": 4, "label": "Agree"},
    {"value": 5, "label": "Strongly agree"},
    {"value": "na", "label": "Not applicable or unknown"},
]


PATHWAYS: List[Dict[str, Any]] = [
    {
        "id": "medical",
        "name": "Medical Needs",
        "short": "Medical",
        "summary": "Concerns involving the child's physical health or medical care.",
        "examples": [
            "Chronic medical conditions",
            "Medications and treatment schedules",
            "Allergies or dietary restrictions",
            "Appointments with paediatricians or specialists",
            "Medical testing or procedures",
            "Physical or occupational therapy",
            "Emergency-care instructions",
            "Health insurance and medical expenses",
        ],
    },
    {
        "id": "educational",
        "name": "Educational Needs",
        "short": "Educational",
        "summary": "Concerns involving the child's learning, school services, or educational progress.",
        "examples": [
            "Learning difficulties or developmental delays",
            "Kindergarten readiness",
            "Academic performance",
            "School attendance",
            "Evaluations and educational testing",
            "IEP or Section 504 services",
            "Tutoring and classroom accommodations",
            "Communication with teachers and school professionals",
            "Special events, field trips, and extracurricular activities",
        ],
    },
    {
        "id": "psychological",
        "name": "Psychological or Behavioural Needs",
        "short": "Psychological or Behavioural",
        "summary": "Concerns involving the child's emotional health, behaviour, or psychological treatment.",
        "examples": [
            "ADHD, anxiety, depression, or autism-related needs",
            "Emotional regulation or behavioural concerns",
            "Counselling or psychological services",
            "Psychological or neuropsychological evaluations",
            "Treatment recommendations",
            "Medication monitoring",
            "Consistency between households",
            "Crisis planning",
            "Communication with therapists and mental-health professionals",
        ],
    },
    {
        "id": "multiple",
        "name": "Multiple or Interconnected Needs",
        "short": "Multiple",
        "summary": (
            "Children's needs do not always fit into one category. Choose this "
            "option when medical, educational, and psychological needs overlap "
            "- for example, a child with ADHD who needs medication management, "
            "counselling, and classroom accommodations."
        ),
        "examples": [
            "ADHD with medication and IEP",
            "Autism spectrum with therapy and school supports",
            "Chronic illness affecting school attendance",
            "Learning disability with counselling",
        ],
        "expands_to": ["medical", "educational", "psychological"],
    },
]


def resolve_pathways(selected: List[str]) -> List[str]:
    """Return the concrete pathway ids to render for a given picker selection."""
    result: List[str] = []
    for pid in selected or []:
        if pid == "multiple":
            for sub in ("medical", "educational", "psychological"):
                if sub not in result:
                    result.append(sub)
        elif pid in {"medical", "educational", "psychological"}:
            if pid not in result:
                result.append(pid)
    return result


# ---------------------------------------------------------------------------
# Per-pathway vocabulary — plugged into a shared 8-step template.
# ---------------------------------------------------------------------------

_VOCAB = {
    "medical": {
        "concern_label":     "medical concern",
        "concern_examples":  "a chronic condition, allergy, medication, therapy, or upcoming procedure",
        "recs_label":        "medical recommendation",
        "professional":      "paediatrician, specialist, or therapist",
        "current_needs_options": [
            "Chronic medical condition",
            "Medication schedule",
            "Allergies or dietary restrictions",
            "Specialist appointments",
            "Medical testing or procedures",
            "Physical therapy",
            "Occupational therapy",
            "Nutritional or feeding support",
            "Emergency-care plan",
            "Health-insurance coordination",
            "Medical-expense coordination",
        ],
        "practical_options": [
            "Shared calendar for medical appointments",
            "Shared medication log (paper or app)",
            "Pillbox or dispenser used consistently in both homes",
            "Emergency-care instructions posted in both homes",
            "Both parents added to the patient portal",
            "Copy of prescriptions kept in each home",
            "Shared travel supply (spare inhaler, EpiPen, etc.)",
            "Alternating attendance at appointments",
            "Both parents attend key appointments together",
            "Third-party liaison (nurse, care coordinator)",
        ],
        "recommendation_options": [
            "Daily medication",
            "As-needed / rescue medication",
            "Ongoing therapy sessions",
            "Diet, feeding, or nutrition plan",
            "Follow-up testing or imaging",
            "Referral to a specialist",
            "Emergency-response plan",
            "Home-care equipment or supplies",
            "Lifestyle or activity guidance",
            "Other",
        ],
        "professional_next_options": [
            "Paediatrician",
            "Specialist physician",
            "Allergist or dietitian",
            "Physical or occupational therapist",
            "Nurse care coordinator",
            "Emergency-care doctor",
            "Other",
            "No new professional needed",
        ],
    },
    "educational": {
        "concern_label":     "educational concern",
        "concern_examples":  "school performance, an IEP or Section 504 plan, attendance, or a specific classroom issue",
        "recs_label":        "educational recommendation",
        "professional":      "teacher, school counsellor, IEP team, or educational specialist",
        "current_needs_options": [
            "Learning difficulty or developmental delay",
            "Kindergarten readiness",
            "Academic performance",
            "School attendance",
            "Educational evaluation or testing",
            "IEP or Section 504 services",
            "Tutoring or academic support",
            "Classroom accommodations",
            "Behaviour plan at school",
            "Communication with teachers",
            "Special events or field trips",
            "Extracurricular activities",
        ],
        "practical_options": [
            "Both parents on the school contact list",
            "Duplicate report cards and school communications sent to each parent",
            "Shared homework folder that travels between homes",
            "Alternating attendance at parent-teacher conferences",
            "Both parents attend IEP or 504 meetings",
            "Shared school calendar (events, holidays, exam dates)",
            "Written homework routine agreed in both homes",
            "Neutral educational liaison or advocate",
            "School-provided planner used consistently in both homes",
            "Both parents review the IEP or 504 plan together",
        ],
        "recommendation_options": [
            "Special-education services (IEP)",
            "Section 504 accommodations",
            "Classroom accommodations",
            "Tutoring or academic support",
            "Behaviour plan at school",
            "Speech-language therapy",
            "Occupational therapy at school",
            "Additional evaluation or testing",
            "Change of placement or setting",
            "Other",
        ],
        "professional_next_options": [
            "Classroom teacher",
            "School counsellor",
            "IEP or 504 coordinator",
            "Special-education advocate",
            "Tutor or academic coach",
            "Educational psychologist",
            "Speech or occupational therapist",
            "Other",
            "No new professional needed",
        ],
    },
    "psychological": {
        "concern_label":     "psychological or behavioural concern",
        "concern_examples":  "ADHD, anxiety, depression, an autism-related need, or a specific behaviour pattern",
        "recs_label":        "clinical recommendation",
        "professional":      "psychologist, therapist, psychiatrist, or behavioural specialist",
        "current_needs_options": [
            "ADHD-related supports",
            "Anxiety-related supports",
            "Depression-related supports",
            "Autism-related supports",
            "Emotional-regulation strategies",
            "Behavioural intervention plan",
            "Counselling or psychotherapy",
            "Psychiatric medication monitoring",
            "Psychological or neuropsychological evaluation",
            "Crisis-response plan",
            "Communication with therapists",
        ],
        "practical_options": [
            "Consistent bedtime and morning routines in both homes",
            "Shared behaviour or reward system",
            "Consistent screen-time rules",
            "Shared coping-skills toolkit that travels with the child",
            "Both parents on the therapist's release-of-information",
            "Alternating attendance at therapy sessions",
            "Written crisis-response plan posted in both homes",
            "Shared calendar for therapy and medication",
            "Third-party parent-coach or family therapist",
            "Neutral communication channel for behavioural updates",
        ],
        "recommendation_options": [
            "Weekly therapy or counselling",
            "Medication management",
            "Behaviour plan at home",
            "Coping-skills tools",
            "Additional evaluation or testing",
            "Sleep or daily-routine changes",
            "Family or parenting support",
            "Crisis-response plan",
            "School-therapist coordination",
            "Other",
        ],
        "professional_next_options": [
            "Child therapist or counsellor",
            "Family therapist",
            "Psychiatrist",
            "Behaviour specialist",
            "School psychologist",
            "Parenting coach",
            "Other",
            "No new professional needed",
        ],
    },
}


# Cross-cutting option lists reused across all pathways for questions that don't
# vary by need type.
_ADDITIONAL_AREAS_OPTIONS = [
    "Sleep or fatigue issues",
    "Diet or nutrition",
    "Sensory sensitivities",
    "Mobility or motor skills",
    "Social relationships",
    "Family stress affecting the child",
    "Financial coordination between homes",
    "None additional",
    "Other",
]

_ADDITIONAL_PRACTICAL_OPTIONS = [
    "Regular parent-only check-ins",
    "Written communication log",
    "Mediation for major decisions",
    "Third-party parenting coordinator",
    "Shared parenting app (OurFamilyWizard, TalkingParents, etc.)",
    "Formal written co-parenting agreement",
    "None additional",
    "Other",
]

_TOP_PRIORITY_OPTIONS = [
    "Schedule the next professional appointment",
    "Refill medication or supplies",
    "Update the shared calendar or plan",
    "Align on daily routine between homes",
    "Have a difficult conversation with my co-parent",
    "Speak with a mediator or family professional",
    "Communicate with the child's school or provider",
    "Complete an evaluation or paperwork",
    "Other",
]

_PLAN_CONCERN_OPTIONS = [
    "No concerns",
    "Concerns about my co-parent following the plan",
    "Concerns about cost or logistics",
    "Concerns about how our child feels about the plan",
    "Concerns about safety or communication",
    "Something else I want to flag",
]


# 8-step template. Items marked `pathway=True` mean their prompt is
# templated per pathway using _VOCAB. Items marked `scored=True` roll
# into the coordination / understanding scores.
_TEMPLATE: List[Dict[str, Any]] = [
    # ---------- Step 1 ---------------------------------------------------
    {"id": "step1", "number": 1, "name": "Understand the Concern",
     "items": [
        {"id": "concern", "type": "textarea", "pathway": True,
         "prompt_template": "Describe the {concern_label} you want to address (e.g. {concern_examples})."},
        {"id": "duration", "type": "single",
         "prompt": "Roughly how long has this been a concern?",
         "options": ["Less than 3 months", "3 to 12 months", "1 to 3 years", "More than 3 years"]},
        {"id": "current_impact", "type": "likert", "scored": True,
         "prompt": "This concern currently affects my child's daily life."},
        {"id": "urgency", "type": "single",
         "prompt": "How time-sensitive is this concern?",
         "options": ["Immediate / crisis", "Needs attention within weeks", "Longer-term planning", "Ongoing / stable"]},
     ]},
    # ---------- Step 2 ---------------------------------------------------
    {"id": "step2", "number": 2, "name": "Identify the Child's Current Needs",
     "items": [
        {"id": "current_needs", "type": "multi", "pathway_options": True,
         "prompt": "Which of the following describe your child's current needs? Select all that apply."},
        {"id": "additional_areas", "type": "multi",
         "prompt": "Are any of these additional areas also involved? Select all that apply, or leave blank.",
         "options_ref": "additional_areas"},
     ]},
    # ---------- Step 3 ---------------------------------------------------
    {"id": "step3", "number": 3, "name": "Review Professional Recommendations",
     "items": [
        {"id": "professionals_seen", "type": "multi", "pathway": True,
         "prompt_template": "Who is currently involved with this concern? Include every {professional} who has evaluated or is treating your child.",
         "options_common": [
             "Paediatrician",
             "Family physician",
             "Specialist physician",
             "Psychologist",
             "Psychiatrist",
             "Therapist or counsellor",
             "Occupational therapist",
             "Physical therapist",
             "Speech-language pathologist",
             "Teacher",
             "School counsellor",
             "IEP or 504 team",
             "Case manager or care coordinator",
             "No one yet",
         ]},
        {"id": "recommendation_types", "type": "multi", "pathway": True,
         "prompt_template": "What does the most recent {recs_label} include? Select every category that applies.",
         "options_from_vocab": "recommendation_options"},
        {"id": "recs_written", "type": "single",
         "prompt": "Do you have the recommendation in writing (report, plan, prescription, IEP, etc.)?",
         "options": ["Yes", "Partly", "No", "Unsure"]},
        {"id": "recs_understand", "type": "likert", "scored": True,
         "prompt": "I understand the current recommendations for my child."},
     ]},
    # ---------- Step 4 ---------------------------------------------------
    {"id": "step4", "number": 4, "name": "Each Parent's Understanding",
     "items": [
        {"id": "same_info", "type": "likert", "scored": True,
         "prompt": "Both parents have received the same written information about this concern."},
        {"id": "attend_appts", "type": "likert", "scored": True,
         "prompt": "Both parents attend key appointments, meetings, or evaluations."},
        {"id": "discuss_openly", "type": "likert", "scored": True,
         "prompt": "My co-parent and I can discuss this concern openly and calmly."},
        {"id": "shared_language", "type": "likert", "scored": True,
         "prompt": "My co-parent and I use the same words when describing the concern to our child."},
        {"id": "believe_understood", "type": "likert", "scored": True,
         "prompt": "I believe my co-parent understands what our child is going through."},
     ]},
    # ---------- Step 5 ---------------------------------------------------
    {"id": "step5", "number": 5, "name": "Coordination Between Homes",
     "items": [
        {"id": "routines_consistent", "type": "likert", "scored": True,
         "prompt": "Daily routines that affect this concern (medication, bedtime, homework, therapy practice) are consistent across both homes."},
        {"id": "follow_recs", "type": "likert", "scored": True,
         "prompt": "Professional recommendations are followed in both homes."},
        {"id": "share_updates", "type": "likert", "scored": True,
         "prompt": "My co-parent and I share updates about appointments, changes, and new information promptly."},
        {"id": "carry_over_supplies", "type": "likert", "scored": True,
         "prompt": "Supplies the child needs (medication, adaptive equipment, homework, comfort items) travel reliably between homes."},
        {"id": "handoffs_reliable", "type": "likert", "scored": True,
         "prompt": "Transitions and handoffs happen without disrupting the plan."},
     ]},
    # ---------- Step 6 ---------------------------------------------------
    {"id": "step6", "number": 6, "name": "Agreement and Disagreement",
     "items": [
        {"id": "agree_areas", "type": "textarea",
         "prompt": "Where do you and your co-parent clearly agree on this concern?"},
        {"id": "disagree_areas", "type": "textarea",
         "prompt": "Where do you and your co-parent see it differently?"},
        {"id": "biggest_gap", "type": "single",
         "prompt": "Which type of gap best describes the disagreement?",
         "options": [
             "Different information",
             "Different priorities",
             "Different parenting styles",
             "Communication breakdown",
             "No meaningful disagreement",
         ]},
     ]},
    # ---------- Step 7 ---------------------------------------------------
    {"id": "step7", "number": 7, "name": "Practical Co-Parenting Options",
     "items": [
        {"id": "practical_selected", "type": "multi", "pathway_options": True,
         "prompt": "Select the practical options you would consider trying. You can pick more than one."},
        {"id": "additional_practical", "type": "multi",
         "prompt": "Any additional cross-cutting options to consider?",
         "options_ref": "additional_practical"},
     ]},
    # ---------- Step 8 ---------------------------------------------------
    {"id": "step8", "number": 8, "name": "Create an Action Plan",
     "items": [
        {"id": "top_priority", "type": "single",
         "prompt": "What is the single most important thing to address in the next 30 days?",
         "options_ref": "top_priority"},
        {"id": "next_meeting", "type": "single",
         "prompt": "When could you and your co-parent meet (or send a written proposal) to discuss this plan?",
         "options": ["This week", "Within 2 weeks", "Within a month", "Undecided"]},
        {"id": "professional_next", "type": "single", "pathway": True,
         "prompt_template": "Which {professional} would be most useful to consult next?",
         "options_from_vocab": "professional_next_options"},
        {"id": "concerns_about_plan", "type": "single",
         "prompt": "Do you have any concerns about the plan you would like to raise before finalising it?",
         "options_ref": "plan_concern"},
     ]},
]


_CROSS_CUTTING_OPTIONS = {
    "additional_areas":     _ADDITIONAL_AREAS_OPTIONS,
    "additional_practical": _ADDITIONAL_PRACTICAL_OPTIONS,
    "top_priority":         _TOP_PRIORITY_OPTIONS,
    "plan_concern":         _PLAN_CONCERN_OPTIONS,
}


def _apply_pathway(item: Dict[str, Any], pathway: str) -> Dict[str, Any]:
    """Return a shallow-copied item with pathway-specific prompt/options resolved."""
    out = dict(item)
    vocab = _VOCAB[pathway]
    if out.get("pathway") and "prompt_template" in out:
        out["prompt"] = out["prompt_template"].format(**vocab)
        out.pop("prompt_template", None)
    if out.get("pathway_options"):
        out["options"] = list(vocab["current_needs_options"]) if item["id"] == "current_needs" \
            else list(vocab["practical_options"])
    if item.get("options_common") and item.get("pathway"):
        out["options"] = list(item["options_common"])
        out.pop("options_common", None)
    # Pathway-specific option list resolved from _VOCAB (e.g. recommendation_options).
    if item.get("options_from_vocab"):
        key = item["options_from_vocab"]
        out["options"] = list(vocab[key])
        out.pop("options_from_vocab", None)
    # Cross-cutting shared option list (same for every pathway).
    if item.get("options_ref"):
        key = item["options_ref"]
        out["options"] = list(_CROSS_CUTTING_OPTIONS[key])
        out.pop("options_ref", None)
    return out


def build_schema(selected: List[str]) -> Dict[str, Any]:
    """Compile the assessment schema for the parent's selected pathways.

    Returned shape:
        {
          "assessment_version": "snc2-2026-1",
          "response_scale": [...],
          "selected_pathways": ["medical", ...],
          "steps": [
             { "id": "step1", "number": 1, "name": "Understand the Concern",
               "pathways": [
                  { "id": "medical", "name": "Medical Needs",
                    "items": [ ... resolved items ... ] },
                  ...
               ]
             },
             ...
          ]
        }
    """
    pathways = resolve_pathways(selected)
    if not pathways:
        raise ValueError("No pathways selected — pick at least one category.")
    steps: List[Dict[str, Any]] = []
    for step in _TEMPLATE:
        block: Dict[str, Any] = {
            "id": step["id"],
            "number": step["number"],
            "name": step["name"],
            "pathways": [],
        }
        for pid in pathways:
            resolved_items = [_apply_pathway(item, pid) for item in step["items"]]
            block["pathways"].append({
                "id": pid,
                "name": next(p["name"] for p in PATHWAYS if p["id"] == pid),
                "items": resolved_items,
            })
        steps.append(block)
    return {
        "assessment_version": ASSESSMENT_VERSION,
        "response_scale": RESPONSE_SCALE,
        "selected_pathways": pathways,
        "steps": steps,
        "pathways_catalog": PATHWAYS,
    }


def qid(step_id: str, pathway: str, item_id: str) -> str:
    """Compose the persisted answer key: 'step5_medical_routines_consistent'."""
    return f"{step_id}_{pathway}_{item_id}"


def parse_qid(k: str) -> Optional[Dict[str, str]]:
    parts = k.split("_", 2)
    if len(parts) < 3:
        return None
    return {"step_id": parts[0], "pathway": parts[1], "item_id": parts[2]}


def scored_qids(pathways: List[str]) -> List[str]:
    """List of every scored question id for a set of pathways."""
    ids: List[str] = []
    for step in _TEMPLATE:
        for item in step["items"]:
            if item.get("scored"):
                for pid in pathways:
                    ids.append(qid(step["id"], pid, item["id"]))
    return ids
