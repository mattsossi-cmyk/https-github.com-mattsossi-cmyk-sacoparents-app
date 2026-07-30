"""Special Needs Co-Parenting v2 report content — 9-section polished framework.

Sections (matches the SA CoParents Special Needs Report Framework):
  1. Report Introduction (`intro`)
  2. Your Family Situation (`family_situation`)
  3. Areas of Need (`areas_of_need`)
  4. Your Co-Parenting Strengths (`strengths`)
  5. Co-Parenting Challenges (`challenges`)          -- 4-part per challenge
  6. Child Impact Summary (`child_impact`)
  7. Detailed Findings by Category (`detailed_findings`)
  8. Parent Alignment Summary (`parent_alignment`)
  9. Recommended Co-Parenting Structure (`recommended_structure`)

Guardrails:
  * Every finding is attributed to the reporting parent's own answers.
  * The report never claims either parent is correct or wrong.
  * The Recommended Co-Parenting Structure section never suggests joint or
    cooperative communication when the parent's own signals point to safety
    concerns or repeated communication breakdown.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from snc2_questions import PATHWAYS, ASSESSMENT_VERSION, qid, resolve_pathways
from snc2_scoring import compute_pathway_scores


DISCLAIMER = (
    "This report reflects one parent's own answers to the SA CoParents "
    "Special Needs Co-Parenting Assessment. It is not a diagnosis, a custody "
    "evaluation, a determination of parental fitness, or legal advice. Where "
    "appropriate, parents should consult their child's paediatrician, "
    "therapist, school, attorney, or another qualified professional."
)

INTRO_BODY = (
    "Your Special Needs Co-Parenting Report summarises the information you "
    "provided about your child's medical, educational, developmental, "
    "behavioural, or psychological needs. It is designed to help you "
    "identify concerns, understand co-parenting challenges, and prepare "
    "practical next steps.\n\n"
    "This report reflects the perspective of one parent. It is not a "
    "diagnosis, custody evaluation, or professional recommendation."
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

STATUS_ORDER = [
    "Strength",
    "Developing",
    "Needs Attention",
    "Priority Concern",
    "Professional Guidance Recommended",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list(v: Any) -> List[str]:
    if not v:
        return []
    if isinstance(v, list):
        return [str(i).strip() for i in v if str(i).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def _get(answers: Dict[str, Any], step: str, pathway: str, item: str) -> Any:
    return answers.get(qid(step, pathway, item))


def _score_to_status(score: Optional[float]) -> str:
    if score is None:
        return "Professional Guidance Recommended"
    if score >= 4.3:
        return "Strength"
    if score >= 3.5:
        return "Developing"
    if score >= 2.5:
        return "Needs Attention"
    if score >= 1.5:
        return "Priority Concern"
    return "Priority Concern"


def _worst(a: str, b: str) -> str:
    """Return the more severe of two statuses (higher index in STATUS_ORDER)."""
    ai = STATUS_ORDER.index(a) if a in STATUS_ORDER else 0
    bi = STATUS_ORDER.index(b) if b in STATUS_ORDER else 0
    return a if ai >= bi else b


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _s1_intro() -> Dict[str, Any]:
    return {"title": "Your Special Needs Co-Parenting Report", "body": INTRO_BODY}


def _s2_family_situation(
    answers: Dict[str, Any], pathways: List[str], child_name: Optional[str],
) -> Dict[str, Any]:
    concerns = []
    professionals = set()
    decisions_needed = []
    disagreements = []
    for pid in pathways:
        pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
        concern = _get(answers, "step1", pid, "concern")
        if concern:
            concerns.append(f"{pname}: {str(concern).strip()[:220]}")
        for pro in _list(_get(answers, "step3", pid, "professionals_seen")):
            professionals.add(pro)
        top = _get(answers, "step8", pid, "top_priority")
        if top:
            decisions_needed.append(f"{pname}: {str(top).strip()[:180]}")
        d = _get(answers, "step6", pid, "disagree_areas")
        if d:
            disagreements.append(f"{pname}: {str(d).strip()[:180]}")

    agreements = []
    for pid in pathways:
        pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
        a = _get(answers, "step6", pid, "agree_areas")
        if a:
            agreements.append(f"{pname}: {str(a).strip()[:180]}")

    summary_lines = []
    if concerns:
        summary_lines.append("You reported the following concerns:")
        summary_lines.extend([f"  - {c}" for c in concerns])
    if not summary_lines:
        summary_lines.append("You have not yet described a specific concern.")

    return {
        "title": "Your Family Situation",
        "child_name": child_name or "-",
        "identified_needs_by_pathway": _needs_by_pathway(answers, pathways),
        "professionals_involved": sorted(professionals),
        "primary_concerns": concerns,
        "decisions_needed": decisions_needed,
        "agreements": agreements,
        "disagreements": disagreements,
        "summary": "\n".join(summary_lines),
    }


def _needs_by_pathway(answers: Dict[str, Any], pathways: List[str]) -> List[Dict[str, Any]]:
    out = []
    for pid in pathways:
        pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
        needs = _list(_get(answers, "step2", pid, "current_needs"))
        out.append({"id": pid, "name": pname, "needs": needs})
    return out


def _s3_areas_of_need(answers: Dict[str, Any], pathways: List[str]) -> Dict[str, Any]:
    blocks = []
    for pid in pathways:
        pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
        concern = _get(answers, "step1", pid, "concern")
        duration = _get(answers, "step1", pid, "duration")
        urgency = _get(answers, "step1", pid, "urgency")
        recs = _get(answers, "step3", pid, "recommendations_text")
        needs = _list(_get(answers, "step2", pid, "current_needs"))
        other_needs = _get(answers, "step2", pid, "other_needs")
        blocks.append({
            "id": pid,
            "name": pname,
            "concern": (concern or "").strip(),
            "duration": duration,
            "urgency": urgency,
            "current_needs": needs + ([other_needs.strip()] if other_needs and other_needs.strip() else []),
            "professional_summary": (recs or "").strip(),
        })
    return {"title": "Areas of Need", "blocks": blocks}


_STRENGTH_RULES = [
    # (test_fn, message)
    (lambda a, pid: isinstance(_get(a, "step3", pid, "recs_written"), str) and _get(a, "step3", pid, "recs_written") in ("Yes", "Partly"),
     "You have professional recommendations in writing, which makes them easier to share consistently."),
    (lambda a, pid: isinstance(_get(a, "step4", pid, "attend_appts"), int) and _get(a, "step4", pid, "attend_appts") >= 4,
     "Both parents attend key appointments, meetings, or evaluations."),
    (lambda a, pid: isinstance(_get(a, "step4", pid, "discuss_openly"), int) and _get(a, "step4", pid, "discuss_openly") >= 4,
     "You and your co-parent can discuss this concern openly and calmly."),
    (lambda a, pid: len(_list(_get(a, "step3", pid, "professionals_seen"))) >= 2
                    and "No one yet" not in _list(_get(a, "step3", pid, "professionals_seen")),
     "Multiple qualified professionals are already involved."),
    (lambda a, pid: isinstance(_get(a, "step5", pid, "follow_recs"), int) and _get(a, "step5", pid, "follow_recs") >= 4,
     "Professional recommendations are followed in both homes."),
    (lambda a, pid: isinstance(_get(a, "step5", pid, "routines_consistent"), int) and _get(a, "step5", pid, "routines_consistent") >= 4,
     "Daily routines that affect this concern are consistent across both homes."),
]


def _s4_strengths(answers: Dict[str, Any], pathways: List[str]) -> Dict[str, Any]:
    items: List[str] = []
    seen = set()
    for pid in pathways:
        for fn, msg in _STRENGTH_RULES:
            try:
                if fn(answers, pid) and msg not in seen:
                    items.append(msg); seen.add(msg)
            except Exception:  # noqa: BLE001
                continue
    if not items:
        items.append(
            "You have taken the time to complete this assessment, which is "
            "itself an act of care and a starting point for a shared plan."
        )
    return {"title": "Your Co-Parenting Strengths", "items": items}


# ---------------------------------------------------------------------------
# Challenges (Section 5) — four-part cards
# ---------------------------------------------------------------------------

_CHALLENGE_CATALOG = [
    # (step, item, threshold, level, title, why_it_matters, options)
    ("step4", "same_info", 3, "understanding",
     "Both parents receiving the same information",
     "When each parent has different notes, dates, or instructions, decisions are made from incomplete pictures and the child ends up carrying the gap.",
     ["Give both parents access to the patient portal or school communication system.",
      "Share appointment or meeting summaries within 24 hours.",
      "Maintain one current medication or accommodations list.",
      "Ask the treating professional to send written summaries to both parents."]),
    ("step4", "attend_appts", 3, "understanding",
     "Attending appointments and meetings",
     "First-hand attendance reduces mistranslation and helps both parents hear the same clinical or educational language.",
     ["Alternate lead attendance for routine visits.",
      "Attend key decisions (evaluations, IEP meetings, medication reviews) together where possible.",
      "Use a phone or video option when one parent can't be present.",
      "Debrief in writing within a day of any missed appointment."]),
    ("step4", "discuss_openly", 3, "understanding",
     "Open, calm discussion of this concern",
     "When conversations are tense, decisions get delayed and children absorb the tension. A structured channel reduces the emotional cost.",
     ["Use email or a co-parenting app so each message has room to think.",
      "Try BIFF-style messages — brief, informative, friendly, firm.",
      "Introduce a written agenda for regular check-ins.",
      "Consider a parenting facilitator or mediator for the recurring topics."]),
    ("step5", "routines_consistent", 3, "coordination",
     "Consistent daily routines across homes",
     "Predictable routines are the strongest support for children with special needs; even small mismatches can escalate anxiety, meltdowns, or missed doses.",
     ["Agree on the smallest routine to align first (bedtime, morning, medication).",
      "Write down the exact steps, times, and who does what.",
      "Send a photo of the routine to both homes so the child sees it in both places.",
      "Review after two weeks and adjust together."]),
    ("step5", "follow_recs", 3, "coordination",
     "Following professional recommendations in both homes",
     "Inconsistent implementation makes it impossible to evaluate whether the plan is working and can undo the child's progress.",
     ["Save the most recent recommendation as a PDF in a shared folder.",
      "Turn the recommendation into a short checklist both homes use.",
      "Confirm changes in writing before adjusting the plan.",
      "Ask the professional to review implementation at the next visit."]),
    ("step5", "share_updates", 3, "coordination",
     "Sharing updates promptly between homes",
     "Delayed information means missed follow-up, duplicate work, and children being asked to be the messenger.",
     ["Agree on a single channel for updates (app, email, group thread).",
      "Set a 24-hour rule for appointment, medication, or school updates.",
      "Use a shared calendar for all events tied to this concern.",
      "Automate school and portal notifications to both parents."]),
    ("step5", "carry_over_supplies", 3, "coordination",
     "Supplies traveling reliably between homes",
     "Missing medication, adaptive equipment, homework, or comfort items disrupts the plan and can create emergencies.",
     ["Keep a duplicate supply in each home wherever possible.",
      "Use a labelled travel bag with a printed checklist.",
      "Include the child in the packing routine as age-appropriate.",
      "Photograph what has been packed on transition day."]),
    ("step5", "handoffs_reliable", 3, "coordination",
     "Reliable transitions and handoffs",
     "Rocky transitions are one of the most common sources of stress for children with special needs; predictability at the moment of handoff is worth a lot.",
     ["Standardise the time and place for handoffs.",
      "Use a written handoff note covering meds, mood, and any incidents.",
      "Introduce a neutral exchange location if direct interaction is difficult.",
      "Build in a short buffer so the child isn't rushed through the transition."]),
]


def _severity_from_score(score: Optional[float]) -> str:
    if score is None:
        return "Professional Guidance Recommended"
    if score >= 3.5:
        return "Developing"
    if score >= 2.5:
        return "Needs Attention"
    return "Priority Concern"


def _s5_challenges(answers: Dict[str, Any], pathways: List[str]) -> Dict[str, Any]:
    challenges: List[Dict[str, Any]] = []
    for pid in pathways:
        pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
        for step, item_id, threshold, _level, title, why, options in _CHALLENGE_CATALOG:
            val = _get(answers, step, pid, item_id)
            if not isinstance(val, int):
                continue
            if val > threshold:
                continue
            challenges.append({
                "pathway_id": pid,
                "pathway_name": pname,
                "title": title,
                "reported": _report_phrase(val, title, pname),
                "why_it_matters": why,
                "concern_level": _severity_from_score(val),
                "options": options,
            })
    return {"title": "Co-Parenting Challenges", "items": challenges}


def _report_phrase(score: int, title: str, pathway_name: str) -> str:
    """One-sentence recap in the parent's voice, without diagnosing."""
    band = {5: "strongly agreed", 4: "agreed", 3: "were unsure", 2: "disagreed", 1: "strongly disagreed"}
    return (f"On the {pathway_name.lower()} pathway you {band.get(score, 'were unsure')} "
            f"that this is currently working ({title.lower()}).")


def _s6_child_impact(answers: Dict[str, Any], pathways: List[str], summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    impacts: List[str] = []
    coord_gaps_present = any((s.get("coordination") or {}).get("score") is not None
                             and s["coordination"]["score"] < 3.5 for s in summaries)
    understanding_gaps = any((s.get("understanding") or {}).get("score") is not None
                             and s["understanding"]["score"] < 3.5 for s in summaries)
    high_impact = any((s.get("impact") or {}).get("score") in (4, 5) for s in summaries)

    if coord_gaps_present:
        impacts.append("Your child may experience different expectations, routines, or "
                       "instructions in each home, which can be confusing and disruptive.")
        impacts.append("Inconsistent implementation makes it harder to evaluate whether "
                       "current supports are actually working.")
    if understanding_gaps:
        impacts.append("When parents work from different information the child can end up "
                       "carrying the gap, sometimes acting as the messenger between homes.")
    if high_impact:
        impacts.append("The concern you described is affecting the child's daily life; "
                       "consistency between homes tends to reduce that day-to-day load.")
    for pid in pathways:
        recs_written = _get(answers, "step3", pid, "recs_written")
        if recs_written in ("No", "Unsure"):
            impacts.append("Without written recommendations, differences in interpretation "
                           "can delay evaluations, treatment, or accommodations.")
            break
    if not impacts:
        impacts.append("Your responses do not point to a specific child-impact pattern at "
                       "this time; continue monitoring as the plan evolves.")
    return {"title": "Child Impact Summary", "possible_effects": impacts}


def _s7_detailed_findings(
    answers: Dict[str, Any], pathways: List[str], summaries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    rows = []
    for s in summaries:
        pid = s["id"]
        pname = s["name"]
        u = s.get("understanding") or {}
        c = s.get("coordination") or {}
        u_status = _score_to_status(u.get("score"))
        c_status = _score_to_status(c.get("score"))
        # A missing "in writing" for the pathway flags Professional Guidance
        recs_written = _get(answers, "step3", pid, "recs_written")
        prof_flag = recs_written in (None, "No", "Unsure")
        overall = _worst(u_status, c_status)
        if prof_flag and overall != "Priority Concern":
            overall = "Professional Guidance Recommended"

        strengths = []
        concerns = []
        actions = []
        resources = []

        if u.get("score") is not None and u["score"] >= 4.3:
            strengths.append("Both parents share strong understanding of the concern.")
        elif u.get("score") is not None and u["score"] < 2.5:
            concerns.append("Understanding of the concern differs meaningfully between parents.")
            actions.append("Establish one shared written source of truth (folder or app) for this pathway.")
        if c.get("score") is not None and c["score"] >= 4.3:
            strengths.append("The plan is executed consistently across both homes.")
        elif c.get("score") is not None and c["score"] < 2.5:
            concerns.append("Coordination between homes is inconsistent.")
            actions.append("Pick one routine and align it in both homes for the next 30 days.")
        if prof_flag:
            actions.append("Request a written summary or recommendation from the treating professional.")
            resources.append("Paediatrician / therapist / IEP team")

        if not actions:
            actions.append("Keep doing what is working; check in monthly to confirm nothing is drifting.")

        rows.append({
            "id": pid,
            "name": pname,
            "status": overall,
            "explanation": (
                f"Understanding across parents on this pathway is "
                f"{u_status.lower()}; coordination between homes is {c_status.lower()}."
            ),
            "strengths": strengths,
            "concerns": concerns,
            "actions": actions,
            "resources": resources,
        })
    return {"title": "Detailed Findings by Category", "categories": rows}


_GAP_LABELS = {
    "Different information":     "disagreement_about_information",
    "Different priorities":      "disagreement_about_priorities",
    "Different parenting styles":"disagreement_about_implementation",
    "Communication breakdown":   "difficulty_sharing_information",
    "No meaningful disagreement":"agreement_about_the_childs_needs",
}


def _s8_parent_alignment(answers: Dict[str, Any], pathways: List[str]) -> Dict[str, Any]:
    tags = set()
    for pid in pathways:
        gap = _get(answers, "step6", pid, "biggest_gap")
        if gap and gap in _GAP_LABELS:
            tags.add(_GAP_LABELS[gap])
        if _get(answers, "step6", pid, "agree_areas"):
            tags.add("agreement_about_the_childs_needs")

    # Human labels for the report
    label_map = {
        "agreement_about_the_childs_needs":  "Agreement about the child's needs",
        "disagreement_about_information":    "Disagreement about information",
        "disagreement_about_priorities":     "Disagreement about priorities",
        "disagreement_about_implementation": "Disagreement about implementation between homes",
        "difficulty_sharing_information":    "Difficulty sharing information",
    }
    resolved = [label_map[t] for t in tags if t in label_map]
    return {
        "title": "Parent Alignment Summary",
        "tags": sorted(tags),
        "resolved_labels": resolved,
        "note": (
            "Parents can share the same goal while disagreeing about the method. "
            "Naming the type of gap is more useful than trying to be right."
        ),
    }


def _s9_recommended_structure(
    answers: Dict[str, Any], pathways: List[str], summaries: List[Dict[str, Any]], tags: List[str],
) -> Dict[str, Any]:
    # Structure selection based on the parent's own signals.
    understanding_scores = [s["understanding"]["score"] for s in summaries
                            if (s.get("understanding") or {}).get("score") is not None]
    coordination_scores = [s["coordination"]["score"] for s in summaries
                            if (s.get("coordination") or {}).get("score") is not None]
    u_avg = round(sum(understanding_scores) / len(understanding_scores), 2) if understanding_scores else None
    c_avg = round(sum(coordination_scores) / len(coordination_scores), 2) if coordination_scores else None

    safety_like = "difficulty_sharing_information" in tags and (u_avg is not None and u_avg < 2.5)

    if safety_like:
        rec_id = "parallel_or_supported"
        rec_name = "Parallel or Professionally Supported Structure"
        rationale = (
            "Your answers point to communication breakdown together with a low "
            "shared understanding of this concern. A parallel or professionally "
            "supported structure protects the child from being caught in that gap."
        )
    elif (u_avg is not None and u_avg >= 4.0) and (c_avg is not None and c_avg >= 4.0):
        rec_id = "cooperative"
        rec_name = "Cooperative Structure"
        rationale = (
            "Your answers show high understanding and consistent coordination "
            "between homes, which typically supports a cooperative structure."
        )
    else:
        rec_id = "structured"
        rec_name = "Structured Co-Parenting"
        rationale = (
            "Your answers point to some coordination or understanding gaps. A "
            "structured approach with written procedures, deadlines, and clearly "
            "assigned responsibilities usually reduces friction."
        )

    safeguards_by_id = {
        "cooperative": [
            "Keep a shared calendar for appointments, meetings, and events.",
            "Confirm any change to routine or medication in writing.",
            "Schedule a short monthly check-in on the plan.",
        ],
        "structured": [
            "Written communication only for logistics; keep it short and factual.",
            "Use BIFF-style messages — brief, informative, friendly, firm.",
            "Written agendas for regular check-ins so both parents come prepared.",
            "Designate a neutral point person for scheduling appointments.",
            "Mediation before any nonemergency change to the plan.",
        ],
        "parallel_or_supported": [
            "Written communication only.",
            "Communication routed through a parenting facilitator, therapist, or app.",
            "Separate attendance at appointments and school meetings when permitted.",
            "Neutral exchange location for handoffs.",
            "Consider a professional tie-breaker or legally approved decision process.",
            "Do not attempt joint problem-solving conversations until safety is confirmed.",
        ],
    }
    return {
        "title": "Recommended Co-Parenting Structure",
        "structure_id": rec_id,
        "structure_name": rec_name,
        "rationale": rationale,
        "safeguards": safeguards_by_id[rec_id],
        "safety_notice": (
            "If you experience family violence, coercive control, intimidation, "
            "or fear in this co-parenting relationship, please complete the SA "
            "CoParents Family Violence & Communication Safety Assessment. Do "
            "not accept a joint communication structure that puts you or your "
            "child at risk."
        ),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_report(
    *,
    parent_name: Optional[str],
    child_name: Optional[str],
    selected_pathways: List[str],
    answers: Dict[str, Any],
) -> Dict[str, Any]:
    pathways = resolve_pathways(selected_pathways)
    if not pathways:
        raise ValueError("No pathways selected.")
    summaries = [compute_pathway_scores(p, answers) for p in pathways]
    alignment = _s8_parent_alignment(answers, pathways)
    return {
        "generated_at": _iso_now(),
        "assessment_version": ASSESSMENT_VERSION,
        "cover": {
            "parent_name": parent_name or "-",
            "child_name": child_name or "-",
            "assessment_date": _iso_now()[:10],
            "selected_pathways": [
                {"id": p, "name": next(x["name"] for x in PATHWAYS if x["id"] == p)}
                for p in pathways
            ],
        },
        "intro":                  _s1_intro(),
        "family_situation":       _s2_family_situation(answers, pathways, child_name),
        "areas_of_need":          _s3_areas_of_need(answers, pathways),
        "strengths":              _s4_strengths(answers, pathways),
        "challenges":             _s5_challenges(answers, pathways),
        "child_impact":           _s6_child_impact(answers, pathways, summaries),
        "detailed_findings":      _s7_detailed_findings(answers, pathways, summaries),
        "parent_alignment":       alignment,
        "recommended_structure":  _s9_recommended_structure(answers, pathways, summaries, alignment["tags"]),
        "pathway_summaries":      summaries,   # kept for the dashboard status pill; no scores shown in the new PDF
        "disclaimer":             DISCLAIMER,
    }
