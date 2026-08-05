"""Psychological / Behavioural Needs — Deep Dive schema (v2).

Iteration 70 (2026-02-05) — rebuilt as a 25-item Co-Parenting
Psychological Alignment Framework, mirroring the shape used by the
Educational Deep Dive v2.

* Emotional Regulation Between Parents         (5 items)
* The Child's Emotional Environment            (5 items)
* Therapy & Mental-Health Coordination         (5 items)
* Trauma, Grief & Attachment                   (5 items)
* Modelling Emotional Health for the Child     (5 items)

Total 100 points; three interpretation bands (81-100 High,
51-80 Moderate, 0-50 Low). See :mod:`psych_deep_scoring`.

The old 11-section v1 schema (psych-deep-1.0.0) has been retired.
Answers saved against that schema are silently ignored at load time and
overwritten by the new schema.
"""
from __future__ import annotations

from typing import Any, Dict, List


DEEP_DIVE_VERSION = "psych-deep-2.0.0"

# ---------------------------------------------------------------------------
# 0-4 alignment likert (identical shape to the Educational v2 scale so the
# UI's LikertRow renders the same 5-button row + N/A).
# ---------------------------------------------------------------------------
ALIGNMENT_SCALE = [0, 1, 2, 3, 4]
ALIGNMENT_LABELS = {
    0: "Never / High Conflict",
    1: "Seldom / Rarely",
    2: "Sometimes / Inconsistent",
    3: "Often / Mostly Consistent",
    4: "Always / Very Consistent",
}

POINTS_PER_ITEM_MAX = 4
TOTAL_ITEMS = 25


def _alignment_item(prompt: str) -> Dict[str, Any]:
    return {
        "type": "alignment",
        "scale": ALIGNMENT_SCALE,
        "labels": ALIGNMENT_LABELS,
        "prompt": prompt,
        "allow_na": True,
        "scored": True,
    }


DEEP_DIVE_SECTIONS: List[Dict[str, Any]] = [
    # 1 -----------------------------------------------------------------
    {"id": "p1", "number": 1, "name": "Emotional Regulation Between Parents",
     "purpose": "How well both adults manage their own emotions in the "
                "child's presence and around each other.",
     "items": {
        "q1": _alignment_item(
            "We keep our own frustration, anger, or sadness in check when "
            "we're with the children."),
        "q2": _alignment_item(
            "We pause and take a breath before responding when the other "
            "parent says something that upsets us."),
        "q3": _alignment_item(
            "We take responsibility for our own emotional reactions rather "
            "than blaming the other parent for how we feel."),
        "q4": _alignment_item(
            "We recognise when we're too heated for a conversation and "
            "postpone it rather than pushing through in front of the child."),
        "q5": _alignment_item(
            "We repair after a disagreement so the tension doesn't linger "
            "in the child's emotional atmosphere."),
     }},
    # 2 -----------------------------------------------------------------
    {"id": "p2", "number": 2, "name": "The Child's Emotional Environment",
     "purpose": "The emotional climate the child actually feels when moving "
                "between homes.",
     "items": {
        "q6": _alignment_item(
            "Our child feels safe expressing sadness, worry, or anger to "
            "EITHER parent without needing to hide it."),
        "q7": _alignment_item(
            "Our child never feels caught in the middle of a disagreement "
            "or asked to take sides."),
        "q8": _alignment_item(
            "Our child sees adults handling stress calmly and constructively "
            "in both homes."),
        "q9": _alignment_item(
            "Our child has predictable emotional routines (a listening "
            "adult, a comfort item, a bedtime wind-down) in both homes."),
        "q10": _alignment_item(
            "Our child is allowed to love and enjoy time with the other "
            "parent without feeling disloyal."),
     }},
    # 3 -----------------------------------------------------------------
    {"id": "p3", "number": 3, "name": "Therapy & Mental-Health Coordination",
     "purpose": "How well both parents support and coordinate the child's "
                "counselling, therapy, and mental-health care.",
     "items": {
        "q11": _alignment_item(
            "Both parents actively support our child's therapy or "
            "counselling — attending, funding, reinforcing at home."),
        "q12": _alignment_item(
            "We share therapist recommendations, session summaries, and "
            "homework between homes within a reasonable time."),
        "q13": _alignment_item(
            "We hold the same house rules that the therapist recommends "
            "(e.g. reflection time, feelings vocabulary, coping toolkit) "
            "in both households."),
        "q14": _alignment_item(
            "We coordinate psychiatric medication doses, timings, and "
            "refills so the child's routine never lapses between houses."),
        "q15": _alignment_item(
            "We never criticise the therapist, the diagnosis, or the "
            "treatment plan in front of the child."),
     }},
    # 4 -----------------------------------------------------------------
    {"id": "p4", "number": 4, "name": "Trauma, Grief & Attachment",
     "purpose": "How we protect the child's attachment security through "
                "big transitions and any earlier losses.",
     "items": {
        "q16": _alignment_item(
            "We recognise the separation itself as a loss for our child "
            "and give them permission to grieve it."),
        "q17": _alignment_item(
            "Reunions after time apart are calm, warm, and unhurried — "
            "not filled with questions about the other parent's household."),
        "q18": _alignment_item(
            "We keep transitions between homes emotionally soft (goodbye "
            "hugs, a comfort object, a predictable handoff)."),
        "q19": _alignment_item(
            "We are alert to signs of anxiety, regression, sleep changes, "
            "or withdrawal, and we alert one another when we notice them."),
        "q20": _alignment_item(
            "We DO NOT interrogate the child about the other household "
            "or use them as a source of information about the other parent."),
     }},
    # 5 -----------------------------------------------------------------
    {"id": "p5", "number": 5, "name": "Modelling Emotional Health for the Child",
     "purpose": "The emotional patterns the child sees us modelling every "
                "day — because they will inherit them.",
     "items": {
        "q21": _alignment_item(
            "We speak about the other parent with respect (or neutrally) "
            "even when the child is not obviously listening."),
        "q22": _alignment_item(
            "We name our own emotions out loud (\"I'm feeling frustrated, "
            "I'm going to step outside for a minute\") so the child sees "
            "emotional literacy modelled."),
        "q23": _alignment_item(
            "We each take care of our own mental health — therapy, "
            "exercise, sleep, community — so the child sees adults "
            "seeking help without shame."),
        "q24": _alignment_item(
            "We celebrate the child's emotional growth (naming feelings, "
            "asking for help, apologising) in both homes."),
        "q25": _alignment_item(
            "We forgive our co-parent when they slip up, the same way we "
            "want the child to learn to forgive."),
     }},
]


# Kept as an empty list for schema stability — v2 has no free-text
# decision topics like v1 did.
DECISION_TOPICS: List[tuple] = []


# ---------------------------------------------------------------------------
# Public helpers (mirror `edu_deep_questions`)
# ---------------------------------------------------------------------------
def public_schema() -> Dict[str, Any]:
    return {
        "version": DEEP_DIVE_VERSION,
        "sections": [
            {
                "id":       s["id"],
                "number":   s["number"],
                "name":     s["name"],
                "purpose":  s.get("purpose"),
                "texas_only": False,
                "gate":     None,
                "items": [{"id": iid, **spec} for iid, spec in s["items"].items()],
            }
            for s in DEEP_DIVE_SECTIONS
        ],
    }


def all_item_keys() -> List[str]:
    out = []
    for s in DEEP_DIVE_SECTIONS:
        for iid in s["items"].keys():
            out.append(f"{s['id']}_{iid}")
    return out


def item_by_key(key: str) -> Dict[str, Any] | None:
    for s in DEEP_DIVE_SECTIONS:
        for iid, spec in s["items"].items():
            if f"{s['id']}_{iid}" == key:
                return {**spec, "id": iid, "section": s["id"]}
    return None


def validate_answer(key: str, value: Any) -> bool:
    if item_by_key(key) is None:
        return False
    if value == "na":
        return True
    if isinstance(value, bool):
        return False
    return isinstance(value, int) and 0 <= value <= 4


def is_v2_key(key: str) -> bool:
    return key.startswith(("p1_", "p2_", "p3_", "p4_", "p5_"))
