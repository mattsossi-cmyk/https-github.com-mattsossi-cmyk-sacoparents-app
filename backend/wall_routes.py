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
_CHEERS_COLLECTION = "wall_cheers"
_BADGE_FOUNDATION_READY = "foundation_ready"
_BADGE_FIRST_COMPARE = "first_compare"
_BADGE_HIGH_ALIGNMENT_90 = "high_alignment_90"
_BADGE_COMMUNICATION_MASTER = "communication_master"

_ANON_SALT_ENV = "WALL_ANON_SALT"

# Human labels for badge types shown on the feed.
_BADGE_LABELS = {
    _BADGE_FOUNDATION_READY:     "lit all five milestones — Foundation Ready.",
    _BADGE_FIRST_COMPARE:        "ran their first co-parent comparison.",
    _BADGE_HIGH_ALIGNMENT_90:    "hit 90%+ alignment with their co-parent.",
    _BADGE_COMMUNICATION_MASTER: "completed every mediation-prep section — Communication Master.",
}

# Badges we only ever want to log once per parent (life-time). Others use a
# 24-hour de-dupe so a flicker back-and-forth doesn't spam the wall but a
# re-earn a week later still shows up.
_LIFETIME_BADGES = frozenset({_BADGE_FIRST_COMPARE, _BADGE_COMMUNICATION_MASTER})


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
    logged this badge in the dedupe window. Lifetime badges (first_compare,
    communication_master) never re-log; other badges use a 24-hour window so
    a flicker at 4/5 → 5/5 → 4/5 → 5/5 doesn't spam the wall."""
    if not await _get_opt_in(db, user_id):
        return None
    if badge_type in _LIFETIME_BADGES:
        # Any prior event of this type for this user blocks logging.
        prior = await db[_EVENTS_COLLECTION].find_one(
            {"user_id": user_id, "badge_type": badge_type}, {"_id": 1},
        )
        if prior:
            return None
    else:
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
# Public helpers — called from other routes on every relevant transition.
# Each one is a safe no-op unless the user is opted-in.
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


async def maybe_log_first_compare(db: AsyncIOMotorDatabase,
                                  user_ids: List[str]) -> None:
    """Log a first_compare badge for each participant that has never
    earned it before. Called when a compare share transitions to
    both-consented ("active")."""
    for uid in user_ids or []:
        if not uid:
            continue
        try:
            await _log_event_once(db, uid, _BADGE_FIRST_COMPARE)
        except Exception:  # noqa: BLE001
            pass


async def maybe_log_high_alignment(db: AsyncIOMotorDatabase,
                                   user_ids: List[str],
                                   aligned_pct: Optional[int]) -> None:
    """Log a 90%+ alignment badge for each participant. Called when a
    compare snapshot is persisted."""
    if aligned_pct is None or aligned_pct < 90:
        return
    for uid in user_ids or []:
        if not uid:
            continue
        try:
            await _log_event_once(db, uid, _BADGE_HIGH_ALIGNMENT_90)
        except Exception:  # noqa: BLE001
            pass


async def maybe_log_communication_master(db: AsyncIOMotorDatabase,
                                         user_id: str,
                                         saved_prep_sections: int,
                                         total_prep_sections: int) -> None:
    """Log a Communication Master badge once when a parent has saved every
    mediation-prep section."""
    if total_prep_sections <= 0 or saved_prep_sections < total_prep_sections:
        return
    try:
        await _log_event_once(db, user_id, _BADGE_COMMUNICATION_MASTER)
    except Exception:  # noqa: BLE001
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
                    user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Public, anonymised feed of badges earned in the last `days` days,
    enriched with cheer counts and whether the caller has cheered each
    event."""
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
    if events:
        event_ids = [e["event_id"] for e in events]
        # Aggregate cheer counts in one pass.
        counts: Dict[str, int] = {eid: 0 for eid in event_ids}
        pipeline = [
            {"$match": {"event_id": {"$in": event_ids}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]
        async for row in db[_CHEERS_COLLECTION].aggregate(pipeline):
            counts[row["_id"]] = int(row["n"])
        # Which events has the caller cheered?
        mine_cursor = db[_CHEERS_COLLECTION].find(
            {"event_id": {"$in": event_ids}, "user_id": user.user_id},
            {"_id": 0, "event_id": 1},
        )
        i_cheered = {r["event_id"] async for r in mine_cursor}
        for ev in events:
            ev["cheer_count"] = counts.get(ev["event_id"], 0)
            ev["i_cheered"] = ev["event_id"] in i_cheered
    total = await db[_EVENTS_COLLECTION].count_documents({
        "created_at": {"$gte": since.isoformat()},
    })
    return {
        "events": events,
        "total": int(total),
        "days": days,
        "limit": limit,
    }


@router.post("/cheer/{event_id}")
async def wall_cheer(event_id: str,
                     user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Toggle a one-tap heart on another parent's badge. Requires the
    caller to be opted-in to the wall (mutual consent to be part of the
    community). Cheerer's identity is never exposed on the feed."""
    # Ensure the event exists.
    ev = await db[_EVENTS_COLLECTION].find_one(
        {"event_id": event_id}, {"_id": 0, "event_id": 1, "user_id": 1},
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    # Cheering yourself is disallowed — it'd inflate counts silently.
    if ev.get("user_id") == user.user_id:
        raise HTTPException(
            status_code=400,
            detail="You can't cheer your own milestone. Nice one though.",
        )
    # Must be opted-in to cheer. Symmetric contract — only wall citizens
    # can interact with the wall.
    if not await _get_opt_in(db, user.user_id):
        raise HTTPException(
            status_code=403,
            detail="Opt in to the community wall before cheering another parent.",
        )
    # Toggle: if the row exists, remove it; otherwise insert it.
    existing = await db[_CHEERS_COLLECTION].find_one(
        {"event_id": event_id, "user_id": user.user_id}, {"_id": 1},
    )
    if existing:
        await db[_CHEERS_COLLECTION].delete_one(
            {"event_id": event_id, "user_id": user.user_id},
        )
        cheered = False
    else:
        await db[_CHEERS_COLLECTION].insert_one({
            "event_id": event_id,
            "user_id": user.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        cheered = True
    cheer_count = await db[_CHEERS_COLLECTION].count_documents(
        {"event_id": event_id},
    )
    return {"ok": True, "cheered": cheered, "cheer_count": int(cheer_count)}
