"""Deterministic Family Report content builder.

Stitches together whichever of these three assessments a parent has completed:
  - Co-Parenting (cp_reports)
  - Special Needs v3 (sn_v3_reports)
  - Family Violence & Communication Safety (safety_assessments)

Design principles:
  * If none are completed → the caller should return 404. This builder assumes
    at least one source is present.
  * Missing sources are noted, not fabricated. The report is honest about
    what's included.
  * Safety data is intentionally summarised (level + pathway + top
    recommendations only) — question-level hits and coercive-control flags
    are NEVER included in the composed report, since Family Reports are
    designed to be shared with mediators / attorneys / co-parents.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_DISCLAIMER = (
    "This Family Report is an educational reflection tool from SA CoParents. "
    "It is not a diagnosis, custody evaluation, or legal advice. Findings are "
    "based on the parent's own self-assessment answers. Safety findings do not "
    "include identifying question-level detail; they only reflect the overall "
    "communication pathway level."
)


_SAFETY_TONE = {
    1: "urgent",     # High concern
    2: "elevated",   # Structured written communication only
    3: "cautious",   # Written channel recommended
    4: "steady",     # Direct communication currently workable
}


def _summarise_cp(cp_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not cp_doc or not cp_doc.get("report"):
        return None
    r = cp_doc["report"]
    return {
        "framework": "10-section Co-Parenting Assessment",
        "generated_at": cp_doc.get("generated_at"),
        "overall_rating": r.get("overall_rating"),
        "overall_summary": r.get("overall_summary"),
        "strengths": r.get("strengths") or [],
        "growth_areas": r.get("growth_areas") or [],
        "show_communication_toolkit": bool(r.get("show_communication_toolkit")),
        "next_steps": r.get("next_steps") or [],
    }


def _summarise_sn(sn_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not sn_doc or not sn_doc.get("report"):
        return None
    r = sn_doc["report"]
    return {
        "framework": "10-principle Special Needs Assessment",
        "generated_at": sn_doc.get("generated_at"),
        "overall_rating": r.get("overall_rating"),
        "overall_summary": r.get("overall_summary"),
        "strengths": r.get("strengths") or [],
        "growth_areas": r.get("growth_areas") or [],
        "show_communication_toolkit": bool(r.get("show_communication_toolkit")),
        "next_steps": r.get("next_steps") or [],
    }


def _summarise_safety(sa_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract the SHAREABLE summary from a raw safety_assessments doc.

    Deliberately drops:
      - section_1 / section_2 raw answers
      - high_concern_hits / coercive_hits (identifiers of specific behaviours)
      - counts (section_1_yes_count / section_2_concern_count)
    """
    if not sa_doc:
        return None
    # The submit_assessment endpoint stores the scored fields nested under
    # `result`. The unit tests pass a pre-flattened dict. Support both.
    result = sa_doc.get("result") or sa_doc
    level = result.get("level")
    if level is None:
        return None
    return {
        "framework": "Family Violence & Communication Safety",
        "generated_at": sa_doc.get("created_at") or sa_doc.get("updated_at"),
        "level": level,
        "tone": _SAFETY_TONE.get(level, "steady"),
        "pathway_title": result.get("pathway_title") or "",
        "pathway_headline": result.get("pathway_headline") or "",
        "pathway_summary": result.get("pathway_summary") or "",
        "recommendations": list(result.get("recommendations") or [])[:5],
    }


def _combined_next_steps(cp: Optional[Dict[str, Any]], sn: Optional[Dict[str, Any]], safety: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Interleave next-step items across sources, dedup, cap at 7.
    Each entry carries a `source` tag so the frontend/PDF can label origin."""
    out: List[Dict[str, str]] = []
    seen = set()

    def add(source: str, text: str):
        t = (text or "").strip()
        if not t or t in seen:
            return
        seen.add(t)
        out.append({"source": source, "text": t})

    # Prioritise safety recommendations first — safety-first framing.
    if safety:
        for rec in safety.get("recommendations") or []:
            add("Safety", rec)
    # Then interleave the two 10-item reports.
    cp_steps = list((cp or {}).get("next_steps") or [])
    sn_steps = list((sn or {}).get("next_steps") or [])
    for i in range(max(len(cp_steps), len(sn_steps))):
        if i < len(cp_steps):
            add("Co-Parenting", cp_steps[i])
        if i < len(sn_steps):
            add("Special Needs", sn_steps[i])
    return out[:7]


def _overall_paragraph(cp, sn, safety, missing: List[str]) -> str:
    parts: List[str] = []
    if safety:
        parts.append(
            f"Your Family Violence & Communication Safety assessment placed your co-parenting "
            f"communication at Level {safety['level']} — {safety['pathway_title']}."
        )
    if cp:
        parts.append(
            f"Your Co-Parenting Assessment (10 sections) currently reflects "
            f"{cp['overall_rating']}."
        )
    if sn:
        parts.append(
            f"Your Special Needs Assessment (10 principles) currently reflects "
            f"{sn['overall_rating']}."
        )
    if missing:
        parts.append(
            "Missing from this report: " + ", ".join(missing) +
            ". Completing the remaining assessments will produce a fuller picture."
        )
    return " ".join(parts)


def build_family_report(
    *,
    parent_name: Optional[str],
    cp_doc: Optional[Dict[str, Any]] = None,
    sn_doc: Optional[Dict[str, Any]] = None,
    safety_doc: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cp = _summarise_cp(cp_doc)
    sn = _summarise_sn(sn_doc)
    safety = _summarise_safety(safety_doc)

    included: List[str] = []
    missing: List[str] = []
    (included if cp else missing).append("Co-Parenting Assessment")
    (included if sn else missing).append("Special Needs Assessment")
    (included if safety else missing).append("Family Violence & Communication Safety")

    return {
        "prepared_by": (parent_name or "").strip() or None,
        "included_sources": included,
        "missing_sources": missing,
        "overall_summary": _overall_paragraph(cp, sn, safety, missing),
        "coparenting": cp,
        "special_needs": sn,
        "safety": safety,
        "combined_next_steps": _combined_next_steps(cp, sn, safety),
        "disclaimer": DEFAULT_DISCLAIMER,
    }
