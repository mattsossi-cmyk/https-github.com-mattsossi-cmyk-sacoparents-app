"""Joint Co-Parenting Agreement Draft — API surface.

Endpoints (all authenticated):
  * GET  /api/joint-agreement/{share_id}         — JSON of the merged draft
  * GET  /api/joint-agreement/{share_id}/pdf     — Branded PDF export

Consent gate reuses the active Compare share pattern used by
`joint_professional_report_routes` and `pathway_report_routes`. A share
already carries mutual, revocable consent between the two parents; we
do not introduce a new consent flow.

Data source per parent: the latest document in `agreements` (produced by
`POST /api/mediation/agreement`). If either parent has never generated
an agreement draft the endpoint returns 409 with a message telling the
caller which parent still needs to generate theirs — without disclosing
the other parent's identity beyond first name.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from typing import Literal

from auth import UserPublic, get_current_user, get_db
from joint_agreement import build_joint_agreement
from joint_professional_report_routes import (
    _find_active_share, _load_user_display_name,
)


router = APIRouter(prefix="/joint-agreement", tags=["joint-agreement"])


async def _load_latest_agreement(
    db: AsyncIOMotorDatabase, user_id: str,
) -> Optional[Dict[str, Any]]:
    return await db["agreements"].find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("generated_at", -1)],
    )


async def _assemble_joint_agreement(
    db: AsyncIOMotorDatabase, share: Dict[str, Any], caller_id: str, share_id: str,
) -> Dict[str, Any]:
    pair: List[str] = list(share.get("_user_pair") or [])
    other_id = [uid for uid in pair if uid != caller_id][0]
    parent_a_name = await _load_user_display_name(db, caller_id, "Parent A")
    parent_b_name = await _load_user_display_name(db, other_id, "Parent B")

    agr_a = await _load_latest_agreement(db, caller_id)
    agr_b = await _load_latest_agreement(db, other_id)

    if not agr_a:
        raise HTTPException(
            409,
            "You haven't generated your individual Co-Parenting Agreement "
            "Draft yet. Open Summary → Co-Parenting Agreement Draft and "
            "generate yours first, then come back.",
        )
    if not agr_b:
        # Deliberately vague about which parent so we don't disclose the
        # co-parent's activity beyond what the Compare share already
        # implies (i.e., that they're a participant).
        raise HTTPException(
            409,
            f"{parent_b_name.split(' ')[0]} hasn't generated their "
            "individual Co-Parenting Agreement Draft yet. Once both "
            "parents have generated theirs, the joint draft will be "
            "ready.",
        )

    return build_joint_agreement(
        share_id=share_id,
        parent_a_name=parent_a_name,
        parent_b_name=parent_b_name,
        agreement_a=agr_a,
        agreement_b=agr_b,
    )


@router.get("/{share_id}")
async def get_joint_agreement(
    share_id: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Deterministic side-by-side merger of both parents' agreement drafts."""
    share = await _find_active_share(db, share_id, user.user_id)
    return await _assemble_joint_agreement(db, share, user.user_id, share_id)


@router.get("/{share_id}/pdf")
async def get_joint_agreement_pdf(
    share_id: str,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Branded PDF of the joint draft — attorney/mediator-ready."""
    from joint_agreement_pdf import build_joint_agreement_pdf

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_joint_agreement(db, share, user.user_id, share_id)
    pdf_bytes = build_joint_agreement_pdf(payload)
    filename = f"joint-coparenting-agreement-{share_id[:10]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Email export — send the Joint Agreement Draft PDF straight to a
# mediator, attorney, court, or therapist. Mirrors the Joint Report
# email endpoint so parents get the same one-tap experience for either
# artefact.
# ---------------------------------------------------------------------------

_ROLE_TO_AUDIENCE = {
    "mediator":                    "Mediator",
    "parent_facilitator_ad_litem": "Parent Facilitator Ad Litem",
    "trial_court":                 "Trial Court",
    "attorney":                    "Family Law Attorney",
    "therapist":                   "Therapist / Counsellor",
    "other":                       "Mediator / Attorney / Trial Court",
}


class JointAgreementEmailBody(BaseModel):
    recipient_email: str = Field(..., max_length=200)
    recipient_name:  Optional[str] = Field(None, max_length=120)
    recipient_role:  Optional[Literal[
        "mediator", "parent_facilitator_ad_litem", "trial_court",
        "attorney", "therapist", "other",
    ]] = None
    audience_label:  Optional[str] = Field(None, max_length=120)
    parent_message:  Optional[str] = Field(None, max_length=1200)


@router.post("/{share_id}/email")
async def email_joint_agreement(
    share_id: str,
    body: JointAgreementEmailBody,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate the joint agreement PDF and email it directly to a
    professional. Reply-to is the sending parent's email.

    Consent gate is identical to `/api/joint-agreement/{share_id}`.
    """
    from datetime import datetime, timezone
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        send_joint_agreement_draft,
    )
    from joint_agreement_pdf import build_joint_agreement_pdf

    to_email = (body.recipient_email or "").strip().lower()
    if "@" not in to_email or "." not in to_email.split("@")[-1]:
        raise HTTPException(400, "That doesn't look like a valid email address.")
    if to_email.endswith("@demo.local"):
        raise HTTPException(400, "Please use your recipient's real email address.")

    parent_email = (user.email or "").strip().lower()
    if not parent_email or parent_email.endswith("@demo.local"):
        raise HTTPException(
            400,
            "Save your work first — add a real email to your account so the "
            "recipient can reply to you.",
        )

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_joint_agreement(db, share, user.user_id, share_id)
    audience = body.audience_label or _ROLE_TO_AUDIENCE.get(
        body.recipient_role or "other", _ROLE_TO_AUDIENCE["other"],
    )

    try:
        pdf_bytes = build_joint_agreement_pdf(payload)
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(500, "Could not assemble the joint agreement PDF.") from e

    try:
        send_joint_agreement_draft(
            to_email=to_email,
            recipient_name=(body.recipient_name or "").strip(),
            recipient_role=audience,
            parent_a_name=payload.get("parent_a_name") or "",
            parent_b_name=payload.get("parent_b_name") or "",
            parent_email=parent_email,
            parent_message=(body.parent_message or "").strip(),
            summary=payload.get("summary") or {},
            pdf_bytes=pdf_bytes,
            pdf_filename=f"joint-coparenting-agreement-{share_id[:10]}.pdf",
        )
    except EmailNotConfigured as e:
        raise HTTPException(
            503,
            "Email isn't configured on this environment. Download the PDF "
            "and share it directly.",
        ) from e
    except EmailSendError as e:
        raise HTTPException(
            503,
            "Couldn't send the joint agreement right now. Please try again "
            "in a moment.",
        ) from e

    await db.joint_agreement_emails.insert_one({
        "user_id":        user.user_id,
        "share_id":       share_id,
        "to_email":       to_email,
        "recipient_name": (body.recipient_name or "").strip(),
        "recipient_role": body.recipient_role,
        "audience":       audience,
        "sent_at":        datetime.now(timezone.utc).isoformat(),
    })
    return {
        "ok": True,
        "emailed_to": to_email,
        "audience": audience,
        "share_id": share_id,
    }

