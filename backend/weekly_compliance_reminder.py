"""Weekly Compliance Reminder — friendly Monday nudge.

When a parent has ≥1 intervention still un-ticked for the current ISO week
AND is opted-in, we send them a warm email listing what's outstanding + their
current streak. The email exists purely to defend the follow-through streak
the compliance system already rewards (iteration 86 badges).

Suppression rules (short-circuit any of these → no send):
  * User has opted out of the reminder (`intervention_reminder_prefs.opted_in`)
  * User has already hit ≥80% for the current week (mission accomplished)
  * User has had zero compliance activity in the past 60 days (drift — no
    email would recover them anyway; avoids dunning inactive users)
  * A reminder has already been sent to this user for this ISO week
    (dedupe via `weekly_compliance_reminder_sends`)
  * User has no email on file or the address looks like a demo/guest

Runtime is gated behind `WEEKLY_COMPLIANCE_REMINDER_ENABLED=1`. The loop is
built to sweep every 60 minutes and only actually dispatch during the
Monday 08:00-22:00 UTC window — parents in the Americas get their nudge
during their real Monday, everyone else gets it Monday-ish. Timezone
personalisation is a future refinement.

Public surface:
  * `send_weekly_compliance_reminders(db, dry_run=False, now=None)` — pure
    coroutine that runs one sweep pass; returns per-user results (used by
    the operator preview endpoint AND the scheduler loop).
  * `weekly_compliance_reminder_loop(app)` — long-running background task
    started from server.py.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

PREFS_COLLECTION = "intervention_reminder_prefs"
SENDS_COLLECTION = "weekly_compliance_reminder_sends"
COMPLIANCE_COLLECTION = "intervention_compliance"

# Suppression thresholds.
_HIGH_ENOUGH_PCT = 80.0           # matches STREAK_THRESHOLD_PCT
_INACTIVITY_DAYS = 60             # no compliance activity in this window → drop

# Sweep loop schedule.
_SWEEP_INTERVAL_S = int(os.environ.get("WEEKLY_COMPLIANCE_REMINDER_SWEEP_SECONDS", "3600"))
_MONDAY_SEND_START_UTC_HOUR = int(os.environ.get("WEEKLY_COMPLIANCE_REMINDER_START_HOUR_UTC", "8"))
_MONDAY_SEND_END_UTC_HOUR = int(os.environ.get("WEEKLY_COMPLIANCE_REMINDER_END_HOUR_UTC", "22"))

# Public URL for the CTA button.
_APP_URL = (os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")


# ---------------------------------------------------------------------------
# Date helpers — kept local so this module doesn't take a hard dep on
# intervention_compliance_routes at import time.
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _week_start(dt: Optional[datetime] = None) -> str:
    d = (dt or _now_utc()).astimezone(timezone.utc)
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _in_send_window(now: datetime) -> bool:
    """True iff `now` is Monday between the configured UTC hour window."""
    now = now.astimezone(timezone.utc)
    return (
        now.weekday() == 0                                     # Monday
        and _MONDAY_SEND_START_UTC_HOUR <= now.hour < _MONDAY_SEND_END_UTC_HOUR
    )


def _reminder_link() -> str:
    return f"{_APP_URL}/compliance" if _APP_URL else "/compliance"


# ---------------------------------------------------------------------------
# Preferences.
# ---------------------------------------------------------------------------

async def get_reminder_pref(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Return `{opted_in: bool, updated_at: iso|null}`.

    Default is opted-in — parents who set up a compliance streak signalled
    they want to be reminded to keep it. Explicit opt-out is a one-tap
    toggle on the compliance page.
    """
    row = await db[PREFS_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0, "opted_in": 1, "updated_at": 1},
    )
    if not row:
        return {"opted_in": True, "updated_at": None}
    return {
        "opted_in":   bool(row.get("opted_in", True)),
        "updated_at": row.get("updated_at"),
    }


async def set_reminder_pref(
    db: AsyncIOMotorDatabase, user_id: str, opted_in: bool
) -> Dict[str, Any]:
    now = _now_utc().isoformat()
    await db[PREFS_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "opted_in": bool(opted_in), "updated_at": now}},
        upsert=True,
    )
    return {"opted_in": bool(opted_in), "updated_at": now}


# ---------------------------------------------------------------------------
# Suppression / decision helpers.
# ---------------------------------------------------------------------------

def _is_demo_email(email: Optional[str]) -> bool:
    if not email:
        return True
    e = email.strip().lower()
    return not e or "@demo.local" in e


async def _has_recent_compliance(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """True iff the user has ticked or logged anything in the compliance
    collection in the last _INACTIVITY_DAYS days."""
    cutoff = (_now_utc() - timedelta(days=_INACTIVITY_DAYS)).isoformat()
    row = await db[COMPLIANCE_COLLECTION].find_one(
        {"user_id": user_id, "updated_at": {"$gte": cutoff}},
        {"_id": 1},
    )
    return bool(row)


async def _already_sent_this_week(
    db: AsyncIOMotorDatabase, user_id: str, week_start: str
) -> bool:
    row = await db[SENDS_COLLECTION].find_one(
        {"user_id": user_id, "week_start": week_start}, {"_id": 1},
    )
    return bool(row)


async def _current_week_summary(
    db: AsyncIOMotorDatabase, user_id: str
) -> Dict[str, Any]:
    """Ask intervention_compliance_routes for the full log; return the
    subset the reminder needs. Lazy import to avoid module-load cycles."""
    from intervention_compliance_routes import _load_latest_interventions

    wk = _week_start()
    catalog = await _load_latest_interventions(db, user_id)

    if not catalog:
        return {"week_start": wk, "total": 0, "followed": 0,
                "pending_items": [], "compliance_pct": 0.0}

    existing_cursor = db[COMPLIANCE_COLLECTION].find(
        {"user_id": user_id, "week_start": wk},
        {"_id": 0, "intervention_key": 1, "followed": 1},
    )
    ticked: set = set()
    async for row in existing_cursor:
        if row.get("followed"):
            ticked.add(row["intervention_key"])

    pending = [c for c in catalog if c["key"] not in ticked]
    total = len(catalog)
    followed = total - len(pending)
    pct = round((followed / total) * 100, 1) if total else 0.0

    return {
        "week_start":     wk,
        "total":          total,
        "followed":       followed,
        "compliance_pct": pct,
        "pending_items":  pending,
    }


async def _current_streak(db: AsyncIOMotorDatabase, user_id: str) -> int:
    from intervention_compliance_routes import build_compliance_snapshot
    snap = await build_compliance_snapshot(db, user_id)
    return int(((snap or {}).get("streak") or {}).get("current_streak") or 0)


# ---------------------------------------------------------------------------
# Sweep pass.
# ---------------------------------------------------------------------------

async def _iter_candidate_users(db: AsyncIOMotorDatabase) -> List[str]:
    """Return user_ids who have compliance activity in the last window."""
    cutoff = (_now_utc() - timedelta(days=_INACTIVITY_DAYS)).isoformat()
    return await db[COMPLIANCE_COLLECTION].distinct(
        "user_id", {"updated_at": {"$gte": cutoff}},
    )


async def _resolve_user_profile(
    db: AsyncIOMotorDatabase, user_id: str
) -> Optional[Dict[str, Any]]:
    """Fetch email + display name from the users collection."""
    row = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "user_id": 1, "email": 1, "name": 1},
    )
    return row


async def _dispatch_one(
    db: AsyncIOMotorDatabase, user_id: str, dry_run: bool,
) -> Dict[str, Any]:
    """Evaluate one user and (unless dry_run) send + record. Returns a
    diagnostic dict."""
    prof = await _resolve_user_profile(db, user_id)
    if not prof:
        return {"user_id": user_id, "sent": False, "reason": "no_user_row"}
    email = prof.get("email")
    if _is_demo_email(email):
        return {"user_id": user_id, "sent": False, "reason": "no_or_demo_email"}

    pref = await get_reminder_pref(db, user_id)
    if not pref["opted_in"]:
        return {"user_id": user_id, "sent": False, "reason": "opted_out"}

    if not await _has_recent_compliance(db, user_id):
        return {"user_id": user_id, "sent": False, "reason": "inactive"}

    wk = _week_start()
    if await _already_sent_this_week(db, user_id, wk):
        return {"user_id": user_id, "sent": False, "reason": "already_sent_this_week"}

    summary = await _current_week_summary(db, user_id)
    if summary["total"] == 0:
        return {"user_id": user_id, "sent": False, "reason": "no_checklist"}
    if summary["compliance_pct"] >= _HIGH_ENOUGH_PCT:
        return {"user_id": user_id, "sent": False, "reason": "already_high_enough"}

    streak = await _current_streak(db, user_id)

    if dry_run:
        return {
            "user_id":        user_id,
            "sent":           False,
            "reason":         "dry_run",
            "would_send_to":  email,
            "pending_count":  len(summary["pending_items"]),
            "current_streak": streak,
        }

    try:
        from email_service import send_weekly_compliance_reminder
        send_weekly_compliance_reminder(
            to_email=email,
            user_name=prof.get("name") or "",
            pending_items=[
                {"text": p["text"], "source": p.get("source"), "group": p.get("group")}
                for p in summary["pending_items"][:5]
            ],
            pending_total=len(summary["pending_items"]),
            current_streak=streak,
            compliance_pct=summary["compliance_pct"],
            week_start=wk,
            cta_url=_reminder_link(),
        )
        send_ok, send_err = True, None
    except Exception as exc:  # noqa: BLE001
        log.warning("weekly compliance reminder send failed for %s: %s", user_id, exc)
        send_ok, send_err = False, str(exc)

    await db[SENDS_COLLECTION].insert_one({
        "user_id":         user_id,
        "week_start":      wk,
        "sent_at":         _now_utc().isoformat(),
        "email":           email,
        "pending_count":   len(summary["pending_items"]),
        "current_streak":  streak,
        "email_ok":        send_ok,
        "email_error":     send_err,
    })
    return {
        "user_id":        user_id,
        "sent":           send_ok,
        "reason":         "delivered" if send_ok else "email_error",
        "email":          email,
        "pending_count":  len(summary["pending_items"]),
        "current_streak": streak,
        "email_error":    send_err,
    }


async def send_weekly_compliance_reminders(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    force_window: bool = False,
) -> Dict[str, Any]:
    """Run one sweep pass.

    `force_window=True` skips the Monday-window gate — used by the operator
    preview endpoint so we can test the sweep any day of the week.
    """
    now = now or _now_utc()
    if not force_window and not _in_send_window(now):
        return {"skipped": "outside_send_window", "at": now.isoformat(), "results": []}

    results: List[Dict[str, Any]] = []
    for uid in await _iter_candidate_users(db):
        try:
            results.append(await _dispatch_one(db, uid, dry_run=dry_run))
        except Exception as exc:  # noqa: BLE001
            log.exception("weekly reminder sweep failed for %s", uid)
            results.append({"user_id": uid, "sent": False, "reason": f"exception: {exc}"})
    return {"at": now.isoformat(), "count": len(results), "results": results}


# ---------------------------------------------------------------------------
# Background loop.
# ---------------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("WEEKLY_COMPLIANCE_REMINDER_ENABLED") or "").strip() in {"1", "true", "yes", "on"}


async def weekly_compliance_reminder_loop(app) -> None:
    """Long-running sweep task started from server.py. No-ops silently when
    the feature is not turned on via env var — safe to always register."""
    if not _enabled():
        log.info("weekly_compliance_reminder_loop: WEEKLY_COMPLIANCE_REMINDER_ENABLED not set; loop idle")
        # Sleep forever rather than exit, so if the operator flips the
        # flag AFTER startup (and restarts supervisord) we still get a
        # clean state on the next boot.
        while True:
            await asyncio.sleep(3600)
    await asyncio.sleep(120)  # small warmup so DB is ready
    while True:
        try:
            db = app.state.db
            await send_weekly_compliance_reminders(db)
        except Exception:  # noqa: BLE001
            log.exception("weekly compliance reminder sweep failed; will retry.")
        await asyncio.sleep(_SWEEP_INTERVAL_S)
