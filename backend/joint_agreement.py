"""Joint Co-Parenting Agreement Draft — deterministic merger.

Given both parents' latest individual Co-Parenting Agreement drafts (as
stored in the `agreements` Mongo collection), produce a neutral,
side-by-side JOINT draft with three explicit buckets per section:

    Both proposed         — clauses that appear in BOTH parents' drafts
    (Parent A) only       — clauses only in caller's draft
    (Parent B) only       — clauses only in the co-parent's draft

The output is intentionally deterministic (no LLM) so tests can lock the
merge behaviour, and so parents get consistent output every time. It is
a *draft for discussion*, never a final agreement — the disclaimer says
so on every surface.

Design commitments (locked in tests):
  * Never labels either draft as "correct" or "better".
  * Never uses possession/custody/access-schedule language — the source
    drafts already avoid it, and we surface exactly what the parents
    wrote.
  * Both parents' actual wording appears verbatim on both sides of the
    side-by-side; the merger only classifies each clause into a bucket.

Public API:
  * `build_joint_agreement(...)` — pure function.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Disclaimer & neutral-language framing — surfaced in the payload + PDF.
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "This Joint Co-Parenting Agreement Draft is a DRAFT FOR DISCUSSION "
    "compiled from both parents' individual agreement drafts. It is not a "
    "signed agreement, a court order, a legal document, or a custody "
    "recommendation. Both parents remain responsible for reviewing each "
    "clause with their own professionals before adopting anything. The "
    "purpose of this document is to make it easy to see where the parents "
    "already converge, and where a mediator or attorney could help bridge "
    "the remaining gaps."
)

NEUTRAL_LANGUAGE_NOTE = (
    "The merger below never labels either parent's draft as correct or "
    "better. Where both parents proposed the same clause we say so; where "
    "only one parent proposed it, we surface the clause verbatim under "
    "that parent's column so the other parent can respond in their own "
    "words."
)

# Similarity threshold above which two strings are treated as the "same"
# clause. Kept generous — parents rarely phrase things identically, but
# we do not want to over-merge either.
_SIMILARITY_MATCH = 0.60


# ---------------------------------------------------------------------------
# Text normalisation + similarity helpers.
# ---------------------------------------------------------------------------

def _normalise(s: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace — for matching."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[\.,;:!\?\"'\-()\[\]]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _similar(a: str, b: str) -> float:
    na, nb = _normalise(a), _normalise(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _clause_text(item: Any) -> str:
    """Extract a single clause string from either a bare string, a
    {area, agreement} dict, or a {area, statement} dict."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("agreement", "statement", "clause", "text", "topic", "value"):
            v = item.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _clause_area(item: Any) -> str:
    if isinstance(item, dict):
        a = item.get("area") or item.get("category")
        if isinstance(a, str) and a.strip():
            return a.strip()
    return ""


# ---------------------------------------------------------------------------
# Bucket builder — the heart of the merger.
# ---------------------------------------------------------------------------

def _merge_lists(
    list_a: List[Any], list_b: List[Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (both, a_only, b_only) buckets from two clause lists.

    Both entries carry `{area, parent_a_text, parent_b_text}` so the UI
    can show them in a two-column strip. Solo entries carry
    `{area, text}` — the other parent's column is intentionally empty
    on the frontend/PDF.
    """
    matched_b: set = set()
    both: List[Dict[str, Any]] = []
    a_only: List[Dict[str, Any]] = []

    for a_item in list_a or []:
        a_text = _clause_text(a_item)
        if not a_text:
            continue
        best_j = -1
        best_score = 0.0
        for j, b_item in enumerate(list_b or []):
            if j in matched_b:
                continue
            b_text = _clause_text(b_item)
            score = _similar(a_text, b_text)
            if score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0 and best_score >= _SIMILARITY_MATCH:
            matched_b.add(best_j)
            b_item = list_b[best_j]
            both.append({
                "area": _clause_area(a_item) or _clause_area(b_item) or "",
                "parent_a_text": a_text,
                "parent_b_text": _clause_text(b_item),
                "similarity": round(best_score, 2),
            })
        else:
            a_only.append({
                "area": _clause_area(a_item),
                "text": a_text,
            })

    b_only: List[Dict[str, Any]] = []
    for j, b_item in enumerate(list_b or []):
        if j in matched_b:
            continue
        b_text = _clause_text(b_item)
        if not b_text:
            continue
        b_only.append({
            "area": _clause_area(b_item),
            "text": b_text,
        })

    return both, a_only, b_only


def _merge_section(
    a: Dict[str, Any], b: Dict[str, Any], key: str, title: str, description: str,
) -> Dict[str, Any]:
    """Merge one field-name across both agreements into a section block."""
    both, a_only, b_only = _merge_lists(a.get(key) or [], b.get(key) or [])
    return {
        "key": key,
        "title": title,
        "description": description,
        "both_proposed": both,
        "parent_a_only": a_only,
        "parent_b_only": b_only,
        "counts": {
            "both_proposed": len(both),
            "parent_a_only": len(a_only),
            "parent_b_only": len(b_only),
        },
    }


# ---------------------------------------------------------------------------
# Overall convergence summary — a single "here's where you already agree"
# headline the frontend can lead with.
# ---------------------------------------------------------------------------

def _convergence_summary(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_both = sum(s["counts"]["both_proposed"] for s in sections)
    total_a = sum(s["counts"]["parent_a_only"] for s in sections)
    total_b = sum(s["counts"]["parent_b_only"] for s in sections)
    total = max(1, total_both + total_a + total_b)
    return {
        "total_clauses":      total_both + total_a + total_b,
        "both_proposed":      total_both,
        "parent_a_only":      total_a,
        "parent_b_only":      total_b,
        "converged_pct":      round(total_both / total * 100),
    }


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def build_joint_agreement(
    *,
    share_id: str,
    parent_a_name: str,
    parent_b_name: str,
    agreement_a: Dict[str, Any],
    agreement_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge two individual agreement drafts into a joint draft.

    Sections merged (matches the fields the mediation_routes agreement
    generator persists today):
      * shared_goals            — child-centered goals both parents named
      * communication           — communication clauses
      * child_needs             — child-needs clauses
      * household_rules         — household-rules clauses
      * priority_items          — ranked priority topics
      * open_for_discussion     — topics each parent explicitly flagged
                                  as still-open. Rendered as PROPOSED
                                  topics rather than agreed clauses.
    """
    sections: List[Dict[str, Any]] = [
        _merge_section(
            agreement_a, agreement_b, "shared_goals",
            "Shared child-centered goals",
            "Goals for the child that appear in both parents' drafts vs. "
            "one only.",
        ),
        _merge_section(
            agreement_a, agreement_b, "communication",
            "Communication",
            "Clauses about how the parents plan to communicate about the "
            "child.",
        ),
        _merge_section(
            agreement_a, agreement_b, "child_needs",
            "Child's needs",
            "Clauses about the child's day-to-day needs and coordination "
            "between homes.",
        ),
        _merge_section(
            agreement_a, agreement_b, "household_rules",
            "Household rhythms & rules",
            "Clauses about household routines the parents want to keep "
            "aligned.",
        ),
        _merge_section(
            agreement_a, agreement_b, "priority_items",
            "Priority topics",
            "Topics each parent ranked as most important for the next "
            "conversation.",
        ),
        _merge_section(
            agreement_a, agreement_b, "open_for_discussion",
            "Still open for discussion",
            "Items each parent explicitly flagged as unresolved. Kept "
            "here so nothing is quietly dropped from the joint draft.",
        ),
    ]

    return {
        "report_type":         "joint_coparenting_agreement_draft",
        "report_title":        "Joint Co-Parenting Agreement Draft",
        "share_id":            share_id,
        "parent_a_name":       parent_a_name,
        "parent_b_name":       parent_b_name,
        "disclaimer":          DISCLAIMER,
        "neutral_language_note": NEUTRAL_LANGUAGE_NOTE,
        "not_a_final_agreement": True,
        "source_agreements": {
            "parent_a_agreement_id": agreement_a.get("agreement_id"),
            "parent_a_generated_at": agreement_a.get("generated_at"),
            "parent_b_agreement_id": agreement_b.get("agreement_id"),
            "parent_b_generated_at": agreement_b.get("generated_at"),
        },
        "sections":            sections,
        "summary":             _convergence_summary(sections),
        "closing_notes": {
            "parent_a": str(agreement_a.get("closing_note") or "").strip(),
            "parent_b": str(agreement_b.get("closing_note") or "").strip(),
        },
        "next_step": (
            "Bring this joint draft to your next mediation session. The "
            "'both proposed' clauses can be adopted quickly; the 'only "
            "one parent proposed' clauses are where the mediator's time "
            "will pay off most."
        ),
    }
