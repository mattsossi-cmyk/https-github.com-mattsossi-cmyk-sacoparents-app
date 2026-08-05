"""Psychological Deep Dive — v2 alignment scoring.

Identical scoring shape to the Educational Deep Dive v2. See
:mod:`edu_deep_scoring` for the full contract. Only the band summaries
and next-step language are psych-specific.
"""
from __future__ import annotations

from typing import Any, Dict, List

from psych_deep_questions import (
    DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION,
    POINTS_PER_ITEM_MAX,
)


HIGH_BAND_MIN = 81
MODERATE_BAND_MIN = 51


def _band(percent: int) -> Dict[str, Any]:
    if percent >= HIGH_BAND_MIN:
        return {
            "band": "high",
            "band_label": "High Alignment",
            "band_summary": (
                "The emotional climate you're building around your child is "
                "steady and coherent. Both homes are modelling regulated "
                "adults, protecting attachment, and reinforcing therapy."
            ),
            "next_steps": [
                "Keep doing what you're doing.",
                "Check in with the therapist or counsellor before any big transition (school year, custody change, medication shift).",
                "Schedule a light quarterly emotional-climate review with your co-parent so consistency doesn't drift.",
            ],
        }
    if percent >= MODERATE_BAND_MIN:
        return {
            "band": "moderate",
            "band_label": "Moderate Alignment",
            "band_summary": (
                "You care about your child's emotional health, but "
                "inconsistencies between homes or unresolved conflict "
                "between parents are showing up in the child's mood, sleep, "
                "or behaviour. Small, targeted repairs will make a big "
                "difference."
            ),
            "next_steps": [
                "Look specifically at Parts 1 and 2 - regulated adults and a safe emotional climate come first.",
                "Ask the child's therapist for THREE cross-home rules you can both hold identically for the next 30 days.",
                "Agree that ONE topic (e.g. bedtime, screen time, reunion routine) will be identical in both homes for 30 days.",
                "Set a 30-day review to check whether the child's sleep, mood, or behaviour has softened.",
            ],
        }
    return {
        "band": "low",
        "band_label": "Low Alignment",
        "band_summary": (
            "The emotional environment across the two homes is measurably "
            "hurting your child. Conflict, criticism, or unpredictability "
            "may be showing up as anxiety, withdrawal, regression, or "
            "acting out - not because the child is 'the problem', but "
            "because the adults' emotional patterns are the input."
        ),
        "next_steps": [
            "Consider a co-parenting therapist or parent coordinator - a neutral third adult who reduces the emotional load between you.",
            "Ensure the child has a stable therapist / counsellor of their own.",
            "Move all non-emergency co-parenting communication to writing so it's calmer and dated.",
            "Focus on ONE small win in Part 1 (your own regulation) first - the child's climate follows the adults'.",
        ],
    }


def _section_score(section: Dict[str, Any],
                   responses: Dict[str, Any]) -> Dict[str, Any]:
    items = section["items"]
    total_items = len(items)
    total = 0
    answered = 0
    na = 0
    for iid in items.keys():
        key = f"{section['id']}_{iid}"
        v = responses.get(key)
        if v == "na":
            na += 1
        elif isinstance(v, bool):
            continue
        elif isinstance(v, int) and 0 <= v <= POINTS_PER_ITEM_MAX:
            total += v
            answered += 1
    possible = answered * POINTS_PER_ITEM_MAX
    percent = round((total / possible) * 100) if possible else 0
    band_key = _band(percent)["band"] if answered else "unrated"
    return {
        "id":       section["id"],
        "number":   section["number"],
        "name":     section["name"],
        "answered": answered,
        "na":       na,
        "unanswered": total_items - answered - na,
        "total":    total,
        "possible": possible,
        "percent":  percent,
        "band":     band_key,
    }


def score_deep_dive(responses: Dict[str, Any]) -> Dict[str, Any]:
    sections: List[Dict[str, Any]] = []
    total = 0
    answered = 0
    na = 0
    unanswered = 0
    for s in DEEP_DIVE_SECTIONS:
        row = _section_score(s, responses or {})
        total += row["total"]
        answered += row["answered"]
        na += row["na"]
        unanswered += row["unanswered"]
        sections.append(row)
    possible = answered * POINTS_PER_ITEM_MAX
    percent = round((total / possible) * 100) if possible else 0
    band_info = _band(percent) if answered else {
        "band": "unrated",
        "band_label": "Not yet scored",
        "band_summary": "Answer at least one item to see your alignment score.",
        "next_steps": [],
    }
    return {
        "version":       DEEP_DIVE_VERSION,
        "total":         int(total),
        "possible":      int(possible),
        "answered":      int(answered),
        "na":            int(na),
        "unanswered":    int(unanswered),
        "percent":       int(percent),
        "band":          band_info["band"],
        "band_label":    band_info["band_label"],
        "band_summary":  band_info["band_summary"],
        "next_steps":    band_info["next_steps"],
        "sections":      sections,
        "totals": {
            "answered":  int(answered),
            "flagged":   sum(1 for s in sections
                             if s["answered"] > 0 and s["band"] == "low"),
            "strengths": sum(1 for s in sections
                             if s["answered"] > 0 and s["band"] == "high"),
        },
        "is_texas": False,
    }
