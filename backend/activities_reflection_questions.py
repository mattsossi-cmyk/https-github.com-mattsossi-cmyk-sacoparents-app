"""
Activities Reflection question bank.

Same conventions as `communication_reflection_questions.py`:
  * Neutral, non-adjudicative, first-person stems.
  * 1–5 Likert responses.
  * Three high-level scoring dimensions.

Scope
-----
Activities = the kids' extracurriculars, sports, arts, camps, faith,
tutoring, and social plans. Explicitly NOT medical, educational, or
therapeutic decisions — those live on the Med / Edu / Psych Deep-Dive
pathways.
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
    "awareness": {
        "label": "Awareness",
        "blurb": "Each of us knows what activities the kids are doing on the other's time.",
    },
    "support": {
        "label": "Support",
        "blurb": "We back the kids' interests without gatekeeping or veto.",
    },
    "logistics": {
        "label": "Logistics",
        "blurb": "Gear, cost, transport, and timing get resolved smoothly.",
    },
}


QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "a1",
        "dimension": "awareness",
        "stem": "I can name the kids' current activities (sport, art, faith, tutoring) and roughly when they meet.",
    },
    {
        "id": "a2",
        "dimension": "awareness",
        "stem": "New activities get added to a shared calendar or list we both can see.",
    },
    {
        "id": "a3",
        "dimension": "awareness",
        "stem": "I know the coach, teacher, or lead adult by name for each of the kids' main activities.",
    },
    {
        "id": "a4",
        "dimension": "awareness",
        "stem": "Game / recital / event dates are visible to us both at least a week ahead.",
    },
    {
        "id": "a5",
        "dimension": "support",
        "stem": "When an activity falls on my parenting time, I get the kids there without last-minute drama.",
    },
    {
        "id": "a6",
        "dimension": "support",
        "stem": "The kids feel free to talk about an activity at both houses, not just the one that signed them up.",
    },
    {
        "id": "a7",
        "dimension": "support",
        "stem": "Adding, changing, or dropping an activity is a joint conversation, not a unilateral call.",
    },
    {
        "id": "a8",
        "dimension": "support",
        "stem": "I make room for the co-parent to attend an event on my time (recital, game, ceremony).",
    },
    {
        "id": "a9",
        "dimension": "logistics",
        "stem": "Gear (uniforms, instruments, water bottle, permission slips) travels between houses without last-minute scrambles.",
    },
    {
        "id": "a10",
        "dimension": "logistics",
        "stem": "Registration fees, gear costs, and travel expenses are agreed on before signing the kids up.",
    },
    {
        "id": "a11",
        "dimension": "logistics",
        "stem": "Transportation to and from activities is planned ahead — no last-minute 'who's driving?' texts.",
    },
    {
        "id": "a12",
        "dimension": "logistics",
        "stem": "Photos, videos, and updates from events are shared with the co-parent within a day or two.",
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
