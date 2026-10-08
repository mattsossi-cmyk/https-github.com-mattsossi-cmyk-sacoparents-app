"""Court page summary pillars, built only from this parent's own results (no two-parent comparison yet)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

_HERE = Path(__file__).parent
SA_NAMES = {s["key"]: s["title"] for s in json.loads((_HERE / "self_assessment_content.json").read_text())["sections"]}
CN_CATS = json.loads((_HERE / "child_needs_content.json").read_text())["categories"]
CN_NAMES = {"medical": "Medical", "educational": "Educational", "psychological": "Psychological"}
CP_SOURCE, SA_SOURCE = "Co-Parenting Relationship", "Self-Assessment"


def _item(text: str, meta: str, source: str) -> Dict[str, str]:
    return {"text": text, "meta": meta, "source": source}


def _cp_rows(cp: Dict[str, Any]) -> List[Dict[str, Any]]:
    snaps = sorted((s for s in cp.get("snapshots") or [] if s.get("submitted_at")), key=lambda s: s["submitted_at"])
    rows = [r for r in (snaps[-1].get("section_avgs") or []) if r.get("avg") is not None] if snaps else []
    return sorted(rows, key=lambda r: r["avg"], reverse=True)


def _sa_rows(sa: Dict[str, Any]) -> List[tuple]:
    sections = ((sa or {}).get("scores") or {}).get("sections") or {}
    return sorted(((SA_NAMES.get(k, k), v) for k, v in sections.items() if k in SA_NAMES), key=lambda r: r[1], reverse=True)


async def build_summary(db: AsyncIOMotorDatabase, uid: str) -> Dict[str, Any]:
    sa = await db.self_assessment_history.find_one({"user_id": uid}, {"_id": 0, "scores": 1}, sort=[("completed_at", -1)])
    cp = await db.cp_report_history.find_one({"_id": uid}, {"snapshots": 1}) or {}
    cn = await db.child_needs_assessments.find_one({"user_id": uid}, {"_id": 0, "answers": 1, "completed_at": 1}) or {}

    cp_rows, sa_rows = _cp_rows(cp), _sa_rows(sa)
    top_cp = cp_rows[:3]
    low_cp = [r for r in cp_rows[::-1] if r not in top_cp][:2]
    alignment = [_item(r["name"], r["rating"], CP_SOURCE) for r in top_cp]
    difference = [_item(r["name"], r["rating"], CP_SOURCE) for r in low_cp]
    if sa_rows:
        alignment.append(_item(sa_rows[0][0], f"{sa_rows[0][1]}%", SA_SOURCE))
        if len(sa_rows) > 1:
            difference.append(_item(sa_rows[-1][0], f"{sa_rows[-1][1]}%", SA_SOURCE))

    child = []
    for cat in CN_CATS:
        answers = (cn.get("answers") or {}).get(cat["key"]) or {}
        filled = sum(1 for f in cat["fields"] if str(answers.get(f["id"]) or "").strip())
        done = bool((cn.get("completed_at") or {}).get(cat["key"]))
        status = "Completed" if done else "In progress" if filled else "Not started"
        child.append(_item(CN_NAMES.get(cat["key"], cat["key"].title()), f"{filled} of {len(cat['fields'])} noted · {status}", "Child Needs"))

    return {
        "alignment": alignment,
        "difference": difference,
        "child": child,
        "has_cp": bool(cp_rows),
        "has_sa": bool(sa_rows),
        "has_child": any(not c["meta"].endswith("Not started") for c in child),
    }
