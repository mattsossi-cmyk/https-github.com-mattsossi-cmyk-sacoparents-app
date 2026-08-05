"""Shared deep-dive co-parent comparison core.

The Educational, Psychological, and Medical Deep Dives all share the same
question schema shape (`DEEP_DIVE_SECTIONS` with items of type likert /
single / multi / text). This module holds the pathway-agnostic alignment
logic so each pathway is a ~15-line wrapper.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


ALIGNMENT_LABELS = {
    "aligned":        "Aligned",
    "close":          "Close alignment",
    "divergent":      "Different views",
    "both_responded": "Both responded",
    "one_only":       "One parent responded",
    "insufficient":   "Not enough data",
}


def _norm_multi(value: Any) -> List[str]:
    if isinstance(value, list):
        return sorted({str(v).strip() for v in value if str(v).strip()})
    return []


def _jaccard(a: List[str], b: List[str]) -> Optional[float]:
    aset, bset = set(a), set(b)
    if not aset and not bset:
        return None
    union = aset | bset
    return len(aset & bset) / len(union) if union else None


def _compare_likert(a: Any, b: Any) -> Dict[str, Any]:
    a_num = a if isinstance(a, int) and 1 <= a <= 5 else None
    b_num = b if isinstance(b, int) and 1 <= b <= 5 else None
    out: Dict[str, Any] = {"parent_a": {"value": a}, "parent_b": {"value": b}}
    if a_num is None or b_num is None:
        out["alignment"] = "insufficient"
        out["gap"] = None
        return out
    gap = abs(a_num - b_num)
    out["gap"] = gap
    out["alignment"] = "aligned" if gap <= 1 else ("close" if gap == 2 else "divergent")
    return out


def _compare_single(a: Any, b: Any) -> Dict[str, Any]:
    a_v = a if isinstance(a, str) and a.strip() else None
    b_v = b if isinstance(b, str) and b.strip() else None
    out: Dict[str, Any] = {"parent_a": {"value": a_v}, "parent_b": {"value": b_v}}
    if a_v is None or b_v is None:
        out["alignment"] = "insufficient" if (a_v is None and b_v is None) else "one_only"
        return out
    out["alignment"] = "aligned" if a_v == b_v else "divergent"
    return out


def _compare_multi(a: Any, b: Any) -> Dict[str, Any]:
    a_list = _norm_multi(a)
    b_list = _norm_multi(b)
    both = sorted(set(a_list) & set(b_list))
    only_a = sorted(set(a_list) - set(b_list))
    only_b = sorted(set(b_list) - set(a_list))
    out: Dict[str, Any] = {
        "parent_a": {"value": a_list},
        "parent_b": {"value": b_list},
        "both": both,
        "only_parent_a": only_a,
        "only_parent_b": only_b,
    }
    j = _jaccard(a_list, b_list)
    if j is None:
        out["alignment"] = "insufficient"
        out["overlap"] = None
        return out
    out["overlap"] = round(j, 2)
    out["alignment"] = "aligned" if j >= 0.66 else ("close" if j >= 0.33 else "divergent")
    return out


def _compare_text(a: Any, b: Any) -> Dict[str, Any]:
    a_v = (a or "").strip() if isinstance(a, str) else ""
    b_v = (b or "").strip() if isinstance(b, str) else ""
    out: Dict[str, Any] = {"parent_a": {"value": a_v}, "parent_b": {"value": b_v}}
    if a_v and b_v:
        out["alignment"] = "both_responded"
    elif a_v or b_v:
        out["alignment"] = "one_only"
    else:
        out["alignment"] = "insufficient"
    return out


def _is_numeric_type(t: Any) -> bool:
    """v1 used "likert" (1-5); v2 uses "alignment" (0-4). Both are numeric
    scales and share the same compare semantics."""
    return t in ("likert", "alignment")


def _compare_item(spec: Dict[str, Any], iid: str, a_val: Any, b_val: Any) -> Dict[str, Any]:
    t = spec.get("type")
    if _is_numeric_type(t):
        cmp = _compare_likert(a_val, b_val)
    elif t == "single":
        cmp = _compare_single(a_val, b_val)
    elif t == "multi":
        cmp = _compare_multi(a_val, b_val)
    else:
        cmp = _compare_text(a_val, b_val)
    return {"id": iid, "type": t, "prompt": spec.get("prompt", ""), **cmp}


def _summary(all_alignments: List[str]) -> Dict[str, Any]:
    counts = {k: 0 for k in ALIGNMENT_LABELS.keys()}
    for a in all_alignments:
        counts[a] = counts.get(a, 0) + 1
    total = len(all_alignments) or 1
    aligned = counts.get("aligned", 0) + counts.get("both_responded", 0)
    diverging = counts.get("divergent", 0)
    return {
        "total_items": len(all_alignments),
        "aligned_pct":   round(aligned / total * 100),
        "divergent_pct": round(diverging / total * 100),
        "counts": counts,
    }


def _highlight_score(section_num: int, item: Dict[str, Any]) -> Optional[float]:
    t = item.get("type")
    align = item.get("alignment")
    if align in {"divergent", "insufficient", "one_only"}:
        return None
    weight = 1.0 + section_num * 0.05
    if _is_numeric_type(t):
        a = (item.get("parent_a") or {}).get("value")
        b = (item.get("parent_b") or {}).get("value")
        if not (isinstance(a, int) and isinstance(b, int)):
            return None
        avg = (a + b) / 2
        gap = abs(a - b)
        if avg < 3.0 or gap > 1:
            return None
        return weight * (4.0 + avg - gap * 0.5)
    if t == "multi":
        overlap = item.get("overlap") or 0
        both = item.get("both") or []
        if not both:
            return None
        return weight * (2.5 + overlap * 3.0 + min(len(both), 3) * 0.3)
    if t == "single":
        return weight * 3.0 if align == "aligned" else None
    if align == "both_responded":
        return weight * 1.5
    return None


def _extract_highlights(sections: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for sec in sections:
        for item in sec.get("items") or []:
            score = _highlight_score(sec.get("number") or 0, item)
            if score is None:
                continue
            scored.append({"score": score, "section": sec, "item": item})
    scored.sort(key=lambda x: x["score"], reverse=True)

    highlights: List[Dict[str, Any]] = []
    for row in scored[:limit]:
        item = row["item"]
        h: Dict[str, Any] = {
            "section_id":     row["section"]["id"],
            "section_number": row["section"]["number"],
            "section_name":   row["section"]["name"],
            "item_id":        item["id"],
            "prompt":         item.get("prompt", ""),
            "alignment":      item.get("alignment"),
            "type":           item.get("type"),
        }
        t = item.get("type")
        if _is_numeric_type(t):
            a = (item.get("parent_a") or {}).get("value")
            b = (item.get("parent_b") or {}).get("value")
            h["parent_a_value"] = a
            h["parent_b_value"] = b
            h["gap"] = item.get("gap")
            avg = (a + b) / 2 if isinstance(a, int) and isinstance(b, int) else None
            h["summary"] = (
                f"Both scored this a strong {min(a, b)}-{max(a, b)}."
                if avg and avg >= 4
                else "Both are broadly aligned here."
            )
        elif t == "multi":
            h["both"] = item.get("both") or []
            h["summary"] = "You both chose: " + ", ".join(h["both"][:4])
        elif t == "single":
            h["value"] = (item.get("parent_a") or {}).get("value")
            h["summary"] = f"You both chose \"{h['value']}\"."
        else:
            h["summary"] = "You both took the time to describe this in your own words."
        highlights.append(h)
    return highlights


def _row(section: Dict[str, Any], item: Dict[str, Any], extras: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "section_id":     section["id"],
        "section_number": section["number"],
        "section_name":   section["name"],
        "item_id":        item["id"],
        "prompt":         item.get("prompt", ""),
        "type":           item.get("type"),
        "alignment":      item.get("alignment"),
        **extras,
    }


def _extract_alignment_lists(sections: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Turn the raw section-by-section comparison into three mediation-ready lists:

    - shared_priorities: what BOTH parents already flagged as important
    - discussion_points: close-but-not-identical items that would benefit from a chat
    - mediation_questions: genuinely divergent items, presented as neutral questions
      (never labelled 'right' vs 'wrong')
    """
    shared: List[Dict[str, Any]] = []
    discuss: List[Dict[str, Any]] = []
    mediate: List[Dict[str, Any]] = []
    for sec in sections:
        for item in sec.get("items") or []:
            t = item.get("type")
            align = item.get("alignment")
            a = (item.get("parent_a") or {}).get("value")
            b = (item.get("parent_b") or {}).get("value")

            # --- Shared priorities: both explicitly flagged this as important ---
            if _is_numeric_type(t) and isinstance(a, int) and isinstance(b, int) and a >= 4 and b >= 4:
                shared.append(_row(sec, item, {
                    "parent_a_value": a,
                    "parent_b_value": b,
                    "reason": (
                        f"Both scored this a {min(a, b)}-{max(a, b)} — clear shared priority."
                    ),
                }))
            elif t == "multi":
                both = item.get("both") or []
                if len(both) >= 2:
                    shared.append(_row(sec, item, {
                        "both": both,
                        "reason": "You both selected " + ", ".join(both[:4])
                                  + (f" (+{len(both) - 4} more)" if len(both) > 4 else "") + ".",
                    }))

            # --- Points for discussion: near-alignment, worth syncing on ---
            if align == "close":
                if _is_numeric_type(t) and isinstance(a, int) and isinstance(b, int):
                    discuss.append(_row(sec, item, {
                        "parent_a_value": a,
                        "parent_b_value": b,
                        "gap": item.get("gap"),
                        "reason": f"Close alignment ({a} vs {b}) — a short conversation likely closes the gap.",
                    }))
                elif t == "multi":
                    discuss.append(_row(sec, item, {
                        "both": item.get("both") or [],
                        "only_parent_a": item.get("only_parent_a") or [],
                        "only_parent_b": item.get("only_parent_b") or [],
                        "reason": "You picked mostly overlapping options — worth checking why the different picks landed differently.",
                    }))
            elif align == "one_only":
                discuss.append(_row(sec, item, {
                    "parent_a_value": a,
                    "parent_b_value": b,
                    "reason": "Only one parent shared their view — the other's perspective would help complete the picture.",
                }))

            # --- Questions for mediation: divergent items, neutralized as questions ---
            if align == "divergent":
                if _is_numeric_type(t) and isinstance(a, int) and isinstance(b, int):
                    q_row = _row(sec, item, {
                        "parent_a_value": a,
                        "parent_b_value": b,
                        "gap": item.get("gap"),
                        "question": f"How will we align on: {item.get('prompt', '')}",
                    })
                elif t == "single":
                    q_row = _row(sec, item, {
                        "parent_a_value": a,
                        "parent_b_value": b,
                        "question": f"You chose different answers to: {item.get('prompt', '')} How do we reconcile that?",
                    })
                elif t == "multi":
                    q_row = _row(sec, item, {
                        "only_parent_a": item.get("only_parent_a") or [],
                        "only_parent_b": item.get("only_parent_b") or [],
                        "both": item.get("both") or [],
                        "question": f"Which of these options do we both commit to on: {item.get('prompt', '')}",
                    })
                else:
                    continue
                mediate.append(q_row)

    # Cap each list at 8 items so the report stays scannable.
    return {
        "shared_priorities": shared[:8],
        "discussion_points": discuss[:8],
        "mediation_questions": mediate[:8],
    }


def build_comparison_from_spec(
    *,
    sections_spec: List[Dict[str, Any]],
    assessment_version: str,
    product_name: str,
    parent_a_name: str,
    parent_b_name: str,
    a_answers: Dict[str, Any],
    b_answers: Dict[str, Any],
) -> Dict[str, Any]:
    """Return the full neutral comparison payload for a deep-dive pathway."""
    all_alignments: List[str] = []
    sections_out: List[Dict[str, Any]] = []
    for sec in sections_spec:
        items_out: List[Dict[str, Any]] = []
        for iid, spec in sec["items"].items():
            key = f"{sec['id']}_{iid}"
            a_val = a_answers.get(key)
            b_val = b_answers.get(key)
            if a_val in (None, "", [], {}) and b_val in (None, "", [], {}):
                continue
            cmp = _compare_item(spec, iid, a_val, b_val)
            items_out.append(cmp)
            all_alignments.append(cmp["alignment"])
        if not items_out:
            continue
        sections_out.append({
            "id": sec["id"],
            "number": sec["number"],
            "name": sec["name"],
            "purpose": sec.get("purpose"),
            "items": items_out,
        })

    alignment_lists = _extract_alignment_lists(sections_out)

    return {
        "assessment_version": assessment_version,
        "product_name": product_name,
        "parent_a_name": parent_a_name,
        "parent_b_name": parent_b_name,
        "sections": sections_out,
        "summary": _summary(all_alignments),
        "highlights": _extract_highlights(sections_out, limit=5),
        "shared_priorities":   alignment_lists["shared_priorities"],
        "discussion_points":   alignment_lists["discussion_points"],
        "mediation_questions": alignment_lists["mediation_questions"],
        "alignment_labels": ALIGNMENT_LABELS,
    }
