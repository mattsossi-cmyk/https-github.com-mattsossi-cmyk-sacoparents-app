"""Weekly Case Analytics Email — Monday-morning digest for mediators.

For every user who has minted at least one in-app Joint Alignment
Case, this sweep sends a weekly rollup email summarising their
`/mine` analytics: total cases, acceptance rate, average time-to-
first-accept, average time-to-both-complete, top assessment lane,
and a `+N this week` delta so trends are visible at a glance.

Runs once daily on Monday between 09:00-11:00 UTC. Dedupe is per
(user_id, ISO-week) so a Monday-morning cron nudge fires exactly
once per mediator per week.

Gated behind `WEEKLY_CASE_ANALYTICS_ENABLED=1` — idle no-op when
unset, safe to always register from `server.py`.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

_CASES_COLLECTION = "joint_alignment_cases"
_SENDS_COLLECTION = "weekly_case_analytics_sends"
_USERS_COLLECTION = "users"
_ORIGIN_IN_APP = "in_app_professional"

_SWEEP_INTERVAL_S = int(os.environ.get("WEEKLY_CASE_ANALYTICS_SWEEP_SECONDS", "3600"))
_MONDAY_SEND_START_UTC_HOUR = int(os.environ.get("WEEKLY_CASE_ANALYTICS_START_HOUR_UTC", "9"))
_MONDAY_SEND_END_UTC_HOUR = int(os.environ.get("WEEKLY_CASE_ANALYTICS_END_HOUR_UTC", "11"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _week_start(dt: Optional[datetime] = None) -> str:
    """ISO date (YYYY-MM-DD) of the Monday preceding `dt` — used as
    the dedupe key so a Monday sweep can't double-send within the
    same week."""
    d = (dt or _now_utc()).astimezone(timezone.utc)
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _in_send_window(now: datetime) -> bool:
    """True iff `now` is Monday between the configured UTC hour window."""
    now = now.astimezone(timezone.utc)
    return (
        now.weekday() == 0
        and _MONDAY_SEND_START_UTC_HOUR <= now.hour < _MONDAY_SEND_END_UTC_HOUR
    )


def _as_aware_utc(v: Any) -> Optional[datetime]:
    """Coerce a Mongo-returned datetime (tz-naive UTC) or ISO string
    into a tz-aware UTC datetime. Mirrors the helper in
    `joint_alignment_routes.py` — kept local so this module has no
    routes-layer imports."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _looks_like_real_email(email: Optional[str]) -> bool:
    if not email:
        return False
    e = email.strip().lower()
    return (
        "@" in e
        and "." in e.split("@")[-1]
        and not e.endswith("@demo.local")
        and not e.endswith("@guest.local")
    )


def _mine_url() -> str:
    base = (os.environ.get("PUBLIC_APP_ORIGIN") or "").rstrip("/") or "https://sacoparentsapp.online"
    return f"{base}/professional/joint-alignment/mine"


# ---------------------------------------------------------------------------
# Aggregation — same math as the analytics endpoint but self-contained
# so the sweep loop has no dependency on the routes layer.
# ---------------------------------------------------------------------------

def _compute_analytics(cases: List[Dict[str, Any]], week_ago: datetime) -> Dict[str, Any]:
    total_cases = len(cases)
    active_cases = sum(1 for c in cases if c.get("status") in ("pending", "in_progress"))
    completed_cases = sum(1 for c in cases if c.get("status") == "both_complete")
    cancelled_cases = sum(1 for c in cases if c.get("status") == "cancelled")

    invited_parents = 0
    accepted_parents = 0
    for c in cases:
        for p in c.get("parents") or []:
            invited_parents += 1
            if p.get("accepted_at"):
                accepted_parents += 1
    acceptance_rate = (
        round(accepted_parents / invited_parents * 100, 1)
        if invited_parents > 0 else None
    )

    first_accept_hours: List[float] = []
    both_complete_hours: List[float] = []
    for c in cases:
        created = _as_aware_utc(c.get("created_at"))
        if not created:
            continue
        accepts = [_as_aware_utc(p.get("accepted_at")) for p in (c.get("parents") or [])]
        accepts = [a for a in accepts if a]
        if accepts:
            first_accept_hours.append((min(accepts) - created).total_seconds() / 3600.0)
        completions = [_as_aware_utc(p.get("assessment_completed_at")) for p in (c.get("parents") or [])]
        completions = [x for x in completions if x]
        if len(completions) >= 2:
            both_complete_hours.append((max(completions) - created).total_seconds() / 3600.0)
    avg_first_accept = (
        round(sum(first_accept_hours) / len(first_accept_hours), 1)
        if first_accept_hours else None
    )
    avg_both_complete = (
        round(sum(both_complete_hours) / len(both_complete_hours), 1)
        if both_complete_hours else None
    )

    breakdown: Dict[str, int] = {}
    for c in cases:
        lane = (c.get("assessment_type") or "unknown")
        breakdown[lane] = breakdown.get(lane, 0) + 1
    most_common_lane = (
        max(breakdown.items(), key=lambda kv: kv[1])[0] if breakdown else None
    )

    # "This week" delta — cases minted since `week_ago`.
    new_this_week = sum(
        1 for c in cases
        if (_as_aware_utc(c.get("created_at")) or _now_utc()) >= week_ago
    )
    completed_this_week = sum(
        1 for c in cases
        if c.get("status") == "both_complete"
        and any(
            (_as_aware_utc(p.get("assessment_completed_at")) or _now_utc()) >= week_ago
            for p in (c.get("parents") or [])
        )
    )

    return {
        "total_cases": total_cases,
        "active_cases": active_cases,
        "completed_cases": completed_cases,
        "cancelled_cases": cancelled_cases,
        "acceptance_rate": acceptance_rate,
        "avg_hours_to_first_accept": avg_first_accept,
        "avg_hours_to_both_complete": avg_both_complete,
        "most_common_assessment_type": most_common_lane,
        "assessment_type_breakdown": breakdown,
        "new_this_week": new_this_week,
        "completed_this_week": completed_this_week,
    }


# ---------------------------------------------------------------------------
# Sweep pipeline.
# ---------------------------------------------------------------------------

async def _iter_candidate_professionals(db: AsyncIOMotorDatabase) -> List[str]:
    """Distinct user_ids that have minted ≥ 1 in-app case. Sweep
    candidates — we still gate each on real-email + not-already-sent."""
    return await db[_CASES_COLLECTION].distinct(
        "professional_created_by",
        {"origin": _ORIGIN_IN_APP, "professional_created_by": {"$nin": [None, ""]}},
    )


async def _cases_for(db: AsyncIOMotorDatabase, user_id: str) -> List[Dict[str, Any]]:
    cursor = db[_CASES_COLLECTION].find({
        "$or": [
            {"professional_created_by": user_id},
            {"professional.id": user_id, "origin": _ORIGIN_IN_APP},
        ],
    })
    return [c async for c in cursor]


async def _resolve_professional(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    doc = await db[_USERS_COLLECTION].find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        # Fall back to the professional block on their first minted case.
        case = await db[_CASES_COLLECTION].find_one(
            {"professional_created_by": user_id, "origin": _ORIGIN_IN_APP},
        )
        if case:
            prof = case.get("professional") or {}
            if prof.get("email"):
                return {"user_id": user_id, "email": prof.get("email"), "name": prof.get("name")}
        return None
    return doc


async def _already_sent_this_week(
    db: AsyncIOMotorDatabase, *, user_id: str, week_start: str,
) -> bool:
    row = await db[_SENDS_COLLECTION].find_one({
        "user_id": user_id, "week_start": week_start,
    })
    return row is not None


async def _record_send(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    week_start: str,
    dry_run: bool,
    reason: str,
) -> None:
    await db[_SENDS_COLLECTION].insert_one({
        "user_id": user_id,
        "week_start": week_start,
        "dry_run": bool(dry_run),
        "reason": reason,
        "created_at": _now_utc(),
    })


async def _dispatch_one(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    week_start: str,
    now: datetime,
    dry_run: bool,
) -> Dict[str, Any]:
    base = {"user_id": user_id, "week_start": week_start, "sent": False}

    if await _already_sent_this_week(db, user_id=user_id, week_start=week_start):
        return {**base, "reason": "already_sent_this_week"}

    profile = await _resolve_professional(db, user_id)
    if not profile:
        return {**base, "reason": "profile_missing"}
    email = profile.get("email")
    if not _looks_like_real_email(email):
        return {**base, "reason": "email_not_real"}

    cases = await _cases_for(db, user_id)
    if not cases:
        return {**base, "reason": "no_cases"}

    week_ago = now - timedelta(days=7)
    stats = _compute_analytics(cases, week_ago)

    if dry_run:
        await _record_send(
            db, user_id=user_id, week_start=week_start,
            dry_run=True, reason="dry_run",
        )
        return {**base, "sent": True, "dry_run": True, "stats": stats}

    try:
        from email_service import (
            EmailNotConfigured, EmailSendError,
            send_weekly_case_analytics_email,
        )
        send_weekly_case_analytics_email(
            to_email=email,
            professional_name=profile.get("name"),
            mine_url=_mine_url(),
            stats=stats,
        )
    except EmailNotConfigured:
        return {**base, "reason": "email_not_configured"}
    except EmailSendError as exc:
        return {**base, "reason": f"email_send_error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        log.exception("weekly analytics email failed for %s", user_id)
        return {**base, "reason": f"exception: {exc}"}

    await _record_send(
        db, user_id=user_id, week_start=week_start,
        dry_run=False, reason="sent",
    )
    return {**base, "sent": True, "stats": stats}


async def send_weekly_case_analytics(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    force_window: bool = False,
) -> Dict[str, Any]:
    """One sweep pass. Same shape/contract as the other Monday sweeps."""
    now = now or _now_utc()
    if not force_window and not _in_send_window(now):
        return {"skipped": "outside_send_window", "at": now.isoformat(), "results": []}

    week_start = _week_start(now)
    candidates = await _iter_candidate_professionals(db)
    results: List[Dict[str, Any]] = []
    for user_id in candidates:
        try:
            results.append(await _dispatch_one(
                db,
                user_id=user_id, week_start=week_start,
                now=now, dry_run=dry_run,
            ))
        except Exception as exc:  # noqa: BLE001
            log.exception("weekly analytics dispatch failed for %s", user_id)
            results.append({
                "user_id": user_id, "week_start": week_start,
                "sent": False, "reason": f"exception: {exc}",
            })
    return {
        "at": now.isoformat(),
        "week_start": week_start,
        "candidates": len(candidates),
        "results": results,
        "sent_count": sum(1 for r in results if r.get("sent")),
    }


# ---------------------------------------------------------------------------
# Background loop.
# ---------------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("WEEKLY_CASE_ANALYTICS_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


async def weekly_case_analytics_loop(app) -> None:
    """Long-running Monday-morning sweep. Idle no-op when the env
    flag is not set — safe to always register from server.py."""
    if not _enabled():
        log.info(
            "weekly_case_analytics_loop: WEEKLY_CASE_ANALYTICS_ENABLED "
            "not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    # Offset so the compliance-reminder and case-analytics sweeps don't
    # kick off simultaneously on startup.
    await asyncio.sleep(300)
    while True:
        try:
            db = app.state.db
            await send_weekly_case_analytics(db)
        except Exception:  # noqa: BLE001
            log.exception("weekly case analytics sweep failed; will retry.")
        await asyncio.sleep(_SWEEP_INTERVAL_S)
