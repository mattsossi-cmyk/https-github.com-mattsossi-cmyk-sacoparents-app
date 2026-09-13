"""Consent Adoption Digest — Monday-morning admin email.

Watches the Child-Needs share-consent flow so admins can spot
friction *before* it becomes a support ticket. Every Monday morning
in the configured send-window timezone, this sweep computes:

  * `parents_consented`           — distinct parents-list entries
    with a truthy `child_needs_share_consent_at` on a joint case.
  * `cases_both_consented`        — joint cases where BOTH parents
    have opted in (i.e. how many joint reports currently unlock
    Section 5 highlights).
  * `cases_total`                 — joint cases that exist. Denominator
    for `unlock_rate_pct`.
  * `parents_consented_delta_7d`  — new parent opt-ins in the last 7d.
  * `cases_both_delta_7d`         — new both-consented cases in 7d.

…and emails it to every recipient in `ADMIN_EMAILS`. Aggregate only —
no verbatim parent answers ever leave the DB.

Gated behind `CONSENT_ADOPTION_DIGEST_ENABLED=1` — idle no-op when
unset, safe to always register from `server.py`.

Contract mirrors `weekly_case_analytics_email.py` so the same
dedupe / send-window / opt-out patterns are reused.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

_CASES_COLLECTION = "joint_alignment_cases"
_SENDS_COLLECTION = "consent_adoption_digest_sends"

_SWEEP_INTERVAL_S = int(
    os.environ.get("CONSENT_ADOPTION_DIGEST_SWEEP_SECONDS", "3600")
)
_MONDAY_SEND_START_HOUR = int(
    os.environ.get("CONSENT_ADOPTION_DIGEST_START_HOUR", "9")
)
_MONDAY_SEND_END_HOUR = int(
    os.environ.get("CONSENT_ADOPTION_DIGEST_END_HOUR", "11")
)
_SEND_WINDOW_TZ_NAME = (
    os.environ.get("CONSENT_ADOPTION_DIGEST_TZ") or "America/Chicago"
)


def _send_window_tz() -> tzinfo:
    try:
        return ZoneInfo(_SEND_WINDOW_TZ_NAME)
    except ZoneInfoNotFoundError:
        log.warning(
            "consent_adoption_digest: unknown timezone %r; falling back to UTC",
            _SEND_WINDOW_TZ_NAME,
        )
        return timezone.utc


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _week_start(dt: Optional[datetime] = None) -> str:
    """ISO date (YYYY-MM-DD) of the Monday preceding `dt`, evaluated
    in the send-window timezone. Dedupe key — one digest per admin
    per ISO week."""
    tz = _send_window_tz()
    d = (dt or _now_utc()).astimezone(tz)
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _in_send_window(now: datetime) -> bool:
    local = now.astimezone(_send_window_tz())
    return (
        local.weekday() == 0
        and _MONDAY_SEND_START_HOUR <= local.hour < _MONDAY_SEND_END_HOUR
    )


def _as_aware_utc(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _admin_console_url() -> str:
    base = (os.environ.get("PUBLIC_APP_ORIGIN") or "").rstrip("/") or "https://sacoparentsapp.online"
    return f"{base}/admin/overview"


# ---------------------------------------------------------------------------
# Aggregation — mirrors the `analytics_routes.py` consent block so admins
# see the same numbers in the digest as in the on-screen console.
# ---------------------------------------------------------------------------

def _compute_consent_stats(cases: List[Dict[str, Any]], week_ago: datetime) -> Dict[str, Any]:
    """Given the full list of joint alignment case docs, compute:

      parents_consented         — parent slots with a truthy
                                  `child_needs_share_consent_at`
      cases_both_consented      — cases where BOTH parents have consented
      cases_total               — cases in the collection
      parents_consented_delta_7d — parent slots that consented in the
                                   last 7 days (by `child_needs_share_consent_at`)
      cases_both_delta_7d       — cases where BOTH parents' consent
                                  timestamps fall in the last 7 days
                                  (i.e. the case transitioned to
                                  both-consented this week)
      unlock_rate_pct           — cases_both_consented / cases_total
    """
    parents_consented = 0
    cases_both_consented = 0
    parents_consented_delta = 0
    cases_both_delta = 0
    cases_total = len(cases)

    for c in cases:
        parents = c.get("parents") or []
        # Guard against unexpected shapes — a 1-parent or 3-parent doc
        # just contributes what it has.
        consent_times = [
            _as_aware_utc(p.get("child_needs_share_consent_at"))
            for p in parents
        ]
        for ts in consent_times:
            if ts is not None:
                parents_consented += 1
                if ts >= week_ago:
                    parents_consented_delta += 1
        # A case counts as "both consented" iff there are ≥ 2 parent
        # slots AND every slot has a truthy consent timestamp. We only
        # look at the first two slots to stay consistent with the
        # analytics_routes.py aggregation (`arrayElemAt` 0 & 1).
        if len(parents) >= 2 and consent_times[0] and consent_times[1]:
            cases_both_consented += 1
            most_recent = max(consent_times[0], consent_times[1])
            if most_recent >= week_ago:
                cases_both_delta += 1

    unlock_rate_pct = (
        round((cases_both_consented / cases_total) * 100)
        if cases_total else 0
    )

    return {
        "parents_consented": parents_consented,
        "cases_both_consented": cases_both_consented,
        "cases_total": cases_total,
        "unlock_rate_pct": unlock_rate_pct,
        "parents_consented_delta_7d": parents_consented_delta,
        "cases_both_delta_7d": cases_both_delta,
    }


# ---------------------------------------------------------------------------
# Sweep pipeline
# ---------------------------------------------------------------------------

async def _load_all_cases(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    cursor = db[_CASES_COLLECTION].find(
        {},
        {
            "_id": 0,
            "case_id": 1,
            "parents.child_needs_share_consent_at": 1,
        },
    )
    return [c async for c in cursor]


async def _already_sent_this_week(
    db: AsyncIOMotorDatabase, *, admin_email: str, week_start: str,
) -> bool:
    row = await db[_SENDS_COLLECTION].find_one({
        "admin_email": admin_email, "week_start": week_start,
    })
    return row is not None


async def _record_send(
    db: AsyncIOMotorDatabase,
    *,
    admin_email: str,
    week_start: str,
    dry_run: bool,
    reason: str,
    stats: Optional[Dict[str, Any]] = None,
) -> None:
    await db[_SENDS_COLLECTION].insert_one({
        "admin_email": admin_email,
        "week_start": week_start,
        "dry_run": bool(dry_run),
        "reason": reason,
        "stats": stats or {},
        "created_at": _now_utc(),
    })


def _has_baseline(stats: Dict[str, Any]) -> bool:
    """Send only when there's SOMETHING to report. Before the feature
    has any consented parents at all we skip the digest — a Monday
    inbox line saying "0 out of 0" is noise, not signal."""
    return bool(
        stats.get("parents_consented", 0)
        or stats.get("cases_both_consented", 0)
    )


async def send_consent_adoption_digest(
    db: AsyncIOMotorDatabase,
    *,
    admin_emails: Optional[List[str]] = None,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    force_window: bool = False,
) -> Dict[str, Any]:
    """One sweep pass.

    * `admin_emails` — if `None`, resolves from analytics_routes.ADMIN_EMAILS
      at call time (so an env change is picked up on the next Monday).
    * `dry_run`      — records a dedupe row + returns stats, does NOT send.
    * `now`          — for tests. Defaults to `datetime.now(utc)`.
    * `force_window` — bypasses the Monday-morning gate for tests /
      manual admin `POST /api/admin/consent-digest/run-now`.
    """
    now = now or _now_utc()
    if not force_window and not _in_send_window(now):
        return {
            "skipped": "outside_send_window",
            "at": now.isoformat(),
            "results": [],
        }

    if admin_emails is None:
        # Lazy import to avoid a hard dependency during pytest module
        # collection when the routes layer is stubbed.
        from analytics_routes import ADMIN_EMAILS
        admin_emails = sorted(ADMIN_EMAILS)

    if not admin_emails:
        return {
            "skipped": "no_admin_recipients",
            "at": now.isoformat(),
            "results": [],
        }

    week_start = _week_start(now)
    week_ago = now - timedelta(days=7)
    cases = await _load_all_cases(db)
    stats = _compute_consent_stats(cases, week_ago)

    if not _has_baseline(stats):
        return {
            "at": now.isoformat(),
            "week_start": week_start,
            "skipped": "no_baseline_activity",
            "stats": stats,
            "results": [],
        }

    results: List[Dict[str, Any]] = []
    for admin_email in admin_emails:
        result = await _dispatch_one(
            db,
            admin_email=admin_email,
            week_start=week_start,
            stats=stats,
            dry_run=dry_run,
        )
        results.append(result)

    return {
        "at": now.isoformat(),
        "week_start": week_start,
        "stats": stats,
        "results": results,
        "sent_count": sum(1 for r in results if r.get("sent")),
    }


async def _dispatch_one(
    db: AsyncIOMotorDatabase,
    *,
    admin_email: str,
    week_start: str,
    stats: Dict[str, Any],
    dry_run: bool,
) -> Dict[str, Any]:
    base = {"admin_email": admin_email, "week_start": week_start, "sent": False}

    if await _already_sent_this_week(
        db, admin_email=admin_email, week_start=week_start,
    ):
        return {**base, "reason": "already_sent_this_week"}

    if dry_run:
        await _record_send(
            db, admin_email=admin_email, week_start=week_start,
            dry_run=True, reason="dry_run", stats=stats,
        )
        return {**base, "sent": True, "dry_run": True, "stats": stats}

    try:
        from email_service import (
            EmailNotConfigured, EmailSendError,
            send_admin_consent_adoption_digest,
        )
        send_admin_consent_adoption_digest(
            to_email=admin_email,
            stats=stats,
            week_start=week_start,
            console_url=_admin_console_url(),
        )
    except EmailNotConfigured:
        return {**base, "reason": "email_not_configured"}
    except EmailSendError as exc:
        return {**base, "reason": f"email_send_error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        log.exception("consent adoption digest failed for %s", admin_email)
        return {**base, "reason": f"exception: {exc}"}

    await _record_send(
        db, admin_email=admin_email, week_start=week_start,
        dry_run=False, reason="sent", stats=stats,
    )
    # Best-effort Slack mirror — one webhook post per successful admin
    # dispatch. Wrapped so a Slack failure NEVER blocks the email path.
    try:
        await _mirror_to_slack(admin_email=admin_email, stats=stats, week_start=week_start)
    except Exception:  # noqa: BLE001
        log.exception("consent adoption digest: slack mirror failed")

    return {**base, "sent": True, "stats": stats}


def _slack_webhook_url() -> Optional[str]:
    url = (os.environ.get("SLACK_DIGEST_WEBHOOK_URL") or "").strip()
    return url or None


async def _mirror_to_slack(
    *,
    admin_email: str,
    stats: Dict[str, Any],
    week_start: str,
) -> None:
    """Post a compact Block-Kit summary of the digest to Slack. No-op
    if `SLACK_DIGEST_WEBHOOK_URL` is not set. Runs in an executor so
    the sweep loop's event loop isn't blocked on Slack's roundtrip."""
    webhook = _slack_webhook_url()
    if not webhook:
        return
    parents = int(stats.get("parents_consented", 0))
    both = int(stats.get("cases_both_consented", 0))
    total = int(stats.get("cases_total", 0))
    unlock_pct = int(stats.get("unlock_rate_pct", 0))
    delta_parents = int(stats.get("parents_consented_delta_7d", 0))
    delta_both = int(stats.get("cases_both_delta_7d", 0))

    payload = {
        "text": (
            f"*SA CoParents · Consent adoption ({week_start})*\n"
            f"• {parents} parents opted in\n"
            f"• {both}/{total} cases fully unlocked ({unlock_pct}%)\n"
            f"• +{delta_parents} parents · +{delta_both} newly-unlocked this week\n"
            f"Emailed to {admin_email} — aggregate only, no verbatim answers."
        ),
    }
    import asyncio, urllib.request, json as _json
    def _post():
        req = urllib.request.Request(
            webhook,
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            _ = resp.read()
    await asyncio.get_running_loop().run_in_executor(None, _post)


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------

def _enabled() -> bool:
    return (os.environ.get("CONSENT_ADOPTION_DIGEST_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


async def consent_adoption_digest_loop(app) -> None:
    """Long-running Monday-morning sweep. Idle no-op when the env flag
    is not set — safe to always register from server.py."""
    if not _enabled():
        log.info(
            "consent_adoption_digest_loop: "
            "CONSENT_ADOPTION_DIGEST_ENABLED not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    # Offset from the other Monday sweeps so they don't all fire at once.
    await asyncio.sleep(420)
    while True:
        try:
            db = app.state.db
            await send_consent_adoption_digest(db)
        except Exception:  # noqa: BLE001
            log.exception(
                "consent adoption digest sweep failed; will retry.",
            )
        await asyncio.sleep(_SWEEP_INTERVAL_S)
