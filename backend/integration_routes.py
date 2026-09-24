"""
Sibling integration for sacoparentsalign.com.

Endpoints on `/api`:
  1. POST /link-codes  — parent-authenticated (JWT). Mints a single-use
     8-char code, 15-minute TTL. Response: {"code": "AB3K7Q2Z"}.
  2. POST /integrations/verify-link-code — server-to-server, gated on
     the `X-Integration-Key` header (constant-time comparison against
     `INTEGRATION_SHARED_SECRET`). Body: {"code": "…"}. Consumes the
     code (single-use) and returns {"email": "…"}.
  3. GET /integrations/export-assessments?email=… — server-to-server,
     same header gate. Returns a JSON bundle of the parent's
     Situation Snapshot, Foundation Statement, and the three-pronged
     Special Needs deep-dive artefacts (Medical, Educational,
     Psychological).
  4. GET /integrations/foundation-statement.pdf?email=… (Iter208) —
     server-to-server, same header gate. Streams the parent's
     Foundation Statement PDF, rendered by the SAME
     `build_foundation_statement_pdf` builder the parent-facing
     `/api/mediation/foundation-statement.pdf` uses. Lets Align embed
     the app-branded PDF directly instead of re-rendering from raw
     JSON — both sites automatically stay visually in sync.

Design notes
------------
* Codes are minted from a curated alphabet (uppercase letters + digits
  minus ambiguous glyphs I/O/1/0) to keep them shareable over voice.
* Codes are stored as bcrypt hashes; the raw code never touches the
  database, matching the pattern used elsewhere in `auth.py` for OTP
  codes.
* Rate limit: 5 mint attempts per parent per hour to keep this from
  becoming a phishing vector.
* HMAC comparison uses `hmac.compare_digest` for constant-time
  equality — the header value is treated as untrusted.
* Never raise details that would let an attacker distinguish
  "unknown email" from "no assessments"; the endpoint returns 404
  once with a generic body.
"""
from __future__ import annotations

import hmac
import logging
import os
import secrets
import string
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Any, Dict, Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from auth import UserPublic, get_current_user, get_db
from safety_gate import require_ipv_clearance


router = APIRouter(tags=["integrations"])
logger = logging.getLogger(__name__)


# Human-friendly, easy-to-say-out-loud code format: SA-XXXXXX.
# Six digits keeps the space large (1,000,000) while staying trivially
# readable over the phone. The "SA-" prefix is cosmetic on the way in
# — the server normalises before hashing so a parent who types
# "sa 482731" or "SA482731" still matches.
_CODE_PREFIX = "SA-"
_CODE_DIGITS = 6
_CODE_LENGTH = len(_CODE_PREFIX) + _CODE_DIGITS  # "SA-482731" == 9 chars
_CODE_TTL_MINUTES = 15
_MINT_RATE_LIMIT_PER_HOUR = 5

_COLL = "link_codes"


# ------------------------------- helpers ------------------------------- #

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code() -> str:
    digits = "".join(secrets.choice(string.digits) for _ in range(_CODE_DIGITS))
    return f"{_CODE_PREFIX}{digits}"


def _normalise_code(raw: str) -> str:
    """
    Accept the code the way a human would paste it: `SA-482731`, `SA
    482731`, `sa482731`, or plain `482731`. Everything non-digit is
    stripped and the canonical `SA-` prefix is re-attached so the
    bcrypt lookup finds the mint we stored.
    """
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != _CODE_DIGITS:
        return ""
    return f"{_CODE_PREFIX}{digits}"


def _hash_code(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_code(code: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _shared_secret() -> Optional[str]:
    """Read the shared secret at request time so tests can monkey-patch env."""
    return os.environ.get("INTEGRATION_SHARED_SECRET")


def _verify_integration_key(header_value: Optional[str]) -> None:
    """
    Constant-time comparison of the `X-Integration-Key` header against
    `INTEGRATION_SHARED_SECRET`. Raises 401 on mismatch or when the
    secret is not configured on the server.
    """
    expected = _shared_secret()
    if not expected:
        logger.error("INTEGRATION_SHARED_SECRET is not set — refusing request")
        raise HTTPException(status_code=503, detail="Integration not configured")
    provided = header_value or ""
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid integration key")


async def _mint_rate_limited(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    since = _now() - timedelta(hours=1)
    count = await db[_COLL].count_documents(
        {"user_id": user_id, "minted_at": {"$gte": since}}
    )
    return count >= _MINT_RATE_LIMIT_PER_HOUR


# ------------------------------- schemas ------------------------------- #

class LinkCodeMintRequest(BaseModel):
    # Which assessment lane the parent is inviting the co-parent on.
    # Optional — the mint works without one so the "link account"
    # entry point in settings still functions — but assessment-end
    # CTAs SHOULD pass it so the sibling app knows which lane to
    # open when the co-parent joins.
    context: Optional[str] = Field(default=None, max_length=32)


class LinkCodeResponse(BaseModel):
    code: str = Field(..., min_length=_CODE_LENGTH, max_length=_CODE_LENGTH)
    context: Optional[str] = None
    expires_at: str = Field(..., description="ISO-8601 expiry timestamp")
    join_url: str = Field(..., description="Public URL to paste into the invite message.")


class VerifyLinkCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)


class VerifyLinkCodeResponse(BaseModel):
    email: EmailStr
    context: Optional[str] = None


# ------------------------------- endpoints ------------------------------- #

@router.post("/link-codes", response_model=LinkCodeResponse)
async def mint_link_code(
    request: Request,
    body: Optional[LinkCodeMintRequest] = None,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Parent-authenticated. Called from the "Create Joint Alignment
    Report" / "Ready to Compare Perspectives?" CTA at the end of an
    eligible assessment (or from the account-settings link entry).
    Returns a human-readable `SA-482731`-shaped code plus a canonical
    `join_url` the parent can paste into their invite message.
    """
    if current.is_guest:
        raise HTTPException(status_code=403, detail="Guest accounts cannot link")

    # Founder safety guardrail (2026-03-04): a parent-minted link code is
    # designed to be pasted to the *co-parent* so they can join on the
    # sibling site. Gate on the family-violence screen. Professional-directed
    # codes never come through this endpoint — `professionals_routes.py`
    # inserts directly into the collection with a `prof:*` context.
    await require_ipv_clearance(db, current.user_id)

    if await _mint_rate_limited(db, current.user_id):
        raise HTTPException(
            status_code=429,
            detail=f"Please wait — you can mint up to {_MINT_RATE_LIMIT_PER_HOUR} codes per hour.",
        )

    # Invalidate any outstanding unused codes for this parent so the
    # newest code is the only one that works.
    await db[_COLL].update_many(
        {"user_id": current.user_id, "consumed_at": None},
        {"$set": {"consumed_at": _now(), "consumed_reason": "superseded"}},
    )

    code = _generate_code()
    context = (body.context if body and body.context else None)
    expires_at = _now() + timedelta(minutes=_CODE_TTL_MINUTES)
    doc = {
        "user_id": current.user_id,
        "email": current.email,
        "code_hash": _hash_code(code),
        "context": context,
        "minted_at": _now(),
        "expires_at": expires_at,
        "consumed_at": None,
        "consumed_reason": None,
        "ip": request.client.host if request.client else None,
    }
    await db[_COLL].insert_one(doc)
    logger.info(
        "link-code minted user=%s context=%s ttl_min=%s",
        current.user_id,
        context,
        _CODE_TTL_MINUTES,
    )
    align_base = os.environ.get(
        "ALIGN_JOIN_URL_BASE", "https://sacoparentsalign.com/join"
    ).rstrip("/")
    return LinkCodeResponse(
        code=code,
        context=context,
        expires_at=expires_at.astimezone(timezone.utc).isoformat(),
        join_url=f"{align_base}/{code}",
    )


@router.post(
    "/integrations/verify-link-code",
    response_model=VerifyLinkCodeResponse,
)
async def verify_link_code(
    body: VerifyLinkCodeRequest,
    x_integration_key: Optional[str] = Header(default=None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Server-to-server. Called by the sibling app after the parent
    pastes the code. Consumes the code (single-use) and returns the
    linked parent's email so the sibling can request the export.
    """
    _verify_integration_key(x_integration_key)

    # Normalise "SA-482731", "sa 482731", "482731" → "SA-482731".
    normalised = _normalise_code(body.code)
    if not normalised:
        raise HTTPException(status_code=404, detail="Code not found or expired")

    # Look at only-unconsumed, non-expired candidates. Iterate to
    # compare the bcrypt hash (bcrypt hashes are not indexable).
    cursor = db[_COLL].find(
        {"consumed_at": None, "expires_at": {"$gte": _now()}},
        {"_id": 1, "user_id": 1, "email": 1, "code_hash": 1, "context": 1},
    )
    async for candidate in cursor:
        if _check_code(normalised, candidate.get("code_hash", "")):
            await db[_COLL].update_one(
                {"_id": candidate["_id"]},
                {
                    "$set": {
                        "consumed_at": _now(),
                        "consumed_reason": "verified",
                    }
                },
            )
            logger.info(
                "link-code verified user=%s email=%s context=%s",
                candidate.get("user_id"),
                candidate.get("email"),
                candidate.get("context"),
            )
            return VerifyLinkCodeResponse(
                email=candidate["email"],
                context=candidate.get("context"),
            )

    raise HTTPException(status_code=404, detail="Code not found or expired")


@router.get("/integrations/export-assessments")
async def export_assessments(
    email: str,
    x_integration_key: Optional[str] = Header(default=None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Server-to-server. Returns the parent's Situation Snapshot,
    Foundation Statement, and the three-pronged Special Needs deep-
    dive artefacts. Only the parent's own material — never any
    co-parent data, never any safety-screen answers.
    """
    _verify_integration_key(x_integration_key)

    if not email:
        raise HTTPException(status_code=400, detail="email query param required")

    user = await db.users.find_one({"email": email.lower()}, {"user_id": 1, "email": 1, "name": 1})
    if not user:
        raise HTTPException(status_code=404, detail="No linked parent found")
    user_id = user["user_id"]

    prep = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0}) or {}
    completed = prep.get("completed") or {}

    # Situation Snapshot = the parent's saved mediation prep answers,
    # normalised so the sibling doesn't have to re-implement the shape.
    situation_snapshot = {
        "situation_focus": _clean(prep.get("child_goals", {}).get("focus")),
        "child_goals": _pick(prep.get("child_goals"), keep=("focus", "topics", "notes")),
        "issues": _pick(prep.get("issues"), keep=("selected", "notes", "priority")),
        "priority": _pick(prep.get("priority"), keep=("issue", "why", "outcome")),
        "comm_style": _pick(prep.get("comm_style"), keep=("style", "notes")),
        "readiness": _pick(prep.get("readiness"), keep=("score", "reflection")),
        "completed_sections": [k for k, v in completed.items() if v],
        "updated_at": _iso(prep.get("updated_at")),
    }

    # Foundation Statement — the four reflective prompts saved via
    # /api/mediation/reflection.
    reflection = prep.get("reflection") or {}
    foundation_statement = {
        "child_lens": _clean(reflection.get("child_lens")),
        "my_part": _clean(reflection.get("my_part")),
        "best_case": _clean(reflection.get("best_case")),
        "coparent_lens": _clean(reflection.get("coparent_lens")),
        "updated_at": _iso(reflection.get("updated_at") or prep.get("updated_at")),
    }

    # Three-pronged Special Needs — pull the parent's latest report
    # payload from each deep-dive collection. If the parent hasn't
    # completed a lane, the field is null (the sibling app can render
    # accordingly).
    special_needs = {
        "medical": await _latest_deep_dive_report(db, "med_deep_reports", user_id),
        "educational": await _latest_deep_dive_report(db, "edu_deep_reports", user_id),
        "psychological": await _latest_deep_dive_report(db, "psych_deep_reports", user_id),
    }

    return {
        "parent": {
            "email": user["email"],
            "name": user.get("name"),
        },
        "situation_snapshot": situation_snapshot,
        "foundation_statement": foundation_statement,
        "special_needs": special_needs,
        "exported_at": _iso(_now()),
        "schema_version": 1,
    }


# --------------------------- payload shaping --------------------------- #

async def _latest_deep_dive_report(
    db: AsyncIOMotorDatabase, collection: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Return a compact projection of the parent's latest deep-dive
    report: profile, foundation statement, questions-for-professional
    list, and top rating areas. Full raw scoring vectors are left
    out — the sibling only needs the parent-facing outputs.
    """
    doc = await db[collection].find_one(
        {"user_id": user_id},
        sort=[("generated_at", -1)],
    )
    if not doc:
        return None
    return {
        "profile": doc.get("profile"),
        "foundation_statement": doc.get("foundation_statement"),
        "questions_for_school_or_parent": doc.get("questions_for_school_or_parent"),
        "questions_for_provider": doc.get("questions_for_provider"),
        "questions_for_therapist": doc.get("questions_for_therapist"),
        "rating_areas": doc.get("rating_areas"),
        "signals": doc.get("signals"),
        "generated_at": _iso(doc.get("generated_at")),
    }


def _pick(source: Optional[Dict[str, Any]], keep) -> Optional[Dict[str, Any]]:
    if not isinstance(source, dict):
        return None
    return {k: source.get(k) for k in keep if source.get(k) is not None} or None


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _iso(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


# --------------------------------------------------------------------- #
# Iter208 — Foundation Statement PDF bytes for Align.
#
# Ships the SAME PDF the parent downloads on the parent-facing app so
# the two sites can never drift visually. Reuses `_load_reflection` +
# `build_foundation_statement_pdf` directly rather than re-implementing
# them here.
# --------------------------------------------------------------------- #
@router.get("/integrations/foundation-statement.pdf")
async def integrations_foundation_statement_pdf(
    email: str,
    x_integration_key: Optional[str] = Header(default=None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Stream the parent's Foundation Statement PDF (server-to-server).

    * Gate: `X-Integration-Key` header must match
      `INTEGRATION_SHARED_SECRET` (constant-time compare).
    * 400 if `email` query param missing.
    * 404 if no parent is linked to that email (same generic body as
      `export-assessments` so we don't leak account existence).
    * 409 when the parent has completed no reflection prompts yet —
      Align's UI can then show its own empty-state instead of
      embedding a hollow PDF.
    * 200 with `application/pdf` bytes rendered by the exact same
      `build_foundation_statement_pdf` builder the parent-facing route
      calls.
    """
    _verify_integration_key(x_integration_key)

    if not email:
        raise HTTPException(status_code=400, detail="email query param required")

    user = await db.users.find_one(
        {"email": email.lower()},
        {"user_id": 1, "email": 1, "name": 1},
    )
    if not user:
        raise HTTPException(status_code=404, detail="No linked parent found")

    prep = await db.prep_data.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    reflection = prep.get("reflection") or {}

    # Reuse the parent-facing builder so future visual updates flow
    # through Align automatically. Lazy import — keeps a heavy PDF
    # module out of the integrations hot path when only JSON lookups
    # are being served.
    from foundation_statement_pdf import (
        build_foundation_statement_pdf,
        foundation_statement_has_content,
    )
    if not foundation_statement_has_content(reflection):
        raise HTTPException(
            status_code=409,
            detail=(
                "This parent hasn't completed a Foundation Statement yet."
            ),
        )

    author_name = (user.get("name") or (user.get("email") or "").split("@", 1)[0]).strip()
    pdf_bytes = build_foundation_statement_pdf(
        author_name=author_name or "A co-parent",
        reflection=reflection,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="foundation-statement.pdf"',
            # Bundle metadata for Align diagnostics — never contains
            # PHI, just render info.
            "X-Report-Type": "foundation_statement",
            "X-Report-Version": "iter208",
        },
    )
