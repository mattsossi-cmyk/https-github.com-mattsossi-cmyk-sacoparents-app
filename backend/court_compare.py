"""Both-parent comparison on the Court page.

Two parents are compared only when they verified the same case code, BOTH opted in, and NEITHER is
safety-flagged (family-violence screen). Anything short of that looks the same to the other parent
("waiting"), so nothing about the co-parent's safety status or choices is revealed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from court_summary import CN_CATS, CN_NAMES, CP_SOURCE, SA_NAMES, SA_SOURCE, load_results
from self_assessment_reminders import is_safety_flagged

router = APIRouter(prefix="/court-path/compare", tags=["court-path"])
SHARES = "court_compare_shares"
SA_ALIGN_GAP = 15


class ShareBody(BaseModel):
    shared: bool


async def _case_key(db: AsyncIOMotorDatabase, uid: str) -> str:
    ps = await db.portal_state.find_one({"user_id": uid}, {"_id": 0, "court_key": 1}) or {}
    return (ps.get("court_key") or "").strip()


async def _is_sharing(db: AsyncIOMotorDatabase, uid: str, key: str) -> bool:
    doc = await db[SHARES].find_one({"user_id": uid}, {"_id": 0, "shared": 1, "court_key": 1})
    return bool(doc and doc.get("shared") and doc.get("court_key") == key)


async def _coparent(db: AsyncIOMotorDatabase, uid: str, key: str) -> Optional[str]:
    # Exactly one other parent on the case; anything else is ambiguous and never paired.
    others = await db.portal_state.find({"court_key": key, "user_id": {"$ne": uid}}, {"_id": 0, "user_id": 1}).to_list(2)
    return others[0]["user_id"] if len(others) == 1 else None


def _row(area: str, mine: str, theirs: str, source: str) -> Dict[str, str]:
    return {"area": area, "mine": mine, "theirs": theirs, "source": source}


def _compare_scores(me: tuple, them: tuple) -> Dict[str, List[Dict[str, str]]]:
    aligned: List[Dict[str, str]] = []
    different: List[Dict[str, str]] = []
    theirs_cp = {r["id"]: r for r in them[0]}
    for r in me[0]:
        o = theirs_cp.get(r["id"])
        if o:
            (aligned if r["rating"] == o["rating"] else different).append(_row(r["name"], r["rating"], o["rating"], CP_SOURCE))
    for key, pct in me[1].items():
        if key in them[1]:
            other = them[1][key]
            bucket = aligned if abs(pct - other) <= SA_ALIGN_GAP else different
            bucket.append(_row(SA_NAMES[key], f"{pct}%", f"{other}%", SA_SOURCE))
    return {"alignment": aligned, "difference": different}


def _answers(cn: Dict[str, Any], cat: str) -> Dict[str, str]:
    return {k: str(v).strip() for k, v in ((cn.get("answers") or {}).get(cat) or {}).items() if str(v or "").strip()}


def _compare_child(me: Dict[str, Any], them: Dict[str, Any]) -> List[Dict[str, Any]]:
    mine_all = {c["key"]: _answers(me, c["key"]) for c in CN_CATS}
    theirs_all = {c["key"]: _answers(them, c["key"]) for c in CN_CATS}
    if not any(mine_all.values()) or not any(theirs_all.values()):
        return []
    out = []
    for cat in CN_CATS:
        mine, theirs = mine_all[cat["key"]], theirs_all[cat["key"]]
        rows = [{"label": f["label"], "mine": mine.get(f["id"], ""), "theirs": theirs.get(f["id"], "")}
                for f in cat["fields"] if mine.get(f["id"]) or theirs.get(f["id"])]
        out.append({"category": CN_NAMES.get(cat["key"], cat["key"].title()), "rows": rows})
    return out


async def build_compare(db: AsyncIOMotorDatabase, uid: str) -> Dict[str, Any]:
    if await is_safety_flagged(db, uid):
        return {"state": "safety_off", "shared": False}
    key = await _case_key(db, uid)
    if not key:
        return {"state": "no_case", "shared": False}
    if not await _is_sharing(db, uid, key):
        return {"state": "not_shared", "shared": False}
    other = await _coparent(db, uid, key)
    if not other or not await _is_sharing(db, other, key) or await is_safety_flagged(db, other):
        return {"state": "waiting", "shared": True}
    me, them = await load_results(db, uid), await load_results(db, other)
    scores = _compare_scores(me, them)
    return {"state": "ready", "shared": True, **scores, "child": _compare_child(me[2], them[2])}


@router.get("")
async def get_compare(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    return await build_compare(db, user.user_id)


@router.post("/share")
async def set_share(
    body: ShareBody, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    if body.shared:
        if await is_safety_flagged(db, user.user_id):
            await db[SHARES].delete_one({"user_id": user.user_id})
            return {"state": "safety_off", "shared": False}
        key = await _case_key(db, user.user_id)
        if not key:
            raise HTTPException(status_code=400, detail="Enter your case code first.")
        await db[SHARES].update_one(
            {"user_id": user.user_id},
            {"$set": {"shared": True, "court_key": key, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    else:
        await db[SHARES].delete_one({"user_id": user.user_id})
    return await build_compare(db, user.user_id)
