"""Psychological / Behavioural Deep Dive — SA CoParents journey report.

Same shape/keys as edu_deep_journey.build_journey_report so the React report
component structure and PDF renderer stay consistent across all three
optional deep dives.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional


FREQ_MAP = {"Always": 5, "Usually": 4, "Sometimes": 3, "Rarely": 2, "Never": 1}
CONSIST_MAP = {"Always Consistent": 5, "Usually Consistent": 4, "Sometimes Consistent": 3,
               "Rarely Consistent": 2, "Never Consistent": 1}
AGREE_MAP = {"Always Agree": 5, "Usually Agree": 4, "Sometimes Agree": 3,
             "Rarely Agree": 2, "Never Agree": 1}
CONFIDENCE_MAP = {"Very Confident": 5, "Confident": 4, "Neutral": 3,
                  "Somewhat Uncertain": 2, "Not Confident": 1}
YES_PARTIAL_NO = {"Yes": 5, "Partial": 3, "No": 1}


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


def _avg(xs):
    return mean(xs) if xs else None


def _pull(responses, *keys):
    xs = []
    for k in keys:
        v = responses.get(k)
        if isinstance(v, int) and 1 <= v <= 5:
            xs.append(v)
        elif isinstance(v, str):
            for m in (FREQ_MAP, CONSIST_MAP, AGREE_MAP, CONFIDENCE_MAP, YES_PARTIAL_NO):
                if v in m:
                    xs.append(m[v]); break
    return xs


def _rating_areas(responses):
    areas = []
    # a. Understanding the child's mental-health / behavioural needs
    xs = _pull(responses, "s3_provider_understands", "s3_confidence_plan",
               "s3_trust_recommendations", "s4_understand_areas_score")
    areas.append({"id": "understanding",
        "area": "Understanding your child's mental-health & behavioural needs",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "You have a clear picture of your child's diagnoses, providers, and plan." if _avg(xs) and _avg(xs) >= 4 else
                     "You are still building a shared picture of your child's mental-health needs." if _avg(xs) and _avg(xs) >= 2.5 else
                     "There may be gaps in shared understanding of your child's mental-health needs.",
    })
    # b. Provider engagement
    xs = _pull(responses, "s2_both_know_provider", "s2_attend_appointments",
               "s2_both_receive_updates", "s2_follow_recs_consistent")
    areas.append({"id": "provider",
        "area": "Provider engagement",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Both parents actively engage with the child's providers." if _avg(xs) and _avg(xs) >= 4 else
                     "You are involved with providers but engagement is inconsistent." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Provider engagement is limited or uneven between parents.",
    })
    # c. Information sharing between parents
    xs = _pull(responses, "s2_communicate_recs", "s9_appointments", "s9_medication_changes",
               "s9_behaviour_changes", "s9_treatment_recs", "s9_therapy_progress")
    areas.append({"id": "sharing",
        "area": "Information sharing between parents",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Appointments, medication changes, and provider updates are shared reliably." if _avg(xs) and _avg(xs) >= 4 else
                     "Some information is shared, but gaps could affect the child's care." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Provider information is not reliably reaching both parents.",
    })
    # d. Consistency between homes (routines / emotional support)
    xs = _pull(responses, "s11_routines", "s11_emotional_support",
               "s11_positive_reinforcement", "s11_calm_environment",
               "s11_safe_expression", "s11_consistent_expectations",
               "s11_healthy_coping", "s11_stress_reduction")
    areas.append({"id": "consistency",
        "area": "Consistency between homes",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Emotional support, routines, and expectations are consistent across both homes." if _avg(xs) and _avg(xs) >= 4 else
                     "Home environments are mostly aligned, with some differences." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Home routines, emotional support, and expectations differ meaningfully between homes.",
    })
    # e. Treatment coordination (medication, therapy homework)
    xs = _pull(responses, "s4_administered_consistent", "s4_communicate_changes",
               "s4_refills_coordinated", "s4_side_effects_discussed",
               "s6_homework_completed", "s6_strategies_reinforced")
    areas.append({"id": "treatment",
        "area": "Treatment coordination",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Medication and therapy strategies are coordinated across both homes." if _avg(xs) and _avg(xs) >= 4 else
                     "Treatment is mostly on track with some gaps in coordination." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Treatment coordination is inconsistent — this could affect the child's progress.",
    })
    # f. Ability to make mental-health decisions
    xs = []
    for tid in ("start_therapy", "change_therapist", "medication",
                "medication_adjustments", "psych_testing", "neuropsych_eval",
                "behaviour_plans", "school_mh_services",
                "alternative_treatments", "family_therapy"):
        v = responses.get(f"s10_{tid}")
        if v in AGREE_MAP:
            xs.append(AGREE_MAP[v])
    areas.append({"id": "decisions",
        "area": "Ability to make mental-health decisions",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "You and your co-parent generally reach mental-health decisions together." if _avg(xs) and _avg(xs) >= 4 else
                     "Some decisions get made together; others stall or default to one parent." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Mental-health decisions are difficult to reach jointly, which may delay support.",
    })
    return areas


PROFILE_STRENGTHS = [
    "Positive engagement with clinicians the child trusts",
    "Willingness to attend appointments and follow through",
    "Openness to trying new coping strategies",
    "Ability to grow when both homes reinforce the same plan",
]


def _child_profile(responses):
    diagnoses = responses.get("s1_diagnoses") or []
    primary = diagnoses[0] if diagnoses else "General emotional / behavioural coordination"
    benefit = "consistent emotional support and coordinated communication between homes"
    if responses.get("s4_has_medication") == "Yes":
        benefit = "a written medication plan shared between homes and providers"
    if any("anxiety" in d.lower() for d in diagnoses):
        benefit = "predictable morning routines and shared calming strategies across homes"
    if any("depression" in d.lower() for d in diagnoses):
        benefit = "coordinated safety planning and consistent connection with a therapist"
    return {
        "strengths": PROFILE_STRENGTHS[:4],
        "concerns": diagnoses,
        "primary_concern": primary,
        "benefit_from": benefit,
        "notes": "",
    }


def _school_involvement(responses):
    providers = responses.get("s2_provider_types") or []
    meetings = [
        {"name": "Therapy appointment",
         "current_status": "Active" if responses.get("s6_attends_therapy") == "Yes" else "Not currently in therapy",
         "next_step": "Confirm both parents receive session summaries and next-step recommendations."},
        {"name": "Prescriber / medication review",
         "current_status": "Active" if responses.get("s4_has_medication") == "Yes" else "Not applicable",
         "next_step": "Attend the next medication review together or share written notes within 48 hours."},
        {"name": "School mental-health team",
         "current_status": "Involved" if any("school" in p.lower() or "counsel" in p.lower() for p in providers) else "Not involved",
         "next_step": "Ask about counsellor support, 504 or IEP mental-health goals if relevant."},
        {"name": "Crisis / safety plan",
         "current_status": "In place" if responses.get("s8_plan_in_writing") == "Yes" else ("Partial" if responses.get("s8_plan_in_writing") == "Partial" else "Not yet"),
         "next_step": "Get the plan in writing, share with both homes, and confirm emergency contacts."},
        {"name": "Neuropsych or psych evaluation",
         "current_status": "Discussed" if responses.get("s10_neuropsych_eval") else "Not requested",
         "next_step": "Discuss whether a written evaluation could clarify next steps."},
    ]
    return {"roles": providers, "meetings": meetings}


INFO_ITEMS = [
    "Appointment schedules", "Medication changes", "Behavioural changes",
    "School concerns", "Treatment recommendations", "Therapy progress",
    "New diagnoses", "Symptom changes",
]
CONSISTENCY_ITEMS = [
    "Routines & sleep", "Emotional support responses", "Positive reinforcement",
    "Calm environment", "Safe expression of feelings", "Consistent expectations",
    "Healthy coping tools", "Stress reduction strategies",
]
DECISION_ABILITIES = [
    "Discuss concerns without dismissing one another",
    "Review provider recommendations before making decisions",
    "Communicate directly with clinicians",
    "Consider the child's own perspective",
    "Consult appropriate professionals",
    "Reach decisions within reasonable time frames",
]


def _coparenting_assessment(responses, rating_by_id):
    sr = rating_by_id.get("sharing", "Not enough info")
    cr = rating_by_id.get("consistency", "Not enough info")
    dr = rating_by_id.get("decisions", "Not enough info")
    if sr == "Strong":
        shared, missing = INFO_ITEMS, []
    elif sr == "Developing":
        shared, missing = INFO_ITEMS[:5], INFO_ITEMS[5:]
    else:
        shared, missing = INFO_ITEMS[:2], INFO_ITEMS[2:]
    return {
        "information_sharing": {"rating": sr, "shared_items": shared, "gap_items": missing},
        "consistency_between_homes": {"rating": cr, "items": CONSISTENCY_ITEMS},
        "decision_making": {"rating": dr, "items": DECISION_ABILITIES},
    }


ALIGNMENT_STATEMENTS = [
    "Both parents want the child to feel emotionally safe and supported.",
    "Both recognise the value of professional mental-health care when needed.",
    "Both support consistent routines that help the child regulate.",
    "Both want the child to be heard without judgement.",
    "Both value the child's emotional well-being at home and school.",
]
ATTENTION_STATEMENTS_BASE = [
    "Parents may have different views about whether professional care is needed.",
    "Provider updates may not be consistently shared.",
    "Home routines and coping tools may differ between homes.",
    "Parents may disagree about medication, therapy, or evaluations.",
    "Conflict may interfere with timely mental-health decisions.",
    "The child may be carrying emotional messages between parents.",
]


def _alignment_and_attention(areas):
    weak = {a["id"] for a in areas if a["rating"] == "Needs Attention"}
    attention = []
    if "understanding" in weak: attention.append(ATTENTION_STATEMENTS_BASE[0])
    if "sharing" in weak: attention.append(ATTENTION_STATEMENTS_BASE[1])
    if "consistency" in weak: attention.append(ATTENTION_STATEMENTS_BASE[2])
    if "treatment" in weak: attention.append(ATTENTION_STATEMENTS_BASE[3])
    if "decisions" in weak: attention.append(ATTENTION_STATEMENTS_BASE[4])
    if not attention:
        attention.append(ATTENTION_STATEMENTS_BASE[5])
    return {"alignment": list(ALIGNMENT_STATEMENTS), "attention": attention}


def _support_level(areas):
    weak = sum(1 for a in areas if a["rating"] == "Needs Attention")
    develop = sum(1 for a in areas if a["rating"] == "Developing")
    if weak == 0 and develop <= 2:
        return {"level": 1, "name": "Maintain and Monitor",
            "description": "You generally understand your child's mental-health needs and can coordinate support.",
            "next_steps": [
                "Continue sharing provider updates promptly.",
                "Keep routines and coping tools consistent across homes.",
                "Review the plan after each provider visit.",
            ]}
    if weak <= 2:
        return {"level": 2, "name": "Develop a Shared Mental-Health Plan",
            "description": "Some differences or communication gaps are affecting coordination.",
            "next_steps": [
                "Create one written mental-health plan shared with both homes.",
                "Attend a therapy or medication review together at least once.",
                "Agree on emergency contacts and a safety plan.",
                "Use a shared parenting app for provider messages.",
            ]}
    return {"level": 3, "name": "Professional Guidance Recommended",
        "description": "Significant disagreement or unresolved concerns may affect the child.",
        "next_steps": [
            "Ask the clinician to hold a joint parent session.",
            "Consider child-focused mediation for stuck decisions.",
            "Get a written treatment plan and safety plan.",
            "Consult an attorney or qualified professional when legal guidance is needed.",
        ]}


PRACTICAL_OPTIONS = [
    "Give both parents provider portal access where allowed.",
    "Use a shared mental-health calendar.",
    "Upload treatment plans, evaluations, and prescriptions to a shared folder.",
    "Set a standard method for notifying the other parent of provider updates.",
    "Attend appointments together, separately, or virtually — whichever is safest and most productive.",
    "Submit questions to the clinician in writing before every visit.",
    "Obtain written recommendations, not just verbal advice.",
    "Use a neutral mental-health professional when parents disagree.",
    "Decide who schedules appointments and who follows up.",
    "Establish in writing how therapy and medication costs are shared.",
    "Keep the child out of adult disagreements about their care.",
]


def _action_plan():
    return [
        {"priority": "1", "action": "Obtain provider records",
         "detail": "Request current treatment plan, medication list, and recent notes",
         "responsible": "Parent", "target": ""},
        {"priority": "2", "action": "Contact clinician",
         "detail": "Ask the therapist / prescriber for a joint or written update",
         "responsible": "Parent", "target": ""},
        {"priority": "3", "action": "Share information",
         "detail": "Send records through the agreed platform",
         "responsible": "Parent", "target": ""},
        {"priority": "4", "action": "Align on home routines",
         "detail": "Pick 2-3 coping tools to reinforce in both homes",
         "responsible": "Parents", "target": ""},
        {"priority": "5", "action": "Review progress",
         "detail": "Revisit the plan at the next provider visit",
         "responsible": "Parents", "target": ""},
    ]


def _foundation_statement(profile):
    concerns = profile.get("concerns") or []
    concerns_text = ", ".join(concerns).lower() if concerns else "consistent emotional support"
    benefit = profile.get("benefit_from") or "coordinated mental-health care"
    return (
        f"My child's strengths include the willingness and capacity to grow when supported. "
        f"My primary concerns are {concerns_text}. "
        f"I believe my child needs {benefit} to feel emotionally safe and continue to progress. "
        f"I am willing to share provider information, consider professional recommendations, "
        f"and participate in a structured decision-making process focused on my child's needs."
    )


def _questions_for_school(profile):
    q = [
        "What emotional or behavioural strengths do we both see in our child?",
        "What information from the provider do we still need?",
        "Are we seeing the same behaviours in both homes?",
        "What support should we try first?",
        "When will we review whether the plan is helping?",
    ]
    if profile.get("primary_concern"):
        q[3] = f"For '{profile['primary_concern']}', what support should we try first?"
    return q


FINAL_SUMMARY = (
    "Your child benefits when mental-health concerns are addressed early, "
    "provider information is shared accurately, and decisions are based on the "
    "child's needs rather than parental conflict. You do not have to agree on "
    "every issue to create a dependable process for supporting your child."
)


DISCLAIMER = (
    "This report reflects the responses of one parent. It is not a diagnosis, "
    "psychological evaluation, or determination of either parent's legal rights. "
    "Consult qualified professionals — the treating clinician, school counsellor, "
    "mediator, or attorney — for decisions that affect your child. In a mental-"
    "health emergency call 911 or the 988 Suicide & Crisis Lifeline."
)


def build_journey_report(*, parent_name, child_name, responses):
    areas = _rating_areas(responses)
    rating_by_id = {a["id"]: a["rating"] for a in areas}
    profile = _child_profile(responses)
    involvement = _school_involvement(responses)
    coparenting = _coparenting_assessment(responses, rating_by_id)
    aa = _alignment_and_attention(areas)
    level = _support_level(areas)
    weak_names = [a["area"] for a in areas if a["rating"] == "Needs Attention"]
    strong_names = [a["area"] for a in areas if a["rating"] == "Strong"]
    parts = ["Your responses indicate that you are actively engaged in your child's mental-health care."]
    if weak_names:
        parts.append("Gaps appear around " + ", ".join(a.lower() for a in weak_names) + ".")
    if strong_names:
        parts.append("Strengths include " + ", ".join(a.lower() for a in strong_names) + ".")
    parts.append("Creating a written plan and a consistent communication process may help both parents support the child more effectively.")
    return {
        "cover": {
            "parent_name": parent_name or "-",
            "child_name": child_name or "-",
            "grade_level": responses.get("s1_grade_level") or "-",
            "school_setting": responses.get("s2_provider_types") and responses["s2_provider_types"][0] or "-",
            "school_state": "-",
        },
        "overview": {
            "purpose_bullets": [
                "Identify your child's mental-health & behavioural strengths and needs.",
                "Consider whether additional professional support may be appropriate.",
                "Evaluate how mental-health information is shared between parents.",
                "Prepare for provider visits, medication reviews, therapy sessions, or school meetings.",
                "Develop practical options centred on your child's well-being.",
            ],
        },
        "support_summary": {
            "ratings": areas,
            "overall_narrative": " ".join(parts),
        },
        "child_profile": profile,
        "school_involvement": involvement,
        "co_parenting_assessment": coparenting,
        "alignment_areas": aa["alignment"],
        "attention_areas": aa["attention"],
        "support_level": level,
        "practical_options": PRACTICAL_OPTIONS,
        "action_plan": _action_plan(),
        "foundation_statement": _foundation_statement(profile),
        "questions_for_school_or_parent": _questions_for_school(profile),
        "final_summary": FINAL_SUMMARY,
        "disclaimer": DISCLAIMER,
    }
