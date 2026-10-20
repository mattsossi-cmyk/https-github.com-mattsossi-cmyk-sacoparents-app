"""Intervention Compliance Log — weekly check-in on which enforced
interventions a parent is actually following.

Interventions come from three sources on the app:
    * Safety Assessment       -> `result.recommendations`
    * ND Risk Assessment      -> `scoring.interventions`
    * Dimension Companion     -> per-dimension `interventions`

At request time we aggregate the parent's LATEST assessment from each
source and mint a stable `intervention_key` = md5(source|text)[:16]
(non-security dedupe id — see `_key`).
The parent then ticks off each item per calendar week (Mon 00:00 UTC).

Storage:
    intervention_compliance  — one document per (user_id, week_start,
                              intervention_key). Idempotent upsert.

Endpoints:
    GET  /api/interventions/log                — current week + items
    POST /api/interventions/log                — upsert one item
    GET  /api/interventions/log/history?weeks=N — % followed for last N weeks
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


router = APIRouter(prefix="/interventions", tags=["interventions"])
COLLECTION = "intervention_compliance"

Source = Literal["safety", "nd_risk", "companion"]


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _week_start(dt: Optional[datetime] = None) -> str:
    """Return ISO date (YYYY-MM-DD) of the Monday of the given UTC datetime."""
    d = (dt or datetime.now(timezone.utc)).astimezone(timezone.utc)
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _key(source: str, text: str) -> str:
    """Stable intervention key across re-assessments — as long as the
    source + wording stay the same, the parent's tick persists.

    Uses MD5 with ``usedforsecurity=False`` because this is a persisted
    dedupe id in ``intervention_compliance_logs.item_key`` — collisions
    here have no security implication, and switching algorithms would
    invalidate every existing user's tick history without a migration.
    """
    return hashlib.md5(  # noqa: S324 — non-security dedupe key (see docstring)
        f"{source}|{text.strip()}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:16]


# ---------------------------------------------------------------------------
# AGGREGATION — build the current-week checklist from latest assessments.
# ---------------------------------------------------------------------------

async def _load_latest_interventions(
    db: AsyncIOMotorDatabase, user_id: str
) -> List[Dict[str, Any]]:
    """Return a flat list of {key, source, group, text} across the parent's
    latest Safety + ND Risk + Companion assessments."""
    items: List[Dict[str, Any]] = []

    # Safety
    safety = None  # in-app safety screen is off
    if safety:
        recs = ((safety.get("result") or {}).get("recommendations") or [])
        level = (safety.get("result") or {}).get("level")
        for txt in recs:
            items.append({
                "key":    _key("safety", txt),
                "source": "safety",
                "group":  f"Dimension 1 · Safety (Level {level})" if level else "Dimension 1 · Safety",
                "text":   txt,
            })

    # ND Risk (most recent)
    nd = await db.nd_assessments.find_one(
        {"target_user_id": user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if nd:
        tier_label = ((nd.get("scoring") or {}).get("tier_label") or "").strip() or "?"
        for txt in ((nd.get("scoring") or {}).get("interventions") or []):
            items.append({
                "key":    _key("nd_risk", txt),
                "source": "nd_risk",
                "group":  f"ND Risk · {tier_label} tier",
                "text":   txt,
            })

    # Companion
    comp = await db.dimension_companion_assessments.find_one(
        {"user_id": user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if comp:
        dims = ((comp.get("scoring") or {}).get("dimensions") or {})
        # Preserve numerical order.
        for k, num, label in (
            ("communication",        "2", "Communication"),
            ("emotional_regulation", "3", "Emotional regulation"),
            ("executive_function",   "4", "Executive function"),
        ):
            d = dims.get(k) or {}
            tier_label = d.get("tier_label") or "-"
            for txt in (d.get("interventions") or []):
                items.append({
                    "key":    _key("companion", txt),
                    "source": "companion",
                    "group":  f"Dimension {num} · {label} ({tier_label})",
                    "text":   txt,
                })
    return items


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class LogEntryPatch(BaseModel):
    intervention_key: str = Field(..., min_length=8, max_length=32)
    source:           Source
    text:             str = Field(..., min_length=1, max_length=1000)
    group:            Optional[str] = Field(None, max_length=200)
    followed:         bool
    notes:            Optional[str] = Field(None, max_length=800)
    week_start:       Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@router.get("/log")
async def get_current_log(
    week_start: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the merged checklist for the current (or specified) week.

    Response shape:
        {
          week_start,
          items: [{key, source, group, text, followed, notes, updated_at}],
          summary: {total, followed, compliance_pct},
        }
    """
    wk = week_start or _week_start()
    catalog = await _load_latest_interventions(db, user.user_id)

    # Batch-fetch existing ticks for this week.
    existing_cursor = db[COLLECTION].find(
        {"user_id": user.user_id, "week_start": wk},
        {"_id": 0},
    )
    existing_by_key: Dict[str, Dict[str, Any]] = {}
    async for row in existing_cursor:
        existing_by_key[row["intervention_key"]] = row

    items: List[Dict[str, Any]] = []
    followed_count = 0
    for c in catalog:
        prior = existing_by_key.get(c["key"]) or {}
        followed = bool(prior.get("followed"))
        if followed:
            followed_count += 1
        items.append({
            **c,
            "followed":   followed,
            "notes":      prior.get("notes"),
            "updated_at": prior.get("updated_at"),
        })

    total = len(items)
    return {
        "week_start": wk,
        "items":      items,
        "summary": {
            "total":          total,
            "followed":       followed_count,
            "compliance_pct": round((followed_count / total) * 100, 1) if total else 0.0,
        },
    }


@router.post("/log")
async def upsert_log_entry(
    body: LogEntryPatch,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    wk = body.week_start or _week_start()
    now = datetime.now(timezone.utc).isoformat()
    result = await db[COLLECTION].update_one(
        {
            "user_id":          user.user_id,
            "week_start":       wk,
            "intervention_key": body.intervention_key,
        },
        {
            "$set": {
                "source":     body.source,
                "text":       body.text,
                "group":      body.group,
                "followed":   body.followed,
                "notes":      body.notes,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return {
        "ok":         True,
        "week_start": wk,
        "matched":    result.matched_count,
        "modified":   result.modified_count,
        "upserted":   bool(result.upserted_id),
    }


@router.get("/log/history")
async def get_history(
    weeks: int = Query(8, ge=1, le=26),
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Weekly compliance % for the last `weeks` weeks (oldest first).

    We compute the denominator per-week from the entries the parent
    actually engaged with that week — this avoids penalising a parent
    whose intervention catalog grew due to a re-assessment. If a week
    has zero recorded ticks, compliance_pct is `null` (rendered as an
    empty bar on the sparkline).
    """
    today = datetime.now(timezone.utc)
    cutoff_date = today - timedelta(days=weeks * 7)
    cursor = db[COLLECTION].find(
        {
            "user_id":    user.user_id,
            "week_start": {"$gte": _week_start(cutoff_date)},
        },
        {"_id": 0, "week_start": 1, "followed": 1},
    )
    by_week: Dict[str, Dict[str, int]] = {}
    async for row in cursor:
        w = row["week_start"]
        bucket = by_week.setdefault(w, {"total": 0, "followed": 0})
        bucket["total"] += 1
        if row.get("followed"):
            bucket["followed"] += 1

    # Emit weeks in chronological order, filling gaps with nulls.
    out: List[Dict[str, Any]] = []
    for i in range(weeks - 1, -1, -1):
        d = today - timedelta(days=i * 7)
        wk = _week_start(d)
        b = by_week.get(wk)
        if not b:
            out.append({"week_start": wk, "total": 0, "followed": 0, "compliance_pct": None})
        else:
            out.append({
                "week_start":     wk,
                "total":          b["total"],
                "followed":       b["followed"],
                "compliance_pct": round((b["followed"] / b["total"]) * 100, 1) if b["total"] else None,
            })
    return {"weeks": out}


# ---------------------------------------------------------------------------
# STREAK REWARDS
# ---------------------------------------------------------------------------

STREAK_THRESHOLD_PCT = 80.0  # weekly compliance % that counts toward the streak

BADGES: List[Dict[str, Any]] = [
    {"key": "compliance_streak_4",  "weeks": 4,
     "label": "4-Week Compliance Champion",
     "description": "Followed your enforced interventions at ≥80% for four weeks in a row."},
    {"key": "compliance_streak_8",  "weeks": 8,
     "label": "8-Week Consistency Anchor",
     "description": "Eight consecutive weeks at ≥80% compliance."},
    {"key": "compliance_streak_12", "weeks": 12,
     "label": "Quarter-Year Habit",
     "description": "A full quarter of ≥80% weekly compliance."},
]


def _compute_streak(weekly_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Given weeks oldest→newest, return current + longest streak lengths.

    A week counts toward a streak when `compliance_pct >= STREAK_THRESHOLD_PCT`.
    Weeks with `null` compliance (no ticks recorded) BREAK the streak — silence
    is not credit. This mirrors the badge language the parent sees.
    """
    current = 0
    longest = 0
    for row in weekly_rows:
        pct = row.get("compliance_pct")
        if pct is not None and pct >= STREAK_THRESHOLD_PCT:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {"current_streak": current, "longest_streak": longest}


async def build_compliance_snapshot(
    db: AsyncIOMotorDatabase, user_id: str
) -> Dict[str, Any]:
    """Return a compact {current_week, streak} snapshot for a user, safe to
    embed in a PDF or email. Uses the same 80% threshold + badge ladder as
    the API endpoints. Public so other modules (PDF, email) can reuse."""
    from datetime import datetime, timedelta, timezone as _tz

    now = datetime.now(_tz.utc)
    weeks_window = 26
    cutoff_date = now - timedelta(days=weeks_window * 7)
    cursor = db[COLLECTION].find(
        {"user_id": user_id, "week_start": {"$gte": _week_start(cutoff_date)}},
        {"_id": 0, "week_start": 1, "followed": 1},
    )
    by_week: Dict[str, Dict[str, int]] = {}
    async for row in cursor:
        b = by_week.setdefault(row["week_start"], {"total": 0, "followed": 0})
        b["total"] += 1
        if row.get("followed"):
            b["followed"] += 1

    weekly_rows: List[Dict[str, Any]] = []
    for i in range(weeks_window - 1, -1, -1):
        d = now - timedelta(days=i * 7)
        wk = _week_start(d)
        b = by_week.get(wk)
        pct = round((b["followed"] / b["total"]) * 100, 1) if b and b["total"] else None
        weekly_rows.append({"week_start": wk, "compliance_pct": pct})

    streak = _compute_streak(weekly_rows)

    # Same badge ladder as /streak.
    badges_out: List[Dict[str, Any]] = []
    next_badge: Optional[Dict[str, Any]] = None
    for b in BADGES:
        earned = streak["longest_streak"] >= b["weeks"]
        badges_out.append({**b, "earned": earned})
        if not earned and next_badge is None:
            next_badge = {
                "key":          b["key"],
                "label":        b["label"],
                "weeks":        b["weeks"],
                "weeks_to_go":  b["weeks"] - streak["current_streak"],
                "progress_pct": round((streak["current_streak"] / b["weeks"]) * 100, 1),
            }

    # Current week aggregates
    this_wk = _week_start(now)
    this_bucket = by_week.get(this_wk, {"total": 0, "followed": 0})
    if this_bucket["total"]:
        pct = round((this_bucket["followed"] / this_bucket["total"]) * 100, 1)
    else:
        pct = None

    return {
        "current_week": {
            "week_start":     this_wk,
            "total":          this_bucket["total"],
            "followed":       this_bucket["followed"],
            "compliance_pct": pct,
        },
        "streak": {
            "threshold_pct":  STREAK_THRESHOLD_PCT,
            "current_streak": streak["current_streak"],
            "longest_streak": streak["longest_streak"],
            "badges":         badges_out,
            "next_badge":     next_badge,
        },
    }


@router.get("/streak")
async def get_streak_and_badges(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the parent's current + longest ≥80% streak, badges earned,
    and progress toward the next badge. The window looks back 26 weeks
    which is enough for the longest badge (12 weeks) plus buffer.
    """
    today = datetime.now(timezone.utc)
    weeks_window = 26
    cutoff_date = today - timedelta(days=weeks_window * 7)
    cursor = db[COLLECTION].find(
        {"user_id": user.user_id, "week_start": {"$gte": _week_start(cutoff_date)}},
        {"_id": 0, "week_start": 1, "followed": 1},
    )
    by_week: Dict[str, Dict[str, int]] = {}
    async for row in cursor:
        b = by_week.setdefault(row["week_start"], {"total": 0, "followed": 0})
        b["total"] += 1
        if row.get("followed"):
            b["followed"] += 1

    weekly_rows: List[Dict[str, Any]] = []
    for i in range(weeks_window - 1, -1, -1):
        d = today - timedelta(days=i * 7)
        wk = _week_start(d)
        b = by_week.get(wk)
        if b and b["total"]:
            pct = round((b["followed"] / b["total"]) * 100, 1)
        else:
            pct = None
        weekly_rows.append({"week_start": wk, "compliance_pct": pct})

    streak = _compute_streak(weekly_rows)

    # Badges — award based on longest streak (once earned, they stay).
    badges_out: List[Dict[str, Any]] = []
    next_badge: Optional[Dict[str, Any]] = None
    for b in BADGES:
        earned = streak["longest_streak"] >= b["weeks"]
        badges_out.append({**b, "earned": earned})
        if not earned and next_badge is None:
            next_badge = {
                "key":            b["key"],
                "label":          b["label"],
                "weeks":          b["weeks"],
                "weeks_to_go":    b["weeks"] - streak["current_streak"],
                "progress_pct":   round((streak["current_streak"] / b["weeks"]) * 100, 1),
            }

    return {
        "threshold_pct":  STREAK_THRESHOLD_PCT,
        "current_streak": streak["current_streak"],
        "longest_streak": streak["longest_streak"],
        "badges":         badges_out,
        "next_badge":     next_badge,
    }



# ---------------------------------------------------------------------------
# WEEKLY REMINDER PREFERENCES + OPERATOR PREVIEW
# ---------------------------------------------------------------------------

class ReminderPrefUpdate(BaseModel):
    opted_in: bool


@router.get("/reminder-preferences")
async def get_reminder_preferences(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return whether this parent wants the weekly Monday reminder email.

    Default is opted-in (implicit — if no row exists we treat it as True).
    """
    from weekly_compliance_reminder import get_reminder_pref
    return await get_reminder_pref(db, user.user_id)


@router.put("/reminder-preferences")
async def update_reminder_preferences(
    body: ReminderPrefUpdate,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Toggle the weekly Monday reminder email on/off for this parent."""
    from weekly_compliance_reminder import set_reminder_pref
    return await set_reminder_pref(db, user.user_id, body.opted_in)


@router.post("/weekly-reminder/admin/send-me-preview")
async def admin_send_me_weekly_reminder_preview(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Fire a real weekly-reminder email to the operator's inbox using
    their real compliance data. Operator-only. Lets the operator sanity-
    check formatting without waiting for Monday."""
    import os as _os
    from weekly_compliance_reminder import (
        _current_streak, _current_week_summary, _reminder_link,
    )
    from email_service import send_weekly_compliance_reminder

    operator_email = (_os.environ.get("OPERATOR_EMAIL") or "").strip().lower()
    if not operator_email or (user.email or "").strip().lower() != operator_email:
        raise HTTPException(403, "Operator only.")

    summary = await _current_week_summary(db, user.user_id)
    streak = await _current_streak(db, user.user_id)

    send_weekly_compliance_reminder(
        to_email=user.email,
        user_name=user.name or "",
        pending_items=[
            {"text": p["text"], "source": p.get("source"), "group": p.get("group")}
            for p in (summary.get("pending_items") or [])[:5]
        ],
        pending_total=len(summary.get("pending_items") or []),
        current_streak=streak,
        compliance_pct=summary.get("compliance_pct") or 0.0,
        week_start=summary.get("week_start") or "",
        cta_url=_reminder_link(),
    )
    return {
        "ok":             True,
        "sent_to":        user.email,
        "pending_count":  len(summary.get("pending_items") or []),
        "current_streak": streak,
        "week_start":     summary.get("week_start"),
    }


@router.post("/weekly-reminder/admin/sweep")
async def admin_run_weekly_reminder_sweep(
    dry_run: bool = Query(True),
    force_window: bool = Query(False),
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Operator-only: run one sweep pass on demand. Defaults to `dry_run=True`
    so the operator can see who WOULD get the reminder without actually
    dispatching. Pass `dry_run=false&force_window=true` to fire real emails
    off-schedule (use with care)."""
    import os as _os
    from weekly_compliance_reminder import send_weekly_compliance_reminders

    operator_email = (_os.environ.get("OPERATOR_EMAIL") or "").strip().lower()
    if not operator_email or (user.email or "").strip().lower() != operator_email:
        raise HTTPException(403, "Operator only.")
    return await send_weekly_compliance_reminders(
        db, dry_run=dry_run, force_window=force_window,
    )
