"""Self Journey Card 1 · Co-Parenting Self-Assessment — save-to-account + branded PDF.

Copy lives in `self_assessment_content.json`, mirrored byte-for-byte at
`frontend/src/pages/portal/selfAssessmentContent.json` (lockstep test:
tests/test_self_assessment.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from auth import UserPublic, get_current_user, get_db
import self_assessment_pdf

CONTENT: Dict[str, Any] = json.loads(
    (Path(__file__).parent / "self_assessment_content.json").read_text(encoding="utf-8")
)
SCALE_VALUES = {s["value"] for s in CONTENT["scale"]}
QUESTION_KEYS = {
    f"{s['key']}{i + 1}" for s in CONTENT["sections"] for i in range(len(s["questions"]))
}

router = APIRouter(prefix="/self-assessment", tags=["self-assessment"])


class SAMeta(BaseModel):
    parent_name: str = Field(default="", max_length=120)
    date: str = Field(default="", max_length=20)
    child: str = Field(default="", max_length=200)
    case_ref: str = Field(default="", max_length=120)


class SAFoundation(BaseModel):
    going_well: List[str] = Field(default_factory=lambda: ["", "", ""], max_length=3)
    improve: List[str] = Field(default_factory=lambda: ["", "", ""], max_length=3)
    shared_goals: str = Field(default="", max_length=3000)

    @field_validator("going_well", "improve")
    @classmethod
    def _cap_items(cls, v: List[str]) -> List[str]:
        return [(x or "")[:2000] for x in v]


class SAState(BaseModel):
    meta: SAMeta = Field(default_factory=SAMeta)
    answers: Dict[str, int] = Field(default_factory=dict)
    foundation: SAFoundation = Field(default_factory=SAFoundation)

    @field_validator("answers")
    @classmethod
    def _valid_answers(cls, v: Dict[str, int]) -> Dict[str, int]:
        return {k: val for k, val in v.items() if k in QUESTION_KEYS and val in SCALE_VALUES}


class SASaved(SAState):
    updated_at: Optional[str] = None


def compute_scores(answers: Dict[str, int]) -> Dict[str, Any]:
    sections = []
    for s in CONTENT["sections"]:
        n = len(s["questions"])
        score = sum(answers.get(f"{s['key']}{i + 1}", 0) for i in range(n))
        sections.append({
            "key": s["key"],
            "label": s["label"],
            "score": score,
            "max": n * max(SCALE_VALUES),
        })
    total = sum(r["score"] for r in sections)
    complete = len(answers) == len(QUESTION_KEYS)
    tier = next((t for t in CONTENT["tiers"] if total >= t["min"]), None) if complete else None
    return {
        "sections": sections,
        "total": total,
        "max": sum(r["max"] for r in sections),
        "answered": len(answers),
        "question_count": len(QUESTION_KEYS),
        "tier": tier,
    }


@router.get("/me", response_model=SASaved)
async def get_my_self_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SASaved:
    doc = await db.self_assessments.find_one({"user_id": user.user_id}, {"_id": 0, "user_id": 0})
    return SASaved(**doc) if doc else SASaved()


@router.put("/me", response_model=SASaved)
async def save_my_self_assessment(
    body: SAState,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SASaved:
    saved = SASaved(**body.model_dump(), updated_at=datetime.now(timezone.utc).isoformat())
    await db.self_assessments.update_one(
        {"user_id": user.user_id},
        {"$set": {**saved.model_dump(), "user_id": user.user_id}},
        upsert=True,
    )
    return saved


def _safe_filename(name: str) -> str:
    out = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in (name or "").strip())
    return out[:60] or "me"


@router.post("/pdf")
async def download_self_assessment_pdf(body: SAState):
    """Public on purpose: the portal is localStorage-first, so a parent
    without an account can still export their reflection."""
    pdf_bytes = self_assessment_pdf.build_self_assessment_pdf(
        content=CONTENT,
        state=body.model_dump(),
        scores=compute_scores(body.answers),
    )
    filename = f"SA_CoParents_Self_Assessment_{_safe_filename(body.meta.parent_name)}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
