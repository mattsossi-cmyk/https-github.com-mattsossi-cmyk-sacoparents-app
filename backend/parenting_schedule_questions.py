"""
Parenting Schedule Reflection question bank.

Same conventions as `communication_reflection_questions.py`:
  * Neutral, non-adjudicative, first-person stems ("I aim to…").
  * 1–5 Likert responses ("Almost never" → "Almost always").
  * Three high-level scoring dimensions.
  * Reverse-scoring supported via `reverse=True` on any stem — none
    used at launch, but the plumbing is here for future items.

Guardrails
----------
* No safety questions. Anything about coercive behaviour / stalking /
  showing up unannounced lives on the Safety pathway, never here.
* No accusations about the co-parent. Every stem is about *my own*
  behaviour, planning, or perception.
"""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = 1

LIKERT_LABELS = [
    "Almost never",
    "Rarely",
    "Sometimes",
    "Often",
    "Almost always",
]

DIMENSIONS = {
    "predictability": {
        "label": "Predictability",
        "blurb": "The kids know the rhythm — the same routines and handoff patterns.",
    },
    "flexibility": {
        "label": "Flexibility",
        "blurb": "When life shifts, we plan changes ahead calmly.",
    },
    "transitions": {
        "label": "Transitions",
        "blurb": "Handoffs feel calm and prepared for the kids.",
    },
}


QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "s1",
        "dimension": "predictability",
        "stem": "The kids can name our current parenting-time pattern (which nights they're where).",
    },
    {
        "id": "s2",
        "dimension": "predictability",
        "stem": "The written schedule and what actually happens week-to-week match up.",
    },
    {
        "id": "s3",
        "dimension": "predictability",
        "stem": "Weekday morning and bedtime routines stay similar across both homes.",
    },
    {
        "id": "s4",
        "dimension": "predictability",
        "stem": "Holidays and school breaks are set on the calendar well before the day arrives.",
    },
    {
        "id": "s5",
        "dimension": "flexibility",
        "stem": "When I need to shift a day, I ask ahead in writing and offer a specific alternative.",
    },
    {
        "id": "s6",
        "dimension": "flexibility",
        "stem": "When my co-parent asks for a swap, I try to say yes when I reasonably can.",
    },
    {
        "id": "s7",
        "dimension": "flexibility",
        "stem": "Last-minute changes stay the exception, not the rule.",
    },
    {
        "id": "s8",
        "dimension": "flexibility",
        "stem": "Missed time is made up in a way we both agree on.",
    },
    {
        "id": "s9",
        "dimension": "transitions",
        "stem": "Handoff times and locations are confirmed in writing before the day.",
    },
    {
        "id": "s10",
        "dimension": "transitions",
        "stem": "The kids' gear (homework, meds, favourite items) travels with them without last-minute scrambles.",
    },
    {
        "id": "s11",
        "dimension": "transitions",
        "stem": "Adult conversation at the handoff stays short and calm — the kids don't overhear conflict.",
    },
    {
        "id": "s12",
        "dimension": "transitions",
        "stem": "Each handoff ends with a warm goodbye so the kids feel steady, not stretched.",
    },
]


def public_schema() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "likert_labels": LIKERT_LABELS,
        "dimensions": DIMENSIONS,
        "questions": [
            {
                "id": q["id"],
                "dimension": q["dimension"],
                "stem": q["stem"],
                "reverse": q.get("reverse", False),
            }
            for q in QUESTIONS
        ],
    }


def validate_answers(answers: Dict[str, Any]) -> Dict[str, int]:
    valid_ids = {q["id"] for q in QUESTIONS}
    cleaned: Dict[str, int] = {}
    for k, v in (answers or {}).items():
        if k not in valid_ids:
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 5:
            cleaned[k] = n
    return cleaned


def score(answers: Dict[str, int]) -> Dict[str, Any]:
    totals: Dict[str, List[int]] = {d: [] for d in DIMENSIONS}
    for q in QUESTIONS:
        raw = answers.get(q["id"])
        if raw is None:
            continue
        value = (6 - raw) if q.get("reverse") else raw
        totals[q["dimension"]].append(value)

    per_dimension = {}
    for dim, values in totals.items():
        if not values:
            per_dimension[dim] = {"score": 0, "answered": 0}
            continue
        avg = sum(values) / len(values)
        pct = round(((avg - 1) / 4) * 100)
        per_dimension[dim] = {"score": pct, "answered": len(values)}

    answered_total = sum(d["answered"] for d in per_dimension.values())
    if answered_total:
        overall = round(
            sum(d["score"] * d["answered"] for d in per_dimension.values())
            / answered_total
        )
    else:
        overall = 0

    return {
        "overall": overall,
        "dimensions": per_dimension,
        "answered_count": answered_total,
        "total_questions": len(QUESTIONS),
    }
