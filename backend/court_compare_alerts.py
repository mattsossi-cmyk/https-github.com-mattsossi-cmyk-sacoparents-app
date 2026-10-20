"""Sharing alert emails for the Court page comparison (max once a week per type, never to safety-flagged parents)."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from email_service import send_compare_ready_alert, send_compare_share_alert
from held_emails import record_held, week_key
from self_assessment_reminders import is_safety_flagged

logger = logging.getLogger(__name__)
ALERTS = "court_compare_alerts"
WEEK = timedelta(days=7)


async def _alert(db: AsyncIOMotorDatabase, uid: str, field: str, send) -> None:
    now = datetime.now(timezone.utc)
    if await is_safety_flagged(db, uid):
        await record_held(db, "compare_alert", uid, f"{field}:{week_key(now)}")
        return
    last = ((await db[ALERTS].find_one({"user_id": uid}, {"_id": 0, field: 1})) or {}).get(field)
    if last and datetime.fromisoformat(last) > now - WEEK:
        return
    user = await db.users.find_one({"user_id": uid}, {"_id": 0, "email": 1, "name": 1})
    if not (user and user.get("email")):
        return
    link = os.environ["PUBLIC_APP_URL"].rstrip("/") + "/dashboard"
    try:
        await asyncio.to_thread(send, to_email=user["email"], user_name=user.get("name"), link_url=link)
    except Exception as exc:  # noqa: BLE001 — an email failure must never break sharing
        logger.warning("court compare %s email failed for %s: %s", field, uid, exc)
        await db[ALERTS].update_one({"user_id": uid}, {"$set": {f"{field}_error": str(exc)[:200]}}, upsert=True)
        return
    await db[ALERTS].update_one({"user_id": uid}, {"$set": {field: now.isoformat()}, "$unset": {f"{field}_error": ""}}, upsert=True)


async def notify_share(db: AsyncIOMotorDatabase, uid: str, other: str, both_sharing: bool) -> None:
    """Co-parent hasn't shared yet -> tell them; both sharing -> tell both it's ready."""
    if both_sharing:
        for person in (uid, other):
            await _alert(db, person, "ready_sent_at", send_compare_ready_alert)
    else:
        await _alert(db, other, "invite_sent_at", send_compare_share_alert)
