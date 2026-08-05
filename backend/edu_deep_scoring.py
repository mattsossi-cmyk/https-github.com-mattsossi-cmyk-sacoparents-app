"""Educational Deep Dive — v2 alignment scoring.

Produces a compact, deterministic score card:

    {
      "version":       "edu-deep-2.0.0",
      "total":         int          # 0-100
      "possible":      int          # scale of 25 * 4 = 100 if all answered
      "answered":      int          # number of items answered (excluding N/A)
      "na":            int          # number of N/A answers
      "unanswered":    int          # number of unanswered items
      "percent":       int          # 0-100, "total / possible" pro-rated
      "band":          str          # "high" | "moderate" | "low"
      "band_label":    str          # human-friendly label
      "band_summary":  str          # sentence explaining what the band means
      "next_steps":    List[str]    # short list of tailored next steps
      "sections":      [
          {"id", "number", "name", "answered", "na",
           "total", "possible", "percent", "band"},
          ...
      ],
    }

Bands (from the user's spec):
    81 - 100  High Alignment      (Collaborative Special Needs Co-Parenting)
    51 -  80  Moderate Alignment  (Inconsistent Special Needs Support)
     0 -  50  Low Alignment       (High Conflict / Fractured Support)

Pro-rating: if any items are unanswered, ``total`` still uses the sum of
raw scores, but ``percent`` is expressed against the number actually
answered so a partial completion isn't punished. The band is determined
by ``percent`` (0-100), not by ``total``.

Backwards-compat shape: the top-level dict also exposes ``totals``
(answered/flagged/strengths counts) and ``is_texas`` so downstream code
that used to depend on the v1 shape doesn't crash.
"""
from __future__ import annotations

from typing import Any, Dict, List

from edu_deep_questions import (
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
                "You provide excellent consistency. Your child benefits "
                "immensely from having the same routines, expectations, "
                "and communication reinforced in both households."
            ),
            "next_steps": [
                "Keep doing what you are doing.",
                "Review the IEP and any medication plan together before the annual ARD meeting.",
                "Schedule a light quarterly check-in so consistency doesn't drift.",
            ],
        }
    if percent >= MODERATE_BAND_MIN:
        return {
            "band": "moderate",
            "band_label": "Moderate Alignment",
            "band_summary": (
                "You both love your child, but differences in routines or "
                "communication gaps are causing friction. Inconsistencies "
                "in ADHD medication, IEP homework rules, or logistics may "
                "cause the child to regress between transitions."
            ),
            "next_steps": [
                "Look specifically at your scores in Parts 3 and 4.",
                "Draft a short 'Special Education & Medical Addendum' to your parenting plan that locks in identical rules.",
                "Agree on ONE shared calendar or co-parenting app and use it consistently for 30 days.",
                "Set a 30-day review to check whether the friction points have eased.",
            ],
        }
    return {
        "band": "low",
        "band_label": "Low Alignment",
        "band_summary": (
            "High conflict or a significant disconnect is actively hurting "
            "your child's academic and behavioural progress. Disagreements "
            "over ADHD, medication, or IEP goals are creating instability."
        ),
        "next_steps": [
            "Switch to communication strictly via text or co-parenting app so records are dated.",
            "Consider hiring a formal Co-Parenting Coordinator or a Special-Education Advocate to mediate ARD meetings.",
            "Loop in the child's therapist / prescriber so medical decisions are made through a neutral professional.",
            "Focus on ONE small win in Part 5 (logistics) first — reliability rebuilds trust.",
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
            continue  # reject bools masquerading as int
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
    """Full score-card. See module docstring for shape."""
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
        "band":         "unrated",
        "band_label":   "Not yet scored",
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
        # ---- Backwards-compat shape (kept so legacy callers don't crash)
        "totals":        {
            "answered":  int(answered),
            "flagged":   sum(1 for s in sections
                             if s["answered"] > 0 and s["band"] == "low"),
            "strengths": sum(1 for s in sections
                             if s["answered"] > 0 and s["band"] == "high"),
        },
        "is_texas":      False,
    }
