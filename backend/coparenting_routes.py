"""FastAPI routes for the SA CoParents 10-section Co-Parenting Assessment.

Mounted at /api/coparenting.

Endpoints:
  GET   /schema                     Returns the 10-section schema + response scale
  GET   /me                         The current user's most recent assessment (answers + scores)
  POST  /answer                     Save a single answer
  POST  /answers/bulk               Save many answers at once
  POST  /complete                   Mark the assessment complete, compute and persist scores
  GET   /scores                     Compute-and-return scores for the current user's saved answers
  DELETE /me                        Reset the current user's assessment (start over)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from coparenting_questions import RESPONSE_SCALE, SECTIONS, find_question, total_question_count
from coparenting_scoring import compute_scores, validate_answers


router = APIRouter(prefix="/coparenting", tags=["coparenting"])
logger = logging.getLogger(__name__)

COLLECTION = "cp_assessments"


# ============================================================
# Pydantic models
# ============================================================
class AnswerIn(BaseModel):
    question_id: str = Field(..., description="Question id, e.g. s1q3")
    value: int = Field(..., ge=0, le=4, description="Likert value 0-4 (Never..Always)")


class AnswersBulkIn(BaseModel):
    answers: Dict[str, int] = Field(..., description="Map of question_id -> value")


# ============================================================
# Helpers
# ============================================================
async def _get_or_create_doc(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user_id, "completed": {"$ne": True}})
    if doc:
        return doc
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        "user_id": user_id,
        "answers": {},
        "completed": False,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
        "scores": None,
    }
    result = await db[COLLECTION].insert_one(new_doc)
    new_doc["_id"] = result.inserted_id
    return new_doc


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = str(doc.get("_id")) if doc.get("_id") is not None else None
    return out


# ============================================================
# Endpoints
# ============================================================
@router.get("/schema")
async def get_schema() -> Dict[str, Any]:
    """Return the full assessment schema for the UI to render."""
    return {
        "response_scale": RESPONSE_SCALE,
        "sections": SECTIONS,
        "total_questions": total_question_count(),
    }


@router.get("/me")
async def get_my_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the current user's in-progress OR most recent completed assessment."""
    doc = await db[COLLECTION].find_one(
        {"user_id": user.user_id}, sort=[("updated_at", -1)]
    )
    if not doc:
        return {"exists": False}
    return {"exists": True, **_serialize(doc)}


@router.post("/answer")
async def save_answer(
    body: AnswerIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    if find_question(body.question_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown question id: {body.question_id}")
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"][body.question_id] = body.value
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}},
    )
    return {"ok": True, "answered": len(doc["answers"]), "total": total_question_count()}


@router.post("/answers/bulk")
async def save_answers_bulk(
    body: AnswersBulkIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    ok, err = validate_answers(body.answers)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"].update(body.answers)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}},
    )
    return {"ok": True, "answered": len(doc["answers"]), "total": total_question_count()}


@router.post("/complete")
async def complete_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id, "completed": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="No in-progress assessment for this user.")
    scores = compute_scores(doc.get("answers") or {})
    now = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "completed": True,
                "completed_at": now,
                "updated_at": now,
                "scores": scores,
            }
        },
    )
    doc["completed"] = True
    doc["completed_at"] = now
    doc["updated_at"] = now
    doc["scores"] = scores
    return {"ok": True, **_serialize(doc)}


@router.get("/scores")
async def get_scores(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id}, sort=[("updated_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment found for this user.")
    if doc.get("scores"):
        return doc["scores"]
    return compute_scores(doc.get("answers") or {})


@router.delete("/me")
async def reset_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Delete all of the user's assessments (both in-progress and completed)."""
    result = await db[COLLECTION].delete_many({"user_id": user.user_id})
    return {"ok": True, "deleted": result.deleted_count}
