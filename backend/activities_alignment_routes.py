"""
Activities Alignment — API endpoints.

Mirrors `communication_alignment_routes.py`. Mounted at
`/api/activities-reflection` (parent-facing) and
`/api/activities-alignment` (paired-view / compare).

Endpoints
---------
GET  /activities-reflection/schema
GET  /activities-reflection/mine
PUT  /activities-reflection
POST /activities-alignment/compare
POST /activities-alignment/compare/summary
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from activities_reflection_questions import (
    DIMENSIONS,
    QUESTIONS,
    VERSION,
    public_schema,
    score,
    validate_answers,
)
from ai_summary_activities import generate_activities_summary


router = APIRouter(tags=["activities-alignment"])
logger = logging.getLogger(__name__)

_COLL = "activities_reflections"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v


class ReflectionSavePayload(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[Dict[str, str]] = None
    intake_choice: Optional[str] = Field(default=None)


class CompareRequest(BaseModel):
    coparent_email: str


class CompareSummaryRequest(BaseModel):
    compare_payload: Dict[str, Any]
    model: Optional[str] = Field(default="claude", pattern="^(claude|gpt)$")


async def _load_reflection(db, user_id: str) -> Optional[Dict[str, Any]]:
    return await db[_COLL].find_one({"user_id": user_id}, {"_id": 0})


def _shape_self(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not doc:
        return {
            "score": {"overall": 0, "dimensions": {}, "answered_count": 0},
            "answers": {},
            "notes": {},
            "intake_choice": None,
            "updated_at": None,
        }
    return {
        "score": doc.get("score") or {},
        "answers": doc.get("answers") or {},
        "notes": doc.get("notes") or {},
        "intake_choice": doc.get("intake_choice"),
        "updated_at": _iso(doc.get("updated_at")),
    }


def _diff_dimensions(
    self_dims: Dict[str, Any], coparent_dims: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    shared: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    for key, meta in DIMENSIONS.items():
        self_score = (self_dims.get(key) or {}).get("score", 0)
        coparent_score = (coparent_dims.get(key) or {}).get("score", 0)
        delta = abs(self_score - coparent_score)
        row = {
            "dimension": key,
            "label": meta["label"],
            "blurb": meta["blurb"],
            "self_score": self_score,
            "coparent_score": coparent_score,
            "delta": delta,
        }
        (shared if delta <= 15 else gaps).append(row)
    gaps.sort(key=lambda r: r["delta"], reverse=True)
    shared.sort(key=lambda r: r["delta"])
    return {"shared": shared, "gaps": gaps}


@router.get("/activities-reflection/schema")
async def get_schema():
    return public_schema()


@router.put("/activities-reflection")
async def save_reflection(
    body: ReflectionSavePayload,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cleaned = validate_answers(body.answers)
    scored = score(cleaned)
    doc = {
        "user_id": current.user_id,
        "email": current.email,
        "version": VERSION,
        "answers": cleaned,
        "notes": {k: (v or "").strip()[:2000] for k, v in (body.notes or {}).items()},
        "intake_choice": body.intake_choice,
        "score": scored,
        "updated_at": _now(),
    }
    await db[_COLL].update_one(
        {"user_id": current.user_id},
        {"$set": doc, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
    )
    try:
        from joint_alignment_routes import mark_assessment_completed  # noqa: WPS433
        await mark_assessment_completed(db, current.user_id, "activities")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "score": scored}


@router.get("/activities-reflection/mine")
async def get_mine(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await _load_reflection(db, current.user_id)
    return _shape_self(doc)


@router.post("/activities-alignment/compare")
async def compare(
    body: CompareRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not body.coparent_email:
        raise HTTPException(status_code=400, detail="coparent_email required")

    coparent = await db.users.find_one(
        {"email": body.coparent_email.lower()},
        {"user_id": 1, "email": 1, "name": 1},
    )
    if not coparent:
        raise HTTPException(status_code=404, detail="Co-parent account not found")

    self_doc = await _load_reflection(db, current.user_id)
    coparent_doc = await _load_reflection(db, coparent["user_id"])

    if not self_doc:
        raise HTTPException(
            status_code=409,
            detail="Complete your Activities Reflection before comparing.",
        )
    if not coparent_doc:
        return {
            "status": "waiting_on_coparent",
            "self": _shape_self(self_doc),
            "coparent": {
                "email": coparent["email"],
                "name": coparent.get("name"),
            },
        }

    self_shape = _shape_self(self_doc)
    coparent_shape = _shape_self(coparent_doc)
    diff = _diff_dimensions(
        self_shape["score"].get("dimensions") or {},
        coparent_shape["score"].get("dimensions") or {},
    )

    return {
        "status": "ready",
        "self": self_shape,
        "coparent": {
            "email": coparent["email"],
            "name": coparent.get("name"),
            **coparent_shape,
        },
        "shared": diff["shared"],
        "gaps": diff["gaps"],
        "generated_at": _iso(_now()),
    }


@router.post("/activities-alignment/compare/summary")
async def compare_summary(
    body: CompareSummaryRequest,
    current: UserPublic = Depends(get_current_user),
):
    payload = body.compare_payload or {}
    if not payload.get("shared") and not payload.get("gaps"):
        raise HTTPException(
            status_code=400,
            detail="compare_payload missing shared/gaps",
        )
    try:
        summary = await generate_activities_summary(payload, model=body.model or "claude")
    except Exception as exc:  # pragma: no cover — fail-soft
        logger.warning("activities summary regen failed: %s", exc)
        raise HTTPException(status_code=502, detail="Summary regeneration failed")
    return {"summary": summary, "model": body.model or "claude"}
