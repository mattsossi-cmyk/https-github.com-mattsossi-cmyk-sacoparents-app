"""Special Needs Co-Parenting v2 — neutral side-by-side comparison builder.

Turns two independently-completed SNC v2 assessments into a **neutral**
step-by-step comparison. The output never labels either parent as correct,
wrong, better, or worse — it only reports the alignment between their answers.

Alignment rules:
  * likert (1-5)   — same value or 1-point gap = "aligned"; 2 points = "close";
                     3+ points = "divergent"; missing/N/A = "insufficient".
  * single choice  — same option = "aligned"; different = "divergent".
  * multi choice   — Jaccard overlap >= 0.66 = "aligned"; >= 0.33 = "close";
                     less than that = "divergent"; both empty = "insufficient".
  * text/textarea  — both provided text = "both_responded"; one only =
                     "one_only"; neither = "insufficient". Text content is
                     shown side-by-side (both parents consented).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from snc2_questions import (
    ASSESSMENT_VERSION, PATHWAYS, RESPONSE_SCALE, _TEMPLATE, _apply_pathway,
    qid, resolve_pathways,
)


ALIGNMENT_LABELS = {
    "aligned":        "Aligned",
    "close":          "Close alignment",
    "divergent":      "Different views",
    "both_responded": "Both responded",
    "one_only":       "One parent responded",
    "insufficient":   "Not enough data",
}


def _likert_label(value: Any) -> Optional[str]:
    for row in RESPONSE_SCALE:
        if row["value"] == value:
            return row["label"]
    return None


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
    out: Dict[str, Any] = {
        "parent_a": {"value": a, "label": _likert_label(a)},
        "parent_b": {"value": b, "label": _likert_label(b)},
    }
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


def _compare_item(item: Dict[str, Any], a_val: Any, b_val: Any) -> Dict[str, Any]:
    t = item.get("type")
    if t == "likert":
        cmp = _compare_likert(a_val, b_val)
    elif t == "single":
        cmp = _compare_single(a_val, b_val)
    elif t == "multi":
        cmp = _compare_multi(a_val, b_val)
    else:
        cmp = _compare_text(a_val, b_val)
    return {
        "id": item["id"],
        "type": t,
        "prompt": item.get("prompt", ""),
        **cmp,
    }


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


def build_comparison(
    *,
    parent_a_name: str,
    parent_b_name: str,
    a_pathways: List[str],
    b_pathways: List[str],
    a_answers: Dict[str, Any],
    b_answers: Dict[str, Any],
    category_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the full neutral comparison payload.

    `category_filter`, when set to one of the pathway ids ("medical",
    "educational", "psychological"), restricts the comparison to just that
    pathway. When None, all shared pathways are included.
    """
    a_res = resolve_pathways(a_pathways)
    b_res = resolve_pathways(b_pathways)
    shared = [p for p in a_res if p in b_res]
    if category_filter:
        if category_filter not in {"medical", "educational", "psychological"}:
            raise ValueError(f"Unknown category filter: {category_filter}")
        if category_filter not in shared:
            raise ValueError(f"Neither parent selected the {category_filter} pathway.")
        shared = [category_filter]

    only_parent_a = [p for p in a_res if p not in b_res]
    only_parent_b = [p for p in b_res if p not in a_res]

    all_alignments: List[str] = []
    steps: List[Dict[str, Any]] = []
    for step in _TEMPLATE:
        block = {
            "id": step["id"],
            "number": step["number"],
            "name": step["name"],
            "pathways": [],
        }
        for pid in shared:
            resolved = [_apply_pathway(it, pid) for it in step["items"]]
            items_out: List[Dict[str, Any]] = []
            for item in resolved:
                key = qid(step["id"], pid, item["id"])
                a_val = a_answers.get(key)
                b_val = b_answers.get(key)
                cmp = _compare_item(item, a_val, b_val)
                items_out.append(cmp)
                all_alignments.append(cmp["alignment"])
            block["pathways"].append({
                "id": pid,
                "name": next(p["name"] for p in PATHWAYS if p["id"] == pid),
                "items": items_out,
            })
        steps.append(block)

    return {
        "assessment_version": ASSESSMENT_VERSION,
        "parent_a_name": parent_a_name,
        "parent_b_name": parent_b_name,
        "category_filter": category_filter,
        "shared_pathways": shared,
        "only_parent_a_pathways": only_parent_a,
        "only_parent_b_pathways": only_parent_b,
        "steps": steps,
        "summary": _summary(all_alignments),
        "alignment_labels": ALIGNMENT_LABELS,
    }
