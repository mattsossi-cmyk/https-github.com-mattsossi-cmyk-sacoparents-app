"""Deterministic scoring for the Special Needs Assessment (v2).

Emits **7 coordination scores** — never a single global "co-parent quality"
number. The seven dimensions come from the user's product spec:

    understanding    — do both parents understand the child?
    info_sharing     — is medical/school/therapy info exchanged in time?
    follow_through   — do agreed actions actually happen?
    consistency      — routines/strategies aligned where the child needs it
    professional     — collaboration with providers & record access
    decision_making  — timely decisions when a decision is required
    transitions      — handovers stable, med/equipment transfer intact

Same input → same output. AI narratives are layered on top of these numbers
in the report, but the numbers themselves never depend on the LLM.
"""

from typing import Any, Dict, List, Optional

from special_needs_questions import (
    COORDINATION_SCALE,
    DOMAIN_ITEMS,
    DOMAINS,
)


DIMENSION_LABELS = {
    "understanding":  "Understanding the child",
    "info_sharing":   "Information sharing",
    "follow_through": "Follow-through",
    "consistency":    "Consistency between homes",
    "professional":   "Professional collaboration",
    "decision_making": "Decision-making",
    "transitions":    "Transition stability",
}

# Map answer value → numeric weight (or None for na / dont_know / disagree).
_WEIGHT = {row["value"]: row["weight"] for row in COORDINATION_SCALE}


def _score_answer(item: dict, value: Optional[str]) -> Optional[int]:
    """Convert a single answer to its 0–100 numeric weight.

    Returns None when the answer carries no numeric signal (not applicable,
    don't know, parents disagree, or unanswered). Reverse-scored items
    (e.g. "has a decision been delayed?") are flipped so that "almost
    always" — a bad signal — maps to 0 instead of 100.
    """
    if value not in _WEIGHT:
        return None
    weight = _WEIGHT[value]
    if weight is None:
        return None
    if item.get("reverse"):
        weight = 100 - weight
    return weight


def _bucket_label(score: int) -> str:
    if score >= 80:
        return "Strong coordination"
    if score >= 60:
        return "Working coordination"
    if score >= 40:
        return "Inconsistent coordination"
    if score >= 20:
        return "Coordination breaking down"
    return "Coordination has broken down"


def _tag_counts(items: List[dict], answers: Dict[str, Any]) -> Dict[str, int]:
    """How many items in this bucket returned na / dont_know / disagree.

    These are surfaced in the report as flags to the parent — a coach
    intervention rather than a punished score.
    """
    counts = {"na": 0, "dont_know": 0, "disagree": 0, "unanswered": 0}
    for it in items:
        v = answers.get(it["id"])
        if v is None or v == "":
            counts["unanswered"] += 1
        elif v in counts:
            counts[v] += 1
    return counts


def compute_scores(answers: Dict[str, Any]) -> dict:
    """Compute all 7 coordination scores from a saved answer map.

    A dimension score is the mean of its contributing scored items,
    rounded to the nearest integer. If a dimension has no numeric
    answers at all (all na / dont_know / disagree / blank), it is
    returned as None with a `no_signal: True` flag so the frontend
    can render "not enough answers yet" instead of a misleading 0.
    """
    by_dim: Dict[str, List[int]] = {k: [] for k in DIMENSION_LABELS}
    dim_items: Dict[str, List[dict]] = {k: [] for k in DIMENSION_LABELS}

    for item in DOMAIN_ITEMS:
        dim = item.get("dim")
        if dim not in by_dim:
            continue
        dim_items[dim].append(item)
        scored = _score_answer(item, answers.get(item["id"]))
        if scored is not None:
            by_dim[dim].append(scored)

    dimensions: Dict[str, dict] = {}
    for dim, values in by_dim.items():
        items = dim_items[dim]
        tag_counts = _tag_counts(items, answers)
        if values:
            score = int(round(sum(values) / len(values)))
            dimensions[dim] = {
                "score": score,
                "label": DIMENSION_LABELS[dim],
                "bucket": _bucket_label(score),
                "items_scored": len(values),
                "items_total": len(items),
                "tags": tag_counts,
                "no_signal": False,
            }
        else:
            dimensions[dim] = {
                "score": None,
                "label": DIMENSION_LABELS[dim],
                "bucket": "Not enough answers yet",
                "items_scored": 0,
                "items_total": len(items),
                "tags": tag_counts,
                "no_signal": True,
            }

    # Per-domain roll-up (the 8 topical domains). Numbers here average
    # every scored item in the domain — helpful for the report's
    # "coordination gaps" table.
    domain_rollups: Dict[str, dict] = {}
    for d in DOMAINS:
        d_items = [it for it in DOMAIN_ITEMS if it.get("domain") == d["id"]]
        d_values: List[int] = []
        for it in d_items:
            s = _score_answer(it, answers.get(it["id"]))
            if s is not None:
                d_values.append(s)
        if d_values:
            avg = int(round(sum(d_values) / len(d_values)))
            domain_rollups[d["id"]] = {
                "score": avg,
                "label": d["label"],
                "bucket": _bucket_label(avg),
                "items_scored": len(d_values),
                "items_total": len(d_items),
                "no_signal": False,
            }
        else:
            domain_rollups[d["id"]] = {
                "score": None,
                "label": d["label"],
                "bucket": "Not enough answers yet",
                "items_scored": 0,
                "items_total": len(d_items),
                "no_signal": True,
            }

    # Coordination structure recommendation — Cooperative / Structured /
    # Parallel — based on the mean of the dimension scores we do have.
    real = [d["score"] for d in dimensions.values() if d["score"] is not None]
    overall = int(round(sum(real) / len(real))) if real else None
    if overall is None:
        structure = None
    elif overall >= 70:
        structure = {
            "id": "cooperative",
            "label": "Cooperative Coordination",
            "blurb": "Direct communication and shared decision-making are working. Keep formalising what you already do well.",
        }
    elif overall >= 45:
        structure = {
            "id": "structured",
            "label": "Structured Coordination",
            "blurb": "Some routes work; others break down. A written plan with clear owners and channels will lower friction.",
        }
    else:
        structure = {
            "id": "parallel",
            "label": "Parallel Coordination",
            "blurb": "Direct back-and-forth is unreliable right now. A structured, low-contact plan with a third-party channel will protect your child from the coordination gap.",
        }

    return {
        "overall_signal": overall,   # informational only — never a "quality" score
        "dimensions": dimensions,
        "domains": domain_rollups,
        "structure": structure,
    }
