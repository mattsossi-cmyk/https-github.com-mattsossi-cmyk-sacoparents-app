"""Mediation prep routes: save/load prep data, AI analysis, summary, PDF export."""
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_current_user
from models import (
    ChildGoalsPayload,
    IssuesPayload,
    PriorityPayload,
    CommStylePayload,
    ReadinessPayload,
    ReflectionPayload,
    CommAnalysisRequest,
    UserPublic,
)
import ai_service
import pdf_service


router = APIRouter(prefix="/mediation", tags=["mediation"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _save_section(db, user_id: str, section: str, payload: dict):
    await db.prep_data.update_one(
        {"user_id": user_id},
        {
            "$set": {
                section: payload,
                "updated_at": _now(),
                f"completed.{section}": True,
            },
            "$setOnInsert": {"user_id": user_id, "created_at": _now()},
        },
        upsert=True,
    )


async def _load_prep(db, user_id: str) -> Dict[str, Any]:
    doc = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0})
    return doc or {"user_id": user_id, "completed": {}}


# ============ Save endpoints ============
@router.put("/child-goals")
async def save_child_goals(
    body: ChildGoalsPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "child_goals", body.dict())
    return {"ok": True}


@router.put("/issues")
async def save_issues(
    body: IssuesPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "issues", body.dict())
    return {"ok": True}


@router.put("/priority")
async def save_priority(
    body: PriorityPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "priority", body.dict())
    return {"ok": True}


@router.put("/comm-style")
async def save_comm_style(
    body: CommStylePayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "comm_style", body.dict())
    return {"ok": True}


@router.put("/readiness")
async def save_readiness(
    body: ReadinessPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "readiness", body.dict())
    return {"ok": True}


@router.put("/reflection")
async def save_reflection(
    body: ReflectionPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "reflection", body.dict())
    return {"ok": True}


@router.get("/prep")
async def get_prep(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    return await _load_prep(request.app.state.db, current.user_id)


# ============ AI endpoints ============
@router.post("/analyze-communication")
async def analyze_communication(
    body: CommAnalysisRequest,
    current: UserPublic = Depends(get_current_user),
):
    try:
        result = await ai_service.analyze_communication(
            body.answers or {}, body.text or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")


@router.post("/reframe")
async def reframe(
    body: dict,
    current: UserPublic = Depends(get_current_user),
):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    try:
        return await ai_service.reframe_message(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI reframe failed: {e}")


@router.post("/summary")
async def generate_summary(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    if not prep.get("child_goals") and not prep.get("issues"):
        raise HTTPException(
            status_code=400,
            detail="Please complete at least Child Goals or Issues first.",
        )
    try:
        summary = await ai_service.generate_summary(prep, current.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summary failed: {e}")

    summary_id = f"sum_{uuid.uuid4().hex[:12]}"
    # Authoritative fields after the AI spread (defensive against hallucinated keys).
    doc = {
        **summary,
        "summary_id": summary_id,
        "user_id": current.user_id,
        "generated_at": _now(),
    }
    await db.summaries.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/summaries")
async def list_summaries(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.summaries.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/summary/{summary_id}/pdf")
async def download_summary_pdf(
    summary_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    summary = await db.summaries.find_one(
        {"summary_id": summary_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    prep = await _load_prep(db, current.user_id)
    pdf_bytes = pdf_service.build_summary_pdf(
        user_name=current.name,
        summary=summary,
        child_goals=prep.get("child_goals"),
        mediation_date=current.mediation_date,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="mediation_summary_{summary_id}.pdf"'
        },
    )


# ============ Co-Parenting Agreement Draft ============
@router.post("/agreement")
async def generate_agreement(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    if not prep.get("child_goals") and not prep.get("issues"):
        raise HTTPException(
            status_code=400,
            detail="Please complete at least Child Goals or Issues first.",
        )
    # Build a focused subset — goals, issues, priority only.
    focused = {
        "child_goals": prep.get("child_goals"),
        "issues": prep.get("issues"),
        "priority": prep.get("priority"),
    }
    try:
        agreement = await ai_service.generate_agreement_draft(focused, current.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI agreement failed: {e}")

    agreement_id = f"agr_{uuid.uuid4().hex[:12]}"
    # Authoritative fields go AFTER the AI spread so Claude can never overwrite
    # our identifiers with a hallucinated key.
    doc = {
        **agreement,
        "agreement_id": agreement_id,
        "user_id": current.user_id,
        "generated_at": _now(),
    }
    await db.agreements.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/agreements")
async def list_agreements(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.agreements.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/agreement/{agreement_id}/pdf")
async def download_agreement_pdf(
    agreement_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    agreement = await db.agreements.find_one(
        {"agreement_id": agreement_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    pdf_bytes = pdf_service.build_agreement_pdf(
        user_name=current.name,
        agreement=agreement,
        mediation_date=current.mediation_date,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="coparenting_agreement_{agreement_id}.pdf"'
        },
    )


# ============ Resources (static seed) ============
RESOURCES = [
    {
        "id": "r1",
        "category": "Communication",
        "title": "BIFF: Brief, Informative, Friendly, Firm",
        "description": "A 4-rule framework for replying to high-conflict messages without escalating.",
        "kind": "article",
    },
    {
        "id": "r2",
        "category": "High Conflict",
        "title": "Disengaging from Provocation",
        "description": "How to recognize bait and respond from a place of calm.",
        "kind": "video",
    },
    {
        "id": "r3",
        "category": "Parallel Parenting",
        "title": "When to Move from Co-Parenting to Parallel Parenting",
        "description": "Reduce exposure to conflict while protecting your child's wellbeing.",
        "kind": "article",
    },
    {
        "id": "r4",
        "category": "Communication",
        "title": "I-Statements for Co-Parents",
        "description": "Express needs without triggering defensiveness.",
        "kind": "article",
    },
    {
        "id": "r5",
        "category": "Rebuilding Trust",
        "title": "Small Consistent Wins",
        "description": "Trust is rebuilt through small, predictable actions over time.",
        "kind": "article",
    },
    {
        "id": "r6",
        "category": "Parenting After Divorce",
        "title": "Helping Your Child Feel Safe",
        "description": "Practical scripts and rituals that anchor your child during transitions.",
        "kind": "video",
    },
]


@router.get("/resources")
async def get_resources():
    return RESOURCES
