"""AI Insight for the Self-Assessment page (Claude via the app's shared AI setup).

* POST /self-assessment/ai/tip      — one gentle tip after each rated section (or overall).
* POST /self-assessment/ai/framing  — "Ask AI for communication framing".

Safety-flagged parents (server-side flag or client hint) get the grey-rock voice.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from ai_service import _extract_json, _make_chat
from auth import bearer, get_current_user
from self_assessment_reminders import is_safety_flagged
from self_assessment_routes import CONTENT
from emergentintegrations.llm.chat import UserMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/self-assessment/ai", tags=["self-assessment"])

SCALE = {s["value"]: s["label"] for s in CONTENT["scale"]}
SECTIONS = {s["key"]: s for s in CONTENT["sections"]}

_VOICE = (
    "You are the SA CoParents Guide, a warm, non-judgmental co-parenting reflection coach. "
    "Speak directly to the parent as 'you'. Never score, diagnose, or compare them to other parents. "
    "Never criticise or speculate about the other parent. Keep the child at the centre. "
)
_GREY_ROCK = (
    "This parent has flagged safety concerns. Focus only on their own wellbeing, boundaries and their "
    "child's stability. Favour brief, factual, written communication and parallel-parenting habits. "
    "Never suggest more contact, joint conversations, meeting in person, or compromise with the other parent. "
)
_TIP_TASK = (
    "The parent rated themselves 1-5 (1 Rarely, 2 Sometimes, 3 Developing, 4 Usually, 5 Consistently) in a "
    "private Self-Assessment. Write ONE gentle, practical tip in exactly 2 short sentences (max 50 words): "
    "briefly acknowledge one real strength from their highest rating, then offer one small, concrete step they "
    "could try this week for their lowest rating. Plain text only, one paragraph: no lists, headings, emojis or "
    "quotation marks."
)
_FRAMING_TASK = (
    "The parent describes a co-parenting situation or pastes a message they want to send. Return strict JSON "
    '{"advice": "...", "suggested": "..."}. advice: 1-2 sentences on how to frame it calmly and child-focused. '
    "suggested: a short message they could send (max 60 words) that is Brief, Informative, Friendly and Firm "
    "(BIFF), or an empty string if no message is needed."
)
_FRAMING_TASK_GREY = (
    "The parent describes a co-parenting situation or pastes a message they want to send. Return strict JSON "
    '{"advice": "...", "suggested": "..."}. advice: 1-2 sentences on keeping it minimal, factual and safe. '
    "suggested: a grey-rock message they could send (max 40 words): only logistics, no feelings, no "
    "apologies, no questions that invite debate. Use an empty string if no message is needed."
)


class TipBody(BaseModel):
    section: str = Field(..., max_length=40)
    answers: Dict[str, int] = Field(default_factory=dict)
    safety_flagged: bool = False
    # Saves the results tip onto this freshly completed entry (signed-in only).
    entry_id: Optional[str] = Field(default=None, max_length=64)


class FramingBody(BaseModel):
    text: str = Field(..., min_length=3, max_length=1000)
    safety_flagged: bool = False


async def _optional_user(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    try:
        return await get_current_user(request, creds)
    except HTTPException:
        return None


async def _grey_rock(request: Request, user, hint: bool) -> bool:
    return hint or bool(user and await is_safety_flagged(request.app.state.db, user.user_id))


async def _guard(request: Request) -> None:
    from portal_routes import _client_ip, _rate_guard
    await _rate_guard(_client_ip(request))


def _rated(section: dict, answers: Dict[str, int]) -> str:
    lines = []
    for i, q in enumerate(section["questions"]):
        v = answers.get(f"{section['key']}_{i + 1}")
        if v not in SCALE:
            raise HTTPException(status_code=400, detail="Please finish this step first.")
        lines.append(f"- {q} -> {v} ({SCALE[v]})")
    return "\n".join(lines)


def _tip_prompt(body: TipBody) -> str:
    if body.section == "overall":
        blocks = [f"{s['title']}:\n{_rated(s, body.answers)}" for s in CONTENT["sections"]]
        return "This is their full Self-Assessment. Base the tip on the whole picture.\n\n" + "\n\n".join(blocks)
    section = SECTIONS.get(body.section)
    if not section:
        raise HTTPException(status_code=400, detail="Unknown step.")
    return f"They just finished the step '{section['title']}':\n{_rated(section, body.answers)}"


async def _ask(system: str, prompt: str) -> str:
    try:
        return (await _make_chat(system, "claude").send_message(UserMessage(text=prompt))).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("self-assessment AI call failed: %s", exc)
        raise HTTPException(status_code=502, detail="The AI guide couldn't respond right now. Please try again.")


@router.post("/tip")
async def ai_tip(body: TipBody, request: Request, user=Depends(_optional_user)) -> Dict[str, str]:
    prompt = _tip_prompt(body)
    await _guard(request)
    grey = await _grey_rock(request, user, body.safety_flagged)
    tip = " ".join((await _ask(_VOICE + (_GREY_ROCK if grey else "") + _TIP_TASK, prompt)).replace('"', "").split())[:600]
    if user and body.entry_id and body.section == "overall":
        await request.app.state.db.self_assessment_history.update_one(
            {"user_id": user.user_id, "id": body.entry_id}, {"$set": {"tips.overall": tip}}
        )
    return {"tip": tip}


@router.post("/framing")
async def ai_framing(body: FramingBody, request: Request, user=Depends(_optional_user)) -> Dict[str, str]:
    await _guard(request)
    grey = await _grey_rock(request, user, body.safety_flagged)
    raw = await _ask(_VOICE + (_GREY_ROCK + _FRAMING_TASK_GREY if grey else _FRAMING_TASK), body.text.strip())
    try:
        data = _extract_json(raw)
    except ValueError:
        data = {"advice": raw, "suggested": ""}
    return {
        "advice": str(data.get("advice") or "").strip()[:600],
        "suggested": str(data.get("suggested") or "").strip()[:600],
    }
