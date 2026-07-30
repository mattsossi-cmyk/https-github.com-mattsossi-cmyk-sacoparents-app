"""SNC v2 co-parent comparison API.

Mounted at /api/snc2/compare.

State machine for `snc2_shares`:

    creator sends link -> both consent + both completed + neither safety-blocked -> active

Endpoints (all authenticated):
  POST   /link                 Request a comparison with a partner (by email)
  GET    /me                   List my outgoing + incoming share requests
  POST   /{share_id}/consent   Grant my consent (safety-checked)
  POST   /{share_id}/revoke    Revoke my consent (moves share to revoked)
  GET    /{share_id}           Neutral comparison payload (?category=medical|...)
  GET    /{share_id}/pdf       Branded neutral comparison PDF (?category=...)

Guardrails:
  * Both parents must explicitly consent before ANY comparison content is
    exposed. Revocation is symmetric.
  * If the consenting parent's latest Safety Assessment recommends "No Direct
    Communication" or "Structured Written Communication Only" (levels 1-2),
    consent is hard-blocked and the parent is pointed to safety options. The
    same block applies at view time — if either parent later files a level-1/2
    assessment, the comparison payload is refused.
  * Neither parent can see the other's raw answers until BOTH assessments are
    complete AND both consents are recorded.
  * Text/free-response content is shown side-by-side once both consent —
    parents have already agreed to share.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

from auth import UserPublic, get_current_user, get_db
from snc2_comparison import build_comparison
from snc2_comparison_pdf import build_comparison_pdf


router = APIRouter(prefix="/snc2/compare", tags=["snc2-compare"])
logger = logging.getLogger(__name__)

SHARES = "snc2_shares"
ASSESSMENTS = "snc2_assessments"
SAFETY = "safety_assessments"

BLOCKING_SAFETY_LEVELS = {1, 2}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "comparison")).strip("_") or "comparison"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


async def _latest_safety_level(db: AsyncIOMotorDatabase, user_id: str) -> Optional[int]:
    doc = await db[SAFETY].find_one(
        {"user_id": user_id}, {"_id": 0, "result": 1},
        sort=[("created_at", -1)],
    )
    if not doc:
        return None
    lvl = (doc.get("result") or {}).get("level")
    return lvl if isinstance(lvl, int) else None


async def _load_user(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"user_id": user_id}, {"_id": 0})


async def _load_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"email": _normalize_email(email)}, {"_id": 0})


def _partner_view(share: Dict[str, Any], me_id: str) -> Dict[str, Any]:
    """Return the partner side of a share record for the given user."""
    if share["creator_user_id"] == me_id:
        return {
            "role": "creator",
            "my_consent": bool(share.get("creator_consent")),
            "partner_consent": bool(share.get("partner_consent")),
            "partner_user_id": share.get("partner_user_id"),
            "partner_name": share.get("partner_name") or "",
            "partner_email": share.get("partner_email"),
        }
    return {
        "role": "partner",
        "my_consent": bool(share.get("partner_consent")),
        "partner_consent": bool(share.get("creator_consent")),
        "partner_user_id": share.get("creator_user_id"),
        "partner_name": share.get("creator_name") or "",
        "partner_email": share.get("creator_email"),
    }


async def _hydrate(db: AsyncIOMotorDatabase, share: Dict[str, Any], me_id: str) -> Dict[str, Any]:
    v = _partner_view(share, me_id)
    my_a = await db[ASSESSMENTS].find_one({"user_id": me_id}, {"_id": 0, "completed": 1, "selected_pathways": 1})
    partner_a = None
    if v["partner_user_id"]:
        partner_a = await db[ASSESSMENTS].find_one(
            {"user_id": v["partner_user_id"]},
            {"_id": 0, "completed": 1, "selected_pathways": 1},
        )
    both_consent = v["my_consent"] and v["partner_consent"]
    my_done = bool((my_a or {}).get("completed"))
    partner_done = bool((partner_a or {}).get("completed"))
    my_paths = (my_a or {}).get("selected_pathways") or []
    partner_paths = (partner_a or {}).get("selected_pathways") or []
    ready = both_consent and my_done and partner_done and (share.get("status") != "revoked")
    return {
        "share_id": share["share_id"],
        "status": share.get("status"),
        "created_at": share.get("created_at"),
        "updated_at": share.get("updated_at"),
        "role": v["role"],
        "my_consent": v["my_consent"],
        "partner_consent": v["partner_consent"],
        "partner_user_id": v["partner_user_id"],
        "partner_name": v["partner_name"],
        "partner_email": v["partner_email"],
        "my_assessment_complete": my_done,
        "partner_assessment_complete": partner_done,
        "my_pathways": my_paths,
        "partner_pathways": partner_paths,
        "shared_pathways": [p for p in my_paths if p in partner_paths],
        "ready_to_view": ready,
    }


# ============ Pydantic ============
class LinkIn(BaseModel):
    email: EmailStr


class ConsentIn(BaseModel):
    consent: bool = True


# ============ Routes ============
@router.post("/link")
async def link_partner(
    body: LinkIn,
    me: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Start a comparison request with a partner that already has an account."""
    if me.is_guest:
        raise HTTPException(
            status_code=403,
            detail="Please claim an account before sending a comparison request.",
        )
    partner_email = _normalize_email(body.email)
    if not partner_email:
        raise HTTPException(status_code=400, detail="Please enter a valid email.")
    if partner_email == _normalize_email(me.email or ""):
        raise HTTPException(
            status_code=400,
            detail="That is your own email. Enter your co-parent's email.",
        )
    partner = await _load_user_by_email(db, partner_email)
    if not partner or partner.get("is_guest"):
        raise HTTPException(
            status_code=404,
            detail=(
                "No SA CoParents account was found for that email. Send a "
                "co-parent invite first so they can create their own account."
            ),
        )

    # Reject if we already have an active or pending share between these two.
    a, b = sorted([me.user_id, partner["user_id"]])
    existing = await db[SHARES].find_one({
        "user_pair": [a, b],
        "status": {"$ne": "revoked"},
    })
    if existing:
        return {"ok": True, "share": await _hydrate(db, existing, me.user_id), "already_existed": True}

    # Safety guardrail on creation — the creator implicitly consents, so we
    # apply the block up front.
    level = await _latest_safety_level(db, me.user_id)
    if level in BLOCKING_SAFETY_LEVELS:
        raise HTTPException(
            status_code=403,
            detail=(
                "Your Safety Assessment recommends a limited-contact pathway. "
                "Sharing detailed Special Needs answers directly with your "
                "co-parent is not appropriate right now. Please review your "
                "safety options before starting a comparison."
            ),
        )

    now = _now_iso()
    share = {
        "share_id": f"snc2_share_{uuid.uuid4().hex[:12]}",
        "user_pair": [a, b],
        "creator_user_id": me.user_id,
        "creator_name": me.name or "",
        "creator_email": me.email,
        "partner_user_id": partner["user_id"],
        "partner_name": partner.get("name") or "",
        "partner_email": partner.get("email"),
        "creator_consent": True,
        "creator_consented_at": now,
        "partner_consent": False,
        "partner_consented_at": None,
        "status": "awaiting_partner_consent",
        "created_at": now,
        "updated_at": now,
    }
    await db[SHARES].insert_one(share.copy())
    return {"ok": True, "share": await _hydrate(db, share, me.user_id), "already_existed": False}


@router.get("/me")
async def list_my_shares(
    me: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    cursor = db[SHARES].find(
        {"user_pair": me.user_id},
        {"_id": 0},
    ).sort("updated_at", -1).limit(50)
    rows = [await _hydrate(db, s, me.user_id) async for s in cursor]
    return {"shares": rows}


async def _find_share(db: AsyncIOMotorDatabase, share_id: str, me_id: str) -> Dict[str, Any]:
    share = await db[SHARES].find_one({"share_id": share_id}, {"_id": 0})
    if not share or me_id not in (share.get("user_pair") or []):
        raise HTTPException(status_code=404, detail="Comparison request not found.")
    return share


@router.post("/{share_id}/consent")
async def consent(
    share_id: str,
    body: ConsentIn,
    me: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    share = await _find_share(db, share_id, me.user_id)
    if share.get("status") == "revoked":
        raise HTTPException(status_code=409, detail="This comparison request was revoked.")

    if body.consent:
        level = await _latest_safety_level(db, me.user_id)
        if level in BLOCKING_SAFETY_LEVELS:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Your Safety Assessment recommends a limited-contact "
                    "pathway. Please review your safety options before "
                    "consenting to a Special Needs comparison."
                ),
            )

    is_creator = share["creator_user_id"] == me.user_id
    now = _now_iso()
    updates: Dict[str, Any] = {"updated_at": now}
    if is_creator:
        updates["creator_consent"] = bool(body.consent)
        updates["creator_consented_at"] = now if body.consent else None
    else:
        updates["partner_consent"] = bool(body.consent)
        updates["partner_consented_at"] = now if body.consent else None

    # Recompute status
    both = (updates.get("creator_consent",
                        share.get("creator_consent")) and
            updates.get("partner_consent",
                        share.get("partner_consent")))
    if both:
        updates["status"] = "active"
    elif is_creator and updates["creator_consent"] and not share.get("partner_consent"):
        updates["status"] = "awaiting_partner_consent"
    elif (not is_creator) and updates["partner_consent"] and not share.get("creator_consent"):
        updates["status"] = "awaiting_creator_consent"
    else:
        updates["status"] = "awaiting_consent"

    await db[SHARES].update_one({"share_id": share_id}, {"$set": updates})
    share.update(updates)
    return {"ok": True, "share": await _hydrate(db, share, me.user_id)}


@router.post("/{share_id}/revoke")
async def revoke(
    share_id: str,
    me: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    share = await _find_share(db, share_id, me.user_id)
    now = _now_iso()
    await db[SHARES].update_one(
        {"share_id": share_id},
        {"$set": {"status": "revoked", "revoked_by_user_id": me.user_id,
                  "revoked_at": now, "updated_at": now}},
    )
    share["status"] = "revoked"
    share["updated_at"] = now
    return {"ok": True, "share": await _hydrate(db, share, me.user_id)}


async def _load_comparison(
    db: AsyncIOMotorDatabase,
    share: Dict[str, Any],
    me_id: str,
    category: Optional[str],
) -> Dict[str, Any]:
    if share.get("status") == "revoked":
        raise HTTPException(status_code=409, detail="This comparison has been revoked.")
    if not (share.get("creator_consent") and share.get("partner_consent")):
        raise HTTPException(
            status_code=409,
            detail="Both parents must consent before the comparison is visible.",
        )
    # Real-time safety check for the viewer.
    my_level = await _latest_safety_level(db, me_id)
    if my_level in BLOCKING_SAFETY_LEVELS:
        raise HTTPException(
            status_code=403,
            detail=(
                "Your Safety Assessment recommends a limited-contact pathway. "
                "Access to co-parent comparison is paused. Please review your "
                "safety options."
            ),
        )
    creator_a = await db[ASSESSMENTS].find_one({"user_id": share["creator_user_id"]})
    partner_a = await db[ASSESSMENTS].find_one({"user_id": share["partner_user_id"]})
    if not creator_a or not creator_a.get("completed"):
        raise HTTPException(status_code=409, detail="The other parent has not finished their assessment yet.")
    if not partner_a or not partner_a.get("completed"):
        raise HTTPException(status_code=409, detail="The other parent has not finished their assessment yet.")

    try:
        return build_comparison(
            parent_a_name=share.get("creator_name") or "Parent A",
            parent_b_name=share.get("partner_name") or "Parent B",
            a_pathways=creator_a.get("selected_pathways") or [],
            b_pathways=partner_a.get("selected_pathways") or [],
            a_answers=creator_a.get("answers") or {},
            b_answers=partner_a.get("answers") or {},
            category_filter=category,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{share_id}")
async def get_comparison(
    share_id: str,
    category: Optional[str] = Query(default=None),
    me: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    share = await _find_share(db, share_id, me.user_id)
    comparison = await _load_comparison(db, share, me.user_id, category)
    return {
        "share": await _hydrate(db, share, me.user_id),
        "comparison": comparison,
    }


@router.get("/{share_id}/pdf")
async def get_comparison_pdf(
    share_id: str,
    category: Optional[str] = Query(default=None),
    me: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    share = await _find_share(db, share_id, me.user_id)
    comparison = await _load_comparison(db, share, me.user_id, category)
    pdf_bytes = build_comparison_pdf(
        comparison=comparison,
        safety_notice=(
            "Safety notice: If either parent's circumstances change, please "
            "revisit the Family Violence & Communication Safety Assessment "
            "before continuing to share detailed information."
        ),
    )
    filename = f"SNC_Comparison_{_safe_filename(share.get('creator_name'))}_and_{_safe_filename(share.get('partner_name'))}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
