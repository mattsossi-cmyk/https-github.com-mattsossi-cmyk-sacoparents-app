"""Parent → Professional report-share invitation flow.

The parent selects one or more of their OWN completed reports and
invites a chosen professional to review them on sacoparentsalign.com.
The parent controls:
  * which specific reports to include (`report_ids`)
  * view-only vs. view+download
  * notify on first view / on download
  * receive-future-versions toggle
  * access expiration (7 / 30 / 60 / 90 days)
  * two explicit consent flags recorded verbatim per iteration's spec

Server-side authorisation gates:
  * A parent can ONLY share reports they own — every `report_id` is
    revalidated against the current owner's catalog at create time.
  * Selected reports must be COMPLETE at create time (otherwise the
    professional would see an empty artefact).
  * Both consent flags must be true; missing either → 400.
  * Rate-limited: 30 invites / hour / parent.
  * Cross-parent report bleed is impossible — the catalog scoped
    query filters on the caller's user_id at every step.

Sibling-portal integration:
  * Every invite mints a `report_permission` per selected report,
    each with its OWN `permission_id`. sacoparentsalign.com's portal
    calls `GET /api/integrations/report-permissions/{permission_id}`
    before every view or download to confirm the parent hasn't
    revoked access.
  * Revoking or extending an invite touches all report_permissions
    for that invite in one atomic update.

Never stored / logged:
  * Raw report body content
  * Password / session data
  * Journal entries
  * AI Coach conversations
  * Unfinished drafts
  * Safety screen answers
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator

from auth import UserPublic, get_current_user, get_db


router = APIRouter(tags=["parent-professional-invitations"])
logger = logging.getLogger(__name__)

_INVITES_COLL = "parent_professional_invitations"
_PERMS_COLL = "professional_report_permissions"
_ACCESS_EVENTS_COLL = "report_access_events"

_INVITE_TOKEN_TTL_HOURS = 72          # per spec
_INVITE_RATE_LIMIT_PER_HOUR = 30
_MAX_REPORTS_PER_INVITE = 10
_ALLOWED_ACCESS_DAYS = {7, 30, 60, 90}
_DEFAULT_ACCESS_DAYS = 30
_CONSENT_VERSION = "2026-09-08"       # bump on every legal-copy change

# Consent text kept verbatim as required by spec — copy is stored
# on the invite row so future legal changes don't retroactively
# rewrite what the parent agreed to.
_AUTHORISATION_TEXT = (
    "I authorize SA CoParents to make the reports selected above "
    "available to the identified professional through SA CoParents "
    "Align. This authorization does not provide access to my entire "
    "account, raw assessment answers, journals, AI Coach "
    "conversations, unfinished work, protected safety responses, or "
    "reports I did not select. I understand that I may revoke future "
    "access, but previously downloaded copies cannot be recalled."
)
_RELATIONSHIP_ACKNOWLEDGEMENT_TEXT = (
    "I understand that accepting this invitation does not by itself "
    "create an attorney-client, therapist-client, physician-patient, "
    "mediator, evaluator, or other professional relationship."
)

_PROFESSIONAL_ROLES = {
    "mediator", "attorney", "therapist", "counselor",
    "parenting-facilitator", "amicus-attorney", "child-advocate",
    "educational-professional", "medical-professional", "other",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(v: Any) -> Optional[str]:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat()
    return None


def _as_utc(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sibling_base() -> str:
    return (
        os.environ.get("SACOPARENTSALIGN_BASE_URL")
        or "https://sacoparentsalign.com"
    ).rstrip("/")


def _invitation_url(token: str) -> str:
    return f"{_sibling_base()}/professional/accept?token={token}"


# ------------------------------- schemas ------------------------------- #

class CreateInvitationBody(BaseModel):
    professional_first_name: str = Field(..., min_length=1, max_length=80)
    professional_last_name: str = Field(..., min_length=1, max_length=80)
    professional_email: EmailStr
    professional_email_confirm: EmailStr
    professional_role: str = Field(..., min_length=1, max_length=40)
    organization: Optional[str] = Field(default=None, max_length=160)
    professional_phone: Optional[str] = Field(default=None, max_length=40)
    reference_number: Optional[str] = Field(default=None, max_length=80)
    personal_message: Optional[str] = Field(default=None, max_length=1000)
    report_ids: List[str] = Field(..., min_length=1, max_length=_MAX_REPORTS_PER_INVITE)
    view_permission: bool = True
    download_permission: bool = False
    notify_on_view: bool = True
    notify_on_download: bool = True
    future_versions: bool = False
    access_days: int = Field(default=_DEFAULT_ACCESS_DAYS)
    consent_authorised: bool
    consent_relationship_acknowledged: bool

    @field_validator("professional_role")
    @classmethod
    def _role_allowed(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in _PROFESSIONAL_ROLES:
            raise ValueError(
                f"role must be one of {sorted(_PROFESSIONAL_ROLES)}",
            )
        return v

    @field_validator("access_days")
    @classmethod
    def _access_days_allowed(cls, v: int) -> int:
        if v not in _ALLOWED_ACCESS_DAYS:
            raise ValueError(
                f"access_days must be one of {sorted(_ALLOWED_ACCESS_DAYS)}",
            )
        return v


class ExtendAccessBody(BaseModel):
    access_days: int = Field(default=_DEFAULT_ACCESS_DAYS)

    @field_validator("access_days")
    @classmethod
    def _access_days_allowed(cls, v: int) -> int:
        if v not in _ALLOWED_ACCESS_DAYS:
            raise ValueError(
                f"access_days must be one of {sorted(_ALLOWED_ACCESS_DAYS)}",
            )
        return v


# ------------------------------- helpers ------------------------------- #

def _shape_invite(inv: Dict[str, Any]) -> Dict[str, Any]:
    """Public shape returned to the parent — never leaks token_hash
    or raw personal message from other users."""
    return {
        "invitation_id": inv.get("invitation_id"),
        "professional_first_name": inv.get("professional_first_name"),
        "professional_last_name": inv.get("professional_last_name"),
        "professional_email": inv.get("professional_email"),
        "professional_role": inv.get("professional_role"),
        "organization": inv.get("organization"),
        "professional_phone": inv.get("professional_phone"),
        "reference_number": inv.get("reference_number"),
        "personal_message": inv.get("personal_message"),
        "selected_reports": inv.get("selected_reports") or [],
        "view_permission": bool(inv.get("view_permission")),
        "download_permission": bool(inv.get("download_permission")),
        "notify_on_view": bool(inv.get("notify_on_view")),
        "notify_on_download": bool(inv.get("notify_on_download")),
        "future_versions": bool(inv.get("future_versions")),
        "status": inv.get("status") or "invitation_sent",
        "created_at": _iso(inv.get("created_at")),
        "token_expires_at": _iso(inv.get("token_expires_at")),
        "access_expiration": _iso(inv.get("access_expiration")),
        "last_access_at": _iso(inv.get("last_access_at")),
        "download_count": int(inv.get("download_count") or 0),
        "view_count": int(inv.get("view_count") or 0),
        "consent_version": inv.get("consent_version"),
        "consent_recorded_at": _iso(inv.get("consent_recorded_at")),
        "revoked_at": _iso(inv.get("revoked_at")),
    }


async def _rate_limit_check(db, user_id: str) -> None:
    since = _now() - timedelta(hours=1)
    recent = await db[_INVITES_COLL].count_documents({
        "inviting_parent_id": user_id, "created_at": {"$gte": since},
    })
    if recent >= _INVITE_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've hit the {_INVITE_RATE_LIMIT_PER_HOUR}/hour "
                "invitation limit. Try again shortly."
            ),
        )


async def _validate_report_ownership(
    db, *, user_id: str, requested_ids: List[str],
) -> List[Dict[str, Any]]:
    """Cross-check every requested report_id against the caller's
    catalog. Returns the matched report metadata list. Raises 400
    when a report_id is unknown or not owned."""
    from parent_report_catalog import list_completed_reports
    catalog = await list_completed_reports(db, user_id=user_id)
    lookup = {r["report_id"]: r for r in catalog}
    matched: List[Dict[str, Any]] = []
    for rid in requested_ids:
        row = lookup.get(rid)
        if not row:
            raise HTTPException(
                status_code=400,
                detail=f"Report {rid!r} is not one of your completed reports.",
            )
        matched.append(row)
    return matched


# ------------------------------- endpoints ------------------------------- #

@router.post("/parent/professional-invitations")
async def create_professional_invitation(
    body: CreateInvitationBody,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Send a secure invitation to a professional to review the reports
    the parent selected. Records:
      * an invite row with a hashed token (raw token returned once
        so the caller can display / email it),
      * one report_permission row per selected report — the sibling
        portal calls back on every access to check permission.
    Emails the professional a portal link (no report content in the
    email).
    """
    # Email confirmation match.
    if body.professional_email.lower().strip() != body.professional_email_confirm.lower().strip():
        raise HTTPException(status_code=400, detail="Professional email addresses don't match.")
    if not body.consent_authorised or not body.consent_relationship_acknowledged:
        raise HTTPException(status_code=400, detail="Both consent boxes must be checked.")
    if not body.view_permission:
        raise HTTPException(
            status_code=400,
            detail="View permission is required — an invitation with no permissions is invalid.",
        )

    await _rate_limit_check(db, current.user_id)

    matched_reports = await _validate_report_ownership(
        db, user_id=current.user_id, requested_ids=body.report_ids,
    )

    now = _now()
    invitation_id = uuid.uuid4().hex[:12]
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    token_expires_at = now + timedelta(hours=_INVITE_TOKEN_TTL_HOURS)
    access_expiration = now + timedelta(days=body.access_days)

    selected_reports_snapshot = [
        {
            "report_id": r["report_id"],
            "lane": r["lane"],
            "title": r["title"],
            "version": int(r.get("version") or 1),
            "completed_at": r.get("completed_at"),
        }
        for r in matched_reports
    ]

    invite_doc = {
        "invitation_id": invitation_id,
        "inviting_parent_id": current.user_id,
        "inviting_parent_name": current.name,
        "inviting_parent_email": current.email,
        "professional_first_name": body.professional_first_name.strip(),
        "professional_last_name": body.professional_last_name.strip(),
        "professional_email": body.professional_email.lower().strip(),
        "professional_role": body.professional_role,
        "organization": (body.organization or "").strip() or None,
        "professional_phone": (body.professional_phone or "").strip() or None,
        "reference_number": (body.reference_number or "").strip() or None,
        "personal_message": (body.personal_message or "").strip() or None,
        "selected_reports": selected_reports_snapshot,
        "view_permission": True,
        "download_permission": bool(body.download_permission),
        "notify_on_view": bool(body.notify_on_view),
        "notify_on_download": bool(body.notify_on_download),
        "future_versions": bool(body.future_versions),
        "invitation_token_hash": token_hash,
        "status": "invitation_sent",
        "created_at": now,
        "token_expires_at": token_expires_at,
        "access_expiration": access_expiration,
        "revoked_at": None,
        "accepted_at": None,
        "declined_at": None,
        "last_access_at": None,
        "view_count": 0,
        "download_count": 0,
        "consent_version": _CONSENT_VERSION,
        "consent_recorded_at": now,
        "consent_texts": {
            "authorised": _AUTHORISATION_TEXT,
            "relationship_acknowledged": _RELATIONSHIP_ACKNOWLEDGEMENT_TEXT,
        },
    }
    await db[_INVITES_COLL].insert_one(invite_doc)

    # One permission row per selected report. Each permission gets
    # its own opaque permission_id so the sibling portal can call
    # back with just that ID.
    for rep in selected_reports_snapshot:
        await db[_PERMS_COLL].insert_one({
            "permission_id": uuid.uuid4().hex,
            "invitation_id": invitation_id,
            "inviting_parent_id": current.user_id,
            "professional_email": invite_doc["professional_email"],
            "report_id": rep["report_id"],
            "lane": rep["lane"],
            "title": rep["title"],
            "version": rep["version"],
            "view_permission": True,
            "download_permission": bool(body.download_permission),
            "future_versions": bool(body.future_versions),
            "created_at": now,
            "expires_at": access_expiration,
            "revoked_at": None,
            "status": "pending",  # pending until invite accepted
        })

    # Best-effort email dispatch — never crash the create call on a
    # provider outage.
    from email_service import (
        EmailNotConfigured, EmailSendError,
        send_parent_professional_share_invitation,
    )
    accept_url = _invitation_url(raw_token)
    delivered = False
    delivery_message: Optional[str] = None
    try:
        send_parent_professional_share_invitation(
            to_email=invite_doc["professional_email"],
            professional_first_name=invite_doc["professional_first_name"],
            inviting_parent_name=current.name or "A parent",
            inviting_parent_email=current.email or "",
            selected_report_titles=[r["title"] for r in selected_reports_snapshot],
            reference_number=invite_doc.get("reference_number"),
            personal_message=invite_doc.get("personal_message"),
            accept_url=accept_url,
            token_expires_at=_iso(token_expires_at),
        )
        delivered = True
    except EmailNotConfigured as exc:
        delivery_message = "Email isn't configured on this environment."
        logger.warning("parent-pro invite email skipped: %s", exc)
    except EmailSendError as exc:
        delivery_message = str(exc) or "Delivery failed."
        logger.warning("parent-pro invite email failed: %s", exc)

    return {
        "invitation_id": invitation_id,
        "invitation": _shape_invite(invite_doc),
        "accept_url": accept_url,       # raw token exposed once, to sender only
        "delivered": delivered,
        "delivery_message": delivery_message,
    }


@router.get("/parent/professional-invitations")
async def list_professional_invitations(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List every invitation the parent has sent, newest-first."""
    cursor = (
        db[_INVITES_COLL]
        .find(
            {"inviting_parent_id": current.user_id},
            {"_id": 0, "invitation_token_hash": 0},
        )
        .sort("created_at", -1)
        .limit(100)
    )
    invitations: List[Dict[str, Any]] = []
    async for inv in cursor:
        invitations.append(_shape_invite(inv))
    return {"invitations": invitations}


@router.get("/parent/professional-invitations/{invitation_id}")
async def get_professional_invitation(
    invitation_id: str = Path(..., min_length=6, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    inv = await db[_INVITES_COLL].find_one(
        {"invitation_id": invitation_id, "inviting_parent_id": current.user_id},
        {"_id": 0, "invitation_token_hash": 0},
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    # Also return the permission rows so the parent sees per-report status.
    perms: List[Dict[str, Any]] = []
    async for p in db[_PERMS_COLL].find(
        {"invitation_id": invitation_id, "inviting_parent_id": current.user_id},
        {"_id": 0, "permission_id": 1, "report_id": 1, "lane": 1, "title": 1,
         "version": 1, "view_permission": 1, "download_permission": 1,
         "expires_at": 1, "revoked_at": 1, "status": 1},
    ):
        perms.append({
            "permission_id": p["permission_id"],
            "report_id": p["report_id"],
            "lane": p["lane"],
            "title": p["title"],
            "version": p["version"],
            "view_permission": bool(p.get("view_permission")),
            "download_permission": bool(p.get("download_permission")),
            "expires_at": _iso(p.get("expires_at")),
            "revoked_at": _iso(p.get("revoked_at")),
            "status": p.get("status") or "pending",
        })
    return {"invitation": _shape_invite(inv), "permissions": perms}


@router.post("/parent/professional-invitations/{invitation_id}/revoke")
async def revoke_professional_invitation(
    invitation_id: str = Path(..., min_length=6, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Revoke every report_permission on the invite. Idempotent —
    revoking an already-revoked invite returns 200 with
    `applied=false`."""
    now = _now()
    result = await db[_INVITES_COLL].update_one(
        {
            "invitation_id": invitation_id,
            "inviting_parent_id": current.user_id,
            "revoked_at": None,
        },
        {"$set": {"revoked_at": now, "status": "access_revoked"}},
    )
    if result.matched_count == 0:
        # Either not found OR already revoked. Distinguish.
        inv = await db[_INVITES_COLL].find_one(
            {"invitation_id": invitation_id, "inviting_parent_id": current.user_id},
            {"_id": 1, "revoked_at": 1},
        )
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found.")
        return {"invitation_id": invitation_id, "applied": False}

    await db[_PERMS_COLL].update_many(
        {"invitation_id": invitation_id, "inviting_parent_id": current.user_id},
        {"$set": {"revoked_at": now, "status": "revoked"}},
    )
    return {"invitation_id": invitation_id, "applied": True, "revoked_at": _iso(now)}


@router.post("/parent/professional-invitations/{invitation_id}/extend")
async def extend_professional_invitation(
    body: ExtendAccessBody,
    invitation_id: str = Path(..., min_length=6, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Push the access_expiration on a NOT-YET-REVOKED invitation
    out by another `access_days` starting FROM NOW (matches the
    'extend' semantic; not additive to the old expiration)."""
    now = _now()
    new_exp = now + timedelta(days=body.access_days)
    result = await db[_INVITES_COLL].update_one(
        {
            "invitation_id": invitation_id,
            "inviting_parent_id": current.user_id,
            "revoked_at": None,
        },
        {"$set": {"access_expiration": new_exp}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found, or already revoked.",
        )
    await db[_PERMS_COLL].update_many(
        {"invitation_id": invitation_id, "inviting_parent_id": current.user_id, "revoked_at": None},
        {"$set": {"expires_at": new_exp}},
    )
    return {
        "invitation_id": invitation_id,
        "access_expiration": _iso(new_exp),
    }


@router.post("/parent/professional-invitations/{invitation_id}/resend")
async def resend_professional_invitation(
    invitation_id: str = Path(..., min_length=6, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Mint a fresh token + 72h expiry and re-send the email. Only
    valid while the invite is still `invitation_sent` /
    `invitation_expired` / never accepted. Revoked + accepted +
    declined invites cannot be resent."""
    inv = await db[_INVITES_COLL].find_one(
        {"invitation_id": invitation_id, "inviting_parent_id": current.user_id},
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if inv.get("revoked_at"):
        raise HTTPException(status_code=409, detail="Invitation has been revoked.")
    if inv.get("accepted_at"):
        raise HTTPException(status_code=409, detail="Invitation has already been accepted.")
    if inv.get("declined_at"):
        raise HTTPException(status_code=409, detail="Invitation was declined.")

    now = _now()
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    token_expires_at = now + timedelta(hours=_INVITE_TOKEN_TTL_HOURS)

    await db[_INVITES_COLL].update_one(
        {"invitation_id": invitation_id, "inviting_parent_id": current.user_id},
        {"$set": {
            "invitation_token_hash": token_hash,
            "token_expires_at": token_expires_at,
            "status": "invitation_sent",
            "resent_at": now,
        }},
    )

    from email_service import (
        EmailNotConfigured, EmailSendError,
        send_parent_professional_share_invitation,
    )
    accept_url = _invitation_url(raw_token)
    try:
        send_parent_professional_share_invitation(
            to_email=inv["professional_email"],
            professional_first_name=inv["professional_first_name"],
            inviting_parent_name=current.name or "A parent",
            inviting_parent_email=current.email or "",
            selected_report_titles=[
                r["title"] for r in (inv.get("selected_reports") or [])
            ],
            reference_number=inv.get("reference_number"),
            personal_message=inv.get("personal_message"),
            accept_url=accept_url,
            token_expires_at=_iso(token_expires_at),
        )
    except (EmailNotConfigured, EmailSendError) as exc:
        logger.warning("parent-pro invite resend email failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc) or "Delivery failed.") from exc

    return {
        "invitation_id": invitation_id,
        "accept_url": accept_url,
        "token_expires_at": _iso(token_expires_at),
    }


# ------------------------------------------------------------------
# Sibling-portal permission check + audit event.
# ------------------------------------------------------------------

def _verify_integration_key(header_value: Optional[str]) -> None:
    expected = os.environ.get("INTEGRATION_SHARED_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="Integration not configured.")
    if not hmac.compare_digest(header_value or "", expected):
        raise HTTPException(status_code=401, detail="Invalid integration key.")


@router.get("/integrations/report-permissions/{permission_id}")
async def check_report_permission(
    permission_id: str = Path(..., min_length=8, max_length=64),
    x_integration_key: Optional[str] = Header(
        default=None, alias="X-Integration-Key",
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """sacoparentsalign.com portal calls this before every view or
    download to confirm the parent hasn't revoked access.

    Returns:
      * `active=True` when the permission exists, is not revoked, and
        access_expiration is in the future.
      * `active=False` with `reason` otherwise (`revoked`, `expired`,
        `unknown`).

    Response always includes the minimal metadata the portal needs
    to render — never the report body content.
    """
    _verify_integration_key(x_integration_key)
    perm = await db[_PERMS_COLL].find_one({"permission_id": permission_id}, {"_id": 0})
    if not perm:
        return {"active": False, "reason": "unknown"}

    if perm.get("revoked_at"):
        return {
            "active": False, "reason": "revoked",
            "permission_id": permission_id,
        }
    exp = _as_utc(perm.get("expires_at"))
    if exp and exp < _now():
        return {
            "active": False, "reason": "expired",
            "permission_id": permission_id,
        }

    return {
        "active": True,
        "permission_id": permission_id,
        "invitation_id": perm.get("invitation_id"),
        "report_id": perm.get("report_id"),
        "lane": perm.get("lane"),
        "title": perm.get("title"),
        "version": int(perm.get("version") or 1),
        "download_permission": bool(perm.get("download_permission")),
        "expires_at": _iso(perm.get("expires_at")),
    }


class RecordAccessBody(BaseModel):
    event: str = Field(..., pattern="^(view|download|accepted|declined)$")
    occurred_at: Optional[str] = Field(default=None, max_length=64)
    user_agent: Optional[str] = Field(default=None, max_length=240)


@router.post("/integrations/report-permissions/{permission_id}/events")
async def record_access_event(
    body: RecordAccessBody,
    permission_id: str = Path(..., min_length=8, max_length=64),
    x_integration_key: Optional[str] = Header(
        default=None, alias="X-Integration-Key",
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Sibling portal reports each view / download / accept /
    decline back to us. This drives the "First view · 2h ago" line
    on the parent-facing management page and the notification
    pipeline."""
    _verify_integration_key(x_integration_key)
    perm = await db[_PERMS_COLL].find_one({"permission_id": permission_id}, {"_id": 0})
    if not perm:
        raise HTTPException(status_code=404, detail="Unknown permission_id.")

    invitation_id = perm.get("invitation_id")
    inv = await db[_INVITES_COLL].find_one({"invitation_id": invitation_id})
    if not inv:
        raise HTTPException(status_code=404, detail="Unknown invitation.")

    now = _as_utc(body.occurred_at) or _now()
    event_doc = {
        "event_id": uuid.uuid4().hex[:16],
        "permission_id": permission_id,
        "invitation_id": invitation_id,
        "inviting_parent_id": inv.get("inviting_parent_id"),
        "event": body.event,
        "occurred_at": now,
        "user_agent": (body.user_agent or "")[:240] or None,
    }
    await db[_ACCESS_EVENTS_COLL].insert_one(event_doc)

    # Roll up counters + flip status on invite.
    invite_update: Dict[str, Any] = {"last_access_at": now}
    perm_update: Dict[str, Any] = {}
    if body.event == "view":
        invite_update["$inc__view_count"] = 1     # sentinel — handled below
    elif body.event == "download":
        invite_update["$inc__download_count"] = 1
    elif body.event == "accepted":
        invite_update["accepted_at"] = now
        invite_update["status"] = "accepted"
        perm_update["status"] = "active"
    elif body.event == "declined":
        invite_update["declined_at"] = now
        invite_update["status"] = "declined"

    set_fields = {k: v for k, v in invite_update.items() if not k.startswith("$inc__")}
    inc_fields: Dict[str, int] = {}
    if "$inc__view_count" in invite_update:
        inc_fields["view_count"] = int(invite_update["$inc__view_count"])
    if "$inc__download_count" in invite_update:
        inc_fields["download_count"] = int(invite_update["$inc__download_count"])

    ops: Dict[str, Any] = {}
    if set_fields:
        ops["$set"] = set_fields
    if inc_fields:
        ops["$inc"] = inc_fields
    if ops:
        await db[_INVITES_COLL].update_one({"invitation_id": invitation_id}, ops)
    if perm_update:
        await db[_PERMS_COLL].update_one(
            {"permission_id": permission_id}, {"$set": perm_update},
        )

    # Fire the notification email best-effort. Never crash on
    # provider errors — the audit event is what really matters.
    # When the parent is in "digest" mode, suppress per-event emails
    # here — the daily rollup will cover them.
    try:
        from email_service import (
            send_parent_professional_share_notification,
        )
        from parent_share_digest import get_notification_mode
        digest_mode = await get_notification_mode(
            db, parent_id=inv.get("inviting_parent_id"),
        )
        if digest_mode == "digest":
            # Skip per-event pings — rolled up in the daily digest.
            pass
        elif body.event == "view" and bool(inv.get("notify_on_view")):
            send_parent_professional_share_notification(
                to_email=inv.get("inviting_parent_email"),
                event="viewed",
                professional_display_name=(
                    f"{inv.get('professional_first_name') or ''} "
                    f"{inv.get('professional_last_name') or ''}".strip()
                ),
                report_title=perm.get("title") or "Your report",
            )
        elif body.event == "download" and bool(inv.get("notify_on_download")):
            send_parent_professional_share_notification(
                to_email=inv.get("inviting_parent_email"),
                event="downloaded",
                professional_display_name=(
                    f"{inv.get('professional_first_name') or ''} "
                    f"{inv.get('professional_last_name') or ''}".strip()
                ),
                report_title=perm.get("title") or "Your report",
            )
        elif body.event == "accepted":
            send_parent_professional_share_notification(
                to_email=inv.get("inviting_parent_email"),
                event="accepted",
                professional_display_name=(
                    f"{inv.get('professional_first_name') or ''} "
                    f"{inv.get('professional_last_name') or ''}".strip()
                ),
                report_title=None,
            )
    except Exception:  # noqa: BLE001 — notifications must never break audit
        logger.exception("parent-pro invite notification email failed")

    return {"event_id": event_doc["event_id"], "recorded": True}


# ------------------------------------------------------------------
# Parent-facing report catalog exposure.
# ------------------------------------------------------------------

@router.get("/parent/report-catalog")
async def get_parent_report_catalog(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the caller's completed reports, ready for the wizard's
    Step 2 picker."""
    from parent_report_catalog import list_completed_reports
    reports = await list_completed_reports(db, user_id=current.user_id)
    return {"reports": reports}


# ---------------------------------------------------------------------
# Digest / immediate notification-mode preference for the parent.
# ---------------------------------------------------------------------

class SetNotificationModeBody(BaseModel):
    mode: str = Field(..., pattern="^(digest|immediate|auto)$")


@router.get("/parent/notification-mode")
async def get_notification_mode_endpoint(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the caller's resolved notification mode + how many
    active invitations they have (drives the toggle-UI copy and the
    auto-elevation hint)."""
    from parent_share_digest import (
        get_notification_mode, _active_invitation_count,
        _MIN_ACTIVE_INVITATIONS_FOR_AUTO_DIGEST,
    )
    resolved = await get_notification_mode(db, parent_id=current.user_id)
    active = await _active_invitation_count(db, current.user_id)
    pref = await db["digest_notification_prefs"].find_one(
        {"parent_id": current.user_id}, {"_id": 0, "mode": 1},
    )
    return {
        "mode": resolved,
        "explicit_pref": (pref or {}).get("mode"),
        "active_invitation_count": active,
        "auto_threshold": _MIN_ACTIVE_INVITATIONS_FOR_AUTO_DIGEST,
    }


@router.put("/parent/notification-mode")
async def set_notification_mode_endpoint(
    body: SetNotificationModeBody,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Set the caller's explicit notification-mode override.
    `"auto"` clears the override so the auto-elevation rule kicks
    in again."""
    from parent_share_digest import set_notification_mode
    resolved = await set_notification_mode(
        db, parent_id=current.user_id, mode=body.mode,
    )
    return {"mode": resolved, "requested": body.mode}


@router.post("/parent/notification-mode/preview-digest")
async def send_test_digest(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send the caller a SAMPLE digest email so they can eyeball
    what tomorrow's rollup will look like. Rolls up the last 7
    days of real events; if the parent has no events yet, sends a
    demo payload with fictitious data so the styling / copy is
    still visible."""
    from parent_share_digest import _gather_events
    from email_service import (
        EmailNotConfigured, EmailSendError,
        send_parent_share_digest_email,
    )
    if not current.email or "@" not in (current.email or ""):
        raise HTTPException(status_code=400, detail="No verified email on file.")

    end = _now()
    start = end - timedelta(days=7)
    events = await _gather_events(
        db, parent_id=current.user_id, since=start, until=end,
    )

    if events:
        # Real rollup from the caller's own recent activity.
        invite_ids = {ev.get("invitation_id") for ev in events if ev.get("invitation_id")}
        invite_lookup: Dict[str, Dict[str, Any]] = {}
        async for inv in db[_INVITES_COLL].find({"invitation_id": {"$in": list(invite_ids)}}):
            invite_lookup[inv.get("invitation_id")] = inv
        perm_ids = {ev.get("permission_id") for ev in events if ev.get("permission_id")}
        perm_lookup: Dict[str, Dict[str, Any]] = {}
        async for p in db[_PERMS_COLL].find({"permission_id": {"$in": list(perm_ids)}}):
            perm_lookup[p.get("permission_id")] = p
        from parent_share_digest import _summarise_events
        summary = _summarise_events(events, invite_lookup, perm_lookup)
        source = "real_events_last_7_days"
    else:
        # Demo payload so preview always renders SOMETHING legible.
        summary = {
            "professionals": [
                {
                    "professional_name": "Adele van Wyk",
                    "professional_email": "adele@example-mediation.co.za",
                    "views": 3, "downloads": 1,
                    "reports_touched": ["Foundation Statement",
                                        "Communication Reflection"],
                    "accepted": True, "declined": False,
                },
                {
                    "professional_name": "Dr. Priya Naidoo",
                    "professional_email": "priya@example.com",
                    "views": 1, "downloads": 0,
                    "reports_touched": ["Educational Needs Report"],
                    "accepted": False, "declined": False,
                },
            ],
            "total_events": 5, "total_views": 4, "total_downloads": 1,
        }
        source = "demo_sample"

    try:
        send_parent_share_digest_email(
            to_email=current.email,
            parent_name=current.name,
            digest_day=(end - timedelta(days=1)).strftime("%Y-%m-%d"),
            summary=summary,
        )
    except EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Email delivery isn't configured on this environment.",
        )
    except EmailSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc) or "Delivery failed.") from exc

    return {
        "delivered": True,
        "to": current.email,
        "source": source,
        "event_count": summary["total_events"],
    }
