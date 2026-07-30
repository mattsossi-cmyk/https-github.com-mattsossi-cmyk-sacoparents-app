"""Neutral scoring for the Special Needs Co-Parenting v2 assessment.

Two composite scores per pathway (each on a 1-5 scale):
    * understanding — how aligned both parents are on the concern
    * coordination  — how consistently the plan is executed across homes

Plus a category impact score (Step 1 "current_impact" item) that flags the
severity of the concern in the reporting parent's view.

Every finding is attributed to the reporting parent's own answers. The
scoring module never claims one parent is right and never diagnoses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from snc2_questions import (
    ASSESSMENT_VERSION, PATHWAYS, _TEMPLATE, _apply_pathway, qid, resolve_pathways,
)


UNDERSTANDING_ITEMS = [
    "recs_understand", "same_info", "attend_appts",
    "discuss_openly", "shared_language", "believe_understood",
]

COORDINATION_ITEMS = [
    "routines_consistent", "follow_recs", "share_updates",
    "carry_over_supplies", "handoffs_reliable",
]


def _bucket(avg: Optional[float]) -> str:
    """Classification band shared by both composite scores."""
    if avg is None:
        return "Not enough data"
    if avg >= 4.3:
        return "Well aligned"
    if avg >= 3.5:
        return "Generally aligned"
    if avg >= 2.5:
        return "Coordination opportunity"
    if avg >= 1.5:
        return "Significant inconsistency"
    return "Priority concern"


def _score(values: List[Any]) -> Optional[float]:
    numbers = [v for v in values if isinstance(v, int) and 1 <= v <= 5]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 2)


def _impact_band(v: Any) -> str:
    if not isinstance(v, int) or v < 1 or v > 5:
        return "Not enough data"
    return {
        5: "High reported impact",
        4: "Notable reported impact",
        3: "Moderate reported impact",
        2: "Limited reported impact",
        1: "Minimal reported impact",
    }[v]


def compute_pathway_scores(pathway: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the two composite scores for one pathway."""
    understanding_values = [answers.get(qid(step, pathway, item))
                            for step in ("step3", "step4")
                            for item in UNDERSTANDING_ITEMS]
    coordination_values = [answers.get(qid("step5", pathway, item))
                           for item in COORDINATION_ITEMS]
    impact = answers.get(qid("step1", pathway, "current_impact"))
    understanding_score = _score(understanding_values)
    coordination_score = _score(coordination_values)
    return {
        "id": pathway,
        "name": next(p["name"] for p in PATHWAYS if p["id"] == pathway),
        "understanding": {
            "score": understanding_score,
            "classification": _bucket(understanding_score),
        },
        "coordination": {
            "score": coordination_score,
            "classification": _bucket(coordination_score),
        },
        "impact": {
            "score": impact if isinstance(impact, int) else None,
            "classification": _impact_band(impact),
        },
    }


def compute_scores(selected: List[str], answers: Dict[str, Any]) -> Dict[str, Any]:
    pathways = resolve_pathways(selected)
    per_pathway = [compute_pathway_scores(p, answers) for p in pathways]
    answered = sum(1 for k in answers.keys())
    return {
        "assessment_version": ASSESSMENT_VERSION,
        "selected_pathways": pathways,
        "pathways": per_pathway,
        "answered_count": answered,
    }


def validate_answer(qkey: str, value: Any) -> bool:
    """Validate an answer value against the resolved schema for its qkey.

    Enforces:
      * Likert 1-5 or "na".
      * Single/multi answers must be drawn from the resolved option list.
      * text/textarea must be strings.

    An unknown `qkey` is rejected to catch typos and stale field references.
    """
    for step in _TEMPLATE:
        for item in step["items"]:
            for pid in ("medical", "educational", "psychological"):
                if qkey != qid(step["id"], pid, item["id"]):
                    continue
                resolved = _apply_pathway(item, pid)
                t = resolved.get("type")
                options = resolved.get("options") or []
                if t == "likert":
                    return value == "na" or (isinstance(value, int) and 1 <= value <= 5)
                if t == "single":
                    if not isinstance(value, str):
                        return False
                    if not options:
                        return True
                    return value in options
                if t == "multi":
                    if not isinstance(value, list):
                        return False
                    if not options:
                        return all(isinstance(v, str) for v in value)
                    return all(isinstance(v, str) and v in options for v in value)
                if t in ("text", "textarea"):
                    return isinstance(value, str)
    return False
