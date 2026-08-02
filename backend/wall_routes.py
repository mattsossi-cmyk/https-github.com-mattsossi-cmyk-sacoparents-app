"""Public Milestone Wall — an opt-in, fully-anonymised feed of badges
earned by other parents this month, so first-timers feel the community
cheering them on.

Privacy model
-------------
* Nothing here is public without an explicit opt-in.
* The wall stores ONLY: a stable hash of the user_id (never the raw id),
  the badge type, and the timestamp.
* Rendered items show a generic label ("A parent lit Foundation Ready")
  plus a relative timestamp. No names, no emails, no city or stats.
* A user can opt out at any time; existing events remain until we run a
  scheduled purge (see /wall/opt-out below — sets deleted flag).

Endpoints
---------
* GET  /api/wall/status  — {opt_in: bool, my_events_this_month: int}
* POST /api/wall/opt-in  — {opt_in: bool} — flips the user preference and,
    on opt-in, backfills a Foundation-Ready event if the user currently
    holds the badge (so the wall shows momentum immediately).
* GET  /api/wall/feed?days=30&limit=50 — {events: [...], total, days}
    Public read-only feed. No auth required is tempting but we keep auth
    to prevent scraping; behind the scenes anyone signed in can read it.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from progress_dashboard_routes import compute_progress


router = APIRouter(prefix="/wall", tags=["wall"])


_OPT_IN_COLLECTION = "wall_opt_in"
_EVENTS_COLLECTION = "wall_events"
_BADGE_FOUNDATION_READY = "foundation_ready"

_ANON_SALT_ENV = "WALL_ANON_SALT"

# Human labels for badge types shown on the feed.
_BADGE_LABELS = {
    _BADGE_FOUNDATION_READY: "lit all five milestones — Foundation Ready.",
}


def _anon_hash(user_id: str) -> str:
    """Stable, non-reversible hash of the user_id. Combined with a salt
    from the environment so a stolen DB copy can't be joined back to
    users. Falls back to a deterministic placeholder salt in dev so the
    hash stays consistent across process restarts."""
    salt = os.environ.get(_ANON_SALT_ENV) or "sacop-wall-anon-salt-dev-only"
    return hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()[:16]


async def _get_opt_in(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    row = await db[_OPT_IN_COLLECTION].find_one({"user_id": user_id}, {"_id": 0})
    return bool(row and row.get("opt_in"))


async def _set_opt_in(db: AsyncIOMotorDatabase, user_id: str, opt_in: bool) -> None:
    await db[_OPT_IN_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "opt_in": bool(opt_in),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def _log_event_once(db: AsyncIOMotorDatabase, user_id: str,
                          badge_type: str) -> Optional[Dict[str, Any]]:
    """Log a badge event iff (1) the user is opted-in AND (2) they haven't
    logged this badge in the last 24h (so a flicker at 4/5 → 5/5 → 4/5 →
    5/5 doesn't spam the wall)."""
    if not await _get_opt_in(db, user_id):
        return None
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = await db[_EVENTS_COLLECTION].find_one({
        "user_id": user_id,
        "badge_type": badge_type,
        "created_at": {"$gte": twenty_four_hours_ago.isoformat()},
    }, {"_id": 1})
    if recent:
        return None
    now = datetime.now(timezone.utc)
    doc = {
        "event_id": f"wall_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,          # kept private for de-dupe / purge
        "user_hash": _anon_hash(user_id),
        "badge_type": badge_type,
        "created_at": now.isoformat(),
    }
    await db[_EVENTS_COLLECTION].insert_one(doc)
    return doc


# ---------------------------------------------------------------------------
# Public helper — called from progress_dashboard_routes on every /progress
# request. Keeps the wall in-sync without introducing a cron job.
# ---------------------------------------------------------------------------
async def maybe_log_foundation_ready(db: AsyncIOMotorDatabase, user_id: str,
                                     foundation_ready: bool) -> None:
    """No-op unless the user is opted-in AND currently Foundation-Ready."""
    if not foundation_ready:
        return
    try:
        await _log_event_once(db, user_id, _BADGE_FOUNDATION_READY)
    except Exception:  # noqa: BLE001
        # Never let a wall-side failure break the dashboard.
        pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
class OptInIn(BaseModel):
    opt_in: bool


@router.get("/status")
async def wall_status(user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    opt_in = await _get_opt_in(db, user.user_id)
    # How many of MY events landed on the wall this calendar month.
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0,
                                               second=0, microsecond=0)
    my_events_this_month = await db[_EVENTS_COLLECTION].count_documents({
        "user_id": user.user_id,
        "created_at": {"$gte": start.isoformat()},
    })
    return {
        "opt_in": opt_in,
        "my_events_this_month": int(my_events_this_month),
    }


@router.post("/opt-in")
async def wall_opt_in(body: OptInIn,
                      user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    await _set_opt_in(db, user.user_id, body.opt_in)
    # If the parent is opting in AND already Foundation-Ready, log an
    # immediate event so the wall reflects their state without waiting
    # for the next /progress refresh.
    logged = None
    if body.opt_in:
        try:
            progress = await compute_progress(db, user)
            if progress.get("foundation_ready"):
                logged = await _log_event_once(db, user.user_id,
                                               _BADGE_FOUNDATION_READY)
        except Exception:  # noqa: BLE001
            logged = None
    return {
        "ok": True,
        "opt_in": body.opt_in,
        "backfilled_event": bool(logged),
    }


def _friendly_delta(created_at_iso: str) -> str:
    """Return a soft, relative timestamp like 'just now', '3 hours ago'."""
    try:
        when = datetime.fromisoformat(created_at_iso)
    except Exception:  # noqa: BLE001
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - when
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = seconds // 86400
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    return f"{months} month{'s' if months != 1 else ''} ago"


@router.get("/feed")
async def wall_feed(days: int = Query(30, ge=1, le=90),
                    limit: int = Query(50, ge=1, le=200),
                    _user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Public, anonymised feed of badges earned in the last `days` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cursor = db[_EVENTS_COLLECTION].find(
        {"created_at": {"$gte": since.isoformat()}},
        {"_id": 0, "user_hash": 1, "badge_type": 1, "created_at": 1, "event_id": 1},
    ).sort("created_at", -1).limit(limit)
    events: List[Dict[str, Any]] = []
    async for row in cursor:
        events.append({
            "event_id": row["event_id"],
            "user_hash": row["user_hash"],
            "badge_type": row["badge_type"],
            "badge_label": _BADGE_LABELS.get(row["badge_type"], row["badge_type"]),
            "created_at": row["created_at"],
            "when_human": _friendly_delta(row["created_at"]),
        })
    total = await db[_EVENTS_COLLECTION].count_documents({
        "created_at": {"$gte": since.isoformat()},
    })
    return {
        "events": events,
        "total": int(total),
        "days": days,
        "limit": limit,
    }
