"""Texas HB 300 (Medical Records Privacy Act) compliance endpoints.

HB 300 — codified as the Texas Medical Records Privacy Act at Tex.
Health & Safety Code Ch. 181 — extends HIPAA for Texas residents. This
module implements the *user-facing* pieces we owe:

  * POST /api/me/hb300/acknowledge      — captures the parent's dated
    receipt of the HB 300 Notice at signup (or later). §181.154 style
    notice of electronic disclosure.
  * POST /api/me/hb300/marketing        — opt-in / opt-out of marketing
    communications. Default is OFF per §181.152.
  * POST /api/me/hb300/access-request   — 15-business-day right-of-
    access clock per §181.102. Instant fulfilment via /me/export, but
    the formal request is recorded so we can prove compliance.
  * GET  /api/me/hb300/status           — current consent + request state.
  * POST /api/admin/breach-report       — admin-only draft of a breach
    notification. Emails OPERATOR_EMAIL. Never sends to end users
    automatically — the runbook requires human review first.

Everything is written to Mongo through the same `PROTECTED_VARIABLES`
env vars used by the rest of the app.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from auth import UserPublic, get_current_user, get_db
from phi_access_routes import record_phi_access


router = APIRouter(tags=["hb300"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Hb300AckPayload(BaseModel):
    """Body of the HB 300 acknowledgement request.

    We keep the version explicit so we can reissue the notice later
    (e.g. Texas amends the statute) and force a re-acknowledgement.
    """
    notice_version: str = Field(default="2026-02-21")


class MarketingConsentPayload(BaseModel):
    opt_in: bool


class AccessRequestPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)
    delivery_email: Optional[EmailStr] = None


class BreachReportPayload(BaseModel):
    """Admin-only breach draft. Every field is required so the runbook
    can be filled out completely before human review."""
    summary: str = Field(min_length=20, max_length=4000)
    discovered_at: datetime
    texas_residents_affected: int = Field(ge=0)
    phi_categories: str = Field(min_length=3, max_length=500)
    remediation: str = Field(min_length=10, max_length=4000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HB300_ACK_COLL = "hb300_acknowledgements"
_HB300_REQUEST_COLL = "hb300_access_requests"
_BREACH_COLL = "hb300_breach_reports"


def _add_business_days(start: datetime, days: int) -> datetime:
    """Return `start` + `days` business days (Mon–Fri). Naive but
    sufficient for a 15-day HB 300 SLA — we intentionally do NOT
    subtract federal holidays; the runbook allows the operator to
    respond earlier, and HB 300 §181.102 is silent on holidays."""
    result = start
    added = 0
    while added < days:
        result = result + timedelta(days=1)
        if result.weekday() < 5:  # 0=Mon, 6=Sun
            added += 1
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/me/hb300/acknowledge")
async def acknowledge_hb300(
    body: Hb300AckPayload,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Record the caller's receipt of the HB 300 Notice.

    Idempotent — repeat calls with the same `notice_version` update the
    timestamp. A different version stacks as a new row so we can prove
    the whole history if audited.
    """
    now = datetime.now(timezone.utc)
    row = {
        "user_id":         user.user_id,
        "email":           user.email,
        "notice_version":  body.notice_version,
        "acknowledged_at": now,
        "ip":              request.client.host if request.client else None,
        "user_agent":      request.headers.get("user-agent"),
    }
    await db[_HB300_ACK_COLL].update_one(
        {"user_id": user.user_id, "notice_version": body.notice_version},
        {"$set": row},
        upsert=True,
    )
    # Mirror on the user document so admin views and export dumps can
    # show the current state without a second lookup.
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "hb300_ack_version": body.notice_version,
            "hb300_ack_at":      now.isoformat(),
        }},
    )
    await record_phi_access(
        db, user_id=user.user_id, action="hb300_ack",
        resource_type="hb300_notice", resource_id=body.notice_version,
        request=request,
    )
    return {"ok": True, "acknowledged_at": now.isoformat(), "notice_version": body.notice_version}


@router.post("/me/hb300/marketing")
async def set_marketing_consent(
    body: MarketingConsentPayload,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Set the caller's marketing-communications opt-in state.

    HB 300 §181.152 requires affirmative opt-in for marketing that
    uses PHI. Default is OFF; this endpoint is the only way to flip
    the flag on. The change is written to `phi_access_log` so an
    auditor can reconstruct the exact moment of opt-in / opt-out.
    """
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "marketing_opt_in":    bool(body.opt_in),
            "marketing_updated_at": now.isoformat(),
        }},
    )
    await record_phi_access(
        db, user_id=user.user_id,
        action="marketing_opt_in" if body.opt_in else "marketing_opt_out",
        resource_type="user_preferences", request=request,
    )
    return {"ok": True, "opt_in": bool(body.opt_in), "updated_at": now.isoformat()}


@router.post("/me/hb300/access-request")
async def submit_hb300_access_request(
    body: AccessRequestPayload,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Formal HB 300 §181.102 15-business-day access request.

    Fulfilment is usually instant — the same data is available via
    `GET /api/me/export`. Filing this endpoint gives the parent a
    paper-trail if they ever need to prove they asked. The response
    includes the SLA deadline so downstream UIs can render it.
    """
    now = datetime.now(timezone.utc)
    due = _add_business_days(now, 15)
    row = {
        "user_id":         user.user_id,
        "email":           user.email,
        "delivery_email":  body.delivery_email or user.email,
        "reason":          body.reason,
        "requested_at":    now,
        "sla_due_at":      due,
        "status":          "received",
        "ip":              request.client.host if request.client else None,
    }
    result = await db[_HB300_REQUEST_COLL].insert_one(row)
    await record_phi_access(
        db, user_id=user.user_id, action="hb300_access_request",
        resource_type="phi_bundle", resource_id=str(result.inserted_id),
        request=request,
    )
    return {
        "ok":              True,
        "requested_at":    now.isoformat(),
        "sla_due_at":      due.isoformat(),
        "self_serve_url":  "/api/me/export",
        "message":         "Your request is on file. You can also download your data instantly from the Data & Retention page.",
    }


@router.get("/me/hb300/status")
async def get_hb300_status(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the caller's HB 300 posture: acknowledgement state,
    marketing opt-in, and any outstanding access requests."""
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0}) or {}
    ack = await db[_HB300_ACK_COLL].find_one(
        {"user_id": user.user_id},
        {"_id": 0},
        sort=[("acknowledged_at", -1)],
    )
    pending = await db[_HB300_REQUEST_COLL].count_documents(
        {"user_id": user.user_id, "status": "received"},
    )
    return {
        "hb300_ack_version":  user_doc.get("hb300_ack_version"),
        "hb300_ack_at":       user_doc.get("hb300_ack_at"),
        "marketing_opt_in":   bool(user_doc.get("marketing_opt_in", False)),
        "latest_ack":         ack,
        "pending_access_requests": pending,
    }


@router.get("/me/hb300/consent-history")
async def get_consent_history(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the caller's marketing consent + HB 300 acknowledgement
    history, newest-first. Powers the "See my consent history" modal
    on the account page so parents have a self-serve paper trail
    for every HB 300 §181.152 (marketing) and §181.154 (notice)
    event on their record.

    Rows are read directly from `phi_access_log` where they were
    written by `POST /api/me/hb300/marketing` and
    `POST /api/me/hb300/acknowledge`. No new writes — we're just
    exposing what the caller already generated about themselves.
    """
    cursor = db.phi_access_log.find(
        {
            "user_id": user.user_id,
            "action":  {"$in": ["marketing_opt_in", "marketing_opt_out",
                                "hb300_ack"]},
        },
        {"_id": 0, "user_id": 0},
    ).sort("at", -1).limit(200)
    events: list = []
    async for row in cursor:
        at = row.get("at")
        events.append({
            "action":     row.get("action"),
            "at":         at.isoformat() if hasattr(at, "isoformat") else at,
            "ip":         row.get("ip"),
            "user_agent": row.get("user_agent"),
            "resource_id": row.get("resource_id"),  # notice_version on hb300_ack rows
        })
    return {"events": events, "total": len(events)}


@router.post("/admin/breach-report")
async def submit_breach_report(
    body: BreachReportPayload,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Admin-only draft of a HB 300 breach notification.

    * Stores the draft in `hb300_breach_reports`.
    * Emails a copy to `OPERATOR_EMAIL` (the account listed in .env).
    * Does NOT notify affected users automatically — the runbook
      requires human review to avoid mis-scoped or premature notices.
    * Flags whether the Texas AG threshold (≥ 250 Texas residents)
      has been crossed so the operator sees it immediately.
    """
    # Admin gate — the app's admin-scope collections mark elevated
    # accounts with `role="admin"` or `is_admin=True` on the user
    # document (NOT the UserPublic wire shape, which intentionally
    # strips those fields). We look up the Mongo row directly so the
    # gate can never be bypassed by whatever fields `UserPublic`
    # happens to expose. The `OPERATOR_EMAIL` fallback lets the
    # single-owner deployment work out-of-the-box.
    operator_email = (os.environ.get("OPERATOR_EMAIL") or "").strip().lower()
    is_operator = operator_email and (user.email or "").lower() == operator_email
    is_admin = bool(is_operator)
    if not is_admin:
        user_doc = await db.users.find_one(
            {"user_id": user.user_id},
            {"_id": 0, "role": 1, "is_admin": 1},
        ) or {}
        is_admin = (
            user_doc.get("role") == "admin"
            or bool(user_doc.get("is_admin", False))
        )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin only.")

    now = datetime.now(timezone.utc)
    ag_threshold_crossed = body.texas_residents_affected >= 250
    row = {
        "summary":                  body.summary,
        "discovered_at":            body.discovered_at,
        "texas_residents_affected": body.texas_residents_affected,
        "phi_categories":           body.phi_categories,
        "remediation":              body.remediation,
        "ag_threshold_crossed":     ag_threshold_crossed,
        "drafted_by":               user.user_id,
        "drafted_at":               now,
        "status":                   "draft",
    }
    result = await db[_BREACH_COLL].insert_one(row)

    # Best-effort operator email — never blocks the primary write.
    try:
        from email_service import send_operator_notification  # type: ignore
        send_operator_notification(
            subject=f"[HB 300 DRAFT] Breach report — {body.texas_residents_affected} TX residents",
            body=(
                f"Discovered: {body.discovered_at.isoformat()}\n"
                f"Texas residents affected: {body.texas_residents_affected}\n"
                f"Texas AG threshold crossed (>=250): {ag_threshold_crossed}\n"
                f"PHI categories: {body.phi_categories}\n\n"
                f"Summary:\n{body.summary}\n\n"
                f"Remediation:\n{body.remediation}\n"
            ),
        )
    except Exception:  # noqa: BLE001 — best-effort notification
        pass

    return {
        "ok":                     True,
        "breach_id":              str(result.inserted_id),
        "drafted_at":             now.isoformat(),
        "ag_threshold_crossed":   ag_threshold_crossed,
        "next_steps": [
            "Review the draft with legal counsel.",
            "Confirm the 60-day notification clock started at discovered_at.",
            "If ag_threshold_crossed is true, file with the Texas Attorney General without unreasonable delay.",
            "Prepare the user-facing notification (60-day deadline).",
            "Log final decisions and post-mortem in the runbook.",
        ],
    }
