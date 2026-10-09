"""
Professionals directory + parent-initiated "send my alignment code to
a professional" flow.

Endpoints (all under `/api`):

  * GET  /professionals
        Public. Returns the curated list of professionals a parent
        can request a Co-Parenting Agreement from. Sourced from the
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
            "San Antonio, Texas 78232",
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
    """
    Idempotent bootstrap:
      * If the collection is empty → insert every entry in the
        initial roster.
      * If an initial-roster entry already exists → refresh the
        canonical fields (name, credentials, license, email,
        address, bio) so a founder-side update in this file
        propagates to production without a manual DB touch.
        `active` / `sort_order` / `phone` / `website` are NOT
        refreshed so an admin toggling those in the DB is not
        clobbered by a redeploy.
    """
    for entry in _INITIAL_ROSTER:
        existing = await db[_COLL].find_one(
            {"professional_id": entry["professional_id"]}, {"_id": 1}
        )
        if not existing:
            doc = {**entry, "created_at": _now(), "updated_at": _now()}
            try:
                await db[_COLL].insert_one(doc)
                logger.info("professionals seed inserted %s", entry["professional_id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("professionals seed insert failed: %s", exc)
            continue
        # Refresh canonical directory fields only — leave admin-
        # controlled toggles alone.
        refresh_fields = {
            k: entry[k]
            for k in (
                "name",
                "credentials",
                "license",
                "email",
                "address_lines",
                "city",
                "state",
                "bio",
            )
            if k in entry
        }
        refresh_fields["updated_at"] = _now()
        try:
            await db[_COLL].update_one(
                {"professional_id": entry["professional_id"]},
                {"$set": refresh_fields},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("professionals seed refresh failed: %s", exc)


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


# ---------------------- Public intro voice (marketing) ---------------------- #
# Streams an ElevenLabs-voiced explainer of what SA CoParents is + the
# four-step Align workflow. Public — no auth — because the surface it
# powers (/for-professionals) is a public marketing page. The audio is
# cached globally per (script_sha, voice, model) so re-plays are free
# after the first render.

@router.get("/for-professionals/intro-audio/manifest")
async def for_professionals_intro_manifest():
    """Return the intro script + audio URL so the frontend can display
    a transcript beside the player (accessibility + skimming)."""
    from professionals_intro_voice import (
        INTRO_SCRIPT,
        DEFAULT_VOICE,
        DEFAULT_MODEL,
        SUPPORTED_VOICES,
        SUPPORTED_MODELS,
    )
    audio_url = (
        f"/api/for-professionals/intro-audio"
        f"?voice={DEFAULT_VOICE}&model={DEFAULT_MODEL}"
    )
    preview_url_base = (
        f"/api/for-professionals/intro-audio/preview"
        f"?model={DEFAULT_MODEL}"
    )
    return {
        "transcript": INTRO_SCRIPT,
        "audio_url": audio_url,
        "preview_url_base": preview_url_base,
        "voice": DEFAULT_VOICE,
        "model": DEFAULT_MODEL,
        "supported_voices": list(SUPPORTED_VOICES),
        "supported_models": list(SUPPORTED_MODELS),
    }


@router.get("/for-professionals/intro-audio")
async def for_professionals_intro_audio(
    request: Request,
    voice: Optional[str] = None,
    model: Optional[str] = None,
):
    """Stream the ElevenLabs-voiced intro as MP3. Public endpoint —
    same audio served to every visitor of /for-professionals."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    from professionals_intro_voice import (
        get_or_generate_intro_audio,
        normalise_model,
        normalise_voice,
    )
    db = request.app.state.db
    v = normalise_voice(voice)
    m = normalise_model(model)
    try:
        audio_bytes, cache_hit = await get_or_generate_intro_audio(
            db, voice=v, model=m,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            # Public marketing asset — safe to cache in the browser + CDN.
            "Cache-Control": "public, max-age=86400",
            "X-Voice-Cache": "hit" if cache_hit else "miss",
        },
    )


@router.get("/for-professionals/intro-audio/preview")
async def for_professionals_intro_audio_preview(
    request: Request,
    voice: Optional[str] = None,
    model: Optional[str] = None,
):
    """~3-second voice-preview endpoint so a visitor can hear each
    ElevenLabs voice before committing to the full 60-second intro.
    Uses the same MongoDB cache collection as the full intro but with
    a `preview` cache-key suffix, so first play per voice bills once
    (~50KB of ElevenLabs characters) and every subsequent play is
    served from cache."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    from professionals_intro_voice import (
        get_or_generate_preview_audio,
        normalise_model,
        normalise_voice,
    )
    db = request.app.state.db
    v = normalise_voice(voice)
    m = normalise_model(model)
    try:
        audio_bytes, cache_hit = await get_or_generate_preview_audio(
            db, voice=v, model=m,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Voice-Cache": "hit" if cache_hit else "miss",
            "X-Voice-Kind": "preview",
        },
    )


# =========================== admin editor =========================== #
# Read-write directory management gated on `require_admin`.
# Professionals cannot self-sign-up — every add / update passes
# through an authenticated ADMIN_EMAILS session, matching the
# founder's guardrail that "professionals have to be added with
# permission".


from analytics_routes import require_admin  # noqa: E402


class AdminProfessionalUpsertBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    credentials: str = Field(..., min_length=1, max_length=400)
    license: Optional[str] = Field(default=None, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    website: Optional[str] = Field(default=None, max_length=200)
    address_lines: List[str] = Field(default_factory=list)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=40)
    bio: Optional[str] = Field(default=None, max_length=2000)
    sort_order: int = Field(default=100)
    active: bool = Field(default=True)


class AdminProfessionalPatchBody(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    credentials: Optional[str] = Field(default=None, min_length=1, max_length=400)
    license: Optional[str] = Field(default=None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=40)
    website: Optional[str] = Field(default=None, max_length=200)
    address_lines: Optional[List[str]] = None
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=40)
    bio: Optional[str] = Field(default=None, max_length=2000)
    sort_order: Optional[int] = None
    active: Optional[bool] = None


def _slugify_professional_id(name: str, existing: set) -> str:
    """
    Human-friendly professional_id derived from the name. Falls back
    to appending an integer suffix if collisions occur.
    """
    base = "".join(
        ch.lower() if ch.isalnum() else "-"
        for ch in (name or "professional")
    )
    base = "-".join(seg for seg in base.split("-") if seg)[:60] or "professional"
    if base not in existing:
        return base
    idx = 2
    while f"{base}-{idx}" in existing:
        idx += 1
    return f"{base}-{idx}"


@router.get("/admin/professionals")
async def admin_list_professionals(
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Admin listing — includes inactive rows and sort_order."""
    await _ensure_seeded(db)
    cursor = db[_COLL].find({}).sort([("sort_order", 1), ("name", 1)])
    professionals = []
    async for p in cursor:
        professionals.append(
            {
                **_public_shape(p),
                "active": bool(p.get("active", True)),
                "sort_order": p.get("sort_order", 100),
                "updated_at": (
                    p.get("updated_at").isoformat()
                    if isinstance(p.get("updated_at"), datetime)
                    else None
                ),
            }
        )
    return {"professionals": professionals}


@router.post("/admin/professionals")
async def admin_create_professional(
    body: AdminProfessionalUpsertBody,
    admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Admin-only professional creation. Every add is deliberate —
    the frontend surfaces an "added with permission" note so an
    admin never accidentally publishes a directory entry.
    """
    ids = {
        doc["professional_id"]
        async for doc in db[_COLL].find({}, {"professional_id": 1})
    }
    professional_id = _slugify_professional_id(body.name, ids)
    doc = {
        "professional_id": professional_id,
        **body.model_dump(),
        "created_at": _now(),
        "updated_at": _now(),
        "created_by_admin_email": admin.email,
    }
    await db[_COLL].insert_one(doc)
    logger.info(
        "professionals admin_create id=%s by=%s", professional_id, admin.email
    )
    fresh = await db[_COLL].find_one({"professional_id": professional_id})
    return {
        **_public_shape(fresh),
        "active": bool(fresh.get("active", True)),
        "sort_order": fresh.get("sort_order", 100),
    }


@router.patch("/admin/professionals/{professional_id}")
async def admin_update_professional(
    body: AdminProfessionalPatchBody,
    professional_id: str = Path(..., min_length=1, max_length=64),
    admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Admin-only partial update. Also the entry point for
    deactivation: send `{"active": false}` to hide a professional
    from the public directory without deleting the row (audit
    trail preserved).
    """
    # `exclude_unset` keeps `active=False` in the patch when the
    # admin explicitly sends it, but drops keys the admin didn't
    # touch. That's the shape we want for a PATCH.
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields provided")
    patch["updated_at"] = _now()
    patch["last_edited_by_admin_email"] = admin.email
    result = await db[_COLL].update_one(
        {"professional_id": professional_id}, {"$set": patch}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Professional not found")
    logger.info(
        "professionals admin_update id=%s by=%s fields=%s",
        professional_id,
        admin.email,
        list(patch.keys()),
    )
    fresh = await db[_COLL].find_one({"professional_id": professional_id})
    return {
        **_public_shape(fresh),
        "active": bool(fresh.get("active", True)),
        "sort_order": fresh.get("sort_order", 100),
    }



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
        "and would like to invite you to prepare a Co-Parenting Agreement.</p>"
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
        "and would like to invite you to prepare a Co-Parenting Agreement.",
        "",
        f"Alignment Code: {code}",
        f"Open on SA CoParents Align: {join_url}",
        "",
        "Individual responses remain private. The Co-Parenting Agreement is",
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
