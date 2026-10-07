"""Opt-in extras for the Mediator Progress Snapshot PDF.

Both are OFF unless the parent explicitly ticks them at export/share time:
the grey-rock timeline reveals safety-mode use, and BIFF pairs include the
parent's original (unedited) messages.
"""
from __future__ import annotations

from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

SOURCE_LABELS = {
    "safety_screen": "Safety screen",
    "toggle_chip": "Grey-Rock chip",
    "import": "Imported",
}


async def load_grey_rock_timeline(db: AsyncIOMotorDatabase, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = await db.grey_rock_audit.find(
        {"user_id": user_id}, {"_id": 0, "event": 1, "source": 1, "at": 1}
    ).sort("at", -1).to_list(limit)
    return [
        {"at": r.get("at"), "event": r.get("event"), "source": SOURCE_LABELS.get(r.get("source"), r.get("source") or "")}
        for r in reversed(rows)
    ]


async def load_biff_pairs(db: AsyncIOMotorDatabase, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    doc = await db.portal_state.find_one({"user_id": user_id}, {"_id": 0, "snapshot_history": 1})
    items = [s for s in ((doc or {}).get("snapshot_history") or []) if s.get("topic") == "biff_pair"]
    items.sort(key=lambda s: s.get("saved_at") or "", reverse=True)
    out = []
    for s in items[:limit]:
        answers = s.get("answers") or []
        original = (answers[0].get("answer") if len(answers) > 0 else "") or ""
        rewrite = (answers[1].get("answer") if len(answers) > 1 else "") or ""
        if original or rewrite:
            out.append({"saved_at": s.get("saved_at"), "original": original, "rewrite": rewrite})
    return out
