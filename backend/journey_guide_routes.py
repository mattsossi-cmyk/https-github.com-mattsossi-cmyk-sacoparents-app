"""Remembered Guide chats for the full-screen Self Journey pages (Co-Parenting Assessment, Child Needs)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from child_needs_routes import CONTENT as NEEDS_CONTENT, FIELDS as NEEDS_FIELDS
from guide_chat import chat_turn, latest_chat, new_chat, plain
from self_assessment_ai import _ask, _guard

router = APIRouter(prefix="/journey-guide", tags=["journey-guide"])

_SHARED = (
    "Speak to the parent as 'you'. Never criticise or speculate about the other parent, and keep the child at the "
    "centre. You are not a lawyer, doctor or therapist: give general guidance only, never legal, medical or "
    "psychological advice, and suggest a qualified professional when it would help. If the parent mentions danger, "
    "abuse or fear for their safety, gently share: call 911 in an emergency, or the National Domestic Violence "
    "Hotline at 1-800-799-7233. "
)
_TASK = (
    "Reply to the parent's new message in 2-4 short sentences (max 90 words). Plain text only: no markdown, "
    "asterisks, lists, headings or emojis, and don't open with a greeting after the first reply."
)
TOPICS: Dict[str, Dict[str, str]] = {
    "self-assessment": {
        "collection": "self_assessment_guide_chats",
        "voice": (
            "You are the SA CoParents Self-Assessment Guide, a calm, supportive coach helping one parent reflect on "
            "their own co-parenting strengths and growth areas (child focus, self-awareness, communication, working "
            "through differences) and set one realistic personal goal. Help them reflect honestly; never tell them "
            "which rating to pick. "
        ),
        "where": "They are on: {}.",
    },
    "coparenting": {
        "collection": "coparenting_guide_chats",
        "voice": (
            "You are the SA CoParents Co-Parenting Guide, a calm, supportive coach helping one parent reflect on their "
            "co-parenting relationship while they complete the Co-Parenting Relationship Assessment. Help them "
            "understand what a question or section is asking and reflect honestly; never tell them which answer to pick. "
        ),
        "where": "They are on the assessment section: {}.",
    },
    "child-needs": {
        "collection": "child_needs_guide_chats",
        "voice": (
            "You are the SA CoParents Child Needs Guide, a calm, supportive coach helping one parent describe their "
            "child's educational, medical and psychological needs so both homes can support the child consistently. "
            "You never diagnose or evaluate the child. "
        ),
        "where": "They are filling in: {}.",
    },
}


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None, max_length=64)
    section: Optional[str] = Field(default=None, max_length=120)
    safety_flagged: bool = False


_SUGGEST_TASK = (
    "Write a short draft answer (1-3 sentences, max 60 words) in the parent's own voice for the form question "
    "below, so they can edit it. Answer only that question; use the parent's other answers as background only. If the parent has started an answer, polish it and keep every fact they gave. "
    "Never invent names, diagnoses, medications, schools, providers or other facts: use square-bracket "
    "placeholders like [school name] or [medication] for anything you don't know. Never include Social Security, "
    "insurance or account numbers. Plain text only: no markdown, quotes, lists or preamble."
)


class SuggestBody(BaseModel):
    category: str = Field(..., max_length=40)
    field_id: str = Field(..., max_length=60)
    draft: str = Field(default="", max_length=2000)
    answers: Dict[str, str] = Field(default_factory=dict)


@router.post("/child-needs/suggest")
async def suggest_child_needs_answer(
    body: SuggestBody, request: Request, user: UserPublic = Depends(get_current_user)
) -> Dict[str, str]:
    field = NEEDS_FIELDS.get(body.category, {}).get(body.field_id)
    if not field or field["type"] in ("select", "rating") or field.get("help") is False:
        raise HTTPException(status_code=404, detail="Unknown question.")
    await _guard(request)
    cat = next(c for c in NEEDS_CONTENT["categories"] if c["key"] == body.category)
    labels = {f["id"]: f["label"] for f in cat["fields"]}
    others = "\n".join(
        f"- {labels[k]}: {str(v)[:300]}" for k, v in body.answers.items() if k in labels and k != body.field_id and str(v).strip()
    )
    prompt = "".join([
        f"Form: {cat['form_title']}\nQuestion: {field['label']}\n",
        f"Example hint shown to the parent: {field['placeholder']}\n" if field.get("placeholder") else "",
        f"Other answers the parent gave in this form:\n{others}\n" if others else "",
        f"Parent's current draft: {body.draft.strip() or '(empty)'}",
    ])
    text = await _ask(TOPICS["child-needs"]["voice"] + _SHARED + _SUGGEST_TASK, prompt)
    return {"suggestion": plain(text, 600)}


def _topic(topic: str) -> Dict[str, str]:
    if topic not in TOPICS:
        raise HTTPException(status_code=404, detail="Unknown guide.")
    return TOPICS[topic]


@router.get("/{topic}/chat")
async def get_chat(
    topic: str, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    return await latest_chat(db, _topic(topic)["collection"], user.user_id)


@router.post("/{topic}/chat/new")
async def start_new_chat(
    topic: str, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    return await new_chat(db, _topic(topic)["collection"], user.user_id)


@router.post("/{topic}/chat")
async def chat(
    topic: str,
    body: ChatBody,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, str]:
    t = _topic(topic)
    return await chat_turn(
        db, t["collection"], request, user, session_id=body.session_id, message=body.message,
        voice=t["voice"] + _SHARED, task=_TASK, context=t["where"].format(body.section) if body.section else "",
        safety_flagged=body.safety_flagged,
    )
