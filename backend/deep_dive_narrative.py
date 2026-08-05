"""Shared per-part narrative builder for v2 deep dives.

Both the Educational and Psychological Deep Dive v2 assessments share the
same 5 parts × 5 items × 0-4 alignment shape. The rich journey/PDF report
tells the story of each part with:

  - a band-driven 2-3 sentence part narrative
  - up to 2 concrete strengths (items scored 3-4)
  - up to 2 growth opportunities (items scored 0-1)
  - a single child-focused reflection line
  - an overall opening + closing story that stitches the 5 parts together

This module is pathway-agnostic: pass the sections spec (from
`edu_deep_questions` / `psych_deep_questions`), the parent's raw answers,
the scored dict, and pathway-specific narrative fragments and it returns
a ready-to-render dict.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _pick_items(section: Dict[str, Any], responses: Dict[str, Any],
                predicate) -> List[Dict[str, Any]]:
    """Return item dicts (id, prompt, value) for numeric answers matching
    `predicate(value)`. Deterministic ordering by value desc/asc then item id."""
    out: List[Dict[str, Any]] = []
    for iid, spec in (section.get("items") or {}).items():
        key = f"{section['id']}_{iid}"
        v = responses.get(key)
        if isinstance(v, bool):  # bool is subclass of int — reject
            continue
        if not isinstance(v, int):
            continue
        if not predicate(v):
            continue
        out.append({"id": iid, "prompt": spec.get("prompt", ""), "value": v})
    return out


def _strengths(section: Dict[str, Any], responses: Dict[str, Any]) -> List[Dict[str, Any]]:
    picks = _pick_items(section, responses, lambda v: v >= 3)
    picks.sort(key=lambda i: (-i["value"], i["id"]))
    return picks[:2]


def _growth(section: Dict[str, Any], responses: Dict[str, Any]) -> List[Dict[str, Any]]:
    picks = _pick_items(section, responses, lambda v: v <= 1)
    picks.sort(key=lambda i: (i["value"], i["id"]))
    return picks[:2]


def build_part_narratives(
    *,
    sections_spec: List[Dict[str, Any]],
    scored_sections: List[Dict[str, Any]],
    responses: Dict[str, Any],
    band_narratives: Dict[str, Dict[str, str]],
    child_reflection_by_part: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Return a list of per-part narrative blocks (one per section spec).

    :param band_narratives: `{ "high"|"moderate"|"low"|"unrated":
                               {"headline": str, "body": str} }`
    :param child_reflection_by_part: `{ section_id: sentence }`
    """
    scored_by_id = {s["id"]: s for s in scored_sections}
    out: List[Dict[str, Any]] = []
    for spec in sections_spec:
        scored = scored_by_id.get(spec["id"]) or {}
        answered = scored.get("answered", 0) or 0
        band = scored.get("band") if answered else "unrated"
        band_copy = band_narratives.get(band, band_narratives["unrated"])
        out.append({
            "id":            spec["id"],
            "number":        spec["number"],
            "name":          spec["name"],
            "purpose":       spec.get("purpose"),
            "answered":      answered,
            "percent":       scored.get("percent", 0),
            "total":         scored.get("total", 0),
            "possible":      scored.get("possible", 0),
            "band":          band,
            "band_headline": band_copy["headline"],
            "narrative":     band_copy["body"].format(name=spec["name"]),
            "strengths":     _strengths(spec, responses),
            "growth":        _growth(spec, responses),
            "child_reflection": child_reflection_by_part.get(spec["id"], ""),
        })
    return out


def build_opening_story(
    *,
    parent_name: Optional[str],
    child_name: Optional[str],
    scored: Dict[str, Any],
    pathway_label: str,
) -> str:
    """A short opening paragraph that names what the parent has just done
    and the emotional frame in which to read the rest of the report."""
    parent = (parent_name or "").strip() or "You"
    child = (child_name or "").strip() or "your child"
    answered = scored.get("answered", 0)
    total = scored.get("percent", 0)
    if answered == 0:
        return (
            f"{parent}, you opened the {pathway_label} for {child} — "
            "that alone is a step most co-parents never take. When you "
            "answer even one item, the report will speak back to you."
        )
    if total >= 81:
        return (
            f"{parent}, you and the other parent are giving {child} a "
            f"remarkably steady {pathway_label.lower()} experience. "
            "This report celebrates what's working and points out the "
            "small tweaks that keep that steadiness durable."
        )
    if total >= 51:
        return (
            f"{parent}, some parts of your {pathway_label.lower()} are "
            f"already holding for {child} — and others are quietly costing "
            "them energy. This report walks through each part with honesty, "
            "not blame, so you can pick the smallest next step that "
            "actually moves the needle."
        )
    return (
        f"{parent}, this report is honest with you because {child} needs "
        "you to be honest with yourself. The picture below isn't a verdict "
        "on you as a parent — it's a map of where the two homes are out of "
        "sync, so you know exactly where to start."
    )


def build_closing_story(
    *,
    scored: Dict[str, Any],
    pathway_label: str,
) -> str:
    """A short closing paragraph that reframes the score as an invitation."""
    band = scored.get("band")
    if band == "high":
        return (
            f"You've built the kind of {pathway_label.lower()} that most "
            "children only dream of. Protect it — steadiness is easier to "
            "lose than to build."
        )
    if band == "moderate":
        return (
            "You are one honest conversation away from real progress. Pick "
            "the single item you scored lowest and treat it as this "
            "month's project. That's how families rebuild."
        )
    if band == "low":
        return (
            "This is not the end of the story. Many parents whose first "
            "run of this assessment landed here have, within a year, moved "
            "into the moderate band — usually with the help of one neutral "
            "third adult (a therapist, a mediator, or a coordinator). Your "
            "child does not need you to be perfect. They need you to be "
            "steady enough, and steady enough is learnable."
        )
    return (
        "Come back to this assessment any time. The moment you answer "
        "more items, the report gets sharper."
    )
