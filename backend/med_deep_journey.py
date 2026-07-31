"""Medical · Prescription & Medication Coordination Deep Dive — SA CoParents
journey report. Same shape/keys as edu_deep_journey.build_journey_report.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional


FREQ_MAP = {"Always": 5, "Usually": 4, "Sometimes": 3, "Rarely": 2, "Never": 1}
CONSIST_MAP = {"Always Consistent": 5, "Usually Consistent": 4, "Sometimes Consistent": 3,
               "Rarely Consistent": 2, "Never Consistent": 1}
AGREE_MAP = {"Always Agree": 5, "Usually Agree": 4, "Sometimes Agree": 3,
             "Rarely Agree": 2, "Never Agree": 1}
YPN_MAP = {"Yes": 5, "Partial": 3, "No": 1}


def _int(v):
    return v if isinstance(v, int) and 1 <= v <= 5 else None


def _rate(score):
    if score is None: return "Not enough info"
    if score >= 4.0: return "Strong"
    if score >= 2.5: return "Developing"
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
            for m in (FREQ_MAP, CONSIST_MAP, AGREE_MAP, YPN_MAP):
                if v in m:
                    xs.append(m[v]); break
    return xs


def _rating_areas(responses):
    areas = []
    # a. Understanding the child's medical needs
    xs = _pull(responses, "s1_list_updated", "s1_both_receive_new_rx")
    shared_info = responses.get("s1_shared_info") or []
    xs.append(5 if len(shared_info) >= 7 else 4 if len(shared_info) >= 5 else 2 if len(shared_info) <= 2 else 3)
    if responses.get("s1_written_med_list") in YPN_MAP:
        xs.append(YPN_MAP[responses["s1_written_med_list"]])
    areas.append({"id": "understanding",
        "area": "Understanding your child's medical needs",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Both parents share an accurate, current picture of every prescription." if _avg(xs) and _avg(xs) >= 4 else
                     "You are still building a shared picture of your child's prescriptions." if _avg(xs) and _avg(xs) >= 2.5 else
                     "There may be gaps in shared understanding of your child's prescriptions.",
    })
    # b. Prescription & supply reliability
    xs = _pull(responses, "s3_supply_each_home", "s3_refill_coordination",
               "s3_expired_check", "s2_pickup_delays", "s2_clear_assignment",
               "s2_confirmation")
    if responses.get("s3_backup_supply") in YPN_MAP:
        xs.append(YPN_MAP[responses["s3_backup_supply"]])
    ea = responses.get("s3_emergency_med_available")
    if ea in ("Yes in both", "Not applicable"): xs.append(5)
    elif ea == "Only one home": xs.append(2)
    elif ea == "No": xs.append(1)
    areas.append({"id": "supply",
        "area": "Prescription & supply reliability",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Prescriptions arrive on time and both homes have reliable supply." if _avg(xs) and _avg(xs) >= 4 else
                     "Supply is mostly reliable with some coordination gaps." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Pickup delays or supply gaps are already affecting the child.",
    })
    # c. Information sharing between parents
    xs = _pull(responses,
               "s5_new_prescriptions", "s5_dose_changes", "s5_missed_doses",
               "s5_side_effects", "s5_refill_needs", "s5_emergency_use",
               "s5_stopping_med", "s5_provider_visits")
    areas.append({"id": "sharing",
        "area": "Information sharing between parents",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Missed doses, side effects, and provider visits are shared promptly." if _avg(xs) and _avg(xs) >= 4 else
                     "Some updates are shared; others fall through the cracks." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Medication updates are not reliably reaching both parents.",
    })
    # d. Administration consistency
    xs = _pull(responses, "s4_same_schedule", "s4_handoff_dose")
    if responses.get("s4_missed_doses_freq") in FREQ_MAP:
        xs.append(6 - FREQ_MAP[responses["s4_missed_doses_freq"]])  # reverse-scored
    if responses.get("s4_dose_log") in YPN_MAP:
        xs.append(YPN_MAP[responses["s4_dose_log"]])
    areas.append({"id": "administration",
        "area": "Medication administration & routines",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Doses are administered consistently across both homes with clear handoffs." if _avg(xs) and _avg(xs) >= 4 else
                     "Administration is mostly consistent with some handoff gaps." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Doses are being missed or handoffs are unclear — a safety concern.",
    })
    # e. Pharmacy & professional coordination
    xs = []
    sp = responses.get("s6_same_pharmacy")
    m = {"Yes always": 5, "Usually": 4, "Sometimes": 3, "No": 1}
    if sp in m: xs.append(m[sp])
    if responses.get("s6_both_authorized") == "Yes": xs.append(5)
    elif responses.get("s6_both_authorized") == "No": xs.append(1)
    if responses.get("s6_pharmacy_has_contacts") in YPN_MAP: xs.append(YPN_MAP[responses["s6_pharmacy_has_contacts"]])
    if responses.get("s6_pharmacist_alignment") in FREQ_MAP: xs.append(FREQ_MAP[responses["s6_pharmacist_alignment"]])
    areas.append({"id": "pharmacy",
        "area": "Pharmacy & professional coordination",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "Pharmacy and prescribers are coordinated across both homes." if _avg(xs) and _avg(xs) >= 4 else
                     "Some pharmacy coordination is in place; still room to consolidate." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Fragmented pharmacies or missing authorisations could interrupt medication.",
    })
    # f. Ability to make medication decisions
    xs = []
    for tid in ("whether_to_use", "which_medication", "dosing", "side_effects",
                "brand_vs_generic", "stopping_med", "as_needed_use", "controlled_use"):
        v = responses.get(f"s10_{tid}")
        if v in AGREE_MAP: xs.append(AGREE_MAP[v])
    areas.append({"id": "decisions",
        "area": "Ability to make medication decisions",
        "rating": _rate(_avg(xs)), "score": None,
        "narrative": "You and your co-parent generally reach medication decisions together." if _avg(xs) and _avg(xs) >= 4 else
                     "Some decisions are aligned; others are difficult to resolve." if _avg(xs) and _avg(xs) >= 2.5 else
                     "Medication decisions are difficult to reach jointly, which may delay care.",
    })
    return areas


PROFILE_STRENGTHS = [
    "Willingness to keep the child's medications on schedule",
    "Openness to talking with the prescriber and pharmacist",
    "Ability to grow when both homes coordinate the same routine",
    "Commitment to keeping rescue / emergency medication accessible",
]


def _child_profile(responses):
    cats = responses.get("s1_med_categories") or []
    primary = cats[0] if cats else "General medication coordination"
    benefit = "one shared, up-to-date medication list and consistent handoffs"
    if responses.get("s8_has_controlled") == "Yes":
        benefit = "written controlled-medication safeguards and tracked handoffs"
    if responses.get("s9_school_meds") == "Yes":
        benefit = "up-to-date school medication authorisation and shared MAR"
    return {
        "strengths": PROFILE_STRENGTHS[:4],
        "concerns": cats,
        "primary_concern": primary,
        "benefit_from": benefit,
        "notes": (responses.get("s1_notes") or "").strip(),
    }


def _school_involvement(responses):
    roles = responses.get("s1_prescriber_types") or []
    meetings = [
        {"name": "Prescriber follow-up",
         "current_status": "Active" if roles else "Not yet",
         "next_step": "Confirm both parents receive the updated prescription list after each visit."},
        {"name": "Pharmacy coordination",
         "current_status": responses.get("s6_same_pharmacy") or "-",
         "next_step": "Consolidate to one primary pharmacy and add both parents to authorised pickup."},
        {"name": "School medication administration",
         "current_status": "In place" if responses.get("s9_school_meds") == "Yes" else "Not applicable",
         "next_step": "Ensure both parents are on the school medication authorisation and MAR distribution."},
        {"name": "Controlled medication agreement",
         "current_status": "In place" if responses.get("s8_provider_agreement") == "Yes" else "Not yet",
         "next_step": "Ask the prescriber for a written controlled-substance agreement if applicable."},
        {"name": "Emergency medication check",
         "current_status": responses.get("s3_emergency_med_available") or "-",
         "next_step": "Confirm rescue medication is present, unexpired, and accessible in BOTH homes."},
    ]
    return {"roles": roles, "meetings": meetings}


INFO_ITEMS = [
    "New prescriptions", "Dose or schedule changes", "Missed doses",
    "Side effects observed", "Refill needs", "Use of rescue / emergency medication",
    "Stopping a medication", "Prescriber visits",
]
CONSISTENCY_ITEMS = [
    "Same daily schedule", "Written dose log", "Handoff dose communication",
    "Backup supply", "Emergency medication access", "Expiration checks",
    "Storage location", "Adult-only administration",
]
DECISION_ABILITIES = [
    "Discuss medication concerns without dismissing one another",
    "Review prescriber recommendations before decisions",
    "Communicate directly with the prescriber and pharmacist",
    "Consider the child's tolerability and preference",
    "Consult appropriate professionals",
    "Reach decisions before the next refill is needed",
]


def _coparenting_assessment(responses, rating_by_id):
    sr = rating_by_id.get("sharing", "Not enough info")
    cr = rating_by_id.get("administration", "Not enough info")
    dr = rating_by_id.get("decisions", "Not enough info")
    if sr == "Strong": shared, missing = INFO_ITEMS, []
    elif sr == "Developing": shared, missing = INFO_ITEMS[:5], INFO_ITEMS[5:]
    else: shared, missing = INFO_ITEMS[:2], INFO_ITEMS[2:]
    return {
        "information_sharing": {"rating": sr, "shared_items": shared, "gap_items": missing},
        "consistency_between_homes": {"rating": cr, "items": CONSISTENCY_ITEMS},
        "decision_making": {"rating": dr, "items": DECISION_ABILITIES},
    }


ALIGNMENT_STATEMENTS = [
    "Both parents want the child to receive medication safely and on time.",
    "Both recognise the importance of rescue / emergency medication access.",
    "Both support communication with the prescriber and pharmacist.",
    "Both want the child to feel supported at every handoff.",
    "Both value the child's health and continuity of care.",
]
ATTENTION_STATEMENTS_BASE = [
    "Parents may have different views about whether medication is needed.",
    "Prescription updates may not be consistently shared.",
    "Administration schedules or handoff communication may differ between homes.",
    "Parents may disagree about medication choice, dose, or brand.",
    "Conflict may delay refills or medication decisions.",
    "The child may be carrying medication information between parents.",
]


def _alignment_and_attention(areas):
    weak = {a["id"] for a in areas if a["rating"] == "Needs Attention"}
    attention = []
    if "understanding" in weak: attention.append(ATTENTION_STATEMENTS_BASE[0])
    if "sharing" in weak: attention.append(ATTENTION_STATEMENTS_BASE[1])
    if "administration" in weak: attention.append(ATTENTION_STATEMENTS_BASE[2])
    if "decisions" in weak: attention.append(ATTENTION_STATEMENTS_BASE[3])
    if "supply" in weak or "pharmacy" in weak: attention.append(ATTENTION_STATEMENTS_BASE[4])
    if not attention:
        attention.append(ATTENTION_STATEMENTS_BASE[5])
    return {"alignment": list(ALIGNMENT_STATEMENTS), "attention": attention}


def _support_level(areas):
    weak = sum(1 for a in areas if a["rating"] == "Needs Attention")
    develop = sum(1 for a in areas if a["rating"] == "Developing")
    if weak == 0 and develop <= 2:
        return {"level": 1, "name": "Maintain and Monitor",
            "description": "You generally have a reliable medication routine and coordination in place.",
            "next_steps": [
                "Keep sharing prescription updates promptly.",
                "Check expiration and refill needs every month.",
                "Review the plan after every prescriber visit.",
            ]}
    if weak <= 2:
        return {"level": 2, "name": "Develop a Shared Medication Plan",
            "description": "Some differences or communication gaps could interrupt the child's medication.",
            "next_steps": [
                "Create one written medication list shared with both homes.",
                "Consolidate to one primary pharmacy.",
                "Set a handoff routine that includes the last dose given.",
                "Confirm rescue medication is present in BOTH homes.",
            ]}
    return {"level": 3, "name": "Professional Guidance Recommended",
        "description": "Significant disagreement or unresolved coordination issues may affect the child's care.",
        "next_steps": [
            "Request a joint prescriber appointment for clarity.",
            "Consider child-focused mediation for medication decisions.",
            "Get a written controlled-substance agreement if applicable.",
            "Consult an attorney or qualified professional when legal guidance is needed.",
        ]}


PRACTICAL_OPTIONS = [
    "Give both parents pharmacy authorisation and provider portal access where allowed.",
    "Use one shared medication calendar with dose times and handoff notes.",
    "Upload prescriptions, MAR, and school authorisations to a shared folder.",
    "Set a standard method for notifying the other parent of dose changes.",
    "Attend prescriber visits together, separately, or virtually — whichever is safest and most productive.",
    "Submit questions to the prescriber in writing before every visit.",
    "Confirm rescue / emergency medication is present, unexpired, and accessible in BOTH homes.",
    "Log every dose given so the receiving home sees the last administered time.",
    "Consolidate to one primary pharmacy and add both parents to pickup.",
    "Establish in writing how medication and copays are shared.",
    "Keep the child out of adult disagreements about their medication.",
]


def _action_plan():
    return [
        {"priority": "1", "action": "Consolidate medication list",
         "detail": "Create one shared list with name, dose, purpose, schedule, prescriber, pharmacy",
         "responsible": "Parent", "target": ""},
        {"priority": "2", "action": "Confirm rescue meds",
         "detail": "Ensure emergency medication is present in both homes",
         "responsible": "Parent", "target": ""},
        {"priority": "3", "action": "Share updates promptly",
         "detail": "Send dose changes, missed doses, and side effects within 24 hours",
         "responsible": "Parent", "target": ""},
        {"priority": "4", "action": "Align on handoffs",
         "detail": "Communicate last dose given and next dose due at every handoff",
         "responsible": "Parents", "target": ""},
        {"priority": "5", "action": "Review with prescriber",
         "detail": "Revisit the plan at the next medication review",
         "responsible": "Parents / prescriber", "target": ""},
    ]


def _foundation_statement(profile):
    concerns = profile.get("concerns") or []
    concerns_text = ", ".join(concerns).lower() if concerns else "reliable medication coordination"
    benefit = profile.get("benefit_from") or "a shared medication process"
    return (
        f"My child's medication needs include {concerns_text}. "
        f"I believe my child needs {benefit} to receive medication safely and on time. "
        f"I am willing to share prescription information, consider prescriber recommendations, "
        f"and participate in a structured decision-making process focused on my child's health."
    )


def _questions_for_school(profile):
    return [
        "Is our current medication list fully shared and accurate in both homes?",
        "Do we both know when a rescue or emergency medication should be used?",
        "Are dose changes and missed doses being communicated within 24 hours?",
        f"For '{profile.get('primary_concern', 'this medication')}', what support should we try first?",
        "When will we review whether the plan is helping?",
    ]


FINAL_SUMMARY = (
    "Your child benefits when medication coordination is addressed early, "
    "prescriptions are shared accurately, and decisions are based on the "
    "child's health rather than parental conflict. You do not have to agree on "
    "every issue to create a dependable process for supporting your child."
)


DISCLAIMER = (
    "This report reflects the responses of one parent. It is not a diagnosis, "
    "medical advice, prescription, or determination of either parent's legal "
    "rights. Consult qualified professionals — the prescriber, pharmacist, "
    "school nurse, mediator, or attorney — for decisions that affect your child. "
    "In a medical emergency call 911 or the poison control centre."
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
    parts = ["Your responses indicate that you are actively coordinating your child's medication."]
    if weak_names:
        parts.append("There may be gaps around " + ", ".join(a.lower() for a in weak_names) + ".")
    if strong_names:
        parts.append("Strengths include " + ", ".join(a.lower() for a in strong_names) + ".")
    parts.append("A written medication plan and a consistent handoff routine can help both parents support the child more effectively.")
    return {
        "cover": {
            "parent_name": parent_name or "-",
            "child_name": child_name or "-",
            "grade_level": "-",
            "school_setting": (responses.get("s1_prescriber_types") or ["-"])[0],
            "school_state": "-",
        },
        "overview": {
            "purpose_bullets": [
                "Confirm both parents share the same accurate medication picture.",
                "Identify supply, refill, or administration gaps early.",
                "Evaluate how medication information is shared between parents.",
                "Prepare for prescriber visits, pharmacy pickup, and school medication reviews.",
                "Develop practical options centred on your child's safety.",
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
