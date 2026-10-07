"""Self Journey Card 1 · Self-Assessment (v2, chat-style).

Draft auto-save, an append-only history of completed assessments, and a
branded PDF. Copy lives in `self_assessment_content.json`, mirrored at
`frontend/src/pages/portal/selfAssessmentContent.json` (lockstep test:
tests/test_self_assessment.py).
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from auth import UserPublic, get_current_user, get_db
import self_assessment_pdf
from self_assessment_reminders import read_unsubscribe_token

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


class SAGoalPractice(BaseModel):
    entry_id: str
    count: int = 0
    last_date: Optional[str] = None
    recent_dates: List[str] = Field(default_factory=list)


class SAHistoryOut(BaseModel):
    entries: List[SAEntry]
    current_goal: Optional[str] = None
    goal_practice: Optional[SAGoalPractice] = None


class SACheckin(BaseModel):
    entry_id: str = Field(..., max_length=64)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


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
    if not entries:
        return SAHistoryOut(entries=[])
    latest = entries[-1]
    return SAHistoryOut(
        entries=entries,
        current_goal=latest.goal or None,
        goal_practice=await _goal_practice(db, user.user_id, latest.id),
    )


async def _goal_practice(db: AsyncIOMotorDatabase, user_id: str, entry_id: str) -> SAGoalPractice:
    rows = await db.self_assessment_checkins.find(
        {"user_id": user_id, "entry_id": entry_id}, {"_id": 0, "date": 1}
    ).to_list(1000)
    dates = sorted(r["date"] for r in rows)
    return SAGoalPractice(
        entry_id=entry_id, count=len(dates), last_date=dates[-1] if dates else None, recent_dates=dates[-60:]
    )


@router.post("/goal/checkin", response_model=SAGoalPractice)
async def goal_checkin(
    body: SACheckin,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SAGoalPractice:
    """'I practised this today' — at most one check-in per local date per goal."""
    try:
        day = date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(422, "Invalid date.")
    today = datetime.now(timezone.utc).date()
    if not (today - timedelta(days=1) <= day <= today + timedelta(days=1)):
        raise HTTPException(422, "Check-ins can only be recorded for today.")
    if not await db.self_assessment_history.find_one({"user_id": user.user_id, "id": body.entry_id}, {"_id": 1}):
        raise HTTPException(404, "Self-Assessment not found.")
    await db.self_assessment_checkins.update_one(
        {"user_id": user.user_id, "entry_id": body.entry_id, "date": body.date},
        {"$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return await _goal_practice(db, user.user_id, body.entry_id)


_UNSUB_PAGE = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head><body style="font-family:Arial,sans-serif;background:#f3effe;margin:0;padding:40px 16px;">
<div style="max-width:440px;margin:0 auto;background:#fff;border-radius:16px;padding:28px;text-align:center;">
<h1 style="color:#4c2889;font-size:20px;margin:0 0 10px;">{title}</h1>
<p style="color:#475569;font-size:14px;line-height:1.5;margin:0;">{body}</p></div></body></html>"""


@router.get("/reminders/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_reminders(token: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> HTMLResponse:
    user_id = read_unsubscribe_token(token)
    if not user_id:
        return HTMLResponse(_UNSUB_PAGE.format(title="Link not valid",
                                               body="This unsubscribe link isn't valid."), status_code=400)
    await db.self_assessment_reminder_prefs.update_one(
        {"user_id": user_id},
        {"$set": {"unsubscribed": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return HTMLResponse(_UNSUB_PAGE.format(
        title="You're unsubscribed",
        body="You won't receive reflection check-in emails anymore. Your reflections stay saved in your account.",
    ))


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
