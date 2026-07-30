"""SA CoParents — Special Needs Co-Parenting Assessment Framework (2026 spec).

Single-parent, 5-point Likert with meta-options. Ten scored domains map to
the framework sections 3–14. Safety (Domain 10) is handled separately —
safety-sensitive answers trigger a review flag rather than being averaged
into a strength score.

The intake profile (Sections 2 and 15) is unscored and captured separately.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# 5-point Likert (int 0..4). Kept as ints for scoring math.
RESPONSE_SCALE: List[Dict[str, Any]] = [
    {"value": 0, "label": "Strongly disagree"},
    {"value": 1, "label": "Disagree"},
    {"value": 2, "label": "Unsure or insufficient information"},
    {"value": 3, "label": "Agree"},
    {"value": 4, "label": "Strongly agree"},
]

# Meta-flags per question. Each is optional and may be combined.
META_FLAGS: List[Dict[str, str]] = [
    {"key": "na",           "label": "Not applicable"},
    {"key": "need_info",    "label": "I need more information"},
    {"key": "want_help",    "label": "I would like professional guidance"},
    {"key": "safety",       "label": "I have a safety concern"},
]


# ---------------------------------------------------------------------------
# Intake profile — Sections 2 + 15. Unscored.
# ---------------------------------------------------------------------------
INTAKE_PROFILE: List[Dict[str, Any]] = [
    {"group": "child", "label": "About your child", "fields": [
        {"id": "child_age",              "label": "Child's age (years)",                             "type": "number"},
        {"id": "child_grade",            "label": "Grade / classroom setting",                       "type": "text"},
        {"id": "school_setting",         "label": "School and classroom setting (public / private / homeschool / other)", "type": "text"},
        {"id": "diagnoses",              "label": "Diagnosed conditions (comma-separated)",          "type": "text"},
        {"id": "suspected",              "label": "Suspected or currently being evaluated for",      "type": "text"},
        {"id": "primary_needs",          "label": "Physical, developmental, emotional, behavioral, or learning needs", "type": "textarea"},
        {"id": "communication_ability",  "label": "Child's communication abilities",                 "type": "textarea"},
        {"id": "professionals",          "label": "Professionals currently involved (pediatrician, therapist, teacher…)", "type": "textarea"},
        {"id": "supports",               "label": "Medications, therapies, accommodations, services", "type": "textarea"},
        {"id": "cultural_notes",         "label": "Important cultural, linguistic, or family considerations", "type": "textarea"},
    ]},
    {"group": "family", "label": "About your family", "fields": [
        {"id": "parenting_schedule",     "label": "Current parenting schedule",                      "type": "textarea"},
        {"id": "other_children",         "label": "Other children in each household",                "type": "text"},
        {"id": "distance",               "label": "Distance between homes and school",               "type": "text"},
        {"id": "decision_making",        "label": "Current decision-making arrangement (joint / one parent / court-ordered)", "type": "text"},
        {"id": "court_orders",           "label": "Existing court orders or parenting agreements",   "type": "textarea"},
        {"id": "comm_method",            "label": "Current method of parent communication",          "type": "text"},
        {"id": "conflict_history",       "label": "History of significant co-parenting conflict or family violence (safe to answer briefly; details are not required here)", "type": "textarea"},
    ]},
    {"group": "voice", "label": "Your child's voice", "fields": [
        {"id": "child_shared",           "label": "What has your child communicated about routines and transitions?", "type": "textarea"},
        {"id": "child_secure",           "label": "Which supports help your child feel most secure?", "type": "textarea"},
        {"id": "child_preferred_comm",   "label": "How does your child prefer to communicate?",       "type": "text"},
        {"id": "child_strengths",        "label": "Your child's interests and strengths",              "type": "textarea"},
    ]},
]


# ---------------------------------------------------------------------------
# 10 scored domains. Each question is one Likert item. Domain 10 (Safety) uses
# reverse-scored items — high agreement equals more safety-sensitive concern.
# ---------------------------------------------------------------------------
DOMAINS: List[Dict[str, Any]] = [
    {
        "id": "d1", "number": 1,
        "name": "Understanding the Child",
        "goal": "Your knowledge of your child's strengths, needs, triggers, and what helps them recover from stress.",
        "framework_ref": "Section 3",
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
        "goal": "School participation, accommodations, IEP/504 involvement, and information sharing about school.",
        "framework_ref": "Section 5 · Section 9",
        "questions": [
            {"id": "d2_q1", "prompt": "I attend parent-teacher conferences and share notes with the other parent when appropriate."},
            {"id": "d2_q2", "prompt": "I participate in ARD / IEP / Section 504 meetings and follow the plan."},
            {"id": "d2_q3", "prompt": "I share school notices, progress reports, and incident notifications promptly."},
            {"id": "d2_q4", "prompt": "I follow the educational strategies recommended by school in my home."},
            {"id": "d2_q5", "prompt": "I ensure both parents are on the school's official contact list."},
            {"id": "d2_q6", "prompt": "I support the child's accommodations and safety plan during school activities."},
        ],
    },
    {
        "id": "d3", "number": 3,
        "name": "Healthcare Coordination",
        "goal": "Medical, mental-health, therapy, and medication management across both homes.",
        "framework_ref": "Section 6",
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
        "framework_ref": "Section 7",
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
        "framework_ref": "Section 8",
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
        "framework_ref": "Section 10",
        "questions": [
            {"id": "d6_q1", "prompt": "I share medical, therapy, and school information with the other parent in a timely way."},
            {"id": "d6_q2", "prompt": "My messages are brief, informative, friendly (or neutral), and firm — child-focused."},
            {"id": "d6_q3", "prompt": "I keep written records of important agreements and updates."},
            {"id": "d6_q4", "prompt": "I respond within a reasonable time to non-emergency messages."},
            {"id": "d6_q5", "prompt": "I avoid accusations or venting in messages the other parent will read."},
            {"id": "d6_q6", "prompt": "I use a communication method that works even when safety or trust is low (app / email / neutral third party)."},
        ],
    },
    {
        "id": "d7", "number": 7,
        "name": "Decision-Making",
        "goal": "How well parents make and resolve decisions about the child.",
        "framework_ref": "Section 11",
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
        "framework_ref": "Section 9",
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
        "framework_ref": "Section 12",
        "questions": [
            {"id": "d9_q1", "prompt": "Health-insurance and uninsured-medical responsibilities are clear between us."},
            {"id": "d9_q2", "prompt": "I use a clear reimbursement or prior-consent procedure for shared expenses."},
            {"id": "d9_q3", "prompt": "I know what public or community resources my child qualifies for."},
            {"id": "d9_q4", "prompt": "Financial disagreements are not currently delaying services my child needs."},
            {"id": "d9_q5", "prompt": "I plan ahead for the cost of therapies, evaluations, and adaptive equipment."},
            {"id": "d9_q6", "prompt": "I document shared expenses in a way both parents can see."},
        ],
    },
    # Domain 10 — Safety. Reverse-scored: "Strongly agree" = safety-sensitive
    # concern present. These items trigger a separate safety review; they are
    # NOT averaged into an overall strength score.
    {
        "id": "d10", "number": 10,
        "name": "Safety & Communication Safety",
        "goal": "Screen for coercive control, harassment, protective-order concerns, and communication safety needs.",
        "framework_ref": "Section 13",
        "safety_sensitive": True,
        "questions": [
            {"id": "d10_q1", "prompt": "I sometimes feel afraid of the other parent.",                                                          "reverse": True, "safety_flag": True},
            {"id": "d10_q2", "prompt": "The other parent has threatened, stalked, or harassed me.",                                              "reverse": True, "safety_flag": True},
            {"id": "d10_q3", "prompt": "There is a history of physical violence or coercive control in our relationship.",                       "reverse": True, "safety_flag": True},
            {"id": "d10_q4", "prompt": "Medical, school, or child information has been used to control or punish me.",                           "reverse": True, "safety_flag": True},
            {"id": "d10_q5", "prompt": "Exchanges feel unsafe or increase conflict for me or my child.",                                         "reverse": True, "safety_flag": True},
            {"id": "d10_q6", "prompt": "There is a current protective order or unresolved legal safety concern between us.",                     "reverse": True, "safety_flag": True},
        ],
    },
]


def total_question_count() -> int:
    return sum(len(d["questions"]) for d in DOMAINS)


def find_question(qid: str) -> Optional[Dict[str, Any]]:
    for d in DOMAINS:
        for q in d["questions"]:
            if q["id"] == qid:
                return q
    return None


def find_domain(did: str) -> Optional[Dict[str, Any]]:
    for d in DOMAINS:
        if d["id"] == did:
            return d
    return None
