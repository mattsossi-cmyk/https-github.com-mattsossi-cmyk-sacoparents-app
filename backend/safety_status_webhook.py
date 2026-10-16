"""Phase 3: signed safety-status webhook to the parent app. Default OFF (SAFETY_STATUS_WEBHOOK). Never carries answers, tiers, free text, discloser identity or rationale."""
import asyncio
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from html import escape

import httpx
from fastapi import APIRouter, Depends, HTTPException

from core import EXTERNAL_APP_URL, db, logger
from email_utils import EMAIL_FROM_NAME, send_email

WEBHOOK_ENABLED = os.environ.get("SAFETY_STATUS_WEBHOOK", "false").lower() == "true"
WEBHOOK_PATH = "/api/internal/safety-status"
VERSION = "1"
RETRY_DELAYS = (1, 3, 9)
MODE_MAP = {"standard": "standard", "structured": "structured", "protected_review": "protected"}
ALLOWED_KEYS = {"case_id", "safety_mode", "set_by", "professional_name", "referral", "screening_offered", "version", "timestamp"}


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def build_payload(case_id: str, pathway: str | None, professional_name: str) -> dict:
    mode = MODE_MAP.get(pathway or "standard", "standard")
    return {"case_id": case_id, "safety_mode": mode, "set_by": "professional", "professional_name": professional_name,
            "referral": mode != "standard", "screening_offered": True, "version": VERSION, "timestamp": datetime.now(timezone.utc).isoformat()}


async def _alert_admin(case_id: str, status: str) -> None:
    admin = os.environ.get("ADMIN_EMAIL")
    if not admin:
        return
    try:
        await send_email(to=admin, subject=f"Safety-status webhook failed - {EMAIL_FROM_NAME}",
                         html=f"<p>The signed safety-status post for case {escape(case_id[:8])} failed after {len(RETRY_DELAYS)} attempts ({escape(status)}). No case content is included in this alert.</p>",
                         case_id=case_id, kind="webhook_failure_alert", to_role="Admin")
    except Exception:
        logger.warning("webhook failure alert not sent for case %s", case_id)


async def deliver(payload: dict) -> dict:
    assert set(payload) == ALLOWED_KEYS
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    secret = os.environ.get("ALIGN_WEBHOOK_SECRET", "")
    rec = {"id": str(uuid.uuid4()), "case_id": payload["case_id"], "safety_mode": payload["safety_mode"], "at": payload["timestamp"], "attempts": 0, "status": "pending"}
    if not secret:
        rec["status"] = "skipped_no_secret"
        await db.webhook_deliveries.insert_one({**rec})
        return rec
    headers = {"Content-Type": "application/json", "X-Align-Signature": sign(secret, body), "X-Align-Timestamp": payload["timestamp"], "X-Align-Version": VERSION}
    for i, delay in enumerate(RETRY_DELAYS):
        rec["attempts"] = i + 1
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{EXTERNAL_APP_URL}{WEBHOOK_PATH}", content=body, headers=headers)
            rec["last_status"] = resp.status_code
            if resp.status_code < 300:
                rec["status"] = "delivered"
                break
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                rec["status"] = f"rejected_{resp.status_code}"
                break
        except Exception as e:
            rec["last_status"] = type(e).__name__
        if i < len(RETRY_DELAYS) - 1:
            await asyncio.sleep(delay)
    if rec["status"] == "pending":
        rec["status"] = "failed"
    if rec["status"] != "delivered":
        await _alert_admin(payload["case_id"], str(rec.get("last_status")))
    await db.webhook_deliveries.insert_one({**rec})
    return rec


def notify_safety_mode(case_id: str, pathway: str | None, professional_name: str) -> None:
    """Fire-and-forget; no-op while the flag is OFF."""
    if not WEBHOOK_ENABLED:
        return
    asyncio.create_task(deliver(build_payload(case_id, pathway, professional_name)))


def build_router(get_current_user) -> APIRouter:
    r = APIRouter()

    @r.get("/admin/safety-status-webhook")
    async def status(user=Depends(get_current_user)):
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        recent = await db.webhook_deliveries.find({}, {"_id": 0}).sort("at", -1).to_list(25)
        return {"enabled": WEBHOOK_ENABLED, "secret_configured": bool(os.environ.get("ALIGN_WEBHOOK_SECRET")), "target": f"{EXTERNAL_APP_URL}{WEBHOOK_PATH}", "version": VERSION, "recent": recent}

    return r
