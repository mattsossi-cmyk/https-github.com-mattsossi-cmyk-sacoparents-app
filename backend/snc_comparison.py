"""Neutral pair-comparison for two independently generated SNC reports.

Rules from the SA CoParents product spec:
  * Compares one parent's report against the other's without picking a winner.
  * Never diagnoses the child, never labels a parent right/wrong, never surfaces
    findings of fact, and never exposes Family Violence & Communication Safety
    (Section 11) responses to the other parent.
  * Verbatim narrative/open-text responses are NEVER copied across; only
    numeric summaries or short neutral phrasings appear.

Output shape (JSON serialisable):
    {
      "generated_at": iso,
      "parents": { "a": {"name": str}, "b": {"name": str} },
      "categories": [ { id, name, a: {...}, b: {...}, bucket, note } ],
      "buckets": {
          "agreement":              [category_id, ...],
          "different_observations": [category_id, ...],
          "missing_information":    [category_id, ...],
          "professional_questions": [str, ...],
          "coordination_areas":     [str, ...]
      },
      "safety_notice": str,   # constant privacy notice; no data
      "disclaimer": str
    }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


AGREEMENT_TOLERANCE = 0.5   # inclusive: |a - b| <= 0.5 → agreement
MISSING = "Not enough data"


SAFETY_NOTICE = (
    "Family Violence and Communication Safety responses (Section 11) are "
    "kept private to each parent and never appear in this side-by-side. If "
    "either parent completes the full Family Violence & Communication Safety "
    "Assessment, its results are also kept out of this document."
)

DISCLAIMER = (
    "This side-by-side is an educational planning aid built from each "
    "parent's own answers. It is not a finding of fact, a diagnosis, a "
    "measure of parental fitness, or legal advice. Neither parent is the "
    "\"correct\" one — the goal is a shared, child-focused plan."
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cat_lookup(category_summary: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index a report.category_summary list by section id."""
    out: Dict[str, Dict[str, Any]] = {}
    for row in category_summary or []:
        cid = row.get("id") or row.get("category_id") or row.get("section_id")
        if cid:
            out[cid] = row
    return out


def _side(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not row:
        return {"score": None, "classification": MISSING}
    return {
        "score": row.get("score") if isinstance(row.get("score"), (int, float)) else None,
        "classification": row.get("classification") or MISSING,
    }


def _bucket_for(pair_a: Dict[str, Any], pair_b: Dict[str, Any]) -> str:
    a = pair_a["score"]
    b = pair_b["score"]
    if a is None and b is None:
        return "missing_information"
    if a is None or b is None:
        return "missing_information"
    if abs(a - b) <= AGREEMENT_TOLERANCE and pair_a["classification"] == pair_b["classification"]:
        return "agreement"
    if abs(a - b) <= AGREEMENT_TOLERANCE:
        # numerically close but different classifications on the boundary — still agreement
        return "agreement"
    return "different_observations"


def _neutral_note(cid: str, name: str, a: Dict[str, Any], b: Dict[str, Any], bucket: str) -> str:
    if bucket == "agreement":
        return (
            f"Both parents describe {name.lower()} similarly "
            f"({a['classification']})."
        )
    if bucket == "missing_information":
        missing_sides = []
        if a["score"] is None:
            missing_sides.append("Parent A")
        if b["score"] is None:
            missing_sides.append("Parent B")
        who = " and ".join(missing_sides) if missing_sides else "one parent"
        return f"{who} has not yet answered enough of {name.lower()} to compare."
    # different observations
    return (
        f"Parents see {name.lower()} differently — Parent A: {a['classification']}, "
        f"Parent B: {b['classification']}."
    )


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items or []:
        if not item or not isinstance(item, str):
            continue
        key = item.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def compare_reports(
    *,
    parent_a_name: str,
    parent_b_name: str,
    report_a: Dict[str, Any],
    report_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the neutral side-by-side dictionary.

    Both reports are the payloads produced by
    :func:`snc_report_content.build_individual_report`.
    Safety (Section 11) data is *not* consulted — the caller must not pass
    reports built with `include_safety=False` requirement; even if they do,
    Section 11 keys are ignored below.
    """
    cats_a = _cat_lookup((report_a or {}).get("category_summary", []))
    cats_b = _cat_lookup((report_b or {}).get("category_summary", []))

    all_ids: List[str] = []
    for key in list(cats_a.keys()) + list(cats_b.keys()):
        # Section 11 (safety) MUST never appear here.
        if key == "s11":
            continue
        if key not in all_ids:
            all_ids.append(key)

    buckets: Dict[str, List[str]] = {
        "agreement": [],
        "different_observations": [],
        "missing_information": [],
    }
    categories: List[Dict[str, Any]] = []

    for cid in all_ids:
        row_a = cats_a.get(cid)
        row_b = cats_b.get(cid)
        name = (row_a or row_b or {}).get("category") or (row_a or row_b or {}).get("name") or cid
        a_side = _side(row_a)
        b_side = _side(row_b)
        bucket = _bucket_for(a_side, b_side)
        buckets[bucket].append(cid)
        categories.append({
            "id": cid,
            "name": name,
            "a": a_side,
            "b": b_side,
            "bucket": bucket,
            "note": _neutral_note(cid, name, a_side, b_side, bucket),
        })

    professional_questions = _dedupe(
        (report_a or {}).get("questions_for_other_parent", [])
        + (report_b or {}).get("questions_for_other_parent", [])
    )

    coordination_a = ((report_a or {}).get("at_a_glance") or {}).get("coordination_areas") or []
    coordination_b = ((report_b or {}).get("at_a_glance") or {}).get("coordination_areas") or []
    coordination_areas = _dedupe(coordination_a + coordination_b)

    return {
        "generated_at": _iso_now(),
        "parents": {
            "a": {"name": parent_a_name or "Parent A"},
            "b": {"name": parent_b_name or "Parent B"},
        },
        "categories": categories,
        "buckets": {
            "agreement": buckets["agreement"],
            "different_observations": buckets["different_observations"],
            "missing_information": buckets["missing_information"],
            "professional_questions": professional_questions,
            "coordination_areas": coordination_areas,
        },
        "counts": {
            "total_categories": len(categories),
            "agreement": len(buckets["agreement"]),
            "different_observations": len(buckets["different_observations"]),
            "missing_information": len(buckets["missing_information"]),
        },
        "safety_notice": SAFETY_NOTICE,
        "disclaimer": DISCLAIMER,
    }
