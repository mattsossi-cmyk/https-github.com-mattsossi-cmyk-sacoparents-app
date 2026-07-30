"""Structured Special Needs Co-Parenting v2 report content.

Renders the individual parent report as the same 8-step workflow the user
progressed through, plus a cover, at-a-glance, and disclaimer.

Report shape (top-level keys):
    cover, purpose, at_a_glance, pathway_summaries,
    steps: [ { number, name, pathways: [ { id, name, response, finding,
                                          child_impact, suggested, action } ] } ],
    disclaimer

Every finding is attributed to the reporting parent's own answers. Neither
parent is labelled "correct" and no clinical diagnosis is offered.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from snc2_questions import (
    ASSESSMENT_VERSION, PATHWAYS, _TEMPLATE, _apply_pathway,
    qid, resolve_pathways,
)
from snc2_scoring import (
    UNDERSTANDING_ITEMS, COORDINATION_ITEMS, compute_pathway_scores,
)


DISCLAIMER = (
    "This report reflects one parent's own answers to the SA CoParents "
    "Special Needs Co-Parenting Assessment. It is an educational planning "
    "tool - not a diagnosis of the child, not a finding of fact, not a "
    "measure of parental fitness, and not legal advice."
)

PURPOSE = (
    "This individual parent report walks through the same eight-step "
    "workflow you completed - understanding the concern, identifying the "
    "child's current needs, reviewing professional recommendations, "
    "assessing each parent's understanding, evaluating coordination between "
    "homes, surfacing areas of agreement and disagreement, choosing "
    "practical co-parenting options, and building an action plan. Every "
    "finding below is attributed to your own answers. It does not describe "
    "your co-parent."
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _list(items: Any) -> List[str]:
    if not items:
        return []
    if isinstance(items, list):
        return [str(i).strip() for i in items if str(i).strip()]
    if isinstance(items, str) and items.strip():
        return [items.strip()]
    return []


def _get(answers: Dict[str, Any], step: str, pathway: str, item: str) -> Any:
    return answers.get(qid(step, pathway, item))


# ---------------------------------------------------------------------------
# Step-specific finding logic
# ---------------------------------------------------------------------------

_IMPACT_PHRASES = {
    5: "reports high daily impact",
    4: "reports notable daily impact",
    3: "reports moderate impact",
    2: "reports limited impact",
    1: "reports minimal impact",
}

_URGENCY_PHRASES = {
    "Immediate / crisis":            "the parent flagged this as an immediate concern",
    "Needs attention within weeks":  "the parent expects this to need attention within weeks",
    "Longer-term planning":          "the parent frames this as longer-term planning",
    "Ongoing / stable":              "the parent describes this as ongoing but stable",
}


def _step1(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    concern = _get(answers, "step1", pathway, "concern") or "not described"
    duration = _get(answers, "step1", pathway, "duration") or "unstated"
    impact = _get(answers, "step1", pathway, "current_impact")
    urgency = _get(answers, "step1", pathway, "urgency") or ""
    impact_phrase = _IMPACT_PHRASES.get(impact if isinstance(impact, int) else 0, "impact rating not provided")
    urgency_phrase = _URGENCY_PHRASES.get(urgency, "")
    return {
        "response": {
            "concern": concern,
            "duration": duration,
            "urgency": urgency or "Unstated",
            "impact": impact if isinstance(impact, int) else None,
        },
        "finding": (
            f"For {pathway_name.lower()}, the parent describes the concern as: "
            f"\"{concern[:200]}\". Duration: {duration.lower()}. "
            f"The parent {impact_phrase}"
            + (f"; {urgency_phrase}" if urgency_phrase else "") + "."
        ),
        "child_impact": (
            "Child impact is reported at level "
            f"{impact if isinstance(impact, int) else '-'} out of 5, which the "
            f"parent describes above."
        ),
        "suggested": (
            "Start the plan from the parent's stated concern rather than any "
            "assumption about what is most important."
        ),
        "action": (
            "Restate the concern in one sentence you and your co-parent can "
            "both agree on before moving to solutions."
        ),
    }


def _step2(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    needs = _list(_get(answers, "step2", pathway, "current_needs"))
    other = _get(answers, "step2", pathway, "other_needs") or ""
    return {
        "response": {"selected_needs": needs, "other": other},
        "finding": (
            f"The parent identified {len(needs)} current need"
            f"{'s' if len(needs) != 1 else ''} in the {pathway_name.lower()} pathway."
        ),
        "child_impact": (
            "A shorter, prioritised list of current needs helps the child "
            "receive the right kind of support in both homes."
        ),
        "suggested": (
            "Confirm this list matches what your treating professionals have "
            "identified — that is often where gaps appear between homes."
        ),
        "action": (
            "Circle the top three needs to focus on in the next 30 days; "
            "share that short list with your co-parent."
        ),
    }


_PROF_YES = {"Yes"}


def _step3(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    pros = _list(_get(answers, "step3", pathway, "professionals_seen"))
    recs = _get(answers, "step3", pathway, "recommendations_text") or ""
    written = _get(answers, "step3", pathway, "recs_written") or "Unsure"
    understand = _get(answers, "step3", pathway, "recs_understand")
    return {
        "response": {"professionals": pros, "recommendations_summary_present": bool(recs.strip()),
                     "in_writing": written, "understanding": understand},
        "finding": (
            f"The parent has engaged {len(pros)} professional"
            f"{'s' if len(pros) != 1 else ''} on the {pathway_name.lower()} concern. "
            f"Written documentation of recommendations: {written.lower()}. "
            f"Self-rated understanding of the recommendations: "
            f"{understand if isinstance(understand, int) else 'not rated'} of 5."
        ),
        "child_impact": (
            "When both parents work from the same written recommendation, the "
            "child experiences one plan, not two."
        ),
        "suggested": (
            "If the recommendation is not in writing, request a summary letter "
            "from the treating professional — it removes room for interpretation."
        ),
        "action": (
            "Save the most recent recommendation as a PDF or photo you can "
            "share with your co-parent verbatim."
        ),
    }


def _score_line(items: List[str], step: str, pathway: str, answers: Dict[str, Any]) -> Optional[float]:
    vals = [answers.get(qid(step, pathway, k)) for k in items if step in ("step3","step4","step5")]
    numbers = [v for v in vals if isinstance(v, int) and 1 <= v <= 5]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 2)


def _step4(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    scores = compute_pathway_scores(pathway, answers)
    understanding = scores["understanding"]
    return {
        "response": {
            "score": understanding["score"],
            "classification": understanding["classification"],
        },
        "finding": (
            f"On the parent's own answers about how both parents share "
            f"information and understanding of this concern, the composite "
            f"is {understanding['score'] if understanding['score'] is not None else '-'} "
            f"of 5 ({understanding['classification'].lower()})."
        ),
        "child_impact": (
            "Aligned understanding between parents reduces mixed messages "
            "to the child and to the professionals involved."
        ),
        "suggested": (
            "Schedule a short recurring check-in (email or app) where each "
            "parent confirms they have the same information."
        ),
        "action": (
            "Agree on one shared source of truth for this concern — e.g., a "
            "shared folder with the latest reports and instructions."
        ),
    }


def _step5(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    scores = compute_pathway_scores(pathway, answers)
    coord = scores["coordination"]
    return {
        "response": {
            "score": coord["score"],
            "classification": coord["classification"],
        },
        "finding": (
            f"On how consistently the plan is executed across both homes, "
            f"the composite is "
            f"{coord['score'] if coord['score'] is not None else '-'} "
            f"of 5 ({coord['classification'].lower()})."
        ),
        "child_impact": (
            "Consistent routines across homes are the single biggest predictor "
            "of a child feeling settled while adults resolve differences."
        ),
        "suggested": (
            "Focus first on the smallest routine that is easy to align in "
            "both homes (bedtime, morning routine, medication timing)."
        ),
        "action": (
            "Pick one routine to align this week; agree on the exact time, "
            "the exact steps, and how to signal when it slips."
        ),
    }


def _step6(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    agree = _get(answers, "step6", pathway, "agree_areas") or ""
    disagree = _get(answers, "step6", pathway, "disagree_areas") or ""
    gap = _get(answers, "step6", pathway, "biggest_gap") or "Unstated"
    return {
        "response": {"agree": agree, "disagree": disagree, "gap_type": gap},
        "finding": (
            "The parent named specific areas of agreement and disagreement. "
            f"The gap that best explains the disagreement: {gap.lower()}."
        ),
        "child_impact": (
            "Naming the type of gap moves the conversation from \"you're wrong\" "
            "to \"we have different information / priorities / styles\"."
        ),
        "suggested": (
            "When you next raise this with your co-parent, lead with the "
            "areas of agreement — it is the honest, low-heat starting point."
        ),
        "action": (
            "In the next conversation, state one thing you agree on before "
            "raising the disagreement."
        ),
    }


def _step7(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    picks = _list(_get(answers, "step7", pathway, "practical_selected"))
    other = _get(answers, "step7", pathway, "practical_other") or ""
    return {
        "response": {"selected_options": picks, "other_option": other},
        "finding": (
            f"The parent is open to trying {len(picks)} practical "
            f"co-parenting option{'s' if len(picks) != 1 else ''} for this concern."
        ),
        "child_impact": (
            "A short list of practical, agreed options is more useful to the "
            "child than a long list of ideas nobody has committed to."
        ),
        "suggested": (
            "Ask your co-parent to select the same options (or add their own) "
            "and see where the overlap sits before you propose any of them."
        ),
        "action": (
            "Pick the two options you would try first and note the exact "
            "start date in your shared calendar."
        ),
    }


def _step8(pathway: str, answers: Dict[str, Any], pathway_name: str) -> Dict[str, Any]:
    top = _get(answers, "step8", pathway, "top_priority") or ""
    when = _get(answers, "step8", pathway, "next_meeting") or "Undecided"
    who = _get(answers, "step8", pathway, "professional_next") or ""
    concerns = _get(answers, "step8", pathway, "concerns_about_plan") or ""
    return {
        "response": {"top_priority": top, "next_meeting": when,
                     "professional_next": who, "concerns_about_plan": concerns},
        "finding": (
            "The parent identified a single 30-day priority and a proposed "
            f"timeline ({when.lower()}) for the next co-parenting conversation."
        ),
        "child_impact": (
            "A visible, dated plan gives the child (and the professionals "
            "supporting the child) a shared target to move toward."
        ),
        "suggested": (
            "Send the plan as a short written proposal rather than asking for "
            "a live discussion — it lowers the temperature and gives both "
            "parents time to think."
        ),
        "action": (
            "Draft a two-paragraph proposal now: the 30-day priority, the "
            "practical option you will try first, and when you want to "
            "review it."
        ),
    }


_STEP_BUILDERS = {
    "step1": _step1, "step2": _step2, "step3": _step3, "step4": _step4,
    "step5": _step5, "step6": _step6, "step7": _step7, "step8": _step8,
}


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

    steps_out: List[Dict[str, Any]] = []
    for step in _TEMPLATE:
        block = {
            "number": step["number"],
            "id": step["id"],
            "name": step["name"],
            "pathways": [],
        }
        builder = _STEP_BUILDERS[step["id"]]
        for pid in pathways:
            pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
            block["pathways"].append({
                "id": pid,
                "name": pname,
                **builder(pid, answers, pname),
            })
        steps_out.append(block)

    pathway_summaries = []
    for pid in pathways:
        scores = compute_pathway_scores(pid, answers)
        pathway_summaries.append({
            "id": pid,
            "name": scores["name"],
            "understanding": scores["understanding"],
            "coordination": scores["coordination"],
            "impact": scores["impact"],
        })

    at_a_glance = _build_at_a_glance(answers, pathways, pathway_summaries)

    return {
        "generated_at": _iso_now(),
        "assessment_version": ASSESSMENT_VERSION,
        "cover": {
            "parent_name": parent_name or "-",
            "child_name": child_name or "-",
            "selected_pathways": [{"id": p, "name": next(x["name"] for x in PATHWAYS if x["id"] == p)}
                                  for p in pathways],
            "assessment_date": _iso_now()[:10],
        },
        "purpose": PURPOSE,
        "at_a_glance": at_a_glance,
        "pathway_summaries": pathway_summaries,
        "steps": steps_out,
        "disclaimer": DISCLAIMER,
    }


def _build_at_a_glance(
    answers: Dict[str, Any], pathways: List[str], summaries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    concerns = []
    top_priorities = []
    coordination_wins = []
    coordination_gaps = []
    for pid in pathways:
        pname = next(p["name"] for p in PATHWAYS if p["id"] == pid)
        c = _get(answers, "step1", pid, "concern")
        if c and str(c).strip():
            concerns.append(f"{pname}: {str(c).strip()[:160]}")
        t = _get(answers, "step8", pid, "top_priority")
        if t and str(t).strip():
            top_priorities.append(f"{pname}: {str(t).strip()[:160]}")

    for s in summaries:
        classification = (s.get("coordination") or {}).get("classification")
        if classification == "Well aligned":
            coordination_wins.append(s["name"])
        elif classification in ("Coordination opportunity", "Significant inconsistency", "Priority concern"):
            coordination_gaps.append(s["name"])

    return {
        "concerns_by_pathway": concerns,
        "top_priorities": top_priorities,
        "coordination_wins": coordination_wins,
        "coordination_gaps": coordination_gaps,
    }
