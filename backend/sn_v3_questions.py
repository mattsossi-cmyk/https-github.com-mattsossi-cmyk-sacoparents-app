"""SA CoParents — Special Needs Co-Parenting Assessment Framework (2026 spec).

Organised to match the Co-Parenting Assessment product exactly:
    - 5-point Likert (0-4) with the same labels.
    - Sections (id d1..d9) each containing 6 questions.
    - Ratings and overall are the same vocabulary as the Co-Parenting product,
      so the Family Report can compose the two identically.

Special Needs-specific additions kept:
    - Unscored intake profile (child + family + child's voice).
    - Meta-flags per question: Not applicable, I need more information,
      I would like professional guidance.

Family-violence / interparental safety is intentionally NOT part of this
assessment. That subject is handled by the separate Family Violence &
Communication Safety product.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# 5-point Likert (int 0..4). Same as Co-Parenting.
RESPONSE_SCALE: List[Dict[str, Any]] = [
    {"value": 0, "label": "Strongly disagree"},
    {"value": 1, "label": "Disagree"},
    {"value": 2, "label": "Unsure or insufficient information"},
    {"value": 3, "label": "Agree"},
    {"value": 4, "label": "Strongly agree"},
]

# Meta-flags per question. Each is optional and may be combined.
META_FLAGS: List[Dict[str, str]] = [
    {"key": "na",        "label": "Not applicable"},
    {"key": "need_info", "label": "I need more information"},
    {"key": "want_help", "label": "I would like professional guidance"},
]


# ---------------------------------------------------------------------------
# Intake profile — child + family + child's voice. Unscored.
# ---------------------------------------------------------------------------
INTAKE_PROFILE: List[Dict[str, Any]] = [
    {"group": "child", "label": "About your child", "fields": [
        {"id": "child_age",              "label": "Child's age (years)",                              "type": "number"},
        {"id": "child_grade",            "label": "Grade / classroom setting",                        "type": "text"},
        {"id": "school_setting",         "label": "School and classroom setting (public / private / homeschool / other)", "type": "text"},
        {"id": "diagnoses",              "label": "Diagnosed conditions (comma-separated)",           "type": "text"},
        {"id": "suspected",              "label": "Suspected or currently being evaluated for",       "type": "text"},
        {"id": "primary_needs",          "label": "Physical, developmental, emotional, behavioral, or learning needs", "type": "textarea"},
        {"id": "communication_ability",  "label": "Child's communication abilities",                  "type": "textarea"},
        {"id": "professionals",          "label": "Professionals currently involved (pediatrician, therapist, teacher...)", "type": "textarea"},
        {"id": "supports",               "label": "Medications, therapies, accommodations, services", "type": "textarea"},
        {"id": "cultural_notes",         "label": "Important cultural, linguistic, or family considerations", "type": "textarea"},
    ]},
    {"group": "family", "label": "About your family", "fields": [
        {"id": "parenting_schedule",     "label": "Current parenting schedule",                       "type": "textarea"},
        {"id": "other_children",         "label": "Other children in each household",                 "type": "text"},
        {"id": "distance",               "label": "Distance between homes and school",                "type": "text"},
        {"id": "decision_making",        "label": "Current decision-making arrangement (joint / one parent / court-ordered)", "type": "text"},
        {"id": "court_orders",           "label": "Existing court orders or parenting agreements",    "type": "textarea"},
        {"id": "comm_method",            "label": "Current method of parent communication",           "type": "text"},
    ]},
    {"group": "voice", "label": "Your child's voice", "fields": [
        {"id": "child_shared",           "label": "What has your child communicated about routines and transitions?", "type": "textarea"},
        {"id": "child_secure",           "label": "Which supports help your child feel most secure?", "type": "textarea"},
        {"id": "child_preferred_comm",   "label": "How does your child prefer to communicate?",       "type": "text"},
        {"id": "child_strengths",        "label": "Your child's interests and strengths",             "type": "textarea"},
    ]},
]


# ---------------------------------------------------------------------------
# 9 scored sections (Special Needs–specific).
# IDs are kept as d1..d9 so existing databases/reports don't collide with
# Co-Parenting's s1..s10 IDs. Every question is a positive-worded Likert item
# scored 0..4 on the standard scale (no reverse-scored items).
# ---------------------------------------------------------------------------
SECTIONS: List[Dict[str, Any]] = [
    {
        "id": "d1", "number": 1,
        "name": "Understanding the Child",
        "goal": "Your knowledge of your child's strengths, needs, triggers, and what helps them recover from stress.",
        "questions": [
            {"id": "d1_q1", "prompt": "I understand my child's primary areas of need."},
            {"id": "d1_q2", "prompt": "I can identify situations that cause my child distress or dysregulation."},
            {"id": "d1_q3", "prompt": "I understand the strategies professionals recommend for my child."},
            {"id": "d1_q4", "prompt": "I recognise my child's strengths and interests, not only their challenges."},
            {"id": "d1_q5", "prompt": "I am willing to reconsider my understanding when new professional information becomes available."},
            {"id": "d1_q6", "prompt": "I know the strategies that help my child recover from stress."},
        ],
    },
    {
        "id": "d2", "number": 2,
        "name": "Educational Coordination",
        "goal": "School participation, accommodations, IEP / 504 involvement, and information sharing about school.",
        "questions": [
            {"id": "d2_q1", "prompt": "I attend parent-teacher conferences and share notes with the other parent when appropriate."},
            {"id": "d2_q2", "prompt": "I participate in ARD / IEP / Section 504 meetings and follow the plan."},
            {"id": "d2_q3", "prompt": "I share school notices, progress reports, and incident notifications promptly."},
            {"id": "d2_q4", "prompt": "I follow the educational strategies recommended by school in my home."},
            {"id": "d2_q5", "prompt": "I ensure both parents are on the school's official contact list."},
            {"id": "d2_q6", "prompt": "I support the child's accommodations during school activities."},
        ],
    },
    {
        "id": "d3", "number": 3,
        "name": "Healthcare Coordination",
        "goal": "Medical, mental-health, therapy, and medication management across both homes.",
        "questions": [
            {"id": "d3_q1", "prompt": "I keep an up-to-date list of medications, dosages, and prescribers."},
            {"id": "d3_q2", "prompt": "I follow through on therapy appointments and reinforce home-carryover strategies."},
            {"id": "d3_q3", "prompt": "I share medical results, appointments, and prescription changes with the other parent."},
            {"id": "d3_q4", "prompt": "I coordinate refill responsibilities and medication transfers between homes."},
            {"id": "d3_q5", "prompt": "I know how to contact prescribing and treating professionals directly."},
            {"id": "d3_q6", "prompt": "I use a clear process for resolving disagreements about medical or therapeutic decisions."},
        ],
    },
    {
        "id": "d4", "number": 4,
        "name": "Daily-Care Consistency",
        "goal": "Whether your home offers stable, predictable, developmentally-appropriate daily care.",
        "questions": [
            {"id": "d4_q1", "prompt": "I keep consistent morning and bedtime routines."},
            {"id": "d4_q2", "prompt": "I support my child's sensory needs, screen limits, and comfort objects."},
            {"id": "d4_q3", "prompt": "I follow through on homework, therapy carry-over, and medication in my home."},
            {"id": "d4_q4", "prompt": "I supervise my child at an age- and needs-appropriate level."},
            {"id": "d4_q5", "prompt": "I prepare my child in advance for changes, appointments, and transitions."},
            {"id": "d4_q6", "prompt": "I aim for enough consistency with the other home to support my child (not identical, but predictable)."},
        ],
    },
    {
        "id": "d5", "number": 5,
        "name": "Transition Support",
        "goal": "Exchanges, transportation, and how well your child adjusts between homes.",
        "questions": [
            {"id": "d5_q1", "prompt": "Exchange times and locations work for my child's needs."},
            {"id": "d5_q2", "prompt": "I use visual schedules, warnings, or checklists to help my child prepare for transitions."},
            {"id": "d5_q3", "prompt": "Medication, equipment, schoolwork, and comfort items travel reliably between homes."},
            {"id": "d5_q4", "prompt": "I give my child recovery time and calm space after exchanges."},
            {"id": "d5_q5", "prompt": "My child's response to transitions is manageable."},
            {"id": "d5_q6", "prompt": "When direct exchanges become difficult, I am open to a neutral or school-based location."},
        ],
    },
    {
        "id": "d6", "number": 6,
        "name": "Communication",
        "goal": "Timely, accurate, child-focused information sharing between homes.",
        "questions": [
            {"id": "d6_q1", "prompt": "I share medical, therapy, and school information with the other parent in a timely way."},
            {"id": "d6_q2", "prompt": "My messages are brief, informative, friendly (or neutral), and firm — child-focused."},
            {"id": "d6_q3", "prompt": "I keep written records of important agreements and updates."},
            {"id": "d6_q4", "prompt": "I respond within a reasonable time to non-emergency messages."},
            {"id": "d6_q5", "prompt": "I avoid accusations or venting in messages the other parent will read."},
            {"id": "d6_q6", "prompt": "I use a communication method that produces a written, timestamped record (app / email / neutral third party)."},
        ],
    },
    {
        "id": "d7", "number": 7,
        "name": "Decision-Making",
        "goal": "How well parents make and resolve decisions about the child.",
        "questions": [
            {"id": "d7_q1", "prompt": "I exchange the relevant records before major decisions are made."},
            {"id": "d7_q2", "prompt": "I bring the child's professionals in for input when decisions are complex."},
            {"id": "d7_q3", "prompt": "I follow the parenting plan or court-ordered decision-making procedure."},
            {"id": "d7_q4", "prompt": "I am open to mediation or facilitated problem-solving when we're stuck."},
            {"id": "d7_q5", "prompt": "I distinguish disagreement about the child's needs from missing information or different observations."},
            {"id": "d7_q6", "prompt": "Emergency and urgent decisions have a clear, agreed-upon process."},
        ],
    },
    {
        "id": "d8", "number": 8,
        "name": "Event Participation",
        "goal": "School events and extracurriculars — attendance, coordination, and child-first behaviour.",
        "questions": [
            {"id": "d8_q1", "prompt": "I promptly share information about the child's events and activities."},
            {"id": "d8_q2", "prompt": "I can attend an event with the other parent without involving the child in conflict."},
            {"id": "d8_q3", "prompt": "I support activities that fit the child's interests, abilities, and accommodations."},
            {"id": "d8_q4", "prompt": "I follow through on registration, transportation, uniforms, and payments in my time."},
            {"id": "d8_q5", "prompt": "The child is not expected to choose which parent may attend."},
            {"id": "d8_q6", "prompt": "I have a plan for responding calmly if my child becomes overwhelmed at an event."},
        ],
    },
    {
        "id": "d9", "number": 9,
        "name": "Resource Coordination",
        "goal": "Financial, insurance, and service coordination that keeps care flowing.",
        "questions": [
            {"id": "d9_q1", "prompt": "Health-insurance and uninsured-medical responsibilities are clear between us."},
            {"id": "d9_q2", "prompt": "I use a clear reimbursement or prior-consent procedure for shared expenses."},
            {"id": "d9_q3", "prompt": "I know what public or community resources my child qualifies for."},
            {"id": "d9_q4", "prompt": "Financial disagreements are not currently delaying services my child needs."},
            {"id": "d9_q5", "prompt": "I plan ahead for the cost of therapies, evaluations, and adaptive equipment."},
            {"id": "d9_q6", "prompt": "I document shared expenses in a way both parents can see."},
        ],
    },
]

# Backwards-compat alias — earlier code referenced DOMAINS.
DOMAINS = SECTIONS


def total_question_count() -> int:
    return sum(len(s["questions"]) for s in SECTIONS)


def find_question(qid: str) -> Optional[Dict[str, Any]]:
    for s in SECTIONS:
        for q in s["questions"]:
            if q["id"] == qid:
                return q
    return None


def find_section(sid: str) -> Optional[Dict[str, Any]]:
    for s in SECTIONS:
        if s["id"] == sid:
            return s
    return None


# Keep the previous public name working for any external callers.
find_domain = find_section
