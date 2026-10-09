"""Child Needs · email finished Educational / Medical / Psychological forms (PDF) to a
professional the parent already invited and who accepted. Parents never type an address."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

import child_needs_pdf
import email_service
from auth import UserPublic, get_current_user, get_db
from child_needs_routes import CONTENT, FIELDS, clean_category

router = APIRouter(prefix="/child-needs", tags=["child-needs-share"])

ROLE_LABELS = {
    "mediator": "Mediator",
    "attorney": "Attorney",
    "therapist": "Therapist / Counselor",
    "counselor": "Counselor",
    "parenting-facilitator": "Parenting Facilitator / Coordinator",
    "amicus-attorney": "Amicus Attorney",
    "child-advocate": "Child Advocate",
    "educational-professional": "Educational Professional",
    "medical-professional": "Medical Professional",
    "other": "Professional",
}
TITLES = {c["key"]: c["card_title"] for c in CONTENT["categories"]}
# Accepted at some point and not revoked by the parent.
PROVIDER_FILTER = {"accepted_at": {"$ne": None}, "status": {"$in": ["accepted", "access_expired"]}}


class Provider(BaseModel):
    provider_id: str
    name: str
    role_label: str
    organization: Optional[str] = None
    email: str


class Share(BaseModel):
    share_id: str
    provider_name: str
    role_label: str
    email: str
    categories: List[str]
    sent_at: str


class ShareIn(BaseModel):
    provider_id: str = Field(min_length=1, max_length=64)
    categories: List[str] = Field(min_length=1, max_length=3)


def _provider(doc: Dict[str, Any]) -> Provider:
    name = f"{doc.get('professional_first_name') or ''} {doc.get('professional_last_name') or ''}".strip()
    return Provider(
        provider_id=doc["invitation_id"],
        name=name or doc["professional_email"],
        role_label=ROLE_LABELS.get(doc.get("professional_role"), "Professional"),
        organization=doc.get("organization"),
        email=doc["professional_email"],
    )


@router.get("/providers", response_model=List[Provider])
async def list_providers(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[Provider]:
    cursor = db.parent_professional_invitations.find(
        {"inviting_parent_id": user.user_id, **PROVIDER_FILTER}, {"_id": 0, "invitation_token_hash": 0}
    ).sort("accepted_at", -1)
    seen, out = set(), []
    async for doc in cursor:
        if doc["professional_email"] not in seen:
            seen.add(doc["professional_email"])
            out.append(_provider(doc))
    return out


@router.get("/shares", response_model=List[Share])
async def list_shares(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[Share]:
    docs = await db.child_needs_shares.find({"user_id": user.user_id}, {"_id": 0}).sort("sent_at", -1).to_list(200)
    return [Share(**d) for d in docs]


@router.post("/share", response_model=Share)
async def share_report(
    body: ShareIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Share:
    if any(k not in FIELDS for k in body.categories):
        raise HTTPException(422, "Unknown form.")
    cats = [k for k in ("educational", "medical", "psychological") if k in body.categories]
    doc = await db.parent_professional_invitations.find_one(
        {"invitation_id": body.provider_id, "inviting_parent_id": user.user_id, **PROVIDER_FILTER}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Pick a professional who has accepted your invitation.")
    state = await db.child_needs_assessments.find_one({"user_id": user.user_id}, {"_id": 0, "answers": 1, "completed_at": 1}) or {}
    answers = {k: clean_category(k, (state.get("answers") or {}).get(k, {})) for k in cats}
    if any(not (state.get("completed_at") or {}).get(k) or not answers[k] for k in cats):
        raise HTTPException(422, "Only completed forms can be sent. Submit the form first.")

    provider = _provider(doc)
    pdf_bytes = child_needs_pdf.build_child_needs_pdf(content=CONTENT, parent_name=user.name or "", answers=answers)
    try:
        await run_in_threadpool(
            email_service.send_child_needs_report,
            to_email=provider.email,
            provider_name=provider.name,
            parent_name=user.name or "A parent",
            parent_email=user.email,
            form_titles=[TITLES[k] for k in cats],
            pdf_bytes=pdf_bytes,
            filename=f"SA_CoParents_Child_Needs_{'_'.join(k.title() for k in cats)}.pdf",
        )
    except email_service.EmailNotConfigured:
        raise HTTPException(503, "Email sending isn't set up yet. Please try again later.")
    except email_service.EmailSendError as e:
        raise HTTPException(502, str(e))

    share = Share(
        share_id=uuid.uuid4().hex[:12],
        provider_name=provider.name,
        role_label=provider.role_label,
        email=provider.email,
        categories=cats,
        sent_at=datetime.now(timezone.utc).isoformat(),
    )
    await db.child_needs_shares.insert_one({"user_id": user.user_id, "provider_id": provider.provider_id, **share.model_dump()})
    return share
