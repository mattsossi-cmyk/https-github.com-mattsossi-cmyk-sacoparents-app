"""Shared multi-turn Guide chat: one ongoing session per parent, stored per collection."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from self_assessment_ai import _GREY_ROCK, _ask, _grey_rock, _guard


def plain(text: str, limit: int) -> str:
    """Strip markdown the model sometimes adds (bold, headings, code ticks) and collapse whitespace."""
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    return " ".join(re.sub(r"[*`\"]", "", text).split())[:limit]


async def latest_chat(db: AsyncIOMotorDatabase, collection: str, uid: str) -> Dict[str, Any]:
    doc = await db[collection].find_one(
        {"user_id": uid}, {"_id": 0, "session_id": 1, "messages": 1}, sort=[("updated_at", -1)]
    )
    return doc or {"session_id": None, "messages": []}


async def new_chat(db: AsyncIOMotorDatabase, collection: str, uid: str) -> Dict[str, Any]:
    """Start a fresh session so a reload shows the new (empty) chat; reuses an already-empty latest one."""
    latest = await latest_chat(db, collection, uid)
    if latest["session_id"] and not latest["messages"]:
        return latest
    sid, now = uuid.uuid4().hex, datetime.now(timezone.utc).isoformat()
    await db[collection].insert_one({"user_id": uid, "session_id": sid, "messages": [], "created_at": now, "updated_at": now})
    return {"session_id": sid, "messages": []}


async def chat_turn(
    db: AsyncIOMotorDatabase,
    collection: str,
    request: Request,
    user: Any,
    *,
    session_id: str | None,
    message: str,
    voice: str,
    task: str,
    context: str,
    safety_flagged: bool,
) -> Dict[str, str]:
    """Answer one message using the stored transcript (last 12 turns) plus page context, then store both."""
    await _guard(request)
    sid = session_id or uuid.uuid4().hex
    doc = await db[collection].find_one({"user_id": user.user_id, "session_id": sid}, {"_id": 0, "messages": 1}) or {}
    transcript = "\n".join(
        f"{'Parent' if m['role'] == 'user' else 'Guide'}: {m['text']}" for m in (doc.get("messages") or [])[-12:]
    )
    message = message.strip()
    prompt = "".join([
        f"{context}\n\n" if context else "",
        f"Conversation so far:\n{transcript}\n\n" if transcript else "",
        f"Parent's new message: {message}",
    ])
    grey = await _grey_rock(request, user, safety_flagged)
    reply = plain(await _ask(voice + (_GREY_ROCK if grey else "") + task, prompt), 1200)
    now = datetime.now(timezone.utc).isoformat()
    turn = [{"role": "user", "text": message, "at": now}, {"role": "guide", "text": reply, "at": now}]
    await db[collection].update_one(
        {"user_id": user.user_id, "session_id": sid},
        {"$push": {"messages": {"$each": turn, "$slice": -60}}, "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"session_id": sid, "reply": reply}
