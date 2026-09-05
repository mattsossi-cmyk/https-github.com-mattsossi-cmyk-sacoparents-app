"""
Communication Reflection question bank.

Neutral, non-adjudicative stems written for a parent reflecting on
themselves — never phrased as an accusation about the co-parent. Every
item accepts a 1–5 Likert response ("Almost never" → "Almost always")
plus an optional short free-text note. The scoring layer aggregates
answers into three high-level dimensions that later feed the Compare
+ Alignment Report artefact.

Guardrails
----------
* First-person stems: "I aim to…", "When we exchange messages, I try
  to…" — never "the other parent does X".
* Sensitive items (safety, threats) intentionally live in the Safety
  assessment, not here. Communication reflection MUST NOT collect
  safety-screen answers.
* Reverse-scoring stems (`reverse=True`) still ask for positive
  behaviour; the scoring layer inverts them so a "1" on a reverse
  stem represents the same directional signal as a "5" on a normal
  stem.
"""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = 1

# Likert anchor labels — parent-facing, hopeful, neutral.
LIKERT_LABELS = [
    "Almost never",
    "Rarely",
    "Sometimes",
    "Often",
    "Almost always",
]

# Three dimensions the parent's answers score into. Kept small on
# purpose — the artefact is a *conversation starter*, not a
# personality test.
DIMENSIONS = {
    "clarity": {
        "label": "Clarity",
        "blurb": "Keeping messages brief, informative, and child-focused.",
    },
    "regulation": {
        "label": "Regulation",
        "blurb": "Staying calm and taking a beat before responding.",
    },
    "structure": {
        "label": "Structure",
        "blurb": "Using channels, timing, and expectations we can both rely on.",
    },
}


# Each stem is a first-person aspiration. `dimension` maps into the
# three high-level scoring buckets. `reverse=True` means high agreement
# indicates *lower* alignment on the dimension — scoring inverts.
QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "c1",
        "dimension": "clarity",
        "stem": "When I message about the kids, I keep it brief and focused on what needs to happen.",
    },
    {
        "id": "c2",
        "dimension": "clarity",
        "stem": "I make it easy to tell the difference between an FYI, a request, and a decision that needs a reply.",
    },
    {
        "id": "c3",
        "dimension": "clarity",
        "stem": "When I bring up a concern, I state the situation first and my proposed next step second.",
    },
    {
        "id": "c4",
        "dimension": "regulation",
        "stem": "Before I hit send on a difficult message, I re-read it once for tone.",
    },
    {
        "id": "c5",
        "dimension": "regulation",
        "stem": "When a message lands the wrong way, I take a beat before responding.",
    },
    {
        "id": "c6",
        "dimension": "regulation",
        "stem": "When we disagree, I stay on the current topic instead of pulling in older frustrations.",
        "reverse": False,
    },
    {
        "id": "c7",
        "dimension": "regulation",
        "stem": "I let long threads sit overnight when I notice myself escalating.",
    },
    {
        "id": "c8",
        "dimension": "structure",
        "stem": "We have a channel (app, email, text) we agree is the right place for co-parenting messages.",
    },
    {
        "id": "c9",
        "dimension": "structure",
        "stem": "We have a rough expectation for how quickly non-urgent messages get answered.",
    },
    {
        "id": "c10",
        "dimension": "structure",
        "stem": "Handoff logistics (times, locations, gear) are confirmed in writing before the day.",
    },
    {
        "id": "c11",
        "dimension": "structure",
        "stem": "Big decisions about the kids happen between the adults, not through the kids.",
    },
    {
        "id": "c12",
        "dimension": "clarity",
        "stem": "I close out threads with a short confirmation once something is agreed.",
    },
]


def public_schema() -> Dict[str, Any]:
    """The frontend intake page renders directly from this."""
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
    """
    Coerce the frontend payload into a clean `{question_id: 1..5}`
    map. Silently drop unknown ids and out-of-range values so a
    malformed submission doesn't 500 the whole call.
    """
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
    """
    Aggregate cleaned answers into per-dimension 0-100 scores plus an
    overall 0-100 score. Reverse-scored items are inverted before
    averaging. Returns 0 for a dimension with no answers rather than
    None so downstream comparators can treat the shape uniformly.
    """
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
        pct = round(((avg - 1) / 4) * 100)  # 1..5 → 0..100
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
