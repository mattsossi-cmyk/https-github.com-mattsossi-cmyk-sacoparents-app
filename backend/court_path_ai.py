"""AI Court Assistant for the Court Ordered page: a multi-turn chat, general guidance only, never legal advice."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from court_checklist import build_checklist
from guide_chat import chat_turn, latest_chat, new_chat
from self_assessment_ai import _VOICE, _ask, _guard

router = APIRouter(prefix="/court-path/ai", tags=["court-path"])
CHATS = "court_path_chats"
STATUS_WORDS = {"done": "done", "in_progress": "in progress", "todo": "not started"}
SPLIT_KEYS = ("core_goals", "child_needs", "co_values", "commitments")
_SPLIT_TASK = (
    "You sort a parent's Foundation Statement draft into four sections of their Foundation Statement form. "
    "Return ONLY a JSON object with exactly these string keys: core_goals (hopes and goals for the child), "
    "child_needs (the child's needs and priorities), co_values (co-parenting principles and values), commitments "
    "(the parent's personal commitments). Use only what the draft says, lightly edited for clarity in neutral, "
    "child-focused first-person language. Do not invent names, facts or promises. Max 600 characters per value; "
    "use an empty string when nothing fits. No markdown."
)

_TASK = (
    "You are now the SA CoParents Court Assistant. The parent is on a court-ordered co-parenting path in the app: "
    "Self Journey steps (Self-Assessment, Co-Parenting Relationship assessment, Child Needs, Foundation Statement), "
    "court modules (A Child Needs & Priorities, B Co-Parenting Dynamics, C Conflict Readiness), a court-ready "
    "summary PDF, a Court checklist PDF, a Communication Builder that rewrites messages in BIFF style (Brief, "
    "Informative, Friendly, Firm), and a professional site where their mediator, attorney or parenting coordinator "
    "reviews their reports. You are not a lawyer: give general information only, never legal advice, never predict "
    "court outcomes or interpret their specific order, and never suggest ignoring or delaying a court order. Never "
    "claim the app's reports are certified, court-admissible, filed automatically, or that they satisfy a court "
    "order; the parent and their professional decide what to share with the court. For case-specific or legal "
    "questions, suggest they ask their attorney, mediator or the court. If they paste a message, offer a short BIFF "
    "version of it. If they mention danger or abuse, share: call 911 in an emergency, or the National Domestic "
    "Violence Hotline at 1-800-799-7233. If they ask you to draft a Foundation Statement or a message, ALWAYS reply "
    "with ONLY the draft itself, even if they already have one: no clarifying questions, no intro, no notes before or "
    "after it. Use what you know about them and a placeholder like [child's name] for anything missing. Keep it a "
    "short child-focused draft in neutral first-person language (max 130 words) they can edit. Otherwise reply in "
    "2-4 short sentences (max 90 words). Plain text only: no markdown, asterisks, lists, headings or emojis, and "
    "don't open with a greeting after the first reply."
)


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None, max_length=64)
    modules: Dict[str, Literal["completed", "in_progress", "not_yet"]] = Field(default_factory=dict)
    safety_flagged: bool = False


@router.get("/chat")
async def get_chat(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    return await latest_chat(db, CHATS, user.user_id)


@router.post("/chat/new")
async def start_new_chat(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    return await new_chat(db, CHATS, user.user_id)


@router.post("/chat")
async def chat(
    body: ChatBody, request: Request, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, str]:
    checklist = await build_checklist(db, user, body.modules)
    lines = [f"- {i['label']}: {STATUS_WORDS[i['status']]}" for i in checklist["items"] if i["key"] != "case"]
    case = "verified" if checklist["case_ref"] else "not entered yet"
    context = f"The parent's court path progress (case code {case}):\n" + "\n".join(lines)
    return await chat_turn(
        db, CHATS, request, user, session_id=body.session_id, message=body.message,
        voice=_VOICE, task=_TASK, context=context, safety_flagged=body.safety_flagged,
    )


class SplitBody(BaseModel):
    text: str = Field(..., min_length=20, max_length=3000)


@router.post("/foundation-split")
async def foundation_split(body: SplitBody, request: Request, user: UserPublic = Depends(get_current_user)) -> Dict[str, str]:
    """Split an AI-drafted Foundation Statement into the Step 4 boxes."""
    await _guard(request)
    raw = await _ask(_SPLIT_TASK, body.text.strip())
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
    except ValueError:
        data = {}
    out = {k: " ".join(str(data.get(k) or "").replace("*", "").split())[:600] for k in SPLIT_KEYS}
    if not any(out.values()):
        raise HTTPException(status_code=502, detail="We couldn't sort that draft right now. Please try again.")
    return out
