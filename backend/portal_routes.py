"""SacoparentsPortal backend routes.

Powers the mobile-first single-page portal (`SacoparentsPortal.jsx`) with:

  * Per-user state persistence (cross-device sync)
      GET  /api/portal/state           — hydrate from Mongo (auth required)
      PUT  /api/portal/state           — upsert the whole portal state
                                          (auth required)

  * Live Claude BIFF refinement (replaces the local regex fallback)
      POST /api/portal/biff-refine     — rate-limited, no auth

  * Court-key verification for the "Door 2" flow
      POST /api/portal/court-keys/verify   — public, checks a hashed key

  * Branded PDFs (replace `window.print()`)
      POST /api/portal/foundation-pdf      — public
      POST /api/portal/legal-report-pdf    — public

The court-keys collection is seeded idempotently at import time (the two
demo keys wired into the mockup: `ALIGN-SA-2026`, `COURT-8842`) so a
fresh Mongo instance already recognises them.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth import get_current_user, get_db
from models import UserPublic
import portal_ai
import portal_pdf


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portal", tags=["portal"])


# --------------------------------------------------------------------- #
# Optional auth (portal state PUT/GET need auth, but the rest are public)
# --------------------------------------------------------------------- #
async def get_current_user_optional(request: Request) -> Optional[UserPublic]:
    """Return the current user if one is authenticated, else `None`.

    Wraps `get_current_user` and swallows its 401 so a caller can serve
    both signed-in and anonymous clients from one handler.
    """
    try:
        # `get_current_user` reads Bearer creds from a FastAPI dependency —
        # we recreate that here with a bare fetch so the wrapper is usable
        # from any handler without threading Depends() through the caller.
        from fastapi.security import HTTPBearer

        bearer = HTTPBearer(auto_error=False)
        creds = await bearer(request)
        return await get_current_user(request, creds)
    except HTTPException:
        return None
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------- #
# BIFF rate-limits (mirrors coach_demo pattern)
# --------------------------------------------------------------------- #
_PER_IP_WINDOW_SECONDS = 3600
_PER_IP_LIMIT = 40                # generous — active portal writes many drafts
_GLOBAL_WINDOW_SECONDS = 3600
_GLOBAL_LIMIT = 800
_MAX_BIFF_INPUT_LEN = 1000

_ip_hits: Dict[str, Deque[float]] = {}
_global_hits: Deque[float] = deque()
_rate_lock = asyncio.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _rate_guard(ip: str) -> None:
    now = time.monotonic()
    async with _rate_lock:
        while _global_hits and now - _global_hits[0] > _GLOBAL_WINDOW_SECONDS:
            _global_hits.popleft()
        stale: list[str] = []
        for other_ip, bucket in _ip_hits.items():
            while bucket and now - bucket[0] > _PER_IP_WINDOW_SECONDS:
                bucket.popleft()
            if not bucket:
                stale.append(other_ip)
        for s in stale:
            _ip_hits.pop(s, None)

        if len(_global_hits) >= _GLOBAL_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="BIFF coach is at global capacity — please try again shortly.",
            )
        bucket = _ip_hits.get(ip)
        if bucket is not None and len(bucket) >= _PER_IP_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="You've hit the BIFF hourly limit — please wait a bit before retrying.",
            )
        if bucket is None:
            bucket = deque()
            _ip_hits[ip] = bucket
        bucket.append(now)
        _global_hits.append(now)


# --------------------------------------------------------------------- #
# Portal state (per-user)
# --------------------------------------------------------------------- #
_PORTAL_COLLECTION = "portal_state"


def _empty_portal_state() -> Dict[str, Any]:
    return {
        "align_records": [],
        "milestones": [],
        "biff_logs": [],
        "foundation_text": "",
        "legal_report": {"sigA": "", "sigB": "", "sigMed": ""},
        "health_index": {"s1": 7, "s2": 6, "s3": 5},
        "court_key": "",
        "reassessments": [],
        "updated_at": None,
    }


class PortalStatePayload(BaseModel):
    align_records: List[Dict[str, Any]] = Field(default_factory=list)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    biff_logs: List[Dict[str, Any]] = Field(default_factory=list)
    foundation_text: str = ""
    legal_report: Dict[str, str] = Field(default_factory=dict)
    health_index: Dict[str, int] = Field(default_factory=dict)
    court_key: str = ""
    reassessments: List[Dict[str, Any]] = Field(default_factory=list)


@router.get("/state")
async def get_state(user: UserPublic = Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    """Return the caller's portal state (creates an empty doc on first hit)."""
    doc = await db[_PORTAL_COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"exists": False, "state": _empty_portal_state()}
    doc.pop("user_id", None)
    return {"exists": True, "state": doc}


@router.put("/state")
async def put_state(
    payload: PortalStatePayload,
    user: UserPublic = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Upsert the caller's portal state as one document."""
    # Cap array sizes so a bad client can't push us over the Mongo doc limit.
    def _cap(seq: list, n: int) -> list:
        return list(seq or [])[:n]

    state = {
        "user_id": user.user_id,
        "align_records": _cap(payload.align_records, 500),
        "milestones": _cap(payload.milestones, 500),
        "biff_logs": _cap(payload.biff_logs, 500),
        "foundation_text": (payload.foundation_text or "")[:5000],
        "legal_report": {
            "sigA": (payload.legal_report or {}).get("sigA", "")[:120],
            "sigB": (payload.legal_report or {}).get("sigB", "")[:120],
            "sigMed": (payload.legal_report or {}).get("sigMed", "")[:200],
        },
        "health_index": {
            "s1": max(1, min(10, int((payload.health_index or {}).get("s1", 5) or 5))),
            "s2": max(1, min(10, int((payload.health_index or {}).get("s2", 5) or 5))),
            "s3": max(1, min(10, int((payload.health_index or {}).get("s3", 5) or 5))),
        },
        "court_key": (payload.court_key or "")[:80],
        "reassessments": _cap(payload.reassessments, 200),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db[_PORTAL_COLLECTION].update_one(
        {"user_id": user.user_id},
        {"$set": state},
        upsert=True,
    )
    return {"ok": True, "updated_at": state["updated_at"]}


# --------------------------------------------------------------------- #
# BIFF refine
# --------------------------------------------------------------------- #
class BiffRefineBody(BaseModel):
    raw: str = Field(min_length=1, max_length=_MAX_BIFF_INPUT_LEN)


@router.post("/biff-refine")
async def biff_refine_endpoint(body: BiffRefineBody, request: Request) -> Dict[str, Any]:
    """Refine a draft into BIFF style via Claude. Rate limited, no auth."""
    ip = _client_ip(request)
    await _rate_guard(ip)
    try:
        result = await portal_ai.refine_biff(body.raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("portal biff-refine LLM call failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The BIFF coach couldn't respond right now — please try again in a moment.",
        )
    return result


# --------------------------------------------------------------------- #
# Court keys (professional handshake with sacoparentsalign.com)
# --------------------------------------------------------------------- #
_COURT_KEYS_COLLECTION = "portal_court_keys"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.strip().upper().encode("utf-8")).hexdigest()


# Demo keys shipped with the mockup so the flow works out-of-the-box on
# a fresh install. Wired into the "Demo Keys" buttons on the court-key
# screen. Real production keys are minted by mediators through the
# sacoparentsalign.com app and inserted via the same collection.
_SEED_COURT_KEYS: List[Dict[str, Any]] = [
    {
        "raw": "ALIGN-SA-2026",
        "case_id": "ALIGN-SA-2026",
        "mediator_name": "Matt Sossi, Licensed Mediator (San Antonio, TX)",
        "expires_at": None,  # sample key — no expiry
    },
    {
        "raw": "COURT-8842",
        "case_id": "COURT-8842",
        "mediator_name": "Matt Sossi, Licensed Mediator (San Antonio, TX)",
        "expires_at": None,
    },
]


async def seed_court_keys(db) -> None:
    """Idempotent seed of the two demo court keys on app startup."""
    for entry in _SEED_COURT_KEYS:
        key_hash = _hash_key(entry["raw"])
        await db[_COURT_KEYS_COLLECTION].update_one(
            {"key_hash": key_hash},
            {
                "$setOnInsert": {
                    "key_hash": key_hash,
                    "case_id": entry["case_id"],
                    "mediator_name": entry["mediator_name"],
                    "expires_at": entry["expires_at"],
                    "revoked_at": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )


class CourtKeyVerifyBody(BaseModel):
    key: str = Field(min_length=3, max_length=80)


@router.post("/court-keys/verify")
async def verify_court_key(body: CourtKeyVerifyBody, request: Request) -> Dict[str, Any]:
    """Return `{ verified, case_id, mediator_name }` for a valid key.

    Rate-limited to prevent brute force. On invalid / expired / revoked
    the response is a 200 with `verified: false` (so the UI can render a
    friendly inline error without treating it like a network failure).
    """
    ip = _client_ip(request)
    await _rate_guard(ip)

    db = request.app.state.db
    key_hash = _hash_key(body.key)
    doc = await db[_COURT_KEYS_COLLECTION].find_one({"key_hash": key_hash}, {"_id": 0})
    if not doc:
        return {"verified": False, "reason": "unknown_key"}
    if doc.get("revoked_at"):
        return {"verified": False, "reason": "revoked"}
    exp = doc.get("expires_at")
    if exp:
        try:
            expires_at = datetime.fromisoformat(exp) if isinstance(exp, str) else exp
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return {"verified": False, "reason": "expired"}
        except Exception:  # noqa: BLE001
            # Corrupt expiry — fail closed.
            return {"verified": False, "reason": "expired"}
    # Note: verification does NOT consume the key — a mediator can hand
    # the same key to both parents.
    await db[_COURT_KEYS_COLLECTION].update_one(
        {"key_hash": key_hash},
        {"$set": {"last_verified_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {
        "verified": True,
        "case_id": doc.get("case_id"),
        "mediator_name": doc.get("mediator_name"),
    }


# --------------------------------------------------------------------- #
# PDFs
# --------------------------------------------------------------------- #
class FoundationPdfBody(BaseModel):
    foundation_text: str = Field(min_length=1, max_length=5000)
    case_ref: Optional[str] = Field(default=None, max_length=80)
    author_name: Optional[str] = Field(default=None, max_length=120)


class LegalReportPdfBody(BaseModel):
    health_index: Dict[str, int] = Field(default_factory=dict)
    foundation_text: Optional[str] = Field(default=None, max_length=5000)
    signatures: Optional[Dict[str, str]] = Field(default=None)
    matrix: Optional[List[Dict[str, str]]] = Field(default=None)
    case_ref: Optional[str] = Field(default=None, max_length=80)


@router.post("/foundation-pdf")
async def foundation_pdf(body: FoundationPdfBody) -> Response:
    try:
        pdf_bytes = portal_pdf.build_portal_foundation_pdf(
            foundation_text=body.foundation_text,
            case_ref=body.case_ref,
            author_name=body.author_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="sacoparents-foundation-statement.pdf"'
            )
        },
    )


@router.post("/legal-report-pdf")
async def legal_report_pdf(body: LegalReportPdfBody) -> Response:
    try:
        pdf_bytes = portal_pdf.build_portal_legal_report_pdf(
            health_index=body.health_index or {},
            foundation_text=body.foundation_text,
            signatures=body.signatures or {},
            matrix=body.matrix,
            case_ref=body.case_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="sacoparents-legal-report.pdf"'
            )
        },
    )
