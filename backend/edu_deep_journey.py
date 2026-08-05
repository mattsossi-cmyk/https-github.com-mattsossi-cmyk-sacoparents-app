"""Educational Deep Dive v2 — score-card journey report.

The rich v1 narrative journey (situation → assessment results → child's
needs → co-parenting challenges → practical options → parent action plan
→ foundation statement) has been retired alongside the v1 60-item
schema.

v2 produces a simpler, honest **score card** driven directly by the
25-item alignment scoring: total /100, band label, per-part scores, and
a short band-specific action list. The rich narrative return will
follow in the next iteration (see the yellow banner on the report
page).

The output dict keeps the same top-level keys the frontend already
consumes (`cover`, `overview`, `support_summary`, `alignment_areas`,
`attention_areas`, `support_level`, `practical_options`, `action_plan`,
`foundation_statement`, `questions_for_school_or_parent`,
`final_summary`, `disclaimer`) so the existing React report page and
PDF renderer don't 500.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from edu_deep_questions import DEEP_DIVE_SECTIONS
from edu_deep_scoring import score_deep_dive
from deep_dive_narrative import (
    build_part_narratives,
    build_opening_story,
    build_closing_story,
)


# Band-driven per-part narrative copy. `body` is a format string with a
# `{name}` placeholder for the part's display name.
_EDU_BAND_NARRATIVES: Dict[str, Dict[str, str]] = {
    "high": {
        "headline": "Steady — keep protecting this",
        "body": (
            "'{name}' is a genuine strength. Both homes appear to hold "
            "this consistently, which is exactly the kind of predictability "
            "that lets a child with special needs settle into learning."
        ),
    },
    "moderate": {
        "headline": "Developing — one small sync away",
        "body": (
            "'{name}' is developing. Some items are held identically "
            "between homes; others are slipping. Pick the single item "
            "you scored lowest and target it for the next 30 days — "
            "small syncs cascade."
        ),
    },
    "low": {
        "headline": "Needs attention — start here",
        "body": (
            "'{name}' is where the child is most likely to feel whiplash "
            "between the two homes. It shows up as anxiety before school, "
            "harder homework nights, or slipping accommodations. Even one "
            "small alignment here creates a visibly calmer child."
        ),
    },
    "unrated": {
        "headline": "Not yet scored",
        "body": (
            "'{name}' isn't scored yet — return to the assessment and "
            "answer the five items in this part to unlock its story."
        ),
    },
}

# Child-focused reflection sentences that tie each part to what the
# child actually experiences at home / school.
_EDU_CHILD_REFLECTION = {
    "p1": "For your child, this shows up as whether they can love both homes without guilt.",
    "p2": "For your child, this shows up as how safe they feel telling both parents the same thing.",
    "p3": "For your child, this shows up as whether their IEP travels with them or gets rewritten each week.",
    "p4": "For your child, this shows up as whether their brain gets to relax into a predictable routine.",
    "p5": "For your child, this shows up as whether daily life feels boring in the best way — reliable.",
}


DISCLAIMER = (
    "This score card reflects the responses of one parent. It is not a "
    "diagnosis, a professional educational evaluation, or a determination "
    "of either parent's legal rights. Consult qualified professionals — "
    "the child's teacher, counsellor, an educational diagnostician, a "
    "mediator, or an attorney — for decisions that affect your child."
)


FINAL_SUMMARY = (
    "Alignment isn't about agreeing on everything. It's about the child "
    "experiencing the same routines, expectations, and calm across both "
    "homes. Small wins in one part often cascade into the others."
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

    # Rating areas — one per section, driven by the section's percent.
    rating_areas: List[Dict[str, Any]] = []
    for section in scored["sections"]:
        rating_areas.append({
            "id":        section["id"],
            "area":      section["name"],
            "rating":    _rating_from_percent(section["percent"])
                         if section["answered"] else "Not enough info",
            "score":     None if not section["answered"]
                         else round(section["percent"] / 25.0, 2),  # 0-4 scale
            "narrative": _section_narrative(section),
            "raw_total": section["total"],
            "raw_possible": section["possible"],
            "percent":   section["percent"],
        })

    # Alignment / attention buckets used by the compare view.
    alignment_areas = [
        a["area"] for a in rating_areas if a["rating"] == "Strong"
    ]
    attention_areas = [
        a["area"] for a in rating_areas if a["rating"] == "Needs Attention"
    ]
    # If nothing hits either bucket, seed with a soft neutral so the report
    # never looks empty.
    if not alignment_areas and not attention_areas:
        alignment_areas = ["You have started measuring alignment — that itself is progress."]

    support_level = _support_level(scored)

    parts_narrative = build_part_narratives(
        sections_spec=DEEP_DIVE_SECTIONS,
        scored_sections=scored["sections"],
        responses=responses or {},
        band_narratives=_EDU_BAND_NARRATIVES,
        child_reflection_by_part=_EDU_CHILD_REFLECTION,
    )
    opening_story = build_opening_story(
        parent_name=parent_name, child_name=child_name,
        scored=scored, pathway_label="Educational Alignment Assessment",
    )
    closing_story = build_closing_story(
        scored=scored, pathway_label="Educational Alignment Assessment",
    )

    return {
        "cover": {
            "parent_name":   parent_name or "-",
            "child_name":    child_name or "-",
            "grade_level":   "-",     # v1 field, retained for schema stability
            "school_setting": "-",
            "school_state":  "-",
        },
        "overview": {
            "purpose_bullets": [
                "Measure how consistently both homes hold the child's routines.",
                "Highlight the parts of co-parenting that already work.",
                "Surface the parts that are quietly costing the child energy.",
                "Point to the smallest next step that will move alignment up.",
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
            "ratings": rating_areas,
            "overall_narrative": scored["band_summary"],
        },
        "child_profile": {
            "strengths":       [],
            "concerns":        [],
            "primary_concern": "",
            "benefit_from":    "",
            "notes":           "",
        },
        "school_involvement": {"roles": [], "meetings": []},
        "co_parenting_assessment": {
            "information_sharing":     {"rating": "Not enough info",
                                        "shared_items": [], "gap_items": []},
            "consistency_between_homes": {"rating": "Not enough info", "items": []},
            "decision_making":         {"rating": "Not enough info", "items": []},
        },
        "alignment_areas": alignment_areas,
        "attention_areas": attention_areas,
        "support_level":   support_level,
        "practical_options": scored["next_steps"],
        "action_plan": _action_plan(rating_areas),
        "foundation_statement": _foundation_statement(rating_areas, scored),
        "questions_for_school_or_parent": [
            "Which routines are we already synced on?",
            "Which one routine, if we synced it, would move the needle most?",
            "What is the smallest change we can commit to for the next 30 days?",
            "When will we review whether alignment improved?",
        ],
        "final_summary": FINAL_SUMMARY,
        "parts_narrative": parts_narrative,
        "opening_story":   opening_story,
        "closing_story":   closing_story,
        "disclaimer":    DISCLAIMER,
    }


def _section_narrative(section: Dict[str, Any]) -> str:
    if not section["answered"]:
        return "Not yet scored for this part."
    p = section["percent"]
    name = section["name"]
    if p >= 81:
        return (
            f"'{name}' is one of your strongest parts. Both homes appear "
            "to hold this consistently — that's exactly the kind of "
            "predictability that helps a child with special needs."
        )
    if p >= 51:
        return (
            f"'{name}' is developing. Some items are consistent between "
            "homes; others slip through. Pick ONE item you rated 2 or "
            "lower and target it this month."
        )
    return (
        f"'{name}' needs attention. This is where the child likely feels "
        "the most whiplash between houses. Start with the single item "
        "you rated lowest — even a small sync makes a visible difference."
    )


def _support_level(scored: Dict[str, Any]) -> Dict[str, Any]:
    band = scored["band"]
    if band == "high":
        return {
            "level": 1, "name": "Maintain and Monitor",
            "description":
                "Alignment is strong. Keep the shared systems that are working "
                "and check in quarterly.",
            "next_steps": scored["next_steps"],
        }
    if band == "moderate":
        return {
            "level": 2, "name": "Draft a Special-Education Addendum",
            "description":
                "Enough friction that the child is likely feeling it. Focus on "
                "the two lowest-scoring parts and lock in identical rules.",
            "next_steps": scored["next_steps"],
        }
    if band == "low":
        return {
            "level": 3, "name": "Professional Coordination Recommended",
            "description":
                "High-conflict or disconnected support is measurably hurting "
                "the child. A neutral professional (co-parenting coordinator, "
                "advocate, or child's therapist) should facilitate.",
            "next_steps": scored["next_steps"],
        }
    return {
        "level": 0, "name": "Not yet scored",
        "description": "Answer at least one item to see your alignment score.",
        "next_steps": [],
    }


def _action_plan(rating_areas: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """A short priority-ordered list of the lowest-scoring parts, so the
    reader sees the biggest levers first."""
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
    # If nothing yet, seed a neutral first step.
    if not plan:
        plan.append({
            "priority": "1", "action": "Complete the alignment assessment",
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
            "Our co-parenting is already working well in " +
            _oxford(strengths) + "."
        )
    if weaknesses:
        parts.append(
            "We can do better in " + _oxford(weaknesses) + "."
        )
    parts.append(
        "I am committed to putting our child's routines above our differences, "
        "using written communication where verbal conversation slips, and "
        "reviewing progress on the smallest sync-up we can commit to right now."
    )
    if scored["band"] == "low":
        parts.append(
            "I am open to having a neutral professional help us build the "
            "structure that our child needs."
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
