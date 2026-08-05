"""Psychological Deep Dive v2 — score-card journey report.

Retires the rich v1 narrative journey (family situation, provider directory,
attachment risk map, therapist-suggestion narrative). v2 delivers the same
compact score-card shape the Educational Deep Dive v2 uses, keyed to the
five psych parts.

Output keys match `edu_deep_journey.build_journey_report` exactly so the
existing React report page keeps rendering.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from psych_deep_scoring import score_deep_dive


DISCLAIMER = (
    "This score card reflects the responses of one parent. It is not a "
    "psychological diagnosis, a professional evaluation, or a determination "
    "of either parent's legal rights. Consult qualified professionals — "
    "the child's therapist, a psychologist, a paediatrician, a mediator, or "
    "an attorney — for decisions that affect your child."
)


FINAL_SUMMARY = (
    "Emotional alignment is not about agreeing on everything. It's about "
    "the child experiencing a coherent emotional climate across two homes. "
    "Small wins in your own regulation cascade into everything else."
)


def _rating_from_percent(percent: int) -> str:
    if percent >= 81:
        return "Strong"
    if percent >= 51:
        return "Developing"
    return "Needs Attention"


def build_journey_report(*, parent_name: Optional[str], child_name: Optional[str],
                         responses: Dict[str, Any]) -> Dict[str, Any]:
    scored = score_deep_dive(responses or {})

    rating_areas: List[Dict[str, Any]] = []
    for section in scored["sections"]:
        rating_areas.append({
            "id":        section["id"],
            "area":      section["name"],
            "rating":    _rating_from_percent(section["percent"])
                         if section["answered"] else "Not enough info",
            "score":     None if not section["answered"]
                         else round(section["percent"] / 25.0, 2),
            "narrative": _section_narrative(section),
            "raw_total": section["total"],
            "raw_possible": section["possible"],
            "percent":   section["percent"],
        })

    alignment_areas = [a["area"] for a in rating_areas if a["rating"] == "Strong"]
    attention_areas = [a["area"] for a in rating_areas if a["rating"] == "Needs Attention"]
    if not alignment_areas and not attention_areas:
        alignment_areas = ["You've started measuring emotional alignment — that itself is progress."]

    return {
        "cover": {
            "parent_name":   parent_name or "-",
            "child_name":    child_name or "-",
            "grade_level":   "-",
            "school_setting": "-",
            "school_state":  "-",
        },
        "overview": {
            "purpose_bullets": [
                "Measure the emotional climate the child feels across two homes.",
                "Highlight the parts of co-parenting that are already regulated.",
                "Surface the patterns that may be showing up in the child's mood or sleep.",
                "Name the smallest next step that would move alignment up.",
            ],
        },
        "score_card": {
            "version":      scored["version"],
            "total":        scored["total"],
            "possible":     scored["possible"],
            "percent":      scored["percent"],
            "answered":     scored["answered"],
            "na":           scored["na"],
            "unanswered":   scored["unanswered"],
            "band":         scored["band"],
            "band_label":   scored["band_label"],
            "band_summary": scored["band_summary"],
            "next_steps":   scored["next_steps"],
            "sections":     scored["sections"],
        },
        "support_summary": {
            "ratings":            rating_areas,
            "overall_narrative":  scored["band_summary"],
        },
        "child_profile": {
            "strengths":       [],
            "concerns":        [],
            "primary_concern": "",
            "benefit_from":    "",
            "notes":           "",
        },
        "school_involvement":       {"roles": [], "meetings": []},
        "co_parenting_assessment": {
            "information_sharing":       {"rating": "Not enough info",
                                          "shared_items": [], "gap_items": []},
            "consistency_between_homes": {"rating": "Not enough info", "items": []},
            "decision_making":           {"rating": "Not enough info", "items": []},
        },
        "alignment_areas": alignment_areas,
        "attention_areas": attention_areas,
        "support_level":   _support_level(scored),
        "practical_options": scored["next_steps"],
        "action_plan":     _action_plan(rating_areas),
        "foundation_statement": _foundation_statement(rating_areas, scored),
        "questions_for_school_or_parent": [
            "Which emotional routines are we already synced on across homes?",
            "Which routine, if we synced it, would soften the child's transitions the most?",
            "What is the smallest change we could commit to for the next 30 days?",
            "When will we check in on whether the child's mood, sleep, or behaviour improved?",
        ],
        "final_summary":   FINAL_SUMMARY,
        "disclaimer":      DISCLAIMER,
    }


def _section_narrative(section: Dict[str, Any]) -> str:
    if not section["answered"]:
        return "Not yet scored for this part."
    p = section["percent"]
    name = section["name"]
    if p >= 81:
        return (
            f"'{name}' is a strength. Both homes appear to hold this "
            "consistently — that steady climate is exactly what a child "
            "needs to feel secure."
        )
    if p >= 51:
        return (
            f"'{name}' is developing. Some items are consistent between "
            "homes; others slip through. Pick ONE item you rated 2 or "
            "lower and target it this month."
        )
    return (
        f"'{name}' needs attention. This is where the child likely feels "
        "the most emotional whiplash between homes. Start with the single "
        "item you rated lowest — even a small sync makes a visible "
        "difference in their mood and sleep."
    )


def _support_level(scored: Dict[str, Any]) -> Dict[str, Any]:
    band = scored["band"]
    if band == "high":
        return {"level": 1, "name": "Maintain and Monitor",
                "description":
                    "The emotional climate is steady. Keep the routines that "
                    "are working and review quarterly.",
                "next_steps": scored["next_steps"]}
    if band == "moderate":
        return {"level": 2, "name": "Draft a Cross-Home Emotional Rulebook",
                "description":
                    "Enough friction that the child is feeling it. Focus on "
                    "the two lowest-scoring parts and lock in identical rules.",
                "next_steps": scored["next_steps"]}
    if band == "low":
        return {"level": 3, "name": "Professional Coordination Recommended",
                "description":
                    "The emotional environment is measurably affecting the "
                    "child. A neutral professional (co-parenting therapist, "
                    "parent coordinator, or the child's own therapist) should "
                    "facilitate.",
                "next_steps": scored["next_steps"]}
    return {"level": 0, "name": "Not yet scored",
            "description": "Answer at least one item to see your alignment score.",
            "next_steps": []}


def _action_plan(rating_areas: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    scored = [a for a in rating_areas if a["percent"] is not None
              and a["rating"] != "Not enough info"]
    scored.sort(key=lambda a: a["percent"])
    plan: List[Dict[str, str]] = []
    for i, a in enumerate(scored[:4], start=1):
        plan.append({
            "priority":    str(i),
            "action":      f"Improve {a['area']}",
            "detail":      f"Currently at {a['percent']}%. Target: at least +15 points this month.",
            "responsible": "Both parents",
            "target":      "30 days",
        })
    if not plan:
        plan.append({
            "priority": "1",
            "action": "Complete the alignment assessment",
            "detail": "Answer all 25 items so we can score the parts accurately.",
            "responsible": "You", "target": "This week",
        })
    return plan


def _foundation_statement(rating_areas: List[Dict[str, Any]],
                          scored: Dict[str, Any]) -> str:
    strengths = [a["area"].lower() for a in rating_areas if a["rating"] == "Strong"]
    weaknesses = [a["area"].lower() for a in rating_areas
                  if a["rating"] == "Needs Attention"]
    parts: List[str] = []
    if strengths:
        parts.append(
            "Our emotional co-parenting is already working well in " +
            _oxford(strengths) + "."
        )
    if weaknesses:
        parts.append(
            "We can do better in " + _oxford(weaknesses) + "."
        )
    parts.append(
        "I am committed to holding my own regulation first, protecting our "
        "child's attachment security through transitions, and reviewing "
        "progress on the smallest sync-up we can commit to right now."
    )
    if scored["band"] == "low":
        parts.append(
            "I am open to bringing in a neutral professional to help us "
            "build the emotional climate our child needs."
        )
    return " ".join(parts)


def _oxford(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
