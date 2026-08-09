"""Coordinator alerting for ND Risk Assessment.

Fires an ops-style email to the operator (``OPERATOR_EMAIL``) the moment
a parent's assessment lands on the ``high`` or ``critical`` tier so the
operator can reach out same day.

Dedupe strategy (stored in ``nd_coordinator_alerts`` collection):

* Same tier, same parent → at most one email per 24 hours. Prevents
  a parent re-submitting the same assessment three times from spamming
  the operator's inbox.
* Tier ESCALATION → always fires immediately (medium → high, low →
  critical, high → critical, etc.). An escalation is defined as a
  strictly higher tier than the last alerted tier for this parent
  within the last 30 days.
* On any successful fire we record the row (assessment_id, tier,
  sent_at) so a retry later gets the correct dedupe answer.
* All email failures are swallowed — a downed email provider must never
  block a parent's submission.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)

COLLECTION = "nd_coordinator_alerts"

# Ordered severity — matches nd_risk_routes._tier.
TIER_ORDER: Dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}

# Only these tiers fire an alert.
ALERT_TIERS = frozenset({"high", "critical"})

# Dedupe window for same-tier re-submissions.
_SAME_TIER_WINDOW_HOURS = 24
# How far back to look for an "escalation" comparison.
_ESCALATION_LOOKBACK_DAYS = 30


async def _last_alert(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_ESCALATION_LOOKBACK_DAYS)).isoformat()
    return await db[COLLECTION].find_one(
        {"user_id": user_id, "sent_at": {"$gte": cutoff}},
        {"_id": 0},
        sort=[("sent_at", -1)],
    )


def _should_fire(prior: Optional[Dict[str, Any]], now_tier: str) -> Optional[str]:
    """Return the ``reason`` string to send with the alert, or ``None`` if
    the alert should be suppressed by dedupe."""
    if now_tier not in ALERT_TIERS:
        return None
    if not prior:
        return "hit"
    prior_tier = prior.get("tier") or "low"
    prior_rank = TIER_ORDER.get(prior_tier, -1)
    now_rank = TIER_ORDER.get(now_tier, -1)
    if now_rank > prior_rank:
        return "escalated"
    # Same tier OR strictly-lower tier (e.g. critical→high oscillation) →
    # respect the 24-hour dedupe window so a fluctuating case doesn't
    # generate repeat operator emails. Previously a downgrade fell
    # through to "hit" which bypassed the window entirely (LOW finding
    # from the iter 87-93 code review).
    try:
        last_sent = datetime.fromisoformat(prior["sent_at"])
    except (KeyError, TypeError, ValueError):
        return "re_hit"
    if datetime.now(timezone.utc) - last_sent >= timedelta(hours=_SAME_TIER_WINDOW_HOURS):
        return "re_hit"
    return None


async def maybe_fire_coordinator_alert(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    assessment_id: str,
    tier: str,
    tier_label: str,
    total_score: int,
    target_name: Optional[str],
    coparent_name: Optional[str],
    submitted_at: str,
) -> Dict[str, Any]:
    """Fire (or suppress) a coordinator alert for this assessment.

    Returns a dict describing what happened — useful in tests and for the
    submit_assessment response. Never raises.
    """
    if tier not in ALERT_TIERS:
        return {"fired": False, "reason": "not_alerting_tier"}

    operator_email = (os.environ.get("OPERATOR_EMAIL") or "").strip().lower()
    if not operator_email:
        log.info("nd_coordinator_alert: OPERATOR_EMAIL not set; skipping")
        return {"fired": False, "reason": "no_operator_email"}

    prior = await _last_alert(db, user_id)
    reason = _should_fire(prior, tier)
    if not reason:
        return {"fired": False, "reason": "deduped"}

    # Import inside the function to avoid a top-level import cycle with
    # email_service (which imports resend at module load time).
    try:
        from email_service import send_coordinator_nd_alert  # noqa: WPS433
        send_coordinator_nd_alert(
            to_email=operator_email,
            tier=tier,
            tier_label=tier_label,
            total_score=int(total_score),
            target_name=target_name,
            coparent_name=coparent_name,
            assessment_id=assessment_id,
            submitted_at=submitted_at,
            reason=reason,
        )
        send_ok, send_error = True, None
    except Exception as exc:  # noqa: BLE001
        # Never let an email hiccup break the parent's submission.
        log.warning("nd_coordinator_alert send failed: %s", exc)
        send_ok, send_error = False, str(exc)

    # Record the row unconditionally so a broken email provider doesn't
    # cause a new alert every submit. If the send failed the operator
    # will notice via the missing email + the audit collection.
    doc = {
        "user_id":       user_id,
        "assessment_id": assessment_id,
        "tier":          tier,
        "tier_label":    tier_label,
        "score":         int(total_score),
        "reason":        reason,
        "sent_at":       datetime.now(timezone.utc).isoformat(),
        "email_ok":      send_ok,
        "email_error":   send_error,
    }
    await db[COLLECTION].insert_one(doc)
    return {"fired": send_ok, "reason": reason, "email_ok": send_ok}
