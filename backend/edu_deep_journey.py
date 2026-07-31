"""Educational Deep Dive — SA CoParents journey report.

Produces the polished, action-oriented report matching the shared SA CoParents
journey:

    Situation → Assessment Results → Child's Needs → Co-Parenting Challenges
    → Practical Options → Parent Action Plan → Foundation Statement

The output is a structured dict consumed by both the React report page and the
FPDF PDF renderer. Neutral, parent-attributed, non-diagnostic, non-adjudicative.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional

from edu_deep_questions import DECISION_TOPICS


# ---- shared scales (kept local so the mapping is auditable) ---------------
FREQ_MAP = {"Always": 5, "Usually": 4, "Sometimes": 3, "Rarely": 2, "Never": 1}
CONSIST_MAP = {"Always Consistent": 5, "Usually Consistent": 4,
               "Sometimes Consistent": 3, "Rarely Consistent": 2,
               "Never Consistent": 1}
AGREE_MAP = {"Always Agree": 5, "Usually Agree": 4, "Sometimes Agree": 3,
             "Rarely Agree": 2, "Never Agree": 1}
YES_NO_MAP = {"Yes": 5, "No": 1}
FREQ4_MAP = {"Consistently": 5, "Usually": 4, "Occasionally": 3, "Rarely": 1}


def _int(v):
    return v if isinstance(v, int) and 1 <= v <= 5 else None


def _rate(score: Optional[float]) -> str:
    if score is None:
        return "Not enough info"
    if score >= 4.0:
        return "Strong"
    if score >= 2.5:
        return "Developing"
    return "Needs Attention"


def _avg(xs: List[int]) -> Optional[float]:
    return mean(xs) if xs else None


def _pull(responses: Dict[str, Any], *keys) -> List[int]:
    xs = []
    for k in keys:
        v = responses.get(k)
        if isinstance(v, int) and 1 <= v <= 5:
            xs.append(v)
        elif isinstance(v, str):
            for m in (FREQ_MAP, CONSIST_MAP, AGREE_MAP, YES_NO_MAP, FREQ4_MAP):
                if v in m:
                    xs.append(m[v])
                    break
    return xs


# ---------------------------------------------------------------------------
# 1) Rating areas (Educational Support Summary)
# ---------------------------------------------------------------------------

def _rating_areas(responses: Dict[str, Any]) -> List[Dict[str, Any]]:
    areas = []

    # a. Understanding the child's educational needs
    xs = _pull(
        responses,
        "s4_familiar_with_goals", "s5_understanding_accommodations",
        "s11_understand_reports", "s6_recs_followed", "s6_support_emotional_home",
    )
    concerns_named = len(responses.get("s1_concerns") or [])
    if concerns_named:
        # Naming concerns is a positive engagement signal, but only mildly.
        xs.append(4 if concerns_named <= 3 else 3)
    a = _avg(xs)
    areas.append({
        "id": "understanding",
        "area": "Understanding the child's educational needs",
        "rating": _rate(a), "score": None if a is None else round(a, 2),
        "narrative": (
            "You have named specific educational concerns and reviewed the "
            "supports in place."
            if a and a >= 4 else
            "You are still building a full picture of your child's educational needs."
            if a and a >= 2.5 else
            "There may be gaps in shared understanding of your child's educational needs."
        ),
    })

    # b. Parent-school involvement
    xs = _pull(
        responses,
        "s11_prepare_meetings", "s11_ask_questions", "s11_advocate_respectfully",
    )
    freq_attend = FREQ_MAP.get(responses.get("s2_how_often_attend"))
    if freq_attend is not None:
        xs.append(freq_attend)
    a = _avg(xs)
    areas.append({
        "id": "involvement",
        "area": "Parent-school involvement",
        "rating": _rate(a), "score": None if a is None else round(a, 2),
        "narrative": (
            "You attend meetings, prepare, and advocate respectfully with the school."
            if a and a >= 4 else
            "You are involved with the school but attendance or preparation is inconsistent."
            if a and a >= 2.5 else
            "Involvement with teachers, counsellors, or the school team is limited."
        ),
    })

    # c. Information sharing between parents
    xs = _pull(responses, "s9_information_shared", "s9_same_information")
    if responses.get("s2_both_receive_updates") == "Yes":
        xs.append(5)
    elif responses.get("s2_both_receive_updates") == "No":
        xs.append(1)
    a = _avg(xs)
    areas.append({
        "id": "sharing",
        "area": "Information sharing between parents",
        "rating": _rate(a), "score": None if a is None else round(a, 2),
        "narrative": (
            "Report cards, updates, and school notices are being shared reliably between homes."
            if a and a >= 4 else
            "Information is shared some of the time, but gaps exist that could cause missed deadlines."
            if a and a >= 2.5 else
            "School information is not reliably reaching both parents."
        ),
    })

    # d. Homework & routine consistency
    xs = _pull(
        responses,
        "s8_homework_consistent", "s8_quiet_study_spaces", "s8_assignments_completed",
        "s8_communicate_missing_work", "s8_child_encouraged", "s8_technology_available",
    )
    a = _avg(xs)
    areas.append({
        "id": "homework",
        "area": "Homework and routine consistency",
        "rating": _rate(a), "score": None if a is None else round(a, 2),
        "narrative": (
            "Homework routines, study spaces, and encouragement are consistent across both homes."
            if a and a >= 4 else
            "Homework and routines are mostly working, with some inconsistencies between homes."
            if a and a >= 2.5 else
            "Homework expectations differ meaningfully between homes and may be affecting the child."
        ),
    })

    # e. Agreement about educational services
    xs = _pull(
        responses,
        "s7_parent_communication", "s7_progress_monitoring", "s7_commitment",
        "s4_both_homes_support",
    )
    a = _avg(xs)
    areas.append({
        "id": "services",
        "area": "Agreement about educational services",
        "rating": _rate(a), "score": None if a is None else round(a, 2),
        "narrative": (
            "You and your co-parent are aligned on tutoring, therapies, and school-based supports."
            if a and a >= 4 else
            "There is partial alignment on educational services — expect some negotiation."
            if a and a >= 2.5 else
            "Agreement on tutoring, IEP support, or extra services is limited right now."
        ),
    })

    # f. Ability to make educational decisions
    xs = []
    for (tid, _prompt) in DECISION_TOPICS:
        v = responses.get(f"s10_{tid}")
        if v in AGREE_MAP:
            xs.append(AGREE_MAP[v])
    # ARD conflict signal (Texas only, reverse-scored)
    ci = _int(responses.get("s3_conflict_interferes"))
    if ci is not None:
        xs.append(6 - ci)
    a = _avg(xs)
    areas.append({
        "id": "decisions",
        "area": "Ability to make educational decisions",
        "rating": _rate(a), "score": None if a is None else round(a, 2),
        "narrative": (
            "You and your co-parent regularly reach educational decisions together."
            if a and a >= 4 else
            "Some decisions get made together; others stall or default to one parent."
            if a and a >= 2.5 else
            "Educational decisions are difficult to reach jointly, and this may delay support for your child."
        ),
    })

    return areas


# ---------------------------------------------------------------------------
# 2) Child's Educational Profile
# ---------------------------------------------------------------------------

STRENGTH_HINTS = [
    "Positive engagement with subjects the child enjoys",
    "Willingness to attend and try new things at school",
    "Strong relationships with teachers or peers when supported",
    "Ability to grow when both homes reinforce the same routines",
]

def _child_profile(responses: Dict[str, Any]) -> Dict[str, Any]:
    concerns = responses.get("s1_concerns") or []
    strengths = STRENGTH_HINTS[:4]  # neutral defaults — parent can override in-app later
    primary = concerns[0] if concerns else "General educational coordination"
    benefit = "consistent homework routines and a shared school-information process"
    if any(c for c in concerns if "IEP" in c or "reading" in c.lower() or "math" in c.lower()):
        benefit = "an updated educational evaluation and a written support plan"
    if any(c for c in concerns if "anxiety" in c.lower() or "refusal" in c.lower()):
        benefit = "coordinated emotional support and a plan for handoff mornings"
    notes = (responses.get("s1_concern_notes") or "").strip()
    return {
        "strengths": strengths,
        "concerns": concerns,
        "primary_concern": primary,
        "benefit_from": benefit,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# 3) School Involvement (roles + meetings)
# ---------------------------------------------------------------------------

MEETING_MAP = [
    ("Parent-teacher conference",
     lambda r: "Scheduled" if r.get("s2_how_often_attend") in ("Always", "Usually")
     else ("Completed" if r.get("s2_how_often_attend") == "Sometimes" else "Needed"),
     "Prepare a shared list of questions with the other parent"),
    ("ARD or IEP meeting",
     lambda r: "Active" if r.get("s4_has_iep") == "Yes"
     else ("Requested" if r.get("s3_attendees") else "Not applicable"),
     "Review the proposed goals and share notes with the other parent"),
    ("School counsellor",
     lambda r: "Involved" if r.get("s6_meets_counselor") == "Yes" else "Not involved",
     "Discuss emotional or social concerns"),
    ("Tutoring / academic support",
     lambda r: ("Current" if (r.get("s7_supports_enrolled") or []) and
                (r.get("s7_supports_enrolled") or []) != ["None"]
                else "Under consideration"),
     "Agree on provider, schedule, and cost"),
    ("Educational evaluation",
     lambda r: "Completed" if r.get("s4_has_iep") == "Yes" or r.get("s5_has_504") == "Yes"
     else "Not requested",
     "Obtain and share the written report"),
]


def _school_involvement(responses: Dict[str, Any]) -> Dict[str, Any]:
    roles = responses.get("s9_roles_involved") or []
    meetings = [
        {"name": name, "current_status": fn(responses), "next_step": step}
        for (name, fn, step) in MEETING_MAP
    ]
    return {"roles": roles, "meetings": meetings}


# ---------------------------------------------------------------------------
# 4) Educational Co-Parenting Assessment (info sharing / consistency / decisions)
# ---------------------------------------------------------------------------

INFO_ITEMS = [
    "Report cards", "Progress reports", "Attendance notices", "Teacher emails",
    "Testing results", "Disciplinary notices", "ARD, IEP, or 504 documents",
    "School calendars", "Special-event notices", "Homework & project information",
]

CONSISTENCY_ITEMS = [
    "Homework routines", "Bedtimes on school nights", "Technology use",
    "Attendance", "Transportation", "School supplies", "Tutoring",
    "Study expectations", "Consequences & encouragement", "Participation in school events",
]

DECISION_ABILITIES = [
    "Discuss concerns without dismissing one another",
    "Review information before making decisions",
    "Communicate directly with the school",
    "Consider the child's perspective",
    "Consult appropriate professionals",
    "Reach decisions within necessary school deadlines",
]


def _coparenting_assessment(responses: Dict[str, Any],
                            rating_by_id: Dict[str, str]) -> Dict[str, Any]:
    sharing_rating = rating_by_id.get("sharing", "Not enough info")
    consist_rating = rating_by_id.get("homework", "Not enough info")
    decision_rating = rating_by_id.get("decisions", "Not enough info")

    # Which info items are likely being shared vs likely gapping — use the
    # top-level "Do both parents receive the same information?" and
    # "both_receive_updates" signals as a broad heuristic.
    if sharing_rating == "Strong":
        info_shared, info_missing = INFO_ITEMS, []
    elif sharing_rating == "Developing":
        info_shared, info_missing = INFO_ITEMS[:6], INFO_ITEMS[6:]
    else:
        info_shared, info_missing = INFO_ITEMS[:3], INFO_ITEMS[3:]

    return {
        "information_sharing": {
            "rating": sharing_rating,
            "shared_items": info_shared,
            "gap_items": info_missing,
        },
        "consistency_between_homes": {
            "rating": consist_rating,
            "items": CONSISTENCY_ITEMS,
        },
        "decision_making": {
            "rating": decision_rating,
            "items": DECISION_ABILITIES,
        },
    }


# ---------------------------------------------------------------------------
# 5) Alignment / Attention areas
# ---------------------------------------------------------------------------

ALIGNMENT_STATEMENTS = [
    "Both parents want the child to succeed.",
    "Both recognise the importance of regular school attendance.",
    "Both support communication with teachers.",
    "Both want the child to receive appropriate services.",
    "Both value the child's emotional well-being at school.",
]

ATTENTION_STATEMENTS_BASE = [
    "Parents may have different views about whether a problem exists.",
    "School records may not be consistently shared.",
    "Homework expectations may differ between homes.",
    "The parents may disagree about evaluations, tutoring, or special-education services.",
    "Conflict may interfere with timely educational decisions.",
    "The child may be carrying information between parents.",
]


def _alignment_and_attention(areas: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    strong_ids = {a["id"] for a in areas if a["rating"] == "Strong"}
    weak_ids = {a["id"] for a in areas if a["rating"] == "Needs Attention"}
    alignment = list(ALIGNMENT_STATEMENTS)
    attention = []
    if "understanding" in weak_ids:
        attention.append(ATTENTION_STATEMENTS_BASE[0])
    if "sharing" in weak_ids:
        attention.append(ATTENTION_STATEMENTS_BASE[1])
    if "homework" in weak_ids:
        attention.append(ATTENTION_STATEMENTS_BASE[2])
    if "services" in weak_ids:
        attention.append(ATTENTION_STATEMENTS_BASE[3])
    if "decisions" in weak_ids:
        attention.append(ATTENTION_STATEMENTS_BASE[4])
    if not attention and (not strong_ids or len(strong_ids) < 6):
        attention.append(ATTENTION_STATEMENTS_BASE[5])
    return {"alignment": alignment, "attention": attention}


# ---------------------------------------------------------------------------
# 6) Support Level (1/2/3)
# ---------------------------------------------------------------------------

def _support_level(areas: List[Dict[str, Any]]) -> Dict[str, Any]:
    weak = sum(1 for a in areas if a["rating"] == "Needs Attention")
    develop = sum(1 for a in areas if a["rating"] == "Developing")
    if weak == 0 and develop <= 2:
        return {
            "level": 1, "name": "Maintain and Monitor",
            "description": "You generally understand the child's needs and can coordinate educational support.",
            "next_steps": [
                "Continue sharing school information promptly.",
                "Review progress at regular intervals — after each report card.",
                "Maintain consistent routines across both homes.",
            ],
        }
    if weak <= 2:
        return {
            "level": 2, "name": "Develop a Shared Educational Plan",
            "description": "Some differences or communication gaps are affecting coordination.",
            "next_steps": [
                "Create one shared school-information process — same portal, same contacts.",
                "Schedule a parent-teacher meeting and prepare shared questions.",
                "Develop consistent homework expectations for both homes.",
                "Identify a short list of questions for school professionals.",
            ],
        }
    return {
        "level": 3, "name": "Professional Guidance Recommended",
        "description": "Significant disagreement or unresolved educational concerns may affect the child.",
        "next_steps": [
            "Request an educational evaluation when appropriate.",
            "Meet with the teacher, counsellor, or special-education team.",
            "Consider child-focused mediation for stuck decisions.",
            "Establish a written educational decision-making process.",
            "Consult an attorney or qualified professional when legal guidance is needed.",
        ],
    }


# ---------------------------------------------------------------------------
# 7) Practical Options, Action Plan, Foundation Statement, Questions, Closing
# ---------------------------------------------------------------------------

PRACTICAL_OPTIONS_BASE = [
    "Give both parents direct access to the school portal.",
    "Use a shared educational calendar.",
    "Upload report cards, evaluations, and IEP documents to a shared folder.",
    "Create a standard method for notifying the other parent of school updates.",
    "Attend school meetings together, separately, or remotely — whichever is safest and most productive.",
    "Submit questions to the school in writing before every meeting.",
    "Obtain written recommendations from professionals, not just verbal advice.",
    "Use a neutral educational professional when parents disagree.",
    "Decide who schedules appointments and who follows up.",
    "Establish in writing how tutoring and other services will be funded.",
    "Keep the child out of adult disagreements — never carry messages through the child.",
]

SAFETY_OPTIONS = [
    "Communicate with the school through separate parent contacts.",
    "Attend school meetings virtually or on different days.",
    "Route sensitive communications through a mediator or parenting coordinator.",
    "Use structured written updates (email or parenting app) with dated records.",
]


def _practical_options(has_safety_flag: bool) -> List[str]:
    if has_safety_flag:
        return PRACTICAL_OPTIONS_BASE + SAFETY_OPTIONS
    return PRACTICAL_OPTIONS_BASE


def _action_plan(support_level: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {"priority": "1", "action": "Obtain school records",
         "detail": "Request current reports, progress notes, and evaluations",
         "responsible": "Parent", "target": ""},
        {"priority": "2", "action": "Contact teacher",
         "detail": "Schedule a parent-teacher conference",
         "responsible": "Parent", "target": ""},
        {"priority": "3", "action": "Share information",
         "detail": "Send records through the agreed platform",
         "responsible": "Parent", "target": ""},
        {"priority": "4", "action": "Identify support",
         "detail": "Discuss tutoring or an evaluation",
         "responsible": "Parents / professional", "target": ""},
        {"priority": "5", "action": "Review progress",
         "detail": "Revisit the plan after the next grading period",
         "responsible": "Parents", "target": ""},
    ]


def _foundation_statement(profile: Dict[str, Any]) -> str:
    strengths = profile.get("strengths") or []
    strengths_text = strengths[0].lower() if strengths else "engagement with subjects they enjoy"
    concerns = profile.get("concerns") or []
    concerns_text = ", ".join(concerns).lower() if concerns else "consistent school communication"
    benefit = profile.get("benefit_from") or "a shared school-information process"
    return (
        f"My child's educational strengths include {strengths_text}. "
        f"My primary concerns are {concerns_text}. "
        f"I believe my child needs {benefit} to feel supported and make educational progress. "
        f"I am willing to share school information, consider professional recommendations, "
        f"and participate in a structured decision-making process focused on my child's needs."
    )


def _questions_for_school(profile: Dict[str, Any]) -> List[str]:
    q = [
        "What educational strengths do we both see in our child?",
        "What information do we still need from the school?",
        "Are we observing the same challenges in both homes?",
        "What support should we try first?",
        "When will we review whether the plan is helping?",
    ]
    if profile.get("primary_concern"):
        q[3] = f"For '{profile['primary_concern']}', what support should we try first?"
    return q


FINAL_SUMMARY = (
    "Your child benefits when educational concerns are addressed early, "
    "information is shared accurately, and decisions are based on the child's "
    "needs rather than parental conflict. You do not have to agree on every "
    "issue to create a dependable process for supporting your child."
)


DISCLAIMER = (
    "This report reflects the responses of one parent. It is not a diagnosis, "
    "a professional educational evaluation, or a determination of either "
    "parent's legal rights. Consult qualified professionals — teachers, "
    "counsellors, an educational diagnostician, a mediator, or an attorney — "
    "for decisions that affect your child."
)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def build_journey_report(*, parent_name: Optional[str], child_name: Optional[str],
                         responses: Dict[str, Any]) -> Dict[str, Any]:
    areas = _rating_areas(responses)
    rating_by_id = {a["id"]: a["rating"] for a in areas}
    profile = _child_profile(responses)
    involvement = _school_involvement(responses)
    coparenting = _coparenting_assessment(responses, rating_by_id)
    aa = _alignment_and_attention(areas)
    level = _support_level(areas)
    options = _practical_options(has_safety_flag=False)
    action_plan = _action_plan(level)
    foundation = _foundation_statement(profile)
    questions = _questions_for_school(profile)

    # Personalised overall paragraph
    weak_names = [a["area"] for a in areas if a["rating"] == "Needs Attention"]
    strong_names = [a["area"] for a in areas if a["rating"] == "Strong"]
    parts = ["Your responses indicate that you are actively involved in your child's education."]
    if weak_names:
        parts.append(
            "There appear to be gaps around " + ", ".join(a.lower() for a in weak_names) + "."
        )
    if strong_names:
        parts.append("Areas of strength include " + ", ".join(a.lower() for a in strong_names) + ".")
    parts.append(
        "Improving documentation and creating a consistent process for "
        "educational decisions may help both parents support the child more effectively."
    )
    overall_narrative = " ".join(parts)

    return {
        "cover": {
            "parent_name": parent_name or "-",
            "child_name": child_name or "-",
            "grade_level": responses.get("s1_grade_level") or "-",
            "school_setting": responses.get("s1_school_setting") or "-",
            "school_state": responses.get("s1_school_state") or "-",
        },
        "overview": {
            "purpose_bullets": [
                "Identify your child's educational strengths and needs.",
                "Consider whether additional support may be appropriate.",
                "Evaluate how educational information is shared between parents.",
                "Prepare for parent-teacher conferences, counselling meetings, ARD meetings, or IEP meetings.",
                "Develop practical options centred on your child's success.",
            ],
        },
        "support_summary": {
            "ratings": areas,
            "overall_narrative": overall_narrative,
        },
        "child_profile": profile,
        "school_involvement": involvement,
        "co_parenting_assessment": coparenting,
        "alignment_areas": aa["alignment"],
        "attention_areas": aa["attention"],
        "support_level": level,
        "practical_options": options,
        "action_plan": action_plan,
        "foundation_statement": foundation,
        "questions_for_school_or_parent": questions,
        "final_summary": FINAL_SUMMARY,
        "disclaimer": DISCLAIMER,
    }
