"""Deterministic Individual Parent Report builder for SNC (Phase A).

Follows the user's 17-section report blueprint verbatim, in the order
specified, using the required pattern:
    response → finding → child impact → suggested option → action step

Every section is populated from the raw answers and the scoring output.
Section 12 (Family Violence and Communication Safety) is captured but is
NEVER included in any shared / comparison view when `include_safety=False`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from snc_questions import SECTIONS, SCORED_CATEGORY_IDS, find_section, find_item
from snc_scoring import (
    classify_avg, CLS_ESTABLISHED, CLS_SUPPORTED, CLS_OPPORTUNITY,
    CLS_INCONSISTENT, CLS_PRIORITY, compute_scores,
)


DISCLAIMER = (
    "This Individual Parent Report is an educational reflection tool from "
    "SA CoParents. It does not diagnose the child, determine parental fitness, "
    "establish that either parent's account is correct, or replace professional "
    "or legal advice. Scores reflect the reporting parent's answers and are not "
    "findings of fact."
)


# ---------------------------------------------------------------------------
# Per-category guidance library
# For each scored category × classification, we keep:
#   finding      — what the parent's answers suggest
#   child_impact — how it may affect the child
#   suggested    — one concrete option worth considering
#   action_step  — a first practical step
# ---------------------------------------------------------------------------
_GUIDANCE: Dict[str, Dict[str, Dict[str, str]]] = {
    "s2": {
        CLS_ESTABLISHED: {
            "finding": "Parent reports a strong, integrated understanding of the child's needs.",
            "child_impact": "The child benefits from a parent who sees the whole picture.",
            "suggested": "Keep the child's professional summary up to date so new information is integrated quickly.",
            "action_step": "Ask the treating provider for a plain-language written summary you can share.",
        },
        CLS_SUPPORTED: {
            "finding": "Parent reports a mostly strong understanding with some unresolved questions.",
            "child_impact": "Small knowledge gaps can lead to different responses in each home.",
            "suggested": "Identify the one or two areas you feel least certain about and get them clarified in writing.",
            "action_step": "Book a 30-minute consult with the diagnosing or treating professional.",
        },
        CLS_OPPORTUNITY: {
            "finding": "Parent's understanding has notable gaps that may be affecting daily decisions.",
            "child_impact": "Inconsistent responses at home can amplify the child's dysregulation.",
            "suggested": "Focus on a single written child summary that both parents (and the school) can rely on.",
            "action_step": "Request a written child summary from the diagnosing/treating professional.",
        },
        CLS_INCONSISTENT: {
            "finding": "Understanding of the child's needs is uneven across situations.",
            "child_impact": "The child may receive very different responses depending on the setting.",
            "suggested": "Slow down and gather the professional information before making major decisions.",
            "action_step": "Prepare three specific questions and take them to the child's primary provider.",
        },
        CLS_PRIORITY: {
            "finding": "Parent reports significant uncertainty about the child's needs.",
            "child_impact": "Decisions taken without clarity can delay important services.",
            "suggested": "Prioritize a comprehensive review with the diagnosing or evaluating professional.",
            "action_step": "Contact the pediatrician (or evaluating specialist) this week to schedule a review.",
        },
    },
    "s3": {
        CLS_ESTABLISHED: {"finding": "Medical/mental-health coordination is solid.", "child_impact": "The child gets consistent care across homes.", "suggested": "Maintain a shared appointment + medication log.", "action_step": "Save the log in a place both parents can access."},
        CLS_SUPPORTED: {"finding": "Coordination generally works with occasional gaps.", "child_impact": "Occasional gaps can cause missed doses or duplicated appointments.", "suggested": "Confirm both parents are on file with every treating provider.", "action_step": "Send a short 'both parents on file, please' email to each provider."},
        CLS_OPPORTUNITY: {"finding": "Medical information does not always reach both homes in time.", "child_impact": "Delayed information can affect medication timing and appointment attendance.", "suggested": "Establish a written provider contact + appointment sharing procedure.", "action_step": "Draft a shared provider contact list this week."},
        CLS_INCONSISTENT: {"finding": "Care coordination is a recurring problem area.", "child_impact": "Continuity of care may be at risk.", "suggested": "Ask providers to send appointment summaries to both parents.", "action_step": "Set up a shared cloud folder for medical records."},
        CLS_PRIORITY: {"finding": "Coordination gaps may be delaying treatment.", "child_impact": "The child may be missing recommended care.", "suggested": "Bring a mediator or Parenting Facilitator into medical decision-making.", "action_step": "Schedule a joint call with the primary treating provider."},
    },
    "s4": {
        CLS_ESTABLISHED: {"finding": "Educational coordination is strong.", "child_impact": "Learning support flows smoothly across homes.", "suggested": "Keep both parents on the school's official contact list.", "action_step": "Verify contact list at the next parent-teacher meeting."},
        CLS_SUPPORTED: {"finding": "School coordination mostly works with occasional gaps.", "child_impact": "Missed information can affect homework and support.", "suggested": "Ask the school to send communications to both parents.", "action_step": "Email the school office requesting duplicate communications."},
        CLS_OPPORTUNITY: {"finding": "Classroom coordination is inconsistent.", "child_impact": "Academic support in one home may not reach the other.", "suggested": "Request a joint parent-teacher meeting.", "action_step": "Contact the teacher to schedule a joint meeting."},
        CLS_INCONSISTENT: {"finding": "Educational information does not reliably reach both homes.", "child_impact": "The child may fall behind on accommodations.", "suggested": "Ask the school counsellor to help even out communication.", "action_step": "Reach out to the school counsellor this week."},
        CLS_PRIORITY: {"finding": "Educational coordination is a significant gap.", "child_impact": "Academic outcomes may be affected.", "suggested": "Ask for a case-manager introduction if an IEP/504 is active.", "action_step": "Contact the IEP/504 case manager this week."},
    },
    "s5": {
        CLS_ESTABLISHED: {"finding": "Transitions are calm and predictable.", "child_impact": "The child adjusts easily between homes.", "suggested": "Keep exchange location and timing consistent.", "action_step": "Document current exchange protocol in one page."},
        CLS_SUPPORTED: {"finding": "Exchanges usually go smoothly with occasional friction.", "child_impact": "Occasional friction can raise the child's stress.", "suggested": "Standardise what travels between homes.", "action_step": "Create a laminated checklist for the child's bag."},
        CLS_OPPORTUNITY: {"finding": "Transitions are a recurring source of stress.", "child_impact": "The child may show dysregulation before or after exchanges.", "suggested": "Move exchanges to a neutral or school-based location.", "action_step": "Propose a neutral exchange location to the other parent."},
        CLS_INCONSISTENT: {"finding": "Exchanges are conflict-prone.", "child_impact": "The child witnesses recurring adult tension.", "suggested": "Consider curbside or school-based exchanges.", "action_step": "Draft the new exchange plan and send it in writing."},
        CLS_PRIORITY: {"finding": "Transition problems are affecting the child's wellbeing.", "child_impact": "Ongoing stress may show up in mood, sleep, or behaviour.", "suggested": "A Parenting Facilitator can help reduce direct contact during exchanges.", "action_step": "Ask your mediator/attorney about a Parenting Facilitator."},
    },
    "s6": {
        CLS_ESTABLISHED: {"finding": "Daily routines are consistent across homes.", "child_impact": "Predictability supports regulation.", "suggested": "Keep anchoring routines (bedtime, meals).", "action_step": "Document what's working so it's easy to preserve."},
        CLS_SUPPORTED: {"finding": "Most routines are consistent with some drift.", "child_impact": "Small drifts add up for a sensitive child.", "suggested": "Pick one anchor routine and hold it identical for 30 days.", "action_step": "Choose bedtime as the anchor and confirm times."},
        CLS_OPPORTUNITY: {"finding": "Daily-care consistency is uneven.", "child_impact": "Transitions and behaviour may be affected.", "suggested": "Post a visible daily rhythm in both homes.", "action_step": "Print a rhythm sheet by Friday."},
        CLS_INCONSISTENT: {"finding": "Routines differ substantially between homes.", "child_impact": "Regulation may be harder for the child.", "suggested": "Ask the child's therapist for a home-carryover plan.", "action_step": "Book a 30-minute consult with the therapist."},
        CLS_PRIORITY: {"finding": "Lack of predictable routines is likely adding stress.", "child_impact": "The child's regulation may be significantly affected.", "suggested": "Start with a single anchor routine and hold it two weeks.", "action_step": "Pick the highest-impact routine and lock the schedule."},
    },
    "s7": {
        CLS_ESTABLISHED: {"finding": "Communication is timely, accurate, child-focused.", "child_impact": "The child benefits from aligned adults.", "suggested": "Keep documenting agreements after each conversation.", "action_step": "Note this month's agreements in your shared thread."},
        CLS_SUPPORTED: {"finding": "Communication is largely reliable with occasional gaps.", "child_impact": "Occasional gaps still create surprises.", "suggested": "Add a weekly 10-minute child-focused check-in.", "action_step": "Propose a fixed day/time to the other parent."},
        CLS_OPPORTUNITY: {"finding": "Timeliness and tone of updates are inconsistent.", "child_impact": "Important information sometimes reaches the other home late.", "suggested": "Introduce a shared parenting app.", "action_step": "Pick one app and invite the other parent."},
        CLS_INCONSISTENT: {"finding": "Communication frequently escalates.", "child_impact": "The child may sense the tension.", "suggested": "Move non-emergency communication to written channels.", "action_step": "Move to text/email for one week and evaluate."},
        CLS_PRIORITY: {"finding": "Communication is a recurring blocker.", "child_impact": "Coordination for the child may be failing.", "suggested": "Consider working with a Parenting Facilitator.", "action_step": "Ask your attorney/mediator for a referral."},
    },
    "s8": {
        CLS_ESTABLISHED: {"finding": "School events are handled child-first.", "child_impact": "The child can enjoy events without stress.", "suggested": "Keep the child out of adult negotiation about attendance.", "action_step": "Confirm the joint plan for the next event."},
        CLS_SUPPORTED: {"finding": "Events mostly go smoothly.", "child_impact": "Occasional friction can spill over onto the child.", "suggested": "Keep a shared events calendar.", "action_step": "Set up (or update) a shared calendar this week."},
        CLS_OPPORTUNITY: {"finding": "Events are a recurring source of tension.", "child_impact": "The child may feel caught in the middle.", "suggested": "Share a written calendar; agree on separate attendance where useful.", "action_step": "Draft the attendance plan for the next term."},
        CLS_INCONSISTENT: {"finding": "Event participation is producing conflict.", "child_impact": "The child may avoid participation to avoid conflict.", "suggested": "Move all event announcements to the shared calendar with reminders.", "action_step": "Post the next 60 days of events."},
        CLS_PRIORITY: {"finding": "Events are frequently a flashpoint.", "child_impact": "The child may associate events with adult conflict.", "suggested": "Agree on separate attendance for now.", "action_step": "Send the proposal in writing this week."},
    },
    "s9": {
        CLS_ESTABLISHED: {"finding": "Extracurricular coordination is strong.", "child_impact": "The child enjoys activities with adult support.", "suggested": "Keep a shared cost + transport record.", "action_step": "Store the record where both parents can see it."},
        CLS_SUPPORTED: {"finding": "Activities generally run smoothly with a few gaps.", "child_impact": "Small gaps (uniform, ride) can leave the child unsupported.", "suggested": "Standardise transport + uniform ownership.", "action_step": "Write the who-does-what plan and share it."},
        CLS_OPPORTUNITY: {"finding": "Coordination is uneven.", "child_impact": "The child may miss activities or arrive unprepared.", "suggested": "Agree on a written cost + transport arrangement.", "action_step": "Draft a one-pager and share it."},
        CLS_INCONSISTENT: {"finding": "Activities are a recurring point of friction.", "child_impact": "The child may sense financial or scheduling tension.", "suggested": "Bring a mediator or Parenting Facilitator into activity decisions.", "action_step": "Ask for support in the next mediation session."},
        CLS_PRIORITY: {"finding": "Activities are causing recurring conflict.", "child_impact": "The child may pull back from activities to avoid stress.", "suggested": "Pause new activities until the shared process is settled.", "action_step": "Send a written proposal to pause + reset."},
    },
    "s10": {
        CLS_ESTABLISHED: {"finding": "Decision-making is calm and structured.", "child_impact": "The child's needs are addressed promptly.", "suggested": "Keep exchanging relevant records before major decisions.", "action_step": "Document your current decision workflow."},
        CLS_SUPPORTED: {"finding": "Most decisions get made, though the process is ad-hoc.", "child_impact": "Occasional stalls delay the child's care.", "suggested": "Adopt a written decision ladder (records → professional input → mediation).", "action_step": "Draft the ladder and propose it to the other parent."},
        CLS_OPPORTUNITY: {"finding": "Decision-making sometimes stalls.", "child_impact": "Care catches up slowly.", "suggested": "Set a deadline for each open decision.", "action_step": "List the currently-open decisions and their deadlines."},
        CLS_INCONSISTENT: {"finding": "Decisions frequently stall.", "child_impact": "The child's care may fall behind.", "suggested": "Follow the parenting-plan procedure strictly.", "action_step": "Review the parenting plan sections on decision-making."},
        CLS_PRIORITY: {"finding": "Decision-making is a recurring blocker.", "child_impact": "Recommended care may be delayed.", "suggested": "A Parenting Facilitator can help with implementation disputes.", "action_step": "Ask your attorney/mediator for a referral."},
    },
    "s12": {
        CLS_ESTABLISHED: {"finding": "Parent capacity and support are strong.", "child_impact": "The child benefits from a well-supported parent.", "suggested": "Protect the practices that keep you resourced.", "action_step": "Schedule your own weekly self-care block."},
        CLS_SUPPORTED: {"finding": "Capacity is generally sufficient with some barriers.", "child_impact": "Barriers can affect follow-through on the plan.", "suggested": "Identify the single biggest barrier and address it first.", "action_step": "Ask one trusted person to help with that barrier."},
        CLS_OPPORTUNITY: {"finding": "Capacity is uneven; barriers appear regularly.", "child_impact": "Follow-through on the child's plan may slip.", "suggested": "Bring one professional or community resource in.", "action_step": "Contact one support resource this week."},
        CLS_INCONSISTENT: {"finding": "Capacity is stretched thin.", "child_impact": "The child may notice inconsistent follow-through.", "suggested": "Consider a parent coach or family therapist.", "action_step": "Book an initial consult."},
        CLS_PRIORITY: {"finding": "Capacity is severely constrained right now.", "child_impact": "The child's plan may not be executable without support.", "suggested": "Look at short-term help (community, extended family, professional).", "action_step": "Reach out to two potential support resources this week."},
    },
}


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def _val(answers: Dict[str, Any], qid: str, default: Any = "") -> Any:
    v = answers.get(qid)
    if v is None:
        return default
    return v


def _get_open_summary(answers: Dict[str, Any], *qids: str) -> str:
    parts = []
    for qid in qids:
        v = _val(answers, qid, "").strip() if isinstance(_val(answers, qid, ""), str) else ""
        if v:
            parts.append(v)
    return "  ".join(parts).strip()


def _category_row(cat: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
    """Build the response→finding→impact→suggested→action row for one category."""
    guidance = _GUIDANCE.get(cat["id"], {}).get(cat["classification"] or "", {})
    return {
        "id":             cat["id"],
        "number":         cat["number"],
        "name":           cat["name"],
        "score":          cat["avg"],
        "classification": cat["classification"],
        "answered":       cat["answered"],
        "total":          cat["total"],
        "finding":        guidance.get("finding", ""),
        "child_impact":   guidance.get("child_impact", ""),
        "suggested":      guidance.get("suggested", ""),
        "action_step":    guidance.get("action_step", ""),
    }


def _questions_for_other_parent(answers: Dict[str, Any], scores: Dict[str, Any]) -> List[str]:
    """Auto-derive Section 16 neutral questions.

    Rules:
      - Standing questions (verbatim from the report spec) always appear first.
      - Any Likert item answered 1 or 2 → surface a neutral question.
      - Any Section 6 consistency answer of 'Sometimes inconsistent' (3) or
        'Frequently inconsistent' (2) → surface a routine-alignment question.
    """
    out: List[str] = []
    seen = set()

    def add(q: str):
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)

    # Standing questions (verbatim from the spec) — always included.
    for q in [
        "What medication schedule has the provider recommended?",
        "Which routines are essential in both homes?",
        "How will each parent receive school notices?",
        "What items must accompany the child during exchanges?",
        "Who will schedule and attend appointments?",
        "How will appointment summaries be shared?",
        "What should happen when the parents disagree about treatment?",
        "Which professional is best qualified to answer the disputed question?",
    ]:
        add(q)

    # Auto-derived from weak answers.
    for section in SECTIONS:
        if not section.get("scored"):
            continue
        for it in section["items"]:
            if not it.get("scored"):
                continue
            raw = answers.get(it["id"])
            if raw is None:
                continue
            if it["type"] == "likert":
                try:
                    v = int(raw) if raw != "na" else None
                except (TypeError, ValueError):
                    v = None
                if v in (1, 2):
                    add(f"How could we align on: '{it['prompt']}'")
            elif it["type"] == "consistency":
                try:
                    v = int(raw) if raw not in ("unknown", "na") else None
                except (TypeError, ValueError):
                    v = None
                if v in (2, 3):
                    add(f"Which parts of '{it['prompt']}' should look the same in both homes?")

    return out[:16]


def _action_plan(scored_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Populate Section 15 Action Plan from the lowest-scoring 2–4 categories."""
    rated = [c for c in scored_rows if c["classification"] is not None]
    rated.sort(key=lambda c: c["score"] or 0)
    plan: List[Dict[str, str]] = []
    for i, row in enumerate(rated[:4], start=1):
        plan.append({
            "priority":         str(i),
            "recommended_action": row["suggested"] or row["finding"] or f"Focus on {row['name']}.",
            "responsible":      "Reporting parent, with input from other parent as appropriate",
            "professional":     _professional_for(row["id"]),
            "target_date":      "Within 30 days",
        })
    return plan


def _professional_for(section_id: str) -> str:
    return {
        "s2":  "Diagnosing / treating professional",
        "s3":  "Pediatrician or treating specialist",
        "s4":  "Teacher, school counsellor, or IEP/504 case manager",
        "s5":  "Family therapist or Parenting Facilitator",
        "s6":  "Occupational therapist or family therapist",
        "s7":  "Parenting Facilitator or mediator",
        "s8":  "School counsellor",
        "s9":  "Activity coordinator or coach",
        "s10": "Mediator, Parenting Facilitator, or family-law attorney",
        "s12": "Family therapist or parent coach",
    }.get(section_id, "")


def _classify_safety(safety: Dict[str, Any]) -> str:
    lvl = safety.get("level")
    if lvl == "unanswered":
        return "Not yet answered."
    if lvl == "clear":
        return "No safety concerns disclosed."
    if lvl == "declined":
        return "Parent preferred not to answer."
    if lvl == "concerns":
        return "Communication-safety concerns identified. Additional Family Violence–IPV Assessment recommended."
    return ""


def build_individual_report(
    *,
    parent_name: Optional[str],
    child_name: Optional[str] = None,
    child_age_grade: Optional[str] = None,
    assessment_date: Optional[str] = None,
    answers: Optional[Dict[str, Any]] = None,
    scores: Optional[Dict[str, Any]] = None,
    include_safety: bool = True,
    assessment_version: str = "snc-2026-1",
) -> Dict[str, Any]:
    """Build the Individual Parent Report (matches the 17-section blueprint).

    When `include_safety=False`, Report Section 12 is redacted.
    """
    answers = answers or {}
    scores = scores or compute_scores(answers)
    cats = scores.get("categories") or []
    rated_rows = [_category_row(c, answers) for c in cats]

    # ------- Report Section 1: Report at a Glance ------------------------
    at_glance = {
        "child_strengths":       _split_bullets(_val(answers, "s1_strengths")),
        "child_needs":           list(_val(answers, "s1_needs") or []) or _split_bullets(_val(answers, "s1_needs_narrative")),
        "parent_priorities":     _split_bullets(_val(answers, "s13_goals")),
        "established_strengths": [r["name"] for r in rated_rows if r["classification"] == CLS_ESTABLISHED],
        "coordination_areas":   [r["name"] for r in rated_rows if r["classification"] == CLS_OPPORTUNITY],
        "priority_concerns":    [r["name"] for r in rated_rows if r["classification"] == CLS_PRIORITY] or ["No priority concerns identified"],
        "professional_questions": _split_bullets(_val(answers, "s13_info_needed")),
    }

    # ------- Section 2: Category Summary table --------------------------
    summary_table = [
        {"id": r["id"], "category": r["name"], "score": r["score"],
         "classification": r["classification"] or "Not enough data",
         "primary_finding": r["finding"]}
        for r in rated_rows
    ]
    # Safety row is always shown but never scored.
    safety_row = {
        "id": "s11",
        "category": "Safety considerations",
        "score": "Not scored",
        "classification": "Separate review",
        "primary_finding": _classify_safety(scores["safety"]),
    }
    summary_table.append(safety_row)

    # ------- Section 3: Child Profile -----------------------------------
    child_profile = {
        "age_grade":         _val(answers, "s1_age"),
        "strengths":         _val(answers, "s1_strengths"),
        "interests":         _val(answers, "s1_joy"),
        "diagnosis_status":  _val(answers, "s1_diagnosis_status"),
        "identified_needs":  list(_val(answers, "s1_needs") or []),
        "narrative":         _val(answers, "s1_needs_narrative"),
    }
    child_profile["summary"] = (
        f"According to this parent, the child demonstrates strengths in "
        f"{_first_sentence(child_profile['strengths']) or '—'}. "
        f"The parent identifies the child's primary support needs as "
        f"{', '.join(child_profile['identified_needs']) or '—'}. "
        f"The parent reports that {child_profile['diagnosis_status'] or 'evaluation status is not specified'}."
    )

    # ------- Sections 4-17 assembled together ---------------------------
    def row_for(sid: str) -> Optional[Dict[str, Any]]:
        for r in rated_rows:
            if r["id"] == sid:
                return r
        return None

    section_understanding = _section_block("s2", row_for("s2"))
    section_medical = _section_block("s3", row_for("s3"), extras={
        "providers":         list(_val(answers, "s3_providers") or []),
        "coordination_open": _val(answers, "s3_open_coord"),
        "missed_delayed":    _val(answers, "s3_open_missed"),
        "improve":           _val(answers, "s3_open_improve"),
    })
    section_school = _section_block("s4", row_for("s4"), extras={
        "school_name": _val(answers, "s4_school_name"),
        "supports":    list(_val(answers, "s4_supports") or []),
        "primary_concern": _val(answers, "s4_open_problem"),
        "most_important": _val(answers, "s4_open_most_important"),
        "changes":     _val(answers, "s4_open_changes"),
    })
    section_transitions = _section_block("s5", row_for("s5"), extras={
        "difficult": _val(answers, "s5_open_difficult"),
        "items":     _val(answers, "s5_open_items"),
        "checklist_wanted": _val(answers, "s5_open_checklist"),
    })
    section_routines = _section_block("s6", row_for("s6"), extras={
        "essential":    _val(answers, "s6_open_essential"),
        "flexibility":  _val(answers, "s6_open_flexibility"),
        "negative":     _val(answers, "s6_open_negative"),
        "routine_grid": _routine_grid(answers),
    })
    section_comm = _section_block("s7", row_for("s7"), extras={
        "preferred_methods": list(_val(answers, "s7_preferred") or []),
    })
    section_events = _section_block("s8", row_for("s8"), extras={
        "context_list": list(_val(answers, "s8_events_context") or []),
    })
    section_extracurricular = _section_block("s9", row_for("s9"), extras={
        "activities": _val(answers, "s9_activities"),
        "benefit":    _val(answers, "s9_benefit"),
    })
    section_decisions = _section_block("s10", row_for("s10"), extras={
        "supports": list(_val(answers, "s10_supports") or []),
    })

    # ------- Report Section 12: Safety (redacted when include_safety=False) --
    if include_safety:
        section_safety = {
            "screen_result":      _classify_safety(scores["safety"]),
            "selected_flags":     scores["safety"].get("selected_flags", []),
            "selected_safeguards": scores["safety"].get("selected_safeguards", []),
            "recommend_full_family_violence_assessment": scores["safety"].get("recommend_full_assessment", False),
            "note": ("Sensitive safety answers are never included in a report "
                     "shared with the other parent. This section is only visible "
                     "in your own report."),
        }
    else:
        section_safety = {"redacted": True,
                          "note": "Safety content is intentionally omitted from any shared / comparison view."}

    section_capacity = _section_block("s12", row_for("s12"), extras={
        "support_requested": _val(answers, "s12_open_support"),
        "manage_well":       _val(answers, "s12_open_manage"),
        "need_help":         _val(answers, "s12_open_help"),
    })

    section_goals = {
        "goals":       _split_bullets(_val(answers, "s13_goals")),
        "concerns":    _split_bullets(_val(answers, "s13_concerns")),
        "from_this_parent":  _val(answers, "s13_need_you"),
        "from_other_parent": _val(answers, "s13_need_other"),
        "from_both_parents": _val(answers, "s13_need_both"),
        "first_issue":       _val(answers, "s13_first"),
        "info_needed":       _val(answers, "s13_info_needed"),
        "thirty_day_agreement": _val(answers, "s13_thirty_day"),
    }

    action_plan = _action_plan(rated_rows)
    thirty_day_steps = [row["action_step"] for row in rated_rows
                        if row.get("action_step") and row["classification"] in (CLS_PRIORITY, CLS_INCONSISTENT, CLS_OPPORTUNITY)][:5]

    questions_for_other = _questions_for_other_parent(answers, scores)

    closing_summary = _closing_summary(child_profile, rated_rows)

    return {
        "cover": {
            "parent_name":       parent_name,
            "child_name":        child_name,
            "child_age_grade":   child_age_grade or child_profile["age_grade"],
            "assessment_date":   assessment_date,
            "report_type":       "Individual Parent Report",
            "assessment_version": assessment_version,
        },
        "purpose": (
            "This report summarizes one parent's understanding of the child's "
            "strengths, needs, services, routines, and co-parenting challenges. "
            "It is intended to help the parent prepare for discussions with the "
            "child's other parent, educators, healthcare providers, therapists, "
            "attorneys, or mediator. This report does not diagnose the child, "
            "determine parental fitness, establish that either parent's account "
            "is correct, or replace professional or legal advice."
        ),
        "at_a_glance":              at_glance,               # Report §1
        "category_summary":         summary_table,           # Report §2
        "child_profile":            child_profile,           # Report §3
        "understanding_acceptance": section_understanding,   # Report §4
        "medical_mental":           section_medical,         # Report §5
        "school":                   section_school,          # Report §6
        "transitions":              section_transitions,     # Report §7
        "daily_routines":           section_routines,        # Report §8
        "communication":            section_comm,            # Report §9
        "events_and_extracurricular": {                      # Report §10
            "school_events":       section_events,
            "extracurricular":     section_extracurricular,
        },
        "decision_making":          section_decisions,       # Report §11
        "safety":                   section_safety,          # Report §12
        "parent_capacity":          section_capacity,        # Report §13
        "goals_concerns":           section_goals,           # Report §14
        "action_plan":              action_plan,             # Report §15
        "thirty_day_steps":         thirty_day_steps,        # Report §15b
        "questions_for_other_parent": questions_for_other,   # Report §16
        "closing":                  closing_summary,         # Report §17
        "disclaimer":               DISCLAIMER,
        "include_safety":           include_safety,
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _split_bullets(text: Any) -> List[str]:
    """Turn a free-text field into up to 3 short bullets."""
    if not isinstance(text, str):
        return []
    # Split on newlines, semicolons, or numbered prefixes.
    import re
    parts = [p.strip(" -•\t") for p in re.split(r"[\n;]|(?<=\.) ", text) if p.strip()]
    return [p for p in parts if p][:3]


def _first_sentence(text: Any) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    import re
    m = re.split(r"(?<=\.) ", text.strip(), maxsplit=1)
    return m[0].rstrip(".")


def _section_block(section_id: str, row: Optional[Dict[str, Any]], extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Standard 5-part block for every scored report section."""
    if row is None:
        block = {
            "score": None, "classification": None,
            "finding": "", "child_impact": "", "suggested": "", "action_step": "",
        }
    else:
        block = {
            "score": row["score"], "classification": row["classification"],
            "finding": row["finding"], "child_impact": row["child_impact"],
            "suggested": row["suggested"], "action_step": row["action_step"],
        }
    if extras:
        block["extras"] = extras
    return block


def _routine_grid(answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build the Section 8 (Report) routine grid from Section 6 answers."""
    labels = [
        ("s6_medication",  "Medication"),
        ("s6_sleep",       "Sleep"),
        ("s6_meals",       "Meals and nutrition"),
        ("s6_homework",    "Homework"),
        ("s6_screen_time", "Screen time"),
        ("s6_therapy",     "Therapy exercises"),
        ("s6_sensory",     "Sensory supports"),
        ("s6_regulation",  "Emotional regulation"),
    ]
    rows = []
    for qid, label in labels:
        v = answers.get(qid)
        if v is None:
            reported = "Unanswered"
        elif v == "unknown":
            reported = "Unknown"
        elif v == "na":
            reported = "Not applicable"
        else:
            reported = {5: "Consistent", 4: "Mostly consistent",
                        3: "Sometimes inconsistent", 2: "Frequently inconsistent"}.get(v, str(v))
        rows.append({"routine": label, "reported_consistency": reported})
    return rows


def _closing_summary(child_profile: Dict[str, Any], rated_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    strengths = child_profile.get("strengths") or "identified strengths"
    needs = ", ".join(child_profile.get("identified_needs") or []) or "identified needs"
    established = [r["name"] for r in rated_rows if r["classification"] == CLS_ESTABLISHED]
    coordination = [r["name"] for r in rated_rows if r["classification"] in (CLS_OPPORTUNITY, CLS_INCONSISTENT, CLS_PRIORITY)]
    priority = [r["name"] for r in rated_rows if r["classification"] == CLS_PRIORITY]
    return {
        "summary_paragraph": (
            f"Based on this parent's responses, the child's primary strengths include "
            f"{_first_sentence(strengths) or '—'}, and the child's principal support "
            f"needs involve {needs}. "
            f"The parent reports established strengths in "
            f"{', '.join(established) or '—'} and identifies a need for greater "
            f"coordination in {', '.join(coordination) or '—'}. "
            f"The most immediate child-focused priorities are "
            f"{', '.join(priority) or '—'}."
        ),
        "one_thing_now": "",
        "one_issue_needing_cooperation": "",
        "one_question_for_professional": "",
    }
