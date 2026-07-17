"""Readiness scoring engine — rule-based, deterministic.

Turns a parent's raw preparation data into four dimension scores (0-100)
plus an overall Readiness Score. Same input → same output, always.
The AI layer then interprets these numbers into a narrative, but the numbers
themselves are always transparent, reproducible, and defensible.

Dimensions:
  * Communication   — how healthy the parent's communication self-assessment is
  * Trust           — how much co-parenting trust has been built (approach, safety)
  * Child Alignment — how child-centred the parent's stated goals and priorities are
  * Conflict        — inverse of how much unresolved conflict remains (higher = better)

Overall Readiness Score = weighted average of the four dimensions.
"""
from typing import Any, Dict, List, Optional, Tuple


# ---- Weights ---------------------------------------------------------------
# Communication self-assessment carries the most weight because it drives
# almost every mediation interaction. Child alignment is a close second — this
# is a child-centred app. Trust and conflict follow.
_WEIGHTS = {
    "communication": 0.30,
    "child_alignment": 0.30,
    "trust": 0.20,
    "conflict": 0.20,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_communication(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 based on the Communication Style self-assessment.

    The Communication Style module scores the parent 1-5 across ~5 sub-facets
    (tone, listening, escalation, boundaries, repair). Higher = healthier.
    We convert the average to a 0-100 scale.
    """
    reasons: List[str] = []
    comm = prep.get("comm_style") or {}
    scores = comm.get("scores") or {}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    if not numeric:
        # No self-assessment yet — neutral placeholder, flagged.
        reasons.append("Communication self-assessment not completed")
        return 50.0, reasons

    avg = sum(numeric) / len(numeric)  # 1-5 scale
    score = _clamp((avg - 1) / 4 * 100)  # 1→0, 5→100

    if avg < 2.5:
        reasons.append("Communication self-ratings are low — room to grow")
    elif avg < 3.5:
        reasons.append("Communication self-ratings are mixed")
    else:
        reasons.append("Communication self-ratings are strong")
    return score, reasons


def _score_child_alignment(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 based on how completely the parent has articulated child-centred
    goals and priorities."""
    reasons: List[str] = []
    goals = prep.get("child_goals") or {}
    priorities = prep.get("priority") or []

    goal_answers = 0
    for k in ("emotional_wellbeing", "stability", "relationships", "development"):
        v = goals.get(k)
        if v and str(v).strip():
            goal_answers += 1

    priorities_count = len(priorities) if isinstance(priorities, list) else 0

    # Base 40 for engaging at all, up to 60 more for completeness.
    if goal_answers == 0 and priorities_count == 0:
        reasons.append("Child-centred goals & priorities not yet defined")
        return 20.0, reasons

    goal_score = (goal_answers / 4) * 40  # up to 40
    prio_score = min(priorities_count / 5, 1.0) * 60  # up to 60
    score = _clamp(goal_score + prio_score)

    if goal_answers >= 3:
        reasons.append("Clear articulation of child-centred goals")
    if priorities_count >= 3:
        reasons.append(f"{priorities_count} priorities ranked with intention")
    if score < 60:
        reasons.append("More child-focused specifics would strengthen the report")
    return score, reasons


def _score_trust(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 — combines: (a) safety assessment flags (b) readiness sub-scores
    around cooperation and co-parenting posture."""
    reasons: List[str] = []
    readiness = prep.get("readiness") or {}
    safety = prep.get("safety_assessment") or {}

    # Safety flags REDUCE trust — this is a hard signal.
    safety_penalty = 0
    if safety.get("high_risk"):
        safety_penalty = 40
        reasons.append("Safety concerns identified — trust score reduced")
    elif safety.get("moderate_concern"):
        safety_penalty = 15
        reasons.append("Some safety concerns noted")

    # Readiness sub-scores relevant to trust: cooperation, hope, patience.
    readiness_scores = readiness.get("scores") or {}
    trust_keys = ("cooperation", "hope_for_agreement", "trust_in_process", "patience")
    trust_vals = [
        float(readiness_scores[k])
        for k in trust_keys
        if isinstance(readiness_scores.get(k), (int, float))
    ]
    if trust_vals:
        avg = sum(trust_vals) / len(trust_vals)  # 1-5
        base = _clamp((avg - 1) / 4 * 100)
    else:
        base = 55.0  # gentle neutral if not yet answered
        reasons.append("Readiness self-ratings incomplete")

    score = _clamp(base - safety_penalty)
    if score >= 75 and not reasons:
        reasons.append("Strong foundation of co-parenting trust")
    return score, reasons


def _score_conflict(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 where HIGHER = LESS unresolved conflict.

    Formula: 100 minus penalties for (a) many unresolved issues, (b) heavy
    'urgent' priorities, (c) low readiness-emotional-preparation self-rating."""
    reasons: List[str] = []
    issues = prep.get("issues") or {}
    priorities = prep.get("priority") or []
    readiness_scores = (prep.get("readiness") or {}).get("scores") or {}

    # Count how many issue categories have content.
    issue_categories_with_content = 0
    for key in ("schedule", "communication", "finances", "safety", "other"):
        v = issues.get(key)
        if v and str(v).strip():
            issue_categories_with_content += 1

    # More issue categories logged → more perceived conflict.
    issue_penalty = min(issue_categories_with_content, 5) * 8  # up to 40

    # 'Urgent' priorities weigh heavier than 'compromise' ones.
    urgent = sum(
        1
        for p in (priorities if isinstance(priorities, list) else [])
        if isinstance(p, dict) and (p.get("category") == "urgent" or p.get("weight") == "urgent")
    )
    urgent_penalty = min(urgent, 5) * 4  # up to 20

    # Emotional preparation lifts the conflict score (parent is calmer → less conflict).
    emo_prep = readiness_scores.get("emotional_preparation")
    if isinstance(emo_prep, (int, float)):
        emo_bonus = (float(emo_prep) - 3) * 5  # -10..+10
    else:
        emo_bonus = 0

    score = _clamp(100 - issue_penalty - urgent_penalty + emo_bonus)

    if issue_categories_with_content >= 4:
        reasons.append("Multiple areas of active concern")
    if urgent >= 2:
        reasons.append(f"{urgent} priorities flagged as urgent")
    if score >= 70:
        reasons.append("Conflict feels manageable in the current picture")
    return score, reasons


def compute_readiness(prep: Dict[str, Any]) -> Dict[str, Any]:
    """Public entry point. Returns dimension scores + weighted overall.

    Shape:
      {
        "overall": 72,
        "label": "Prepared for Mediation" | "Moderately Ready" | "Needs Support",
        "dimensions": {
          "communication":   {"score": 68, "reasons": [...]},
          "trust":           {"score": 74, "reasons": [...]},
          "child_alignment": {"score": 82, "reasons": [...]},
          "conflict":        {"score": 60, "reasons": [...]}
        },
        "weights": {...}
      }
    """
    dims: Dict[str, Dict[str, Any]] = {}
    for name, scorer in (
        ("communication", _score_communication),
        ("trust", _score_trust),
        ("child_alignment", _score_child_alignment),
        ("conflict", _score_conflict),
    ):
        score, reasons = scorer(prep)
        dims[name] = {"score": round(score, 1), "reasons": reasons}

    overall = sum(dims[k]["score"] * _WEIGHTS[k] for k in _WEIGHTS)
    overall_rounded = round(overall)

    if overall >= 75:
        label = "Prepared for Mediation"
    elif overall >= 55:
        label = "Moderately Ready"
    else:
        label = "Needs Support"

    return {
        "overall": overall_rounded,
        "label": label,
        "dimensions": dims,
        "weights": _WEIGHTS,
    }
