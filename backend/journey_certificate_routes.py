"""Individual Journey certificate sharing: email it to an accepted professional or the case-code co-parent.
Parents never type an address. The co-parent option is hidden when either parent is safety-flagged."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

import email_service
from auth import UserPublic, get_current_user, get_db
from child_needs_share_routes import PROVIDER_FILTER, _provider
from court_compare import _case_key, _coparent
from journey_summary_routes import CertificateIn, certificate_bytes
from self_assessment_reminders import is_safety_flagged

router = APIRouter(prefix="/journey-summary/certificate", tags=["journey-certificate"])
SHARES = "journey_certificate_shares"
COPARENT_ID = "coparent"


class Recipient(BaseModel):
    recipient_id: str
    name: str
    role_label: str
    email: str


class CertShare(BaseModel):
    share_id: str
    name: str
    role_label: str
    email: str
    sent_at: str


class SendIn(CertificateIn):
    recipient_id: str = Field(min_length=1, max_length=64)


async def _recipients(db: AsyncIOMotorDatabase, uid: str) -> List[Recipient]:
    out: List[Recipient] = []
    key = await _case_key(db, uid)
    other = await _coparent(db, uid, key) if key else None
    if other and not await is_safety_flagged(db, uid) and not await is_safety_flagged(db, other):
        co = await db.users.find_one({"user_id": other}, {"_id": 0, "name": 1, "email": 1}) or {}
        if co.get("email"):
            out.append(Recipient(recipient_id=COPARENT_ID, name=co.get("name") or "Your co-parent", role_label="Co-parent", email=co["email"]))
    seen = {r.email for r in out}
    cursor = db.parent_professional_invitations.find({"inviting_parent_id": uid, **PROVIDER_FILTER}, {"_id": 0}).sort("accepted_at", -1)
    async for doc in cursor:
        if doc["professional_email"] not in seen:
            seen.add(doc["professional_email"])
            p = _provider(doc)
            out.append(Recipient(recipient_id=p.provider_id, name=p.name, role_label=p.role_label, email=p.email))
    return out


@router.get("/recipients", response_model=List[Recipient])
async def list_recipients(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[Recipient]:
    return await _recipients(db, user.user_id)


@router.get("/shares", response_model=List[CertShare])
async def list_shares(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[CertShare]:
    docs = await db[SHARES].find({"user_id": user.user_id}, {"_id": 0}).sort("sent_at", -1).to_list(100)
    return [CertShare(**d) for d in docs]


@router.post("/send", response_model=CertShare)
async def send_certificate(
    body: SendIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CertShare:
    to = next((r for r in await _recipients(db, user.user_id) if r.recipient_id == body.recipient_id), None)
    if not to:
        raise HTTPException(404, "That person isn't available to send to.")
    pdf_bytes = await certificate_bytes(db, user.user_id, body.name)
    try:
        await run_in_threadpool(
            email_service.send_journey_certificate,
            to_email=to.email,
            recipient_name=to.name,
            parent_name=user.name or "A parent",
            parent_email=user.email,
            pdf_bytes=pdf_bytes,
        )
    except email_service.EmailNotConfigured:
        raise HTTPException(503, "Email sending isn't set up yet. Please try again later.")
    except email_service.EmailSendError as e:
        raise HTTPException(502, str(e))
    share = CertShare(share_id=uuid.uuid4().hex[:12], name=to.name, role_label=to.role_label, email=to.email, sent_at=datetime.now(timezone.utc).isoformat())
    await db[SHARES].insert_one({"user_id": user.user_id, "recipient_id": to.recipient_id, **share.model_dump()})
    return share
