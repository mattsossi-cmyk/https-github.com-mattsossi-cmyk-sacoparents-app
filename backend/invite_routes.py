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
        "status": doc.get("status"),
        "created_at": doc.get("created_at"),
        "last_sent_at": doc.get("last_sent_at"),
        "opened_at": doc.get("opened_at"),
        "signed_up_at": doc.get("signed_up_at"),
    }


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

    # Rate-limit: 3 fresh invites per 24h (resends of an existing invite don't count).
    day_ago = _iso(_now() - timedelta(days=1))
    fresh_today = await db.coparent_invites.count_documents({
        "inviter_user_id": current.user_id,
        "created_at": {"$gte": day_ago},
    })

    existing = await db.coparent_invites.find_one(
        {"inviter_user_id": current.user_id, "invitee_email": invitee},
        {"_id": 0},
    )

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
        if fresh_today >= INVITE_RATE_LIMIT_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"You've sent {INVITE_RATE_LIMIT_PER_DAY} invites in the last 24 hours. "
                    "Please try again tomorrow."
                ),
            )
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
    return {"invites": rows, "rate_limit_per_day": INVITE_RATE_LIMIT_PER_DAY}


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
    if invite.get("status") == "signed_up":
        raise HTTPException(
            status_code=400,
            detail="This co-parent has already accepted your invite.",
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
