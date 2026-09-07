"""Interactive AI Coach chat routes.

Multi-turn GPT chat (Claude fallback) that helps a parent move from
emotionally reactive to child-centered — BIFF-first, prep-aware, and
safety-alert. Sessions and messages are persisted to Mongo so a parent
can pick a conversation back up later. Model choice is app-wide
primary by default; a per-message `model` field (`"gpt"` | `"claude"`)
lets parents switch tone on demand.

Endpoints (mounted under /api/coach):
  POST   /sessions                       — create a new session
  GET    /sessions                       — list sessions (newest first)
  GET    /sessions/{session_id}          — fetch session + full history
  POST   /sessions/{session_id}/message  — send a user message, get AI reply
  DELETE /sessions/{session_id}          — delete a session (and messages)
  GET    /starters                       — a small library of suggested
                                            opening prompts, used by the
                                            empty state on the /coach page
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

import ai_service
from auth import get_current_user
from models import UserPublic


router = APIRouter(prefix="/coach", tags=["coach"])


# ---- constants ------------------------------------------------------------
MAX_MESSAGE_LEN = 4000
MAX_HISTORY_TURNS = 40  # sanity ceiling; the LLM prompt itself is capped to 20
DEFAULT_TITLE = "New conversation"

# Empty-state suggestions surfaced on the /coach page. Ordered so the most
# common heat-of-the-moment scenario appears first.
STARTER_PROMPTS = [
    {
        "id": "just_had_hard_exchange",
        "label": "I just had a hard exchange with my co-parent",
        "prompt": "I just had a hard exchange with my co-parent and I feel really activated. Help me sort through what happened before I say something I'll regret.",
    },
    {
        "id": "draft_biff_reply",
        "label": "Help me draft a BIFF reply",
        "prompt": "My co-parent sent me a message that pushed my buttons and I need help drafting a Brief, Informative, Friendly, Firm reply. I'll paste the message next.",
    },
    {
        "id": "child_transition_hard",
        "label": "My child is struggling with transitions",
        "prompt": "My child has been having a really hard time with the handoff between our two homes. What can I try?",
    },
    {
        "id": "pre_mediation_nerves",
        "label": "I have mediation coming up and I'm anxious",
        "prompt": "I have a mediation session coming up and I'm feeling anxious. Help me center myself and get clear on what actually matters for my child.",
    },
    {
        "id": "co_parent_wont_communicate",
        "label": "My co-parent won't respond to me",
        "prompt": "My co-parent has stopped responding to my messages about our child's schedule. What are my options that keep the focus on our child?",
    },
]


# ---- helpers --------------------------------------------------------------
def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_title(text: str) -> str:
    """Turn the first user message into a short session title."""
    clean = " ".join((text or "").split())
    if not clean:
        return DEFAULT_TITLE
    if len(clean) <= 60:
        return clean
    return clean[:57].rstrip() + "…"


async def _get_session_or_404(db, user_id: str, session_id: str) -> Dict[str, Any]:
    doc = await db.coach_sessions.find_one(
        {"session_id": session_id, "user_id": user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Coach session not found")
    return doc


async def _load_history(db, session_id: str) -> List[Dict[str, Any]]:
    cursor = db.coach_messages.find(
        {"session_id": session_id}, {"_id": 0}
    ).sort("created_at", 1)
    return await cursor.to_list(MAX_HISTORY_TURNS * 2)


async def _load_prep_context(db, user_id: str) -> Optional[Dict[str, Any]]:
    """Pull the small subset of prep data the coach actually uses so we
    don't ship irrelevant fields into the LLM prompt."""
    doc = await db.prep_data.find_one(
        {"user_id": user_id},
        {
            "_id": 0,
            "child_goals": 1,
            "reflection": 1,
            "priority": 1,
            "child_name": 1,
        },
    )
    return doc or None


# ---- request bodies -------------------------------------------------------
class NewSessionBody(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)


class SendMessageBody(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LEN)
    # Per-message override — "gpt" | "claude" | None (use app-wide primary).
    # Lets parents toggle tone from the chat surface (`/coach`) without
    # changing the app-wide default.
    model: Optional[str] = Field(default=None, max_length=20)


# ---- endpoints ------------------------------------------------------------
@router.get("/starters")
async def list_starter_prompts():
    return {"starters": STARTER_PROMPTS}


@router.post("/sessions")
async def create_session(
    body: NewSessionBody,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    session_id = f"coach_{uuid.uuid4().hex[:12]}"
    doc = {
        "session_id": session_id,
        "user_id": current.user_id,
        "title": (body.title or DEFAULT_TITLE).strip()[:120],
        "created_at": _now(),
        "updated_at": _now(),
        "message_count": 0,
        "safety_flag": False,
    }
    await db.coach_sessions.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/sessions")
async def list_sessions(
    request: Request,
    current: UserPublic = Depends(get_current_user),
    limit: int = 30,
):
    db = request.app.state.db
    limit = max(1, min(limit, 100))
    cursor = db.coach_sessions.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("updated_at", -1).limit(limit)
    sessions = await cursor.to_list(limit)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    session = await _get_session_or_404(db, current.user_id, session_id)
    messages = await _load_history(db, session_id)
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    await _get_session_or_404(db, current.user_id, session_id)
    await db.coach_sessions.delete_one(
        {"session_id": session_id, "user_id": current.user_id}
    )
    await db.coach_messages.delete_many({"session_id": session_id})
    return {"ok": True}


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    body: SendMessageBody,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    session = await _get_session_or_404(db, current.user_id, session_id)

    user_content = body.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    now = _now()

    # Persist the user turn first so the history is complete even if the
    # LLM call fails.
    user_msg = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "session_id": session_id,
        "user_id": current.user_id,
        "role": "user",
        "content": user_content,
        "created_at": now,
    }
    await db.coach_messages.insert_one(user_msg.copy())
    user_msg.pop("_id", None)

    # Build the multi-turn history for the LLM (excluding the just-inserted
    # user message — we pass that as the new user_message instead).
    history_docs = await _load_history(db, session_id)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in history_docs
        if m.get("message_id") != user_msg["message_id"]
    ]

    prep_context = await _load_prep_context(db, current.user_id)

    try:
        ai_result = await ai_service.generate_coach_reply(
            user_message=user_content,
            history=history,
            prep_context=prep_context,
            model_preference=body.model,
        )
    except Exception as e:  # noqa: BLE001
        # Roll back the user turn so the parent can re-try cleanly without
        # accumulating orphaned turns in the transcript.
        await db.coach_messages.delete_one({"message_id": user_msg["message_id"]})
        raise HTTPException(status_code=502, detail=f"AI coach unavailable: {e}")

    assistant_msg = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "session_id": session_id,
        "user_id": current.user_id,
        "role": "assistant",
        "content": ai_result["reply"],
        "suggested_followups": ai_result.get("suggested_followups") or [],
        "safety_flag": bool(ai_result.get("safety_flag", False)),
        "created_at": _now(),
    }
    await db.coach_messages.insert_one(assistant_msg.copy())
    assistant_msg.pop("_id", None)

    # Bump session metadata. If this is the first user message on a "New
    # conversation" session, promote it into a real title.
    updates: Dict[str, Any] = {
        "updated_at": _now(),
        "message_count": (session.get("message_count") or 0) + 2,
    }
    if assistant_msg["safety_flag"]:
        updates["safety_flag"] = True
    if (session.get("title") or DEFAULT_TITLE) == DEFAULT_TITLE and (
        session.get("message_count") or 0
    ) == 0:
        updates["title"] = _derive_title(user_content)
    await db.coach_sessions.update_one(
        {"session_id": session_id, "user_id": current.user_id},
        {"$set": updates},
    )

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "session_updates": updates,
    }
