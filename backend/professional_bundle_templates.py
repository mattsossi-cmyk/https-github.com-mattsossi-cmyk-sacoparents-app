"""Professional Bundle Templates — Iter197.

Lets a professional (mediator / attorney / therapist / coordinator)
save a favourite bundle of assessments — e.g. "High-conflict
co-parenting: Co-Parenting + Communication + Safety" — and then apply
it to a new case with one click instead of re-picking every lane.

Endpoints (all JWT-authed, mounted under `/api`):
  * GET    /professional/bundle-templates
        → returns the caller's templates only. Never leaks another
          professional's saved bundles.
  * POST   /professional/bundle-templates
        → creates a new template owned by the caller. Body:
          {name, primary_assessment_type, extra_steps:[{assessment_type,required}]}
  * DELETE /professional/bundle-templates/{template_id}
        → hard-deletes the template. Ownership guardrail: 404 if the
          template belongs to a different professional (never leak
          existence).

Data model (`professional_bundle_templates` collection):
  {
    _id:                    ObjectId,
    owner_user_id:          str,
    name:                   str  (max 120 chars, user-supplied label)
    primary_assessment_type: str  (validated against joint_alignment_routes._ASSESSMENT_TYPES)
    extra_steps: [
      { assessment_type: str, required: bool }, ...
    ],
    created_at:             datetime,
    updated_at:             datetime,
  }

Kept intentionally small — no versioning, no share-with-team, no
soft-delete. If a template proves useful cross-professional we'll
promote it to a shared library later.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db


router = APIRouter(tags=["professional-bundle-templates"])

_COLL = "professional_bundle_templates"
_MAX_TEMPLATES_PER_USER = 25  # soft cap — plenty of headroom for a
# power-user without letting a runaway script fill a professional's
# sidebar with 10k rows.


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BundleStepInput(BaseModel):
    assessment_type: str
    required: bool = True


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    primary_assessment_type: str
    extra_steps: List[BundleStepInput] = Field(default_factory=list)


class TemplatePublic(BaseModel):
    id: str
    name: str
    primary_assessment_type: str
    extra_steps: List[BundleStepInput]
    created_at: str
    updated_at: str


def _validate_assessment_type(t: str) -> str:
    """Local mirror of the routes-level validator so this module
    doesn't force a hard import from `joint_alignment_routes` (avoids
    a circular import when the routes file grows further)."""
    from joint_alignment_routes import _ASSESSMENT_TYPES
    if t not in _ASSESSMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown assessment_type — expected one of {sorted(_ASSESSMENT_TYPES)}",
        )
    return t


def _public_shape(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name") or "",
        "primary_assessment_type": doc.get("primary_assessment_type"),
        "extra_steps": [
            {"assessment_type": s.get("assessment_type"),
             "required": bool(s.get("required", True))}
            for s in (doc.get("extra_steps") or [])
        ],
        "created_at": (doc.get("created_at") or _now()).isoformat(),
        "updated_at": (doc.get("updated_at") or _now()).isoformat(),
    }


@router.get("/professional/bundle-templates")
async def list_bundle_templates(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the caller's saved bundle templates, newest first."""
    cursor = (
        db[_COLL].find({"owner_user_id": current.user_id})
        .sort("created_at", -1)
        .limit(_MAX_TEMPLATES_PER_USER)
    )
    templates = [_public_shape(doc) async for doc in cursor]
    return {"templates": templates}


@router.post("/professional/bundle-templates", response_model=TemplatePublic)
async def create_bundle_template(
    body: CreateTemplateRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Persist a new bundle template. Ownership scoped to the calling
    account — every downstream operation looks up by owner_user_id."""
    # Cap enforcement so a runaway integration can't pile up rows.
    count = await db[_COLL].count_documents({"owner_user_id": current.user_id})
    if count >= _MAX_TEMPLATES_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have {_MAX_TEMPLATES_PER_USER} saved bundles. "
                f"Delete one before saving another."
            ),
        )

    primary = _validate_assessment_type(body.primary_assessment_type)
    seen = {primary}
    extras_clean: List[Dict[str, Any]] = []
    for step in body.extra_steps:
        at = _validate_assessment_type(step.assessment_type)
        if at in seen:
            # Silently dedupe — primary is always required and can't
            # be listed twice.
            continue
        seen.add(at)
        extras_clean.append({"assessment_type": at, "required": bool(step.required)})

    now = _now()
    doc = {
        "owner_user_id": current.user_id,
        "name": body.name.strip(),
        "primary_assessment_type": primary,
        "extra_steps": extras_clean,
        "created_at": now,
        "updated_at": now,
    }
    res = await db[_COLL].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _public_shape(doc)


@router.delete("/professional/bundle-templates/{template_id}")
async def delete_bundle_template(
    template_id: str = Path(..., min_length=1, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Hard-delete. Returns 404 whenever the caller isn't the owner —
    never confirm existence of another professional's template."""
    try:
        oid = ObjectId(template_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Bundle template not found")

    res = await db[_COLL].delete_one({
        "_id": oid,
        "owner_user_id": current.user_id,
    })
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bundle template not found")
    return {"deleted": True, "id": template_id}
