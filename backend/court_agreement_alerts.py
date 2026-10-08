"""Email the co-parent when an area is marked agreed or a "What we agreed" note is added.

At most one email per parent every 6 hours. Changes inside the window are queued and bundled into the next
email: sent with the next change after the window, or by the daily cron sweep (flush_all). Only sent while the
comparison is still active (both sharing, neither parent safety-flagged).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from court_agreements import INTENT_NOTICE
from email_service import send_agreement_update_alert

logger = logging.getLogger(__name__)
QUEUE = "court_agreement_alerts"
WINDOW = timedelta(hours=6)


async def queue_alert(db: AsyncIOMotorDatabase, actor: str, area_key: str, kind: str, note: str = "") -> None:
    from court_compare import _resolve  # local import: court_compare imports this module

    _base, key, other = await _resolve(db, actor)
    if not other:
        return
    area = area_key.split("|", 1)[-1]
    entry = {"area": area, "kind": kind, "note": note, "at": datetime.now(timezone.utc).isoformat()}
    await db[QUEUE].update_one({"user_id": other}, {"$pull": {"pending": {"area": area, "kind": kind}}}, upsert=True)
    await db[QUEUE].update_one({"user_id": other}, {"$push": {"pending": entry}, "$set": {"court_key": key}})
    await flush_one(db, other)


async def flush_one(db: AsyncIOMotorDatabase, uid: str) -> bool:
    from court_compare import _resolve

    doc = await db[QUEUE].find_one({"user_id": uid}, {"_id": 0})
    pending = (doc or {}).get("pending") or []
    if not pending:
        return False
    now = datetime.now(timezone.utc)
    last = doc.get("last_sent_at")
    if last and datetime.fromisoformat(last) > now - WINDOW:
        return False
    _base, key, other = await _resolve(db, uid)
    if not other or key != doc.get("court_key"):
        await db[QUEUE].update_one({"user_id": uid}, {"$set": {"pending": []}})
        return False
    user = await db.users.find_one({"user_id": uid}, {"_id": 0, "email": 1, "name": 1})
    if not (user and user.get("email")):
        return False
    link = os.environ["PUBLIC_APP_URL"].rstrip("/") + "/dashboard"
    try:
        await asyncio.to_thread(
            send_agreement_update_alert, to_email=user["email"], user_name=user.get("name"), link_url=link,
            items=pending, notice=INTENT_NOTICE,
        )
    except Exception as exc:  # noqa: BLE001 — an email failure must never break agreements
        logger.warning("agreement alert email failed for %s: %s", uid, exc)
        await db[QUEUE].update_one({"user_id": uid}, {"$set": {"last_error": str(exc)[:200]}})
        return False
    sent = [p["at"] for p in pending]
    await db[QUEUE].update_one(
        {"user_id": uid},
        {"$pull": {"pending": {"at": {"$in": sent}}}, "$set": {"last_sent_at": now.isoformat()}, "$unset": {"last_error": ""}},
    )
    return True


async def flush_all(db: AsyncIOMotorDatabase) -> int:
    sent = 0
    async for doc in db[QUEUE].find({"pending.0": {"$exists": True}}, {"_id": 0, "user_id": 1}):
        sent += await flush_one(db, doc["user_id"])
    return sent
