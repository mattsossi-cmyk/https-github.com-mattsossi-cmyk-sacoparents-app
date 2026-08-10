"""Compare Invite Nudge Reminder — weekly friendly nudge to creators of
pending Compare Share invitations whose partner has not yet consented.

When parent A sends parent B a Compare Share request (via
`deep_dive_compare_router_factory.link_partner` or the SNC2 flow), the
share row lands in `awaiting_partner_consent`. If parent B never opens
the invite email — because it landed in spam, because they haven't
logged into the app in a while, or because the relationship stalled —
parent A has no visibility that they are waiting on the other side.

This module sweeps every share collection weekly and emails the CREATOR
a warm nudge when their request has been pending more than 7 days
without partner consent. Suppression rules:

  * Share status is not `awaiting_partner_consent` (already active,
    already revoked, or already declined) → skip
  * `partner_consent` is True (state machine already advanced but
    status might not have updated yet on some legacy rows) → skip
  * `created_at` is less than 7 days ago → not stale yet, skip
  * A nudge for this share_id has already been sent to this creator
    in the last 7 days (dedupe via `compare_invite_nudge_sends`) → skip
  * Creator has no real email on file, or looks like a demo/guest → skip

Runtime is gated behind `COMPARE_INVITE_NUDGE_ENABLED=1`. Sweep runs
hourly, only dispatches during Mon 08–22 UTC (same window as the
compliance reminder — parents don't need two Monday-morning emails).

Public surface:
  * `send_compare_invite_nudges(db, dry_run=False, now=None, force_window=False)`
    — pure coroutine that runs one sweep pass; returns per-share results.
  * `compare_invite_nudge_loop(app)` — long-running background task
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

# Every collection where a Compare-style share might land in
# `awaiting_partner_consent`. Adding a new share type in future is a
# one-liner in this tuple.
SHARE_COLLECTIONS = (
    "edu_deep_shares",
    "psych_deep_shares",
    "med_deep_shares",
    "snc2_shares",
)
SENDS_COLLECTION = "compare_invite_nudge_sends"

# Suppression thresholds.
_STALE_DAYS = int(os.environ.get("COMPARE_INVITE_NUDGE_STALE_DAYS", "7"))
_DEDUPE_DAYS = int(os.environ.get("COMPARE_INVITE_NUDGE_DEDUPE_DAYS", "7"))

# Sweep loop schedule.
_SWEEP_INTERVAL_S = int(os.environ.get("COMPARE_INVITE_NUDGE_SWEEP_SECONDS", "3600"))
_SEND_START_UTC_HOUR = int(os.environ.get("COMPARE_INVITE_NUDGE_START_HOUR_UTC", "8"))
_SEND_END_UTC_HOUR = int(os.environ.get("COMPARE_INVITE_NUDGE_END_HOUR_UTC", "22"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _in_send_window(now: datetime) -> bool:
    """Monday-only send window. Same policy as weekly compliance."""
    return (
        now.weekday() == 0
        and _SEND_START_UTC_HOUR <= now.hour < _SEND_END_UTC_HOUR
    )


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


async def _find_stale_pending_shares(
    db: AsyncIOMotorDatabase, cutoff_iso: str,
) -> List[Dict[str, Any]]:
    """Return every share across every share collection that is:
    * status == awaiting_partner_consent
    * partner_consent == False
    * created_at older than the cutoff
    Each row is annotated with `_collection` so the sender + dedupe
    hooks can carry the origin without a second lookup."""
    stale: List[Dict[str, Any]] = []
    for coll in SHARE_COLLECTIONS:
        cursor = db[coll].find(
            {
                "status":          "awaiting_partner_consent",
                "partner_consent": {"$ne": True},
                "created_at":      {"$lt": cutoff_iso},
            },
            {"_id": 0},
        )
        async for row in cursor:
            row["_collection"] = coll
            stale.append(row)
    return stale


async def _already_nudged_recently(
    db: AsyncIOMotorDatabase, share_id: str, cutoff_iso: str,
) -> bool:
    """True if we sent a nudge for this share within the dedupe window."""
    row = await db[SENDS_COLLECTION].find_one({
        "share_id":   share_id,
        "created_at": {"$gte": cutoff_iso},
    })
    return row is not None


async def _record_send(
    db: AsyncIOMotorDatabase,
    *,
    share_id: str,
    creator_user_id: str,
    to_email: str,
    dry_run: bool,
    reason: str,
) -> None:
    await db[SENDS_COLLECTION].insert_one({
        "share_id":        share_id,
        "creator_user_id": creator_user_id,
        "to_email":        to_email,
        "dry_run":         bool(dry_run),
        "reason":          reason,
        "created_at":      _now_utc().isoformat(),
    })


def _share_kind_label(collection: str) -> str:
    """Human-readable label used in the email copy."""
    return {
        "edu_deep_shares":   "Educational Deep-Dive",
        "psych_deep_shares": "Psychological Deep-Dive",
        "med_deep_shares":   "Medical Deep-Dive",
        "snc2_shares":       "SNC-2 Comparison",
    }.get(collection, "Compare Share")


async def _dispatch_one(
    db: AsyncIOMotorDatabase,
    share: Dict[str, Any],
    *,
    dry_run: bool,
    dedupe_cutoff_iso: str,
) -> Dict[str, Any]:
    """Send a nudge for a single stale share. Never raises — errors are
    captured in the per-row result dict."""
    share_id = share.get("share_id") or ""
    creator_id = share.get("creator_user_id") or ""
    creator_email = share.get("creator_email") or ""
    partner_email = share.get("partner_email") or ""

    base = {"share_id": share_id, "creator_user_id": creator_id, "sent": False}

    if not _looks_like_real_email(creator_email):
        return {**base, "reason": "creator_email_not_real"}
    if await _already_nudged_recently(db, share_id, dedupe_cutoff_iso):
        return {**base, "reason": "already_nudged_within_dedupe_window"}

    kind_label = _share_kind_label(share.get("_collection") or "")

    if dry_run:
        await _record_send(
            db,
            share_id=share_id, creator_user_id=creator_id,
            to_email=creator_email, dry_run=True,
            reason="dry_run",
        )
        return {**base, "sent": True, "dry_run": True,
                "to_email": creator_email, "kind": kind_label}

    try:
        from email_service import (
            EmailNotConfigured, EmailSendError, send_compare_invite_nudge,
        )
        send_compare_invite_nudge(
            to_email=creator_email,
            creator_name=share.get("creator_name") or "",
            partner_name=share.get("partner_name") or "",
            partner_email=partner_email or "",
            kind_label=kind_label,
            created_at_iso=share.get("created_at") or "",
        )
    except EmailNotConfigured:
        return {**base, "reason": "email_not_configured"}
    except EmailSendError as exc:
        return {**base, "reason": f"email_send_error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        log.exception("nudge send failed for share %s", share_id)
        return {**base, "reason": f"exception: {exc}"}

    await _record_send(
        db,
        share_id=share_id, creator_user_id=creator_id,
        to_email=creator_email, dry_run=False,
        reason="sent",
    )
    return {**base, "sent": True, "to_email": creator_email, "kind": kind_label}


async def send_compare_invite_nudges(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    force_window: bool = False,
) -> Dict[str, Any]:
    """Run one sweep pass. Same shape/contract as the weekly compliance
    sweep so operators can reuse the same preview endpoint pattern."""
    now = now or _now_utc()
    if not force_window and not _in_send_window(now):
        return {"skipped": "outside_send_window", "at": now.isoformat(), "results": []}

    stale_cutoff_iso = (now - timedelta(days=_STALE_DAYS)).isoformat()
    dedupe_cutoff_iso = (now - timedelta(days=_DEDUPE_DAYS)).isoformat()

    stale = await _find_stale_pending_shares(db, stale_cutoff_iso)
    results: List[Dict[str, Any]] = []
    for share in stale:
        try:
            results.append(await _dispatch_one(
                db, share,
                dry_run=dry_run,
                dedupe_cutoff_iso=dedupe_cutoff_iso,
            ))
        except Exception as exc:  # noqa: BLE001
            log.exception("nudge dispatch failed for share %s", share.get("share_id"))
            results.append({
                "share_id": share.get("share_id"),
                "sent": False,
                "reason": f"exception: {exc}",
            })
    return {
        "at":            now.isoformat(),
        "candidates":    len(stale),
        "results":       results,
        "sent_count":    sum(1 for r in results if r.get("sent")),
    }


# ---------------------------------------------------------------------------
# Background loop.
# ---------------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("COMPARE_INVITE_NUDGE_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


async def compare_invite_nudge_loop(app) -> None:
    """Long-running sweep task started from server.py. No-ops silently
    when the feature is not turned on via env var — safe to always
    register."""
    if not _enabled():
        log.info(
            "compare_invite_nudge_loop: COMPARE_INVITE_NUDGE_ENABLED not set; loop idle"
        )
        while True:
            await asyncio.sleep(3600)
    await asyncio.sleep(150)  # small warmup so DB is ready + offset from other loops
    while True:
        try:
            db = app.state.db
            await send_compare_invite_nudges(db)
        except Exception:  # noqa: BLE001
            log.exception("compare invite nudge sweep failed; will retry.")
        await asyncio.sleep(_SWEEP_INTERVAL_S)
