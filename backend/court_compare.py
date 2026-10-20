"""Both-parent comparison on the Court page.

Two parents are compared only when they verified the same case code, BOTH opted in, and NEITHER is
safety-flagged (family-violence screen). Anything short of that looks the same to the other parent
("waiting"), so nothing about the co-parent's safety status or choices is revealed.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from ai_notice_routes import require_ai_notice
from court_agreements import INTENT_NOTICE, annotate, is_celebrated, load_agreements, mark_celebrated, set_mark, set_note
from court_agreement_alerts import queue_alert
from court_compare_alerts import notify_share
from court_compare_pdf import build_compare_pdf
from court_summary import CN_CATS, CN_NAMES, CP_SOURCE, SA_NAMES, SA_SOURCE, load_results
from self_assessment_ai import _ask, _guard
from self_assessment_reminders import is_safety_flagged

router = APIRouter(prefix="/court-path/compare", tags=["court-path"])
SHARES = "court_compare_shares"
POINTS = "court_talking_points"
SA_ALIGN_GAP = 15
MAX_POINTS = 8
_POINTS_TASK = (
    "You help two separated parents start calm, child-focused conversations about areas where their own ratings "
    "differ. For EACH area listed, write ONE short conversation opener (max 35 words) that either parent could say "
    "or that both could read together: neutral 'we' and 'our child' language, curious not blaming, never suggesting "
    "who is right, no legal advice, no diagnosis. Return ONLY a JSON array of objects with keys \"area\" (exactly "
    "as given) and \"text\", in the same order. No markdown."
)


class ShareBody(BaseModel):
    shared: bool


class AgreeBody(BaseModel):
    area: str = Field(..., min_length=3, max_length=200)
    agreed: bool


class NoteBody(BaseModel):
    area: str = Field(..., min_length=3, max_length=200)
    note: str = Field("", max_length=600)


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


async def _resolve(db: AsyncIOMotorDatabase, uid: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """(base state, case key, co-parent id only when the comparison is ready)."""
    if await is_safety_flagged(db, uid):
        return {"state": "not_available", "shared": False}, "", None
    key = await _case_key(db, uid)
    if not key:
        return {"state": "no_case", "shared": False}, "", None
    if not await _is_sharing(db, uid, key):
        return {"state": "not_shared", "shared": False}, key, None
    other = await _coparent(db, uid, key)
    if not other or not await _is_sharing(db, other, key) or await is_safety_flagged(db, other):
        return {"state": "waiting", "shared": True}, key, None
    return {"state": "ready", "shared": True}, key, other


def _basis(difference: List[Dict[str, str]]) -> str:
    # Same for both parents (order-free), so saved talking points are shared and go stale when answers change.
    rows = sorted(f"{r['source']}|{r['area']}|{'/'.join(sorted((r['mine'], r['theirs'])))}" for r in difference)
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


async def _ready_data(db: AsyncIOMotorDatabase, uid: str, key: str, other: str) -> Dict[str, Any]:
    me, them = await load_results(db, uid), await load_results(db, other)
    scores = _compare_scores(me, them)
    saved = await db[POINTS].find_one({"court_key": key}, {"_id": 0})
    points = None
    if saved:
        points = {"items": saved["items"], "generated_at": saved["generated_at"], "stale": saved["basis"] != _basis(scores["difference"])}
    difference, progress = annotate(scores["difference"], await load_agreements(db, key), uid)
    progress["celebrated"] = await is_celebrated(db, uid, key)
    return {**scores, "difference": difference, "progress": progress, "intent_notice": INTENT_NOTICE,
            "child": _compare_child(me[2], them[2]), "talking_points": points}


async def build_compare(db: AsyncIOMotorDatabase, uid: str) -> Dict[str, Any]:
    base, key, other = await _resolve(db, uid)
    return {**base, **(await _ready_data(db, uid, key, other))} if other else base


async def _ready_or_409(db: AsyncIOMotorDatabase, uid: str) -> Tuple[str, str, Dict[str, Any]]:
    base, key, other = await _resolve(db, uid)
    if not other:
        raise HTTPException(status_code=409, detail="This is available once both parents are sharing.")
    return key, other, await _ready_data(db, uid, key, other)


@router.get("")
async def get_compare(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    return await build_compare(db, user.user_id)


@router.post("/share")
async def set_share(
    body: ShareBody,
    background: BackgroundTasks,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    uid = user.user_id
    if not body.shared:
        await db[SHARES].delete_one({"user_id": uid})
        return await build_compare(db, uid)
    if await is_safety_flagged(db, uid):
        await db[SHARES].delete_one({"user_id": uid})
        return {"state": "not_available", "shared": False}
    key = await _case_key(db, uid)
    if not key:
        raise HTTPException(status_code=400, detail="Enter your case code first.")
    was_sharing = await _is_sharing(db, uid, key)
    await db[SHARES].update_one(
        {"user_id": uid},
        {"$set": {"shared": True, "court_key": key, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    other = await _coparent(db, uid, key)
    if other and not was_sharing:
        background.add_task(notify_share, db, uid, other, await _is_sharing(db, other, key))
    return await build_compare(db, uid)


async def _names(db: AsyncIOMotorDatabase, uid: str, other: str) -> List[str]:
    out = []
    for person, fallback in ((uid, "Parent A"), (other, "Parent B")):
        ps = await db.portal_state.find_one({"user_id": person}, {"_id": 0, "court_legal_name": 1}) or {}
        u = await db.users.find_one({"user_id": person}, {"_id": 0, "name": 1}) or {}
        out.append((ps.get("court_legal_name") or u.get("name") or fallback).strip())
    return out


@router.get("/pdf")
async def compare_pdf(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> StreamingResponse:
    key, other, data = await _ready_or_409(db, user.user_id)
    pts = data["talking_points"]
    pdf = build_compare_pdf({
        **data, "case": key, "names": await _names(db, user.user_id, other),
        "talking_points": pts["items"] if pts and not pts["stale"] else [],
    })
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="SA_CoParents_Side_by_Side_Comparison.pdf"'},
    )


def _parse_points(raw: str, difference: List[Dict[str, str]]) -> List[Dict[str, str]]:
    match = re.search(r"\[.*\]", raw, re.S)
    try:
        items = json.loads(match.group(0)) if match else []
    except ValueError:
        items = []
    by_area = {str(i.get("area", "")).strip().lower(): i for i in items if isinstance(i, dict)}
    out = []
    for n, r in enumerate(difference):
        item = by_area.get(r["area"].lower()) or (items[n] if n < len(items) and isinstance(items[n], dict) else {})
        text = " ".join(str(item.get("text") or "").replace("*", "").split())[:280]
        if text:
            out.append({"area": r["area"], "source": r["source"], "text": text})
    return out


@router.post("/talking-points")
async def talking_points(request: Request, user: UserPublic = Depends(require_ai_notice), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    key, _other, data = await _ready_or_409(db, user.user_id)
    difference = data["difference"][:MAX_POINTS]
    if not difference:
        raise HTTPException(status_code=400, detail="There are no differing areas to talk about yet.")
    await _guard(request)
    prompt = "\n".join(f"- {r['area']} ({r['source']}): one parent rated {r['mine']}, the other {r['theirs']}" for r in difference)
    items = _parse_points(await _ask(_POINTS_TASK, prompt), difference)
    if not items:
        raise HTTPException(status_code=502, detail="We couldn't suggest talking points right now. Please try again.")
    now = datetime.now(timezone.utc).isoformat()
    await db[POINTS].update_one(
        {"court_key": key},
        {"$set": {"court_key": key, "items": items, "basis": _basis(data["difference"]), "generated_at": now, "generated_by": user.user_id}},
        upsert=True,
    )
    return await build_compare(db, user.user_id)


def _area_or_400(data: Dict[str, Any], area: str) -> None:
    if area not in {r["key"] for r in data["difference"]}:
        raise HTTPException(status_code=400, detail="That area isn't one where your answers differ.")


@router.post("/agree")
async def agree(
    body: AgreeBody, background: BackgroundTasks, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """Either parent's mark makes the area agreed for both; each parent can only undo their own mark."""
    key, _other, data = await _ready_or_409(db, user.user_id)
    _area_or_400(data, body.area)
    await set_mark(db, key, body.area, user.user_id, body.agreed)
    if body.agreed:
        background.add_task(queue_alert, db, user.user_id, body.area, "agreed")
    return await build_compare(db, user.user_id)


@router.put("/agree/note")
async def agree_note(
    body: NoteBody, background: BackgroundTasks, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    key, _other, data = await _ready_or_409(db, user.user_id)
    _area_or_400(data, body.area)
    if not await set_note(db, key, body.area, user.user_id, body.note):
        raise HTTPException(status_code=400, detail="Mark this area as agreed first.")
    note = " ".join(body.note.split())[:300]
    if note:
        background.add_task(queue_alert, db, user.user_id, body.area, "note", note)
    return await build_compare(db, user.user_id)


@router.post("/celebrated")
async def celebrated(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, bool]:
    key, _other, _data = await _ready_or_409(db, user.user_id)
    await mark_celebrated(db, user.user_id, key)
    return {"ok": True}
