"""Journal routes — daily quick entries, formal-reflection snapshots, and a
weekly AI recap.

Collection: `journal_entries`
Shape:
    {
        "entry_id": str,        # short uuid
        "user_id": str,
        "kind": "daily" | "reflection_snapshot",
        "content": str,         # plain text (free-form for daily; formatted block for snapshots)
        "prompt_id": str|None,  # which daily prompt this answered
        "prompt_text": str|None,
        "created_at": str,      # ISO datetime
        "week_iso": str,        # 'YYYY-Www' bucket — cheap weekly grouping
    }

Collection: `journal_recaps`
Shape:
    {
        "user_id": str,
        "week_iso": str,
        "recap_text": str,
        "themes": List[str],
        "generated_at": str,
    }
"""
import hashlib
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import ai_service
from auth import get_current_user
from models import UserPublic

router = APIRouter(prefix="/journal", tags=["journal"])


# ============ Helpers ============
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _week_iso(dt: Optional[datetime] = None) -> str:
    """Return ISO-week bucket key (e.g. '2026-W05')."""
    d = dt or _now()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


# ============ Daily prompts ============
DAILY_PROMPTS = [
    {"id": "win_today",       "text": "What did you do well today as a parent?"},
    {"id": "trigger",         "text": "What triggered me today — and what did I do with it?"},
    {"id": "child_eyes",      "text": "If my child described today, what would they say?"},
    {"id": "small_choice",    "text": "Name one small choice I made today that I'm proud of."},
    {"id": "grace",           "text": "Where can I extend a little grace to myself or my co-parent today?"},
    {"id": "feeling_word",    "text": "If I had to pick one word for how I felt today, what would it be — and why?"},
    {"id": "release",         "text": "What am I carrying that I'd like to set down before tomorrow?"},
    {"id": "ask_for_help",    "text": "What would 'asking for help' look like for me this week?"},
    {"id": "calm_anchor",     "text": "What helped me feel calm today, even briefly?"},
    {"id": "future_self",     "text": "What would my future self thank me for doing this week?"},
    {"id": "gratitude_kid",   "text": "What's one thing my child did today that I want to remember?"},
    {"id": "boundary",        "text": "Is there a boundary I want to hold gently this week?"},
    {"id": "story_telling",   "text": "What story am I telling myself right now — and is it serving me?"},
    {"id": "regret",          "text": "Is there anything from today I'd like to repair, with myself or someone else?"},
]


def _prompt_for_date(d: datetime) -> dict:
    """Deterministically pick a prompt per-day (by day-of-year)."""
    idx = d.timetuple().tm_yday % len(DAILY_PROMPTS)
    return DAILY_PROMPTS[idx]


# ============ Pydantic models ============
class JournalEntryIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    prompt_id: Optional[str] = None


class JournalEntryOut(BaseModel):
    entry_id: str
    kind: str
    content: str
    prompt_id: Optional[str] = None
    prompt_text: Optional[str] = None
    created_at: str


class JournalListOut(BaseModel):
    entries: List[JournalEntryOut]
    total: int


class JournalPromptOut(BaseModel):
    prompt_id: str
    prompt_text: str
    date: str


class JournalRecapOut(BaseModel):
    week_iso: str
    recap_text: Optional[str] = None
    themes: List[str] = []
    generated_at: Optional[str] = None
    entry_count: int


# ============ Endpoints ============
@router.get("/prompt", response_model=JournalPromptOut)
async def todays_prompt():
    """Return today's gentle prompt. Same prompt all day for a calmer UX."""
    now = _now()
    p = _prompt_for_date(now)
    return JournalPromptOut(
        prompt_id=p["id"],
        prompt_text=p["text"],
        date=now.date().isoformat(),
    )


@router.post("/entries", response_model=JournalEntryOut, status_code=201)
async def create_entry(
    body: JournalEntryIn,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    content = body.content.strip()
    # Pydantic min_length=1 already rejects empty bodies with 422 before
    # we get here; this strip-then-check defends against whitespace-only
    # submissions like "   \n".
    if not content:
        raise HTTPException(status_code=400, detail="Entry can't be empty.")

    prompt_text = None
    if body.prompt_id:
        match = next((p for p in DAILY_PROMPTS if p["id"] == body.prompt_id), None)
        if match:
            prompt_text = match["text"]

    now = _now()
    doc = {
        "entry_id": _short_id(),
        "user_id": current.user_id,
        "kind": "daily",
        "content": content,
        "prompt_id": body.prompt_id,
        "prompt_text": prompt_text,
        "created_at": _iso(now),
        "week_iso": _week_iso(now),
    }
    await db.journal_entries.insert_one(doc)
    return JournalEntryOut(**{k: doc[k] for k in JournalEntryOut.model_fields.keys()})


@router.get("/entries", response_model=JournalListOut)
async def list_entries(
    request: Request,
    current: UserPublic = Depends(get_current_user),
    limit: int = 50,
):
    db = request.app.state.db
    limit = max(1, min(limit, 200))
    cursor = (
        db.journal_entries.find(
            {"user_id": current.user_id},
            {"_id": 0, "user_id": 0, "week_iso": 0},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    rows = await cursor.to_list(limit)
    total = await db.journal_entries.count_documents({"user_id": current.user_id})
    return JournalListOut(entries=rows, total=total)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    res = await db.journal_entries.delete_one(
        {"entry_id": entry_id, "user_id": current.user_id}
    )
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found.")
    return None


# ============ Reflection snapshot (called from mediation_routes.save_reflection) ============
def _reflection_signature(reflection: dict) -> str:
    """Stable hash of the non-empty string fields — used to skip duplicate
    snapshots when the user re-saves without changing anything. Non-string
    fields like the `private: bool` flag are ignored."""
    if not reflection:
        return ""
    items = []
    for k, v in reflection.items():
        if not isinstance(v, str):
            continue
        stripped = v.strip()
        if stripped:
            items.append((k, stripped))
    if not items:
        return ""
    items.sort()
    s = "|".join(f"{k}={v}" for k, v in items)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _format_reflection_snapshot(reflection: dict) -> str:
    """Render the formal Reflection step as a journal-friendly block."""
    parts = []
    labels = {
        "child_lens": "Through your child's eyes",
        "own_part": "Your own part",
        "best_outcome": "Your best-case outcome",
        "release": "What you'd like to set down",
    }
    for key, label in labels.items():
        val = reflection.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"**{label}**\n{val.strip()}")
    return "\n\n".join(parts)


async def maybe_snapshot_reflection(db, user_id: str, reflection: dict) -> bool:
    """Insert a reflection_snapshot journal entry if the content changed.
    Returns True if a snapshot was created.

    Called from `/api/mediation/reflection` PUT handler so journaling is
    transparent — every save the user makes becomes a date-stamped entry
    they can look back on.
    """
    content = _format_reflection_snapshot(reflection)
    if not content:
        return False

    sig = _reflection_signature(reflection)
    if not sig:
        return False

    # Skip if the latest snapshot has the same signature
    latest = await db.journal_entries.find_one(
        {"user_id": user_id, "kind": "reflection_snapshot"},
        {"_id": 0, "signature": 1},
        sort=[("created_at", -1)],
    )
    if latest and latest.get("signature") == sig:
        return False

    now = _now()
    await db.journal_entries.insert_one({
        "entry_id": _short_id(),
        "user_id": user_id,
        "kind": "reflection_snapshot",
        "content": content,
        "signature": sig,
        "created_at": _iso(now),
        "week_iso": _week_iso(now),
    })
    return True


# ============ Weekly recap ============
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


@router.get("/weekly-recap", response_model=JournalRecapOut)
async def weekly_recap(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Returns the cached recap for the current ISO week, or generates one
    on first request of the week. Effectively a 'delivered each Sunday'
    experience: when the new ISO week begins, the next time the user opens
    the History tab a fresh recap is computed."""
    db = request.app.state.db
    now = _now()
    wk = _week_iso(now)

    # Rolling 7-day window — recap reflects "the last 7 days from now",
    # which gives a useful view any day of the week. The CACHE key
    # (week_iso) is aligned to the ISO week so a fresh recap is generated
    # at most once per calendar week per user, keeping LLM spend bounded.
    week_start = now - timedelta(days=7)
    cursor = db.journal_entries.find(
        {"user_id": current.user_id, "created_at": {"$gte": _iso(week_start)}},
        {"_id": 0, "kind": 1, "content": 1, "prompt_text": 1, "created_at": 1},
    ).sort("created_at", 1)
    entries = await cursor.to_list(50)
    entry_count = len(entries)

    # Return cached if exists for this week
    cached = await db.journal_recaps.find_one(
        {"user_id": current.user_id, "week_iso": wk}, {"_id": 0}
    )
    if cached:
        return JournalRecapOut(
            week_iso=wk,
            recap_text=cached.get("recap_text"),
            themes=cached.get("themes", []),
            generated_at=cached.get("generated_at"),
            entry_count=entry_count,
        )

    # Need at least 2 entries before we generate a meaningful recap
    if entry_count < 2:
        return JournalRecapOut(
            week_iso=wk,
            recap_text=None,
            themes=[],
            generated_at=None,
            entry_count=entry_count,
        )

    if not EMERGENT_LLM_KEY:
        # Graceful degrade — no AI configured. Show entry count only.
        return JournalRecapOut(
            week_iso=wk,
            recap_text=None,
            themes=[],
            generated_at=None,
            entry_count=entry_count,
        )

    # Generate via Claude (Emergent LLM key)
    try:
        result = await ai_service.generate_journal_weekly_recap(entries)
    except Exception:
        # Don't fail the request — just return uncached state
        return JournalRecapOut(
            week_iso=wk,
            recap_text=None,
            themes=[],
            generated_at=None,
            entry_count=entry_count,
        )

    doc = {
        "user_id": current.user_id,
        "week_iso": wk,
        "recap_text": result.get("recap_text"),
        "themes": result.get("themes", []),
        "generated_at": _iso(now),
    }
    await db.journal_recaps.update_one(
        {"user_id": current.user_id, "week_iso": wk},
        {"$set": doc},
        upsert=True,
    )
    return JournalRecapOut(
        week_iso=wk,
        recap_text=doc["recap_text"],
        themes=doc["themes"],
        generated_at=doc["generated_at"],
        entry_count=entry_count,
    )
