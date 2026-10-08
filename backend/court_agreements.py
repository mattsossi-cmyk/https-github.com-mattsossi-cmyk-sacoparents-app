"""Agreement tracker for differing areas on the Court page comparison (shared per case)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

AGREEMENTS = "court_agreements"
CELEBRATIONS = "court_celebrations"
NOTE_MAX = 300
INTENT_NOTICE = (
    "By marking an area as agreed, the parties have evidenced their intent to make an agreement. "
    "This document does not reflect a binding agreement on the parties."
)


def area_key(row: Dict[str, str]) -> str:
    return f"{row['source']}|{row['area']}"


async def load_agreements(db: AsyncIOMotorDatabase, key: str) -> Dict[str, Dict[str, Any]]:
    docs = await db[AGREEMENTS].find({"court_key": key}, {"_id": 0}).to_list(200)
    return {d["area_key"]: d for d in docs if d.get("marked_by")}


def annotate(difference: List[Dict[str, str]], agreements: Dict[str, Dict[str, Any]], uid: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows = []
    for r in difference:
        a = agreements.get(area_key(r)) or {}
        by = a.get("marked_by") or []
        rows.append({**r, "key": area_key(r), "agreed": bool(by), "by_me": uid in by, "by_them": any(x != uid for x in by),
                     "note": a.get("note") or "", "agreed_at": a.get("agreed_at")})
    agreed = sum(1 for r in rows if r["agreed"])
    return rows, {"agreed": agreed, "total": len(rows), "all_agreed": bool(rows) and agreed == len(rows)}


async def set_mark(db: AsyncIOMotorDatabase, key: str, area: str, uid: str, agreed: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    match = {"court_key": key, "area_key": area}
    if agreed:
        await db[AGREEMENTS].update_one(
            match,
            {"$addToSet": {"marked_by": uid}, "$set": {"updated_at": now}, "$setOnInsert": {"note": "", "agreed_at": now}},
            upsert=True,
        )
        await db[AGREEMENTS].update_one({**match, "agreed_at": None}, {"$set": {"agreed_at": now}})
    else:
        # Only the parent's own mark is removed; the note is kept in case they agree again.
        await db[AGREEMENTS].update_one(match, {"$pull": {"marked_by": uid}, "$set": {"updated_at": now}})
        await db[AGREEMENTS].update_one({**match, "marked_by": {"$size": 0}}, {"$set": {"agreed_at": None}})


async def set_note(db: AsyncIOMotorDatabase, key: str, area: str, uid: str, note: str) -> bool:
    res = await db[AGREEMENTS].update_one(
        {"court_key": key, "area_key": area, "marked_by.0": {"$exists": True}},
        {"$set": {"note": " ".join(note.split())[:NOTE_MAX], "note_by": uid, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return res.matched_count > 0


async def is_celebrated(db: AsyncIOMotorDatabase, uid: str, key: str) -> bool:
    return bool(await db[CELEBRATIONS].find_one({"user_id": uid, "court_key": key}, {"_id": 1}))


async def mark_celebrated(db: AsyncIOMotorDatabase, uid: str, key: str) -> None:
    await db[CELEBRATIONS].update_one(
        {"user_id": uid, "court_key": key},
        {"$setOnInsert": {"celebrated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
