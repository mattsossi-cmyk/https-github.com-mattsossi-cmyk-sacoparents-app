"""AI guide for the Court Ordered page: general process guidance, never legal advice."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from self_assessment_ai import _GREY_ROCK, _VOICE, _ask, _grey_rock, _guard, _optional_user

router = APIRouter(prefix="/court-path/ai", tags=["court-path"])

_TASK = (
    "The parent is on a court-ordered co-parenting path in the SA CoParents app. The app offers three modules "
    "(A Child Needs & Priorities, B Co-Parenting Dynamics, C Conflict Readiness), a court-ready summary PDF, "
    "a Communication Builder that rewrites messages in BIFF style (Brief, Informative, Friendly, Firm), and "
    "a professional site where their mediator, attorney or parenting coordinator reviews their reports. "
    "Answer their question in 2-4 short, plain sentences (max 90 words). You are not a lawyer: give general "
    "information only, never legal advice, never predict court outcomes or interpret their specific order, and "
    "never suggest ignoring or delaying a court order. Never claim the app's reports are certified, "
    "court-admissible, filed automatically, or that they satisfy a court order; the parent and their professional "
    "decide what to share with the court. For case-specific or legal questions, suggest they ask "
    "their attorney, mediator or the court. If they paste a message, offer a short BIFF version of it. "
    "Plain text only, one paragraph: no lists, headings, emojis or quotation marks."
)


class GuideBody(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    safety_flagged: bool = False


@router.post("/guide")
async def ai_guide(body: GuideBody, request: Request, user=Depends(_optional_user)) -> Dict[str, str]:
    await _guard(request)
    grey = await _grey_rock(request, user, body.safety_flagged)
    answer = await _ask(_VOICE + (_GREY_ROCK if grey else "") + _TASK, body.question.strip())
    return {"answer": " ".join(answer.split())[:900]}
