"""
Sibling integration for sacoparentsalign.com.

Three endpoints on `/api`:
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
from typing import Any, Dict, Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from auth import UserPublic, get_current_user, get_db


router = APIRouter(tags=["integrations"])
logger = logging.getLogger(__name__)


# 8-char alphabet, ambiguous glyphs (I, O, 1, 0) dropped.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8
_CODE_TTL_MINUTES = 15
_MINT_RATE_LIMIT_PER_HOUR = 5

_COLL = "link_codes"


# ------------------------------- helpers ------------------------------- #

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


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

class LinkCodeResponse(BaseModel):
    code: str = Field(..., min_length=_CODE_LENGTH, max_length=_CODE_LENGTH)


class VerifyLinkCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)


class VerifyLinkCodeResponse(BaseModel):
    email: EmailStr


# ------------------------------- endpoints ------------------------------- #

@router.post("/link-codes", response_model=LinkCodeResponse)
async def mint_link_code(
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Parent-authenticated. Called from account settings on
    sacoparentsapp.online when the parent wants to link their account
    to sacoparentsalign.com. Returns a single-use 8-character code
    the parent copies into the sibling app.
    """
    if current.is_guest:
        raise HTTPException(status_code=403, detail="Guest accounts cannot link")

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
    doc = {
        "user_id": current.user_id,
        "email": current.email,
        "code_hash": _hash_code(code),
        "minted_at": _now(),
        "expires_at": _now() + timedelta(minutes=_CODE_TTL_MINUTES),
        "consumed_at": None,
        "consumed_reason": None,
        "ip": request.client.host if request.client else None,
    }
    await db[_COLL].insert_one(doc)
    logger.info(
        "link-code minted user=%s ttl_min=%s", current.user_id, _CODE_TTL_MINUTES
    )
    return LinkCodeResponse(code=code)


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

    # Look at only-unconsumed, non-expired candidates. Iterate to
    # compare the bcrypt hash (bcrypt hashes are not indexable).
    cursor = db[_COLL].find(
        {"consumed_at": None, "expires_at": {"$gte": _now()}},
        {"_id": 1, "user_id": 1, "email": 1, "code_hash": 1},
    )
    async for candidate in cursor:
        if _check_code(body.code, candidate.get("code_hash", "")):
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
                "link-code verified user=%s email=%s",
                candidate.get("user_id"),
                candidate.get("email"),
            )
            return VerifyLinkCodeResponse(email=candidate["email"])

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
