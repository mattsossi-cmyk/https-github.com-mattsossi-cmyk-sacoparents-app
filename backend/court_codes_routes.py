"""Court codes a professional creates inside SA CoParents, with the assessments they ask the parent to complete.

The parent types the code on their Court page; the requested options are auto-ticked (court_checklist.py). The
professional who created the code sees, per linked parent, only whether each requested assessment is done, in
progress or not started, with dates — never answers.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import get_current_user, get_db
from court_checklist import REQUESTABLE, RequestKey, progress_rows
from models import UserPublic
from portal_routes import _hash_key

router = APIRouter(prefix="/professional/court-codes", tags=["court-codes"])

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _chunk(n: int) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


class CourtCodeCreate(BaseModel):
    label: str = Field("", max_length=80)  # the professional's own case reference; never shown to the parent
    requested: List[RequestKey] = Field(..., min_length=1, max_length=7)
    valid_days: Literal[30, 60, 90, 180] = 90


async def linked_parents(db: AsyncIOMotorDatabase, case_id: str, keys: List[str], with_nudge: bool = False) -> List[Dict[str, Any]]:
    """Parents who entered this code: display name + status-only rows for the requested options."""
    from professional_nudges import nudge_next_at, nudge_pid

    out = []
    async for ps in db.portal_state.find({"court_key": case_id}, {"_id": 0, "user_id": 1, "court_legal_name": 1}).limit(10):
        user = await db.users.find_one({"user_id": ps["user_id"]}, {"_id": 0, "name": 1}) or {}
        row = {
            "name": (ps.get("court_legal_name") or "").strip() or user.get("name") or "Parent",
            "assessments": await progress_rows(db, ps["user_id"], keys),
        }
        if with_nudge:
            row.update(pid=nudge_pid(case_id, ps["user_id"]), nudge_next_at=await nudge_next_at(db, case_id, ps["user_id"]))
        out.append(row)
    return out


async def _public(db: AsyncIOMotorDatabase, doc: Dict[str, Any]) -> Dict[str, Any]:
    keys = [k for k in REQUESTABLE if k in (doc.get("requested") or [])]
    return {
        "case_id": doc["case_id"],
        "label": doc.get("label") or "",
        "requested": keys,
        "created_at": doc.get("created_at"),
        "expires_at": doc.get("expires_at"),
        "revoked_at": doc.get("revoked_at"),
        "parents": await linked_parents(db, doc["case_id"], keys, with_nudge=True),
    }


@router.post("")
async def create_court_code(
    body: CourtCodeCreate, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """Returns the code once (only its hash is stored)."""
    now = datetime.now(timezone.utc)
    code = f"SAC-{_chunk(4)}-{_chunk(4)}"
    case_id = f"CC-{_chunk(6)}"
    while await db.portal_court_keys.find_one({"case_id": case_id}, {"_id": 1}):
        case_id = f"CC-{_chunk(6)}"
    doc = {
        "key_hash": _hash_key(code),
        "case_id": case_id,
        "mediator_name": (user.name or "").strip() or "Your professional",
        "requested": [k for k in REQUESTABLE if k in body.requested],
        "label": body.label.strip(),
        "created_by": user.user_id,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=body.valid_days)).isoformat(),
        "revoked_at": None,
    }
    await db.portal_court_keys.insert_one(doc)
    return {"code": code, **await _public(db, doc)}


@router.get("")
async def list_my_court_codes(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    docs = await db.portal_court_keys.find({"created_by": user.user_id}, {"_id": 0, "key_hash": 0}).sort("created_at", -1).to_list(100)
    return {"codes": [await _public(db, d) for d in docs]}


@router.post("/{case_id}/revoke")
async def revoke_court_code(case_id: str, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    res = await db.portal_court_keys.update_one(
        {"case_id": case_id, "created_by": user.user_id, "revoked_at": None},
        {"$set": {"revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Court code not found.")
    return {"ok": True}
