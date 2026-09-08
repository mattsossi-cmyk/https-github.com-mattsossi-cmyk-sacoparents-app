"""Access-Expiring Sweep.

Two responsibilities:
  1. **Warning email** — fired ONCE when a live parent-share
     invitation is exactly 7 days out from `access_expiration`. Gives
     the parent a chance to Extend before the professional loses
     portal access silently.
  2. **Auto-expire** — on every sweep, flip any
     `access_expiration < now` invitation with
     `status != "access_expired"` and `revoked_at is None` over to
     `status = "access_expired"`. All linked
     `professional_report_permissions` rows are timestamped and their
     `status` set to `expired` in the same pass. Permission-check
     endpoint (`GET /integrations/report-permissions/{id}`) already
     surfaces this state — this sweep just keeps the invite doc
     honest so the parent's console reads correctly.

Idle no-op unless `ACCESS_EXPIRING_SWEEP_ENABLED=1`. Runs hourly.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

_INVITES_COLL = "parent_professional_invitations"
_PERMS_COLL = "professional_report_permissions"
_WARN_SENDS_COLL = "access_expiring_warning_sends"

_SWEEP_INTERVAL_S = int(os.environ.get("ACCESS_EXPIRING_SWEEP_SECONDS", "3600"))
_WARNING_DAYS = int(os.environ.get("ACCESS_EXPIRING_WARNING_DAYS", "7"))
# Warning-window band width in hours. Sweeps run hourly, so a 24h
# band means a single row is caught by ONE sweep on the day it
# crosses the "7 days out" threshold, then de-duped by the sends
# collection.
_WARNING_WINDOW_HOURS = int(os.environ.get("ACCESS_EXPIRING_WARN_WINDOW_HOURS", "24"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------
# Auto-expire.
# ---------------------------------------------------------------------

async def flip_expired_invitations(
    db: AsyncIOMotorDatabase, *, now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Flip every invite whose access_expiration has passed to
    `status="access_expired"`. Idempotent — only touches rows
    that aren't already flipped or revoked."""
    now = now or _now_utc()
    q = {
        "revoked_at": None,
        "access_expiration": {"$lt": now},
        "status": {"$ne": "access_expired"},
    }
    result = await db[_INVITES_COLL].update_many(
        q, {"$set": {"status": "access_expired", "auto_expired_at": now}},
    )
    perm_result = await db[_PERMS_COLL].update_many(
        {"expires_at": {"$lt": now}, "revoked_at": None, "status": {"$ne": "expired"}},
        {"$set": {"status": "expired"}},
    )
    return {
        "invitations_flipped": result.modified_count,
        "permissions_flipped": perm_result.modified_count,
        "at": now.isoformat(),
    }


# ---------------------------------------------------------------------
# 7-day warning email.
# ---------------------------------------------------------------------

async def _iter_warning_candidates(
    db: AsyncIOMotorDatabase, *, now: datetime,
) -> List[Dict[str, Any]]:
    """Invites whose access_expiration is `_WARNING_DAYS` days away
    (± `_WARNING_WINDOW_HOURS` hours), not revoked, not already
    warned. Returns raw invite docs so the caller can extract
    everything needed for the email."""
    lower = now + timedelta(days=_WARNING_DAYS) - timedelta(hours=_WARNING_WINDOW_HOURS)
    upper = now + timedelta(days=_WARNING_DAYS) + timedelta(hours=_WARNING_WINDOW_HOURS)
    cursor = db[_INVITES_COLL].find({
        "revoked_at": None,
        "status": {"$nin": ["access_expired", "declined"]},
        "access_expiration": {"$gte": lower, "$lte": upper},
    })
    out: List[Dict[str, Any]] = []
    async for row in cursor:
        out.append(row)
    return out


async def _already_warned(
    db: AsyncIOMotorDatabase, *, invitation_id: str,
) -> bool:
    return await db[_WARN_SENDS_COLL].find_one(
        {"invitation_id": invitation_id}, {"_id": 1},
    ) is not None


async def _record_warning(
    db: AsyncIOMotorDatabase, *,
    invitation_id: str, parent_id: str, sent_at: datetime,
    dry_run: bool, reason: str,
) -> None:
    await db[_WARN_SENDS_COLL].insert_one({
        "invitation_id": invitation_id,
        "parent_id": parent_id,
        "sent_at": sent_at,
        "dry_run": dry_run,
        "reason": reason,
    })


async def _send_warning_for(
    db: AsyncIOMotorDatabase, *, invite: Dict[str, Any],
    now: datetime, dry_run: bool,
) -> Dict[str, Any]:
    invitation_id = invite.get("invitation_id")
    parent_id = invite.get("inviting_parent_id")
    base = {"invitation_id": invitation_id, "sent": False}
    if not invitation_id or not parent_id:
        return {**base, "reason": "malformed_invite"}
    if await _already_warned(db, invitation_id=invitation_id):
        return {**base, "reason": "already_warned"}
    parent_email = invite.get("inviting_parent_email")
    if not parent_email or "@" not in parent_email:
        return {**base, "reason": "no_parent_email"}

    if dry_run:
        await _record_warning(
            db, invitation_id=invitation_id, parent_id=parent_id,
            sent_at=now, dry_run=True, reason="dry_run",
        )
        return {**base, "sent": True, "dry_run": True}

    try:
        from email_service import (
            EmailNotConfigured, EmailSendError,
            send_parent_share_access_expiring_email,
        )
        send_parent_share_access_expiring_email(
            to_email=parent_email,
            parent_name=invite.get("inviting_parent_name"),
            professional_name=(
                f"{invite.get('professional_first_name') or ''} "
                f"{invite.get('professional_last_name') or ''}".strip()
                or "the professional"
            ),
            professional_email=invite.get("professional_email"),
            report_titles=[
                r.get("title") for r in (invite.get("selected_reports") or [])
                if r.get("title")
            ],
            access_expires_at=invite.get("access_expiration"),
        )
    except EmailNotConfigured:
        return {**base, "reason": "email_not_configured"}
    except EmailSendError as exc:
        return {**base, "reason": f"email_send_error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        log.exception("access-expiring email failed for invite %s", invitation_id)
        return {**base, "reason": f"exception: {exc}"}

    await _record_warning(
        db, invitation_id=invitation_id, parent_id=parent_id,
        sent_at=now, dry_run=False, reason="sent",
    )
    return {**base, "sent": True}


async def send_access_expiring_warnings(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or _now_utc()
    candidates = await _iter_warning_candidates(db, now=now)
    results: List[Dict[str, Any]] = []
    for invite in candidates:
        results.append(await _send_warning_for(
            db, invite=invite, now=now, dry_run=dry_run,
        ))
    return {
        "at": now.isoformat(),
        "candidates": len(candidates),
        "results": results,
        "sent_count": sum(1 for r in results if r.get("sent") and not r.get("dry_run")),
    }


# ---------------------------------------------------------------------
# Public sweep entrypoint.
# ---------------------------------------------------------------------

async def run_access_expiring_sweep(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or _now_utc()
    warning_pass = await send_access_expiring_warnings(db, dry_run=dry_run, now=now)
    flip_pass = await flip_expired_invitations(db, now=now)
    return {
        "at": now.isoformat(),
        "warnings": warning_pass,
        "flips": flip_pass,
    }


# ---------------------------------------------------------------------
# Background loop.
# ---------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("ACCESS_EXPIRING_SWEEP_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


async def access_expiring_sweep_loop(app) -> None:
    if not _enabled():
        log.info(
            "access_expiring_sweep_loop: ACCESS_EXPIRING_SWEEP_ENABLED "
            "not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    await asyncio.sleep(240)  # spread startup load
    while True:
        try:
            db = app.state.db
            await run_access_expiring_sweep(db)
        except Exception:  # noqa: BLE001
            log.exception("access-expiring sweep failed; will retry.")
        await asyncio.sleep(_SWEEP_INTERVAL_S)
