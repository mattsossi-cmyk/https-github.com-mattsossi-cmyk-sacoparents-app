"""Joint Co-Parenting Summary for Professional Review — API surface.

Two endpoints:
  * GET /api/joint-professional-report/{share_id}       — JSON
  * GET /api/joint-professional-report/{share_id}/pdf   — PDF

Both are gated behind an active Compare share the caller is a
participant in. The same consent model the Pathway Report uses — an
active Compare share IS the mutual consent for a joint report. No
new consent flow is introduced.

Data pulled per parent:
  * SNC v2 comparison (via `snc2_comparison.build_comparison`).
  * Mediation prep (`prep_data` — child_goals + priority).
  * Dimension Companion latest assessment (communication + emotional-
    regulation tiers).
  * TISFL Finding 3 ONLY (Parenting-Plan Implications). Findings 1 & 2
    remain private to the parent that completed the safety screen.
"""
from __future__ import annotations

from io import BytesIO
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
from joint_professional_report import build_joint_report
from share_link_common import (
    absolute_origin, is_link_preview_bot, render_preview_html, clean_note,
)
from share_routes import record_share_token, is_share_token_revoked
from snc2_comparison import build_comparison
from trauma_lens import redact_for_compare


router = APIRouter(prefix="/joint-professional-report", tags=["joint-professional-report"])


# ---------------------------------------------------------------------------
# Consent gate — reuses the Compare-share pattern from pathway_report_routes.
# ---------------------------------------------------------------------------
#
# Post-audit (SEC-003): the joint artefacts aggregate the FULL SNC2
# comparison + mediation prep + dimension companion + Finding 3 of the
# safety lens. That aggregation is broader than a single deep-dive
# share represents. So we only accept the two share types that
# represent full-scope mutual consent between the two parents:
#
#   * snc2_shares    — the full Special-Needs comparison share
#   * compare_shares — the legacy top-level Compare share
#
# Narrow domain-specific deep-dive shares (edu/med/psych) still gate
# their own comparison endpoints; they no longer unlock the broader
# joint report / joint agreement aggregators.

_SHARE_COLLECTIONS = (
    "snc2_shares",
    "compare_shares",  # legacy fallback
)


async def _find_active_share(
    db: AsyncIOMotorDatabase, share_id: str, user_id: str,
) -> Dict[str, Any]:
    """Locate an active Compare share the caller is a participant in.

    Different SNC v2 shares use different `user_pair` vs
    `creator_user_id`/`partner_user_id` shapes. Both are handled below.
    """
    row: Optional[Dict[str, Any]] = None
    for collection in _SHARE_COLLECTIONS:
        row = await db[collection].find_one(
            {"share_id": share_id}, {"_id": 0},
        )
        if row:
            break
    if not row:
        raise HTTPException(404, "Compare share not found.")

    # Two share shapes exist in the codebase — normalise them.
    pair: List[str] = list(row.get("user_pair") or [])
    if not pair:
        creator = row.get("creator_user_id")
        partner = row.get("partner_user_id")
        pair = [x for x in (creator, partner) if x]
    row["_user_pair"] = pair

    # SNC v2 shares use two `creator_consent` / `partner_consent` flags
    # plus a `status` field. Pathway shares use `status="active"`. Handle
    # both so the report unlocks whenever both parents have consented.
    is_active = (row.get("status") == "active") or (
        bool(row.get("creator_consent")) and bool(row.get("partner_consent"))
        and row.get("status") != "revoked"
    )
    if not is_active:
        raise HTTPException(
            409,
            "This Compare share is not yet fully consented — the Joint "
            "Professional Report needs both parents' explicit consent "
            "through the Compare flow before it can be generated.",
        )
    if user_id not in pair:
        raise HTTPException(403, "You are not a participant in this share.")
    return row


# ---------------------------------------------------------------------------
# Loaders.
# ---------------------------------------------------------------------------

async def _load_snc2_assessment(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    return await db["snc2_assessments"].find_one(
        {"user_id": user_id}, {"_id": 0},
    ) or {}


async def _load_prep(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    return await db["prep_data"].find_one(
        {"user_id": user_id}, {"_id": 0},
    ) or {}


async def _load_dim_companion(
    db: AsyncIOMotorDatabase, user_id: str,
) -> Optional[Dict[str, Any]]:
    return await db["dimension_companion_assessments"].find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)],
    )


async def _load_finding3(
    db: AsyncIOMotorDatabase, user_id: str,
) -> Optional[Dict[str, Any]]:
    """Return Finding 3 (Parenting-Plan Implications) only. Never Findings 1/2."""
    doc = await db["safety_assessments"].find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)],
    )
    if not doc:
        return None
    lens = (doc.get("result") or {}).get("lens") or {}
    redacted = redact_for_compare(lens)
    return (redacted.get("findings") or {}).get("parenting_plan_implications")


async def _load_user_display_name(
    db: AsyncIOMotorDatabase, user_id: str, fallback: str,
) -> str:
    doc = await db["users"].find_one({"user_id": user_id}, {"_id": 0, "name": 1})
    return ((doc or {}).get("name") or fallback).strip()


async def _resolve_pair_names(
    db: AsyncIOMotorDatabase, share: Dict[str, Any], caller_id: str,
) -> Dict[str, str]:
    """Return {'a_id','b_id','a_name','b_name'} with caller as parent A."""
    pair: List[str] = list(share.get("_user_pair") or [])
    other = [uid for uid in pair if uid != caller_id][0]
    a_name = await _load_user_display_name(db, caller_id, "Parent A")
    b_name = await _load_user_display_name(db, other, "Parent B")
    return {"a_id": caller_id, "b_id": other, "a_name": a_name, "b_name": b_name}


# ---------------------------------------------------------------------------
# Business logic — assemble the aggregated payload.
# ---------------------------------------------------------------------------

async def _assemble_report(
    db: AsyncIOMotorDatabase, share: Dict[str, Any], caller_id: str, share_id: str,
) -> Dict[str, Any]:
    names = await _resolve_pair_names(db, share, caller_id)
    snc_a = await _load_snc2_assessment(db, names["a_id"])
    snc_b = await _load_snc2_assessment(db, names["b_id"])
    prep_a = await _load_prep(db, names["a_id"])
    prep_b = await _load_prep(db, names["b_id"])
    dim_a = await _load_dim_companion(db, names["a_id"])
    dim_b = await _load_dim_companion(db, names["b_id"])
    lens3_a = await _load_finding3(db, names["a_id"])
    lens3_b = await _load_finding3(db, names["b_id"])

    # Build the SNC v2 comparison. If either parent has not completed the
    # SNC v2 assessment we still produce the report, but comparison-driven
    # sections will be empty with a helpful `empty_reason`.
    comparison: Dict[str, Any]
    if (
        snc_a and snc_b
        and snc_a.get("completed") and snc_b.get("completed")
    ):
        comparison = build_comparison(
            parent_a_name=names["a_name"],
            parent_b_name=names["b_name"],
            a_pathways=snc_a.get("selected_pathways") or [],
            b_pathways=snc_b.get("selected_pathways") or [],
            a_answers=snc_a.get("answers") or {},
            b_answers=snc_b.get("answers") or {},
        )
    else:
        comparison = {
            "shared_pathways": [],
            "steps": [],
            "highlights": [],
            "summary": {"total_items": 0, "aligned_pct": 0, "divergent_pct": 0, "counts": {}},
        }

    return build_joint_report(
        parent_a_name=names["a_name"],
        parent_b_name=names["b_name"],
        share_id=share_id,
        comparison=comparison,
        prep_a=prep_a,
        prep_b=prep_b,
        dim_a=dim_a,
        dim_b=dim_b,
        lens_finding3_a=lens3_a,
        lens_finding3_b=lens3_b,
    )


# ---------------------------------------------------------------------------
# Routes.
# ---------------------------------------------------------------------------

@router.get("/professional-intro.pdf")
async def get_professional_intro_pdf():
    """3-minute intro to SA CoParents rendered as a branded PDF.

    Public — no consent gate. The document carries no user data; it is
    a generic explainer parents can hand to a professional alongside
    (or before) any joint artefact. Declared BEFORE the `{share_id}`
    route so FastAPI's fixed-path match wins.
    """
    from professional_intro_transcript import (
        PROFESSIONAL_INTRO_FILENAME, build_professional_intro_pdf,
    )
    pdf_bytes = build_professional_intro_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{PROFESSIONAL_INTRO_FILENAME}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{share_id}")
async def get_joint_report(
    share_id: str,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """JSON payload of the Joint Co-Parenting Summary for Professional Review."""
    from phi_access_routes import record_phi_access

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_report(db, share, user.user_id, share_id)
    await record_phi_access(
        db, user_id=user.user_id, action="read",
        resource_type="joint_professional_report",
        share_id=share_id, request=request,
    )
    return payload


@router.get("/{share_id}/pdf")
async def get_joint_report_pdf(
    share_id: str,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Branded PDF of the joint report — attorney/mediator-ready."""
    from joint_professional_report_pdf import build_joint_report_pdf
    from phi_access_routes import record_phi_access

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_report(db, share, user.user_id, share_id)
    pdf_bytes = build_joint_report_pdf(payload)
    filename = f"joint-professional-report-{share_id[:10]}.pdf"
    await record_phi_access(
        db, user_id=user.user_id, action="download",
        resource_type="joint_professional_report_pdf",
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
# Email export — send the Joint Report PDF directly to a mediator,
# attorney, court, or therapist. Mirrors the Pathway Report email
# pattern so tone + audit shape stay consistent.
# ---------------------------------------------------------------------------

_ROLE_TO_AUDIENCE = {
    "mediator":                    "Mediator",
    "parent_facilitator_ad_litem": "Parent Facilitator Ad Litem",
    "trial_court":                 "Trial Court",
    "attorney":                    "Family Law Attorney",
    "therapist":                   "Therapist / Counsellor",
    "other":                       "Mediator / Attorney / Trial Court",
}


class JointReportEmailBody(BaseModel):
    recipient_email: str = Field(..., max_length=200)
    recipient_name:  Optional[str] = Field(None, max_length=120)
    recipient_role:  Optional[Literal[
        "mediator", "parent_facilitator_ad_litem", "trial_court",
        "attorney", "therapist", "other",
    ]] = None
    audience_label:  Optional[str] = Field(None, max_length=120)
    parent_message:  Optional[str] = Field(None, max_length=1200)


@router.post("/{share_id}/email")
async def email_joint_report(
    share_id: str,
    body: JointReportEmailBody,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate the joint report PDF and email it directly to a
    professional. Reply-to is the sending parent's email so the
    recipient can respond without an intermediary.

    Consent gate is identical to `/api/joint-professional-report/{share_id}`:
    caller must be a participant in an active Compare share.
    """
    from datetime import datetime, timezone
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        send_joint_professional_report,
    )
    from joint_professional_report_pdf import build_joint_report_pdf

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
    payload = await _assemble_report(db, share, user.user_id, share_id)
    audience = body.audience_label or _ROLE_TO_AUDIENCE.get(
        body.recipient_role or "other", _ROLE_TO_AUDIENCE["other"]
    )

    try:
        pdf_bytes = build_joint_report_pdf(payload)
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(500, "Could not assemble the joint report PDF.") from e

    try:
        send_joint_professional_report(
            to_email=to_email,
            recipient_name=(body.recipient_name or "").strip(),
            recipient_role=audience,
            parent_a_name=payload.get("parent_a_name") or "",
            parent_b_name=payload.get("parent_b_name") or "",
            parent_email=parent_email,
            parent_message=(body.parent_message or "").strip(),
            summary_counts=payload.get("summary_counts") or {},
            pdf_bytes=pdf_bytes,
            pdf_filename=f"joint-professional-report-{share_id[:10]}.pdf",
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
            "Couldn't send the joint report right now. Please try again "
            "in a moment.",
        ) from e

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.joint_report_emails.insert_one({
        "user_id":        user.user_id,
        "share_id":       share_id,
        "to_email":       to_email,
        "recipient_name": (body.recipient_name or "").strip(),
        "recipient_role": body.recipient_role,
        "audience":       audience,
        "sent_at":        now_iso,
    })
    # Audit-log this disclosure so it appears in the parent's own
    # accounting of disclosures.
    from phi_access_routes import record_phi_access
    await record_phi_access(
        db, user_id=user.user_id, action="email_disclosure",
        resource_type="joint_professional_report_pdf",
        share_id=share_id, request=request,
    )
    return {
        "ok": True,
        "emailed_to": to_email,
        "audience": audience,
        "share_id": share_id,
    }



# ---------------------------------------------------------------------------
# Public shareable HTML / PDF / OG-preview link — mirrors the Joint
# Agreement flow. Sending parent mints a signed token; mediators and
# attorneys open the link in-browser without logging in.
# ---------------------------------------------------------------------------

_REPORT_LINK_EXPIRE_CHOICES = {1, 7, 14, 30}


class JointReportShareLinkBody(BaseModel):
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
async def create_joint_report_share_link(
    share_id: str,
    body: JointReportShareLinkBody,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Mint a signed, revocable, time-limited link a mediator/attorney can
    open in-browser to view (and optionally download) the joint report."""
    from datetime import datetime, timezone
    from phi_access_routes import record_phi_access

    if not body.consent_acknowledged:
        raise HTTPException(
            400,
            "Explicit consent is required before a shareable link can be created.",
        )
    expire_days = (
        body.expire_days if body.expire_days in _REPORT_LINK_EXPIRE_CHOICES else 7
    )

    share = await _find_active_share(db, share_id, user.user_id)
    # Re-assemble so we fail fast (409) if either parent's inputs are
    # still missing — same UX as the authenticated view.
    await _assemble_report(db, share, user.user_id, share_id)

    token = create_share_token(
        doc_type="joint_report",
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
        doc_type="joint_report",
        doc_id=share_id,
        expires_at=expires_at,
        label=(body.label or None),
        note=clean_note(body.note),
    )
    await record_phi_access(
        db, user_id=user.user_id, action="share_link_created",
        resource_type="joint_professional_report",
        share_id=share_id, request=request,
    )
    return {
        "token": token,
        "jti": payload.get("jti"),
        "path": f"/joint-report/shared/{token}",
        "preview_path": f"/api/joint-professional-report/preview/{token}",
        "api_path": f"/api/joint-professional-report/shared/{token}",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expire_days": expire_days,
    }


async def _load_shared_report(
    token: str, db: AsyncIOMotorDatabase,
) -> Dict[str, Any]:
    """Decode the token, verify revocation, and rebuild the joint report
    payload. Attaches the sender's optional landing note."""
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "joint_report":
        raise HTTPException(404, "This link has expired or is invalid.")
    jti = payload.get("jti")
    if await is_share_token_revoked(db, jti):
        raise HTTPException(404, "This link has been revoked by the sender.")
    share_id = payload["doc_id"]
    sender_id = payload["sub"]
    share = await _find_active_share(db, share_id, sender_id)
    report = await _assemble_report(db, share, sender_id, share_id)
    report["shared_by_name"] = report.get("parent_a_name") or ""
    if jti:
        row = await db.share_tokens.find_one({"jti": jti}, {"_id": 0, "note": 1})
        report["sender_note"] = (row or {}).get("note") or None
    else:
        report["sender_note"] = None
    return report


@router.get("/shared/{token}")
async def get_shared_joint_report(token: str, request: Request):
    """Public — no auth. JSON payload of the joint report."""
    from phi_access_routes import record_phi_access

    db: AsyncIOMotorDatabase = request.app.state.db
    payload = await _load_shared_report(token, db)
    decoded = decode_share_token(token) or {}
    await record_phi_access(
        db, user_id=decoded.get("sub") or "unknown",
        action="external_read_via_share_link",
        resource_type="joint_professional_report",
        share_id=decoded.get("doc_id"), request=request,
    )
    return payload


@router.get("/shared/{token}/pdf")
async def get_shared_joint_report_pdf(token: str, request: Request):
    """Public — no auth. Renders the PDF using the signed link."""
    from joint_professional_report_pdf import build_joint_report_pdf
    from phi_access_routes import record_phi_access

    db: AsyncIOMotorDatabase = request.app.state.db
    payload = await _load_shared_report(token, db)
    pdf_bytes = build_joint_report_pdf(payload)
    decoded = decode_share_token(token) or {}
    share_id = decoded.get("doc_id") or "unknown"
    await record_phi_access(
        db, user_id=decoded.get("sub") or "unknown",
        action="external_download_via_share_link",
        resource_type="joint_professional_report_pdf",
        share_id=decoded.get("doc_id"), request=request,
    )
    filename = f"joint-professional-report-{share_id[:10]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
        },
    )


@router.get("/preview/{token}")
async def joint_report_link_preview(token: str, request: Request):
    """Bot-aware OG preview. Real browsers get a 302 to the SPA
    (`/joint-report/shared/{token}`); crawlers get OG-tagged HTML."""
    from fastapi.responses import HTMLResponse, RedirectResponse

    origin = absolute_origin(request)
    spa_url = f"{origin}/joint-report/shared/{token}"
    if not is_link_preview_bot(request.headers.get("user-agent", "")):
        return RedirectResponse(url=spa_url, status_code=302)

    db: AsyncIOMotorDatabase = request.app.state.db
    sender = ""
    try:
        payload = await _load_shared_report(token, db)
        sender = (payload or {}).get("shared_by_name") or ""
    except HTTPException:
        sender = ""
    except Exception:  # pragma: no cover
        sender = ""

    if sender:
        title = f"Joint Co-Parenting Summary for Professional Review · shared by {sender}"
    else:
        title = "Joint Co-Parenting Summary for Professional Review · SA CoParents"
    description = (
        "A neutral summary of both parents' inputs — pathways, dimension "
        "notes, and shared-parenting implications — prepared for a "
        "mediator or attorney. Not a signed agreement or court order."
    )
    html_body = render_preview_html(
        title=title,
        description=description,
        canonical_url=spa_url,
        og_image_url=f"{origin}/og-image.png",
        og_image_alt="SA CoParents · Joint Co-Parenting Summary",
    )
    return HTMLResponse(
        content=html_body,
        headers={"Cache-Control": "public, max-age=300"},
    )
