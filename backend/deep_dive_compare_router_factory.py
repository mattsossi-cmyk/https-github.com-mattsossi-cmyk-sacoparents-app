"""Factory that builds a co-parent comparison APIRouter for any deep-dive
pathway (Educational, Psychological, Medical). All three pathways share the
identical state machine (link → mutual consent → view → PDF → revoke) and
safety guardrail, so we build them from one place.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

from auth import UserPublic, get_current_user, get_db


SAFETY = "safety_assessments"
SNAPSHOTS = "deep_dive_compare_snapshots"
BLOCKING_SAFETY_LEVELS = {1, 2}
logger = logging.getLogger(__name__)


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


async def _load_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"email": _normalize_email(email)}, {"_id": 0})


class LinkIn(BaseModel):
    email: EmailStr


class ConsentIn(BaseModel):
    consent: bool = True


def make_deep_dive_compare_router(
    *,
    prefix: str,                # e.g. "/edu-deep/compare"
    tag: str,                   # e.g. "edu-deep-compare"
    shares_collection: str,     # e.g. "edu_deep_shares"
    assessments_collection: str, # e.g. "edu_deep_assessments"
    share_id_prefix: str,       # e.g. "edu_deep_share_"
    product_label: str,         # e.g. "Educational Deep Dive"
    pdf_filename_stem: str,     # e.g. "EduDeep_Comparison"
    build_comparison: Callable[..., Dict[str, Any]],
    build_comparison_pdf: Callable[..., bytes],
    pdf_header_subtitle: str,   # e.g. "Educational Deep Dive Co-Parent Comparison"
    pdf_product_title: str,     # e.g. "Educational Deep Dive Comparison"
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    def _partner_view(share: Dict[str, Any], me_id: str) -> Dict[str, Any]:
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
        my_a = await db[assessments_collection].find_one({"user_id": me_id}, {"_id": 0, "completed": 1})
        partner_a = None
        if v["partner_user_id"]:
            partner_a = await db[assessments_collection].find_one(
                {"user_id": v["partner_user_id"]}, {"_id": 0, "completed": 1},
            )
        both_consent = v["my_consent"] and v["partner_consent"]
        my_done = bool((my_a or {}).get("completed"))
        partner_done = bool((partner_a or {}).get("completed"))
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
            "ready_to_view": ready,
        }

    def _safety_message() -> str:
        return (
            "Your Safety Assessment recommends a limited-contact pathway. "
            f"Sharing detailed {product_label} answers directly with your "
            "co-parent is not appropriate right now. Please review your "
            "safety options before starting a comparison."
        )

    @router.post("/link")
    async def link_partner(body: LinkIn,
                           me: UserPublic = Depends(get_current_user),
                           db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
        if me.is_guest:
            raise HTTPException(status_code=403, detail="Please claim an account before sending a comparison request.")
        partner_email = _normalize_email(body.email)
        if not partner_email:
            raise HTTPException(status_code=400, detail="Please enter a valid email.")
        if partner_email == _normalize_email(me.email or ""):
            raise HTTPException(status_code=400, detail="That is your own email. Enter your co-parent's email.")
        partner = await _load_user_by_email(db, partner_email)
        if not partner or partner.get("is_guest"):
            raise HTTPException(
                status_code=404,
                detail=("No SA CoParents account was found for that email. Send a "
                        "co-parent invite first so they can create their own account."),
            )
        a, b = sorted([me.user_id, partner["user_id"]])
        existing = await db[shares_collection].find_one({"user_pair": [a, b], "status": {"$ne": "revoked"}})

        # Safety guardrail applies before returning either an existing or new
        # share so a parent whose safety level drops later can't slip back in.
        level = await _latest_safety_level(db, me.user_id)
        if level in BLOCKING_SAFETY_LEVELS:
            raise HTTPException(status_code=403, detail=_safety_message())

        if existing:
            return {"ok": True, "share": await _hydrate(db, existing, me.user_id), "already_existed": True}

        now = _now_iso()
        share = {
            "share_id": f"{share_id_prefix}{uuid.uuid4().hex[:12]}",
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
        await db[shares_collection].insert_one(share.copy())
        return {"ok": True, "share": await _hydrate(db, share, me.user_id), "already_existed": False}

    @router.get("/me")
    async def list_my_shares(me: UserPublic = Depends(get_current_user),
                             db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
        cursor = db[shares_collection].find({"user_pair": me.user_id}, {"_id": 0}).sort("updated_at", -1).limit(50)
        rows = [await _hydrate(db, s, me.user_id) async for s in cursor]
        return {"shares": rows}

    async def _find_share(db: AsyncIOMotorDatabase, share_id: str, me_id: str) -> Dict[str, Any]:
        share = await db[shares_collection].find_one({"share_id": share_id}, {"_id": 0})
        if not share or me_id not in (share.get("user_pair") or []):
            raise HTTPException(status_code=404, detail="Comparison request not found.")
        return share

    @router.post("/{share_id}/consent")
    async def consent(share_id: str, body: ConsentIn,
                      me: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
        share = await _find_share(db, share_id, me.user_id)
        if share.get("status") == "revoked":
            raise HTTPException(status_code=409, detail="This comparison request was revoked.")
        if body.consent:
            level = await _latest_safety_level(db, me.user_id)
            if level in BLOCKING_SAFETY_LEVELS:
                raise HTTPException(status_code=403, detail=(
                    "Your Safety Assessment recommends a limited-contact pathway. "
                    f"Please review your safety options before consenting to a "
                    f"{product_label} comparison."))

        is_creator = share["creator_user_id"] == me.user_id
        now = _now_iso()
        updates: Dict[str, Any] = {"updated_at": now}
        if is_creator:
            updates["creator_consent"] = bool(body.consent)
            updates["creator_consented_at"] = now if body.consent else None
        else:
            updates["partner_consent"] = bool(body.consent)
            updates["partner_consented_at"] = now if body.consent else None

        both = (updates.get("creator_consent", share.get("creator_consent")) and
                updates.get("partner_consent", share.get("partner_consent")))
        if both:
            updates["status"] = "active"
        elif is_creator and updates.get("creator_consent") and not share.get("partner_consent"):
            updates["status"] = "awaiting_partner_consent"
        elif (not is_creator) and updates.get("partner_consent") and not share.get("creator_consent"):
            updates["status"] = "awaiting_creator_consent"
        else:
            updates["status"] = "awaiting_consent"

        await db[shares_collection].update_one({"share_id": share_id}, {"$set": updates})
        share.update(updates)
        return {"ok": True, "share": await _hydrate(db, share, me.user_id)}

    @router.post("/{share_id}/revoke")
    async def revoke(share_id: str,
                     me: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
        share = await _find_share(db, share_id, me.user_id)
        now = _now_iso()
        await db[shares_collection].update_one(
            {"share_id": share_id},
            {"$set": {"status": "revoked", "revoked_by_user_id": me.user_id,
                      "revoked_at": now, "updated_at": now}},
        )
        share["status"] = "revoked"
        share["updated_at"] = now
        return {"ok": True, "share": await _hydrate(db, share, me.user_id)}

    async def _load_comparison(db, share, me_id):
        if share.get("status") == "revoked":
            raise HTTPException(status_code=409, detail="This comparison has been revoked.")
        if not (share.get("creator_consent") and share.get("partner_consent")):
            raise HTTPException(status_code=409, detail="Both parents must consent before the comparison is visible.")
        my_level = await _latest_safety_level(db, me_id)
        if my_level in BLOCKING_SAFETY_LEVELS:
            raise HTTPException(status_code=403, detail=(
                "Your Safety Assessment recommends a limited-contact pathway. "
                "Access to co-parent comparison is paused. Please review your safety options."))
        creator_a = await db[assessments_collection].find_one({"user_id": share["creator_user_id"]})
        partner_a = await db[assessments_collection].find_one({"user_id": share["partner_user_id"]})
        if not creator_a or not creator_a.get("completed"):
            raise HTTPException(status_code=409, detail="The other parent has not finished their assessment yet.")
        if not partner_a or not partner_a.get("completed"):
            raise HTTPException(status_code=409, detail="The other parent has not finished their assessment yet.")
        comparison = build_comparison(
            parent_a_name=share.get("creator_name") or "Parent A",
            parent_b_name=share.get("partner_name") or "Parent B",
            a_answers=creator_a.get("responses") or {},
            b_answers=partner_a.get("responses") or {},
        )
        # Snapshot for the timeline. Dedupe by (creator_updated_at, partner_updated_at)
        # so viewing the comparison many times a day doesn't spam rows — a new row
        # only lands when either parent has re-run their assessment since last time.
        creator_ts = creator_a.get("updated_at") or creator_a.get("created_at")
        partner_ts = partner_a.get("updated_at") or partner_a.get("created_at")
        snapshot_key = f"{creator_ts}|{partner_ts}"
        existing = await db[SNAPSHOTS].find_one(
            {"share_id": share["share_id"], "snapshot_key": snapshot_key}, {"_id": 0, "snapshot_id": 1},
        )
        if not existing:
            highlights = (comparison.get("highlights") or [])[:3]
            top_prompts = [
                {"prompt": h.get("prompt", ""), "section_name": h.get("section_name", "")}
                for h in highlights
            ]
            try:
                await db[SNAPSHOTS].insert_one({
                    "snapshot_id": f"snap_{uuid.uuid4().hex[:12]}",
                    "share_id": share["share_id"],
                    "pathway_id": tag,  # e.g. "edu-deep-compare"
                    "product_label": product_label,
                    "snapshot_key": snapshot_key,
                    "creator_updated_at": creator_ts,
                    "partner_updated_at": partner_ts,
                    "created_at": _now_iso(),
                    "summary": comparison.get("summary") or {},
                    "top_highlights": top_prompts,
                })
            except Exception:  # noqa: BLE001
                # Never let a snapshot-write failure block the view — the
                # comparison itself is what the parent asked for.
                logger.exception("Failed to persist compare snapshot for share %s", share["share_id"])
        return comparison

    @router.get("/{share_id}")
    async def get_comparison(share_id: str,
                             me: UserPublic = Depends(get_current_user),
                             db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
        share = await _find_share(db, share_id, me.user_id)
        comparison = await _load_comparison(db, share, me.user_id)
        return {"share": await _hydrate(db, share, me.user_id), "comparison": comparison}

    @router.get("/{share_id}/pdf")
    async def get_comparison_pdf(share_id: str,
                                 me: UserPublic = Depends(get_current_user),
                                 db: AsyncIOMotorDatabase = Depends(get_db)):
        share = await _find_share(db, share_id, me.user_id)
        comparison = await _load_comparison(db, share, me.user_id)
        pdf_bytes = build_comparison_pdf(
            comparison=comparison,
            safety_notice=(
                "Safety notice: If either parent's circumstances change, please "
                "revisit the Family Violence & Communication Safety Assessment "
                "before continuing to share detailed information."
            ),
            product_title=pdf_product_title,
            header_subtitle=pdf_header_subtitle,
        )
        filename = (f"{pdf_filename_stem}_{_safe_filename(share.get('creator_name'))}"
                    f"_and_{_safe_filename(share.get('partner_name'))}.pdf")
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/{share_id}/timeline")
    async def get_timeline(share_id: str,
                           me: UserPublic = Depends(get_current_user),
                           db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
        """Return the comparison alignment history for this share.

        Snapshots are inserted on comparison-view (deduped by assessment
        timestamps) so re-running an assessment naturally produces a new row
        the next time either parent opens the comparison.
        """
        share = await _find_share(db, share_id, me.user_id)
        cursor = db[SNAPSHOTS].find({"share_id": share_id}, {"_id": 0}).sort("created_at", 1)
        snapshots = [s async for s in cursor]
        # Trend series for the sparkline / progress bar.
        series = [
            {
                "created_at": s.get("created_at"),
                "aligned_pct": (s.get("summary") or {}).get("aligned_pct", 0),
                "divergent_pct": (s.get("summary") or {}).get("divergent_pct", 0),
                "total_items": (s.get("summary") or {}).get("total_items", 0),
            }
            for s in snapshots
        ]
        first_pct = series[0]["aligned_pct"] if series else 0
        latest_pct = series[-1]["aligned_pct"] if series else 0
        return {
            "share_id": share_id,
            "product_label": product_label,
            "snapshots": snapshots,
            "series": series,
            "count": len(snapshots),
            "first_aligned_pct": first_pct,
            "latest_aligned_pct": latest_pct,
            "delta_aligned_pct": latest_pct - first_pct,
        }

    return router
