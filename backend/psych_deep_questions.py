"""Psychological / Behavioural Needs — Deep Dive schema.

Eleven-section optional companion assessment. Same architecture as
edu_deep_questions.py — see that module for design notes.
"""
from __future__ import annotations

from typing import Any, Dict, List


DEEP_DIVE_VERSION = "psych-deep-1.0.0"


# ---- shared option sets ----
FREQUENCY_5 = ["Always", "Usually", "Sometimes", "Rarely", "Never"]
CONFIDENCE_5 = ["Very Confident", "Confident", "Neutral", "Somewhat Confident", "Not Confident"]
AGREEMENT_5 = ["Always Agree", "Usually Agree", "Sometimes Agree", "Rarely Agree", "Never Agree"]
CONSISTENCY_5 = ["Always Consistent", "Usually Consistent", "Sometimes Consistent", "Rarely Consistent", "Never Consistent"]
CAREGIVER_4 = ["Mother", "Father", "Both", "Other caregiver"]
YES_NO = ["Yes", "No"]

DIAGNOSES = [
    "ADHD", "Autism Spectrum Disorder", "Anxiety Disorder", "Depression",
    "PTSD", "OCD", "Bipolar Disorder", "Oppositional Defiant Disorder (ODD)",
    "Conduct Disorder", "Adjustment Disorder", "Trauma-related concerns",
    "Attachment concerns", "Emotional dysregulation", "Eating disorder",
    "Sleep disorder", "Sensory Processing Disorder",
    "No diagnosis", "Diagnosis pending", "Prefer not to answer",
]

PROVIDER_TYPES = [
    "Child Psychologist", "Child Psychiatrist",
    "Licensed Professional Counsellor (LPC)",
    "Licensed Clinical Social Worker (LCSW)",
    "Marriage and Family Therapist (LMFT)",
    "Play Therapist", "Behavioural Therapist", "ABA Therapist",
    "Trauma Therapist", "School Counsellor", "No current provider",
]

PRESCRIBER_TYPES = ["Paediatrician", "Psychiatrist", "Neurologist", "Other", "Not applicable"]

NON_MED_INTERVENTIONS = [
    "Behavioural Therapy", "Cognitive Behavioural Therapy (CBT)",
    "Parent Training", "Occupational Therapy", "Social Skills Groups",
    "Speech Therapy", "Executive Function Coaching", "Exercise Programs",
    "Nutrition", "Sleep Interventions", "Mindfulness", "Meditation",
    "Biofeedback", "Sensory Regulation", "Family Therapy", "Other",
]

SUPPORT_AREAS = [
    "Anxiety", "Emotional regulation", "Meltdowns", "Anger",
    "Transitions", "Social interactions", "School stress",
    "Peer relationships", "Self-esteem",
]

CRISIS_AREAS = [
    "Severe anxiety", "Panic attacks", "Emotional crisis",
    "Aggressive behaviour", "Self-harm concerns", "Suicidal statements",
    "Psychiatric emergency",
]

COMM_TOPICS = [
    ("appointments", "Appointment scheduling"),
    ("medication_changes", "Medication changes"),
    ("behaviour_changes", "Behaviour changes"),
    ("school_concerns", "School concerns"),
    ("treatment_recs", "Treatment recommendations"),
    ("therapy_progress", "Therapy progress"),
    ("new_diagnoses", "New diagnoses"),
    ("symptom_changes", "Changes in symptoms"),
]

DECISION_TOPICS = [
    ("start_therapy", "Starting therapy"),
    ("change_therapist", "Changing therapists"),
    ("medication", "Medication"),
    ("medication_adjustments", "Medication adjustments"),
    ("psych_testing", "Psychological testing"),
    ("neuropsych_eval", "Neuropsychological evaluation"),
    ("behaviour_plans", "Behaviour plans"),
    ("school_mh_services", "School mental health services"),
    ("alternative_treatments", "Alternative treatments"),
    ("family_therapy", "Family therapy"),
]

HOME_SUPPORT_AREAS = [
    "Predictable routines", "Emotional support", "Positive reinforcement",
    "Calm environment", "Safe expression of emotions",
    "Consistent expectations", "Healthy coping strategies", "Stress reduction",
]


def _lk(prompt: str) -> Dict[str, Any]:
    return {"type": "likert", "prompt": prompt, "scored": True}


def _sg(prompt: str, options: List[str]) -> Dict[str, Any]:
    return {"type": "single", "prompt": prompt, "options": options}


def _ml(prompt: str, options: List[str]) -> Dict[str, Any]:
    return {"type": "multi", "prompt": prompt, "options": options}


def _tx(prompt: str) -> Dict[str, Any]:
    return {"type": "textarea", "prompt": prompt}


DEEP_DIVE_SECTIONS: List[Dict[str, Any]] = [
    # 1. Psychological Profile ---------------------------------------------
    {"id": "s1", "number": 1, "name": "Psychological Profile",
     "purpose": "Capture any current or pending psychological, behavioural, or emotional diagnoses.",
     "items": {
        "diagnoses": _ml("Has your child been diagnosed with any of the following? Select all that apply.", DIAGNOSES),
        "profile_notes": _tx("Anything specific you would like the report to note (optional)?"),
     }},
    # 2. Mental Health Professional -----------------------------------------
    {"id": "s2", "number": 2, "name": "Mental Health Professional",
     "purpose": "Identify the current provider(s) and how both parents engage with them.",
     "items": {
        "provider_types":       _ml("Is your child currently seeing a mental health professional? Select all that apply.", PROVIDER_TYPES),
        "both_know_provider":   _sg("Do both parents know who the provider is?", FREQUENCY_5),
        "attend_appointments":  _sg("Does each parent attend appointments when appropriate?", FREQUENCY_5),
        "both_receive_updates": _sg("Do both parents receive treatment updates?", FREQUENCY_5),
        "communicate_recs":     _sg("Do parents communicate about recommendations?", FREQUENCY_5),
        "follow_recs_consistent": _sg("Do parents follow treatment recommendations consistently?", FREQUENCY_5),
     }},
    # 3. Confidence in the Provider ----------------------------------------
    {"id": "s3", "number": 3, "name": "Confidence in the Provider",
     "purpose": "Assess parent confidence in and coordination around the current provider.",
     "items": {
        "provider_understands":  _sg("How confident are you that the provider understands your child's needs?", CONFIDENCE_5),
        "confidence_plan":       _sg("How confident are you in the treatment plan?", CONFIDENCE_5),
        "trust_recommendations": _sg("Do you trust the provider's recommendations?", CONFIDENCE_5),
        "both_confident":        _sg("Do both parents have confidence in the provider?", CONFIDENCE_5),
        "discuss_respectfully":  _lk("Disagreements about treatment can be discussed respectfully."),
     }},
    # 4. Medication Management ---------------------------------------------
    {"id": "s4", "number": 4, "name": "Medication Management",
     "purpose": "Understand medication coordination between homes.",
     "gate": {"item": "has_medication", "value": "Yes"},
     "items": {
        "has_medication":        _sg("Is your child prescribed medication?", YES_NO),
        "prescriber":            _sg("Who prescribed the medication?", PRESCRIBER_TYPES),
        "understand_areas":      _ml("Do both parents understand:", [
                                    "Medication purpose", "Dosage", "Side effects",
                                    "Administration schedule", "Monitoring requirements",
                                 ]),
        "administered_consistent": _lk("Medication is administered consistently in both homes."),
        "communicate_changes":   _lk("Parents communicate about medication changes."),
        "refills_coordinated":   _lk("Refill schedules are coordinated between homes."),
        "side_effects_discussed": _lk("Side effects are discussed between parents."),
        "concerns_reported":     _lk("Concerns are reported promptly to the prescriber."),
     }},
    # 5. Alternatives to Medication ----------------------------------------
    {"id": "s5", "number": 5, "name": "Alternatives to Medication",
     "purpose": "Assess non-medication interventions and cross-home consistency.",
     "items": {
        "interventions": _ml("Which non-medication interventions has your family discussed or used? Select all that apply.", NON_MED_INTERVENTIONS),
        "both_support":  _lk("Both parents support these interventions."),
        "implemented_consistently": _lk("Alternative therapies are implemented consistently in both homes."),
        "child_participates": _lk("The child participates in these interventions regularly."),
        "outcomes_reviewed":  _lk("Outcomes are reviewed together by both parents."),
     }},
    # 6. Therapy Participation ---------------------------------------------
    {"id": "s6", "number": 6, "name": "Therapy Participation",
     "purpose": "Assess consistency of the child's therapy engagement.",
     "gate": {"item": "attends_therapy", "value": "Yes"},
     "items": {
        "attends_therapy":       _sg("Does your child currently attend therapy?", YES_NO),
        "attendance_consistency": _sg("How consistently does your child attend therapy?", FREQUENCY_5),
        "who_transports":        _sg("Who typically transports the child?", CAREGIVER_4),
        "who_communicates":      _sg("Who communicates with the therapist?", CAREGIVER_4),
        "therapist_homework":    _sg("Does the therapist provide homework?", YES_NO),
        "homework_completed":    _lk("Therapy homework is completed at home."),
        "strategies_reinforced": _lk("Coping strategies are reinforced in both homes."),
     }},
    # 7. Behavioural & Emotional Support ----------------------------------
    {"id": "s7", "number": 7, "name": "Behavioural & Emotional Support",
     "purpose": "Assess consistency of parenting strategies across common behavioural and emotional areas.",
     "items": {
        strategy_id: _sg(f"How consistent are the strategies for {label.lower()}?", CONSISTENCY_5)
        for (strategy_id, label) in [
            ("anxiety", "Anxiety"),
            ("emotional_regulation", "Emotional regulation"),
            ("meltdowns", "Meltdowns"),
            ("anger", "Anger"),
            ("transitions", "Transitions"),
            ("social_interactions", "Social interactions"),
            ("school_stress", "School stress"),
            ("peer_relationships", "Peer relationships"),
            ("self_esteem", "Self-esteem"),
        ]
     }},
    # 8. Crisis Planning ----------------------------------------------------
    {"id": "s8", "number": 8, "name": "Crisis Planning",
     "purpose": "Assess whether both parents share a crisis plan for common psychiatric or behavioural crises.",
     "items": {
        "planned_areas":     _ml("Do the parents have a shared plan if the child experiences:", CRISIS_AREAS),
        "know_emergency_contacts": _sg("Do both parents know the emergency contacts?", YES_NO),
        "know_crisis_procedures": _sg("Do both parents know the crisis procedures?", YES_NO),
        "plan_in_writing":   _sg("Is the crisis plan documented in writing?", ["Yes", "Partial", "No"]),
     }},
    # 9. Communication Between Parents ------------------------------------
    {"id": "s9", "number": 9, "name": "Communication Between Parents",
     "purpose": "Assess how consistently parents discuss key topics.",
     "items": {
        topic_id: _sg(f"How often do parents discuss {label.lower()}?", FREQUENCY_5)
        for (topic_id, label) in COMM_TOPICS
     }},
    # 10. Psychological Decision-Making -----------------------------------
    {"id": "s10", "number": 10, "name": "Psychological Decision-Making",
     "purpose": "Assess whether parents can agree on major psychological / mental health decisions.",
     "items": {
        topic_id: _sg(f"How often do parents agree on {label.lower()}?", AGREEMENT_5)
        for (topic_id, label) in DECISION_TOPICS
     }},
    # 11. Home Support ----------------------------------------------------
    {"id": "s11", "number": 11, "name": "Home Support",
     "purpose": "Assess how consistently both homes provide the emotional foundation the child needs.",
     "items": {
        home_id: _sg(f"How consistently does each home provide {label.lower()}?", CONSISTENCY_5)
        for home_id, label in [
            ("routines", "Predictable routines"),
            ("emotional_support", "Emotional support"),
            ("positive_reinforcement", "Positive reinforcement"),
            ("calm_environment", "Calm environment"),
            ("safe_expression", "Safe expression of emotions"),
            ("consistent_expectations", "Consistent expectations"),
            ("healthy_coping", "Healthy coping strategies"),
            ("stress_reduction", "Stress reduction"),
        ]
     }},
]


def public_schema() -> Dict[str, Any]:
    return {
        "version": DEEP_DIVE_VERSION,
        "sections": [
            {
                "id": s["id"], "number": s["number"], "name": s["name"],
                "purpose": s.get("purpose"), "gate": s.get("gate"),
                "items": [{"id": iid, **spec} for iid, spec in s["items"].items()],
            } for s in DEEP_DIVE_SECTIONS
        ],
    }


def all_item_keys() -> List[str]:
    return [f"{s['id']}_{iid}" for s in DEEP_DIVE_SECTIONS for iid in s["items"].keys()]


def item_by_key(key: str) -> Dict[str, Any] | None:
    for s in DEEP_DIVE_SECTIONS:
        for iid, spec in s["items"].items():
            if f"{s['id']}_{iid}" == key:
                return {**spec, "id": iid, "section": s["id"]}
    return None


def validate_answer(key: str, value: Any) -> bool:
    spec = item_by_key(key)
    if not spec:
        return False
    t = spec["type"]
    if t == "likert":
        return value == "na" or (isinstance(value, int) and 1 <= value <= 5)
    if t == "single":
        opts = spec.get("options") or []
        return isinstance(value, str) and (not opts or value in opts)
    if t == "multi":
        opts = spec.get("options") or []
        return isinstance(value, list) and all(
            isinstance(v, str) and (not opts or v in opts) for v in value
        )
    if t in ("text", "textarea"):
        return isinstance(value, str)
    return False
