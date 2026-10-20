"""Mediation prep routes: save/load prep data, AI analysis, summary, PDF export."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_current_user, create_share_token, decode_share_token, require_active_user
from ai_notice_routes import require_ai_notice
from share_routes import record_share_token, is_share_token_revoked

# Daily email cap for demo/guest accounts. Permanent accounts are uncapped.
# Overridable via env so an admin can dial this without a redeploy.
GUEST_EMAIL_DAILY_LIMIT = int(os.environ.get("GUEST_EMAIL_DAILY_LIMIT", "1"))
from models import (
    ChildGoalsPayload,
    IssuesPayload,
    PriorityPayload,
    CommStylePayload,
    ReadinessPayload,
    ReflectionPayload,
    CommAnalysisRequest,
    UserPublic,
)
import ai_service
import pdf_service
import certificate_service
from progress_dashboard_routes import compute_progress
import email_service
import journal_routes
import report_visibility
from pydantic import BaseModel, EmailStr, Field
from typing import List
import mediation_sharing  # noqa: E402
import prep_privacy  # noqa: E402


router = APIRouter(prefix="/mediation", tags=["mediation"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _save_section(db, user_id: str, section: str, payload: dict):
    await db.prep_data.update_one(
        {"user_id": user_id},
        {
            "$set": {
                section: payload,
                "updated_at": _now(),
                f"completed.{section}": True,
            },
            "$setOnInsert": {"user_id": user_id, "created_at": _now()},
        },
        upsert=True,
    )


async def _load_prep(db, user_id: str) -> Dict[str, Any]:
    doc = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0})
    return doc or {"user_id": user_id, "completed": {}}


def _snapshot_prep(prep: Dict[str, Any]) -> Dict[str, Any]:
    """Freeze the parts of prep we want to compare across summaries (never the Issues safety text)."""
    return {
        "child_goals": prep.get("child_goals"),
        "issues": prep_privacy.clean_issues(prep.get("issues")),
        "priority": prep.get("priority"),
        "comm_style": prep.get("comm_style"),
        "readiness": prep.get("readiness"),
    }


async def _previous_doc(db, collection: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Most recent doc of that type for the user — used as the comparison baseline."""
    return await db[collection].find_one(
        {"user_id": user_id, "prep_snapshot": {"$exists": True}},
        {"_id": 0},
        sort=[("generated_at", -1)],
    )


# ============ Save endpoints ============
@router.put("/child-goals")
async def save_child_goals(
    body: ChildGoalsPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "child_goals", body.dict())
    return {"ok": True}


@router.put("/issues")
async def save_issues(
    body: IssuesPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    # The safety box is now the Family check-in card: new safety text is dropped, text already saved is kept as is.
    payload = prep_privacy.clean_issues(body.dict())
    saved = prep_privacy.saved_safety_text(((await db.prep_data.find_one({"user_id": current.user_id}, {"_id": 0, "issues": 1})) or {}).get("issues"))
    if saved:
        payload.setdefault("items", {})[prep_privacy.SAFETY_ISSUE] = saved
    await _save_section(db, current.user_id, "issues", payload)
    return {"ok": True}


@router.put("/priority")
async def save_priority(
    body: PriorityPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "priority", body.dict())
    return {"ok": True}


@router.put("/comm-style")
async def save_comm_style(
    body: CommStylePayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "comm_style", body.dict())
    return {"ok": True}


@router.put("/readiness")
async def save_readiness(
    body: ReadinessPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "readiness", body.dict())
    return {"ok": True}


@router.put("/reflection")
async def save_reflection(
    body: ReflectionPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    payload = body.dict()
    db = request.app.state.db
    await _save_section(db, current.user_id, "reflection", payload)
    # Quietly archive a journal snapshot if the content changed since last save.
    await journal_routes.maybe_snapshot_reflection(db, current.user_id, payload)
    return {"ok": True}


@router.get("/prep")
async def get_prep(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    return prep_privacy.without_safety_text(await _load_prep(request.app.state.db, current.user_id))



# ============ Foundation Statement — download + share ============
_FOUNDATION_SHARE_HOURLY_LIMIT = int(
    os.environ.get("FOUNDATION_STATEMENT_SHARE_HOURLY_LIMIT", "5")
)
# 30-day preview link — matches the Joint Agreement / Joint Report
# share-token windows. Recipient-facing URL is short-lived; the audit
# row + PDF attachment remain forever.
_FOUNDATION_PREVIEW_EXPIRE_DAYS = 30


class FoundationStatementShareBody(BaseModel):
    """Body for `POST /mediation/foundation-statement/share`."""
    recipient_email: EmailStr
    recipient_name: Optional[str] = Field(default=None, max_length=80)
    personal_note: Optional[str] = Field(default=None, max_length=500)


def _author_display_name(user: UserPublic) -> str:
    """Prefer explicit display name; fall back to the email local-part
    so we never surface an empty string on the PDF."""
    if user.name and user.name.strip():
        return user.name.strip()
    if user.email:
        return user.email.split("@", 1)[0]
    return "A co-parent"


async def _load_reflection_for_current(db, user_id: str) -> Dict[str, Any]:
    prep = await _load_prep(db, user_id)
    return prep.get("reflection") or {}


async def _mint_foundation_share_link(
    *,
    request: Request,
    db,
    user: UserPublic,
    expire_days: int,
    recipient_email: Optional[str],
    personal_note: Optional[str],
) -> Tuple[str, str]:
    """Mint a signed, revocable share-preview token for the caller's
    Foundation Statement and return `(token, absolute_preview_url)`.

    The URL is stable across resends of the same original share row
    because a *new* token is minted every time (matches Joint Report
    behaviour) — parents don't have a "reuse the old link" flow. A
    revoked/expired token 404s cleanly on the public endpoints.
    """
    from datetime import datetime, timezone
    from share_link_common import absolute_origin

    token = create_share_token(
        doc_type="foundation_statement",
        doc_id=user.user_id,   # the reflection is scoped to the user
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
        doc_type="foundation_statement",
        doc_id=user.user_id,
        expires_at=expires_at,
        label=recipient_email or None,
        note=(personal_note or "").strip() or None,
        token=token,
    )
    origin = absolute_origin(request)
    preview_url = f"{origin}/foundation/shared/{token}"
    return token, preview_url


@router.get("/foundation-statement.pdf")
async def download_foundation_statement(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Download the caller's Foundation Statement as a one-page PDF.
    Rejects with 409 when the parent hasn't written any prompts yet
    so a hollow document can't be exfiltrated by accident."""
    from foundation_statement_pdf import (
        build_foundation_statement_pdf,
        foundation_statement_has_content,
    )
    db = request.app.state.db
    reflection = await _load_reflection_for_current(db, current.user_id)
    if not foundation_statement_has_content(reflection):
        raise HTTPException(
            status_code=409,
            detail=(
                "Your Foundation Statement is empty. Write at least one "
                "prompt on /reflection before downloading."
            ),
        )
    pdf_bytes = build_foundation_statement_pdf(
        author_name=_author_display_name(current),
        reflection=reflection,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="foundation-statement.pdf"'
            ),
        },
    )


@router.post("/foundation-statement/email-me")
async def email_foundation_statement_to_me(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Email the caller their OWN Foundation Statement as an attached
    PDF — parity with the `/snc2/report/email`, `/edu-deep/report/email`,
    `/med-deep/report/email`, and `/psych-deep/report/email` endpoints.

    Distinct from `POST /foundation-statement/share`, which sends the
    document to a THIRD PARTY and creates an audit-tracked share row.
    This helper writes no history — it's a receipt for the parent.
    """
    from foundation_statement_pdf import (
        build_foundation_statement_pdf,
        foundation_statement_has_content,
    )
    import email_service

    if current.is_guest:
        raise HTTPException(
            status_code=403,
            detail="Please claim an account before emailing your Foundation Statement.",
        )
    to_email = (current.email or "").strip().lower()
    if not to_email:
        raise HTTPException(status_code=400, detail="No email address on file.")

    db = request.app.state.db
    reflection = await _load_reflection_for_current(db, current.user_id)
    if not foundation_statement_has_content(reflection):
        raise HTTPException(
            status_code=409,
            detail=(
                "Your Foundation Statement is empty. Write at least one "
                "prompt on /reflection before emailing it."
            ),
        )
    pdf_bytes = build_foundation_statement_pdf(
        author_name=_author_display_name(current),
        reflection=reflection,
    )
    try:
        email_service.send_foundation_statement_pdf_to_me(
            to_email=to_email,
            user_name=current.name,
            pdf_bytes=pdf_bytes,
        )
    except email_service.EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Email delivery isn't configured on this environment.",
        )
    except email_service.EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))
    from report_deliveries import record_email_delivery
    await record_email_delivery(
        db, user_id=current.user_id,
        report_type="foundation_statement", to_email=to_email,
    )
    return {
        "ok": True,
        "sent_to": to_email,
        "filename": "foundation-statement.pdf",
    }



@router.post("/foundation-statement/share")
async def share_foundation_statement(
    body: FoundationStatementShareBody,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Email the caller's Foundation Statement PDF to a recipient
    (co-parent or mediator). Rate-limited per user per hour so a
    misclick can't spam an inbox."""
    from foundation_statement_pdf import (
        build_foundation_statement_pdf,
        foundation_statement_has_content,
    )
    db = request.app.state.db
    reflection = await _load_reflection_for_current(db, current.user_id)
    if not foundation_statement_has_content(reflection):
        raise HTTPException(
            status_code=409,
            detail=(
                "Your Foundation Statement is empty. Write at least one "
                "prompt on /reflection before sharing."
            ),
        )
    recipient_email = body.recipient_email.strip().lower()
    if recipient_email == (current.email or "").strip().lower():
        raise HTTPException(
            status_code=400,
            detail="You can't share the Foundation Statement with yourself.",
        )

    # Sliding-hour rate limit — cheap dedupe against misclicks.
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = await db.foundation_statement_shares.count_documents({
        "user_id": current.user_id,
        "created_at": {"$gte": one_hour_ago},
    })
    if recent_count >= _FOUNDATION_SHARE_HOURLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                "You've hit the hourly share limit. Take a breath and try "
                "again in an hour."
            ),
        )

    pdf_bytes = build_foundation_statement_pdf(
        author_name=_author_display_name(current),
        reflection=reflection,
    )

    # Mint a 30-day share-preview token BEFORE sending the email so
    # the recipient can open the statement in-browser (with "Read to
    # me" voice playback) without downloading the PDF attachment.
    share_token_str, preview_url = await _mint_foundation_share_link(
        request=request,
        db=db,
        user=current,
        expire_days=_FOUNDATION_PREVIEW_EXPIRE_DAYS,
        recipient_email=recipient_email,
        personal_note=body.personal_note,
    )

    try:
        email_service.send_foundation_statement_share(
            to_email=recipient_email,
            recipient_name=body.recipient_name,
            sender_name=_author_display_name(current),
            sender_email=current.email or "",
            personal_note=body.personal_note,
            pdf_bytes=pdf_bytes,
            preview_url=preview_url,
        )
    except email_service.EmailNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Email isn't configured on this environment yet — "
                "download the PDF and forward it manually for now."
            ),
        ) from exc
    except email_service.EmailSendError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc) or "Could not send email right now.",
        ) from exc

    # Audit trail — the parent can review who they've shared with
    # from `/my-plan` in a future iteration, and this row also
    # backs the rate limit above.
    audit_id = uuid.uuid4().hex[:12]
    await db.foundation_statement_shares.insert_one({
        "share_id": audit_id,
        "user_id": current.user_id,
        "recipient_email": recipient_email,
        "recipient_name": (body.recipient_name or "").strip() or None,
        # We store the personal note verbatim so the parent can
        # one-tap resend the exact same email later. Rows belong to
        # the sender (`user_id: current.user_id`) so no cross-user
        # exposure — parents only ever see their own history.
        "personal_note": (body.personal_note or "").strip() or None,
        "had_personal_note": bool(
            body.personal_note and body.personal_note.strip()
        ),
        "preview_token": share_token_str,
        "sender_email": current.email,
        "created_at": datetime.now(timezone.utc),
    })
    return {
        "ok": True,
        "delivered_to": recipient_email,
        "preview_url": preview_url,
        "preview_expires_in_days": _FOUNDATION_PREVIEW_EXPIRE_DAYS,
        "remaining_this_hour": max(
            0, _FOUNDATION_SHARE_HOURLY_LIMIT - recent_count - 1,
        ),
    }


@router.get("/foundation-statement/shares")
async def list_foundation_statement_shares(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Return the caller's most-recent Foundation Statement shares
    (last 25). Powers the "Share history" view on /my-plan so a
    parent can see who they've sent to and re-send with one tap.

    For every share row that carries a `preview_token`, we resolve
    its `share_tokens` sibling doc + compute one of four statuses:
      * `active`   — link still opens
      * `revoked`  — parent hit Revoke; recipient now 404s
      * `expired`  — 30-day window elapsed
      * `none`     — legacy row (pre-preview-link feature)
    """
    db = request.app.state.db
    cursor = (
        db.foundation_statement_shares
        .find({"user_id": current.user_id})
        .sort("created_at", -1)
        .limit(25)
    )
    audit_rows: List[Dict[str, Any]] = []
    async for row in cursor:
        audit_rows.append(row)

    # Batch-fetch the sibling share_tokens rows so we don't fan out
    # N queries. Only rows with a preview_token participate.
    tokens = [r.get("preview_token") for r in audit_rows if r.get("preview_token")]
    token_meta: Dict[str, Dict[str, Any]] = {}
    if tokens:
        # Look up by the FULL token — share_tokens stores the raw
        # JWT under the `token` field. We keep the jti alongside so
        # the frontend can call the revoke endpoint.
        async for tok_doc in db.share_tokens.find(
            {"token": {"$in": tokens}, "user_id": current.user_id},
            {"_id": 0, "token": 1, "jti": 1, "revoked_at": 1, "expires_at": 1},
        ):
            token_meta[tok_doc["token"]] = tok_doc

    # Aggregate open counts / last-opened per jti in one round-trip
    # so the History tab stays fast even with 25 share rows.
    jtis = [t.get("jti") for t in token_meta.values() if t.get("jti")]
    open_stats: Dict[str, Dict[str, Any]] = {}
    daily_stats: Dict[str, List[int]] = {}
    if jtis:
        from foundation_statement_analytics import opens_by_jti, opens_daily_by_jti
        open_stats = await opens_by_jti(db, user_id=current.user_id, jtis=jtis)
        daily_stats = await opens_daily_by_jti(
            db, user_id=current.user_id, jtis=jtis,
        )

    now = datetime.now(timezone.utc)
    rows: List[Dict[str, Any]] = []
    for row in audit_rows:
        preview_token = row.get("preview_token")
        preview_status = "none"
        preview_jti: Optional[str] = None
        expires_at: Optional[str] = None
        if preview_token:
            meta = token_meta.get(preview_token) or {}
            preview_jti = meta.get("jti")
            expires_at = meta.get("expires_at")
            if meta.get("revoked_at"):
                preview_status = "revoked"
            elif meta.get("expires_at"):
                # `expires_at` is stored as an ISO string on
                # share_tokens.
                try:
                    exp = datetime.fromisoformat(str(meta["expires_at"]))
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    preview_status = "expired" if exp < now else "active"
                except ValueError:
                    preview_status = "active"
            else:
                preview_status = "active"
        rows.append({
            "share_id": row.get("share_id"),
            "recipient_email": row.get("recipient_email"),
            "recipient_name": row.get("recipient_name"),
            "personal_note": row.get("personal_note"),
            "created_at": (
                row["created_at"].isoformat()
                if isinstance(row.get("created_at"), datetime)
                else row.get("created_at")
            ),
            # Preview link surface — powers the "Manage links" UI
            # on the parent's Share modal.
            "preview_jti": preview_jti,
            "preview_status": preview_status,
            "preview_expires_at": expires_at,
            # Open analytics (bot-filtered) — closes the "did they
            # read it?" feedback loop.
            "open_count": (
                open_stats.get(preview_jti, {}).get("open_count", 0)
                if preview_jti else 0
            ),
            "last_opened_at": (
                open_stats.get(preview_jti, {}).get("last_opened_at")
                if preview_jti else None
            ),
            "unique_ip_count": (
                open_stats.get(preview_jti, {}).get("unique_ip_count", 0)
                if preview_jti else 0
            ),
            # 7-day per-day open counts, oldest → today. Always a
            # 7-element list so the sparkline never null-guards.
            "daily_opens_7d": (
                daily_stats.get(preview_jti) or [0] * 7
                if preview_jti else [0] * 7
            ),
        })
    return {"shares": rows}


class FoundationPreviewRevokeBody(BaseModel):
    """Body for `POST /foundation-statement/preview-links/revoke`."""
    jti: str = Field(..., min_length=8, max_length=128)


@router.post("/foundation-statement/preview-links/revoke")
async def revoke_foundation_preview_link(
    body: FoundationPreviewRevokeBody,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Revoke a Foundation Statement preview link by JTI. Idempotent
    — revoking an already-revoked link is a soft no-op so a
    double-tap on the UI never surfaces an error.

    Ownership check: the caller must own the token (user_id match).
    A cross-user attempt 404s so we don't leak the existence of a
    foreign token.
    """
    db = request.app.state.db
    tok = await db.share_tokens.find_one(
        {"jti": body.jti, "user_id": current.user_id},
        {"_id": 0, "jti": 1, "revoked_at": 1, "doc_type": 1},
    )
    if not tok:
        raise HTTPException(
            status_code=404,
            detail="Preview link not found or not owned by this account.",
        )
    if tok.get("doc_type") != "foundation_statement":
        # Belt-and-braces — this endpoint is dedicated to statement
        # tokens so we never accidentally revoke someone's Joint
        # Agreement share.
        raise HTTPException(
            status_code=400,
            detail="This link is not a Foundation Statement preview.",
        )
    if tok.get("revoked_at"):
        return {"ok": True, "already_revoked": True}
    await db.share_tokens.update_one(
        {"jti": body.jti, "user_id": current.user_id},
        {"$set": {"revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "already_revoked": False}


@router.post("/foundation-statement/shares/{share_id}/resend")
async def resend_foundation_statement_share(
    share_id: str = Path(..., min_length=1, max_length=40),
    request: Request = None,
    current: UserPublic = Depends(get_current_user),
):
    """Resend a previously-shared Foundation Statement to the same
    recipient with the same personal note. The PDF is regenerated
    on the fly so the recipient always gets the CURRENT reflection
    content, not a stale snapshot — this matches parents' intuition
    ("if I updated it, resend the fresh one"). Rate-limited via the
    same 5/hour ceiling as first-time sends."""
    from foundation_statement_pdf import (
        build_foundation_statement_pdf,
        foundation_statement_has_content,
    )
    db = request.app.state.db
    original = await db.foundation_statement_shares.find_one({
        "share_id": share_id,
        "user_id": current.user_id,
    })
    if not original:
        raise HTTPException(status_code=404, detail="Share not found.")

    reflection = await _load_reflection_for_current(db, current.user_id)
    if not foundation_statement_has_content(reflection):
        raise HTTPException(
            status_code=409,
            detail="Your Foundation Statement is empty. Write at least one prompt on /reflection before resending.",
        )

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = await db.foundation_statement_shares.count_documents({
        "user_id": current.user_id,
        "created_at": {"$gte": one_hour_ago},
    })
    if recent_count >= _FOUNDATION_SHARE_HOURLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="You've hit the hourly share limit. Try again in an hour.",
        )

    pdf_bytes = build_foundation_statement_pdf(
        author_name=_author_display_name(current),
        reflection=reflection,
    )
    # Resends mint a *fresh* 30-day preview URL — the earlier link's
    # jti isn't reused, so revoking one doesn't nuke the other.
    share_token_str, preview_url = await _mint_foundation_share_link(
        request=request,
        db=db,
        user=current,
        expire_days=_FOUNDATION_PREVIEW_EXPIRE_DAYS,
        recipient_email=original["recipient_email"],
        personal_note=original.get("personal_note"),
    )
    try:
        email_service.send_foundation_statement_share(
            to_email=original["recipient_email"],
            recipient_name=original.get("recipient_name"),
            sender_name=_author_display_name(current),
            sender_email=current.email or "",
            personal_note=original.get("personal_note"),
            pdf_bytes=pdf_bytes,
            preview_url=preview_url,
        )
    except email_service.EmailNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="Email isn't configured on this environment yet.",
        ) from exc
    except email_service.EmailSendError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc) or "Could not send email right now.",
        ) from exc

    # Fresh audit row so history + rate limit still work correctly.
    new_id = uuid.uuid4().hex[:12]
    await db.foundation_statement_shares.insert_one({
        "share_id": new_id,
        "user_id": current.user_id,
        "recipient_email": original["recipient_email"],
        "recipient_name": original.get("recipient_name"),
        "personal_note": original.get("personal_note"),
        "had_personal_note": bool(original.get("personal_note")),
        "preview_token": share_token_str,
        "resent_from": share_id,
        "sender_email": current.email,
        "created_at": datetime.now(timezone.utc),
    })
    return {
        "ok": True,
        "delivered_to": original["recipient_email"],
        "preview_url": preview_url,
        "share_id": new_id,
        "remaining_this_hour": max(
            0, _FOUNDATION_SHARE_HOURLY_LIMIT - recent_count - 1,
        ),
    }


# ============ Foundation Statement — "Read to me" voice playback ============
@router.get("/foundation-statement/voice/manifest")
async def foundation_statement_voice_manifest(
    request: Request,
    voice: Optional[str] = None,
    model: Optional[str] = None,
    current: UserPublic = Depends(get_current_user),
):
    """Return the ordered list of prompt sections the parent has
    filled in, along with a per-section audio URL. The frontend fires
    one audio request per section so each row can highlight as it
    plays. Rejects with 409 when the reflection is empty."""
    from foundation_statement_voice import (
        foundation_statement_sections,
        normalise_model,
        normalise_voice,
        SUPPORTED_VOICES,
        SUPPORTED_MODELS,
    )
    db = request.app.state.db
    reflection = await _load_reflection_for_current(db, current.user_id)
    sections = foundation_statement_sections(reflection)
    if not sections:
        raise HTTPException(
            status_code=409,
            detail=(
                "Your Foundation Statement is empty. Write at least one "
                "prompt on /reflection before using Read to me."
            ),
        )
    v = normalise_voice(voice)
    m = normalise_model(model)
    api_prefix = "/api/mediation/foundation-statement/voice/section"
    manifest = []
    for idx, sec in enumerate(sections):
        # Word count powers a smooth per-section duration estimate on
        # the client while the audio blob loads.
        word_count = len(sec["sanitized"].split())
        manifest.append({
            "index": idx,
            "key": sec["key"],
            "label": sec["label"],
            "text": sec["text"],
            "word_count": word_count,
            "audio_url": (
                f"{api_prefix}/{sec['key']}?voice={v}&model={m}"
            ),
        })
    return {
        "sections": manifest,
        "voice": v,
        "model": m,
        "supported_voices": list(SUPPORTED_VOICES),
        "supported_models": list(SUPPORTED_MODELS),
    }


@router.get("/foundation-statement/voice/section/{section_key}")
async def foundation_statement_voice_section(
    request: Request,
    section_key: str = Path(..., min_length=1, max_length=40),
    voice: Optional[str] = None,
    model: Optional[str] = None,
    current: UserPublic = Depends(get_current_user),
):
    """Stream a single section as MP3 audio. Cached per-user +
    per-content so repeated plays don't re-bill Emergent credits."""
    from foundation_statement_voice import (
        foundation_statement_sections,
        get_or_generate_section_audio,
        normalise_model,
        normalise_voice,
    )
    db = request.app.state.db
    reflection = await _load_reflection_for_current(db, current.user_id)
    sections = foundation_statement_sections(reflection)
    if not sections:
        raise HTTPException(
            status_code=409,
            detail="Your Foundation Statement is empty.",
        )
    # Look up the requested section + preserve its index (spoken
    # intro is only added to section 0).
    target: Optional[Dict[str, Any]] = None
    target_index = -1
    for idx, sec in enumerate(sections):
        if sec["key"] == section_key:
            target = sec
            target_index = idx
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Unknown section.")
    v = normalise_voice(voice)
    m = normalise_model(model)
    try:
        audio_bytes, cache_hit = await get_or_generate_section_audio(
            db,
            user_id=current.user_id,
            section=target,
            section_index=target_index,
            voice=v,
            model=m,
        )
    except RuntimeError as exc:
        # Missing key OR provider returned unexpected payload — both
        # are 502 (upstream issue), not 500.
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Voice-Cache": "hit" if cache_hit else "miss",
        },
    )


# ============ Foundation Statement — public shared preview ============
# These endpoints back a token-signed public preview page. Recipients
# (co-parents, mediators, attorneys) open `/foundation/shared/:token`
# in-browser after receiving the parent's email and see the statement
# rendered warmly + a "Read to me" voice player. No login required.
#
# Contract mirrors the Joint Agreement / Joint Report share pattern
# already shipped: JWT-signed token, revocable via `share_tokens`,
# 30-day default expiry.

async def _load_shared_foundation(
    *,
    token: str,
    db,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Decode + validate a foundation-statement share token. Returns
    (payload, sender_user_doc). Raises 404 for expired / revoked /
    invalid tokens so we never leak the reason to a bad actor."""
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "foundation_statement":
        raise HTTPException(404, "This link has expired or is invalid.")
    jti = payload.get("jti")
    if await is_share_token_revoked(db, jti):
        raise HTTPException(404, "This link has been revoked by the sender.")
    sender_id = payload.get("sub")
    if not sender_id:
        raise HTTPException(404, "This link is malformed.")
    user_doc = await db.users.find_one(
        {"user_id": sender_id},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1},
    )
    if not user_doc:
        raise HTTPException(404, "This link is no longer available.")
    return payload, user_doc


def _sender_display_name(user_doc: Dict[str, Any]) -> str:
    name = (user_doc.get("name") or "").strip()
    if name:
        return name
    email = (user_doc.get("email") or "").strip()
    if email:
        return email.split("@", 1)[0]
    return "A co-parent"


@router.get("/foundation-statement/shared/{token}")
async def get_shared_foundation_statement(
    token: str,
    request: Request,
):
    """Public — no auth. Returns the JSON payload of the parent's
    Foundation Statement for the token's holder. The four canonical
    prompts are surfaced as [{key, label, text}] so a React page can
    render them; the recipient never sees the parent's private
    metadata (email, user_id, other prep sections)."""
    from foundation_statement_voice import foundation_statement_sections
    from foundation_statement_analytics import (
        client_ip_from_request,
        record_preview_open,
    )
    db = request.app.state.db
    payload, user_doc = await _load_shared_foundation(token=token, db=db)
    reflection = await _load_reflection_for_current(db, user_doc["user_id"])
    sections = foundation_statement_sections(reflection)
    if not sections:
        # Sender wrote their reflection at share time but has since
        # cleared it — treat as revoked-shaped 404 so the recipient
        # doesn't see an empty document.
        raise HTTPException(
            404,
            "The sender has removed the content of their Foundation Statement.",
        )
    # Best-effort analytics — bot-filtered inside `record_preview_open`
    # so a link-unfurl doesn't inflate the count. NEVER blocks the
    # response.
    await record_preview_open(
        db,
        jti=payload.get("jti"),
        doc_owner_user_id=user_doc.get("user_id"),
        user_agent=request.headers.get("user-agent"),
        ip=client_ip_from_request(request),
        referer=request.headers.get("referer"),
    )
    # Look up the note the sender attached at mint time (recipient
    # name / personal note) — best-effort, present on newer rows.
    landing_note: Optional[str] = None
    if payload.get("jti"):
        row = await db.share_tokens.find_one(
            {"jti": payload["jti"]},
            {"_id": 0, "note": 1},
        )
        landing_note = (row or {}).get("note") or None
    return {
        "sender_name": _sender_display_name(user_doc),
        "sections": [
            {"key": s["key"], "label": s["label"], "text": s["text"]}
            for s in sections
        ],
        "sender_note": landing_note,
        "expires_at": (
            datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()
            if payload.get("exp") else None
        ),
    }


@router.get("/foundation-statement/shared/{token}/voice/manifest")
async def get_shared_foundation_voice_manifest(
    token: str,
    request: Request,
    voice: Optional[str] = None,
    model: Optional[str] = None,
):
    """Public voice manifest for a shared statement — same shape as
    the authenticated manifest, but the `audio_url` points at the
    public `/shared/{token}/voice/section/{key}` endpoint."""
    from foundation_statement_voice import (
        foundation_statement_sections,
        normalise_model,
        normalise_voice,
        SUPPORTED_MODELS,
        SUPPORTED_VOICES,
    )
    db = request.app.state.db
    _payload, user_doc = await _load_shared_foundation(token=token, db=db)
    reflection = await _load_reflection_for_current(db, user_doc["user_id"])
    sections = foundation_statement_sections(reflection)
    if not sections:
        raise HTTPException(404, "This statement has no content.")
    v = normalise_voice(voice)
    m = normalise_model(model)
    prefix = f"/api/mediation/foundation-statement/shared/{token}/voice/section"
    return {
        "sections": [
            {
                "index": idx,
                "key": sec["key"],
                "label": sec["label"],
                "text": sec["text"],
                "word_count": len(sec["sanitized"].split()),
                "audio_url": f"{prefix}/{sec['key']}?voice={v}&model={m}",
            }
            for idx, sec in enumerate(sections)
        ],
        "voice": v,
        "model": m,
        "supported_voices": list(SUPPORTED_VOICES),
        "supported_models": list(SUPPORTED_MODELS),
        "sender_name": _sender_display_name(user_doc),
    }


@router.get("/foundation-statement/shared/{token}/voice/section/{section_key}")
async def get_shared_foundation_voice_section(
    token: str,
    request: Request,
    section_key: str = Path(..., min_length=1, max_length=40),
    voice: Optional[str] = None,
    model: Optional[str] = None,
):
    """Public per-section MP3 stream for a shared Foundation Statement.
    Cache is shared with the authenticated per-user cache — same
    (user_id, section_key, text_sha, voice, model) key, so the parent
    tapping "Read to me" on their own /my-plan warms the cache for
    every mediator who later opens the shared link (and vice versa)."""
    from foundation_statement_voice import (
        foundation_statement_sections,
        get_or_generate_section_audio,
        normalise_model,
        normalise_voice,
    )
    db = request.app.state.db
    _payload, user_doc = await _load_shared_foundation(token=token, db=db)
    reflection = await _load_reflection_for_current(db, user_doc["user_id"])
    sections = foundation_statement_sections(reflection)
    if not sections:
        raise HTTPException(404, "This statement has no content.")
    target: Optional[Dict[str, Any]] = None
    target_index = -1
    for idx, sec in enumerate(sections):
        if sec["key"] == section_key:
            target = sec
            target_index = idx
            break
    if target is None:
        raise HTTPException(404, "Unknown section.")
    v = normalise_voice(voice)
    m = normalise_model(model)
    try:
        audio_bytes, cache_hit = await get_or_generate_section_audio(
            db,
            user_id=user_doc["user_id"],
            section=target,
            section_index=target_index,
            voice=v,
            model=m,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Voice-Cache": "hit" if cache_hit else "miss",
        },
    )


# ============ AI endpoints ============
@router.post("/analyze-communication")
async def analyze_communication(
    body: CommAnalysisRequest,
    current: UserPublic = Depends(require_ai_notice),
):
    try:
        result = await ai_service.analyze_communication(
            body.answers or {}, body.text or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")


@router.post("/reframe")
async def reframe(
    body: dict,
    current: UserPublic = Depends(require_ai_notice),
):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    try:
        return await ai_service.reframe_message(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI reframe failed: {e}")


# Section-level coaching insights — replaces bare scores with 3 warm insights
# (strength, growth area, next step). Called from ReadinessCheck, CommStyle,
# and MyPlan. Section values: readiness | comm-style | overall
_ALLOWED_COACHING_SECTIONS = {"readiness", "comm-style", "overall"}


@router.post("/section-coaching")
async def section_coaching(
    body: dict,
    current: UserPublic = Depends(require_ai_notice),
):
    section = (body.get("section") or "").strip()
    payload = body.get("data") or {}
    if section not in _ALLOWED_COACHING_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"section must be one of {sorted(_ALLOWED_COACHING_SECTIONS)}",
        )
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="data must be a non-empty object")
    try:
        return await ai_service.generate_section_coaching(section, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coaching failed: {e}")


@router.post("/summary")
async def generate_summary(
    request: Request,
    current: UserPublic = Depends(require_ai_notice),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    if not prep.get("child_goals") and not prep.get("issues"):
        raise HTTPException(
            status_code=400,
            detail="Please complete at least Child Goals or Issues first.",
        )
    previous = await _previous_doc(db, "summaries", current.user_id)
    # Compute deterministic readiness scores from raw prep data (0-100 per
    # dimension, plus overall). The AI narrative interprets these numbers
    # but never changes them.
    from readiness_scoring import compute_readiness  # local import
    readiness = compute_readiness(prep)
    try:
        summary = await ai_service.generate_summary(prep, current.name, previous, readiness=readiness)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summary failed: {e}")

    # Force the deterministic values onto the summary — trust the math, not the LLM.
    summary["readiness_score"] = readiness["overall"]
    summary["readiness_label"] = readiness["label"]
    summary["readiness"] = readiness

    summary_id = f"sum_{uuid.uuid4().hex[:12]}"
    doc = {
        **summary,
        mediation_sharing.CLEAN: True,
        "summary_id": summary_id,
        "user_id": current.user_id,
        "generated_at": _now(),
        "prep_snapshot": _snapshot_prep(prep),
        "previous_summary_id": previous.get("summary_id") if previous else None,
    }
    await db.summaries.insert_one(doc.copy())
    doc.pop("_id", None)

    # Schedule a 7-day post-event "How was mediation?" survey (idempotent —
    # only the first summary per user actually creates a doc; subsequent
    # summaries no-op).
    try:
        import survey_routes  # local import to avoid circular at module load
        await survey_routes.schedule_post_event_survey(
            db,
            user_id=current.user_id,
            email=current.email if not current.is_guest else None,
            name=current.name,
            summary_id=summary_id,
        )
    except Exception:  # noqa: BLE001
        # Survey scheduling must never block summary generation.
        pass

    # Also schedule a 14-day check-in with a personalised journal recap.
    try:
        import checkin_routes
        await checkin_routes.schedule_post_summary_checkin(
            db,
            user_id=current.user_id,
            email=current.email if not current.is_guest else None,
            name=current.name,
            summary_id=summary_id,
        )
    except Exception:  # noqa: BLE001
        pass

    return doc


@router.get("/summaries")
async def list_summaries(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.summaries.find(
        {"user_id": current.user_id}, {"_id": 0, "prep_snapshot": 0, "share_copy": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/summary/{summary_id}/pdf")
async def download_summary_pdf(
    summary_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    excluded: Optional[str] = None,
    sign: bool = False,
    note: str = "",
):
    db = request.app.state.db
    summary = await db.summaries.find_one(
        {"summary_id": summary_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    prep = await _load_prep(db, current.user_id)
    ex_list = _resolve_excluded("summary", excluded, summary.get("visibility"))
    from pdf_signing import sign_kwargs
    pdf_bytes = pdf_service.build_summary_pdf(
        user_name=current.name,
        summary=summary,
        child_goals=prep.get("child_goals"),
        mediation_date=current.mediation_date,
        excluded_sections=ex_list,
        **sign_kwargs(sign, current.name, note),
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="mediation_summary_{summary_id}.pdf"'
        },
    )


# ============ Certificate of Completion ============
class CertificateRequest(BaseModel):
    # Optional override — parents can dedicate the certificate to a display
    # name that differs from their account name (e.g. married name, preferred
    # name). Falls back to the account name when omitted or blank.
    name: Optional[str] = Field(default=None, max_length=120)


@router.get("/certificate/eligibility")
async def certificate_eligibility(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Report whether the parent has completed enough of the program to earn
    a certificate. The threshold is intentionally forgiving: 5 of 6 core prep
    steps done. Demo/guest users are always eligible so they can preview.
    """
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    completed = prep.get("completed") or {}
    core_steps = ["child_goals", "issues", "priority", "comm_style", "readiness", "reflection"]
    done = [k for k in core_steps if completed.get(k)]
    threshold = 5
    is_eligible = current.is_guest or len(done) >= threshold
    return {
        "eligible": is_eligible,
        "is_guest": current.is_guest,
        "completed_steps": done,
        "required_steps": core_steps,
        "threshold": threshold,
        "display_name": current.name or "",
    }


@router.get("/certificate/preview")
async def preview_certificate(
    request: Request,
    current: UserPublic = Depends(get_current_user),
    name: Optional[str] = None,
):
    """Return the composed certificate as an inline PNG for on-screen preview."""
    display = (name or current.name or "").strip()
    # Foundation Ready ribbon is stamped when the parent has all 5 progress
    # milestones lit at generation time. Best-effort — never fail the
    # preview over a progress-lookup hiccup.
    foundation_ready = False
    try:
        progress = await compute_progress(request.app.state.db, current)
        foundation_ready = bool(progress.get("foundation_ready"))
    except Exception:  # noqa: BLE001
        pass
    png = certificate_service.build_certificate_png(
        display, foundation_ready=foundation_ready,
    )
    return StreamingResponse(
        BytesIO(png),
        media_type="image/png",
        headers={"Cache-Control": "no-store",
                 "X-Foundation-Ready": "1" if foundation_ready else "0"},
    )


@router.post("/certificate/download")
async def download_certificate(
    body: CertificateRequest,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Return the certificate as a downloadable PDF. Any authenticated user
    (including a demo/guest) can generate one; the demo watermark on the
    account itself communicates the sandbox state, not this document."""
    display = (body.name or current.name or "").strip()
    if not display:
        display = "Committed Co-Parent"
    foundation_ready = False
    try:
        progress = await compute_progress(request.app.state.db, current)
        foundation_ready = bool(progress.get("foundation_ready"))
    except Exception:  # noqa: BLE001
        pass
    pdf_bytes = certificate_service.build_certificate_pdf(
        display, foundation_ready=foundation_ready,
    )

    # Best-effort audit trail — never fail the download over logging.
    try:
        await request.app.state.db.certificates_issued.insert_one(
            {
                "user_id": current.user_id,
                "display_name": display,
                "is_guest": current.is_guest,
                "issued_at": _now(),
            }
        )
    except Exception:  # noqa: BLE001
        pass

    safe_name = "".join(c if c.isalnum() else "_" for c in display).strip("_") or "certificate"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SA_CoParents_Certificate_{safe_name}.pdf"'
        },
    )


# ============ Co-Parenting Agreement Draft ============
@router.post("/agreement")
async def generate_agreement(
    request: Request,
    current: UserPublic = Depends(require_ai_notice),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    if not prep.get("child_goals") and not prep.get("issues"):
        raise HTTPException(
            status_code=400,
            detail="Please complete at least Child Goals or Issues first.",
        )
    # Build a focused subset — goals, issues, priority only.
    focused = {
        "child_goals": prep.get("child_goals"),
        "issues": prep.get("issues"),
        "priority": prep.get("priority"),
    }
    previous = await _previous_doc(db, "agreements", current.user_id)
    from readiness_scoring import compute_readiness  # local import
    readiness = compute_readiness(prep)
    try:
        agreement = await ai_service.generate_agreement_draft(
            focused, current.name, previous, readiness=readiness
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI agreement failed: {e}")

    # Attach the deterministic readiness bundle so the frontend can draw bars.
    agreement["readiness"] = readiness

    agreement_id = f"agr_{uuid.uuid4().hex[:12]}"
    doc = {
        **agreement,
        mediation_sharing.CLEAN: True,
        "agreement_id": agreement_id,
        "user_id": current.user_id,
        "generated_at": _now(),
        "prep_snapshot": _snapshot_prep(prep),
        "previous_agreement_id": previous.get("agreement_id") if previous else None,
    }
    await db.agreements.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/agreements")
async def list_agreements(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.agreements.find(
        {"user_id": current.user_id}, {"_id": 0, "prep_snapshot": 0, "share_copy": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/agreement/{agreement_id}/pdf")
async def download_agreement_pdf(
    agreement_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    excluded: Optional[str] = None,
    sign: bool = False,
    note: str = "",
):
    db = request.app.state.db
    agreement = await db.agreements.find_one(
        {"agreement_id": agreement_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    ex_list = _resolve_excluded("agreement", excluded, agreement.get("visibility"))
    from pdf_signing import sign_kwargs
    pdf_bytes = pdf_service.build_agreement_pdf(
        user_name=current.name,
        agreement=agreement,
        mediation_date=current.mediation_date,
        excluded_sections=ex_list,
        **sign_kwargs(sign, current.name, note),
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="coparenting_agreement_{agreement_id}.pdf"'
        },
    )


# ============ Shareable download links (no-auth, signed) ============
class ShareLinkBody(BaseModel):
    excluded: Optional[List[str]] = None
    expire_days: Optional[int] = 7  # 1 | 7 | 30 | None ("never")
    label: Optional[str] = None


class VisibilityBody(BaseModel):
    excluded: List[str] = Field(default_factory=list)


def _resolve_excluded(
    report_type: str,
    query_csv: Optional[str],
    stored_visibility: Optional[Dict[str, Any]],
) -> List[str]:
    """Merge three sources of section-visibility with priority:
      1. Query string (per-request override)
      2. Persisted visibility on the doc
      3. Empty (nothing excluded)
    Always cleaned/validated against the report type's catalog + locked keys."""
    raw: List[str] = []
    if query_csv is not None:
        raw = [x for x in query_csv.split(",") if x]
    elif stored_visibility:
        raw = list((stored_visibility or {}).get("excluded") or [])
    return report_visibility.clean_excluded(report_type, raw)


@router.get("/reports/sections/{report_type}")
async def get_section_catalog(report_type: str):
    """Return the section catalog (used by the frontend visibility panel)."""
    sections = report_visibility.REPORT_SECTIONS.get(report_type)
    if sections is None:
        raise HTTPException(status_code=404, detail="Unknown report type")
    return {"report_type": report_type, "sections": sections}


@router.patch("/summary/{summary_id}/visibility")
async def update_summary_visibility(
    summary_id: str,
    body: VisibilityBody,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    ex = report_visibility.clean_excluded("summary", body.excluded)
    result = await db.summaries.update_one(
        {"summary_id": summary_id, "user_id": current.user_id},
        {"$set": {"visibility": {"excluded": ex, "updated_at": _now()}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {"summary_id": summary_id, "excluded": ex}


@router.patch("/agreement/{agreement_id}/visibility")
async def update_agreement_visibility(
    agreement_id: str,
    body: VisibilityBody,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    ex = report_visibility.clean_excluded("agreement", body.excluded)
    result = await db.agreements.update_one(
        {"agreement_id": agreement_id, "user_id": current.user_id},
        {"$set": {"visibility": {"excluded": ex, "updated_at": _now()}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agreement not found")
    return {"agreement_id": agreement_id, "excluded": ex}


@router.post("/summary/{summary_id}/share-link")
async def create_summary_share_link(
    summary_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    body: Optional[ShareLinkBody] = None,
):
    db = request.app.state.db
    summary = await db.summaries.find_one(
        {"summary_id": summary_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    incoming = (body.excluded if body else None)
    if incoming is None:
        incoming = (summary.get("visibility") or {}).get("excluded") or []
    ex = report_visibility.clean_excluded("summary", incoming)
    expire_days = body.expire_days if body else 7
    await mediation_sharing.prepare(db, "summary", summary, current)
    token = create_share_token("summary", summary_id, current.user_id,
                               excluded_sections=ex, expire_days=expire_days, extra_claims={"clean": 1})
    payload = decode_share_token(token) or {}
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) if payload.get("exp") else None
    await record_share_token(db, jti=payload.get("jti"), user_id=current.user_id,
                             doc_type="summary", doc_id=summary_id,
                             expires_at=expires_at,
                             label=(body.label if body else None))
    return {"token": token, "jti": payload.get("jti"),
            "path": f"/api/mediation/shared/{token}", "excluded": ex,
            "expires_at": expires_at.isoformat() if expires_at else None}


@router.post("/agreement/{agreement_id}/share-link")
async def create_agreement_share_link(
    agreement_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    body: Optional[ShareLinkBody] = None,
):
    db = request.app.state.db
    agreement = await db.agreements.find_one(
        {"agreement_id": agreement_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    incoming = (body.excluded if body else None)
    if incoming is None:
        incoming = (agreement.get("visibility") or {}).get("excluded") or []
    ex = report_visibility.clean_excluded("agreement", incoming)
    expire_days = body.expire_days if body else 7
    await mediation_sharing.prepare(db, "agreement", agreement, current)
    token = create_share_token("agreement", agreement_id, current.user_id,
                               excluded_sections=ex, expire_days=expire_days, extra_claims={"clean": 1})
    payload = decode_share_token(token) or {}
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) if payload.get("exp") else None
    await record_share_token(db, jti=payload.get("jti"), user_id=current.user_id,
                             doc_type="agreement", doc_id=agreement_id,
                             expires_at=expires_at,
                             label=(body.label if body else None))
    return {"token": token, "jti": payload.get("jti"),
            "path": f"/api/mediation/shared/{token}", "excluded": ex,
            "expires_at": expires_at.isoformat() if expires_at else None}


async def _shared_pdf(db, kind: str, doc: Dict[str, Any], user_name: str, mediation_date, excluded) -> bytes:
    view, ex = mediation_sharing.shared_view(kind, doc, excluded)
    if kind == "summary":
        prep = await _load_prep(db, doc["user_id"])
        return pdf_service.build_summary_pdf(user_name=user_name or "", summary=view, child_goals=prep.get("child_goals"),
                                             mediation_date=mediation_date, excluded_sections=ex)
    return pdf_service.build_agreement_pdf(user_name=user_name or "", agreement=view, mediation_date=mediation_date,
                                           excluded_sections=ex)


@router.get("/shared/{token}")
async def download_shared_pdf(
    token: str,
    request: Request,
):
    """Public endpoint: anyone with a valid signed token can download the PDF."""
    payload = decode_share_token(token)
    if not payload:
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db = request.app.state.db
    if await is_share_token_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=404, detail="This link has been revoked by the sender.")
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="This link is no longer valid.")

    doc_type = payload["doc_type"]
    doc_id = payload["doc_id"]
    if doc_type not in mediation_sharing.COLL:
        raise HTTPException(status_code=404, detail="Unknown document type")
    # Links made before the privacy update can't be cleaned: the parent can make a new one.
    if not payload.get("clean"):
        raise HTTPException(status_code=410, detail=mediation_sharing.OLD_LINK)
    coll, key = mediation_sharing.COLL[doc_type]
    doc = await db[coll].find_one({key: doc_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    pdf_bytes = await _shared_pdf(db, doc_type, doc, user.get("name", ""), user.get("mediation_date"), payload.get("ex"))
    filename = mediation_sharing.FILENAME[doc_type]

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ============ Things I Can Improve On ============
@router.post("/improvement-plan")
async def generate_improvement_plan_route(
    request: Request,
    current: UserPublic = Depends(require_ai_notice),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    comm = prep.get("comm_style")
    readiness = prep.get("readiness")
    if not comm and not readiness:
        raise HTTPException(
            status_code=400,
            detail="Please complete the Communication and Readiness steps first.",
        )
    previous = await _previous_doc(db, "improvement_plans", current.user_id)
    from readiness_scoring import compute_readiness  # local import
    readiness_scores = compute_readiness(prep)
    try:
        plan = await ai_service.generate_improvement_plan(
            comm, readiness, current.name, previous, readiness_scores=readiness_scores
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI plan failed: {e}")

    plan["readiness"] = readiness_scores

    plan_id = f"imp_{uuid.uuid4().hex[:12]}"
    doc = {
        **plan,
        "plan_id": plan_id,
        "user_id": current.user_id,
        "generated_at": _now(),
        "prep_snapshot": _snapshot_prep(prep),
        "previous_plan_id": previous.get("plan_id") if previous else None,
    }
    await db.improvement_plans.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/improvement-plans")
async def list_improvement_plans(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.improvement_plans.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


# ============ Device registration (mobile push notifications) ============
class DeviceRegistration(BaseModel):
    token: str = Field(min_length=4, max_length=4096)
    platform: str = Field(min_length=1, max_length=20)  # "ios" | "android" | "web"


@router.post("/devices/register")
async def register_device(
    body: DeviceRegistration,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    # Upsert by (user_id, token) so re-registration is idempotent.
    await db.devices.update_one(
        {"user_id": current.user_id, "token": body.token},
        {
            "$set": {
                "user_id": current.user_id,
                "token": body.token,
                "platform": body.platform,
                "updated_at": _now(),
            },
            "$setOnInsert": {"registered_at": _now()},
        },
        upsert=True,
    )
    return {"ok": True}


# ============ Email to mediator ============
class MediatorEmailRequest(BaseModel):
    mediator_email: EmailStr
    mediator_name: Optional[str] = Field(default=None, max_length=120)
    summary_id: Optional[str] = None
    agreement_id: Optional[str] = None


@router.get("/email/status")
async def email_status(current: UserPublic = Depends(get_current_user)):
    return {"configured": email_service.is_configured()}


@router.post("/email-mediator")
async def email_mediator(
    body: MediatorEmailRequest,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db

    # Spam guardrail for demo/guest accounts. Permanent accounts have no
    # daily cap — they're identified, so misuse is recoverable.
    if current.is_guest:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        recent = await db.mediator_emails.count_documents(
            {"user_id": current.user_id, "sent_at": {"$gte": since}}
        )
        if recent >= GUEST_EMAIL_DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"You've already sent {recent} email(s) today from a demo session. "
                    "Set up a free account to send more."
                ),
            )

    if not body.summary_id and not body.agreement_id:
        raise HTTPException(
            status_code=400,
            detail="Please choose at least one document to attach.",
        )

    attachments: list = []
    doc_labels: list = []

    # The mediator gets the shared copy: no safety text, reflection answers or readiness score.
    for kind, doc_id, label, missing in (("summary", body.summary_id, "Mediation Summary", "Summary not found"),
                                         ("agreement", body.agreement_id, "Co-Parenting Agreement Draft", "Agreement draft not found")):
        if not doc_id:
            continue
        coll, key = mediation_sharing.COLL[kind]
        doc = await db[coll].find_one({key: doc_id, "user_id": current.user_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail=missing)
        await mediation_sharing.prepare(db, kind, doc, current)
        excluded = (doc.get("visibility") or {}).get("excluded")
        attachments.append((mediation_sharing.FILENAME[kind],
                            await _shared_pdf(db, kind, doc, current.name, current.mediation_date, excluded)))
        doc_labels.append(label)

    try:
        email_service.send_mediator_email(
            to_email=body.mediator_email,
            mediator_name=body.mediator_name,
            user_name=current.name or "",
            user_email=current.email,
            attachments=attachments,
            doc_labels=doc_labels,
        )
    except email_service.EmailNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
    except email_service.EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Log the send (best-effort, not fatal).
    try:
        await db.mediator_emails.insert_one(
            {
                "user_id": current.user_id,
                "mediator_email": body.mediator_email,
                "mediator_name": body.mediator_name,
                "summary_id": body.summary_id,
                "agreement_id": body.agreement_id,
                "doc_labels": doc_labels,
                "sent_at": _now(),
            }
        )
    except Exception:
        pass

    return {"ok": True, "sent_to": body.mediator_email, "documents": doc_labels}


# ============ Resources (static seed) ============
RESOURCES = [
    {
        "id": "r2",
        "category": "High Conflict",
        "title": "Disengaging from Provocation",
        "description": "How to recognize bait and respond from a place of calm.",
        "kind": "video",
        "url": "https://youtu.be/7gjQnnUxLBs?si=ITTTAndKFYDaqugb",
    },
    {
        "id": "r8",
        "category": "Parallel Parenting",
        "title": "Parallel Parenting Explained (Video)",
        "description": "A clear walkthrough of how parallel parenting works in high-conflict situations and why it can be safer for the child than traditional co-parenting.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=b0IL8baFUmQ",
    },
    {
        "id": "r10",
        "category": "Parallel Parenting",
        "title": "Moving from Co-Parenting to Parallel Parenting (Video)",
        "description": "When traditional co-parenting isn't working, this walkthrough explains how to transition to a parallel parenting model and what to expect along the way.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=Tj9zCQgLnxA",
    },
    {
        "id": "r4",
        "category": "Communication",
        "title": "I-Statements for Co-Parents (Video)",
        "description": "A short walkthrough on using I-statements to express needs without triggering defensiveness — a key skill for keeping co-parenting conversations productive.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=gG25Kq_3gmg",
    },
    {
        "id": "r5",
        "category": "Rebuilding Trust",
        "title": "Small Consistent Wins (Video)",
        "description": "Trust is rebuilt through small, predictable actions over time. This short video unpacks how repeated, low-stakes follow-through rebuilds credibility with your co-parent and your child.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=k-k8lTJLFVU",
    },
    {
        "id": "r6",
        "category": "Parenting After Divorce",
        "title": "Helping Your Child Feel Safe",
        "description": "Practical scripts and rituals that anchor your child during transitions.",
        "kind": "video",
        "url": "https://youtu.be/oKd7PI_GjSs?si=xhm3g3pUjW1NLU3c",
    },
    {
        "id": "r7",
        "category": "Communication",
        "title": "BIFF Response Method — Bill Eddy",
        "description": "Watch Bill Eddy walk through the BIFF method (Brief, Informative, Friendly, Firm) for replying to high-conflict messages without escalating.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=ggXhQLihi54",
    },
    {
        "id": "r9",
        "category": "Communication",
        "title": "BIFF — Bill Eddy's book (Amazon)",
        "description": "Get Bill Eddy's pocket-sized guide to writing Brief, Informative, Friendly, Firm responses to hostile emails, texts, and social media — perfect for high-conflict co-parenting.",
        "kind": "article",
        "url": "https://www.amazon.com/s?k=Bill+Eddy+BIFF&i=stripbooks",
    },
]


@router.get("/resources")
async def get_resources():
    return RESOURCES
