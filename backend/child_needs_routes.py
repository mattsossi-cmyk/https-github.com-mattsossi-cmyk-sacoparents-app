"""Self Journey Card 3 · Your Child's Specific Needs (Medical / Educational /
Psychological) — save-to-account + one combined branded PDF.

Copy lives in `child_needs_content.json`, mirrored at
`frontend/src/pages/portal/childNeedsContent.json` (lockstep test:
tests/test_child_needs.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
import child_needs_pdf

CONTENT: Dict[str, Any] = json.loads(
    (Path(__file__).parent / "child_needs_content.json").read_text(encoding="utf-8")
)
FIELDS = {c["key"]: {f["id"]: f for f in c["fields"]} for c in CONTENT["categories"]}

router = APIRouter(prefix="/child-needs", tags=["child-needs"])


def clean_category(category: str, answers: Dict[str, str]) -> Dict[str, str]:
    fields = FIELDS[category]
    out: Dict[str, str] = {}
    for fid, raw in (answers or {}).items():
        f = fields.get(fid)
        value = (raw or "").strip()[:2000] if isinstance(raw, str) else ""
        if not f or not value:
            continue
        if f["type"] == "select" and value not in f["options"]:
            continue
        out[fid] = value
    return out


def clean_all(answers: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {k: clean_category(k, v) for k, v in (answers or {}).items() if k in FIELDS}


class CategoryIn(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)


class ChildNeedsState(BaseModel):
    answers: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    completed_at: Dict[str, str] = Field(default_factory=dict)


class ChildNeedsPdfIn(BaseModel):
    parent_name: str = Field(default="", max_length=120)
    answers: Dict[str, Dict[str, str]] = Field(default_factory=dict)


@router.get("/me", response_model=ChildNeedsState)
async def get_my_child_needs(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ChildNeedsState:
    doc = await db.child_needs_assessments.find_one({"user_id": user.user_id}, {"_id": 0, "user_id": 0})
    return ChildNeedsState(**doc) if doc else ChildNeedsState()


@router.put("/me/{category}", response_model=ChildNeedsState)
async def save_category(
    category: str,
    body: CategoryIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ChildNeedsState:
    if category not in FIELDS:
        raise HTTPException(404, "Unknown assessment.")
    answers = clean_category(category, body.answers)
    if not answers:
        raise HTTPException(422, "Fill in at least one question before saving.")
    now = datetime.now(timezone.utc).isoformat()
    await db.child_needs_assessments.update_one(
        {"user_id": user.user_id},
        {"$set": {f"answers.{category}": answers, f"completed_at.{category}": now, "updated_at": now}},
        upsert=True,
    )
    return await get_my_child_needs(user, db)


def _safe_filename(name: Optional[str]) -> str:
    out = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in (name or "").strip())
    return out[:60] or "me"


@router.post("/pdf")
async def download_child_needs_pdf(body: ChildNeedsPdfIn):
    """Public on purpose (localStorage-first portal): renders whichever
    categories the parent has filled in."""
    answers = clean_all(body.answers)
    if not any(answers.values()):
        raise HTTPException(400, "Complete at least one assessment first.")
    pdf_bytes = child_needs_pdf.build_child_needs_pdf(
        content=CONTENT, parent_name=body.parent_name, answers=answers
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="SA_CoParents_Child_Specific_Needs_{_safe_filename(body.parent_name)}.pdf"'},
    )
