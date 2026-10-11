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

import logging
import os
import secrets
import string
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from auth import UserPublic, get_current_user, get_db
from integration_keys import match_integration_key
from safety_gate import require_ipv_clearance
from self_assessment_reminders import is_safety_flagged


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
_LINKS = "align_links"
_ACCESS_LOG = "align_access_log"
_NOT_LINKED = "No linked parent found"


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
    if not match_integration_key(provided):
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
    Parent-authenticated. Called from the "Create Co-Parenting
    Agreement" / "Ready to Compare Perspectives?" CTA at the end of an
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
            await _record_link(db, candidate["user_id"], candidate["email"], candidate.get("context"))
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
    user = await _linked_user(db, email)
    user_id = user["user_id"]
    redacted = await is_safety_flagged(db, user_id)
    await _log_read(db, user_id, "export-assessments", redacted)

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
    # /api/mediation/reflection. Canonical keys are the ones the
    # frontend writes (child_lens / own_part / best_outcome /
    # coparent_feedback — see models.ReflectionPayload). The
    # historical export shape used different names (my_part /
    # best_case / coparent_lens) that no writer ever populated, so
    # 3 of 4 fields silently came back null for every parent.
    # We now read canonical keys but keep the historical output field
    # names AND populate a `canonical` block so Align can migrate off
    # the legacy names on its own timeline.
    reflection = prep.get("reflection") or {}
    canonical = {
        "child_lens": _clean(reflection.get("child_lens")),
        "own_part": _clean(reflection.get("own_part")),
        "best_outcome": _clean(reflection.get("best_outcome")),
        "coparent_feedback": _clean(reflection.get("coparent_feedback")),
    }
    foundation_statement = {
        # Historical field names — kept populated so any existing
        # Align integration that still reads them starts receiving
        # real data immediately.
        "child_lens": canonical["child_lens"],
        "my_part": canonical["own_part"],
        "best_case": canonical["best_outcome"],
        "coparent_lens": canonical["coparent_feedback"],
        # Canonical block — the shape Align should adopt going forward.
        "canonical": canonical,
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
    if redacted:
        situation_snapshot, foundation_statement, special_needs = _redact_for_safety(
            situation_snapshot, foundation_statement, special_needs
        )

    return {
        "parent": {
            "email": user["email"],
            "name": user.get("name"),
        },
        "situation_snapshot": situation_snapshot,
        "foundation_statement": foundation_statement,
        "special_needs": special_needs,
        "redacted_for_safety": redacted,
        "exported_at": _iso(_now()),
        "schema_version": 1,
    }


# ----------------------------- Align links ----------------------------- #

async def _record_link(db: AsyncIOMotorDatabase, user_id: str, email: str, context: Optional[str]) -> None:
    await db[_LINKS].update_one(
        {"user_id": user_id},
        {"$set": {"email": (email or "").lower(), "context": context, "linked_at": _now(), "unlinked_at": None}},
        upsert=True,
    )


async def _linked_user(db: AsyncIOMotorDatabase, email: str) -> Dict[str, Any]:
    """The parent behind `email`, only if they linked with a code and haven't unlinked. Same 404 either way."""
    if not email:
        raise HTTPException(status_code=400, detail="email query param required")
    user = await db.users.find_one({"email": email.lower()}, {"_id": 0, "user_id": 1, "email": 1, "name": 1})
    if not user or not await db[_LINKS].find_one({"user_id": user["user_id"], "unlinked_at": None}, {"_id": 1}):
        raise HTTPException(status_code=404, detail=_NOT_LINKED)
    return user


async def _log_read(db: AsyncIOMotorDatabase, user_id: str, endpoint: str, redacted: bool) -> None:
    await db[_ACCESS_LOG].insert_one({"user_id": user_id, "endpoint": endpoint, "redacted": redacted, "at": _now()})


async def migrate_verified_links(db: AsyncIOMotorDatabase) -> int:
    """Keep parents who already linked with a code before links were tracked (never re-links an unlinked parent)."""
    n = 0
    async for c in db[_COLL].find({"consumed_reason": "verified"}, {"_id": 0, "user_id": 1, "email": 1, "context": 1, "consumed_at": 1}):
        res = await db[_LINKS].update_one(
            {"user_id": c["user_id"]},
            {"$setOnInsert": {"email": (c.get("email") or "").lower(), "context": c.get("context"),
                              "linked_at": c.get("consumed_at") or _now(), "unlinked_at": None, "migrated": True}},
            upsert=True,
        )
        n += 1 if res.upserted_id else 0
    return n


_READ_LABELS = {
    "export-assessments": "Your Situation Snapshot, Foundation Statement and Special Needs summaries",
    "foundation-statement.pdf": "Your Foundation Statement PDF",
}


_REDACTED_NOTES = {
    "export-assessments": "Answers and writing withheld for safety",
    "foundation-statement.pdf": "Blocked for safety",
}


class AlignRead(BaseModel):
    at: str
    what: str
    redacted: bool
    note: Optional[str] = None


class AlignLinkStatus(BaseModel):
    linked: bool
    linked_at: Optional[str] = None
    last_read_at: Optional[str] = None
    recent_reads: List[AlignRead] = []


async def _link_status(db: AsyncIOMotorDatabase, user_id: str) -> AlignLinkStatus:
    link = await db[_LINKS].find_one({"user_id": user_id, "unlinked_at": None}, {"_id": 0, "linked_at": 1})
    logs = await db[_ACCESS_LOG].find({"user_id": user_id}, {"_id": 0}).sort("at", -1).limit(5).to_list(5)
    reads = [
        AlignRead(
            at=_iso(r["at"]),
            what=_READ_LABELS.get(r["endpoint"], r["endpoint"]),
            redacted=bool(r.get("redacted")),
            note=_REDACTED_NOTES.get(r["endpoint"]) if r.get("redacted") else None,
        )
        for r in logs
    ]
    return AlignLinkStatus(
        linked=bool(link),
        linked_at=_iso((link or {}).get("linked_at")),
        last_read_at=reads[0].at if reads else None,
        recent_reads=reads,
    )


@router.get("/integrations/align-link", response_model=AlignLinkStatus)
async def align_link_status(current: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    return await _link_status(db, current.user_id)


@router.delete("/integrations/align-link", response_model=AlignLinkStatus)
async def unlink_align(current: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    """Parent turns off Align's access. Linking again needs a new code."""
    await db[_LINKS].update_one({"user_id": current.user_id, "unlinked_at": None}, {"$set": {"unlinked_at": _now()}})
    logger.info("align unlinked user=%s", current.user_id)
    return await _link_status(db, current.user_id)


_KEEP_WHEN_REDACTED = ("completed_sections", "updated_at")


def _redact_for_safety(snapshot: Dict[str, Any], foundation: Dict[str, Any], needs: Dict[str, Any]):
    """Safety-flagged parent: drop every answer and narrative; keep which sections are done, ratings and dates."""
    snap = {k: (v if k in _KEEP_WHEN_REDACTED else None) for k, v in snapshot.items()}
    fs = {k: None for k in ("child_lens", "my_part", "best_case", "coparent_lens")}
    fs.update(canonical={k: None for k in foundation["canonical"]}, updated_at=foundation.get("updated_at"))
    sn = {k: (v and {"rating_areas": v.get("rating_areas"), "generated_at": v.get("generated_at")}) for k, v in needs.items()}
    return snap, fs, sn


class CourtKeyUpsert(BaseModel):
    key: str = Field(..., min_length=3, max_length=80)
    case_id: str = Field(..., min_length=1, max_length=80)
    mediator_name: str = Field("", max_length=200)
    expires_at: Optional[datetime] = None
    # Court page options the professional asks the parent to complete (auto-ticked when the parent links the code).
    requested: List[Literal["coparent", "self", "educational", "medical", "psychological", "foundation", "parallel"]] = Field(default_factory=list, max_length=7)


@router.post("/integrations/court-keys")
async def upsert_court_key(
    body: CourtKeyUpsert,
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Server-to-server: Align creates or updates a court code, optionally with the assessments the professional asked for."""
    _verify_integration_key(x_integration_key)
    from court_checklist import REQUESTABLE
    from portal_routes import _hash_key

    key_hash = _hash_key(body.key)
    requested = [k for k in REQUESTABLE if k in body.requested]
    await db.portal_court_keys.update_one(
        {"key_hash": key_hash},
        {
            "$set": {"case_id": body.case_id.strip(), "mediator_name": body.mediator_name.strip(),
                     "expires_at": _iso(body.expires_at), "requested": requested, "updated_at": _iso(_now())},
            "$setOnInsert": {"key_hash": key_hash, "revoked_at": None, "created_at": _iso(_now())},
        },
        upsert=True,
    )
    return {"case_id": body.case_id.strip(), "requested": requested}


@router.get("/integrations/court-keys/{case_id}/progress")
async def court_key_progress(
    case_id: str,
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Server-to-server, status only: per parent who entered an Align-made code, Done / In progress / Not started + dates."""
    _verify_integration_key(x_integration_key)
    from court_checklist import REQUESTABLE
    from court_codes_routes import linked_parents

    cid = case_id.strip()
    # Align-made codes only: codes created inside SA CoParents always carry `created_by`.
    kd = await db.portal_court_keys.find_one({"case_id": cid, "created_by": {"$exists": False}}, {"_id": 0, "requested": 1, "revoked_at": 1})
    if not kd:
        raise HTTPException(status_code=404, detail="Court code not found")
    keys = [k for k in REQUESTABLE if k in (kd.get("requested") or [])]
    return {"case_id": cid, "requested": keys, "revoked": bool(kd.get("revoked_at")), "parents": await linked_parents(db, cid, keys)}


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
    user = await _linked_user(db, email)
    if await is_safety_flagged(db, user["user_id"]):
        await _log_read(db, user["user_id"], "foundation-statement.pdf", True)
        raise HTTPException(status_code=403, detail="Not available for this parent.")
    await _log_read(db, user["user_id"], "foundation-statement.pdf", False)

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
