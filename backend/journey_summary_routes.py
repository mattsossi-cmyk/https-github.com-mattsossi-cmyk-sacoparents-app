"""Self Journey summary: one-time 5-of-5 celebration flag + combined Journey Summary PDF."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Dict

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user, get_db
from child_needs_routes import CONTENT as NEEDS_CONTENT
from coparenting_routes import COLLECTION as CP_COLLECTION
from coparenting_scoring import compute_scores as cp_scores
from journey_summary_pdf import build_journey_summary_pdf
from self_assessment_routes import CONTENT as SA_CONTENT, band_for

router = APIRouter(prefix="/journey-summary", tags=["journey-summary"])
CELEBRATIONS = "journey_celebrations"


@router.get("/celebrated")
async def get_celebrated(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, bool]:
    return {"celebrated": bool(await db[CELEBRATIONS].find_one({"user_id": user.user_id}, {"_id": 1}))}


@router.post("/celebrated")
async def mark_celebrated(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, bool]:
    await db[CELEBRATIONS].update_one(
        {"user_id": user.user_id},
        {"$setOnInsert": {"celebrated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"celebrated": True}


STEP_CELEBRATIONS = "journey_step_celebrations"


@router.get("/steps-celebrated")
async def get_steps_celebrated(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, bool]:
    return {"celebrated": bool(await db[STEP_CELEBRATIONS].find_one({"user_id": user.user_id}, {"_id": 1}))}


@router.post("/steps-celebrated")
async def mark_steps_celebrated(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, bool]:
    await db[STEP_CELEBRATIONS].update_one(
        {"user_id": user.user_id},
        {"$setOnInsert": {"celebrated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"celebrated": True}


@router.get("/pdf")
async def journey_summary_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> StreamingResponse:
    uid = user.user_id
    history = await db.self_assessment_history.find({"user_id": uid}, {"_id": 0, "user_id": 0}).sort("completed_at", 1).to_list(500)
    cp_doc = await db[CP_COLLECTION].find_one({"user_id": uid, "completed": True}, {"_id": 0}, sort=[("updated_at", -1)])
    if cp_doc and not cp_doc.get("scores"):
        cp_doc["scores"] = cp_scores(cp_doc.get("answers") or {})
    needs = await db.child_needs_assessments.find_one({"user_id": uid}, {"_id": 0}) or {}
    pdf_bytes = build_journey_summary_pdf(
        parent_name=user.name,
        sa_history=history,
        sa_content=SA_CONTENT,
        band_for=band_for,
        cp_doc=cp_doc,
        needs_content=NEEDS_CONTENT,
        needs_state=needs,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="SA_CoParents_Journey_Summary.pdf"'},
    )
