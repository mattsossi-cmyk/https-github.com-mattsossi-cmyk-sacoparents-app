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

from auth import (
    UserPublic, get_current_user, get_db,
    create_share_token, decode_share_token,
)
from joint_agreement import build_joint_agreement, regenerate_individual_from_joint
from joint_professional_report_routes import (
    _find_active_share, _load_user_display_name,
)
from share_routes import record_share_token, is_share_token_revoked
from share_link_common import (
    absolute_origin as _absolute_origin,
    is_link_preview_bot as _is_link_preview_bot,
    render_preview_html as _render_preview_html,
    clean_note,
)


router = APIRouter(prefix="/joint-agreement", tags=["joint-agreement"])


async def _load_latest_agreement(
    db: AsyncIOMotorDatabase, user_id: str,
) -> Optional[Dict[str, Any]]:
    return await db["agreements"].find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("generated_at", -1)],
    )


async def _load_reflection_answers(
    db: AsyncIOMotorDatabase, user_id: str,
    subject: str = "co_parenting",
) -> Dict[str, str]:
    """Iter191: fetch a parent's saved free-text reflection answers so
    the joint agreement payload can surface "Both parents mentioned X"
    bullets on §2 of the alignment report. Returns `{}` when the parent
    has not submitted — the merger then falls back to clause-only
    analysis without leaking that either parent opted in or out.

    Iter192 safety guard: safety-sensitive subjects are NEVER loaded
    through this path — Safety reflections require an explicit
    dual-consent ceremony on the `/api/alignment-reflection/{safety}/compare`
    endpoint and never auto-merge into the joint agreement.

    Wrapped in try/except because some legacy test fixtures stub `db`
    with a minimal object that lacks the alignment_reflections
    collection — reflections are purely additive, so a lookup failure
    should never break the joint-agreement contract."""
    try:
        from alignment_reflection_questions import is_sensitive_subject
        if is_sensitive_subject(subject):
            return {}
    except Exception:  # noqa: BLE001
        pass
    try:
        doc = await db["alignment_reflections"].find_one(
            {"user_id": user_id, "subject": subject}, {"_id": 0},
        )
    except (KeyError, AttributeError, TypeError):
        return {}
    if not doc:
        return {}
    answers = doc.get("answers") or {}
    return {k: (v or "") for k, v in answers.items() if isinstance(v, str)}


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

    # Iter191: pull reflection answers for both parents (optional).
    # Empty dicts are safe — build_joint_agreement only emits
    # reflection_analysis when BOTH sides have non-empty answers.
    reflections_a = await _load_reflection_answers(db, caller_id)
    reflections_b = await _load_reflection_answers(db, other_id)

    return build_joint_agreement(
        share_id=share_id,
        parent_a_name=parent_a_name,
        parent_b_name=parent_b_name,
        agreement_a=agr_a,
        agreement_b=agr_b,
        reflections_a=reflections_a,
        reflections_b=reflections_b,
    )


@router.get("/{share_id}")
async def get_joint_agreement(
    share_id: str,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Deterministic side-by-side merger of both parents' agreement drafts."""
    from phi_access_routes import record_phi_access

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_joint_agreement(db, share, user.user_id, share_id)
    await record_phi_access(
        db, user_id=user.user_id, action="read",
        resource_type="joint_agreement",
        share_id=share_id, request=request,
    )
    return payload


@router.get("/{share_id}/pdf")
async def get_joint_agreement_pdf(
    share_id: str,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Branded PDF of the joint draft — attorney/mediator-ready."""
    from joint_agreement_pdf import build_joint_agreement_pdf
    from phi_access_routes import record_phi_access

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_joint_agreement(db, share, user.user_id, share_id)
    pdf_bytes = build_joint_agreement_pdf(payload)
    filename = f"joint-coparenting-agreement-{share_id[:10]}.pdf"
    await record_phi_access(
        db, user_id=user.user_id, action="download",
        resource_type="joint_agreement_pdf",
        share_id=share_id, request=request,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
        },
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
    request: Request,
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

    # Mint a shareable preview link so the recipient can click through
    # to the in-browser view straight from their inbox. 14 days is long
    # enough to survive the typical email follow-up window; the parent
    # can revoke it early from their share-management UI at any time.
    preview_url = None
    preview_jti = None
    try:
        preview_token = create_share_token(
            doc_type="joint_agreement",
            doc_id=share_id,
            user_id=user.user_id,
            expire_days=14,
        )
        decoded_preview = decode_share_token(preview_token) or {}
        preview_expires = (
            datetime.fromtimestamp(decoded_preview["exp"], tz=timezone.utc)
            if decoded_preview.get("exp") else None
        )
        preview_jti = decoded_preview.get("jti")
        await record_share_token(
            db,
            jti=preview_jti,
            user_id=user.user_id,
            doc_type="joint_agreement",
            doc_id=share_id,
            expires_at=preview_expires,
            label=f"Emailed to {to_email}",
            token=preview_token,
        )
        preview_url = f"{_absolute_origin(request)}/api/joint-agreement/preview/{preview_token}"
        from phi_access_routes import record_phi_access
        await record_phi_access(
            db, user_id=user.user_id, action="share_link_created",
            resource_type="joint_agreement",
            share_id=share_id, request=request,
        )
    except Exception:  # noqa: BLE001 - preview link is best-effort
        # If minting fails for any reason the email still goes out
        # with just the PDF attachment — never block the send.
        preview_url = None

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
            preview_url=preview_url,
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
        "preview_jti":    preview_jti,
        "sent_at":        datetime.now(timezone.utc).isoformat(),
    })
    from phi_access_routes import record_phi_access
    await record_phi_access(
        db, user_id=user.user_id, action="email_disclosure",
        resource_type="joint_agreement_pdf",
        share_id=share_id,
    )
    return {
        "ok": True,
        "emailed_to": to_email,
        "audience": audience,
        "share_id": share_id,
        "preview_included": bool(preview_url),
        "preview_jti": preview_jti,
    }



# ---------------------------------------------------------------------------
# Recently Shared With — last 3 professionals this parent has emailed the
# joint agreement to. Mirrors the Joint Report endpoint so the UI strip
# can hit either artefact with the same shape.
# ---------------------------------------------------------------------------

@router.get("/{share_id}/recent-recipients")
async def recent_joint_agreement_recipients(
    share_id: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return up to 3 most-recent, de-duplicated-by-email send events
    for the caller on this share. Consent-gated identically to the
    email endpoint."""
    await _find_active_share(db, share_id, user.user_id)
    cursor = db.joint_agreement_emails.find(
        {"user_id": user.user_id, "share_id": share_id},
        {"_id": 0},
    ).sort("sent_at", -1).limit(30)
    seen: set = set()
    recents: List[Dict[str, Any]] = []
    async for row in cursor:
        email = (row.get("to_email") or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        recents.append({
            "to_email":       email,
            "recipient_name": row.get("recipient_name") or "",
            "recipient_role": row.get("recipient_role"),
            "audience":       row.get("audience"),
            "sent_at":        row.get("sent_at"),
        })
        if len(recents) >= 3:
            break
    return {"recipients": recents}



# ---------------------------------------------------------------------------
# Regenerate the caller's individual draft using the joint's
# `both_proposed` clauses as anchors. Deterministic — the parent's
# voice is preserved verbatim; anchor clauses are promoted to the top
# of each section and flagged.
# ---------------------------------------------------------------------------

@router.post("/{share_id}/regenerate-mine")
async def regenerate_my_agreement_from_joint(
    share_id: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Refresh the caller's individual Co-Parenting Agreement Draft so
    that clauses both parents have already proposed appear at the top
    of each section (marked `anchored: true`).

    Non-destructive: the caller's prior agreement doc stays in the
    `agreements` collection so history is preserved. A fresh doc is
    inserted with a `regenerated_from_joint` audit stanza pointing back
    to the joint share.

    Consent gate is identical to the other joint-agreement endpoints —
    the caller must be a participant in an active Compare share and
    both parents must have generated their individual drafts.
    """
    from datetime import datetime, timezone

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_joint_agreement(db, share, user.user_id, share_id)

    # The joint payload treats the caller as parent A. Their individual
    # draft is the source we regenerate from.
    caller_agreement = await _load_latest_agreement(db, user.user_id)
    if not caller_agreement:  # pragma: no cover - _assemble already 409s
        raise HTTPException(
            409,
            "You haven't generated your individual Co-Parenting Agreement "
            "Draft yet. Open Summary -> Co-Parenting Agreement Draft and "
            "generate yours first, then come back.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    new_doc, anchor_counts = regenerate_individual_from_joint(
        caller_agreement=caller_agreement,
        joint_payload=payload,
        now_iso=now_iso,
        co_parent_name=payload.get("parent_b_name") or "your co-parent",
    )
    # Persist. We keep the prior agreement doc untouched so parents can
    # revert or reference their earlier drafts if needed.
    new_doc["user_id"] = user.user_id
    await db.agreements.insert_one(new_doc.copy())

    return {
        "ok":                  True,
        "new_agreement_id":    new_doc["agreement_id"],
        "prior_agreement_id":  new_doc["regenerated_from_joint"]["prior_agreement_id"],
        "total_anchors":       new_doc["regenerated_from_joint"]["total_anchors"],
        "anchor_counts":       anchor_counts,
        "share_id":            share_id,
    }



# ---------------------------------------------------------------------------
# Public shareable HTML/PDF link — so a mediator or attorney can open the
# joint draft in-browser without logging in. The sending parent explicitly
# mints the token from the authenticated view; the underlying data is
# re-assembled on every read so revoking either parent's Compare consent
# stops the link from resolving (defence in depth on top of jti-revoke).
# ---------------------------------------------------------------------------


_SHARE_LINK_EXPIRE_CHOICES = {1, 7, 14, 30}


class JointAgreementShareLinkBody(BaseModel):
    consent_acknowledged: bool = Field(
        ...,
        description=(
            "Must be true. Confirms the sending parent has read the "
            "pre-share consent bullets before the link is minted."
        ),
    )
    expire_days: Optional[int] = 7
    label: Optional[str] = Field(None, max_length=120)
    note: Optional[str] = Field(
        None, max_length=500,
        description=(
            "Optional short personal note from the sending parent, "
            "displayed at the top of the shared page for the recipient."
        ),
    )


@router.post("/{share_id}/share-link")
async def create_joint_agreement_share_link(
    share_id: str,
    body: JointAgreementShareLinkBody,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Mint a signed, revocable, time-limited link a mediator/attorney can
    open in-browser to view (and optionally download) the joint draft."""
    from datetime import datetime, timezone
    from phi_access_routes import record_phi_access

    if not body.consent_acknowledged:
        raise HTTPException(
            400,
            "Explicit consent is required before a shareable link can be created.",
        )
    expire_days = body.expire_days if body.expire_days in _SHARE_LINK_EXPIRE_CHOICES else 7

    share = await _find_active_share(db, share_id, user.user_id)
    # Re-assemble to guarantee both drafts exist before we hand out a link.
    # Raises 409 with a friendly message if either parent's individual
    # draft is missing — same UX as the authenticated view.
    await _assemble_joint_agreement(db, share, user.user_id, share_id)

    token = create_share_token(
        doc_type="joint_agreement",
        doc_id=share_id,
        user_id=user.user_id,
        expire_days=expire_days,
    )
    payload = decode_share_token(token) or {}
    expires_at = (
        datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if payload.get("exp") else None
    )
    await record_share_token(
        db,
        jti=payload.get("jti"),
        user_id=user.user_id,
        doc_type="joint_agreement",
        doc_id=share_id,
        expires_at=expires_at,
        label=(body.label or None),
        note=clean_note(body.note),
        token=token,
    )
    await record_phi_access(
        db, user_id=user.user_id, action="share_link_created",
        resource_type="joint_agreement",
        share_id=share_id, request=request,
    )
    return {
        "token": token,
        "jti": payload.get("jti"),
        "path": f"/joint-agreement/shared/{token}",
        "preview_path": f"/api/joint-agreement/preview/{token}",
        "api_path": f"/api/joint-agreement/shared/{token}",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expire_days": expire_days,
    }


async def _load_shared_joint(
    token: str, db: AsyncIOMotorDatabase,
) -> Dict[str, Any]:
    """Decode the token, verify revocation, and rebuild the joint payload.

    The sending parent (token `sub`) is treated as the caller when
    re-assembling — this is safe because the token can only have been
    minted by a share participant, and `_find_active_share` re-checks
    that the underlying Compare share is still consented.
    """
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "joint_agreement":
        raise HTTPException(404, "This link has expired or is invalid.")
    jti = payload.get("jti")
    if await is_share_token_revoked(db, jti):
        raise HTTPException(404, "This link has been revoked by the sender.")
    share_id = payload["doc_id"]
    sender_id = payload["sub"]
    share = await _find_active_share(db, share_id, sender_id)
    joint = await _assemble_joint_agreement(db, share, sender_id, share_id)
    joint["shared_by_name"] = joint.get("parent_a_name") or ""
    # Pull the sender's optional landing note off the share_tokens row.
    if jti:
        row = await db.share_tokens.find_one(
            {"jti": jti}, {"_id": 0, "note": 1},
        )
        joint["sender_note"] = (row or {}).get("note") or None
    else:
        joint["sender_note"] = None
    return joint


@router.get("/shared/{token}")
async def get_shared_joint_agreement(token: str, request: Request):
    """Public — no auth. Renders the JSON payload of the joint draft for
    an unauthenticated mediator/attorney using the signed link."""
    from phi_access_routes import record_phi_access

    db: AsyncIOMotorDatabase = request.app.state.db
    payload = await _load_shared_joint(token, db)
    # Log the external view against the sender's PHI access history so
    # they can see who's opening their link.
    decoded = decode_share_token(token) or {}
    await record_phi_access(
        db, user_id=decoded.get("sub") or "unknown",
        action="external_read_via_share_link",
        resource_type="joint_agreement",
        share_id=decoded.get("doc_id"),
        jti=decoded.get("jti"), request=request,
    )
    return payload


# ---------------------------------------------------------------------------
# Bot-aware preview endpoint — the URL parents actually paste into email
# or messaging apps. When Slackbot / Twitterbot / etc. hits this route
# it gets a minimal HTML page carrying proper Open Graph / Twitter meta
# tags so the pasted URL renders as a branded card. Real browsers get a
# 302 to the SPA route (`/joint-agreement/shared/{token}`) so the UX
# doesn't change for humans.
#
# Never reveals PHI in the preview — the title only names the sending
# parent (already public in any Compare-share invite email they sent)
# and the description is the neutral draft-for-discussion disclaimer.
# ---------------------------------------------------------------------------


_BOT_UA_SIGNALS = ()  # deprecated — moved to share_link_common; retained
# only to avoid breaking any external caller that imported the name.


@router.get("/preview/{token}")
async def joint_agreement_link_preview(token: str, request: Request):
    """Serve OG-tagged HTML to social-preview crawlers; 302 real
    browsers to the SPA-rendered shared page."""
    from fastapi.responses import HTMLResponse, RedirectResponse

    origin = _absolute_origin(request)
    spa_url = f"{origin}/joint-agreement/shared/{token}"
    user_agent = request.headers.get("user-agent", "")

    # Humans get straight to the app. We don't hit the DB in that path
    # so the redirect is cheap and preserves referrer behaviour.
    if not _is_link_preview_bot(user_agent):
        return RedirectResponse(url=spa_url, status_code=302)

    # Bot path — try to personalise the title with the sender's name.
    # Failure is soft: an invalid or revoked token still gets a generic
    # branded card so the URL never looks broken in a paste preview.
    db: AsyncIOMotorDatabase = request.app.state.db
    sender = ""
    try:
        payload = await _load_shared_joint(token, db)
        sender = (payload or {}).get("shared_by_name") or ""
    except HTTPException:
        sender = ""
    except Exception:  # pragma: no cover - never fail a preview render
        sender = ""

    if sender:
        title = f"Joint Co-Parenting Agreement Draft · shared by {sender}"
    else:
        title = "Joint Co-Parenting Agreement Draft · SA CoParents"

    description = (
        "A neutral, side-by-side draft of both parents' co-parenting "
        "clauses — for discussion with a mediator or attorney. Not a "
        "signed agreement, court order, or legal document."
    )
    html_body = _render_preview_html(
        title=title,
        description=description,
        canonical_url=spa_url,
        og_image_url=f"{origin}/og-image.png",
        og_image_alt="SA CoParents · Joint Co-Parenting Agreement Draft",
    )
    return HTMLResponse(
        content=html_body,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/shared/{token}/pdf")
async def get_shared_joint_agreement_pdf(token: str, request: Request):
    """Public — no auth. Renders the PDF using the signed link."""
    from joint_agreement_pdf import build_joint_agreement_pdf
    from phi_access_routes import record_phi_access

    db: AsyncIOMotorDatabase = request.app.state.db
    payload = await _load_shared_joint(token, db)
    pdf_bytes = build_joint_agreement_pdf(payload)
    decoded = decode_share_token(token) or {}
    share_id = decoded.get("doc_id") or "unknown"
    await record_phi_access(
        db, user_id=decoded.get("sub") or "unknown",
        action="external_download_via_share_link",
        resource_type="joint_agreement_pdf",
        share_id=decoded.get("doc_id"),
        jti=decoded.get("jti"), request=request,
    )
    filename = f"joint-coparenting-agreement-{share_id[:10]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
        },
    )
