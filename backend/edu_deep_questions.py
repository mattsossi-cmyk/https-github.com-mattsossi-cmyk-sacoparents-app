"""Educational Needs — Deep Dive schema.

A twelve-section optional companion assessment to the lighter SNC v2
educational pathway. Lives at /special-needs-v2/educational-deep-dive.

Design notes:
  * Questions are option-based wherever possible (single / multi / likert /
    yes-no) so parents rarely have to type. Free-text is reserved for open
    "anything else you want to note" fields.
  * The report only surfaces sections where the parent's answers indicate a
    concern (`is_flagged` in scoring). Every section still has a strength
    template applied when the answers indicate a strength.
  * Section 3 (ARD) is only shown when Section 1 school_state == "TX".
"""
from __future__ import annotations

from typing import Any, Dict, List


DEEP_DIVE_VERSION = "edu-deep-1.0.0"


# ---- shared option sets ----
FREQUENCY_5 = ["Always", "Usually", "Sometimes", "Rarely", "Never"]
FREQUENCY_4 = ["Always", "Usually", "Sometimes", "Never"]
AGREEMENT_5 = ["Always Agree", "Usually Agree", "Sometimes Agree", "Rarely Agree", "Never Agree"]
ROLE_4 = ["Mother", "Father", "Both", "Neither"]
CAREGIVER_4 = ["Mother", "Father", "Both", "Other caregiver"]
YES_NO = ["Yes", "No"]
YES_NO_UNSURE = ["Yes", "No", "Unsure"]

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "Other / Not US",
]

GRADE_LEVELS = [
    "PreK", "Kindergarten", "1st", "2nd", "3rd", "4th", "5th",
    "6th", "7th", "8th", "9th", "10th", "11th", "12th",
    "Post-secondary transition", "Not currently enrolled",
]

SCHOOL_SETTINGS = [
    "Public School", "Private School", "Charter School", "Homeschool",
    "Online / Virtual School", "Preschool / Early Learning Centre",
]

EDU_CONCERNS = [
    "Reading", "Writing", "Math", "Attention", "Executive Functioning",
    "Speech", "Language", "Social Skills", "Behaviour", "Emotional Regulation",
    "Gifted", "Dyslexia", "Dysgraphia", "Dyscalculia", "Autism",
    "ADHD", "Intellectual Disability", "Developmental Delay",
    "Learning Disability", "Other",
]

IEP_AREAS = [
    "Academic Goals", "Behaviour Goals", "Speech Goals",
    "Occupational Therapy Goals", "Social Goals", "Transition Goals",
    "Assistive Technology", "Transportation", "Testing Accommodations",
]

COUNSELOR_FREQ = ["Weekly", "Bi-weekly", "Monthly", "As-needed", "Rarely", "Never"]

TUTORING_TYPES = [
    "Private tutor", "Reading specialist", "Math specialist",
    "Speech support", "Academic coaching", "Learning pod", "Other",
]

SCHOOL_ROLES = [
    "Teacher", "Principal", "Assistant Principal", "Special Education Teacher",
    "School Counsellor", "Speech Therapist", "Occupational Therapist",
    "Behaviour Specialist", "Reading Specialist", "Math Specialist",
    "School Psychologist",
]

DECISION_TOPICS = [
    ("school_choice", "School choice"),
    ("special_ed_placement", "Special education placement"),
    ("testing", "Testing"),
    ("tutoring", "Tutoring"),
    ("summer_school", "Summer school"),
    ("extracurricular", "Extracurricular participation"),
    ("retention", "Grade retention"),
    ("advanced_classes", "Advanced classes"),
    ("behavior_plans", "Behaviour plans"),
    ("testing_accommodations", "Testing accommodations"),
    ("transportation", "Transportation"),
]

PLANNING_AREAS = ["Semester goals", "Reading goals", "Math goals", "Attendance", "Behaviour"]


def _lk(prompt: str, scored: bool = True) -> Dict[str, Any]:
    return {"type": "likert", "prompt": prompt, "scored": scored}


def _sg(prompt: str, options: List[str]) -> Dict[str, Any]:
    return {"type": "single", "prompt": prompt, "options": options}


def _ml(prompt: str, options: List[str]) -> Dict[str, Any]:
    return {"type": "multi", "prompt": prompt, "options": options}


def _tx(prompt: str) -> Dict[str, Any]:
    return {"type": "textarea", "prompt": prompt}


# ---- Section schema ----
# Each section has: id, number, name, purpose, items[], scoring policy
DEEP_DIVE_SECTIONS: List[Dict[str, Any]] = [
    # 1. Educational Profile ------------------------------------------------
    {"id": "s1", "number": 1, "name": "Educational Profile",
     "purpose": "Set the child's current schooling context.",
     "items": {
        "school_setting": _sg("What is your child's current school setting?", SCHOOL_SETTINGS),
        "grade_level":    _sg("What is your child's current grade level?", GRADE_LEVELS),
        "school_state":   _sg("Which state is the child's school located in?", US_STATES),
        "concerns":       _ml("Which educational areas are you concerned about? Select all that apply.", EDU_CONCERNS),
        "concern_notes":  _tx("Anything specific you want the report to note (optional)?"),
     }},
    # 2. Parent-Teacher Communication --------------------------------------
    {"id": "s2", "number": 2, "name": "Parent-Teacher Communication",
     "purpose": "Assess how consistently both parents engage with the classroom teacher.",
     "items": {
        "how_often_attend":   _sg("How often do you attend parent-teacher conferences?", FREQUENCY_5),
        "both_can_attend":    _sg("Can both parents attend?", FREQUENCY_5),
        "communicate_after":  _sg("Do the parents communicate after the meetings?", FREQUENCY_4),
        "discuss_goals":      _lk("Educational goals are discussed before the meeting."),
        "both_receive_updates": _sg("Do both parents receive school updates?", YES_NO),
     }},
    # 3. ARD Meetings (Texas only) -----------------------------------------
    {"id": "s3", "number": 3, "name": "ARD Meetings (Texas)",
     "purpose": "Assess ARD (Admission, Review, and Dismissal) participation. Shown only when the school state is Texas.",
     "texas_only": True,
     "items": {
        "attendees":            _ml("Who attends ARD meetings?", CAREGIVER_4),
        "review_plan_before":   _lk("Both parents review the proposed educational plan beforehand."),
        "comfort_participating": _lk("I am comfortable participating during ARD meetings."),
        "conflict_interferes":  _lk("Conflict between parents interferes with decision making."),
        "prepare_questions":    _lk("Parents prepare questions beforehand."),
        "decisions_focus_child": _lk("Decisions are focused on the child's needs."),
     }},
    # 4. IEP ---------------------------------------------------------------
    {"id": "s4", "number": 4, "name": "Individualized Education Program (IEP)",
     "purpose": "Understand how well both homes engage with the IEP.",
     "gate": {"item": "has_iep", "value": "Yes"},
     "items": {
        "has_iep":                _sg("Does your child currently have an IEP?", YES_NO),
        "who_reviews":            _sg("Who reviews the IEP?", ["Mother", "Father", "Both", "School only"]),
        "familiar_with_goals":    _lk("I am familiar with my child's IEP goals."),
        "both_homes_support":     _lk("Both homes support the IEP."),
        "monitor_progress":       _lk("Parents monitor progress against the IEP."),
        "accommodations_consistent": _lk("Accommodations are implemented consistently in both homes."),
        "iep_areas":              _ml("Which IEP areas apply to your child?", IEP_AREAS),
     }},
    # 5. Section 504 Plan --------------------------------------------------
    {"id": "s5", "number": 5, "name": "Section 504 Plan",
     "purpose": "Understand engagement with the child's 504 Plan.",
     "gate": {"item": "has_504", "value": "Yes"},
     "items": {
        "has_504":                    _sg("Does your child have a 504 Plan?", YES_NO),
        "understanding_accommodations": _lk("I understand the accommodations in the 504 Plan."),
        "consistency_across_homes":   _lk("Accommodations are applied consistently across both homes."),
        "school_communication":       _lk("Communication with the school about the 504 Plan is timely."),
        "implementation":             _lk("Accommodations are actually implemented at school."),
        "annual_reviews":             _lk("Annual reviews are completed on time."),
     }},
    # 6. School Counselor --------------------------------------------------
    {"id": "s6", "number": 6, "name": "School Counsellor",
     "purpose": "Understand the child's engagement with the school counsellor.",
     "gate": {"item": "meets_counselor", "value": "Yes"},
     "items": {
        "meets_counselor":       _sg("Does your child meet with a school counsellor?", YES_NO),
        "frequency":             _sg("How often?", COUNSELOR_FREQ),
        "parents_communicate":   _lk("Both parents communicate with the counsellor."),
        "counselor_provides_recs": _sg("Does the counsellor provide recommendations?", YES_NO),
        "recs_followed":         _lk("Recommendations from the counsellor are followed at home."),
        "support_emotional_home": _lk("Emotional-regulation strategies are supported at home."),
     }},
    # 7. Academic Support Services ----------------------------------------
    {"id": "s7", "number": 7, "name": "Academic Support Services",
     "purpose": "Assess consistency of tutoring, Kumon, Sylvan, or other academic supports.",
     "items": {
        "supports_enrolled":     _ml("Which academic support services is the child currently enrolled in? Select all that apply.",
                                     ["Kumon", "Sylvan Learning"] + TUTORING_TYPES + ["None"]),
        "who_transports":        _sg("Who typically transports the child to these services?", CAREGIVER_4 + ["Not applicable"]),
        "who_supervises":        _sg("Who supervises homework related to these services?", CAREGIVER_4 + ["Not applicable"]),
        "attendance_consistency": _lk("Attendance at these services is consistent."),
        "parent_communication":  _lk("Parents communicate with each other about attendance and progress."),
        "progress_monitoring":   _lk("Both parents monitor the child's progress in these services."),
        "commitment":            _lk("Both parents are committed to continuing these services."),
     }},
    # 8. Homework & Home Learning ----------------------------------------
    {"id": "s8", "number": 8, "name": "Homework & Home Learning",
     "purpose": "Assess how consistently the child's home learning environment is supported.",
     "items": {
        "homework_consistent":       _lk("Homework expectations are consistent between homes."),
        "quiet_study_spaces":        _lk("Both homes have a quiet study space."),
        "assignments_completed":     _lk("Assignments are completed on time."),
        "communicate_missing_work":  _lk("Parents communicate about missing work."),
        "child_encouraged":          _lk("The child receives encouragement about school work in both homes."),
        "technology_available":      _lk("Technology needed for school is available in both homes."),
     }},
    # 9. Communication with School ----------------------------------------
    {"id": "s9", "number": 9, "name": "Communication with School",
     "purpose": "Assess general communication with school staff across both homes.",
     "items": {
        "roles_involved":         _ml("Which school staff are involved with your child? Select all that apply.", SCHOOL_ROLES),
        "who_communicates":       _sg("Who typically communicates with the school?", ROLE_4),
        "communication_respectful": _lk("Communication with the school is respectful."),
        "information_shared":     _lk("School information is shared between parents."),
        "same_information":       _sg("Do both parents receive the same information from the school?", FREQUENCY_5),
     }},
    # 10. Educational Decision Making -------------------------------------
    {"id": "s10", "number": 10, "name": "Educational Decision Making",
     "purpose": "Assess whether parents can agree on major educational decisions.",
     "items": {
        topic_id: _sg(prompt, AGREEMENT_5) for (topic_id, prompt) in DECISION_TOPICS
     }},
    # 11. Educational Advocacy --------------------------------------------
    {"id": "s11", "number": 11, "name": "Educational Advocacy",
     "purpose": "Assess how well parents advocate together for their child.",
     "items": {
        "know_rights":         _lk("Parents know their educational rights."),
        "prepare_meetings":    _lk("Parents prepare for school meetings."),
        "ask_questions":       _lk("Parents ask questions during school meetings."),
        "advocate_respectfully": _lk("Parents advocate respectfully with school staff."),
        "focus_long_term":     _lk("Parents focus on the child's long-term success."),
        "understand_reports":  _lk("Parents understand educational reports and test results."),
     }},
    # 12. Educational Planning --------------------------------------------
    {"id": "s12", "number": 12, "name": "Educational Planning",
     "purpose": "Capture the parent's short-term planning priorities.",
     "items": {
        "planning_areas":       _ml("Which areas are you actively planning for over the next semester? Select all that apply.", PLANNING_AREAS),
        "priority_area":        _sg("Which planning area is highest priority right now?",
                                    PLANNING_AREAS + ["Other / Not sure"]),
        "biggest_barrier":      _sg("What is the biggest barrier to consistent planning?",
                                    ["Time", "Cost", "Communication with co-parent",
                                     "Communication with school", "Child engagement", "Other / Not sure"]),
     }},
]


# ---- helper for the frontend ----
def public_schema() -> Dict[str, Any]:
    """Serialisable schema used by the React page."""
    return {
        "version": DEEP_DIVE_VERSION,
        "sections": [
            {
                "id": s["id"],
                "number": s["number"],
                "name": s["name"],
                "purpose": s.get("purpose"),
                "texas_only": bool(s.get("texas_only")),
                "gate": s.get("gate"),
                "items": [
                    {"id": iid, **spec} for iid, spec in s["items"].items()
                ],
            }
            for s in DEEP_DIVE_SECTIONS
        ],
    }


def all_item_keys() -> List[str]:
    """`{section_id}_{item_id}` composite keys used as answer keys."""
    out = []
    for s in DEEP_DIVE_SECTIONS:
        for iid in s["items"].keys():
            out.append(f"{s['id']}_{iid}")
    return out


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
