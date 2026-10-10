"""Self Journey summary: one-time 5-of-5 celebration flag + combined Journey Summary PDF."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from child_needs_routes import CONTENT as NEEDS_CONTENT
from coparenting_routes import COLLECTION as CP_COLLECTION
from coparenting_scoring import compute_scores as cp_scores
from journey_certificate_pdf import build_certificate_pdf
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
STEP_TITLES = [
    "Self-Assessment",
    "Co-Parenting Assessment",
    "Your Child's Specific Needs",
    "Foundation Statement",
    "Parallel Parenting Plan",
    "Communication Builder",
]


class CertificateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


async def _missing_steps(db: AsyncIOMotorDatabase, uid: str) -> List[str]:
    needs = await db.child_needs_assessments.find_one({"user_id": uid}, {"_id": 0, "completed_at": 1}) or {}
    portal = await db.portal_state.find_one({"user_id": uid}, {"_id": 0, "biff_logs": 1}) or {}
    done = [
        bool(await db.self_assessment_history.find_one({"user_id": uid}, {"_id": 1})),
        bool(await db[CP_COLLECTION].find_one({"user_id": uid, "completed": True}, {"_id": 1})),
        all((needs.get("completed_at") or {}).get(k) for k in ("educational", "medical", "psychological")),
        bool(await db.foundation_builder.find_one({"user_id": uid}, {"_id": 1})),
        bool(await db.parallel_parenting_plans.find_one({"user_id": uid, "completed_at": {"$ne": None}}, {"_id": 1})),
        len(portal.get("biff_logs") or []) > 1,  # the first entry is the built-in demo
    ]
    return [t for t, ok in zip(STEP_TITLES, done) if not ok]


async def certificate_bytes(db: AsyncIOMotorDatabase, uid: str, raw_name: str) -> bytes:
    """Validated certificate PDF: name present and all 6 steps finished (422 otherwise)."""
    name = raw_name.strip()
    if not name:
        raise HTTPException(422, "Please enter the name to print.")
    missing = await _missing_steps(db, uid)
    if missing:
        raise HTTPException(422, f"Finish every step first. Still to do: {', '.join(missing)}.")
    flag = await db[STEP_CELEBRATIONS].find_one({"user_id": uid}, {"_id": 0, "celebrated_at": 1}) or {}
    return build_certificate_pdf(
        name=name, finished_iso=flag.get("celebrated_at") or datetime.now(timezone.utc).isoformat(), steps=STEP_TITLES
    )


@router.post("/certificate")
async def journey_certificate(
    body: CertificateIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes = await certificate_bytes(db, user.user_id, body.name)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="SA_CoParents_Individual_Journey_Certificate.pdf"'},
    )


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
