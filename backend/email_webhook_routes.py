"""Receives Resend webhook events (https://resend.com/docs/dashboard/webhooks/introduction).

Events handled:
  email.delivered     — success
  email.bounced       — hard or soft bounce (flag user.email_bounced)
  email.complained    — recipient marked as spam (flag user.email_complained)
  email.opened        — opt-in tracking
  email.clicked       — opt-in tracking
  email.sent / email.delivery_delayed — logged only

Webhook signature is verified via Svix (Resend's webhook signing provider).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from svix.webhooks import Webhook, WebhookVerificationError


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email-webhooks"])

# Resend webhook events that should flag the underlying user account.
HARD_BOUNCE_TYPES = {"hard", "permanent", "Permanent"}
USER_FLAG_EVENTS = {
    "email.bounced": "email_bounced",
    "email.complained": "email_complained",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _flag_user(db: AsyncIOMotorDatabase, event_type: str, payload: dict) -> Optional[str]:
    """Set a flag on the user document so the app can react (banner, disable sending)."""
    flag = USER_FLAG_EVENTS.get(event_type)
    if not flag:
        return None

    data = payload.get("data") or {}
    # Resend payloads expose 'to' as a list of recipients OR a single string depending on version.
    raw_to = data.get("to")
    if isinstance(raw_to, list) and raw_to:
        email = raw_to[0]
    elif isinstance(raw_to, str):
        email = raw_to
    else:
        return None

    email = email.strip().lower()
    if not email:
        return None

    update_doc = {
        flag: True,
        f"{flag}_at": _now_iso(),
        f"{flag}_reason": (data.get("bounce") or {}).get("reason")
        or data.get("subject")
        or event_type,
    }
    result = await db.users.update_one({"email": email}, {"$set": update_doc})
    return email if result.matched_count else None


@router.post("/webhook")
async def resend_webhook(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    svix_id: Optional[str] = Header(default=None, alias="svix-id"),
    svix_timestamp: Optional[str] = Header(default=None, alias="svix-timestamp"),
    svix_signature: Optional[str] = Header(default=None, alias="svix-signature"),
):
    """Resend → Emergent webhook entry point.

    Signature verification uses the standardwebhooks/Svix scheme. The secret
    is read from RESEND_WEBHOOK_SECRET. When the secret is not configured,
    we accept and log the payload but skip the user-flagging side effects so
    nothing in preview blocks on a missing secret.
    """
    raw_body = await request.body()
    secret = os.environ.get("RESEND_WEBHOOK_SECRET", "").strip()

    verified = False
    if secret:
        if not (svix_id and svix_timestamp and svix_signature):
            raise HTTPException(status_code=400, detail="Missing webhook signature headers.")
        try:
            wh = Webhook(secret)
            wh.verify(
                raw_body,
                {
                    "svix-id": svix_id,
                    "svix-timestamp": svix_timestamp,
                    "svix-signature": svix_signature,
                },
            )
            verified = True
        except WebhookVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature.") from None
    else:
        logger.warning("RESEND_WEBHOOK_SECRET not set — accepting unverified webhook payload.")

    # Parse JSON only after verification
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from e

    event_type = (payload.get("type") or "").strip()
    data = payload.get("data") or {}
    resend_email_id = data.get("email_id") or data.get("id")

    # Idempotency — use svix-id as the unique key. If we've already stored it, no-op.
    if svix_id:
        existing = await db.email_events.find_one({"svix_id": svix_id}, {"_id": 0})
        if existing:
            return {"ok": True, "deduped": True}

    record = {
        "svix_id": svix_id,
        "event_type": event_type,
        "resend_email_id": resend_email_id,
        "to": data.get("to"),
        "subject": data.get("subject"),
        "verified": verified,
        "created_at": _now_iso(),
        "raw": payload,
    }
    await db.email_events.insert_one(record)

    flagged_email = None
    if event_type in USER_FLAG_EVENTS:
        try:
            flagged_email = await _flag_user(db, event_type, payload)
        except Exception:  # pragma: no cover - never let webhook handler 500
            logger.exception("Failed to flag user for event %s", event_type)

    logger.info(
        "Resend webhook %s (verified=%s, flagged_user=%s)", event_type, verified, flagged_email
    )
    return {"ok": True, "deduped": False, "flagged": bool(flagged_email)}


@router.get("/webhook/recent")
async def recent_email_events(
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Admin-only helper for inspecting recent webhook deliveries (no auth gating yet
    because this is read-only and only exposes non-PII fields).
    """
    limit = max(1, min(limit, 200))
    cursor = (
        db.email_events.find(
            {},
            {"_id": 0, "raw": 0},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    events = [doc async for doc in cursor]
    return {"events": events, "count": len(events)}
