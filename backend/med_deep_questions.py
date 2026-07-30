"""Medical Needs — Prescription Sharing & Medication Coordination Deep Dive.

Ten-section optional companion assessment. Same architecture as
psych_deep_questions.py / edu_deep_questions.py. Neutral, parent-reported,
non-diagnostic, non-adjudicative, safety-aware. All prompts are option-based
except one optional free-text "notes" field in Section 1.
"""
from __future__ import annotations

from typing import Any, Dict, List


DEEP_DIVE_VERSION = "med-deep-1.0.0"


# ---- shared option sets ----
FREQUENCY_5 = ["Always", "Usually", "Sometimes", "Rarely", "Never"]
CONSISTENCY_5 = ["Always Consistent", "Usually Consistent", "Sometimes Consistent",
                 "Rarely Consistent", "Never Consistent"]
AGREEMENT_5 = ["Always Agree", "Usually Agree", "Sometimes Agree",
               "Rarely Agree", "Never Agree"]
CAREGIVER_4 = ["Mother", "Father", "Both", "Other caregiver"]
YES_NO = ["Yes", "No"]
YES_PARTIAL_NO = ["Yes", "Partial", "No"]
COUNT_5 = ["0", "1", "2", "3", "4+"]


MEDICATION_CATEGORIES = [
    "Daily maintenance medication",
    "As-needed (PRN) medication",
    "Rescue / emergency medication (e.g., inhaler, EpiPen, glucagon)",
    "Controlled substance (e.g., stimulant, benzodiazepine, opioid)",
    "Antibiotic / short course",
    "Over-the-counter / supplement recommended by provider",
    "Compounded or specialty medication",
    "No current medication",
]

PRESCRIBER_TYPES = [
    "Paediatrician", "Family physician", "Psychiatrist", "Neurologist",
    "Allergist / Immunologist", "Endocrinologist", "Gastroenterologist",
    "Cardiologist", "Pulmonologist", "Dermatologist", "Other specialist",
    "Not applicable",
]

INFO_ITEMS = [
    "Medication name(s)",
    "Dose / strength",
    "Purpose / condition treated",
    "Administration schedule (times, with/without food)",
    "Side effects to watch for",
    "Interactions & allergies",
    "Prescriber name & contact",
    "Pharmacy name & contact",
]

PICKUP_ISSUES = [
    "Delay of one or more days after prescription written",
    "Missed pick-up so a dose was skipped",
    "Confusion about who was picking up",
    "Pharmacy closed / hours mismatch",
    "Insurance authorisation delay",
    "Prescription lost or misplaced",
    "Ran out before refill was picked up",
    "No issues in the last 6 months",
]

FINANCIAL_ISSUES = [
    "Copay is a barrier",
    "Insurance denied / requires prior auth",
    "Split of medication cost is unclear",
    "One parent refuses to pay their share",
    "HSA / FSA coordination is confusing",
    "Formulary changes caused disruption",
    "Cash-pay cost is unaffordable",
    "No financial barriers currently",
]

CONTROL_PROTECTIONS = [
    "Medication stored in a locked location",
    "Weekly count tracked in writing",
    "Transfer between homes is logged",
    "Only the parent administers doses (never the child alone)",
    "Prescriber's controlled-substance agreement is on file",
    "Both parents receive the pharmacy pick-up receipt",
    "No protections currently in place",
]

SCHOOL_COORD_ITEMS = [
    "Both parents signed the school medication authorisation",
    "School nurse has the current prescription order",
    "Field-trip / off-campus authorisation is on file",
    "PRN (as-needed) medication is authorised and stocked",
    "Emergency plan (e.g., asthma or anaphylaxis) is on file",
    "Both parents receive the school Medication Administration Record (MAR)",
    "School is notified promptly of dose or med changes",
    "None of the above",
]

DISAGREEMENT_TOPICS = [
    ("whether_to_use", "Whether to use medication at all"),
    ("which_medication", "Which medication to use"),
    ("dosing", "Dose or timing"),
    ("side_effects", "Concern about side effects"),
    ("brand_vs_generic", "Brand versus generic"),
    ("stopping_med", "When to stop the medication"),
    ("as_needed_use", "Use of PRN / as-needed medication"),
    ("controlled_use", "Use of controlled medication"),
]

PARENT_COMM_TOPICS = [
    ("new_prescriptions", "New prescriptions"),
    ("dose_changes", "Dose or schedule changes"),
    ("missed_doses", "Missed doses"),
    ("side_effects", "Side effects observed"),
    ("refill_needs", "Refill needs / running low"),
    ("emergency_use", "Use of rescue or emergency medication"),
    ("stopping_med", "Stopping a medication"),
    ("provider_visits", "Prescriber appointments"),
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
    # 1. Prescription Information Sharing --------------------------------
    {"id": "s1", "number": 1, "name": "Prescription Information Sharing",
     "purpose": "Confirm both parents share the same accurate picture of every prescription.",
     "items": {
        "med_categories":      _ml("Which medication categories does your child currently use? Select all that apply.", MEDICATION_CATEGORIES),
        "prescriber_types":    _ml("Which types of prescribers are involved? Select all that apply.", PRESCRIBER_TYPES),
        "shared_info":         _ml("Which of the following do BOTH parents currently know accurately? Select all that apply.", INFO_ITEMS),
        "written_med_list":    _sg("Is there a written, up-to-date medication list shared between homes?", YES_PARTIAL_NO),
        "list_updated":        _sg("How often is the shared medication list updated after a change?", FREQUENCY_5),
        "both_receive_new_rx": _sg("Do both parents learn about new prescriptions promptly?", FREQUENCY_5),
        "notes":               _tx("Anything else you would like the report to note about prescription information (optional)?"),
     }},
    # 2. Prescription Pick-Up Problems -----------------------------------
    {"id": "s2", "number": 2, "name": "Prescription Pick-Up",
     "purpose": "Identify friction, delays, or missed doses linked to who fills the prescription.",
     "items": {
        "who_picks_up":     _sg("Who typically picks up prescriptions?", CAREGIVER_4),
        "pickup_issues":    _ml("In the last 6 months, which of these pick-up issues have occurred? Select all that apply.", PICKUP_ISSUES),
        "pickup_delays":    _sg("How often does a pick-up delay cause a missed dose?", FREQUENCY_5),
        "clear_assignment": _sg("Is it clear ahead of time who is picking up each prescription?", FREQUENCY_5),
        "confirmation":     _sg("Does the other parent get a confirmation once medication has been picked up?", FREQUENCY_5),
     }},
    # 3. Medication Supply -----------------------------------------------
    {"id": "s3", "number": 3, "name": "Medication Supply Between Homes",
     "purpose": "Assess whether the child has continuous supply in the home they are in.",
     "items": {
        "supply_each_home":       _sg("Does the child have a working supply in both homes at all times?", FREQUENCY_5),
        "backup_supply":          _sg("Is a labelled backup dose kept at each home for handoff or travel days?", YES_PARTIAL_NO),
        "refill_coordination":    _sg("Are refills coordinated so the child never runs out during a transition?", FREQUENCY_5),
        "runs_out_frequency":     _sg("How often has your child run out of a needed medication in the last 6 months?", ["Never", "Once", "2-3 times", "More than 3 times"]),
        "emergency_med_available": _sg("Is emergency / rescue medication (e.g., inhaler, EpiPen) available in BOTH homes?", ["Yes in both", "Only one home", "No", "Not applicable"]),
        "expired_check":          _sg("How often is medication checked for expiration or damage?", FREQUENCY_5),
     }},
    # 4. Medication Administration ---------------------------------------
    {"id": "s4", "number": 4, "name": "Medication Administration",
     "purpose": "Understand how doses are given day-to-day and whether administration is consistent.",
     "items": {
        "who_administers":      _sg("Who typically administers medication in each home?", CAREGIVER_4),
        "same_schedule":        _sg("Do both homes use the same administration schedule?", CONSISTENCY_5),
        "missed_doses_freq":    _sg("How often are doses missed in either home?", FREQUENCY_5),
        "dose_log":             _sg("Is dose administration recorded (log, app, MAR) in both homes?", YES_PARTIAL_NO),
        "handoff_dose":         _sg("How consistently is the last/next dose communicated at handoff?", FREQUENCY_5),
        "child_involved":       _sg("Is the child developmentally involved in taking medication safely?", ["Yes, appropriately", "Sometimes", "No", "Not applicable"]),
     }},
    # 5. Parent-to-Parent Communication ----------------------------------
    {"id": "s5", "number": 5, "name": "Parent-to-Parent Communication",
     "purpose": "Assess how consistently parents discuss medication topics.",
     "items": {
        topic_id: _sg(f"How often do parents communicate about {label.lower()}?", FREQUENCY_5)
        for (topic_id, label) in PARENT_COMM_TOPICS
     }},
    # 6. Pharmacy Coordination -------------------------------------------
    {"id": "s6", "number": 6, "name": "Pharmacy Coordination",
     "purpose": "Assess whether both homes use a coordinated pharmacy pathway.",
     "items": {
        "same_pharmacy":        _sg("Do both parents use the same pharmacy for the child?", ["Yes always", "Usually", "Sometimes", "No"]),
        "both_authorized":      _sg("Are both parents authorised to pick up medication at that pharmacy?", YES_NO),
        "pharmacy_has_contacts": _sg("Does the pharmacy have current contact info for both parents?", YES_PARTIAL_NO),
        "pharmacist_alignment": _sg("How often are pharmacist recommendations shared between parents?", FREQUENCY_5),
        "delivery_pickup":      _sg("Are pharmacy delivery or automatic refill options in place?", YES_PARTIAL_NO),
     }},
    # 7. Financial / Insurance Barriers ----------------------------------
    {"id": "s7", "number": 7, "name": "Financial & Insurance Barriers",
     "purpose": "Surface financial or insurance blockers that could interrupt medication.",
     "items": {
        "financial_issues":  _ml("Which of the following apply? Select all that apply.", FINANCIAL_ISSUES),
        "cost_split_clear":  _sg("Is the cost-split for medication clearly agreed in writing?", YES_PARTIAL_NO),
        "reimbursement":     _sg("How consistently is one parent reimbursed when they front the cost?", FREQUENCY_5),
        "insurance_current": _sg("Is the child's active insurance card up-to-date in both homes?", YES_PARTIAL_NO),
        "affordability":     _sg("Overall, how affordable is the current medication routine?", ["Very affordable", "Affordable", "Neutral", "Somewhat difficult", "A major barrier"]),
     }},
    # 8. Controlled-Medication Accountability ----------------------------
    {"id": "s8", "number": 8, "name": "Controlled Medication Accountability",
     "purpose": "For controlled substances, assess safe storage, tracking, and transfer.",
     "gate": {"item": "has_controlled", "value": "Yes"},
     "items": {
        "has_controlled":     _sg("Is your child prescribed a controlled substance?", YES_NO),
        "controlled_type":    _sg("What best describes it?", ["Stimulant (ADHD medication)", "Benzodiazepine", "Opioid", "Other controlled substance", "Prefer not to say"]),
        "protections":        _ml("Which safeguards are currently in place in BOTH homes? Select all that apply.", CONTROL_PROTECTIONS),
        "count_tracking":     _sg("Is the pill/dose count tracked at each handoff?", YES_PARTIAL_NO),
        "diversion_concerns": _sg("Are you concerned about diversion or unauthorised access?", ["No concerns", "Mild concerns", "Moderate concerns", "Significant concerns"]),
        "provider_agreement": _sg("Is a controlled-substance / opioid agreement on file with the prescriber?", YES_PARTIAL_NO),
     }},
    # 9. School Medication Coordination ----------------------------------
    {"id": "s9", "number": 9, "name": "School Medication Coordination",
     "purpose": "Ensure the school medication process is authorised and reliable.",
     "gate": {"item": "school_meds", "value": "Yes"},
     "items": {
        "school_meds":         _sg("Does your child take medication at school or before/after care?", YES_NO),
        "school_items":        _ml("Which of the following are currently in place at school? Select all that apply.", SCHOOL_COORD_ITEMS),
        "both_on_paperwork":   _sg("Are both parents named on the school medication paperwork?", YES_PARTIAL_NO),
        "school_updates":      _sg("How consistently does the school report administration to both parents?", FREQUENCY_5),
        "field_trip_ready":    _sg("Is medication authorised and packed for field trips or off-campus events?", YES_PARTIAL_NO),
     }},
    # 10. Medication Disagreements ---------------------------------------
    {"id": "s10", "number": 10, "name": "Medication Decisions & Disagreements",
     "purpose": "Assess where parents disagree about medication decisions.",
     "items": {
        topic_id: _sg(f"How often do parents agree on {label.lower()}?", AGREEMENT_5)
        for (topic_id, label) in DISAGREEMENT_TOPICS
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
