"""Progress Dashboard — five visual pills for /dashboard.

Read-only aggregator over existing collections. Each pill turns ✓ when
its criterion is met. Criteria are intentionally low-friction so parents
see progress early and stay motivated.

Pills:
  * foundation_completed     — Foundation Statement written + user has a name
  * child_needs_identified   — at least one deep dive completed OR an SNC v2 report exists
  * communication_readiness  — mediation prep `comm_style` section saved
  * mediation_readiness      — 3+ mediation prep sections saved (any of child_goals,
                               issues, priority, comm_style, readiness, reflection)
  * conflict_reduced         — most-recent compare snapshot for the user has
                               aligned_pct >= 60 (across any pathway)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from wall_utils import (
    BADGE_LABELS,
    build_weekly_cheer_digest,
    maybe_log_communication_master,
    maybe_log_foundation_ready,
    maybe_log_hundred_day_streak,
    maybe_log_month_streak,
    maybe_log_week_streak,
)


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


_MEDIATION_PREP_SECTIONS = ("child_goals", "issues", "priority", "comm_style",
                            "readiness", "reflection")

_DEEP_DIVE_ASSESSMENTS = ("edu_deep_assessments", "psych_deep_assessments",
                          "med_deep_assessments")

_DEEP_DIVE_SHARES = ("edu_deep_shares", "psych_deep_shares", "med_deep_shares")

_ALIGNMENT_THRESHOLD = 60
_HISTORY_COLLECTION = "progress_daily_history"
_HISTORY_DAYS = 30


async def _has_foundation_text(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    row = await db["portal_state"].find_one({"user_id": user_id}, {"_id": 0, "foundation_text": 1}) or {}
    return bool((row.get("foundation_text") or "").strip())


async def _any_child_needs_signal(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """Either any deep dive completed, or an SNC v2 report exists."""
    for coll in _DEEP_DIVE_ASSESSMENTS:
        row = await db[coll].find_one({"user_id": user_id, "completed": True}, {"_id": 1})
        if row:
            return True
    row = await db["snc2_reports"].find_one({"user_id": user_id}, {"_id": 1})
    return bool(row)


def _saved_prep_sections(prep: Dict[str, Any]) -> List[str]:
    """Return the list of prep sections that have at least one saved value."""
    saved = []
    for k in _MEDIATION_PREP_SECTIONS:
        val = prep.get(k)
        # A prep section is "saved" if it exists as a non-empty dict / non-empty value.
        if isinstance(val, dict) and val:
            saved.append(k)
        elif isinstance(val, (list, str)) and val:
            saved.append(k)
    return saved


async def _latest_alignment_pct(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Find the user's most recent compare snapshot across all three
    pathways. Returns {aligned_pct: int|None, pathway: str|None}."""
    # Gather every share_id the user participates in across all pathways.
    share_id_to_pathway: Dict[str, str] = {}
    for coll in _DEEP_DIVE_SHARES:
        cursor = db[coll].find(
            {"user_pair": user_id, "status": {"$ne": "revoked"}},
            {"_id": 0, "share_id": 1},
        )
        pathway_key = coll.split("_", 1)[0]  # "edu" | "psych" | "med"
        async for s in cursor:
            share_id_to_pathway[s["share_id"]] = pathway_key
    if not share_id_to_pathway:
        return {"aligned_pct": None, "pathway": None}
    snap = await db["deep_dive_compare_snapshots"].find_one(
        {"share_id": {"$in": list(share_id_to_pathway.keys())}},
        {"_id": 0, "share_id": 1, "summary": 1},
        sort=[("created_at", -1)],
    )
    if not snap:
        return {"aligned_pct": None, "pathway": None}
    pct = (snap.get("summary") or {}).get("aligned_pct")
    try:
        pct = int(pct) if pct is not None else None
    except Exception:  # noqa: BLE001
        pct = None
    return {"aligned_pct": pct, "pathway": share_id_to_pathway.get(snap.get("share_id"))}


async def compute_progress(db: AsyncIOMotorDatabase, user: UserPublic) -> Dict[str, Any]:
    """Compute the five progress pills for a single user. Pure — no DB
    writes — so it can be reused by /progress AND certificate rendering.

    Return payload matches the /progress endpoint (minus history)."""
    prep = await db["prep_data"].find_one({"user_id": user.user_id}, {"_id": 0}) or {}

    has_foundation = await _has_foundation_text(db, user.user_id)
    has_name = bool((user.name or "").strip())
    foundation_completed = has_foundation and has_name

    child_needs_identified = await _any_child_needs_signal(db, user.user_id)

    saved_sections = _saved_prep_sections(prep)
    communication_readiness = "comm_style" in saved_sections
    mediation_readiness = len(saved_sections) >= 3

    alignment = await _latest_alignment_pct(db, user.user_id)
    conflict_reduced = (
        alignment["aligned_pct"] is not None
        and alignment["aligned_pct"] >= _ALIGNMENT_THRESHOLD
    )

    pills = [
        {
            "id": "foundation_completed",
            "label": "Foundation completed",
            "done": foundation_completed,
            "detail": (
                "Foundation Statement saved + profile filled."
                if foundation_completed
                else ("Add your name in profile." if has_foundation
                      else "Write your Foundation Statement.")
            ),
        },
        {
            "id": "child_needs_identified",
            "label": "Child needs identified",
            "done": child_needs_identified,
            "detail": (
                "You've mapped your child's needs at least once."
                if child_needs_identified
                else "Finish one Special Needs deep dive or the Special Needs Compass."
            ),
        },
        {
            "id": "communication_readiness",
            "label": "Communication readiness",
            "done": communication_readiness,
            "detail": (
                "Communication Style module completed."
                if communication_readiness
                else "Complete the Communication Style prep module."
            ),
        },
        {
            "id": "mediation_readiness",
            "label": "Mediation readiness",
            "done": mediation_readiness,
            "detail": (
                f"{len(saved_sections)} of {len(_MEDIATION_PREP_SECTIONS)} prep sections saved."
                if mediation_readiness
                else f"Complete 3 prep sections (you have {len(saved_sections)})."
            ),
        },
        {
            "id": "conflict_reduced",
            "label": "Conflict reduced",
            "done": conflict_reduced,
            "detail": (
                f"Latest alignment: {alignment['aligned_pct']}%."
                if alignment["aligned_pct"] is not None
                else "Run a co-parent comparison to see your alignment."
            ),
        },
    ]
    completed_count = sum(1 for p in pills if p["done"])
    total = len(pills)
    return {
        "pills": pills,
        "completed_count": completed_count,
        "total": total,
        "foundation_ready": completed_count == total,
        "alignment_pct": alignment["aligned_pct"],
        "alignment_pathway": alignment["pathway"],
        "alignment_threshold": _ALIGNMENT_THRESHOLD,
    }


async def _upsert_today_history(db: AsyncIOMotorDatabase, user_id: str,
                                completed_count: int, total: int) -> None:
    """Persist today's completed_count so we can render a sparkline of
    momentum over time. Idempotent — one row per user per UTC date, updated
    whenever the user hits the /progress endpoint."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db[_HISTORY_COLLECTION].update_one(
        {"user_id": user_id, "date": today},
        {"$set": {
            "user_id": user_id,
            "date": today,
            "completed_count": int(completed_count),
            "total": int(total),
            "ready": completed_count == total,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def _read_history_series(db: AsyncIOMotorDatabase, user_id: str,
                               days: int = _HISTORY_DAYS) -> List[Dict[str, Any]]:
    """Return the last `days` days of history as a dense list — one entry
    per date from (today - days + 1) to today. Missing days are backfilled
    with the last known value so the sparkline stays continuous."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    cursor = db[_HISTORY_COLLECTION].find(
        {"user_id": user_id,
         "date": {"$gte": start.strftime("%Y-%m-%d"),
                  "$lte": end.strftime("%Y-%m-%d")}},
        {"_id": 0, "date": 1, "completed_count": 1, "total": 1, "ready": 1},
    ).sort("date", 1)
    by_date = {row["date"]: row async for row in cursor}
    series: List[Dict[str, Any]] = []
    last_done = 0
    last_total = 5
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        row = by_date.get(d)
        if row:
            last_done = int(row.get("completed_count") or 0)
            last_total = int(row.get("total") or 5)
        series.append({
            "date": d,
            "done": last_done,
            "total": last_total,
            "ready": last_done == last_total and last_total > 0,
            "visited": row is not None,
        })
    return series


async def _current_streak_days(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Count consecutive days (ending today, UTC) that the parent visited
    the dashboard. Break resets to 0; today with a row counts as 1."""
    # Pull the last ~60 days of history so a long streak is representable.
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=59)
    cursor = db[_HISTORY_COLLECTION].find(
        {"user_id": user_id,
         "date": {"$gte": start.strftime("%Y-%m-%d"),
                  "$lte": end.strftime("%Y-%m-%d")}},
        {"_id": 0, "date": 1},
    )
    dates = {row["date"] async for row in cursor}
    streak = 0
    for i in range(60):
        d = (end - timedelta(days=i)).strftime("%Y-%m-%d")
        if d in dates:
            streak += 1
        else:
            break
    return streak


@router.get("/progress")
async def get_progress(user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Return the five progress pills for the /dashboard visual, plus a
    30-day sparkline of momentum. Upserts today's snapshot as a side effect
    so the history stays fresh without a separate cron job. Also logs a
    Public Milestone Wall event when a Foundation-Ready parent has opted
    in — silently, no-op for anyone who hasn't opted in."""
    body = await compute_progress(db, user)
    # Persist today's snapshot for the sparkline. Fire-and-forget for
    # resilience: a Mongo hiccup on the history collection must never
    # break the dashboard.
    try:
        await _upsert_today_history(db, user.user_id,
                                    body["completed_count"], body["total"])
    except Exception:  # noqa: BLE001
        pass
    try:
        history = await _read_history_series(db, user.user_id, days=_HISTORY_DAYS)
    except Exception:  # noqa: BLE001
        history = []
    body["history"] = history
    body["history_days"] = _HISTORY_DAYS
    # Current consecutive-day streak — fuels the "Consistent Coparent"
    # badge below and the weekly email summary.
    try:
        streak = await _current_streak_days(db, user.user_id)
    except Exception:  # noqa: BLE001
        streak = 0
    body["streak_days"] = int(streak)
    # Public Milestone Wall — safe no-op unless opted in.
    try:
        await maybe_log_foundation_ready(db, user.user_id,
                                         bool(body.get("foundation_ready")))
        # Communication Master badge: all 6 mediation-prep sections saved.
        prep = await db["prep_data"].find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        saved = _saved_prep_sections(prep)
        await maybe_log_communication_master(
            db, user.user_id, len(saved), len(_MEDIATION_PREP_SECTIONS),
        )
        # 7-day consistent-visit streak.
        await maybe_log_week_streak(db, user.user_id, streak)
        # 30-day and 100-day long-haul streaks — lifetime badges.
        await maybe_log_month_streak(db, user.user_id, streak)
        await maybe_log_hundred_day_streak(db, user.user_id, streak)
    except Exception:  # noqa: BLE001
        pass
    return body


# ---------------------------------------------------------------------------
# Weekly Progress Email — Sunday summary of milestones + streak.
# ---------------------------------------------------------------------------
_WEEKLY_EMAIL_LOG = "weekly_progress_email_log"
_WEEKLY_EMAIL_NOTES = "weekly_progress_email_notes"
_WEEKLY_NOTE_MAX_CHARS = 280


def _iso_week_key(dt: Optional[datetime] = None) -> str:
    """Return a stable "YYYY-Wnn" key for the ISO calendar week the given
    UTC datetime falls into. Used to guarantee at most one weekly email
    per user per ISO week."""
    now = dt or datetime.now(timezone.utc)
    y, w, _ = now.isocalendar()
    return f"{y:04d}-W{w:02d}"


class WeeklyEmailIn(BaseModel):
    force: Optional[bool] = False


class WeeklyNoteIn(BaseModel):
    note: str = ""


async def _fetch_weekly_note(db: AsyncIOMotorDatabase, user_id: str,
                             week_key: str) -> Dict[str, Any]:
    """Return the parent's saved handwritten note for the given ISO week
    (or an empty stub if nothing's been saved yet)."""
    doc = await db[_WEEKLY_EMAIL_NOTES].find_one(
        {"user_id": user_id, "week_key": week_key}, {"_id": 0},
    )
    return {
        "note": (doc or {}).get("note", "") or "",
        "updated_at": (doc or {}).get("updated_at"),
        "week_key": week_key,
        "max_chars": _WEEKLY_NOTE_MAX_CHARS,
    }


async def _build_weekly_email_context(db: AsyncIOMotorDatabase,
                                      user: UserPublic) -> Dict[str, Any]:
    """Compute the data the Sunday email will render: progress numbers,
    streak, this-week milestones, alignment %, dashboard URL. Shared by
    the send endpoint AND the preview endpoint so the inline preview on
    the dashboard mirrors the email pixel-for-pixel."""
    progress = await compute_progress(db, user)
    try:
        streak = await _current_streak_days(db, user.user_id)
    except Exception:  # noqa: BLE001
        streak = 0
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    milestones_this_week: List[str] = []
    try:
        cursor = db["wall_events"].find(
            {"user_id": user.user_id,
             "created_at": {"$gte": week_start.isoformat()}},
            {"_id": 0, "badge_type": 1, "created_at": 1},
        ).sort("created_at", 1)
        seen = []
        async for row in cursor:
            label = BADGE_LABELS.get(row["badge_type"], row["badge_type"])
            seen.append(label.rstrip("."))
        milestones_this_week = list(dict.fromkeys(seen))
    except Exception:  # noqa: BLE001
        milestones_this_week = []
    frontend_origin = os.environ.get("FRONTEND_ORIGIN") or "https://sacoparentsapp.online"
    note_doc = await _fetch_weekly_note(db, user.user_id, _iso_week_key(now))
    # Community cheer digest — anonymised hearts landed on this parent's
    # badges plus the community's top-cheered moments this week.
    try:
        cheer_digest = await build_weekly_cheer_digest(db, user.user_id, week_start)
    except Exception:  # noqa: BLE001
        cheer_digest = {"opted_in": False, "cheers_received": [],
                        "community_pulse": [], "week_start": week_start.isoformat()}
    total_cheers_received = sum(
        int(r.get("cheer_count") or 0) for r in cheer_digest["cheers_received"]
    )
    return {
        "user_name": user.name,
        "user_email": user.email,
        "completed_count": int(progress.get("completed_count") or 0),
        "total": int(progress.get("total") or 5),
        "streak_days": int(streak),
        "milestones_this_week": milestones_this_week,
        "alignment_pct": progress.get("alignment_pct"),
        "dashboard_url": f"{frontend_origin.rstrip('/')}/dashboard",
        "personal_note": note_doc["note"],
        "personal_note_updated_at": note_doc["updated_at"],
        "wall_opted_in":       cheer_digest["opted_in"],
        "cheers_received":     cheer_digest["cheers_received"],
        "cheers_received_total": int(total_cheers_received),
        "community_pulse":     cheer_digest["community_pulse"],
    }


@router.get("/weekly-email/preview")
async def weekly_email_preview(user: UserPublic = Depends(get_current_user),
                               db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Return the exact data the upcoming Sunday email will contain, so
    the dashboard can render an inline preview. Also surfaces the current
    week's send state so the UI can label the card."""
    ctx = await _build_weekly_email_context(db, user)
    week_key = _iso_week_key()
    log = await db[_WEEKLY_EMAIL_LOG].find_one(
        {"user_id": user.user_id, "week_key": week_key}, {"_id": 0},
    )
    now = datetime.now(timezone.utc)
    return {
        "week_key": week_key,
        "sent_this_week": bool(log),
        "sent_at": (log or {}).get("sent_at"),
        "is_sunday_utc": now.weekday() == 6,
        "weekday_utc": now.weekday(),
        "preview": ctx,
    }


@router.post("/weekly-email/send")
async def send_weekly_email(body: WeeklyEmailIn = WeeklyEmailIn(),
                            user: UserPublic = Depends(get_current_user),
                            db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Send the parent their Sunday progress snapshot. Idempotent per ISO
    week — a second call in the same week returns `already_sent: True`
    unless `force=True`. Auto-fire safe: the frontend can call this every
    time the dashboard loads on a Sunday without spamming."""
    if not (user.email or "").strip():
        raise HTTPException(status_code=400,
                            detail="Add an email to your profile first.")
    week_key = _iso_week_key()
    log = await db[_WEEKLY_EMAIL_LOG].find_one(
        {"user_id": user.user_id, "week_key": week_key}, {"_id": 0},
    )
    if log and not body.force:
        return {"ok": True, "already_sent": True, "week_key": week_key,
                "sent_at": log.get("sent_at")}

    ctx = await _build_weekly_email_context(db, user)

    from email_service import send_weekly_progress_summary
    try:
        send_weekly_progress_summary(
            to_email=user.email,
            user_name=user.name,
            completed_count=ctx["completed_count"],
            total=ctx["total"],
            streak_days=ctx["streak_days"],
            milestones_this_week=ctx["milestones_this_week"],
            alignment_pct=ctx["alignment_pct"],
            dashboard_url=ctx["dashboard_url"],
            personal_note=ctx.get("personal_note") or "",
            cheers_received=ctx.get("cheers_received") or [],
            community_pulse=ctx.get("community_pulse") or [],
            wall_opted_in=bool(ctx.get("wall_opted_in")),
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503,
                            detail="Email is temporarily unavailable. Try again shortly.") from e

    sent_at_iso = datetime.now(timezone.utc).isoformat()
    await db[_WEEKLY_EMAIL_LOG].update_one(
        {"user_id": user.user_id, "week_key": week_key},
        {"$set": {
            "user_id": user.user_id,
            "week_key": week_key,
            "sent_at": sent_at_iso,
            "completed_count": ctx["completed_count"],
            "streak_days": ctx["streak_days"],
            "had_personal_note": bool((ctx.get("personal_note") or "").strip()),
        }},
        upsert=True,
    )
    # Auto-clear the handwritten note for this week once the email fires
    # so next week starts from a blank slate (user preference: fresh weekly).
    await db[_WEEKLY_EMAIL_NOTES].delete_one(
        {"user_id": user.user_id, "week_key": week_key},
    )
    return {
        "ok": True,
        "already_sent": False,
        "week_key": week_key,
        "sent_at": sent_at_iso,
        "milestones_this_week": ctx["milestones_this_week"],
        "streak_days": ctx["streak_days"],
        "personal_note_included": bool((ctx.get("personal_note") or "").strip()),
        "cheers_received_total": int(ctx.get("cheers_received_total") or 0),
        "community_pulse_count": len(ctx.get("community_pulse") or []),
    }


@router.get("/weekly-email/status")
async def weekly_email_status(user: UserPublic = Depends(get_current_user),
                              db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Frontend uses this to decide whether to auto-fire the Sunday email:
    returns whether we've already sent for this ISO week + today's UTC
    weekday (Mon=0, Sun=6)."""
    week_key = _iso_week_key()
    log = await db[_WEEKLY_EMAIL_LOG].find_one(
        {"user_id": user.user_id, "week_key": week_key}, {"_id": 0},
    )
    now = datetime.now(timezone.utc)
    return {
        "week_key": week_key,
        "sent_this_week": bool(log),
        "sent_at": (log or {}).get("sent_at"),
        "is_sunday_utc": now.weekday() == 6,
        "weekday_utc": now.weekday(),
    }



# ---------------------------------------------------------------------------
# Weekly Email — handwritten personal note (per ISO week, auto-clears on send).
# ---------------------------------------------------------------------------
@router.get("/weekly-email/note")
async def get_weekly_email_note(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the parent's saved handwritten note for the current ISO week.
    The note is week-scoped and auto-clears once the Sunday email fires."""
    return await _fetch_weekly_note(db, user.user_id, _iso_week_key())


@router.post("/weekly-email/note")
async def save_weekly_email_note(
    body: WeeklyNoteIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Save (or clear) the parent's handwritten note for the current ISO
    week. Silently trims to `_WEEKLY_NOTE_MAX_CHARS` — the frontend also
    enforces this but we clamp defensively for API callers."""
    week_key = _iso_week_key()
    text = (body.note or "").strip()
    if len(text) > _WEEKLY_NOTE_MAX_CHARS:
        text = text[:_WEEKLY_NOTE_MAX_CHARS].rstrip()
    if not text:
        await db[_WEEKLY_EMAIL_NOTES].delete_one(
            {"user_id": user.user_id, "week_key": week_key},
        )
        return {
            "note": "", "updated_at": None, "week_key": week_key,
            "max_chars": _WEEKLY_NOTE_MAX_CHARS, "cleared": True,
        }
    updated_at = datetime.now(timezone.utc).isoformat()
    await db[_WEEKLY_EMAIL_NOTES].update_one(
        {"user_id": user.user_id, "week_key": week_key},
        {"$set": {
            "user_id": user.user_id,
            "week_key": week_key,
            "note": text,
            "updated_at": updated_at,
        }},
        upsert=True,
    )
    return {
        "note": text,
        "updated_at": updated_at,
        "week_key": week_key,
        "max_chars": _WEEKLY_NOTE_MAX_CHARS,
        "cleared": False,
    }
