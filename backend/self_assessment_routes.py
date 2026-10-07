"""Self Journey Card 1 · Self-Assessment (v2, chat-style).

Draft auto-save, an append-only history of completed assessments, and a
branded PDF. Copy lives in `self_assessment_content.json`, mirrored at
`frontend/src/pages/portal/selfAssessmentContent.json` (lockstep test:
tests/test_self_assessment.py).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from auth import UserPublic, get_current_user, get_db
import self_assessment_pdf

CONTENT: Dict[str, Any] = json.loads(
    (Path(__file__).parent / "self_assessment_content.json").read_text(encoding="utf-8")
)
SCALE_VALUES = {s["value"] for s in CONTENT["scale"]}
MAX_VALUE = max(SCALE_VALUES)
QUESTION_KEYS = [
    f"{s['key']}_{i + 1}" for s in CONTENT["sections"] for i in range(len(s["questions"]))
]
REFLECTION_KEYS = [q["key"] for q in CONTENT["reflection"]["questions"]]

router = APIRouter(prefix="/self-assessment", tags=["self-assessment"])


def _clean_answers(v: Dict[str, int]) -> Dict[str, int]:
    return {k: val for k, val in v.items() if k in QUESTION_KEYS and val in SCALE_VALUES}


def _clean_reflections(v: Dict[str, str]) -> Dict[str, str]:
    return {k: (val or "")[:2000] for k, val in v.items() if k in REFLECTION_KEYS}


class _Responses(BaseModel):
    answers: Dict[str, int] = Field(default_factory=dict)
    reflections: Dict[str, str] = Field(default_factory=dict)

    @field_validator("answers")
    @classmethod
    def clean_answers(cls, v: Dict[str, int]) -> Dict[str, int]:
        return _clean_answers(v)

    @field_validator("reflections")
    @classmethod
    def clean_reflections(cls, v: Dict[str, str]) -> Dict[str, str]:
        return _clean_reflections(v)


class SADraft(_Responses):
    started: bool = False
    parent_name: str = Field(default="", max_length=120)
    goal: Optional[str] = Field(default=None, max_length=1000)


class SADraftOut(SADraft):
    updated_at: Optional[str] = None


class SAEntry(BaseModel):
    id: str
    completed_at: str
    parent_name: str = ""
    answers: Dict[str, int]
    reflections: Dict[str, str] = Field(default_factory=dict)
    goal: str = ""
    scores: Dict[str, Any]


class SAHistoryOut(BaseModel):
    entries: List[SAEntry]
    current_goal: Optional[str] = None


class SAPdfItem(_Responses):
    completed_at: Optional[str] = Field(default=None, max_length=40)
    parent_name: str = Field(default="", max_length=120)
    goal: str = Field(default="", max_length=1000)


class SAPdfRequest(BaseModel):
    entry: SAPdfItem
    history: List[SAPdfItem] = Field(default_factory=list, max_length=100)


def band_for(score: int) -> Optional[Dict[str, Any]]:
    return next((b for b in CONTENT["bands"] if score >= b["min"]), None)


def compute_scores(answers: Dict[str, int]) -> Dict[str, Any]:
    sections = {}
    for s in CONTENT["sections"]:
        raw = sum(answers.get(f"{s['key']}_{i + 1}", 0) for i in range(len(s["questions"])))
        sections[s["key"]] = round(raw * 100 / (len(s["questions"]) * MAX_VALUE))
    total_raw = sum(answers.get(k, 0) for k in QUESTION_KEYS)
    return {
        "overall": round(total_raw * 100 / (len(QUESTION_KEYS) * MAX_VALUE)),
        "sections": sections,
        "answered": len(answers),
        "question_count": len(QUESTION_KEYS),
    }


@router.get("/me", response_model=SADraftOut)
async def get_my_draft(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SADraftOut:
    doc = await db.self_assessment_drafts.find_one({"user_id": user.user_id}, {"_id": 0, "user_id": 0})
    return SADraftOut(**doc) if doc else SADraftOut()


@router.put("/me", response_model=SADraftOut)
async def save_my_draft(
    body: SADraft,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SADraftOut:
    saved = SADraftOut(**body.model_dump(), updated_at=datetime.now(timezone.utc).isoformat())
    await db.self_assessment_drafts.update_one(
        {"user_id": user.user_id},
        {"$set": {**saved.model_dump(), "user_id": user.user_id}},
        upsert=True,
    )
    return saved


@router.post("/complete", response_model=SAEntry)
async def complete_assessment(
    body: SADraft,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SAEntry:
    if len(body.answers) != len(QUESTION_KEYS):
        raise HTTPException(422, f"All {len(QUESTION_KEYS)} rated questions must be answered.")
    entry = SAEntry(
        id=str(uuid.uuid4()),
        completed_at=datetime.now(timezone.utc).isoformat(),
        parent_name=body.parent_name,
        answers=body.answers,
        reflections=body.reflections,
        goal=(body.goal or "").strip(),
        scores=compute_scores(body.answers),
    )
    await db.self_assessment_history.insert_one({**entry.model_dump(), "user_id": user.user_id})
    await db.self_assessment_drafts.delete_one({"user_id": user.user_id})
    return entry


@router.get("/history", response_model=SAHistoryOut)
async def get_history(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SAHistoryOut:
    cursor = db.self_assessment_history.find(
        {"user_id": user.user_id}, {"_id": 0, "user_id": 0}
    ).sort("completed_at", 1)
    entries = [SAEntry(**d) for d in await cursor.to_list(100)]
    return SAHistoryOut(entries=entries, current_goal=(entries[-1].goal or None) if entries else None)


def _safe_filename(name: str) -> str:
    out = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in (name or "").strip())
    return out[:60] or "me"


@router.post("/pdf")
async def download_pdf(body: SAPdfRequest):
    """Public on purpose: the portal is localStorage-first, so a parent
    without an account can still export their reflection."""
    entry = body.entry.model_dump()
    entry["scores"] = compute_scores(body.entry.answers)
    history = []
    for h in body.history:
        item = h.model_dump()
        item["scores"] = compute_scores(h.answers)
        history.append(item)
    pdf_bytes = self_assessment_pdf.build_self_assessment_pdf(
        content=CONTENT, entry=entry, history=history, band_for=band_for
    )
    filename = f"SA_CoParents_Self_Assessment_{_safe_filename(body.entry.parent_name)}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
