"""Self Journey · Parallel Parenting Option Builder: saved plan, AI step tips, guide chat, branded PDF.

Copy lives in `parallel_parenting_content.json`, mirrored at
`frontend/src/pages/portal/parallel/ppContent.json`.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from auth import UserPublic, get_current_user, get_db
from self_assessment_ai import _GREY_ROCK, _ask, _grey_rock, _guard
import parallel_parenting_pdf

CONTENT: Dict[str, Any] = json.loads(
    (Path(__file__).parent / "parallel_parenting_content.json").read_text(encoding="utf-8")
)
STEPS = {s["key"]: s for s in CONTENT["steps"]}
OPTIONS = {q["id"]: {o["id"]: o for o in q["options"]} for s in CONTENT["steps"] for q in s["questions"]}
PLANS = "parallel_parenting_plans"
CHATS = "parallel_parenting_chats"

router = APIRouter(prefix="/parallel-parenting", tags=["parallel-parenting"])

_VOICE = (
    "You are the SA CoParents Parallel Parenting Guide, a calm, supportive coach helping one parent build a "
    "parallel parenting plan: each parent runs their own home and time with the child, with minimal, structured, "
    "written contact between parents. Speak to the parent as 'you'. Never criticise or speculate about the other "
    "parent, and keep the child at the centre. You are not a lawyer or therapist: give general guidance only, never "
    "legal advice, and remind them an existing court order always comes first when relevant. If the parent "
    "mentions danger, abuse or fear for their safety, gently share: call 911 in an emergency, or the National "
    "Domestic Violence Hotline at 1-800-799-7233. "
)
_TIP_TASK = (
    "The parent just finished one step of their Parallel Parenting Option Builder. Write ONE gentle, practical tip "
    "in exactly 2 short sentences (max 50 words) that helps them put these choices into practice this week. "
    "Plain text only, one paragraph: no lists, headings, emojis or quotation marks."
)
_CHAT_TASK = (
    "Reply to the parent's new message in 2-4 short sentences (max 90 words). Plain text only: no markdown, "
    "asterisks, lists, headings or emojis, and don't open with a greeting after the first reply. When it helps, "
    "point them to the right step of the builder: 1 Communication Boundaries, "
    "2 Parenting Time & Exchanges, 3 Decision-Making, 4 Information Sharing, 5 Household Routines, "
    "6 Changes & Disagreements."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plain(text: str, limit: int) -> str:
    """Strip markdown the model sometimes adds (bold, headings, code ticks) and collapse whitespace."""
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    return " ".join(re.sub(r"[*`\"]", "", text).split())[:limit]


class PlanBody(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)
    notes: Dict[str, str] = Field(default_factory=dict)
    step: int = Field(default=0, ge=0, le=len(CONTENT["steps"]))
    completed: bool = False

    @field_validator("answers")
    @classmethod
    def _answers(cls, v: Dict[str, str]) -> Dict[str, str]:
        return {k: o for k, o in (v or {}).items() if o in OPTIONS.get(k, {})}

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: Dict[str, str]) -> Dict[str, str]:
        return {k: t[:1000] for k, t in (v or {}).items() if k in STEPS and isinstance(t, str)}


class PlanState(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)
    notes: Dict[str, str] = Field(default_factory=dict)
    tips: Dict[str, str] = Field(default_factory=dict)
    step: int = 0
    completed_at: Optional[str] = None
    updated_at: Optional[str] = None


class TipBody(BaseModel):
    step: str = Field(..., max_length=40)
    answers: Dict[str, str] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=1000)
    safety_flagged: bool = False


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None, max_length=64)
    step: Optional[str] = Field(default=None, max_length=40)
    safety_flagged: bool = False


async def _plan(db: AsyncIOMotorDatabase, uid: str) -> PlanState:
    doc = await db[PLANS].find_one({"user_id": uid}, {"_id": 0, "user_id": 0})
    return PlanState(**doc) if doc else PlanState()


def _choices(step: Dict[str, Any], answers: Dict[str, str]) -> List[str]:
    picked = [(q, OPTIONS[q["id"]].get(answers.get(q["id"], ""))) for q in step["questions"]]
    return [f"- {q['text']} -> {o['label']}" for q, o in picked if o]


def _plan_summary(plan: PlanState) -> str:
    blocks = [f"{s['title']}:\n" + "\n".join(lines) for s in CONTENT["steps"] if (lines := _choices(s, plan.answers))]
    return "\n".join(blocks)


@router.get("/me", response_model=PlanState)
async def get_plan(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> PlanState:
    return await _plan(db, user.user_id)


@router.put("/me", response_model=PlanState)
async def save_plan(
    body: PlanBody, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> PlanState:
    fields = {"answers": body.answers, "notes": body.notes, "step": body.step, "updated_at": _now()}
    if body.completed and not (await _plan(db, user.user_id)).completed_at:
        fields["completed_at"] = fields["updated_at"]
    await db[PLANS].update_one({"user_id": user.user_id}, {"$set": fields}, upsert=True)
    return await _plan(db, user.user_id)


@router.post("/ai/tip")
async def ai_tip(
    body: TipBody, request: Request, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, str]:
    step = STEPS.get(body.step)
    if not step:
        raise HTTPException(status_code=400, detail="Unknown step.")
    lines = _choices(step, body.answers)
    if not lines:
        raise HTTPException(status_code=400, detail="Choose at least one option in this step first.")
    await _guard(request)
    grey = await _grey_rock(request, user, body.safety_flagged)
    prompt = f"Step: {step['title']}\nTheir choices:\n" + "\n".join(lines)
    if body.notes.strip():
        prompt += f"\nTheir note: {body.notes.strip()}"
    tip = _plain(await _ask(_VOICE + (_GREY_ROCK if grey else "") + _TIP_TASK, prompt), 600)
    await db[PLANS].update_one({"user_id": user.user_id}, {"$set": {f"tips.{step['key']}": tip}}, upsert=True)
    return {"tip": tip}


@router.get("/ai/chat")
async def get_chat(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[CHATS].find_one(
        {"user_id": user.user_id}, {"_id": 0, "session_id": 1, "messages": 1}, sort=[("updated_at", -1)]
    )
    return doc or {"session_id": None, "messages": []}


@router.post("/ai/chat")
async def chat(
    body: ChatBody, request: Request, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, str]:
    await _guard(request)
    sid = body.session_id or uuid.uuid4().hex
    doc = await db[CHATS].find_one({"user_id": user.user_id, "session_id": sid}, {"_id": 0, "messages": 1}) or {}
    transcript = "\n".join(
        f"{'Parent' if m['role'] == 'user' else 'Guide'}: {m['text']}" for m in (doc.get("messages") or [])[-12:]
    )
    summary = _plan_summary(await _plan(db, user.user_id))
    step = STEPS.get(body.step or "")
    message = body.message.strip()
    prompt = "".join([
        f"The parent's plan choices so far:\n{summary}\n\n" if summary else "",
        f"They are on the step: {step['title']}.\n\n" if step else "",
        f"Conversation so far:\n{transcript}\n\n" if transcript else "",
        f"Parent's new message: {message}",
    ])
    grey = await _grey_rock(request, user, body.safety_flagged)
    reply = _plain(await _ask(_VOICE + (_GREY_ROCK if grey else "") + _CHAT_TASK, prompt), 1200)
    now = _now()
    turn = [{"role": "user", "text": message, "at": now}, {"role": "guide", "text": reply, "at": now}]
    await db[CHATS].update_one(
        {"user_id": user.user_id, "session_id": sid},
        {"$push": {"messages": {"$each": turn, "$slice": -60}}, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"session_id": sid, "reply": reply}


@router.post("/pdf")
async def download_plan_pdf(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    plan = await _plan(db, user.user_id)
    if not plan.answers and not any(v.strip() for v in plan.notes.values()):
        raise HTTPException(status_code=400, detail="Choose at least one option first.")
    pdf_bytes = parallel_parenting_pdf.build_pp_pdf(CONTENT, plan.model_dump(), user.name)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="SA_CoParents_Parallel_Parenting_Plan.pdf"'},
    )
