"""Monday 9am Central: neutral reminder to parents with requested-but-unfinished Court-page assessments.

The email never names an assessment ("You have 2 assessments waiting for you"). Skipped for safety-flagged
parents, unsubscribed parents, guests and bounced/complained addresses. One email per parent per ISO week.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import JWT_ALGO, JWT_SECRET
from court_checklist import assessment_statuses
from self_assessment_reminders import is_safety_flagged

logger = logging.getLogger(__name__)

UNSUB_KIND = "court_reminder_unsub"


def make_unsubscribe_token(user_id: str) -> str:
    return jwt.encode({"kind": UNSUB_KIND, "sub": user_id}, JWT_SECRET, algorithm=JWT_ALGO)


def read_unsubscribe_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"require": ["kind", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload["sub"] if payload.get("kind") == UNSUB_KIND else None


def _links(user_id: str) -> Dict[str, str]:
    app = (os.environ.get("PUBLIC_APP_URL") or "https://sacoparentsapp.online").rstrip("/")
    api = (os.environ.get("PUBLIC_BACKEND_URL") or app).rstrip("/")
    return {
        "cta": f"{app}/login",
        "unsubscribe": f"{api}/api/court-path/reminders/unsubscribe?token={make_unsubscribe_token(user_id)}",
    }


async def _sync_professional_ticks(db: AsyncIOMotorDatabase) -> None:
    """Apply professional requests (joint cases + court codes) for parents who haven't opened their Court page since."""
    from court_checklist import _sync_professional_requests

    uids = set()
    async for case in db.joint_alignment_cases.find({"status": {"$ne": "cancelled"}, "parents.user_id": {"$exists": True}}, {"_id": 0, "parents.user_id": 1}):
        uids.update(p["user_id"] for p in case.get("parents") or [] if p.get("user_id"))
    codes = await db.portal_court_keys.distinct("case_id", {"requested.0": {"$exists": True}, "revoked_at": None})
    if codes:
        uids.update(await db.portal_state.distinct("user_id", {"court_key": {"$in": codes}}))
    for uid in uids:
        await _sync_professional_requests(db, uid)


async def send_requested_reminders(db: AsyncIOMotorDatabase, *, now: Optional[datetime] = None) -> Dict[str, int]:
    from email_service import EmailNotConfigured, EmailSendError, send_requested_reminder

    await _sync_professional_ticks(db)
    now = now or datetime.now(timezone.utc)
    year, wk, _ = now.isocalendar()
    week = f"{year}-W{wk:02d}"
    stats = {"checked": 0, "sent": 0, "failed": 0, "all_done": 0, "already_sent": 0, "skipped_safety": 0,
             "skipped_unsubscribed": 0, "skipped_no_email": 0}
    async for doc in db.court_requested.find({"keys.0": {"$exists": True}}, {"_id": 0, "user_id": 1, "keys": 1, "reminders_off": 1}):
        stats["checked"] += 1
        uid = doc["user_id"]
        if doc.get("reminders_off"):
            stats["skipped_unsubscribed"] += 1
            continue
        if await db.requested_reminder_sends.find_one({"user_id": uid, "week": week, "status": "sent"}, {"_id": 1}):
            stats["already_sent"] += 1
            continue
        st = await assessment_statuses(db, uid)
        waiting = sum(1 for k in doc["keys"] if k in st and st[k]["status"] != "done")
        if not waiting:
            stats["all_done"] += 1
            continue
        if await is_safety_flagged(db, uid):
            stats["skipped_safety"] += 1
            continue
        user = await db.users.find_one({"user_id": uid}, {"_id": 0, "email": 1, "name": 1, "is_guest": 1,
                                                          "email_bounced": 1, "email_complained": 1})
        if not user or not user.get("email") or user.get("is_guest") or user.get("email_bounced") or user.get("email_complained"):
            stats["skipped_no_email"] += 1
            continue
        links = _links(uid)
        status = "sent"
        try:
            send_requested_reminder(
                to_email=user["email"],
                first_name=(user.get("name") or "").split(" ")[0] or None,
                waiting=waiting,
                cta_url=links["cta"],
                unsubscribe_url=links["unsubscribe"],
            )
            stats["sent"] += 1
        except (EmailNotConfigured, EmailSendError) as exc:
            status = "failed"
            stats["failed"] += 1
            logger.warning("requested reminder failed for %s: %s", uid, exc)
        await db.requested_reminder_sends.update_one(
            {"user_id": uid, "week": week},
            {"$set": {"status": status, "waiting": waiting, "sent_at": now.isoformat()}},
            upsert=True,
        )
    return stats
