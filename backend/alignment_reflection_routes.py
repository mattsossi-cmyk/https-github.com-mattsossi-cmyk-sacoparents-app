"""Alignment Reflection Prompts — API endpoints (Iter191).

Mirrors `activities_alignment_routes.py`. Mounted at
`/api/alignment-reflection`.

Endpoints
---------
GET  /alignment-reflection/schema/{subject}          - Public prompt schema
GET  /alignment-reflection/{subject}/mine            - Caller's saved reflection
PUT  /alignment-reflection/{subject}                 - Save (upsert) caller's answers
POST /alignment-reflection/{subject}/compare        - Compare with a co-parent

Data model
----------
Mongo collection `alignment_reflections`:
    { user_id, email, subject, answers:{prompt_id: str}, updated_at, created_at }

Answers are stored VERBATIM — the analysis layer (see
`alignment_reflection_analysis.py`) is the ONLY place that reads them
to compare across parents. Per PHI-safety principle: individual
free-text is never surfaced to the co-parent unless the compare
endpoint successfully loads BOTH docs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from alignment_reflection_questions import (
    SUBJECTS,
    SUBJECT_CO_PARENTING,
    SUBJECT_SAFETY,
    is_known_subject,
    is_sensitive_subject,
    prompts_for,
    prompt_ids_for,
)
from alignment_reflection_analysis import analyse_reflections


router = APIRouter(tags=["alignment-reflection"])
logger = logging.getLogger(__name__)

_COLL = "alignment_reflections"

# Hard cap per-answer length to match the prompt config. Kept in
# lockstep with `alignment_reflection_questions.py::max_length`. Any
# submitted answer longer than this is truncated server-side rather
# than rejected — parents typing a monologue should still save.
_ANSWER_MAX = 600


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(v: Any) -> Optional[str]:
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v if isinstance(v, str) else None


def _clean_answers(subject: str, raw: Dict[str, Any]) -> Dict[str, str]:
    """Filter answers down to the KNOWN prompt IDs for this subject
    and truncate each to the per-answer cap. Unknown prompt IDs are
    silently dropped so a stale client cannot poison the record."""
    allowed = set(prompt_ids_for(subject))
    cleaned: Dict[str, str] = {}
    for k, v in (raw or {}).items():
        if k not in allowed:
            continue
        text = (v or "").strip()
        if not text:
            continue
        cleaned[k] = text[:_ANSWER_MAX]
    return cleaned


def _serialize(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Shape a Mongo document for the API response — never leaks
    `_id` or the caller's own user_id back on the wire."""
    if not doc:
        return {"answers": {}, "updated_at": None, "created_at": None}
    return {
        "answers":    doc.get("answers") or {},
        "updated_at": _iso(doc.get("updated_at")),
        "created_at": _iso(doc.get("created_at")),
    }


# ---------------------------------------------------------------------------
# Pydantic bodies.
# ---------------------------------------------------------------------------

class SavePayload(BaseModel):
    """Caller pushes {prompt_id: str} for the subject. Extra keys are
    dropped server-side to prevent client-side prompt spoofing."""
    answers: Dict[str, str] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    coparent_email: str
    # Iter192: safety-sensitive subjects require an explicit
    # dual-consent flag on every compare request. The flag is
    # transient — it never persists, so a Safety compare is a
    # deliberate ceremony every time.
    safety_dual_consent_acknowledged: bool = False


# ---------------------------------------------------------------------------
# Endpoints.
# ---------------------------------------------------------------------------

def _require_subject(subject: str) -> str:
    if not is_known_subject(subject):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown alignment reflection subject: {subject}",
        )
    return subject


@router.get("/alignment-reflection/subjects")
async def list_subjects():
    """Public subject picker payload — every subject with its label,
    blurb, and `sensitive` flag so the frontend can render the safety
    disclosure banner where needed."""
    return {
        "subjects": [
            {
                "id":        meta["id"],
                "label":     meta["label"],
                "blurb":     meta["blurb"],
                "sensitive": meta.get("sensitive", False),
                "prompt_count": len(meta["prompts"]),
            }
            for meta in SUBJECTS.values()
        ],
    }


@router.get("/alignment-reflection/schema/{subject}")
async def get_schema(subject: str):
    """Public prompt schema for a subject — no auth required so the
    marketing page can preview the questions the parent will see."""
    _require_subject(subject)
    meta = SUBJECTS[subject]
    return {
        "id":      meta["id"],
        "label":   meta["label"],
        "blurb":   meta["blurb"],
        "prompts": prompts_for(subject),
    }


@router.get("/alignment-reflection/{subject}/mine")
async def get_mine(
    subject: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _require_subject(subject)
    doc = await db[_COLL].find_one(
        {"user_id": current.user_id, "subject": subject},
        {"_id": 0},
    )
    return _serialize(doc)


@router.put("/alignment-reflection/{subject}")
async def save_reflection(
    subject: str,
    body: SavePayload,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _require_subject(subject)
    cleaned = _clean_answers(subject, body.answers)
    await db[_COLL].update_one(
        {"user_id": current.user_id, "subject": subject},
        {
            "$set": {
                "user_id":    current.user_id,
                "email":      current.email,
                "subject":    subject,
                "answers":    cleaned,
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )
    return {"ok": True, "answered_count": len(cleaned)}


@router.post("/alignment-reflection/{subject}/compare")
async def compare(
    subject: str,
    body: CompareRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the sacoparentsalign-style analysis when BOTH parents
    have saved answers for this subject. If only the caller has
    saved, return a `waiting_on_coparent` status so the frontend
    can show a "we're waiting for your co-parent" state instead of
    a broken report page."""
    _require_subject(subject)
    if not (body.coparent_email or "").strip():
        raise HTTPException(status_code=400, detail="coparent_email required")

    # Iter192 · safety-sensitive routing. Safety reflections carry
    # extra weight — physical/emotional-safety topics can escalate a
    # low-conflict co-parenting relationship if surfaced carelessly.
    # Both parents must EXPLICITLY acknowledge dual-consent on every
    # compare request; the flag is never persisted so the ceremony is
    # deliberate each time.
    if is_sensitive_subject(subject) and not body.safety_dual_consent_acknowledged:
        raise HTTPException(
            status_code=428,  # Precondition Required — matches the "consent required" HTTP semantics.
            detail=(
                "This subject is safety-sensitive. Set "
                "`safety_dual_consent_acknowledged` to true after "
                "confirming BOTH parents have opted in — Safety "
                "reflections are never shared without dual-consent."
            ),
        )

    coparent = await db.users.find_one(
        {"email": body.coparent_email.lower().strip()},
        {"user_id": 1, "email": 1, "name": 1},
    )
    if not coparent:
        raise HTTPException(status_code=404, detail="Co-parent account not found")

    self_doc = await db[_COLL].find_one(
        {"user_id": current.user_id, "subject": subject},
        {"_id": 0},
    )
    coparent_doc = await db[_COLL].find_one(
        {"user_id": coparent["user_id"], "subject": subject},
        {"_id": 0},
    )

    if not self_doc or not (self_doc.get("answers") or {}):
        raise HTTPException(
            status_code=409,
            detail=(
                "Complete your Alignment Reflection before comparing with "
                "your co-parent."
            ),
        )
    if not coparent_doc or not (coparent_doc.get("answers") or {}):
        return {
            "status":   "waiting_on_coparent",
            "subject":  subject,
            "self":     _serialize(self_doc),
            "coparent": {
                "email": coparent["email"],
                "name":  coparent.get("name") or "your co-parent",
            },
        }

    parent_a_name = (
        getattr(current, "name", None)
        or (current.email.split("@")[0] if current.email else "Parent A")
    )
    parent_b_name = coparent.get("name") or (
        coparent["email"].split("@")[0] if coparent.get("email") else "Parent B"
    )
    analysis = analyse_reflections(
        self_doc.get("answers") or {},
        coparent_doc.get("answers") or {},
        subject=subject,
        parent_a_name=parent_a_name,
        parent_b_name=parent_b_name,
    )
    return {
        "status":       "ready",
        "subject":      subject,
        "parent_a_name": parent_a_name,
        "parent_b_name": parent_b_name,
        "analysis":     analysis,
    }
