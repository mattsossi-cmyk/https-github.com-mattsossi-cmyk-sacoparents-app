"""Special Needs Assessment — Phase D: Safeguards score + disagreement pathway.

Split out from `special_needs_scoring.py` to keep the coordination-scores file
focused on the 7 numeric dimensions. This module handles:

  * Safeguards score (0–100) with per-group roll-ups.
  * `disagreement_index` (0–10) tallying disagree-responses across the
    coordination items + risky concern_response answers + critical-domain
    consistency breakdowns.
  * The pathway engine that maps those signals to one of 4 tiers of
    recommended next actions (light-touch → specialist mediator + consults).

Design principles:
  - Deterministic. Same inputs → same outputs. Never depends on an LLM.
  - The tier is a *recommendation*, never a diagnosis. Every tier tells
    the parent what to do next AND when to call a human.
  - Missing safeguards raise the tier, but the pathway is capped by the
    disagreement_index — you can have perfect safeguards and still need
    Tier 3 if concern_response = "conflict".
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Set

from special_needs_questions import (
    COORDINATION_SCALE,
    DOMAIN_ITEMS,
    CONSISTENCY_ITEMS,
    SAFEGUARDS_ITEMS,
    SAFEGUARD_SCALE,
    SAFEGUARD_GROUPS,
    DISAGREEMENT_RISKY_VALUES,
)

# ---- Safeguards scoring ---------------------------------------------------

_SAFEGUARD_WEIGHT = {row["value"]: row["weight"] for row in SAFEGUARD_SCALE}


def _safeguard_group_map() -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {g["id"]: [] for g in SAFEGUARD_GROUPS}
    for it in SAFEGUARDS_ITEMS:
        out.setdefault(it["group"], []).append(it)
    return out


def compute_safeguards(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Return per-group + overall safeguards summary.

    Score is the mean of the non-null (`in_place`=100, `partial`=55,
    `not_yet`=0) weights. `not_needed` and unanswered items are excluded
    from the denominator — the parent has said the item is not applicable
    to their child, so counting it either way would misrepresent the
    picture.
    """
    groups: Dict[str, Dict[str, Any]] = {}
    missing_items: List[Dict[str, str]] = []
    partial_items: List[Dict[str, str]] = []
    in_place_items: List[Dict[str, str]] = []
    scored_values: List[int] = []

    for g in SAFEGUARD_GROUPS:
        g_items = [it for it in SAFEGUARDS_ITEMS if it["group"] == g["id"]]
        g_scores: List[int] = []
        for it in g_items:
            v = answers.get(it["id"])
            w = _SAFEGUARD_WEIGHT.get(v)
            if w is None:
                # unanswered or not_needed
                continue
            g_scores.append(w)
            scored_values.append(w)
            if v == "not_yet":
                missing_items.append({"id": it["id"], "label": it["label"], "group": g["id"]})
            elif v == "partial":
                partial_items.append({"id": it["id"], "label": it["label"], "group": g["id"]})
            elif v == "in_place":
                in_place_items.append({"id": it["id"], "label": it["label"], "group": g["id"]})
        if g_scores:
            groups[g["id"]] = {
                "score": int(round(sum(g_scores) / len(g_scores))),
                "label": g["label"],
                "items_scored": len(g_scores),
                "items_total": len(g_items),
            }
        else:
            groups[g["id"]] = {
                "score": None,
                "label": g["label"],
                "items_scored": 0,
                "items_total": len(g_items),
            }

    overall = int(round(sum(scored_values) / len(scored_values))) if scored_values else None
    return {
        "overall_score": overall,
        "groups": groups,
        "in_place": in_place_items,
        "partial": partial_items,
        "missing": missing_items,
        "items_scored": len(scored_values),
        "items_total": len(SAFEGUARDS_ITEMS),
    }


# ---- Disagreement index --------------------------------------------------

# "disagree" is one of the valid answer values on the shared coordination
# scale. It means "parents disagree about how this actually looks in
# practice" — a strong signal that alignment work is needed even if the
# item can't be numerically scored.
_DISAGREE_VALUE = "disagree"

# Domains where consistency breakdown is especially concerning.
_CRITICAL_DIMS_FOR_CONSISTENCY = {"medical", "education"}


def compute_disagreement(
    answers: Dict[str, Any],
    dimensions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute the disagreement_index (0–10) and its component signals."""
    disagree_ids: List[str] = []
    for item in DOMAIN_ITEMS:
        if answers.get(item["id"]) == _DISAGREE_VALUE:
            disagree_ids.append(item["id"])
    # Consistency items also emit disagree signals.
    for c in CONSISTENCY_ITEMS:
        if answers.get(c["id"]) == _DISAGREE_VALUE:
            disagree_ids.append(c["id"])

    concern_response = answers.get("concern_response")
    risky = concern_response in DISAGREEMENT_RISKY_VALUES

    # Critical-domain consistency: dimensions is optional; when supplied
    # (post-scoring) we can flag domains whose score is very low.
    critical_low: List[str] = []
    if dimensions:
        for dim_id, dim in (dimensions or {}).items():
            score = dim.get("score")
            if score is not None and score < 40 and dim_id in _CRITICAL_DIMS_FOR_CONSISTENCY:
                critical_low.append(dim_id)

    # The index is a small integer summarising the risk:
    #   +1 per disagree response (capped at +6)
    #   +2 if concern_response is risky
    #   +2 if any critical-domain consistency is below 40
    idx = min(6, len(disagree_ids))
    if risky:
        idx += 2
    if critical_low:
        idx += 2
    idx = min(10, idx)

    return {
        "index": idx,
        "disagree_ids": disagree_ids,
        "risky_concern_response": risky,
        "concern_response": concern_response,
        "critical_low_domains": critical_low,
    }


# ---- Pathway engine ------------------------------------------------------

# Balanced escalation thresholds — user chose option (b) from the plan.
# Tier 3 (Parenting Coordinator recommended) triggers when:
#   index >= 5, OR
#   index >= 3 AND concern_response is risky
#
# Tier 4 (Specialist mediator + separate consults) triggers on top of Tier 3
# when we also see missing safeguards in TWO groups OR index >= 8.


def _tier_for(
    disagreement: Dict[str, Any],
    safeguards: Dict[str, Any],
) -> str:
    idx = disagreement["index"]
    risky = disagreement["risky_concern_response"]
    missing = safeguards.get("missing") or []
    groups_missing: Set[str] = {m["group"] for m in missing}

    if idx >= 8 or (idx >= 5 and len(groups_missing) >= 2):
        return "T4"
    if idx >= 5 or (idx >= 3 and risky):
        return "T3"
    if idx >= 2 or len(missing) >= 3:
        return "T2"
    return "T1"


_TIER_META = {
    "T1": {
        "id": "T1",
        "label": "Tier 1 — Add missing safeguards",
        "tone": "info",
        "summary": "Coordination is holding. The focus is on closing any gaps in the protective structures around your child.",
    },
    "T2": {
        "id": "T2",
        "label": "Tier 2 — Structured written communication",
        "tone": "warn",
        "summary": "Direct back-and-forth is starting to strain. Move key coordination onto a monitored written channel and add missing safeguards.",
    },
    "T3": {
        "id": "T3",
        "label": "Tier 3 — Parenting Coordinator recommended",
        "tone": "warn",
        "summary": "Repeated disagreement or risky response patterns are surfacing. A Parenting Coordinator or Family Facilitator can hold decisions when the two parents get stuck.",
    },
    "T4": {
        "id": "T4",
        "label": "Tier 4 — Specialist mediator + professional consults",
        "tone": "urgent",
        "summary": "Coordination gaps + disagreement patterns are affecting the child's care. Bring in a specialist mediator AND separate professional evaluations before major decisions.",
    },
}


def _actions_for(tier: str, safeguards: Dict[str, Any], disagreement: Dict[str, Any]) -> List[Dict[str, str]]:
    """Deterministic action list per tier. Each action has:
        - title (verb-first, short)
        - detail (one sentence of context)
        - when (target timeline)
    """
    missing_labels = [m["label"] for m in (safeguards.get("missing") or [])[:3]]
    partial_labels = [p["label"] for p in (safeguards.get("partial") or [])[:2]]
    critical_low = disagreement.get("critical_low_domains") or []

    common_add_safeguards = {
        "title": "Add the missing safeguards",
        "detail": (
            "Prioritise: " + ", ".join(missing_labels)
            if missing_labels
            else "You have most protective structures in place — focus on strengthening the partial ones."
        ),
        "when": "Within 30 days",
    }

    strengthen_partial = {
        "title": "Strengthen partial safeguards",
        "detail": "Turn the partials into fully-in-place structures: " + ", ".join(partial_labels)
                  if partial_labels else "Turn partially-in-place safeguards into fully-in-place structures.",
        "when": "Within 60 days",
    }

    written_channel = {
        "title": "Move coordination onto a monitored written channel",
        "detail": "Use OurFamilyWizard, TalkingParents, or a co-parenting app for schedule, medical, and school communications. Written channels reduce reactive escalation.",
        "when": "This week",
    }

    doc_disagreements = {
        "title": "Document the disagreements",
        "detail": "For each item where you and the other parent disagree, capture: what each parent thinks the child needs, and what a professional has said (if applicable). Bring this list to your next mediator or PC session.",
        "when": "This week",
    }

    call_pc = {
        "title": "Consult a Parenting Coordinator or Family Facilitator",
        "detail": "A PC / Family Facilitator is a neutral trained to hold decisions when co-parents get stuck. In Texas, search the Texas Association of Mediators or ask your family lawyer for a referral.",
        "when": "Within 14 days",
    }

    specialist_consult = {
        "title": "Get separate professional consults where you disagree",
        "detail": (
            "Book independent professional opinions on the critical areas: "
            + ", ".join(critical_low)
            if critical_low
            else "Book independent professional opinions on the areas where you and the other parent see the child differently."
        ),
        "when": "Within 30 days",
    }

    specialist_mediator = {
        "title": "Engage a specialist family mediator",
        "detail": "A mediator with special-needs training will structure decisions around the child's needs — not the parents' positions. Ask for someone who has worked with IEP/504 or high-conflict special-needs cases before.",
        "when": "Within 30 days",
    }

    save_child = {
        "title": "Protect the child from the coordination gap",
        "detail": "While coordination is being rebuilt, keep the child out of adult discussions and give them predictable routines. This is the single most protective action you can take right now.",
        "when": "Ongoing",
    }

    if tier == "T1":
        return [common_add_safeguards, strengthen_partial, save_child]
    if tier == "T2":
        return [written_channel, common_add_safeguards, doc_disagreements, save_child]
    if tier == "T3":
        return [call_pc, written_channel, doc_disagreements, common_add_safeguards, save_child]
    # T4
    return [
        specialist_mediator,
        specialist_consult,
        call_pc,
        written_channel,
        doc_disagreements,
        save_child,
    ]


def build_pathway(
    answers: Dict[str, Any],
    dimensions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The end-to-end pathway result — used by the report generator + PDF."""
    safeguards = compute_safeguards(answers)
    disagreement = compute_disagreement(answers, dimensions=dimensions)
    tier_id = _tier_for(disagreement, safeguards)
    meta = _TIER_META[tier_id]
    actions = _actions_for(tier_id, safeguards, disagreement)
    return {
        "tier": meta,
        "actions": actions,
        "safeguards": safeguards,
        "disagreement": disagreement,
    }
