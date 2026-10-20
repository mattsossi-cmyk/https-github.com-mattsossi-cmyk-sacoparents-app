"""Reminder emails held back because of an old safety result: counts only. No name, email or user id is stored."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from auth import JWT_SECRET

COLL = "safety_held_emails"
SMALL = 5
KINDS = {
    "reassess": "Self-Assessment reassess reminder",
    "weekly_note": "Self Journey weekly note",
    "requested": "Requested-steps reminder",
    "pro_nudge": "Professional nudge",
    "compare_alert": "Court page comparison alert",
    "draft_nudge": "Unfinished-draft reminder",
}


def week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


async def record_held(db, kind: str, user_id: str, period: str) -> None:
    """One row per email that would have gone out; later sweeps for the same email add nothing."""
    key = hmac.new(JWT_SECRET.encode(), f"{kind}|{user_id}|{period}".encode(), hashlib.sha256).hexdigest()
    await db[COLL].update_one({"_id": key}, {"$setOnInsert": {"kind": kind, "at": datetime.now(timezone.utc).isoformat()}},
                              upsert=True)


def _cell(n: int) -> Dict[str, Any]:
    return {"count": None, "fewer_than_5": True} if 0 < n < SMALL else {"count": n, "fewer_than_5": False}


async def held_counts(db, days: int = 30) -> Dict[str, Any]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = db[COLL].aggregate([{"$match": {"at": {"$gte": since}}}, {"$group": {"_id": "$kind", "n": {"$sum": 1}}}])
    raw = {r["_id"]: r["n"] async for r in rows}
    return {"days": days, "total": _cell(sum(raw.values())),
            "kinds": [{"kind": k, "label": label, **_cell(raw.get(k, 0))} for k, label in KINDS.items()]}
