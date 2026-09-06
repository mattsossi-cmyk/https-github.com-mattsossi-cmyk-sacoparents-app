"""Invite Co-parent flow.

Lets a signed-in parent email a one-tap link inviting their co-parent to prep
for mediation **independently** (separate, private account). The inviter sees a
list of sent invites with delivery status (sent / opened / signed up).

Design choices (confirmed with user):
  - Invitee gets a brand-new, **independent** account — never shares prep data
    with the inviter, never sees their answers.
  - Email-only invite (no custom note in v1 — keeps the email body universally
    polite, avoids accidental venting in an estranged-couple context).
  - Rate limit: 3 invites per inviter per 24h.

Endpoints:
  - POST /api/invites/coparent                          (auth)
  - GET  /api/invites/coparent                          (auth)
  - POST /api/invites/coparent/resend/{invite_id}       (auth)
  - GET  /api/invites/coparent/by-token/{token}         (public)
  - POST /api/invites/coparent/accept/{token}           (public)
"""
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

import email_service
from auth import (
    _set_jwt_cookie,
    _serialize_user,
    create_jwt,
    get_current_user,
    get_db,
    hash_password,
)
from models import TokenResponse, UserPublic
from safety_gate import require_ipv_clearance, ipv_gate_status


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invites", tags=["invites"])

INVITE_RATE_LIMIT_PER_DAY = int(os.environ.get("COPARENT_INVITE_PER_DAY", "3"))
INVITE_LIFETIME_DAYS = int(os.environ.get("COPARENT_INVITE_LIFETIME_DAYS", "30"))
# How often (seconds) we'll allow a resend on the same invite (avoid mash-spam).
INVITE_RESEND_MIN_INTERVAL_SECONDS = 5 * 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _frontend_origin(request: Request) -> str:
    """Best-effort origin for building the public invite link."""
    public = (os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")
    if public:
        return public
    # Fall back to the Origin/Referer header so it works in any deployment.
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if origin:
        # Strip path if it was a referer
        m = re.match(r"^(https?://[^/]+)", origin)
        if m:
            return m.group(1)
    return ""


def _invite_to_public_dict(doc: dict) -> dict:
    return {
        "invite_id": doc.get("invite_id"),
        "invitee_email": doc.get("invitee_email"),
        "status": _effective_status(doc),
        "created_at": doc.get("created_at"),
        "last_sent_at": doc.get("last_sent_at"),
        "opened_at": doc.get("opened_at"),
        "signed_up_at": doc.get("signed_up_at"),
    }


def _effective_status(doc: dict) -> str:
    """Return the *observed* status, expiring pending invitations that are
    past their `expires_at`. Founder rule (2026-03-04): a pending invite
    that runs out its lifetime is presumed rejected — never re-issuable."""
    status = doc.get("status") or "pending"
    if status != "pending":
        return status
    exp_iso = doc.get("expires_at")
    if not exp_iso:
        return status
    try:
        exp = datetime.fromisoformat(exp_iso)
    except (TypeError, ValueError):
        return status
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= _now():
        return "expired"
    return status


# ============ Pydantic bodies ============
class CoparentInviteRequest(BaseModel):
    email: EmailStr


class CoparentInviteAccept(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


# ============ Auth endpoints ============
@router.post("/coparent")
async def send_coparent_invite(
    body: CoparentInviteRequest,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send (or re-use) an invite to the given co-parent email."""
    # Demo (guest) accounts can invite a co-parent too — the recipient signs up
    # as their own permanent account, completely independent of the demo.
    # When the guest later claims their own account, both halves persist.
    if current.is_guest and not current.email:
        raise HTTPException(
            status_code=400,
            detail="Demo sessions can't send invites without an email address.",
        )
    invitee = _normalize_email(body.email)
    if not invitee:
        raise HTTPException(status_code=400, detail="Please enter a valid email.")
    if invitee == _normalize_email(current.email or ""):
        raise HTTPException(
            status_code=400,
            detail="That's your own email — try your co-parent's address instead.",
        )

    # Founder safety guardrail (2026-03-04): every parent-to-co-parent invitation
    # must be gated on the family-violence safety screen. Raises 403 with a
    # structured `code`+`message` payload when the parent has not completed
    # the screen or is at Level 1/2.
    await require_ipv_clearance(db, current.user_id)

    # Founder single-invite rule (2026-03-04): a parent gets ONE lifetime
    # invitation to their co-parent. If it hasn't been accepted within the
    # invitation lifetime it is presumed rejected — no further outreach
    # is permitted from this app. Resends to the SAME still-pending
    # recipient remain OK (they don't create a new invite).
    prior = await db.coparent_invites.find_one(
        {"inviter_user_id": current.user_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if prior:
        prior_status = _effective_status(prior)
        same_recipient = _normalize_email(prior.get("invitee_email") or "") == invitee
        if prior_status == "signed_up":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Your co-parent has already accepted the invitation."
                ),
            )
        if prior_status in ("expired", "rejected"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Your previous invitation was not accepted within the "
                    f"{INVITE_LIFETIME_DAYS}-day window and is now closed. "
                    "Only one invitation is permitted between parents through this app."
                ),
            )
        if not same_recipient:
            raise HTTPException(
                status_code=400,
                detail=(
                    "You already have a pending invitation to another co-parent email. "
                    "Only one invitation is permitted between parents through this app."
                ),
            )

    existing = prior if (prior and _normalize_email(prior.get("invitee_email") or "") == invitee) else None

    if existing:
        # Resend gate: too-soon resends are a no-op (still return success so the
        # UI shows the same confirmation but we don't actually re-email).
        last_sent = existing.get("last_sent_at")
        if last_sent:
            try:
                gap = (_now() - datetime.fromisoformat(last_sent)).total_seconds()
                if gap < INVITE_RESEND_MIN_INTERVAL_SECONDS:
                    return {"ok": True, "invite": _invite_to_public_dict(existing), "resent": False}
            except (TypeError, ValueError):
                pass
        invite = existing
        token = invite["token"]
    else:
        # Don't let users invite an email that is already a permanent account
        # of their own — that would just funnel them to their own login screen.
        target = await db.users.find_one(
            {"email": invitee, "is_guest": {"$ne": True}},
            {"_id": 0, "user_id": 1},
        )
        if target and target.get("user_id") == current.user_id:
            raise HTTPException(
                status_code=400,
                detail="That's your own account — try your co-parent's address instead.",
            )
        token = secrets.token_urlsafe(32)
        invite = {
            "invite_id": f"inv_{uuid.uuid4().hex[:12]}",
            "token": token,
            "inviter_user_id": current.user_id,
            "inviter_name": current.name or "",
            "inviter_email": current.email,
            "invitee_email": invitee,
            "status": "pending",
            "created_at": _iso(_now()),
            "expires_at": _iso(_now() + timedelta(days=INVITE_LIFETIME_DAYS)),
            "last_sent_at": None,
            "opened_at": None,
            "signed_up_at": None,
            "signed_up_user_id": None,
        }
        await db.coparent_invites.insert_one(invite.copy())

    origin = _frontend_origin(request)
    link_url = f"{origin}/invite/{token}" if origin else f"/invite/{token}"
    try:
        email_service.send_coparent_invite(
            to_email=invitee,
            link_url=link_url,
            inviter_name=current.name or "",
        )
    except email_service.EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Email isn't configured yet. Please try again in a moment.",
        )
    except email_service.EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    await db.coparent_invites.update_one(
        {"token": token},
        {"$set": {"last_sent_at": _iso(_now())}},
    )

    fresh = await db.coparent_invites.find_one({"token": token}, {"_id": 0})
    return {"ok": True, "invite": _invite_to_public_dict(fresh), "resent": bool(existing)}


@router.get("/coparent")
async def list_my_invites(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.coparent_invites.find(
        {"inviter_user_id": current.user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(50)
    rows = [
        _invite_to_public_dict(doc) async for doc in cursor
    ]
    # Founder single-invite rule (2026-03-04): expose whether the parent
    # has used their lifetime invitation so the UI can hide the form and
    # show the current status instead of a fresh input.
    invite_used = bool(rows)
    latest_status = rows[0]["status"] if rows else None
    can_send_new = not invite_used  # once used, no new invitations
    return {
        "invites": rows,
        "invite_used": invite_used,
        "latest_status": latest_status,
        "can_send_new": can_send_new,
        "policy": "one_invite_per_parent_lifetime",
    }


@router.get("/coparent/gate")
async def coparent_invite_gate(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Non-raising status of the family-violence safety gate.

    The Invite Co-Parent UIs call this on mount so they can render a
    "complete the safety screen first" prompt (or a compassionate
    resources card at Level 1/2) instead of surfacing an email input
    the parent will then be blocked from submitting.
    """
    return await ipv_gate_status(db, current.user_id)


@router.post("/coparent/resend/{invite_id}")
async def resend_coparent_invite(
    invite_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    invite = await db.coparent_invites.find_one(
        {"invite_id": invite_id, "inviter_user_id": current.user_id}, {"_id": 0}
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found.")
    status = _effective_status(invite)
    if status == "signed_up":
        raise HTTPException(
            status_code=400,
            detail="This co-parent has already accepted your invite.",
        )
    if status in ("expired", "rejected"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"This invitation ran out its {INVITE_LIFETIME_DAYS}-day window and "
                "is now closed. Only one invitation is permitted between parents."
            ),
        )
    # Re-route through the create endpoint logic for the resend gate / email.
    return await send_coparent_invite(
        CoparentInviteRequest(email=invite["invitee_email"]),
        request,
        current,
        db,
    )


# ============ Public endpoints (token-based, no login) ============
@router.get("/coparent/by-token/{token}")
async def fetch_coparent_invite(token: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.coparent_invites.find_one({"token": token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="This invite link is no longer valid.")
    # Expired?
    try:
        if datetime.fromisoformat(doc["expires_at"]) <= _now():
            raise HTTPException(
                status_code=410,
                detail="This invite link has expired. Ask your co-parent to send a new one.",
            )
    except (TypeError, ValueError):
        pass
    # First-touch tracking: mark opened the first time the recipient loads it.
    if not doc.get("opened_at"):
        await db.coparent_invites.update_one(
            {"token": token},
            {
                "$set": {
                    "opened_at": _iso(_now()),
                    # Only bump status if we haven't already advanced past it.
                    "status": "opened" if doc.get("status") == "pending" else doc.get("status"),
                }
            },
        )
    return {
        "inviter_name": doc.get("inviter_name") or "Your co-parent",
        "invitee_email": doc.get("invitee_email"),
        "status": doc.get("status"),
        "already_accepted": doc.get("status") == "signed_up",
    }


@router.post("/coparent/accept/{token}", response_model=TokenResponse)
async def accept_coparent_invite(
    token: str,
    response: Response,
    body: CoparentInviteAccept = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    invite = await db.coparent_invites.find_one({"token": token}, {"_id": 0})
    if not invite:
        raise HTTPException(status_code=404, detail="This invite link is no longer valid.")
    try:
        if datetime.fromisoformat(invite["expires_at"]) <= _now():
            raise HTTPException(status_code=410, detail="This invite link has expired.")
    except (TypeError, ValueError):
        pass
    if invite.get("status") == "signed_up":
        raise HTTPException(
            status_code=409,
            detail="An account has already been created from this invite. Please sign in instead.",
        )

    email = _normalize_email(invite["invitee_email"])
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing and not existing.get("is_guest"):
        raise HTTPException(
            status_code=400,
            detail="An account already exists for this email. Please sign in instead.",
        )

    user_id = uuid.uuid4().hex
    doc = {
        "user_id": user_id,
        "email": email,
        "name": body.name.strip(),
        "hashed_password": hash_password(body.password),
        "auth_method": "jwt",
        "children": [],
        "custody_situation": "",
        "mediation_date": None,
        "picture": None,
        "email_verified": True,  # Email ownership proven via the invite link.
        "invited_by_user_id": invite.get("inviter_user_id"),
        "created_at": _iso(_now()),
    }
    await db.users.insert_one(doc.copy())
    await db.coparent_invites.update_one(
        {"token": token},
        {
            "$set": {
                "status": "signed_up",
                "signed_up_at": _iso(_now()),
                "signed_up_user_id": user_id,
            }
        },
    )

    jwt_token = create_jwt(user_id)
    _set_jwt_cookie(response, jwt_token)
    return TokenResponse(access_token=jwt_token, user=_serialize_user(doc))
