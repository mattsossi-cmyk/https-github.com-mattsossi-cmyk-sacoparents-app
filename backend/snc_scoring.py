"""Deterministic scoring for the Special Needs Co-Parenting Assessment (SNC).

Scored categories: Sections 2, 3, 4, 5, 6, 7, 8, 9, 10, 12.
Section 6 uses a mapped consistency scale (Consistent=5..Frequently=2).
Section 11 is safety-sensitive and is never averaged into any category.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from snc_questions import (
    SECTIONS, SCORED_CATEGORY_IDS, find_section, scored_items,
    total_scored_items,
)


# Report classifications — verbatim thresholds from the user spec.
CLS_ESTABLISHED = "Established strength"
CLS_SUPPORTED   = "Generally supported"
CLS_OPPORTUNITY = "Coordination opportunity"
CLS_INCONSISTENT= "Significant inconsistency"
CLS_PRIORITY    = "Priority concern"

CLASSIFICATION_TIERS: List[Tuple[float, str]] = [
    (4.25, CLS_ESTABLISHED),
    (3.50, CLS_SUPPORTED),
    (2.75, CLS_OPPORTUNITY),
    (2.00, CLS_INCONSISTENT),
    (0.00, CLS_PRIORITY),
]


def classify_avg(avg: Optional[float]) -> Optional[str]:
    if avg is None:
        return None
    for threshold, label in CLASSIFICATION_TIERS:
        if avg >= threshold:
            return label
    return CLS_PRIORITY


def _numeric_value(item: Dict[str, Any], raw: Any) -> Optional[int]:
    """Return the numeric 1..5 value for a scored answer, or None if excluded.

    Excluded values (returned as None):
      - "na" (Not applicable) on any scored item.
      - "unknown" on Section 6 consistency items.
      - Missing / unanswered items.
    """
    if raw is None:
        return None
    itype = item.get("type")
    if itype == "likert":
        if raw == "na":
            return None
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return None
        if 1 <= v <= 5:
            return v
        return None
    if itype == "consistency":
        if raw in ("na", "unknown"):
            return None
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return None
        # Consistency scale carries the numeric on 2..5 (see CONSISTENCY_SCALE).
        if 2 <= v <= 5:
            return v
        return None
    return None


def _score_category(section_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    section = find_section(section_id) or {}
    items = scored_items(section_id)
    values: List[int] = []
    na_count = 0
    for it in items:
        raw = answers.get(it["id"])
        if raw is None:
            continue
        v = _numeric_value(it, raw)
        if v is None:
            # Distinguish an explicit N/A / Unknown from an unanswered item.
            if raw in ("na", "unknown"):
                na_count += 1
            continue
        values.append(v)
    answered = len(values)
    total = len(items)
    avg = round(sum(values) / answered, 3) if answered > 0 else None
    return {
        "id": section_id,
        "number": section.get("number"),
        "name": section.get("name"),
        "avg": avg,
        "classification": classify_avg(avg),
        "answered": answered,
        "total": total,
        "na_count": na_count,
    }


def _safety_summary(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Interpret Section 11 without producing a co-parenting score.

    Result levels (used to route the parent to the next resource):
      - "clear":       explicit "None of these apply."
      - "declined":    explicit "Prefer not to answer."
      - "concerns":    one or more actionable safety flags selected.
      - "unanswered":  nothing selected yet.
    """
    raw = answers.get("s11_flags")
    selected: List[str] = []
    if isinstance(raw, list):
        selected = [str(x) for x in raw if x]
    elif isinstance(raw, str) and raw:
        selected = [raw]

    if not selected:
        level = "unanswered"
    elif "None of these apply." in selected and len(selected) == 1:
        level = "clear"
    elif "Prefer not to answer." in selected and len(selected) == 1:
        level = "declined"
    else:
        # Filter to actionable flags (drop the two housekeeping options).
        actionable = [s for s in selected
                      if s not in ("None of these apply.", "Prefer not to answer.")]
        level = "concerns" if actionable else "clear"

    safeguards = answers.get("s11_safeguards") or []
    if not isinstance(safeguards, list):
        safeguards = [safeguards] if safeguards else []

    return {
        "level": level,                       # unanswered | clear | declined | concerns
        "flagged": level == "concerns",
        "selected_flags": selected,
        "selected_safeguards": [str(x) for x in safeguards if x],
        "recommend_full_assessment": level == "concerns",
    }


def compute_scores(answers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute the full SNC scoring payload for a single parent.

    Args:
      answers: {question_id -> raw answer}. Missing keys are treated as unanswered.
    """
    answers = answers or {}
    categories = [_score_category(sid, answers) for sid in SCORED_CATEGORY_IDS]
    rated = [c for c in categories if c["classification"] is not None]

    # Overall summary hint (never a "score" — just a director for the report copy).
    if not rated:
        overall_hint = "not_enough_data"
    else:
        priority = [c for c in rated if c["classification"] == CLS_PRIORITY]
        inconsistent = [c for c in rated if c["classification"] == CLS_INCONSISTENT]
        established = [c for c in rated if c["classification"] == CLS_ESTABLISHED]
        if priority or len(inconsistent) >= 3:
            overall_hint = "priority_focus"
        elif len(established) >= len(rated) - 2:
            overall_hint = "established_overall"
        else:
            overall_hint = "coordination_focus"

    strongest = []
    weakest = []
    if rated:
        by_avg = sorted(rated, key=lambda c: c["avg"] or 0)
        low = by_avg[0]["avg"]
        high = by_avg[-1]["avg"]
        weakest = [c["id"] for c in rated if c["avg"] == low]
        strongest = [c["id"] for c in rated if c["avg"] == high]

    return {
        "categories": categories,
        "safety": _safety_summary(answers),
        "overall_hint": overall_hint,
        "strongest_category_ids": strongest,
        "weakest_category_ids": weakest,
        "answered_scored_count": sum(c["answered"] for c in categories),
        "total_scored_count": total_scored_items(),
    }


def validate_answers(answers: Dict[str, Any]) -> Tuple[bool, str]:
    """Light validation for the raw answer map.

    Accepts Likert values 1..5 or "na"; consistency values 2..5 or "unknown"/"na";
    multi-selects as list-of-string; free text as string. Unknown ids are ignored.
    """
    if not isinstance(answers, dict):
        return False, "answers must be an object"
    from snc_questions import find_item as _find
    for qid, v in answers.items():
        item = _find(qid)
        if item is None:
            continue  # accept unknown ids (kept as context)
        itype = item.get("type")
        if itype == "likert":
            if v == "na":
                continue
            if isinstance(v, int) and 1 <= v <= 5:
                continue
            return False, f"Likert value for {qid} must be 1-5 or 'na'"
        if itype == "consistency":
            if v in ("na", "unknown"):
                continue
            if isinstance(v, int) and 2 <= v <= 5:
                continue
            return False, f"Consistency value for {qid} must be 2-5, 'unknown', or 'na'"
        if itype == "multi":
            if v is None:
                continue
            if not isinstance(v, list):
                return False, f"Value for {qid} must be a list"
            if not all(isinstance(x, str) for x in v):
                return False, f"Multi-select {qid} must be a list of strings"
        # single / text / textarea are permissive
    return True, ""
