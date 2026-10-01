"""Iter237 · Progress-share analytics — did the mediator open it?

Lightweight open-tracking for the one-page Progress Snapshot a
parent emails to a mediator. Scope is intentionally minimal:

  * `record_share(...)` persists a `progress_shares` doc per send
    (`share_id`, parent `user_id`, mediator email + optional name,
    `sent_at`, `opened_at=None`, `open_count=0`).
  * `record_open(share_id)` is called by a 1x1 pixel endpoint when
    the mediator opens the email. First open stamps `opened_at`;
    subsequent opens just bump `open_count`. No IP addresses, no
    user-agents stored — the parent only needs the fact "they saw
    it", not forensic detail.
  * `recent_shares_for(user_id)` returns the N most recent shares
    with open status for the Progress Tile "Share history" strip.

No PHI, no clinical data — just the metadata of a parent-initiated
hand-off to their chosen professional.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


COLLECTION = "progress_shares"
RECENT_LIMIT = 6


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mint_share_id() -> str:
    """8-hex-char token wrapped with a readable prefix. The share_id
    is embedded verbatim in the tracking-pixel URL so a short token
    keeps the URL compact in email clients that render the raw src."""
    return "sh_" + secrets.token_hex(6)


async def record_share(
    db: AsyncIOMotorDatabase,
    *,
    share_id: str,
    user_id: str,
    parent_name: Optional[str],
    to_email: str,
    mediator_name: Optional[str],
) -> None:
    await db[COLLECTION].insert_one({
        "share_id":      share_id,
        "user_id":       user_id,
        "parent_name":   (parent_name or "").strip() or None,
        "to_email":      (to_email or "").strip().lower(),
        "mediator_name": (mediator_name or "").strip() or None,
        "sent_at":       _now_iso(),
        "opened_at":     None,
        "open_count":    0,
    })


async def record_open(
    db: AsyncIOMotorDatabase,
    *,
    share_id: str,
) -> None:
    """Idempotent open-tracking.

    * First open: stamp `opened_at` and set `open_count=1`.
    * Subsequent opens: `$inc` `open_count` + stamp `last_opened_at`.
    * Unknown share_id: no-op (we don't want a mangled pixel URL to
      produce a 500).
    """
    now = _now_iso()
    doc = await db[COLLECTION].find_one({"share_id": share_id}, {"_id": 1, "opened_at": 1})
    if not doc:
        return
    if doc.get("opened_at"):
        await db[COLLECTION].update_one(
            {"_id": doc["_id"]},
            {"$inc": {"open_count": 1}, "$set": {"last_opened_at": now}},
        )
    else:
        await db[COLLECTION].update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "opened_at": now,
                    "last_opened_at": now,
                },
                "$inc": {"open_count": 1},
            },
        )


async def recent_shares_for(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    limit: int = RECENT_LIMIT,
) -> List[Dict[str, Any]]:
    cursor = (
        db[COLLECTION]
        .find({"user_id": user_id}, {"_id": 0, "user_id": 0})
        .sort("sent_at", -1)
        .limit(limit)
    )
    return [row async for row in cursor]
