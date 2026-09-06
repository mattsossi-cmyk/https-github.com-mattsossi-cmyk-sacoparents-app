"""Joint Alignment Invitation Reminder — nudges parents whose Joint
Alignment Case invitation is still unaccepted 5+ days after the
mediator minted the case.

The professional flow (see `joint_alignment_routes.py`
`professional_create_case`) sends the initial invitation email
immediately. If a parent misses that email — spam folder, quiet
inbox — the mediator has no way to know without checking the
`/professional/joint-alignment/mine` console. This module runs an
hourly sweep and, for each case parent that:

  * has NOT accepted their invitation yet (`accepted_at` is null)
  * whose invitation was minted 5+ days ago
  * whose invitation token has NOT yet expired (7-day TTL —
    still 1-2 days of usable life)
  * has NOT already received a reminder for THIS case (dedupe row
    in `joint_alignment_invite_nudge_sends`)
  * has a real-looking email (no @demo.local / @guest.local)

...emails the parent a warm nudge with the same invitation URL and
the professional's name. Suppression rules match the compare
invite nudge module so operators can reuse the same runbook.

Runtime is gated behind `JOINT_ALIGN_INVITE_NUDGE_ENABLED=1`.
No-ops silently when the env var is not set (safe to always
register from `server.py`).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

_CASES_COLLECTION = "joint_alignment_cases"
_SENDS_COLLECTION = "joint_alignment_invite_nudge_sends"

# Only in-app-professional cases participate — server-to-server
# cases from the sibling site handle their own reminders on that
# side; we don't want two apps double-nudging the same parent.
_ORIGIN_IN_APP = "in_app_professional"

# Nudge if the invitation is at least this many days old and the
# parent hasn't accepted yet.
_STALE_DAYS = int(os.environ.get("JOINT_ALIGN_INVITE_NUDGE_STALE_DAYS", "5"))
# Never dedupe within this many days — one reminder per case
# per parent (case TTL is 60 days so this is functionally
# "one reminder ever").
_DEDUPE_DAYS = int(os.environ.get("JOINT_ALIGN_INVITE_NUDGE_DEDUPE_DAYS", "60"))

# Sweep loop cadence + send window (UTC, 08–22, any weekday).
# Not restricted to Mondays because mediation timelines are shorter
# than compliance timelines — a stale invite on Tuesday morning
# should nudge Tuesday morning, not wait a week.
_SWEEP_INTERVAL_S = int(os.environ.get("JOINT_ALIGN_INVITE_NUDGE_SWEEP_SECONDS", "3600"))
_SEND_START_UTC_HOUR = int(os.environ.get("JOINT_ALIGN_INVITE_NUDGE_START_HOUR_UTC", "8"))
_SEND_END_UTC_HOUR = int(os.environ.get("JOINT_ALIGN_INVITE_NUDGE_END_HOUR_UTC", "22"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _in_send_window(now: datetime) -> bool:
    return _SEND_START_UTC_HOUR <= now.hour < _SEND_END_UTC_HOUR


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


def _join_base() -> str:
    """Public origin used to render invitation URLs — mirrors the
    logic in joint_alignment_routes so both codepaths land on the
    same URL for a given token."""
    base = (os.environ.get("PUBLIC_APP_ORIGIN") or "").rstrip("/")
    if not base:
        base = "https://sacoparentsapp.online"
    return f"{base}/join"


async def _find_stale_pending_parents(
    db: AsyncIOMotorDatabase, now: datetime,
) -> List[Dict[str, Any]]:
    """Return one entry per (case, parent) that is currently stale.
    Each row has enough context to render + dedupe + send an
    invitation-reminder email in one pass — no second lookup.
    """
    stale_before = now - timedelta(days=_STALE_DAYS)
    cursor = db[_CASES_COLLECTION].find(
        {
            "origin": _ORIGIN_IN_APP,
            "status": {"$in": ["pending", "in_progress"]},
            "created_at": {"$lt": stale_before},
        },
        {"_id": 0},
    )
    out: List[Dict[str, Any]] = []
    async for case in cursor:
        case_id = case.get("case_id") or ""
        professional_name = ((case.get("professional") or {}).get("name")) or ""
        parents = case.get("parents") or []
        for p in parents:
            if p.get("accepted_at"):
                continue
            token_exp = p.get("token_expires_at")
            if token_exp is not None:
                # MongoDB returns naive datetimes; normalise both sides
                # to UTC-aware so the compare doesn't raise.
                if getattr(token_exp, "tzinfo", None) is None:
                    token_exp = token_exp.replace(tzinfo=timezone.utc)
                if token_exp < now:
                    # Token already expired — the mediator has to remint
                    # anyway; a nudge with a dead link would confuse.
                    continue
            out.append({
                "case_id": case_id,
                "professional_name": professional_name,
                "parent_email": p.get("email") or "",
                "parent_name": p.get("name") or "",
                "invitation_token": p.get("invitation_token") or "",
                "token_expires_at": token_exp,
                "assessment_type": case.get("assessment_type") or "",
                "created_at": case.get("created_at"),
            })
    return out


async def _already_nudged_recently(
    db: AsyncIOMotorDatabase,
    *,
    case_id: str,
    parent_email: str,
    cutoff: datetime,
) -> bool:
    row = await db[_SENDS_COLLECTION].find_one({
        "case_id": case_id,
        "parent_email": parent_email,
        "created_at": {"$gte": cutoff},
    })
    return row is not None


async def _record_send(
    db: AsyncIOMotorDatabase,
    *,
    case_id: str,
    parent_email: str,
    dry_run: bool,
    reason: str,
) -> None:
    await db[_SENDS_COLLECTION].insert_one({
        "case_id": case_id,
        "parent_email": parent_email,
        "dry_run": bool(dry_run),
        "reason": reason,
        "created_at": _now_utc(),
    })


async def _dispatch_one(
    db: AsyncIOMotorDatabase,
    row: Dict[str, Any],
    *,
    dry_run: bool,
    dedupe_cutoff: datetime,
) -> Dict[str, Any]:
    """Send a reminder for a single stale (case, parent). Never
    raises — errors are captured in the result dict so the sweep
    can continue after a single bad row.
    """
    case_id = row["case_id"]
    parent_email = row["parent_email"]
    base = {"case_id": case_id, "parent_email": parent_email, "sent": False}

    if not _looks_like_real_email(parent_email):
        return {**base, "reason": "parent_email_not_real"}
    if not row.get("invitation_token"):
        return {**base, "reason": "no_invitation_token"}
    if await _already_nudged_recently(
        db, case_id=case_id, parent_email=parent_email, cutoff=dedupe_cutoff,
    ):
        return {**base, "reason": "already_nudged_within_dedupe_window"}

    invitation_url = f"{_join_base()}/{row['invitation_token']}"

    if dry_run:
        await _record_send(
            db,
            case_id=case_id, parent_email=parent_email,
            dry_run=True, reason="dry_run",
        )
        return {
            **base, "sent": True, "dry_run": True,
            "invitation_url": invitation_url,
        }

    try:
        from email_service import (
            EmailNotConfigured, EmailSendError,
            send_joint_alignment_invitation_reminder,
        )
        send_joint_alignment_invitation_reminder(
            to_email=parent_email,
            invitation_url=invitation_url,
            case_id=case_id,
            professional_name=row.get("professional_name") or None,
            parent_name=row.get("parent_name") or None,
            assessment_type=row.get("assessment_type") or None,
        )
    except EmailNotConfigured:
        return {**base, "reason": "email_not_configured"}
    except EmailSendError as exc:
        return {**base, "reason": f"email_send_error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        log.exception("joint-alignment reminder failed for %s", case_id)
        return {**base, "reason": f"exception: {exc}"}

    await _record_send(
        db,
        case_id=case_id, parent_email=parent_email,
        dry_run=False, reason="sent",
    )
    return {**base, "sent": True, "invitation_url": invitation_url}


async def send_joint_alignment_invitation_reminders(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    force_window: bool = False,
) -> Dict[str, Any]:
    """Run one sweep pass. Same shape/contract as the compare
    invite nudge sweep so operators can reuse the same preview
    endpoint pattern."""
    now = now or _now_utc()
    if not force_window and not _in_send_window(now):
        return {"skipped": "outside_send_window", "at": now.isoformat(), "results": []}

    dedupe_cutoff = now - timedelta(days=_DEDUPE_DAYS)

    stale = await _find_stale_pending_parents(db, now)
    results: List[Dict[str, Any]] = []
    for row in stale:
        try:
            results.append(await _dispatch_one(
                db, row,
                dry_run=dry_run,
                dedupe_cutoff=dedupe_cutoff,
            ))
        except Exception as exc:  # noqa: BLE001
            log.exception(
                "joint-alignment nudge dispatch failed for %s",
                row.get("case_id"),
            )
            results.append({
                "case_id": row.get("case_id"),
                "parent_email": row.get("parent_email"),
                "sent": False,
                "reason": f"exception: {exc}",
            })
    return {
        "at": now.isoformat(),
        "candidates": len(stale),
        "results": results,
        "sent_count": sum(1 for r in results if r.get("sent")),
    }


# ---------------------------------------------------------------------------
# Background loop.
# ---------------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("JOINT_ALIGN_INVITE_NUDGE_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


async def joint_alignment_invite_nudge_loop(app) -> None:
    """Long-running sweep started from server.py. Idle no-op when
    the env flag is not set — safe to always register."""
    if not _enabled():
        log.info(
            "joint_alignment_invite_nudge_loop: JOINT_ALIGN_INVITE_NUDGE_ENABLED "
            "not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    # Small offset from other sweep loops so a startup burst doesn't
    # hammer the DB on all reminders at once.
    await asyncio.sleep(200)
    while True:
        try:
            db = app.state.db
            await send_joint_alignment_invitation_reminders(db)
        except Exception:  # noqa: BLE001
            log.exception("joint-alignment invite nudge sweep failed; will retry.")
        await asyncio.sleep(_SWEEP_INTERVAL_S)
