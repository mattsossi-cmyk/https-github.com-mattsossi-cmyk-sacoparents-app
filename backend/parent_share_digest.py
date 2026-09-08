"""Daily parent share-notification digest.

Parents with ≥3 active invitations (or explicit opt-in via
`digest_notification_prefs.mode = "digest"`) get a rolled-up
"who viewed what today" email instead of individual view / download
pings. Fires once per parent per calendar day (UTC).

- Idle no-op unless `PARENT_SHARE_DIGEST_ENABLED=1`.
- Send-window: any hour by default; override with
  `PARENT_SHARE_DIGEST_START_HOUR` / `_END_HOUR` (24-hour, local tz
  `PARENT_SHARE_DIGEST_TZ` — defaults to America/Chicago so the
  digest lands early morning for South African users too since their
  events roll in during our afternoon).
- Dedupe: `parent_share_digest_sends` keyed on `(parent_id,
  digest_day)`.
- Bookkeeping: parent's PER-EVENT notification emails are suppressed
  for a given day IF the parent is in `digest` mode. Suppression
  happens at the event handler in
  `parent_professional_invitations.record_access_event` (see helper
  `is_parent_in_digest_mode`).

Never surfaces raw report content in the email.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

_INVITES_COLL = "parent_professional_invitations"
_EVENTS_COLL = "report_access_events"
_PREFS_COLL = "digest_notification_prefs"
_SENDS_COLL = "parent_share_digest_sends"

_MIN_ACTIVE_INVITATIONS_FOR_AUTO_DIGEST = 3
_SWEEP_INTERVAL_S = int(
    os.environ.get("PARENT_SHARE_DIGEST_SWEEP_SECONDS", "1800"),
)
_START_HOUR = int(os.environ.get("PARENT_SHARE_DIGEST_START_HOUR", "7"))
_END_HOUR = int(os.environ.get("PARENT_SHARE_DIGEST_END_HOUR", "10"))
_TZ_NAME = os.environ.get("PARENT_SHARE_DIGEST_TZ") or "America/Chicago"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _digest_tz() -> tzinfo:
    try:
        return ZoneInfo(_TZ_NAME)
    except ZoneInfoNotFoundError:
        return timezone.utc


def _in_send_window(now: datetime) -> bool:
    local = now.astimezone(_digest_tz())
    return _START_HOUR <= local.hour < _END_HOUR


def _digest_day_key(now: datetime) -> str:
    """The "day this digest covers" — UTC calendar day. Sending on
    Tuesday 08:00 CT covers events from Monday 00:00 UTC → Tuesday
    00:00 UTC (i.e. the just-completed UTC day)."""
    prev = now.astimezone(timezone.utc) - timedelta(days=1)
    return prev.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------
# Mode resolution + suppression helper.
# ---------------------------------------------------------------------

async def get_notification_mode(
    db: AsyncIOMotorDatabase, *, parent_id: str,
) -> str:
    """Return `"digest"` or `"immediate"` for a parent.

    Precedence:
      1. Explicit user pref in `digest_notification_prefs`.
      2. Auto: ≥3 active (non-revoked, non-expired) invitations →
         `digest`. Otherwise `immediate`.
    """
    pref = await db[_PREFS_COLL].find_one(
        {"parent_id": parent_id},
        {"_id": 0, "mode": 1},
    )
    if pref and pref.get("mode") in {"digest", "immediate"}:
        return pref["mode"]
    active_count = await _active_invitation_count(db, parent_id)
    return "digest" if active_count >= _MIN_ACTIVE_INVITATIONS_FOR_AUTO_DIGEST else "immediate"


async def set_notification_mode(
    db: AsyncIOMotorDatabase, *, parent_id: str, mode: str,
) -> str:
    """Persist an explicit override. `mode` must be one of
    `"digest" | "immediate" | "auto"`. `"auto"` deletes the pref
    so the resolver falls back to the auto rule."""
    if mode == "auto":
        await db[_PREFS_COLL].delete_one({"parent_id": parent_id})
        return await get_notification_mode(db, parent_id=parent_id)
    if mode not in {"digest", "immediate"}:
        raise ValueError("mode must be one of digest, immediate, auto")
    await db[_PREFS_COLL].update_one(
        {"parent_id": parent_id},
        {"$set": {
            "parent_id": parent_id,
            "mode": mode,
            "updated_at": _now_utc(),
        }},
        upsert=True,
    )
    return mode


async def _active_invitation_count(
    db: AsyncIOMotorDatabase, parent_id: str,
) -> int:
    now = _now_utc()
    return await db[_INVITES_COLL].count_documents({
        "inviting_parent_id": parent_id,
        "revoked_at": None,
        "access_expiration": {"$gte": now},
    })


# ---------------------------------------------------------------------
# Sweep.
# ---------------------------------------------------------------------

async def _iter_candidate_parents(db: AsyncIOMotorDatabase) -> List[str]:
    """Union of:
      * every parent with an explicit `mode="digest"` pref
      * every parent with ≥3 active invitations (auto-elevated)
    """
    explicit_cursor = db[_PREFS_COLL].find(
        {"mode": "digest"}, {"_id": 0, "parent_id": 1},
    )
    explicit = set()
    async for row in explicit_cursor:
        if row.get("parent_id"):
            explicit.add(row["parent_id"])

    now = _now_utc()
    auto_cursor = db[_INVITES_COLL].aggregate([
        {"$match": {
            "revoked_at": None,
            "access_expiration": {"$gte": now},
        }},
        {"$group": {"_id": "$inviting_parent_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": _MIN_ACTIVE_INVITATIONS_FOR_AUTO_DIGEST}}},
    ])
    auto = set()
    async for row in auto_cursor:
        if row.get("_id"):
            auto.add(row["_id"])

    # Subtract explicit `immediate` opt-outs so a user in auto range
    # who explicitly opted OUT is respected.
    override_out_cursor = db[_PREFS_COLL].find(
        {"mode": "immediate"}, {"_id": 0, "parent_id": 1},
    )
    override_out = set()
    async for row in override_out_cursor:
        if row.get("parent_id"):
            override_out.add(row["parent_id"])

    return sorted((explicit | auto) - override_out)


async def _already_sent_today(
    db: AsyncIOMotorDatabase, *, parent_id: str, digest_day: str,
) -> bool:
    row = await db[_SENDS_COLL].find_one(
        {"parent_id": parent_id, "digest_day": digest_day},
        {"_id": 1},
    )
    return row is not None


async def _record_send(
    db: AsyncIOMotorDatabase, *, parent_id: str,
    digest_day: str, event_count: int, dry_run: bool, reason: str,
) -> None:
    await db[_SENDS_COLL].insert_one({
        "parent_id": parent_id,
        "digest_day": digest_day,
        "event_count": event_count,
        "dry_run": bool(dry_run),
        "reason": reason,
        "sent_at": _now_utc(),
    })


async def _gather_events(
    db: AsyncIOMotorDatabase, *, parent_id: str,
    since: datetime, until: datetime,
) -> List[Dict[str, Any]]:
    cursor = (
        db[_EVENTS_COLL]
        .find({
            "inviting_parent_id": parent_id,
            "occurred_at": {"$gte": since, "$lt": until},
        }, {"_id": 0})
        .sort("occurred_at", 1)
    )
    out: List[Dict[str, Any]] = []
    async for row in cursor:
        out.append(row)
    return out


def _summarise_events(
    events: List[Dict[str, Any]],
    invite_lookup: Dict[str, Dict[str, Any]],
    perm_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Roll up events into a per-professional summary."""
    by_pro: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        inv = invite_lookup.get(ev.get("invitation_id"))
        if not inv:
            continue
        pro_key = ev.get("invitation_id")
        row = by_pro.setdefault(pro_key, {
            "professional_name": (
                f"{inv.get('professional_first_name') or ''} "
                f"{inv.get('professional_last_name') or ''}".strip()
                or "A professional"
            ),
            "professional_email": inv.get("professional_email"),
            "views": 0,
            "downloads": 0,
            "reports_touched": set(),
            "accepted": False,
            "declined": False,
        })
        if ev.get("event") == "view":
            row["views"] += 1
        elif ev.get("event") == "download":
            row["downloads"] += 1
        elif ev.get("event") == "accepted":
            row["accepted"] = True
        elif ev.get("event") == "declined":
            row["declined"] = True
        perm = perm_lookup.get(ev.get("permission_id"))
        if perm and perm.get("title"):
            row["reports_touched"].add(perm["title"])

    normalised = []
    for row in by_pro.values():
        normalised.append({
            "professional_name": row["professional_name"],
            "professional_email": row["professional_email"],
            "views": row["views"],
            "downloads": row["downloads"],
            "reports_touched": sorted(row["reports_touched"]),
            "accepted": row["accepted"],
            "declined": row["declined"],
        })
    normalised.sort(
        key=lambda r: (r["views"] + r["downloads"]), reverse=True,
    )

    total_events = sum(1 for _ in events)
    total_views = sum(r["views"] for r in normalised)
    total_downloads = sum(r["downloads"] for r in normalised)
    return {
        "professionals": normalised,
        "total_events": total_events,
        "total_views": total_views,
        "total_downloads": total_downloads,
    }


async def _dispatch_one(
    db: AsyncIOMotorDatabase,
    *,
    parent_id: str,
    digest_day: str,
    now: datetime,
    dry_run: bool,
) -> Dict[str, Any]:
    base = {"parent_id": parent_id, "digest_day": digest_day, "sent": False}
    if await _already_sent_today(db, parent_id=parent_id, digest_day=digest_day):
        return {**base, "reason": "already_sent"}

    # Pull the parent's email (from any invite row — cheapest lookup).
    any_invite = await db[_INVITES_COLL].find_one(
        {"inviting_parent_id": parent_id},
        {"_id": 0, "inviting_parent_email": 1, "inviting_parent_name": 1},
    )
    parent_email = (any_invite or {}).get("inviting_parent_email")
    if not parent_email or "@" not in parent_email:
        return {**base, "reason": "no_email"}

    day_start = datetime.strptime(digest_day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    events = await _gather_events(
        db, parent_id=parent_id, since=day_start, until=day_end,
    )
    if not events:
        # Silence-is-safety: no events → no email. Still record a
        # send row so we don't recompute later in the day.
        await _record_send(
            db, parent_id=parent_id, digest_day=digest_day,
            event_count=0, dry_run=dry_run, reason="no_events_silent",
        )
        return {**base, "reason": "no_events_silent"}

    invite_ids = {ev.get("invitation_id") for ev in events if ev.get("invitation_id")}
    invite_lookup: Dict[str, Dict[str, Any]] = {}
    async for inv in db[_INVITES_COLL].find({"invitation_id": {"$in": list(invite_ids)}}):
        invite_lookup[inv.get("invitation_id")] = inv

    perm_ids = {ev.get("permission_id") for ev in events if ev.get("permission_id")}
    perm_lookup: Dict[str, Dict[str, Any]] = {}
    async for p in db["professional_report_permissions"].find(
        {"permission_id": {"$in": list(perm_ids)}},
    ):
        perm_lookup[p.get("permission_id")] = p

    summary = _summarise_events(events, invite_lookup, perm_lookup)

    parent_name = (any_invite or {}).get("inviting_parent_name") or None

    if dry_run:
        await _record_send(
            db, parent_id=parent_id, digest_day=digest_day,
            event_count=len(events), dry_run=True, reason="dry_run",
        )
        return {**base, "sent": True, "dry_run": True, "summary": summary}

    try:
        from email_service import (
            EmailNotConfigured, EmailSendError,
            send_parent_share_digest_email,
        )
        send_parent_share_digest_email(
            to_email=parent_email,
            parent_name=parent_name,
            digest_day=digest_day,
            summary=summary,
        )
    except EmailNotConfigured:
        return {**base, "reason": "email_not_configured"}
    except EmailSendError as exc:
        return {**base, "reason": f"email_send_error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        log.exception("parent share digest send failed for %s", parent_id)
        return {**base, "reason": f"exception: {exc}"}

    await _record_send(
        db, parent_id=parent_id, digest_day=digest_day,
        event_count=len(events), dry_run=False, reason="sent",
    )
    return {**base, "sent": True, "summary": summary}


async def send_parent_share_digests(
    db: AsyncIOMotorDatabase,
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    force_window: bool = False,
) -> Dict[str, Any]:
    """One sweep pass. Returns a shape identical to the other sweeps."""
    now = now or _now_utc()
    if not force_window and not _in_send_window(now):
        return {
            "skipped": "outside_send_window", "at": now.isoformat(),
            "results": [],
        }

    digest_day = _digest_day_key(now)
    candidates = await _iter_candidate_parents(db)
    results: List[Dict[str, Any]] = []
    for parent_id in candidates:
        try:
            results.append(await _dispatch_one(
                db,
                parent_id=parent_id, digest_day=digest_day,
                now=now, dry_run=dry_run,
            ))
        except Exception as exc:  # noqa: BLE001
            log.exception("parent share digest dispatch failed for %s", parent_id)
            results.append({
                "parent_id": parent_id, "digest_day": digest_day,
                "sent": False, "reason": f"exception: {exc}",
            })
    return {
        "at": now.isoformat(),
        "digest_day": digest_day,
        "candidates": len(candidates),
        "results": results,
        "sent_count": sum(1 for r in results if r.get("sent") and not r.get("dry_run")),
    }


# ---------------------------------------------------------------------------
# Background loop.
# ---------------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("PARENT_SHARE_DIGEST_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


async def parent_share_digest_loop(app) -> None:
    if not _enabled():
        log.info(
            "parent_share_digest_loop: PARENT_SHARE_DIGEST_ENABLED "
            "not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    await asyncio.sleep(180)  # spread startup load
    while True:
        try:
            db = app.state.db
            await send_parent_share_digests(db)
        except Exception:  # noqa: BLE001
            log.exception("parent share digest sweep failed; will retry.")
        await asyncio.sleep(_SWEEP_INTERVAL_S)
