"""Guided Journey Draft Nudge — iter223.

Weekly friendly nudge to parents whose Guided Journey wizard draft
has gone stale but hasn't yet expired at the 14-day TTL. Called from
the platform cron (`.emergent/crons.yml` → `/api/cron/guided-draft-nudge`).

Design:
  * Pure async ``send_guided_draft_nudges(db)`` — cron / admin / manual
    invocation, never self-schedules.
  * Dedupe: one nudge per (user_id, topic, iso_week) tracked in
    ``guided_draft_nudges`` collection. First-touch wins for the week.
  * Only touches parents whose:
        - draft ``updated_at`` is >= NUDGE_MIN_DAYS days ago
        - draft ``updated_at`` is <  DRAFT_TTL_DAYS days ago
          (about-to-expire, not already expired)
  * Never touches drafts that have already been converted into an
    actual portal record (Foundation Statement, align_record, etc.).
    Those live outside ``portal_state.guided_drafts``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


logger = logging.getLogger(__name__)

PORTAL_STATE_COLL = "portal_state"
USERS_COLL = "users"
NUDGES_COLL = "guided_draft_nudges"

# Fire when a draft has been silent for at least this long — must be
# tighter than the 14-day TTL so parents get real time to act.
NUDGE_MIN_DAYS = 5
# Matches ``GUIDED_DRAFT_TTL_MS`` on the frontend so the nudge stops
# once a draft is about to be auto-cleared anyway.
DRAFT_TTL_DAYS = 14

# Human-friendly topic labels — kept in lockstep with the frontend
# ``TOPIC_TITLES`` map in ``GuidedJourneyModal.jsx``.
_TOPIC_LABELS: Dict[str, str] = {
    "foundation": "Foundation Statement",
    "coparenting": "Co-parenting Assessment",
    "safety": "Conflict Readiness",
    "medical": "Medical Needs Assessment",
    "educational": "Educational Assessment",
    "psychological": "Psychological Assessment",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_week_key(when: datetime) -> str:
    """Deduplication key — one nudge per parent per topic per ISO week."""
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_updated_at(snapshot: Dict[str, Any]) -> Optional[datetime]:
    """Parse the draft's ``updated_at`` ms epoch. Returns UTC datetime."""
    raw = snapshot.get("updated_at")
    if isinstance(raw, (int, float)):
        # Millisecond epoch (frontend writes ``Date.now()``).
        return datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


async def send_guided_draft_nudges(
    db: AsyncIOMotorDatabase,
    *,
    portal_url: Optional[str] = None,
) -> Dict[str, int]:
    """Sweep ``portal_state`` for stale-but-not-expired guided drafts.

    Returns a small stats dict for logs/observability.
    """
    # Late import so this module stays test-friendly even when the
    # email service is misconfigured (Resend key missing in preview).
    from email_service import send_guided_draft_nudge as _email

    portal_url = portal_url or "https://sacoparentsapp.online/"
    now = _now()
    week_key = _iso_week_key(now)
    ttl_cutoff = now - timedelta(days=DRAFT_TTL_DAYS)
    nudge_cutoff = now - timedelta(days=NUDGE_MIN_DAYS)

    scanned = 0
    eligible = 0
    sent = 0
    skipped_dupes = 0

    cursor = db[PORTAL_STATE_COLL].find(
        {"guided_drafts": {"$exists": True, "$ne": None}}
    )
    async for doc in cursor:
        scanned += 1
        drafts = doc.get("guided_drafts") or {}
        if not isinstance(drafts, dict) or not drafts:
            continue

        user_id = doc.get("user_id")
        user_doc = None
        if user_id:
            user_doc = await db[USERS_COLL].find_one({"user_id": user_id})
        if not user_doc or not user_doc.get("email"):
            continue

        for topic, snapshot in drafts.items():
            if not isinstance(snapshot, dict):
                continue
            if topic not in _TOPIC_LABELS:
                continue
            updated = _parse_updated_at(snapshot)
            if not updated:
                continue
            # In-window: stale but not yet expired.
            if updated > nudge_cutoff:
                continue
            if updated < ttl_cutoff:
                continue

            eligible += 1

            # Dedupe: one email per (user_id, topic, iso_week).
            dedupe_key = {
                "user_id": user_id,
                "topic": topic,
                "week_key": week_key,
            }
            already = await db[NUDGES_COLL].find_one(dedupe_key)
            if already:
                skipped_dupes += 1
                continue

            progress = snapshot.get("progress") or {}
            days_since = max(1, (now - updated).days)
            days_left = max(1, DRAFT_TTL_DAYS - days_since)
            try:
                _email(
                    to_email=user_doc["email"],
                    parent_name=user_doc.get("name") or None,
                    topic_label=_TOPIC_LABELS[topic],
                    step_number=int(progress.get("step") or 0),
                    total_steps=int(progress.get("total") or 5),
                    days_since_update=days_since,
                    days_left=days_left,
                    portal_url=portal_url,
                )
                sent += 1
                await db[NUDGES_COLL].insert_one(
                    {
                        **dedupe_key,
                        "sent_at": now.isoformat(),
                        "days_since_update": days_since,
                        "days_left": days_left,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "guided draft nudge failed for user=%s topic=%s: %s",
                    user_id,
                    topic,
                    exc,
                )

    logger.info(
        "guided_draft_nudge sweep: scanned=%d eligible=%d sent=%d dupes=%d",
        scanned,
        eligible,
        sent,
        skipped_dupes,
    )
    return {
        "scanned": scanned,
        "eligible": eligible,
        "sent": sent,
        "skipped_dupes": skipped_dupes,
    }
