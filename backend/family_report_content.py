"""Deterministic Family Report content builder.

Stitches together whichever of these sources a parent has completed:
  - Co-Parenting Report (cp_reports)
  - Family Violence & Communication Safety (safety_assessments)

Special Needs Co-Parenting is being reworked and is intentionally not part
of the Family Report right now.
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
    1: "urgent",
    2: "elevated",
    3: "cautious",
    4: "steady",
}


def _embed_cp(cp_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not cp_doc or not cp_doc.get("report"):
        return None
    return {
        "framework": "10-section Co-Parenting Assessment",
        "generated_at": cp_doc.get("generated_at"),
        "report": cp_doc["report"],
    }


def _summarise_safety(sa_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not sa_doc:
        return None
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
        "recommendations": list(result.get("recommendations") or [])[:6],
    }


def _combined_next_steps(cp: Optional[Dict], safety: Optional[Dict]) -> List[Dict[str, str]]:
    """Interleave next-step items across sources, dedup, cap at 7."""
    out: List[Dict[str, str]] = []
    seen = set()

    def add(source: str, text: str):
        t = (text or "").strip()
        if not t or t in seen:
            return
        seen.add(t)
        out.append({"source": source, "text": t})

    if safety:
        for rec in safety.get("recommendations") or []:
            add("Safety", rec)
    cp_steps = list(((cp or {}).get("report") or {}).get("next_steps") or [])
    for step in cp_steps:
        add("Co-Parenting", step)
    return out[:7]


def _overall_paragraph(cp, safety, missing: List[str]) -> str:
    parts: List[str] = []
    if safety:
        parts.append(
            f"Your Family Violence & Communication Safety assessment placed your co-parenting "
            f"communication at Level {safety['level']} — {safety['pathway_title']}."
        )
    if cp:
        r = cp["report"]
        parts.append(
            f"Your Co-Parenting Assessment (10 sections) currently reflects {r.get('overall_rating')}."
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
    safety_doc: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cp = _embed_cp(cp_doc)
    safety = _summarise_safety(safety_doc)

    included: List[str] = []
    missing: List[str] = []
    (included if cp else missing).append("Co-Parenting Assessment")
    (included if safety else missing).append("Family Violence & Communication Safety")

    return {
        "prepared_by": (parent_name or "").strip() or None,
        "included_sources": included,
        "missing_sources": missing,
        "overall_summary": _overall_paragraph(cp, safety, missing),
        "coparenting": cp,
        "safety": safety,
        "combined_next_steps": _combined_next_steps(cp, safety),
        "disclaimer": DEFAULT_DISCLAIMER,
    }
