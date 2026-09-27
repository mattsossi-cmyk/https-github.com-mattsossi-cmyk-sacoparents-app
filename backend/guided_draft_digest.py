"""Guided Draft Nudge Digest — iter224.

Weekly admin summary of last week's Guided Journey nudge batch:
how many nudges went out and how many parents finished (or edited)
their draft within 7 days of receiving one.

Fired by the platform cron ``.emergent/crons.yml`` → ``/api/cron/nudge-digest``
one hour after the nudge sweep, so this run measures the PRIOR week's
batch — every included parent has had a full 7 days to react.

"Finished" heuristic (privacy-preserving, no PHI leaked):
  * The parent's ``portal_state.guided_drafts[topic]`` for that
    nudge no longer exists  → converted (they hit Confirm & save
    which clears the draft), or
  * The draft's ``updated_at`` ms epoch is > the nudge's
    ``sent_at`` ms epoch → they picked it back up after seeing
    the email.
Anything else is counted as untouched.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


logger = logging.getLogger(__name__)

PORTAL_STATE_COLL = "portal_state"
NUDGES_COLL = "guided_draft_nudges"

# Cover the week that ENDS 7 days ago (i.e. nudges sent between
# now-14 days and now-7 days). Anything newer hasn't had 7 days to
# react yet; anything older is stale enough that we don't want to
# revisit it in this week's digest.
LOOKBACK_START_DAYS = 14
LOOKBACK_END_DAYS = 7

# Follow-up window: how long after the nudge_sent_at the parent has
# to "finish" for us to count it as a conversion.
FOLLOW_UP_DAYS = 7

_TOPIC_LABELS: Dict[str, str] = {
    "foundation": "Foundation Statement",
    "coparenting": "Co-parenting Assessment",
    "safety": "Safety Check",
    "medical": "Medical Needs Assessment",
    "educational": "Educational Assessment",
    "psychological": "Psychological Assessment",
}


def _admin_recipients() -> List[str]:
    raw = os.environ.get("ADMIN_EMAILS", "mattsossi@bsossi.com")
    return [e.strip() for e in raw.split(",") if e.strip()]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sent_at_dt(row: Dict[str, Any]) -> Optional[datetime]:
    raw = row.get("sent_at")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    return None


def _draft_updated_at_ms(snapshot: Dict[str, Any]) -> Optional[int]:
    raw = snapshot.get("updated_at") if isinstance(snapshot, dict) else None
    if isinstance(raw, (int, float)):
        return int(raw)
    return None


async def compute_digest(
    db: AsyncIOMotorDatabase,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return the raw digest payload without sending an email.

    Split from ``send_nudge_digest`` so tests + the future admin UI
    can render the same numbers.

    iter230 — also computes the PRIOR digest window (14–7 days
    before this window) so the founder email can show a
    week-over-week trend. Returns ``previous_total_sent``,
    ``previous_total_finished``, ``previous_conversion_pct``,
    ``trend_delta_pct`` and ``trend_direction`` ('up' / 'down' /
    'flat' / 'new'). 'new' means we have no prior data to
    compare against.
    """
    now = now or _now()
    window_start, window_end, current = await _compute_window(
        db, now=now, offset_days=0
    )
    prev_start, prev_end, previous = await _compute_window(
        db, now=now, offset_days=7
    )

    total_sent = current["total_sent"]
    total_finished = current["total_finished"]
    conversion = (
        round(total_finished / total_sent * 100, 1) if total_sent else 0.0
    )
    prev_total_sent = previous["total_sent"]
    prev_total_finished = previous["total_finished"]
    prev_conversion = (
        round(prev_total_finished / prev_total_sent * 100, 1)
        if prev_total_sent
        else 0.0
    )

    if prev_total_sent == 0:
        trend_direction = "new"
        trend_delta_pct = 0.0
    else:
        trend_delta_pct = round(conversion - prev_conversion, 1)
        if trend_delta_pct > 0.5:
            trend_direction = "up"
        elif trend_delta_pct < -0.5:
            trend_direction = "down"
        else:
            trend_direction = "flat"

    return {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "total_sent": total_sent,
        "total_finished": total_finished,
        "conversion_pct": conversion,
        "by_topic": {
            _TOPIC_LABELS[k]: v for k, v in sorted(current["by_topic"].items())
        },
        "previous_window_start": prev_start.isoformat(),
        "previous_window_end": prev_end.isoformat(),
        "previous_total_sent": prev_total_sent,
        "previous_total_finished": prev_total_finished,
        "previous_conversion_pct": prev_conversion,
        "trend_delta_pct": trend_delta_pct,
        "trend_direction": trend_direction,
    }


async def _compute_window(
    db: AsyncIOMotorDatabase,
    *,
    now: datetime,
    offset_days: int,
) -> tuple:
    """Compute totals for a single 7-day window offset by ``offset_days``.

    offset_days=0 → the current digest window (now-14d → now-7d).
    offset_days=7 → the previous window (now-21d → now-14d).

    Returns (window_start, window_end, {total_sent, total_finished,
    by_topic}).
    """
    window_start = now - timedelta(days=LOOKBACK_START_DAYS + offset_days)
    window_end = now - timedelta(days=LOOKBACK_END_DAYS + offset_days)

    total_sent = 0
    total_finished = 0
    by_topic: Dict[str, Dict[str, int]] = {}

    # Index portal_state docs by user_id once so we don't hit Mongo
    # per-nudge — the sweep is tiny but this keeps digest cost O(n).
    portal_docs: Dict[str, Dict[str, Any]] = {}
    async for doc in db[PORTAL_STATE_COLL].find(
        {}, {"user_id": 1, "guided_drafts": 1}
    ):
        uid = doc.get("user_id")
        if uid:
            portal_docs[uid] = doc

    async for row in db[NUDGES_COLL].find({}):
        sent_at = _sent_at_dt(row)
        if not sent_at:
            continue
        if sent_at < window_start or sent_at > window_end:
            continue
        topic = row.get("topic")
        if topic not in _TOPIC_LABELS:
            continue

        total_sent += 1
        by_topic.setdefault(topic, {"sent": 0, "finished": 0})
        by_topic[topic]["sent"] += 1

        # Finished heuristic — draft cleared entirely OR updated
        # after the nudge went out.
        finished = False
        portal_doc = portal_docs.get(row.get("user_id"))
        drafts = (portal_doc or {}).get("guided_drafts") if portal_doc else None
        if not isinstance(drafts, dict) or topic not in drafts:
            finished = True
        else:
            updated_ms = _draft_updated_at_ms(drafts[topic])
            sent_ms = int(sent_at.timestamp() * 1000)
            if updated_ms and updated_ms > sent_ms:
                # Also within the follow-up window
                follow_deadline_ms = int(
                    (sent_at + timedelta(days=FOLLOW_UP_DAYS)).timestamp() * 1000
                )
                if updated_ms <= follow_deadline_ms:
                    finished = True

        if finished:
            total_finished += 1
            by_topic[topic]["finished"] += 1

    return window_start, window_end, {
        "total_sent": total_sent,
        "total_finished": total_finished,
        "by_topic": by_topic,
    }


async def send_nudge_digest(
    db: AsyncIOMotorDatabase,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute + email the weekly digest to every ``ADMIN_EMAILS`` inbox."""
    from email_service import send_nudge_digest as _email

    digest = await compute_digest(db, now=now)
    recipients = _admin_recipients()

    if digest["total_sent"] == 0:
        logger.info("nudge digest: no nudges in window, skipping email")
        return {**digest, "recipients_sent": 0}

    sent_count = 0
    for admin_email in recipients:
        try:
            _email(to_email=admin_email, digest=digest)
            sent_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "nudge digest email failed for %s: %s", admin_email, exc
            )
    logger.info(
        "nudge digest sent to %d admins (total_sent=%d, finished=%d)",
        sent_count,
        digest["total_sent"],
        digest["total_finished"],
    )
    return {**digest, "recipients_sent": sent_count}
