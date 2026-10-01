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
      POST /api/portal/foundation-pdf         — public
      POST /api/portal/legal-report-pdf       — public
      POST /api/portal/weekly-progress-pdf    — public

  * Signed share-links for any generated PDF (short URL to text/email)
      POST /api/portal/share                  — public, mints share_id
      GET  /api/portal/share/{share_id}.pdf   — public, regenerates PDF

The court-keys collection is seeded idempotently at import time (the two
demo keys wired into the mockup: `ALIGN-SA-2026`, `COURT-8842`) so a
fresh Mongo instance already recognises them.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
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
        "safety_ack": None,
        "safety_plan": None,
        "guided_drafts": None,
        "snapshot_history": None,
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
    # Safety-first sync (iter212). Both are opaque JSON blobs the client
    # owns — the server only enforces size + shape at write time so we
    # can iterate on the client without a schema migration.
    safety_ack: Optional[Dict[str, Any]] = None
    safety_plan: Optional[Dict[str, Any]] = None
    # Guided Journey draft sync (iter222). Map: topic -> snapshot the
    # frontend GuidedJourneyModal writes on every parent-send so a
    # signed-in parent can resume a mid-wizard session on a new device.
    guided_drafts: Optional[Dict[str, Any]] = None
    # Snapshot Library (iter227). Ordered list (newest first) of
    # committed Guided Journey runs so the toolkit's "Recent
    # snapshots" strip can re-download without re-running the wizard.
    snapshot_history: Optional[List[Dict[str, Any]]] = None


@router.get("/state")
async def get_state(user: UserPublic = Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    """Return the caller's portal state (creates an empty doc on first hit)."""
    doc = await db[_PORTAL_COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"exists": False, "state": _empty_portal_state()}
    doc.pop("user_id", None)
    return {"exists": True, "state": doc}


def _sanitize_safety_ack(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Whitelist the small handful of safety-ack keys.

    Kept intentionally opaque to the server — the ack is a client-owned
    JSON blob. We enforce keys + types so a bad client can't push a
    huge object into every parent's record.
    """
    if not isinstance(raw, dict):
        return None
    cleared = bool(raw.get("cleared"))
    flagged = bool(raw.get("flagged"))
    date = str(raw.get("date", ""))[:40]
    if not date:
        return None
    return {"cleared": cleared, "flagged": flagged, "date": date}


_SAFETY_PLAN_KEYS = (
    "safe_place",
    "trusted_contact",
    "essentials",
    "code_word",
    "tech_notes",
)


def _sanitize_safety_plan(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Whitelist Safety Plan text fields and cap them at 500 chars each.

    A parent's Safety Plan is private and NEVER surfaced to the co-parent
    via joint reports or share links — the caller-scoped `portal_state`
    endpoint is the only surface that reads it back.
    """
    if not isinstance(raw, dict):
        return None
    out: Dict[str, Any] = {}
    for key in _SAFETY_PLAN_KEYS:
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val[:500]
    if not out:
        return None
    updated_at = raw.get("updated_at")
    if isinstance(updated_at, str):
        out["updated_at"] = updated_at[:40]
    return out


_GUIDED_TOPICS = {
    "foundation",
    "coparenting",
    "safety",
    "medical",
    "educational",
    "psychological",
}


def _sanitize_guided_drafts(
    raw: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Whitelist Guided Journey draft snapshots for cross-device resume.

    Draft snapshots are opaque JSON the client owns. We cap per-topic
    payload size (~12 KB) and only accept known topic keys so a bad
    client can't push runaway blobs into the parent's record. Passing
    ``None`` (or an empty dict) clears every draft.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    out: Dict[str, Any] = {}
    for topic, snapshot in raw.items():
        if topic not in _GUIDED_TOPICS:
            continue
        if not isinstance(snapshot, dict):
            continue
        # Truncate history / answers arrays defensively (each guided
        # topic maxes out at ~10 turns so 40 is a very safe ceiling).
        hist = snapshot.get("history")
        answers = snapshot.get("answers")
        if isinstance(hist, list):
            snapshot["history"] = hist[:40]
        if isinstance(answers, list):
            snapshot["answers"] = answers[:40]
        # Enforce total per-topic byte cap after truncation.
        import json as _json

        serialized = _json.dumps(snapshot, default=str)
        if len(serialized) > 12_000:
            continue
        out[topic] = snapshot
    return out or None


_MAX_SNAPSHOT_HISTORY = 12
_MAX_SNAPSHOT_BYTES = 12_000


def _sanitize_snapshot_history(
    raw: Optional[List[Dict[str, Any]]],
) -> Optional[List[Dict[str, Any]]]:
    """Whitelist committed Guided Journey snapshots for the toolkit strip.

    Each item must carry ``topic``, ``answers`` (list), ``saved_at``
    (iso string), and optional ``id``, ``save_key``, ``category``.
    Extra keys are dropped defensively. Total is capped at
    ``_MAX_SNAPSHOT_HISTORY`` items (newest first) and each item at
    ``_MAX_SNAPSHOT_BYTES`` bytes so a bad client can't push runaway
    data into portal_state.
    """
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    import json as _json

    out: List[Dict[str, Any]] = []
    for item in raw:
        if len(out) >= _MAX_SNAPSHOT_HISTORY:
            break
        if not isinstance(item, dict):
            continue
        topic = item.get("topic")
        if topic not in _GUIDED_TOPICS:
            continue
        answers = item.get("answers")
        if not isinstance(answers, list) or not answers:
            continue
        clean_answers: List[Dict[str, str]] = []
        for qa in answers[:40]:
            if not isinstance(qa, dict):
                continue
            q = str(qa.get("question") or "")[:400]
            a = str(qa.get("answer") or "")[:2000]
            if q or a:
                clean_answers.append({"question": q, "answer": a})
        if not clean_answers:
            continue
        cleaned: Dict[str, Any] = {
            "topic": topic,
            "answers": clean_answers,
            "saved_at": str(item.get("saved_at") or "")[:40],
        }
        if "id" in item:
            try:
                cleaned["id"] = int(item["id"])
            except (TypeError, ValueError):
                pass
        if item.get("save_key"):
            cleaned["save_key"] = str(item["save_key"])[:64]
        if item.get("category"):
            cleaned["category"] = str(item["category"])[:64]
        if item.get("safety_flagged"):
            cleaned["safety_flagged"] = True
        # iter235 — preserve the parent's custom label so the
        # Snapshot library reads like a real folder ("Emma's summer
        # plan") instead of the auto-generated topic + ago string.
        # Capped at 40 chars matching the frontend input maxLength.
        if item.get("label"):
            cleaned["label"] = str(item["label"])[:40]
        # iter237 — preserve the pin flag so a renamed "active plan"
        # stays at the top of the Snapshot library. `pinned_at` lets
        # the UI sort multiple pinned items by most-recently-pinned
        # when the parent flips several on in a row.
        if item.get("pinned"):
            cleaned["pinned"] = True
            if item.get("pinned_at"):
                cleaned["pinned_at"] = str(item["pinned_at"])[:40]
        if len(_json.dumps(cleaned, default=str)) > _MAX_SNAPSHOT_BYTES:
            continue
        out.append(cleaned)
    return out or None


@router.put("/state")
async def put_state(
    payload: PortalStatePayload,
    user: UserPublic = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Merge the caller's portal state.

    Only fields explicitly present in the request body are written
    (`pydantic.model_dump(exclude_unset=True)`). A partial-update
    client sending `{"safety_plan": null}` clears only that field
    and leaves align_records / milestones / biff_logs / health_index
    / etc. untouched.

    A client that still sends the full state (the current Portal
    frontend) works exactly as before — every field is `set`, so
    every field is updated.
    """
    # Cap array sizes so a bad client can't push us over the Mongo doc limit.
    def _cap(seq: list, n: int) -> list:
        return list(seq or [])[:n]

    updates = payload.model_dump(exclude_unset=True)
    if "align_records" in updates:
        updates["align_records"] = _cap(updates["align_records"], 500)
    if "milestones" in updates:
        updates["milestones"] = _cap(updates["milestones"], 500)
    if "biff_logs" in updates:
        updates["biff_logs"] = _cap(updates["biff_logs"], 500)
    if "reassessments" in updates:
        updates["reassessments"] = _cap(updates["reassessments"], 200)
    if "foundation_text" in updates:
        updates["foundation_text"] = (updates["foundation_text"] or "")[:5000]
    if "court_key" in updates:
        updates["court_key"] = (updates["court_key"] or "")[:80]
    if "legal_report" in updates:
        lr = updates["legal_report"] or {}
        updates["legal_report"] = {
            "sigA": lr.get("sigA", "")[:120],
            "sigB": lr.get("sigB", "")[:120],
            "sigMed": lr.get("sigMed", "")[:200],
        }
    if "health_index" in updates:
        hi = updates["health_index"] or {}
        updates["health_index"] = {
            "s1": max(1, min(10, int(hi.get("s1", 5) or 5))),
            "s2": max(1, min(10, int(hi.get("s2", 5) or 5))),
            "s3": max(1, min(10, int(hi.get("s3", 5) or 5))),
        }
    if "safety_ack" in updates:
        updates["safety_ack"] = _sanitize_safety_ack(updates["safety_ack"])
    if "safety_plan" in updates:
        updates["safety_plan"] = _sanitize_safety_plan(updates["safety_plan"])
    if "guided_drafts" in updates:
        updates["guided_drafts"] = _sanitize_guided_drafts(updates["guided_drafts"])
    if "snapshot_history" in updates:
        updates["snapshot_history"] = _sanitize_snapshot_history(
            updates["snapshot_history"]
        )
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db[_PORTAL_COLLECTION].update_one(
        {"user_id": user.user_id},
        {"$set": updates, "$setOnInsert": {"user_id": user.user_id}},
        upsert=True,
    )
    return {"ok": True, "updated_at": updates["updated_at"]}


# --------------------------------------------------------------------- #
# BIFF refine
# --------------------------------------------------------------------- #
class BiffRefineBody(BaseModel):
    raw: str = Field(min_length=1, max_length=_MAX_BIFF_INPUT_LEN)
    safety_flagged: bool = False


class GuidedJourneyStepBody(BaseModel):
    """One turn of the Coparenting Journey guided chat wizard."""

    topic: str = Field(
        pattern="^(foundation|safety|coparenting|medical|educational|psychological)$"
    )
    step_index: int = Field(ge=-1, le=20)  # -1 = intro turn
    parent_answer: str = Field(default="", max_length=4000)
    safety_flagged: bool = False


@router.post("/guided-journey/step")
async def guided_journey_step_endpoint(
    body: GuidedJourneyStepBody, request: Request
) -> Dict[str, Any]:
    """Emit the coach's next turn in the guided-journey chat wizard.

    Rate-limited via the shared BIFF/verify quota. No auth (offline-
    first parity with the rest of the portal).
    """
    ip = _client_ip(request)
    await _rate_guard(ip)
    try:
        return await portal_ai.guided_journey_step(
            topic=body.topic,
            step_index=body.step_index,
            parent_answer=body.parent_answer,
            safety_flagged=bool(body.safety_flagged),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=502, detail="Coach is warming up — please try again."
        )


# --------------------------------------------------------------------- #
# iter222 · Coparent Snapshot PDF — one-page shareable summary of a
# finished Guided Journey wizard run.
# --------------------------------------------------------------------- #
class GuidedSnapshotPdfBody(BaseModel):
    topic: str = Field(
        pattern="^(foundation|safety|coparenting|medical|educational|psychological)$"
    )
    answers: List[Dict[str, str]] = Field(default_factory=list)
    parent_name: Optional[str] = None
    case_ref: Optional[str] = None
    safety_flagged: bool = False
    variant: str = Field(default="standard", pattern="^(standard|fridge|fridge_pair)$")


@router.post("/guided-snapshot-pdf")
async def guided_snapshot_pdf(body: GuidedSnapshotPdfBody) -> Response:
    """Stream a one-page Coparent Snapshot PDF from a guided run.

    Public — same auth tier as the other portal PDF endpoints so a
    parent can download without an account. ``variant='fridge'``
    returns a postcard-sized A6 variant with hand-sign lines.
    ``variant='fridge_pair'`` returns two side-by-side fridge cards
    on an A5-landscape sheet with a cut line down the middle so both
    parents get an identical card from one print.
    """
    try:
        pdf_bytes = portal_pdf.build_portal_guided_snapshot_pdf(
            topic=body.topic,
            answers=body.answers,
            author_name=body.parent_name,
            case_ref=body.case_ref,
            safety_flagged=bool(body.safety_flagged),
            variant=body.variant,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if body.variant == "fridge":
        suffix = "-fridge"
    elif body.variant == "fridge_pair":
        suffix = "-fridge-pair"
    else:
        suffix = ""
    filename = f"coparent-snapshot-{body.topic}{suffix}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --------------------------------------------------------------------- #
# iter222 · Voice Note transcription (Whisper via Emergent LLM Key)
# --------------------------------------------------------------------- #
from fastapi import UploadFile, File

_MAX_VOICE_BYTES = 25 * 1024 * 1024  # Whisper's 25 MB hard cap
_ALLOWED_VOICE_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/m4a",
    "audio/x-m4a",
    # Some browsers (Safari) omit the codecs suffix
    "audio/mp3",
}


@router.post("/voice-transcribe")
async def voice_transcribe(
    request: Request,
    audio: UploadFile = File(...),
) -> Dict[str, Any]:
    """Transcribe a short parent voice note to text via Whisper.

    Multipart upload from the browser MediaRecorder. Nothing is stored
    on disk — the bytes go straight to Whisper and are dropped. Rate
    limited via the shared BIFF/guided-journey quota so a bad client
    can't burn Whisper credits.
    """
    ip = _client_ip(request)
    await _rate_guard(ip)

    if audio.content_type and audio.content_type not in _ALLOWED_VOICE_TYPES:
        # Chromium sometimes stamps "audio/webm;codecs=opus" — allow it.
        if not audio.content_type.startswith(tuple(_ALLOWED_VOICE_TYPES)):
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported audio type: {audio.content_type}",
            )

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio payload")
    if len(data) > _MAX_VOICE_BYTES:
        raise HTTPException(status_code=413, detail="Audio too large (25 MB max)")

    try:
        text = await portal_ai.transcribe_voice_note(
            data, filename=audio.filename or "voice_note.webm"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.warning("voice transcription failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Voice transcription unavailable — please try typing instead.",
        )
    return {"text": text}


@router.post("/biff-refine")
async def biff_refine_endpoint(body: BiffRefineBody, request: Request) -> Dict[str, Any]:
    """Refine a draft into BIFF style via Claude. Rate limited, no auth.

    When `safety_flagged=true` (the parent's own Quick Safety Check
    returned any risk signal), the coach switches to a grey-rock
    variant so replies stay safer to send to a coercive co-parent.
    """
    ip = _client_ip(request)
    await _rate_guard(ip)
    try:
        result = await portal_ai.refine_biff(
            body.raw, safety_flagged=bool(body.safety_flagged)
        )
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


class WeeklyProgressPdfBody(BaseModel):
    health_index: Dict[str, int] = Field(default_factory=dict)
    biff_logs: Optional[List[Dict[str, Any]]] = Field(default=None)
    milestones: Optional[List[Dict[str, Any]]] = Field(default=None)
    reassessments: Optional[List[Dict[str, Any]]] = Field(default=None)
    foundation_text: Optional[str] = Field(default=None, max_length=5000)
    case_ref: Optional[str] = Field(default=None, max_length=80)
    author_name: Optional[str] = Field(default=None, max_length=120)


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


@router.post("/weekly-progress-pdf")
async def weekly_progress_pdf(body: WeeklyProgressPdfBody) -> Response:
    try:
        pdf_bytes = portal_pdf.build_portal_weekly_progress_pdf(
            health_index=body.health_index or {},
            biff_logs=body.biff_logs or [],
            milestones=body.milestones or [],
            reassessments=body.reassessments or [],
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
                'attachment; filename="sacoparents-weekly-progress.pdf"'
            )
        },
    )


class CompleteReportPdfBody(BaseModel):
    """Complete Coparenting Report bundle payload.

    Every field is optional — the PDF renders an empty-state stub for
    sections the parent hasn't filled in yet, so nothing is silently
    hidden from a reader (mediator / attorney / co-parent).
    """

    safety_ack: Optional[Dict[str, Any]] = Field(default=None)
    cop_assessment: Optional[Dict[str, Any]] = Field(default=None)
    align_records: Optional[List[Dict[str, Any]]] = Field(default=None)
    joint_records: Optional[List[Dict[str, Any]]] = Field(default=None)
    foundation_text: Optional[str] = Field(default=None, max_length=8000)
    case_ref: Optional[str] = Field(default=None, max_length=80)
    author_name: Optional[str] = Field(default=None, max_length=120)


@router.post("/complete-report-pdf")
async def complete_report_pdf(
    body: CompleteReportPdfBody,
    request: Request,
    user: Optional[UserPublic] = Depends(get_current_user_optional),
) -> Response:
    """Assemble the Complete Coparenting Report PDF from the portal's
    self-guided artefacts (Safety Check answers, Co-parenting
    Assessment / Health Index, individual + joint Align-Before-Agreement
    records, and Foundation Statement). Missing sections render as
    empty-state stubs so a mediator or attorney sees exactly what the
    parent has and hasn't completed.

    Optional auth: when the caller presents a valid bearer token, we
    also fetch their latest `agreements` doc and pipe it into Section
    4 as the Joint Alignment Summary. Unauthenticated callers get the
    empty-state stub for that section (or whatever `joint_records`
    they pass in the body).
    """
    joint_summary = None
    if user is not None:
        try:
            db = request.app.state.db
            joint_summary = await db["agreements"].find_one(
                {"user_id": user.user_id},
                {"_id": 0},
                sort=[("generated_at", -1)],
            )
        except Exception:
            # Non-fatal — degrade to the empty-state stub so a Mongo
            # blip never blocks a PDF.
            joint_summary = None

    try:
        pdf_bytes = portal_pdf.build_portal_complete_report_pdf(
            safety_ack=body.safety_ack,
            cop_assessment=body.cop_assessment,
            align_records=body.align_records or [],
            joint_records=body.joint_records or [],
            joint_summary=joint_summary,
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
                'attachment; filename="sacoparents-complete-report.pdf"'
            )
        },
    )


# --------------------------------------------------------------------- #
# Share-links — persist an artefact payload and mint a signed short URL.
# --------------------------------------------------------------------- #
_SHARES_COLLECTION = "portal_pdf_shares"
_SHARE_TTL_DAYS = 30
_ALLOWED_TTL_DAYS = {7, 30}

# Reuse the auth password-hash context so we don't ship a second crypto
# dependency. bcrypt is fine for a short passphrase.
from auth import pwd_ctx as _pwd_ctx  # noqa: E402

# Public origin the short URL is built against. Prefers request scheme+host
# so preview / prod / custom-domain deployments all Just Work; falls back
# to PORTAL_SHARE_ORIGIN env var if present.
_PUBLIC_ORIGIN = os.environ.get("PORTAL_SHARE_ORIGIN", "").rstrip("/")


def _share_origin(request: Request) -> str:
    if _PUBLIC_ORIGIN:
        return _PUBLIC_ORIGIN
    # `x-forwarded-host` beats `host` behind the k8s ingress.
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or "sacoparentsapp.online"
    ).split(",")[0].strip()
    scheme = (
        request.headers.get("x-forwarded-proto")
        or request.url.scheme
        or "https"
    ).split(",")[0].strip()
    return f"{scheme}://{host}"

_ALLOWED_ARTEFACT_TYPES = {"foundation", "legal", "weekly", "complete"}
_FILENAMES = {
    "foundation": "sacoparents-foundation-statement.pdf",
    "legal": "sacoparents-legal-report.pdf",
    "weekly": "sacoparents-weekly-progress.pdf",
    "complete": "sacoparents-complete-report.pdf",
}


class SharePayload(BaseModel):
    artefact_type: str = Field(pattern="^(foundation|legal|weekly|complete)$")
    # Reuse the same body shape as the direct-download endpoints.
    payload: Dict[str, Any] = Field(default_factory=dict)
    # Optional passphrase — if set, the recipient must supply it via
    # `?p=<passphrase>` on the fetch URL. Max 40 chars is a UX choice,
    # not a security ceiling (bcrypt truncates at 72 bytes anyway).
    passphrase: Optional[str] = Field(default=None, max_length=40)
    ttl_days: Optional[int] = Field(default=None, ge=1, le=90)


@router.post("/share")
async def create_share_link(body: SharePayload, request: Request) -> Dict[str, Any]:
    """Persist the payload used to generate a portal PDF and mint a
    signed short URL. Rate limited (shares the BIFF/verify quota).

    Returns `{share_id, url, expires_at, requires_passphrase}`.
    """
    ip = _client_ip(request)
    await _rate_guard(ip)

    if body.artefact_type not in _ALLOWED_ARTEFACT_TYPES:
        raise HTTPException(status_code=400, detail="Unknown artefact type")

    # Validate the payload can produce a PDF before we store it — cheap
    # smoke test that saves us from minting broken links.
    try:
        _regenerate_share_pdf(body.artefact_type, body.payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ttl_days = body.ttl_days if body.ttl_days in _ALLOWED_TTL_DAYS else _SHARE_TTL_DAYS
    passphrase = (body.passphrase or "").strip()
    passphrase_hash = _pwd_ctx.hash(passphrase[:72]) if passphrase else None

    share_id = secrets.token_urlsafe(10)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=ttl_days)

    db = request.app.state.db
    await db[_SHARES_COLLECTION].insert_one(
        {
            "share_id": share_id,
            "artefact_type": body.artefact_type,
            "payload": body.payload,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "revoked_at": None,
            "hit_count": 0,
            "passphrase_hash": passphrase_hash,
            "ttl_days": ttl_days,
        }
    )

    return {
        "share_id": share_id,
        "url": f"{_share_origin(request)}/api/portal/share/{share_id}.pdf",
        "expires_at": expires_at.isoformat(),
        "requires_passphrase": bool(passphrase_hash),
        "ttl_days": ttl_days,
    }


def _regenerate_share_pdf(artefact_type: str, payload: Dict[str, Any]) -> bytes:
    """Dispatch to the correct builder based on artefact type."""
    if artefact_type == "foundation":
        return portal_pdf.build_portal_foundation_pdf(
            foundation_text=payload.get("foundation_text") or "",
            case_ref=payload.get("case_ref"),
            author_name=payload.get("author_name"),
        )
    if artefact_type == "legal":
        return portal_pdf.build_portal_legal_report_pdf(
            health_index=payload.get("health_index") or {},
            foundation_text=payload.get("foundation_text"),
            signatures=payload.get("signatures") or {},
            matrix=payload.get("matrix"),
            case_ref=payload.get("case_ref"),
        )
    if artefact_type == "weekly":
        return portal_pdf.build_portal_weekly_progress_pdf(
            health_index=payload.get("health_index") or {},
            biff_logs=payload.get("biff_logs") or [],
            milestones=payload.get("milestones") or [],
            reassessments=payload.get("reassessments") or [],
            foundation_text=payload.get("foundation_text"),
            case_ref=payload.get("case_ref"),
            author_name=payload.get("author_name"),
        )
    if artefact_type == "complete":
        return portal_pdf.build_portal_complete_report_pdf(
            safety_ack=payload.get("safety_ack"),
            cop_assessment=payload.get("cop_assessment"),
            align_records=payload.get("align_records") or [],
            joint_records=payload.get("joint_records") or [],
            joint_summary=payload.get("joint_summary"),
            foundation_text=payload.get("foundation_text"),
            case_ref=payload.get("case_ref"),
            author_name=payload.get("author_name"),
        )
    raise ValueError(f"Unknown artefact_type: {artefact_type}")


_PASSPHRASE_GATE_HTML = """<!doctype html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Enter passphrase - sacoparentsapp.online</title>
<style>
  :root { --purple:#4A1A6E; --accent:#6D28D9; --wash:#F4EFFF; --ink:#1A1330; --slate:#64748B; }
  body { font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    background:#F1F5F9; margin:0; padding:0; color:var(--ink); min-height:100vh;
    display:flex; align-items:center; justify-content:center; }
  .card { max-width: 400px; width: calc(100% - 32px); background:#fff;
    border-radius: 20px; padding: 28px; box-shadow: 0 10px 40px rgba(29,20,60,0.15);
    border: 1px solid #E5E0EE; }
  .brand { color: var(--purple); font-weight: 700; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  h1 { color: var(--ink); font-size: 20px; margin: 0 0 8px 0; }
  p { color: var(--slate); font-size: 13px; line-height: 1.5; margin: 0 0 16px; }
  input { width: 100%; padding: 12px 14px; border: 2px solid #E5E0EE; border-radius: 12px;
    font-size: 15px; font-family: ui-monospace,Menlo,Consolas,monospace;
    letter-spacing: 2px; box-sizing: border-box; }
  input:focus { outline: none; border-color: var(--accent); }
  button { margin-top: 12px; width: 100%; padding: 12px 14px; border: 0;
    background: var(--purple); color: white; font-weight: 700; font-size: 14px;
    border-radius: 12px; cursor: pointer; }
  button:hover { background: #3D1360; }
  .err { color: #B91C1C; font-size: 12px; margin-top: 8px; font-weight: 600; }
  .foot { color: var(--slate); font-size: 10px; text-align:center; margin-top:20px; }
</style></head>
<body>
  <form class="card" method="GET">
    <div class="brand">sacoparentsapp.online</div>
    <h1>Passphrase required</h1>
    <p>The parent who shared this link protected it with a passphrase. Enter it below to view the PDF.</p>
    <input type="text" name="p" placeholder="Passphrase" autofocus autocomplete="off"/>
    {{ERROR_BLOCK}}
    <button type="submit">Open PDF</button>
    <div class="foot">SA CoParents Assessment &amp; Alignment Portal</div>
  </form>
</body></html>"""


def _passphrase_gate_html(*, error: bool) -> str:
    err_block = (
        '<div class="err">That passphrase did not match. Try again.</div>'
        if error else ""
    )
    return _PASSPHRASE_GATE_HTML.replace("{{ERROR_BLOCK}}", err_block)


@router.get("/share/{share_id}.pdf")
async def fetch_share_pdf(
    share_id: str,
    request: Request,
    p: Optional[str] = None,
) -> Response:
    """Regenerate and stream the PDF a share link points to.

    If the share is passphrase-protected, `?p=<passphrase>` must be
    supplied (and match) — otherwise the response is a small HTML
    gateway page (200 OK, text/html) asking the recipient to enter it.
    """
    db = request.app.state.db
    # Very lax id shape so we don't over-validate — the collection
    # lookup is the real gate. But block obvious bad inputs so we can
    # 404 fast.
    if not share_id or len(share_id) > 32 or not share_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=404, detail="Share not found")

    doc = await db[_SHARES_COLLECTION].find_one({"share_id": share_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Share not found")
    if doc.get("revoked_at"):
        raise HTTPException(status_code=410, detail="Share revoked")
    exp = doc.get("expires_at")
    if exp:
        try:
            expires_at = datetime.fromisoformat(exp) if isinstance(exp, str) else exp
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=410, detail="Share expired")
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001 - corrupt expiry => fail closed
            raise HTTPException(status_code=410, detail="Share expired")

    # Passphrase gate — if the share has a hash, the recipient must
    # supply the matching passphrase via ?p=<...>. When missing we
    # serve a friendly HTML form (200 OK). When wrong we serve the
    # same form with an error message.
    passphrase_hash = doc.get("passphrase_hash")
    if passphrase_hash:
        if not p:
            return Response(
                content=_passphrase_gate_html(error=False),
                media_type="text/html",
                status_code=200,
                headers={"Cache-Control": "no-store"},
            )
        try:
            ok = _pwd_ctx.verify((p or "")[:72], passphrase_hash)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            return Response(
                content=_passphrase_gate_html(error=True),
                media_type="text/html",
                status_code=200,
                headers={"Cache-Control": "no-store"},
            )

    try:
        pdf_bytes = _regenerate_share_pdf(
            doc.get("artefact_type") or "foundation",
            doc.get("payload") or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Bump the hit counter — fire-and-forget, doesn't block the response.
    try:
        await db[_SHARES_COLLECTION].update_one(
            {"share_id": share_id},
            {
                "$inc": {"hit_count": 1},
                "$set": {"last_fetched_at": datetime.now(timezone.utc).isoformat()},
            },
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to bump share hit_count for %s", share_id)

    filename = _FILENAMES.get(doc.get("artefact_type"), "sacoparents.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )
