"""
Professionals directory + parent-initiated "send my alignment code to
a professional" flow.

Endpoints (all under `/api`):

  * GET  /professionals
        Public. Returns the curated list of professionals a parent
        can request a Joint Alignment Report from. Sourced from the
        `professionals` collection; seeded on first read with the
        initial roster (Matt Sossi).

  * POST /professionals/{professional_id}/send-alignment-code
        Parent JWT required. Mints a fresh alignment code tagged
        with the professional_id + assessment_type + optional short
        parent message, then emails the professional with the code.
        Returns the minted code so the parent's UI can also display
        it as a fallback.

Design notes
------------
* Directory seeding is idempotent: the first `GET` after a fresh
  deploy inserts the initial roster if the collection is empty.
  Later additions come from the DB (or a future admin endpoint).
* The email delivery to the professional uses the existing Resend
  transport (`email_service._send`) — no new secrets required.
  Delivery is best-effort: an SMTP outage does not fail the mint.
* The code itself piggybacks on the parent-driven link-code
  infrastructure in `integration_routes.py` — one shared TTL, one
  shared hash, one shared normalisation. We simply inject the
  professional context tag before the doc is inserted.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from auth import UserPublic, get_current_user, get_db
import integration_routes as ir
import email_service


router = APIRouter(tags=["professionals"])
logger = logging.getLogger(__name__)

_COLL = "professionals"

# Initial roster — seeded on first read of an empty collection.
# Later additions can flow through an admin endpoint or a database
# migration; the roster here is intentionally minimal so a fresh
# deploy always has at least one professional the parent can pick.
_INITIAL_ROSTER: List[Dict[str, Any]] = [
    {
        "professional_id": "matt-sossi",
        "name": "Matt Sossi",
        "credentials": (
            "San Antonio Attorney, Family Law Mediator, Parent Facilitator"
        ),
        "license": "Licensed to Practice in the State of Texas",
        "email": "mattsossi@bsossi.com",
        "address_lines": [
            "16607 Blanco #703",
            "San Antonio, Texas 78205",
        ],
        "city": "San Antonio",
        "state": "TX",
        "phone": None,
        "website": None,
        "active": True,
        "sort_order": 0,
        "bio": (
            "Family-law mediation and parent facilitation focused on "
            "child-centered outcomes and structured co-parenting agreements."
        ),
    },
]

# ASSESSMENT_TYPE strings mirror the constant used across
# joint_alignment_routes / integration_routes.
_ASSESSMENT_LABELS = {
    "co-parenting": "Co-Parenting Assessment",
    "communication": "Communication Assessment",
    "educational": "Educational Needs Assessment",
    "medical": "Medical Needs Assessment",
    "psychological": "Psychological / Emotional Needs Assessment",
    "special-needs": "Special Needs Assessment",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _ensure_seeded(db: AsyncIOMotorDatabase) -> None:
    count = await db[_COLL].estimated_document_count()
    if count > 0:
        return
    docs = []
    for entry in _INITIAL_ROSTER:
        docs.append({**entry, "created_at": _now(), "updated_at": _now()})
    if docs:
        try:
            await db[_COLL].insert_many(docs)
            logger.info("professionals directory seeded (%s entries)", len(docs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("professionals seed skipped: %s", exc)


def _public_shape(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Public projection — everything a parent needs to identify the
    professional. Email is public since the whole point of the
    directory is to allow parents to send a request to it.
    """
    return {
        "professional_id": p.get("professional_id"),
        "name": p.get("name"),
        "credentials": p.get("credentials"),
        "license": p.get("license"),
        "email": p.get("email"),
        "phone": p.get("phone"),
        "website": p.get("website"),
        "address_lines": p.get("address_lines") or [],
        "city": p.get("city"),
        "state": p.get("state"),
        "bio": p.get("bio"),
    }


# ------------------------------- schemas ------------------------------- #

class SendCodeRequest(BaseModel):
    assessment_type: str = Field(..., min_length=1, max_length=40)
    parent_message: Optional[str] = Field(default=None, max_length=1000)


class SendCodeResponse(BaseModel):
    code: str
    professional: Dict[str, Any]
    delivered: bool
    delivered_error: Optional[str] = None
    expires_at: str


# ------------------------------- endpoints ------------------------------- #

@router.get("/professionals")
async def list_professionals(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Public listing. Only active professionals are returned; ordered
    by `sort_order` then by name so the initial roster's ordering
    stays stable.
    """
    await _ensure_seeded(db)
    cursor = db[_COLL].find({"active": True}).sort([("sort_order", 1), ("name", 1)])
    professionals = [_public_shape(p) async for p in cursor]
    return {"professionals": professionals}


@router.post(
    "/professionals/{professional_id}/send-alignment-code",
    response_model=SendCodeResponse,
)
async def send_alignment_code_to_professional(
    body: SendCodeRequest,
    request: Request,
    professional_id: str = Path(..., min_length=1, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Parent-authenticated. Mints a fresh alignment code, tags it with
    the chosen professional + assessment_type + optional parent note,
    and sends an email to the professional with the code embedded.

    Best-effort email delivery — a Resend outage MUST NOT prevent
    the parent from seeing the code in the UI.
    """
    if current.is_guest:
        raise HTTPException(status_code=403, detail="Guest accounts cannot send codes")

    await _ensure_seeded(db)
    professional = await db[_COLL].find_one(
        {"professional_id": professional_id, "active": True}
    )
    if not professional:
        raise HTTPException(status_code=404, detail="Professional not found")

    # Rate limit — reuse the same 5/hr guard as parent-driven mints.
    if await ir._mint_rate_limited(db, current.user_id):
        raise HTTPException(
            status_code=429,
            detail=f"Please wait — you can mint up to {ir._MINT_RATE_LIMIT_PER_HOUR} codes per hour.",
        )

    # Supersede any outstanding unused codes so the freshest one is
    # the only one that verifies. Matches the parent-driven flow.
    await db[ir._COLL].update_many(
        {"user_id": current.user_id, "consumed_at": None},
        {"$set": {"consumed_at": _now(), "consumed_reason": "superseded"}},
    )

    code = ir._generate_code()
    expires_at = _now() + timedelta(minutes=ir._CODE_TTL_MINUTES)
    context = f"prof:{professional_id}:{body.assessment_type}"
    await db[ir._COLL].insert_one(
        {
            "user_id": current.user_id,
            "email": current.email,
            "code_hash": ir._hash_code(code),
            "context": context,
            "minted_at": _now(),
            "expires_at": expires_at,
            "consumed_at": None,
            "consumed_reason": None,
            "ip": request.client.host if request.client else None,
            # Extra metadata so audit logs can attribute the code to
            # a professional-directed request.
            "professional_id": professional_id,
            "assessment_type": body.assessment_type,
            "parent_message": (body.parent_message or "").strip()[:1000] or None,
        }
    )
    logger.info(
        "professional alignment-code minted user=%s professional=%s",
        current.user_id,
        professional_id,
    )

    delivered = True
    delivered_error: Optional[str] = None
    try:
        _send_professional_email(
            professional=professional,
            parent_name=current.name or current.email,
            parent_email=current.email,
            assessment_type=body.assessment_type,
            code=code,
            parent_message=(body.parent_message or "").strip() or None,
        )
    except email_service.EmailNotConfigured:
        delivered = False
        delivered_error = "Email delivery is not configured on this environment."
        logger.warning("professional email skipped — Resend not configured")
    except Exception as exc:  # noqa: BLE001
        delivered = False
        delivered_error = "Email delivery failed. Please try again in a moment."
        logger.exception("professional email delivery failed: %s", exc)

    return SendCodeResponse(
        code=code,
        professional=_public_shape(professional),
        delivered=delivered,
        delivered_error=delivered_error,
        expires_at=expires_at.astimezone(timezone.utc).isoformat(),
    )


# ------------------------------- email template ------------------------------- #

def _send_professional_email(
    *,
    professional: Dict[str, Any],
    parent_name: str,
    parent_email: str,
    assessment_type: str,
    code: str,
    parent_message: Optional[str],
) -> None:
    assessment_label = _ASSESSMENT_LABELS.get(assessment_type, assessment_type)
    align_base = os.environ.get(
        "ALIGN_JOIN_URL_BASE", "https://sacoparentsalign.com/join"
    ).rstrip("/")
    join_url = f"{align_base}/{code}"
    subject = (
        f"SA CoParents Alignment Code: {parent_name} — {assessment_label}"
    )

    body_html = (
        f"<p>{_html_escape(parent_name)} has completed the "
        f"<strong>{_html_escape(assessment_label)}</strong> in SA CoParents "
        "and would like to invite you to prepare a Joint Alignment Report.</p>"
        f"<p><strong>Alignment Code:</strong> <code style=\"font-size:16px;"
        "font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
        f"background:#F8F7FC;padding:4px 10px;border-radius:6px;color:#3D1A78\">{code}</code></p>"
        f"<p>Enter the code on <a href=\"{join_url}\">SA CoParents Align</a> "
        "to open the case, then invite the co-parent to complete their "
        "individual assessment.</p>"
        "<p>Individual responses remain private. The Joint Alignment "
        "Report is prepared only after both parents have completed the "
        "same assessment.</p>"
    )
    if parent_message:
        body_html += (
            f"<p style=\"border-left:3px solid #3D1A78;padding-left:12px;"
            "color:#4B4567\"><em>Message from "
            f"{_html_escape(parent_name)}:</em><br/>"
            f"{_html_escape(parent_message)}</p>"
        )

    html = email_service._branded_html(
        headline="Joint Alignment Request",
        body_html=body_html,
        cta_label="Open on SA CoParents Align",
        cta_url=join_url,
    )
    text_lines = [
        f"{parent_name} has completed the {assessment_label} in SA CoParents",
        "and would like to invite you to prepare a Joint Alignment Report.",
        "",
        f"Alignment Code: {code}",
        f"Open on SA CoParents Align: {join_url}",
        "",
        "Individual responses remain private. The Joint Alignment Report is",
        "prepared only after both parents have completed the same assessment.",
    ]
    if parent_message:
        text_lines += ["", f"Message from {parent_name}:", parent_message]

    email_service._send(
        to_email=professional["email"],
        subject=subject,
        html=html,
        text="\n".join(text_lines),
        reply_to=parent_email,
    )


def _html_escape(v: str) -> str:
    return (
        (v or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
