"""Special Needs Co-Parenting — independent invite + neutral comparison.

Mounted at /api/snc (extension to the SNC product routes).

Design contract:
  * Independent accounts: the invitee's SNC assessment is entirely their own.
    Neither parent ever sees the other's raw answers or narratives.
  * Section 11 (Family Violence & Communication Safety) responses are NEVER
    included in the comparison payload.
  * Comparison uses only structured category scores + category classifications;
    verbatim narrative/open-text fields are NOT copied across.
  * Comparison never picks a winner and never labels either parent right/wrong.

Endpoints:
  POST   /snc/invite/coparent                     (auth)
  GET    /snc/invite/mine                         (auth)
  GET    /snc/invite/by-token/{token}             (public)
  POST   /snc/invite/accept/{token}               (auth)
  POST   /snc/invite/{invite_id}/resend           (auth)
  DELETE /snc/invite/{invite_id}                  (auth)
  GET    /snc/comparison/{invite_id}              (auth — either linked parent)
  POST   /snc/comparison/{invite_id}/regenerate   (auth — either linked parent)
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

import email_service
from auth import UserPublic, get_current_user, get_db
from snc_comparison import compare_reports
from snc_comparison_pdf import build_snc_comparison_pdf


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/snc", tags=["snc-invite"])

INVITES = "snc_invites"
REPORTS = "snc_reports"
COMPARISONS = "snc_comparisons"

INVITE_LIFETIME_DAYS = int(os.environ.get("SNC_INVITE_LIFETIME_DAYS", "60"))
INVITE_RATE_LIMIT_PER_DAY = int(os.environ.get("SNC_INVITE_PER_DAY", "5"))
INVITE_RESEND_MIN_INTERVAL_SECONDS = 5 * 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _frontend_origin(request: Request) -> str:
    public = (os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")
    if public:
        return public
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if origin:
        m = re.match(r"^(https?://[^/]+)", origin)
        if m:
            return m.group(1)
    return ""


def _serialize_invite(doc: Dict[str, Any], *, viewer_id: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "invite_id": doc.get("invite_id"),
        "from_user_id": doc.get("from_user_id"),
        "from_name": doc.get("from_name"),
        "invitee_email": doc.get("invitee_email"),
        "status": doc.get("status"),
        "created_at": doc.get("created_at"),
        "last_sent_at": doc.get("last_sent_at"),
        "accepted_at": doc.get("accepted_at"),
        "accepted_by_user_id": doc.get("accepted_by_user_id"),
        "expires_at": doc.get("expires_at"),
    }
    if viewer_id and viewer_id == doc.get("from_user_id"):
        out["direction"] = "sent"
        # Only the inviter gets the raw token back so they can copy/share it.
        out["token"] = doc.get("token")
    elif viewer_id and viewer_id == doc.get("accepted_by_user_id"):
        out["direction"] = "received"
    return out


class SNCInviteCreate(BaseModel):
    email: EmailStr


# ============ Invite endpoints ============
@router.post("/invite/coparent")
async def create_snc_invite(
    body: SNCInviteCreate,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Create an SNC invite and email a one-tap link to the co-parent."""
    invitee_email = _normalize_email(body.email)
    if not invitee_email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if invitee_email == _normalize_email(current.email):
        raise HTTPException(status_code=400, detail="You can't invite yourself.")

    # Rate limit per day per inviter.
    since = _now() - timedelta(days=1)
    same_day = await db[INVITES].count_documents({
        "from_user_id": current.user_id,
        "created_at": {"$gte": _iso(since)},
    })
    if same_day >= INVITE_RATE_LIMIT_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Daily invite limit reached ({INVITE_RATE_LIMIT_PER_DAY}). "
                   f"Please try again tomorrow.",
        )

    # Reuse a pending invite to the same address instead of stacking duplicates.
    existing = await db[INVITES].find_one({
        "from_user_id": current.user_id,
        "invitee_email": invitee_email,
        "status": {"$in": ["pending", "accepted"]},
    })
    if existing and existing.get("status") == "accepted":
        raise HTTPException(status_code=409, detail="This co-parent already accepted your invite.")
    if existing:
        invite = existing
    else:
        token = secrets.token_urlsafe(24)
        invite = {
            "invite_id": f"snci_{uuid.uuid4().hex[:12]}",
            "token": token,
            "from_user_id": current.user_id,
            "from_email": _normalize_email(current.email),
            "from_name": current.name,
            "invitee_email": invitee_email,
            "status": "pending",
            "created_at": _iso(_now()),
            "expires_at": _iso(_now() + timedelta(days=INVITE_LIFETIME_DAYS)),
            "last_sent_at": None,
        }
        await db[INVITES].insert_one(invite)

    origin = _frontend_origin(request)
    accept_url = f"{origin}/special-needs/invite/{invite['token']}"
    sent = False
    if email_service.is_configured():
        try:
            email_service.send_snc_coparent_invite(
                to_email=invitee_email,
                inviter_name=current.name,
                accept_url=accept_url,
            )
            sent = True
        except Exception:  # noqa: BLE001
            logger.exception("SNC invite email failed for %s", invitee_email)

    now_iso = _iso(_now())
    await db[INVITES].update_one(
        {"invite_id": invite["invite_id"]},
        {"$set": {"last_sent_at": now_iso}},
    )
    invite["last_sent_at"] = now_iso

    return {
        "sent": sent,
        "invite": _serialize_invite(invite, viewer_id=current.user_id),
        "accept_url": accept_url,
        "reason": None if sent else "The invite was created, but the email couldn't be delivered right now. Share the link directly.",
    }


@router.get("/invite/mine")
async def list_my_snc_invites(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    sent_cur = db[INVITES].find({"from_user_id": current.user_id}).sort("created_at", -1)
    sent = [_serialize_invite(d, viewer_id=current.user_id) async for d in sent_cur]
    received_cur = db[INVITES].find({"accepted_by_user_id": current.user_id}).sort("created_at", -1)
    received = [_serialize_invite(d, viewer_id=current.user_id) async for d in received_cur]
    return {"sent": sent, "received": received}


@router.get("/invite/by-token/{token}")
async def get_snc_invite_by_token(token: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[INVITES].find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Invite not found or has expired.")
    if doc.get("expires_at") and doc["expires_at"] < _iso(_now()):
        return {"status": "expired", "from_name": doc.get("from_name"), "invitee_email": doc.get("invitee_email")}
    return {
        "status": doc.get("status"),
        "from_name": doc.get("from_name"),
        "invitee_email": doc.get("invitee_email"),
        "invite_id": doc.get("invite_id"),
    }


@router.post("/invite/accept/{token}")
async def accept_snc_invite(
    token: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[INVITES].find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Invite not found.")
    if doc.get("from_user_id") == current.user_id:
        raise HTTPException(status_code=400, detail="You can't accept your own invite.")
    if doc.get("expires_at") and doc["expires_at"] < _iso(_now()):
        raise HTTPException(status_code=410, detail="This invite has expired. Please ask your co-parent to send a new one.")
    if doc.get("status") == "accepted" and doc.get("accepted_by_user_id") != current.user_id:
        raise HTTPException(status_code=409, detail="This invite has already been accepted by another account.")

    now_iso = _iso(_now())
    updates = {
        "status": "accepted",
        "accepted_by_user_id": current.user_id,
        "accepted_at": doc.get("accepted_at") or now_iso,
    }
    await db[INVITES].update_one({"invite_id": doc["invite_id"]}, {"$set": updates})
    doc.update(updates)
    return {"ok": True, "invite": _serialize_invite(doc, viewer_id=current.user_id)}


@router.post("/invite/{invite_id}/resend")
async def resend_snc_invite(
    invite_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[INVITES].find_one({"invite_id": invite_id, "from_user_id": current.user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Invite not found.")
    if doc.get("status") == "accepted":
        raise HTTPException(status_code=400, detail="This invite has already been accepted.")
    last_iso = doc.get("last_sent_at")
    if last_iso:
        last_dt = datetime.fromisoformat(last_iso)
        if (_now() - last_dt).total_seconds() < INVITE_RESEND_MIN_INTERVAL_SECONDS:
            raise HTTPException(status_code=429, detail="Please wait a few minutes before resending.")
    origin = _frontend_origin(request)
    accept_url = f"{origin}/special-needs/invite/{doc['token']}"
    sent = False
    if email_service.is_configured():
        try:
            email_service.send_snc_coparent_invite(
                to_email=doc["invitee_email"],
                inviter_name=current.name,
                accept_url=accept_url,
            )
            sent = True
        except Exception:  # noqa: BLE001
            logger.exception("SNC invite resend failed for %s", doc.get("invitee_email"))
    now_iso = _iso(_now())
    await db[INVITES].update_one({"invite_id": invite_id}, {"$set": {"last_sent_at": now_iso}})
    return {"sent": sent, "invite_id": invite_id, "accept_url": accept_url}


@router.delete("/invite/{invite_id}")
async def revoke_snc_invite(
    invite_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    result = await db[INVITES].delete_one({"invite_id": invite_id, "from_user_id": current.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invite not found.")
    await db[COMPARISONS].delete_many({"invite_id": invite_id})
    return {"ok": True}


# ============ Comparison endpoints ============
async def _load_report(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db[REPORTS].find_one({"user_id": user_id}, {"_id": 0})


async def _load_user_name(db: AsyncIOMotorDatabase, user_id: str) -> str:
    doc = await db["users"].find_one({"user_id": user_id}, {"_id": 0, "full_name": 1, "name": 1, "email": 1})
    if not doc:
        return "Parent"
    return doc.get("full_name") or doc.get("name") or doc.get("email") or "Parent"


async def _authorised_invite(
    db: AsyncIOMotorDatabase, invite_id: str, viewer_id: str,
) -> Dict[str, Any]:
    doc = await db[INVITES].find_one({"invite_id": invite_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Invite not found.")
    if viewer_id not in (doc.get("from_user_id"), doc.get("accepted_by_user_id")):
        raise HTTPException(status_code=403, detail="You don't have access to this comparison.")
    return doc


async def _build_comparison(
    db: AsyncIOMotorDatabase, invite: Dict[str, Any],
) -> Dict[str, Any]:
    parent_a_id = invite["from_user_id"]
    parent_b_id = invite.get("accepted_by_user_id")
    if not parent_b_id:
        raise HTTPException(status_code=409, detail="Waiting for your co-parent to accept the invite.")

    report_a = await _load_report(db, parent_a_id)
    report_b = await _load_report(db, parent_b_id)
    if not report_a or not report_b:
        missing_side = "you" if not report_a else "your co-parent"
        if not report_a and not report_b:
            missing_side = "both parents"
        raise HTTPException(status_code=409, detail=f"Waiting for the report from {missing_side}.")

    name_a = await _load_user_name(db, parent_a_id)
    name_b = await _load_user_name(db, parent_b_id)

    payload = compare_reports(
        parent_a_name=name_a,
        parent_b_name=name_b,
        report_a=report_a.get("report") or {},
        report_b=report_b.get("report") or {},
    )
    payload["source_updated"] = {
        "a": report_a.get("generated_at"),
        "b": report_b.get("generated_at"),
    }
    doc_out = {
        "invite_id": invite["invite_id"],
        "generated_at": payload["generated_at"],
        "source_updated": payload["source_updated"],
        "comparison": payload,
    }
    await db[COMPARISONS].replace_one({"invite_id": invite["invite_id"]}, doc_out, upsert=True)
    doc_out.pop("_id", None)
    return doc_out


def _is_comparison_stale(cached: Dict[str, Any], report_a: Dict[str, Any], report_b: Dict[str, Any]) -> bool:
    if not cached:
        return True
    src = cached.get("source_updated") or {}
    return (
        (src.get("a") or "") != (report_a.get("generated_at") or "")
        or (src.get("b") or "") != (report_b.get("generated_at") or "")
    )


@router.get("/comparison/{invite_id}")
async def get_comparison(
    invite_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    invite = await _authorised_invite(db, invite_id, current.user_id)
    cached = await db[COMPARISONS].find_one({"invite_id": invite_id}, {"_id": 0})
    parent_a_id = invite["from_user_id"]
    parent_b_id = invite.get("accepted_by_user_id")

    report_a = await _load_report(db, parent_a_id) if parent_a_id else None
    report_b = await _load_report(db, parent_b_id) if parent_b_id else None

    if not (report_a and report_b):
        return {
            "invite": _serialize_invite(invite, viewer_id=current.user_id),
            "ready": False,
            "missing": {
                "a_report": report_a is None,
                "b_report": report_b is None,
                "b_accepted": parent_b_id is not None,
            },
            "comparison": None,
        }

    if not cached or _is_comparison_stale(cached, report_a, report_b):
        doc = await _build_comparison(db, invite)
    else:
        doc = cached

    return {
        "invite": _serialize_invite(invite, viewer_id=current.user_id),
        "ready": True,
        "cached": bool(cached) and not _is_comparison_stale(cached, report_a, report_b),
        "generated_at": doc.get("generated_at"),
        "comparison": doc.get("comparison"),
    }


@router.post("/comparison/{invite_id}/regenerate")
async def regenerate_comparison(
    invite_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    invite = await _authorised_invite(db, invite_id, current.user_id)
    doc = await _build_comparison(db, invite)
    return {
        "invite": _serialize_invite(invite, viewer_id=current.user_id),
        "ready": True,
        "cached": False,
        "generated_at": doc.get("generated_at"),
        "comparison": doc.get("comparison"),
    }


def _safe_filename(name: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in (name or "report")).strip("_")
    return out or "report"


@router.get("/comparison/{invite_id}/pdf")
async def download_comparison_pdf(
    invite_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Download the neutral side-by-side as a branded PDF.

    Either linked parent may download. The PDF renderer never receives
    Section 11 (safety) data because the caller strips it before caching —
    ``snc_comparison.compare_reports`` skips ``s11`` entirely.
    """
    invite = await _authorised_invite(db, invite_id, current.user_id)
    cached = await db[COMPARISONS].find_one({"invite_id": invite_id}, {"_id": 0})
    parent_a_id = invite["from_user_id"]
    parent_b_id = invite.get("accepted_by_user_id")
    report_a = await _load_report(db, parent_a_id) if parent_a_id else None
    report_b = await _load_report(db, parent_b_id) if parent_b_id else None
    if not (report_a and report_b):
        raise HTTPException(status_code=409, detail="Both parents must complete their assessments first.")
    if not cached or _is_comparison_stale(cached, report_a, report_b):
        cached = await _build_comparison(db, invite)

    pdf_bytes = build_snc_comparison_pdf(comparison=cached.get("comparison") or {})
    a_name = ((cached.get("comparison") or {}).get("parents") or {}).get("a", {}).get("name") or "Parent_A"
    b_name = ((cached.get("comparison") or {}).get("parents") or {}).get("b", {}).get("name") or "Parent_B"
    filename = f"SNC_Comparison_{_safe_filename(a_name)}_vs_{_safe_filename(b_name)}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
