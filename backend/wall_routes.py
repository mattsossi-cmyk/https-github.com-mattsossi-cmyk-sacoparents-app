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

Pure helpers (anon hashing, log_event_once, and the various maybe_log_*
functions) live in :mod:`wall_utils` so the dashboard route can call them
without creating a circular import.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from wall_utils import (
    BADGE_FOUNDATION_READY,
    BADGE_LABELS,
    CHEERS_COLLECTION,
    EVENTS_COLLECTION,
    get_opt_in,
    log_event_once,
    maybe_log_communication_master,
    maybe_log_first_compare,
    maybe_log_foundation_ready,
    maybe_log_high_alignment,
    maybe_log_week_streak,
    set_opt_in,
)

__all__ = [
    "router",
    # Re-exported for existing call sites in other route modules.
    "maybe_log_foundation_ready",
    "maybe_log_first_compare",
    "maybe_log_high_alignment",
    "maybe_log_communication_master",
    "maybe_log_week_streak",
]


router = APIRouter(prefix="/wall", tags=["wall"])


async def top_cheered_since(db: AsyncIOMotorDatabase, days: int = 7,
                            limit: int = 3, viewer_id: Optional[str] = None,
                            ) -> List[Dict[str, Any]]:
    """Return the most-cheered events in the last `days` days. Enriches
    each row with the same anonymised fields the feed uses so the
    frontend can render a "most-cheered" spotlight above the feed."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_iso = since.isoformat()
    pipeline = [
        {"$match": {"created_at": {"$gte": since_iso}}},
        {"$group": {"_id": "$event_id", "cheer_count": {"$sum": 1}}},
        {"$sort": {"cheer_count": -1}},
        {"$limit": int(limit)},
    ]
    cheer_rows = [row async for row in db[CHEERS_COLLECTION].aggregate(pipeline)]
    if not cheer_rows:
        return []
    event_ids = [r["_id"] for r in cheer_rows]
    counts_by_id = {r["_id"]: int(r["cheer_count"]) for r in cheer_rows}
    events_cursor = db[EVENTS_COLLECTION].find(
        {"event_id": {"$in": event_ids}},
        {"_id": 0, "event_id": 1, "user_hash": 1, "badge_type": 1, "created_at": 1},
    )
    events_by_id: Dict[str, Dict[str, Any]] = {
        row["event_id"]: row async for row in events_cursor
    }
    i_cheered: set = set()
    if viewer_id:
        mine_cursor = db[CHEERS_COLLECTION].find(
            {"event_id": {"$in": event_ids}, "user_id": viewer_id},
            {"_id": 0, "event_id": 1},
        )
        i_cheered = {r["event_id"] async for r in mine_cursor}
    result: List[Dict[str, Any]] = []
    for row in cheer_rows:  # preserves the sorted-desc order
        ev = events_by_id.get(row["_id"])
        if not ev:
            continue
        result.append({
            "event_id":    ev["event_id"],
            "user_hash":   ev["user_hash"],
            "badge_type":  ev["badge_type"],
            "badge_label": BADGE_LABELS.get(ev["badge_type"], ev["badge_type"]),
            "created_at":  ev["created_at"],
            "when_human":  _friendly_delta(ev["created_at"]),
            "cheer_count": counts_by_id[row["_id"]],
            "i_cheered":   ev["event_id"] in i_cheered,
        })
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
class OptInIn(BaseModel):
    opt_in: bool


@router.get("/status")
async def wall_status(user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    opt_in = await get_opt_in(db, user.user_id)
    # How many of MY events landed on the wall this calendar month.
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0,
                                               second=0, microsecond=0)
    my_events_this_month = await db[EVENTS_COLLECTION].count_documents({
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
    await set_opt_in(db, user.user_id, body.opt_in)
    # If the parent is opting in AND already Foundation-Ready, log an
    # immediate event so the wall reflects their state without waiting
    # for the next /progress refresh. Lazy-import compute_progress so we
    # never form a top-level circular import with progress_dashboard_routes.
    logged = None
    if body.opt_in:
        try:
            from progress_dashboard_routes import compute_progress
            progress = await compute_progress(db, user)
            if progress.get("foundation_ready"):
                logged = await log_event_once(
                    db, user.user_id, BADGE_FOUNDATION_READY,
                )
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
                    user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Public, anonymised feed of badges earned in the last `days` days,
    enriched with cheer counts and whether the caller has cheered each
    event."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cursor = db[EVENTS_COLLECTION].find(
        {"created_at": {"$gte": since.isoformat()}},
        {"_id": 0, "user_hash": 1, "badge_type": 1, "created_at": 1, "event_id": 1},
    ).sort("created_at", -1).limit(limit)
    events: List[Dict[str, Any]] = []
    async for row in cursor:
        events.append({
            "event_id": row["event_id"],
            "user_hash": row["user_hash"],
            "badge_type": row["badge_type"],
            "badge_label": BADGE_LABELS.get(row["badge_type"], row["badge_type"]),
            "created_at": row["created_at"],
            "when_human": _friendly_delta(row["created_at"]),
        })
    if events:
        event_ids = [e["event_id"] for e in events]
        counts: Dict[str, int] = {eid: 0 for eid in event_ids}
        pipeline = [
            {"$match": {"event_id": {"$in": event_ids}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]
        async for row in db[CHEERS_COLLECTION].aggregate(pipeline):
            counts[row["_id"]] = int(row["n"])
        mine_cursor = db[CHEERS_COLLECTION].find(
            {"event_id": {"$in": event_ids}, "user_id": user.user_id},
            {"_id": 0, "event_id": 1},
        )
        i_cheered = {r["event_id"] async for r in mine_cursor}
        for ev in events:
            ev["cheer_count"] = counts.get(ev["event_id"], 0)
            ev["i_cheered"] = ev["event_id"] in i_cheered
    total = await db[EVENTS_COLLECTION].count_documents({
        "created_at": {"$gte": since.isoformat()},
    })
    top_cheered = await top_cheered_since(
        db, days=7, limit=3, viewer_id=user.user_id,
    )
    return {
        "events": events,
        "total": int(total),
        "days": days,
        "limit": limit,
        "top_cheered": top_cheered,
    }


@router.post("/cheer/{event_id}")
async def wall_cheer(event_id: str,
                     user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Toggle a one-tap heart on another parent's badge. Requires the
    caller to be opted-in to the wall (mutual consent to be part of the
    community). Cheerer's identity is never exposed on the feed."""
    ev = await db[EVENTS_COLLECTION].find_one(
        {"event_id": event_id}, {"_id": 0, "event_id": 1, "user_id": 1},
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    if ev.get("user_id") == user.user_id:
        raise HTTPException(
            status_code=400,
            detail="You can't cheer your own milestone. Nice one though.",
        )
    if not await get_opt_in(db, user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Opt in to the community wall before cheering another parent.",
        )
    existing = await db[CHEERS_COLLECTION].find_one(
        {"event_id": event_id, "user_id": user.user_id}, {"_id": 1},
    )
    if existing:
        await db[CHEERS_COLLECTION].delete_one(
            {"event_id": event_id, "user_id": user.user_id},
        )
        cheered = False
    else:
        await db[CHEERS_COLLECTION].insert_one({
            "event_id": event_id,
            "user_id": user.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        cheered = True
    cheer_count = await db[CHEERS_COLLECTION].count_documents(
        {"event_id": event_id},
    )
    return {"ok": True, "cheered": cheered, "cheer_count": int(cheer_count)}
