"""Self-Assessment reassess reminders — 6-week email + 8-week gentle follow-up.

Safety-first: parents with a Grey-Rock / DV flag (portal_state.safety_ack.flagged)
or a latest IPV screen at Level 1–2 never receive these emails; they only see
the in-app "Time to reassess" note. Every email has a plain subject line and
a one-tap unsubscribe link.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import JWT_ALGO, JWT_SECRET
from safety_gate import BLOCKED_LEVEL_CEILING, _latest_safety_level

logger = logging.getLogger(__name__)

FIRST_AFTER_DAYS = 42
FOLLOW_UP_AFTER_DAYS = 56
MIN_GAP_DAYS = 10
UNSUB_KIND = "sa_reminder_unsub"


def make_unsubscribe_token(user_id: str) -> str:
    return jwt.encode({"kind": UNSUB_KIND, "sub": user_id}, JWT_SECRET, algorithm=JWT_ALGO)


def read_unsubscribe_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"require": ["kind", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload["sub"] if payload.get("kind") == UNSUB_KIND else None


async def is_safety_flagged(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    ps = await db.portal_state.find_one({"user_id": user_id}, {"_id": 0, "safety_ack": 1})
    if ((ps or {}).get("safety_ack") or {}).get("flagged"):
        return True
    level = await _latest_safety_level(db, user_id)
    return level is not None and level <= BLOCKED_LEVEL_CEILING


def _due_kind(completed_at: datetime, sent: Dict[str, datetime], now: datetime) -> Optional[str]:
    age = now - completed_at
    if "6w" not in sent:
        return "6w" if age >= timedelta(days=FIRST_AFTER_DAYS) else None
    if "8w" not in sent and age >= timedelta(days=FOLLOW_UP_AFTER_DAYS):
        return "8w" if now - sent["6w"] >= timedelta(days=MIN_GAP_DAYS) else None
    return None


def _links(user_id: str) -> Dict[str, str]:
    app = (os.environ.get("PUBLIC_APP_URL") or "https://sacoparentsapp.online").rstrip("/")
    api = (os.environ.get("PUBLIC_BACKEND_URL") or app).rstrip("/")
    return {
        "cta": f"{app}/dashboard?open=self-assessment",
        "unsubscribe": f"{api}/api/self-assessment/reminders/unsubscribe?token={make_unsubscribe_token(user_id)}",
    }


async def send_reassess_reminders(db: AsyncIOMotorDatabase, *, now: Optional[datetime] = None) -> Dict[str, int]:
    from email_service import EmailNotConfigured, EmailSendError, send_reassess_reminder

    now = now or datetime.now(timezone.utc)
    stats = {"checked": 0, "sent": 0, "failed": 0, "skipped_safety": 0, "skipped_unsubscribed": 0,
             "skipped_no_email": 0, "not_due": 0}
    latest_per_user = db.self_assessment_history.aggregate([
        {"$sort": {"completed_at": -1}},
        {"$group": {"_id": "$user_id", "entry_id": {"$first": "$id"}, "completed_at": {"$first": "$completed_at"}}},
    ])
    async for row in latest_per_user:
        stats["checked"] += 1
        user_id, entry_id = row["_id"], row["entry_id"]
        completed = datetime.fromisoformat(row["completed_at"])
        sent = {
            r["kind"]: datetime.fromisoformat(r["sent_at"])
            async for r in db.self_assessment_reminders.find(
                {"user_id": user_id, "entry_id": entry_id, "status": "sent"}, {"_id": 0}
            )
        }
        kind = _due_kind(completed, sent, now)
        if not kind:
            stats["not_due"] += 1
            continue
        if await db.self_assessment_reminder_prefs.find_one({"user_id": user_id, "unsubscribed": True}):
            stats["skipped_unsubscribed"] += 1
            continue
        if await is_safety_flagged(db, user_id):
            stats["skipped_safety"] += 1
            continue
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1, "name": 1, "is_guest": 1,
                                                                "email_bounced": 1, "email_complained": 1})
        if not user or not user.get("email") or user.get("is_guest") or user.get("email_bounced") \
                or user.get("email_complained"):
            stats["skipped_no_email"] += 1
            continue
        links = _links(user_id)
        status = "sent"
        try:
            send_reassess_reminder(
                to_email=user["email"],
                first_name=(user.get("name") or "").split(" ")[0] or None,
                follow_up=(kind == "8w"),
                cta_url=links["cta"],
                unsubscribe_url=links["unsubscribe"],
            )
            stats["sent"] += 1
        except (EmailNotConfigured, EmailSendError) as exc:
            status = "failed"
            stats["failed"] += 1
            logger.warning("reassess reminder %s failed for %s: %s", kind, user_id, exc)
        await db.self_assessment_reminders.update_one(
            {"user_id": user_id, "entry_id": entry_id, "kind": kind},
            {"$set": {"status": status, "sent_at": now.isoformat()}},
            upsert=True,
        )
    return stats
