"""Share-link management API — mounted at /api/share.

Provides:
  * Recording share tokens as they are minted (opaque table keyed by JTI)
  * User-facing listing + revocation
  * A `is_share_token_revoked()` helper called from each shared endpoint

Storage: `share_tokens` collection.  Each row:
  {
    "jti":         uuid hex,
    "user_id":     owner,
    "doc_type":    same values used by create_share_token (cp_report | summary
                   | agreement | safety | edu_deep_share …),
    "doc_id":      subject document,
    "label":       optional short human label the user typed at share time,
    "created_at":  iso,
    "expires_at":  iso | None,
    "revoked_at":  iso | None,
  }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db


router = APIRouter(prefix="/share", tags=["share"])

COLLECTION = "share_tokens"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record_share_token(
    db: AsyncIOMotorDatabase,
    *,
    jti: str,
    user_id: str,
    doc_type: str,
    doc_id: str,
    expires_at: Optional[datetime],
    label: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a freshly-minted share token so it can be listed / revoked."""
    doc = {
        "jti": jti,
        "user_id": user_id,
        "doc_type": doc_type,
        "doc_id": doc_id,
        "label": label,
        "note": note,
        "created_at": _now_iso(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "revoked_at": None,
    }
    await db[COLLECTION].replace_one({"jti": jti}, doc, upsert=True)
    return doc


async def is_share_token_revoked(db: AsyncIOMotorDatabase, jti: Optional[str]) -> bool:
    """Return True if the given jti has been explicitly revoked.

    Tokens minted before this feature shipped have no jti — those are treated
    as not revoked (they still expire via the JWT `exp` claim as before).
    """
    if not jti:
        return False
    row = await db[COLLECTION].find_one({"jti": jti}, {"_id": 0, "revoked_at": 1})
    return bool(row and row.get("revoked_at"))


def _public_row(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "jti": doc.get("jti"),
        "doc_type": doc.get("doc_type"),
        "doc_id": doc.get("doc_id"),
        "label": doc.get("label"),
        "created_at": doc.get("created_at"),
        "expires_at": doc.get("expires_at"),
        "revoked_at": doc.get("revoked_at"),
    }


class RevokeIn(BaseModel):
    jti: str


@router.get("/mine")
async def list_my_shares(user: UserPublic = Depends(get_current_user),
                        db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, List[Dict[str, Any]]]:
    """Return active + past share tokens created by the current user."""
    cursor = db[COLLECTION].find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1)
    rows = [_public_row(r) async for r in cursor]
    now = datetime.now(timezone.utc)
    active, past = [], []
    for r in rows:
        expired = False
        if r.get("expires_at"):
            try:
                expired = datetime.fromisoformat(r["expires_at"]) < now
            except ValueError:
                expired = False
        r["status"] = "revoked" if r.get("revoked_at") else ("expired" if expired else "active")
        (past if r["status"] != "active" else active).append(r)
    return {"active": active, "past": past}


@router.post("/revoke")
async def revoke(body: RevokeIn,
                 user: UserPublic = Depends(get_current_user),
                 db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    row = await db[COLLECTION].find_one({"jti": body.jti, "user_id": user.user_id}, {"_id": 0})
    if not row:
        raise HTTPException(status_code=404, detail="Share link not found.")
    if row.get("revoked_at"):
        return {"ok": True, "already_revoked": True}
    await db[COLLECTION].update_one(
        {"jti": body.jti, "user_id": user.user_id},
        {"$set": {"revoked_at": _now_iso()}},
    )
    return {"ok": True}
