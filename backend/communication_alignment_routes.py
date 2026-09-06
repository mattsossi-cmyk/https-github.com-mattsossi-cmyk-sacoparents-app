"""
Communication Alignment — API endpoints.

Mounted at `/api/communication-reflection` (parent-facing) and
`/api/communication-alignment` (paired-view / compare).

Endpoints
---------
GET  /communication-reflection/schema
    Return the question bank + likert labels + dimensions.
PUT  /communication-reflection
    Save the parent's answers + optional per-item notes + optional
    unsafe flag (indicates the parent bailed to the Safety pathway).
GET  /communication-reflection/mine
    Return the caller's stored answers + latest score.
POST /communication-alignment/compare
    Pair with a co-parent by share_id (existing snc2 pair) and return
    a neutral Compare payload:
        { self: {score,dims}, coparent: {score,dims}, gaps: [...],
          shared: [...], notes: {self, coparent} }.
POST /communication-alignment/compare/summary
    Regenerate a neutral LLM-authored 2-paragraph exec summary from
    the compare payload. Never adjudicates who is "right".
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from communication_reflection_questions import (
    DIMENSIONS,
    QUESTIONS,
    VERSION,
    public_schema,
    score,
    validate_answers,
)
from ai_summary_communication import generate_communication_summary


router = APIRouter(tags=["communication-alignment"])
logger = logging.getLogger(__name__)

_COLL = "communication_reflections"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v


# ------------------------------- schemas ------------------------------- #

class ReflectionSavePayload(BaseModel):
    # `Any` at the boundary so a malformed frontend payload gets
    # gracefully filtered by validate_answers() instead of 422-ing
    # the whole submission — matches the tolerant-input contract the
    # module docstring promises.
    answers: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[Dict[str, str]] = None
    intake_choice: Optional[str] = Field(
        default=None,
        description="One of the 5 intake keys: productive / difficult / high-conflict / very-limited / unsafe.",
    )


class CompareRequest(BaseModel):
    coparent_email: str


class CompareSummaryRequest(BaseModel):
    compare_payload: Dict[str, Any]
    model: Optional[str] = Field(default="claude", pattern="^(claude|gpt)$")


# ------------------------------- helpers ------------------------------- #

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


def _shape_public(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Same as `_shape_self` but with the private free-text `notes` and
    raw `answers` dropped. Used when returning the *co-parent's*
    branch of a compare payload — the caller sees the aggregated
    scores + intake choice, never the free-text.
    """
    shaped = _shape_self(doc)
    shaped.pop("notes", None)
    shaped.pop("answers", None)
    return shaped


def _diff_dimensions(
    self_dims: Dict[str, Any], coparent_dims: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Given the two parents' per-dimension scores, split into `shared`
    (within 15 points) and `gaps` (further apart). Every row includes
    the neutral label + blurb so the frontend / LLM prompt can render
    without extra lookups.
    """
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


# ------------------------------- endpoints ------------------------------- #

@router.get("/communication-reflection/schema")
async def get_schema():
    return public_schema()


@router.put("/communication-reflection")
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
    # Propagate to any open Joint Alignment Cases so a professional
    # sees the parent as "completed" on the communication lane.
    try:
        from joint_alignment_routes import mark_assessment_completed  # noqa: WPS433
        await mark_assessment_completed(db, current.user_id, "communication")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "score": scored}


@router.get("/communication-reflection/mine")
async def get_mine(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await _load_reflection(db, current.user_id)
    return _shape_self(doc)


@router.post("/communication-alignment/compare")
async def compare(
    body: CompareRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Pair by co-parent email. The sibling app can call this once both
    parents have completed their reflection; the shape mirrors the
    joint-report compare shape used elsewhere in the codebase.
    """
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
            detail="Complete your Communication Reflection before comparing.",
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
    coparent_shape = _shape_public(coparent_doc)
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


@router.post("/communication-alignment/compare/summary")
async def compare_summary(
    body: CompareSummaryRequest,
    current: UserPublic = Depends(get_current_user),
):
    """
    Regenerate the LLM-authored neutral exec summary for the current
    compare payload. Kept as a separate endpoint so the parent can
    switch between Claude / GPT without re-running the whole pair.
    """
    payload = body.compare_payload or {}
    if not payload.get("shared") and not payload.get("gaps"):
        raise HTTPException(
            status_code=400,
            detail="compare_payload missing shared/gaps",
        )
    try:
        summary = await generate_communication_summary(payload, model=body.model or "claude")
    except Exception as exc:  # pragma: no cover — fail-soft
        logger.warning("communication summary regen failed: %s", exc)
        raise HTTPException(status_code=502, detail="Summary regeneration failed")
    return {"summary": summary, "model": body.model or "claude"}
