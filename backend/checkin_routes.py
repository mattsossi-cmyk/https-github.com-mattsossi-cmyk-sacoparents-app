"""Two-week post-summary check-in email.

When a user generates a Mediation Prep Summary, we schedule a friendly check-in
14 days later. The email includes their personal weekly-journal recap (if they
have at least 2 entries in the past 7 days) plus a soft CTA back into the app.

Idempotent: only one check-in is scheduled per (user_id, summary_id). Guests
without an email address are skipped.

A background `asyncio` task in server.py (`checkin_scheduler_loop`) sweeps
the queue every 30 minutes.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

import ai_service
import email_service


logger = logging.getLogger(__name__)

CHECKIN_DELAY_DAYS = int(os.environ.get("POST_SUMMARY_CHECKIN_DELAY_DAYS", "14"))
SCHEDULER_INTERVAL_SECONDS = int(os.environ.get("POST_SUMMARY_CHECKIN_SWEEP_SECONDS", "1800"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _public_app_url() -> str:
    return (os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")


def _journal_link() -> str:
    base = _public_app_url()
    return f"{base}/journal" if base else "/journal"


async def schedule_post_summary_checkin(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    email: Optional[str],
    name: Optional[str],
    summary_id: str,
) -> None:
    """Idempotent: skips if a check-in already exists for this (user, summary).
    Also skips guests without a real email."""
    if not email or "@demo.local" in email:
        return
    existing = await db.post_summary_checkins.find_one(
        {"user_id": user_id, "summary_id": summary_id}, {"_id": 0, "checkin_id": 1}
    )
    if existing:
        return
    await db.post_summary_checkins.insert_one({
        "checkin_id": f"chk_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "summary_id": summary_id,
        "email": email,
        "name": name or "",
        "status": "pending",
        "created_at": _iso(_now()),
        "scheduled_send_at": _iso(_now() + timedelta(days=CHECKIN_DELAY_DAYS)),
        "sent_at": None,
    })


async def _build_recap_text(db: AsyncIOMotorDatabase, user_id: str) -> Optional[str]:
    """Pull the user's last 7 days of journal entries and (if any) produce a
    short AI recap. Returns None if there's nothing meaningful to summarize."""
    week_start = _iso(_now() - timedelta(days=7))
    cursor = db.journal_entries.find(
        {"user_id": user_id, "created_at": {"$gte": week_start}},
        {"_id": 0, "kind": 1, "content": 1, "prompt_text": 1, "created_at": 1},
    ).sort("created_at", 1)
    entries = await cursor.to_list(50)
    if len(entries) < 2:
        return None
    if not os.environ.get("EMERGENT_LLM_KEY"):
        return None
    try:
        result = await ai_service.generate_journal_weekly_recap(entries)
        return (result or {}).get("recap_text")
    except Exception:  # noqa: BLE001
        logger.exception("Checkin recap generation failed for user %s", user_id)
        return None


async def _process_one(db: AsyncIOMotorDatabase, doc: dict) -> None:
    """Generate recap + send email for a single pending check-in."""
    try:
        recap_text = await _build_recap_text(db, doc["user_id"])
        email_service.send_post_summary_checkin(
            to_email=doc["email"],
            user_name=doc.get("name") or "",
            recap_text=recap_text,
            journal_url=_journal_link(),
        )
        await db.post_summary_checkins.update_one(
            {"checkin_id": doc["checkin_id"]},
            {"$set": {"status": "sent", "sent_at": _iso(_now())}},
        )
        logger.info("Post-summary check-in sent → %s", doc["email"])
    except email_service.EmailNotConfigured:
        # Stop the sweep — no point retrying every doc when email is off.
        raise
    except Exception:  # noqa: BLE001
        logger.exception("Check-in send failed for %s", doc.get("email"))


async def _send_due(db: AsyncIOMotorDatabase) -> None:
    cursor = db.post_summary_checkins.find(
        {
            "status": "pending",
            "sent_at": None,
            "scheduled_send_at": {"$lte": _iso(_now())},
        },
        {"_id": 0},
    ).limit(50)
    async for doc in cursor:
        try:
            await _process_one(db, doc)
        except email_service.EmailNotConfigured:
            logger.warning("Resend not configured; skipping check-in sweep.")
            return


async def checkin_scheduler_loop(app) -> None:
    """Long-lived background task — sweeps the queue every 30 minutes."""
    await asyncio.sleep(90)  # small warmup so DB is ready
    while True:
        try:
            db = app.state.db
            await _send_due(db)
        except Exception:  # noqa: BLE001
            logger.exception("Check-in scheduler sweep failed; will retry.")
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
