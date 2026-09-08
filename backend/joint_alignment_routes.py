"""
Joint Alignment — professional-driven case flow.

Introduced 2026-03-04 to support the workflow where a professional
(mediator, attorney, therapist, parenting facilitator) creates a
Joint Alignment Case on `sacoparentsalign.com` and both parents are
invited via secure single-purpose tokens to complete their private
assessments on `sacoparentsapp.online`.

Endpoints mounted under `/api`:

Server-to-server (Align → this app), gated on `X-Integration-Key`:
  * POST /integrations/joint-alignment/cases
        Create a new case + emit invitation URLs for both parents.
        Response includes `case_id` (`SA-XXXXXX`), plus each
        parent's `invitation_url` — Align uses those URLs in the
        emails it sends.
  * GET  /integrations/joint-alignment/cases/{case_id}
        Retrieve the case status. When both parents have
        completed, the response also includes their data-minimised
        assessment payloads (only the lane requested by the case,
        never any unrelated SA CoParents data).

Parent-facing (JWT required unless otherwise stated):
  * GET  /joint-alignment/invitation/{token}
        No auth required — used by the /join/:token landing page
        to render the "You've Been Invited" screen. Returns only
        the minimal preview: assessment_type, professional_name,
        case_id, expired? — never any PII of the other parent.
  * POST /joint-alignment/invitation/{token}/accept
        JWT required. Associates the invitation with the parent's
        account. The parent's authenticated email must match the
        invitation's email (case-insensitive) — this is what
        prevents Parent B from claiming Parent A's invitation.
  * POST /joint-alignment/manual-code
        JWT required. Alternate entry when the parent has only
        the visible `SA-XXXXXX` case_id (no invitation token in
        hand). Same email-match guardrail.
  * GET  /joint-alignment/mine
        JWT required. Returns all cases the authenticated parent
        appears in, shaped for the dashboard "Joint Alignment
        Requests" section. Never includes the co-parent's
        answers.

Guardrails
----------
* All server-to-server calls check `X-Integration-Key` via
  `hmac.compare_digest`.
* Invitation tokens are 32-byte urlsafe random strings; TTL 7 days.
* Case IDs use the same human-friendly `SA-XXXXXX` format as
  parent-driven link codes so parents don't have to learn two
  systems. Collision-resistant retry loop on mint.
* Data minimisation: the case export includes ONLY the assessment
  lane requested by the case, never the parent's foundation
  statement / other lanes / mediation prep / notes.
* An invitation can only be accepted by an authenticated user whose
  email matches. The visible SA-XXXXXX case_id ALONE is never
  sufficient to see any content.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, ValidationError

from auth import UserPublic, get_current_user, get_db


router = APIRouter(tags=["joint-alignment"])
logger = logging.getLogger(__name__)

_CASES_COLL = "joint_alignment_cases"

_ASSESSMENT_TYPES = {
    "co-parenting",
    "communication",
    "educational",
    "medical",
    "psychological",
    "special-needs",
}

# Deep-dive collection each assessment type maps into, for the export.
_ASSESSMENT_REPORT_COLL = {
    "medical": "med_deep_reports",
    "educational": "edu_deep_reports",
    "psychological": "psych_deep_reports",
}

# Case ID format matches the parent-driven mint: SA-XXXXXX (6 digits).
_CASE_ID_PREFIX = "SA-"
_CASE_ID_DIGITS = 6

_INVITATION_TOKEN_BYTES = 32
_INVITATION_TTL_DAYS = 7
_CASE_TTL_DAYS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: Optional[datetime]) -> bool:
    """
    Motor returns tz-naive datetimes from Mongo even when we stored
    tz-aware. Normalise to UTC on the read side so the comparison
    never TypeErrors.
    """
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < _now()


def _as_aware_utc(v) -> Optional[datetime]:
    """Coerce any Mongo-returned datetime (tz-naive UTC) or ISO string
    into a tz-aware UTC datetime. Returns None for falsy / unparsable
    input. Used by the analytics aggregator when computing time-deltas
    so mixed-timezone rows never TypeError."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _iso(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v


def _shared_secret() -> Optional[str]:
    return os.environ.get("INTEGRATION_SHARED_SECRET")


def _verify_integration_key(header_value: Optional[str]) -> None:
    expected = _shared_secret()
    if not expected:
        logger.error("INTEGRATION_SHARED_SECRET is not set — refusing request")
        raise HTTPException(status_code=503, detail="Integration not configured")
    if not hmac.compare_digest(header_value or "", expected):
        raise HTTPException(status_code=401, detail="Invalid integration key")


def _generate_case_id() -> str:
    digits = "".join(secrets.choice("0123456789") for _ in range(_CASE_ID_DIGITS))
    return f"{_CASE_ID_PREFIX}{digits}"


async def _mint_unique_case_id(db: AsyncIOMotorDatabase) -> str:
    for _ in range(10):
        candidate = _generate_case_id()
        if not await db[_CASES_COLL].find_one({"case_id": candidate}, {"_id": 1}):
            return candidate
    raise HTTPException(status_code=500, detail="Failed to mint unique case id")


def _mint_invitation_token() -> str:
    return secrets.token_urlsafe(_INVITATION_TOKEN_BYTES)


def _join_base() -> str:
    """
    Public URL parents land on. Default points at the SA CoParents
    app (where the assessment is completed) — never Align.
    """
    return os.environ.get(
        "APP_JOIN_URL_BASE", "https://sacoparentsapp.online/join"
    ).rstrip("/")


def _validate_assessment_type(t: str) -> str:
    if t not in _ASSESSMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown assessment_type — expected one of {sorted(_ASSESSMENT_TYPES)}",
        )
    return t


# ------------------------------- schemas ------------------------------- #

class ProfessionalInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr


class ParentInfo(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=200)


class CreateCaseRequest(BaseModel):
    assessment_type: str
    professional: ProfessionalInfo
    parents: List[ParentInfo]
    align_case_reference: Optional[str] = Field(default=None, max_length=128)


class CreateCaseParentResponse(BaseModel):
    email: EmailStr
    invitation_url: str
    token_expires_at: str


class CreateCaseResponse(BaseModel):
    case_id: str
    status: str
    assessment_type: str
    created_at: str
    case_expires_at: str
    parents: List[CreateCaseParentResponse]
    email_deliveries: Optional[List[Dict[str, Any]]] = None


class ManualCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)


# ------------------------------- helpers ------------------------------- #

def _normalise_case_id(raw: str) -> str:
    """Accept 'SA-482731', 'sa 482731', '482731', 'SA482731'."""
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != _CASE_ID_DIGITS:
        return ""
    return f"{_CASE_ID_PREFIX}{digits}"


def _parent_public_shape(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Never expose the *other* parent's answers, tokens, or user_id
    beyond the presence signal a professional or a parent needs to
    see: name, email hint, status.
    """
    return {
        "email": p.get("email"),
        "name": p.get("name"),
        "status": (
            "completed"
            if p.get("assessment_completed_at")
            else "in_progress"
            if p.get("accepted_at")
            else "invited"
        ),
        "accepted_at": _iso(p.get("accepted_at")),
        "assessment_completed_at": _iso(p.get("assessment_completed_at")),
    }


def _case_public_shape(case: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "assessment_type": case["assessment_type"],
        "status": _derived_status(case),
        "professional": {
            "name": (case.get("professional") or {}).get("name"),
            # id + email deliberately withheld — those are Align-side identifiers
        },
        "align_case_reference": case.get("align_case_reference"),
        "parents": [_parent_public_shape(p) for p in (case.get("parents") or [])],
        "created_at": _iso(case.get("created_at")),
        "case_expires_at": _iso(case.get("case_expires_at")),
    }


def _derived_status(case: Dict[str, Any]) -> str:
    parents = case.get("parents") or []
    if case.get("status") in ("expired", "cancelled"):
        return case["status"]
    completed = sum(1 for p in parents if p.get("assessment_completed_at"))
    accepted = sum(1 for p in parents if p.get("accepted_at"))
    if completed >= len(parents) and parents:
        return "both_complete"
    if accepted or completed:
        return "in_progress"
    return "pending"


async def _latest_report(
    db: AsyncIOMotorDatabase, coll: str, user_id: str
) -> Optional[Dict[str, Any]]:
    return await db[coll].find_one({"user_id": user_id}, sort=[("generated_at", -1)])


async def _minimised_assessment_payload(
    db: AsyncIOMotorDatabase, assessment_type: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Only the assessment lane the case requested. Never the parent's
    other lanes, unrelated notes, or safety-screen answers.
    Returns `None` if the parent has not completed this lane.

    Co-Parenting pathway (2026-03-04 founder spec):
        Co-Parenting Assessment → Foundation Statement →
        Mediation Statement → Mediation Preparation.
    So a co-parenting export bundles all four steps into a single
    payload the Align joint report can render from.
    """
    if assessment_type == "co-parenting":
        return await _coparenting_payload(db, user_id)

    coll = _ASSESSMENT_REPORT_COLL.get(assessment_type)
    if not coll:
        # Communication uses its own compare pipeline; special-needs
        # is a super-set exported via med/edu/psych rather than a
        # single collection. Return None for now.
        return None
    doc = await _latest_report(db, coll, user_id)
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


async def _coparenting_payload(
    db: AsyncIOMotorDatabase, user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Bundle the four Co-Parenting pathway artefacts:
      1. `assessment`         — SNC v2 co-parenting compare doc.
      2. `foundation_statement` — the four reflective prompts saved
         via /api/mediation/reflection.
      3. `mediation_statement` — AI-generated short document (if
         already generated). Nullable.
      4. `mediation_preparation` — child_goals + issues + priority +
         readiness sections from prep_data.

    Returns `None` when NONE of the four artefacts exist for this
    parent — the case shouldn't advance to `both_complete` without
    at least one step done.
    """
    prep = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0}) or {}
    reflection = prep.get("reflection") or {}
    completed = prep.get("completed") or {}
    snc_doc = await db.snc_v2_answers.find_one({"user_id": user_id}, {"_id": 0})
    mediation_statement_doc = await db.mediation_statements.find_one(
        {"user_id": user_id}, sort=[("generated_at", -1)]
    )

    has_any = any(
        [
            snc_doc,
            any(reflection.get(k) for k in ("child_lens", "my_part", "best_case", "coparent_lens")),
            bool(mediation_statement_doc),
            any(completed.values()),
        ]
    )
    if not has_any:
        return None

    return {
        "assessment": (
            {
                "answers_summary": _summarise_snc_answers(snc_doc.get("answers") if snc_doc else None),
                "updated_at": _iso((snc_doc or {}).get("updated_at")),
            }
            if snc_doc
            else None
        ),
        "foundation_statement": {
            "child_lens": _clean(reflection.get("child_lens")),
            "my_part": _clean(reflection.get("my_part")),
            "best_case": _clean(reflection.get("best_case")),
            "coparent_lens": _clean(reflection.get("coparent_lens")),
            "updated_at": _iso(reflection.get("updated_at") or prep.get("updated_at")),
        }
        if reflection
        else None,
        "mediation_statement": (
            {
                "text": mediation_statement_doc.get("text"),
                "generated_at": _iso(mediation_statement_doc.get("generated_at")),
            }
            if mediation_statement_doc
            else None
        ),
        "mediation_preparation": {
            "child_goals": _pick_prep(prep.get("child_goals"), ("focus", "topics", "notes")),
            "issues": _pick_prep(prep.get("issues"), ("selected", "notes", "priority")),
            "priority": _pick_prep(prep.get("priority"), ("issue", "why", "outcome")),
            "readiness": _pick_prep(prep.get("readiness"), ("score", "reflection")),
            "completed_sections": [k for k, v in completed.items() if v],
            "updated_at": _iso(prep.get("updated_at")),
        },
        "pathway_version": 1,
    }


def _summarise_snc_answers(answers) -> Optional[Dict[str, Any]]:
    """
    Compact projection: how many questions answered per dimension.
    Raw answers are never returned to Align — that would break the
    data-minimisation contract.
    """
    if not isinstance(answers, dict):
        return None
    return {
        "answered_count": sum(1 for v in answers.values() if v is not None),
        "keys": sorted(answers.keys())[:50],
    }


def _pick_prep(source, keep):
    if not isinstance(source, dict):
        return None
    picked = {k: source.get(k) for k in keep if source.get(k) is not None}
    return picked or None


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


# =========================== integration endpoints =========================== #

class ProfessionalCreateCaseRequest(BaseModel):
    """
    In-app professional-driven case creation. Same shape as the
    server-to-server variant but without the `professional` block —
    the authenticated caller IS the professional. Optional
    `professional_name` / `professional_email` overrides let a
    coordinator create the case on behalf of another professional
    (useful when a paralegal is logged in and driving the workflow
    for the mediator).
    """
    assessment_type: str
    parents: List[ParentInfo]
    professional_name: Optional[str] = Field(default=None, max_length=200)
    professional_email: Optional[EmailStr] = Field(default=None)
    align_case_reference: Optional[str] = Field(default=None, max_length=128)
    reminder_note: Optional[str] = Field(default=None, max_length=240)


@router.post(
    "/professional/joint-alignment/cases",
    response_model=CreateCaseResponse,
)
async def professional_create_case(
    body: ProfessionalCreateCaseRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated variant of `integration_create_case`. Lets a
    mediator, attorney, or paralegal create a Joint Alignment Case
    from inside the parent app without needing to bounce to
    `sacoparentsalign.com`. The caller becomes the professional of
    record (name/email pulled from their account) unless override
    fields are supplied.

    Rate-limited implicitly by JWT (one authenticated account can't
    fan out mint requests to spam parents at high volume — abusive
    accounts get locked out through the standard auth system).
    """
    return await _create_and_invite_case(body=body, current=current, db=db)


async def _create_and_invite_case(
    *,
    body: ProfessionalCreateCaseRequest,
    current: UserPublic,
    db: AsyncIOMotorDatabase,
) -> CreateCaseResponse:
    """Shared core between the single-case POST endpoint and the
    bulk CSV import. Validates the payload, mints the case + tokens,
    inserts the case doc, and best-effort fires invitation emails.

    Raises `HTTPException` for validation failures — the bulk caller
    catches them and records each row's outcome individually so a
    single bad row doesn't abort the whole import.
    """
    assessment_type = _validate_assessment_type(body.assessment_type)

    if len(body.parents) != 2:
        raise HTTPException(
            status_code=400,
            detail="A Joint Alignment Case requires exactly two parents.",
        )
    emails = {p.email.lower() for p in body.parents}
    if len(emails) != 2:
        raise HTTPException(
            status_code=400,
            detail="Parent emails must be distinct.",
        )

    prof_name = (body.professional_name or current.name or "").strip()
    prof_email = (body.professional_email or current.email or "").strip().lower()
    if not prof_name or not prof_email:
        raise HTTPException(
            status_code=400,
            detail="Professional name and email are required.",
        )

    case_id = await _mint_unique_case_id(db)
    now = _now()
    token_exp = now + timedelta(days=_INVITATION_TTL_DAYS)
    case_exp = now + timedelta(days=_CASE_TTL_DAYS)

    parent_docs = []
    parent_response_rows: List[CreateCaseParentResponse] = []
    join_base = _join_base()
    for idx, parent in enumerate(body.parents):
        token = _mint_invitation_token()
        parent_docs.append(
            {
                "parent_slot": "A" if idx == 0 else "B",
                "email": parent.email.lower(),
                "name": parent.name,
                "invitation_token": token,
                "token_expires_at": token_exp,
                "accepted_at": None,
                "user_id": None,
                "assessment_completed_at": None,
                "assessment_ref": None,
            }
        )
        parent_response_rows.append(
            CreateCaseParentResponse(
                email=parent.email,
                invitation_url=f"{join_base}/{token}",
                token_expires_at=_iso(token_exp),
            )
        )

    case_doc = {
        "case_id": case_id,
        "assessment_type": assessment_type,
        "professional": {
            # Track the app-user who minted the case so we can list
            # cases-I-created without leaking cross-professional data.
            "id": current.user_id,
            "name": prof_name,
            "email": prof_email,
        },
        "professional_created_by": current.user_id,
        "origin": "in_app_professional",
        "align_case_reference": body.align_case_reference,
        "reminder_note": (body.reminder_note or "").strip() or None,
        "parents": parent_docs,
        "status": "pending",
        "created_at": now,
        "case_expires_at": case_exp,
    }
    await db[_CASES_COLL].insert_one(case_doc)
    logger.info(
        "joint-alignment case created in-app case_id=%s prof_user=%s assessment=%s",
        case_id,
        current.user_id,
        assessment_type,
    )

    # Best-effort invitation emails so the mediator doesn't have to
    # copy-paste. Never fail the mint if delivery breaks — the URLs
    # are already returned in the response for on-screen copy.
    email_status: List[Dict[str, Any]] = []
    for idx, (parent, row) in enumerate(zip(body.parents, parent_response_rows)):
        try:
            from email_service import send_joint_alignment_invitation
            send_joint_alignment_invitation(
                to_email=parent.email,
                invitation_url=row.invitation_url,
                case_id=case_id,
                professional_name=prof_name,
                parent_name=parent.name,
                assessment_type=assessment_type,
            )
            email_status.append({"email": parent.email, "delivered": True})
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "joint-alignment invite email failed case=%s parent_idx=%s err=%s",
                case_id, idx, exc,
            )
            email_status.append({"email": parent.email, "delivered": False})

    return CreateCaseResponse(
        case_id=case_id,
        status="pending",
        assessment_type=assessment_type,
        created_at=_iso(now),
        case_expires_at=_iso(case_exp),
        parents=parent_response_rows,
        email_deliveries=email_status,
    )


# ============ Bulk CSV Invite ============
# Header names accepted in the uploaded CSV (case-insensitive). A row
# that provides `assessment_type` (or the alias `type`) overrides the
# multipart form's `default_assessment_type` fallback. A row that
# provides `reminder_note` (alias `note`) overrides the multipart's
# `default_reminder_note`.
#
# Required columns per row: parent1_email, parent2_email.
# Optional: parent1_name, parent2_name, assessment_type, reminder_note, reference.
_BULK_CSV_MAX_ROWS = 100
_BULK_CSV_MAX_BYTES = 128 * 1024  # 128KB — comfortably covers 100 rows
_BULK_CSV_ALIASES = {
    "parent1_email": {"parent1_email", "parent_1_email", "email_1", "parent1email"},
    "parent2_email": {"parent2_email", "parent_2_email", "email_2", "parent2email"},
    "parent1_name":  {"parent1_name", "parent_1_name", "name_1", "parent1name"},
    "parent2_name":  {"parent2_name", "parent_2_name", "name_2", "parent2name"},
    "assessment_type": {"assessment_type", "type", "lane", "assessment"},
    "reminder_note": {"reminder_note", "note"},
    "reference":     {"reference", "ref", "align_case_reference"},
}


def _normalise_bulk_headers(raw_headers: List[str]) -> Dict[str, int]:
    """Map incoming CSV header cell → canonical field name (via the
    alias table). Returns {canonical_field: column_index}. Extra
    columns are ignored (never raise — mediators paste from Excel and
    often carry stray columns)."""
    out: Dict[str, int] = {}
    for idx, raw in enumerate(raw_headers):
        key = (raw or "").strip().lower()
        for canonical, aliases in _BULK_CSV_ALIASES.items():
            if canonical in out:
                continue
            if key in aliases:
                out[canonical] = idx
                break
    return out


async def _bulk_duplicate_case_exists(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    email_a: str,
    email_b: str,
) -> Optional[str]:
    """Return an active `case_id` when the caller has already minted
    an in-app case pairing these two emails (any lane), otherwise
    None. Only "pending" and "in_progress" are considered active —
    finished / cancelled / expired cases don't block a fresh mint."""
    e1 = email_a.lower()
    e2 = email_b.lower()
    active_row = await db[_CASES_COLL].find_one(
        {
            "professional_created_by": user_id,
            "origin": "in_app_professional",
            "status": {"$in": ["pending", "in_progress"]},
            "parents.email": {"$all": [e1, e2]},
        },
        {"_id": 0, "case_id": 1},
    )
    return active_row.get("case_id") if active_row else None


_BULK_IMPORTS_COLL = "bulk_csv_imports"
_BULK_HISTORY_PAGE_LIMIT = 50           # cap for list endpoint
_BULK_SAMPLE_ERROR_LIMIT = 5            # errors stored inline on the summary row


async def _record_bulk_import(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    filename: Optional[str],
    default_lane: Optional[str],
    default_note: Optional[str],
    total_rows: int,
    created: List[Dict[str, Any]],
    skipped: List[Dict[str, Any]],
    errored: List[Dict[str, Any]],
    variant: str,      # "single" or "stream" — powers UX distinction
    started_at: datetime,
) -> str:
    """Persist a one-line summary of a bulk-CSV import so the
    mediator can visit `/professional/joint-alignment/bulk/history`
    later and re-inspect a batch. Errors are truncated to the first
    5 for the summary row; full detail lives in the `errored`
    breakdown stored alongside.

    Never raises — a logging failure MUST NOT abort a successful
    import (the cases already exist). Returns the new import_id, or
    an empty string on failure.
    """
    try:
        import_id = uuid.uuid4().hex[:12]
        await db[_BULK_IMPORTS_COLL].insert_one({
            "import_id": import_id,
            "user_id": user_id,
            "variant": variant,
            "filename": (filename or "").strip() or None,
            "default_assessment_type": default_lane,
            "default_reminder_note": default_note,
            "started_at": started_at,
            "finished_at": _now(),
            "total_rows": total_rows,
            "created_count": len(created),
            "skipped_count": len(skipped),
            "errored_count": len(errored),
            # Case IDs kept in insert order so a mediator can walk the
            # imports table and jump to any of the 100 minted cases.
            "case_ids": [c.get("case_id") for c in created if c.get("case_id")],
            # Skipped duplicate case IDs kept too so the mediator can
            # see which existing cases the re-upload pointed at.
            "skipped_case_ids": [
                s.get("case_id") for s in skipped if s.get("case_id")
            ],
            # Store the full errored breakdown — 100 rows worst-case,
            # each a small `{row, reason}` doc, so total size stays
            # well under the 16 MB Mongo cap.
            "errored_rows": errored,
            "sample_errors": errored[:_BULK_SAMPLE_ERROR_LIMIT],
        })
        return import_id
    except Exception:  # noqa: BLE001 — logging never blocks the import
        logger.exception("bulk-csv import log failed user=%s", user_id)
        return ""


@router.post("/professional/joint-alignment/cases/bulk-csv")
async def professional_bulk_create_from_csv(
    file: UploadFile = File(..., description="CSV file with case rows."),
    default_assessment_type: Optional[str] = None,
    default_reminder_note: Optional[str] = None,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated bulk case importer for mediators / paralegals
    running a caseload. Mints up to 100 Joint Alignment cases from a
    single CSV upload.

    Behaviour:
      * The CSV must have a header row; column order is flexible.
      * Required columns: `parent1_email`, `parent2_email`.
      * Optional per-row: `parent1_name`, `parent2_name`,
        `assessment_type`, `reminder_note`, `reference`.
      * Missing per-row `assessment_type` falls back to the form's
        `default_assessment_type` field.
      * Missing per-row `reminder_note` falls back to `default_reminder_note`.
      * Rows are minted sequentially (invitation emails go out via the
        same best-effort path as the single-case endpoint).
      * A row that would duplicate an active case owned by this
        mediator (same two emails) is SILENTLY SKIPPED — never
        errored, so a mediator can safely re-upload a CSV.
      * Bad rows (invalid email, missing lane) get recorded in
        the response's `errored` array; the rest of the CSV still
        goes through.

    Response shape:
    ```
    {
      "created":   [{"row": 2, "case_id": "SA-XXXXXX", "parents": [{email, invitation_url}]}, ...],
      "skipped":   [{"row": 3, "reason": "duplicate", "case_id": "SA-YYYYYY"}, ...],
      "errored":   [{"row": 4, "reason": "..."}, ...],
      "total_rows": 20
    }
    ```
    """
    import csv
    import io

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Upload must be a .csv file.",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="CSV is empty.")
    if len(raw) > _BULK_CSV_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV is too large. Max {_BULK_CSV_MAX_BYTES // 1024} KB.",
        )

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV must be UTF-8 encoded (or plain ASCII).",
        ) from exc

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV has no rows.")

    header_row = rows[0]
    header_map = _normalise_bulk_headers(header_row)
    if "parent1_email" not in header_map or "parent2_email" not in header_map:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV must include both parent1_email and parent2_email "
                "columns."
            ),
        )

    data_rows = rows[1:]
    # Drop blank tail rows (Excel exports frequently trail with empties).
    while data_rows and all(not (c or "").strip() for c in data_rows[-1]):
        data_rows.pop()

    if len(data_rows) == 0:
        raise HTTPException(
            status_code=400,
            detail="CSV has no data rows.",
        )
    if len(data_rows) > _BULK_CSV_MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"Too many rows. Max {_BULK_CSV_MAX_ROWS} cases per upload.",
        )

    def cell(row, key: str) -> str:
        idx = header_map.get(key)
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    created: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    errored: List[Dict[str, Any]] = []

    default_lane = (default_assessment_type or "").strip() or None
    default_note = (default_reminder_note or "").strip() or None
    started_at = _now()

    for offset, row in enumerate(data_rows):
        # Row numbers are 1-indexed AND include the header row, so the
        # first data row is `row 2` in a spreadsheet.
        row_no = offset + 2
        try:
            email_a = cell(row, "parent1_email")
            email_b = cell(row, "parent2_email")
            if not email_a or not email_b:
                errored.append({
                    "row": row_no,
                    "reason": "missing parent1_email or parent2_email",
                })
                continue

            # Silent-skip duplicates BEFORE any lane / validation checks
            # so a re-uploaded CSV never surfaces spurious "missing lane"
            # errors on rows the mediator already minted.
            dup_case_id = await _bulk_duplicate_case_exists(
                db,
                user_id=current.user_id,
                email_a=email_a,
                email_b=email_b,
            )
            if dup_case_id:
                skipped.append({
                    "row": row_no,
                    "reason": "duplicate",
                    "case_id": dup_case_id,
                })
                continue

            lane = cell(row, "assessment_type") or default_lane
            if not lane:
                errored.append({
                    "row": row_no,
                    "reason": "missing assessment_type (and no default)",
                })
                continue

            try:
                request_body = ProfessionalCreateCaseRequest(
                    assessment_type=lane,
                    parents=[
                        ParentInfo(
                            email=email_a,
                            name=cell(row, "parent1_name") or None,
                        ),
                        ParentInfo(
                            email=email_b,
                            name=cell(row, "parent2_name") or None,
                        ),
                    ],
                    align_case_reference=cell(row, "reference") or None,
                    reminder_note=(cell(row, "reminder_note") or default_note),
                )
            except ValidationError as ve:
                # First validation error is enough context for a
                # human — surface the message verbatim so they can
                # fix the row without decoding pydantic dumps.
                first = ve.errors()[0] if ve.errors() else {}
                errored.append({
                    "row": row_no,
                    "reason": first.get("msg") or "invalid row",
                })
                continue

            try:
                res = await _create_and_invite_case(
                    body=request_body, current=current, db=db,
                )
            except HTTPException as he:
                errored.append({"row": row_no, "reason": he.detail})
                continue

            created.append({
                "row": row_no,
                "case_id": res.case_id,
                "assessment_type": res.assessment_type,
                "parents": [
                    {"email": p.email, "invitation_url": p.invitation_url}
                    for p in res.parents
                ],
                "email_deliveries": res.email_deliveries or [],
            })
        except Exception as exc:  # noqa: BLE001 — defensive per-row guard
            logger.exception(
                "bulk-csv row failure user=%s row=%s", current.user_id, row_no,
            )
            errored.append({"row": row_no, "reason": str(exc) or "unknown error"})

    logger.info(
        "joint-alignment bulk-csv import user=%s total=%s created=%s skipped=%s errored=%s",
        current.user_id, len(data_rows), len(created), len(skipped), len(errored),
    )
    import_id = await _record_bulk_import(
        db,
        user_id=current.user_id,
        filename=file.filename,
        default_lane=default_lane,
        default_note=default_note,
        total_rows=len(data_rows),
        created=created,
        skipped=skipped,
        errored=errored,
        variant="single",
        started_at=started_at,
    )
    return {
        "import_id": import_id or None,
        "total_rows": len(data_rows),
        "created": created,
        "skipped": skipped,
        "errored": errored,
    }


@router.post("/professional/joint-alignment/cases/bulk-csv/stream")
async def professional_bulk_create_from_csv_stream(
    file: UploadFile = File(..., description="CSV file with case rows."),
    default_assessment_type: Optional[str] = None,
    default_reminder_note: Optional[str] = None,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Streaming NDJSON variant of `bulk-csv`. Emits one JSON line per
    event so the frontend can update a live progress bar as each
    case gets minted — critical UX for 100-row imports that take
    ~60-120 seconds end-to-end.

    Event stream shape (one per line, `\\n`-delimited):
      * `{"event":"start","total_rows":N}`                    — before any row work
      * `{"event":"row","row":N,"status":"created|skipped|errored","case_id":?,"reason":?,"parents":?}`  — one per row
      * `{"event":"done","summary":{total,created,skipped,errored}}`  — final

    Fatal errors (invalid CSV / oversize / missing columns) still
    return standard HTTP 4xx BEFORE the stream begins so the client
    can surface them in an error toast without needing to parse
    NDJSON.
    """
    import csv
    import io
    import json

    from fastapi.responses import StreamingResponse

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload must be a .csv file.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="CSV is empty.")
    if len(raw) > _BULK_CSV_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV is too large. Max {_BULK_CSV_MAX_BYTES // 1024} KB.",
        )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV must be UTF-8 encoded (or plain ASCII).",
        ) from exc

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise HTTPException(status_code=400, detail="CSV has no rows.")
    header_map = _normalise_bulk_headers(rows[0])
    if "parent1_email" not in header_map or "parent2_email" not in header_map:
        raise HTTPException(
            status_code=400,
            detail="CSV must include both parent1_email and parent2_email columns.",
        )
    data_rows = rows[1:]
    while data_rows and all(not (c or "").strip() for c in data_rows[-1]):
        data_rows.pop()
    if len(data_rows) == 0:
        raise HTTPException(status_code=400, detail="CSV has no data rows.")
    if len(data_rows) > _BULK_CSV_MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"Too many rows. Max {_BULK_CSV_MAX_ROWS} cases per upload.",
        )

    def cell(row, key: str) -> str:
        idx = header_map.get(key)
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    default_lane = (default_assessment_type or "").strip() or None
    default_note = (default_reminder_note or "").strip() or None
    user_id = current.user_id

    async def _emit():
        """Async generator that yields NDJSON lines. Each `yield`
        flushes to the wire immediately (FastAPI/StreamingResponse
        wires this to Starlette's send loop with no buffering)."""
        totals = {"created": 0, "skipped": 0, "errored": 0}
        # Accumulate the raw row records too so we can persist a
        # single "bulk import" summary row for the History page
        # after the stream finishes.
        created: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        errored: List[Dict[str, Any]] = []
        started_at = _now()
        yield json.dumps({"event": "start", "total_rows": len(data_rows)}) + "\n"

        for offset, row in enumerate(data_rows):
            row_no = offset + 2
            payload: Dict[str, Any] = {"event": "row", "row": row_no}
            try:
                email_a = cell(row, "parent1_email")
                email_b = cell(row, "parent2_email")
                if not email_a or not email_b:
                    payload.update({
                        "status": "errored",
                        "reason": "missing parent1_email or parent2_email",
                    })
                    errored.append({"row": row_no, "reason": payload["reason"]})
                    totals["errored"] += 1
                    yield json.dumps(payload) + "\n"
                    continue

                dup = await _bulk_duplicate_case_exists(
                    db, user_id=user_id, email_a=email_a, email_b=email_b,
                )
                if dup:
                    payload.update({
                        "status": "skipped",
                        "reason": "duplicate",
                        "case_id": dup,
                    })
                    skipped.append({"row": row_no, "reason": "duplicate", "case_id": dup})
                    totals["skipped"] += 1
                    yield json.dumps(payload) + "\n"
                    continue

                lane = cell(row, "assessment_type") or default_lane
                if not lane:
                    payload.update({
                        "status": "errored",
                        "reason": "missing assessment_type (and no default)",
                    })
                    errored.append({"row": row_no, "reason": payload["reason"]})
                    totals["errored"] += 1
                    yield json.dumps(payload) + "\n"
                    continue

                try:
                    request_body = ProfessionalCreateCaseRequest(
                        assessment_type=lane,
                        parents=[
                            ParentInfo(email=email_a, name=cell(row, "parent1_name") or None),
                            ParentInfo(email=email_b, name=cell(row, "parent2_name") or None),
                        ],
                        align_case_reference=cell(row, "reference") or None,
                        reminder_note=(cell(row, "reminder_note") or default_note),
                    )
                except ValidationError as ve:
                    first = ve.errors()[0] if ve.errors() else {}
                    payload.update({
                        "status": "errored",
                        "reason": first.get("msg") or "invalid row",
                    })
                    errored.append({"row": row_no, "reason": payload["reason"]})
                    totals["errored"] += 1
                    yield json.dumps(payload) + "\n"
                    continue

                try:
                    res = await _create_and_invite_case(
                        body=request_body, current=current, db=db,
                    )
                except HTTPException as he:
                    payload.update({"status": "errored", "reason": he.detail})
                    errored.append({"row": row_no, "reason": he.detail})
                    totals["errored"] += 1
                    yield json.dumps(payload) + "\n"
                    continue

                payload.update({
                    "status": "created",
                    "case_id": res.case_id,
                    "assessment_type": res.assessment_type,
                    "parents": [
                        {"email": p.email, "invitation_url": p.invitation_url}
                        for p in res.parents
                    ],
                    "email_deliveries": res.email_deliveries or [],
                })
                created.append({"row": row_no, "case_id": res.case_id})
                totals["created"] += 1
                yield json.dumps(payload) + "\n"

            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "bulk-csv stream row failure user=%s row=%s", user_id, row_no,
                )
                errored.append({"row": row_no, "reason": str(exc) or "unknown error"})
                totals["errored"] += 1
                yield json.dumps({
                    "event": "row", "row": row_no,
                    "status": "errored", "reason": str(exc) or "unknown error",
                }) + "\n"

        # Persist an import-summary row so the History page can list
        # this batch later. Never blocks the client — logged best-effort.
        import_id = await _record_bulk_import(
            db,
            user_id=user_id,
            filename=file.filename,
            default_lane=default_lane,
            default_note=default_note,
            total_rows=len(data_rows),
            created=created,
            skipped=skipped,
            errored=errored,
            variant="stream",
            started_at=started_at,
        )
        yield json.dumps({
            "event": "done",
            "import_id": import_id or None,
            "summary": {"total_rows": len(data_rows), **totals},
        }) + "\n"

    return StreamingResponse(
        _emit(),
        media_type="application/x-ndjson",
        headers={
            # Disable proxy buffering so each line hits the browser as
            # it's produced (nginx / cloudfront otherwise wait for
            # ~8KB before flushing).
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/professional/joint-alignment/cases/bulk-csv/template")
async def professional_bulk_csv_template(
    current: UserPublic = Depends(get_current_user),
):
    """Download an empty CSV template the mediator can fill in with
    the correct column headers already in place. JWT-required so the
    template doesn't get scraped by anonymous crawlers."""
    from fastapi.responses import Response as FastAPIResponse
    _ = current
    header_line = (
        "parent1_email,parent1_name,parent2_email,parent2_name,"
        "assessment_type,reminder_note,reference\n"
    )
    example = (
        "sam@example.com,Sam Parent,riley@example.com,Riley Parent,"
        "communication,See you Thursday - takes about 15 minutes.,MATTER-2026-001\n"
    )
    body = header_line + example
    return FastAPIResponse(
        content=body,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="joint-alignment-bulk-template.csv"'
            ),
        },
    )


@router.get("/professional/joint-alignment/bulk/history")
async def professional_bulk_history(
    limit: int = 20,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Paginated list of the caller's past bulk-CSV imports (most
    recent first, capped at 50). Powers the `/bulk/history` page so
    a mediator can look back at last week's caseload upload and see
    which cases got created."""
    safe_limit = max(1, min(limit or 20, _BULK_HISTORY_PAGE_LIMIT))
    cursor = (
        db[_BULK_IMPORTS_COLL]
        .find({"user_id": current.user_id})
        .sort("started_at", -1)
        .limit(safe_limit)
    )
    rows: List[Dict[str, Any]] = []
    async for row in cursor:
        rows.append({
            "import_id": row.get("import_id"),
            "variant": row.get("variant") or "single",
            "filename": row.get("filename"),
            "default_assessment_type": row.get("default_assessment_type"),
            "default_reminder_note": row.get("default_reminder_note"),
            "started_at": _iso(row.get("started_at")) if row.get("started_at") else None,
            "finished_at": _iso(row.get("finished_at")) if row.get("finished_at") else None,
            "total_rows": row.get("total_rows", 0),
            "created_count": row.get("created_count", 0),
            "skipped_count": row.get("skipped_count", 0),
            "errored_count": row.get("errored_count", 0),
            "sample_errors": row.get("sample_errors") or [],
        })
    return {"imports": rows}


@router.get("/professional/joint-alignment/bulk/history/{import_id}")
async def professional_bulk_history_detail(
    import_id: str = Path(..., min_length=6, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Full detail of a single bulk import — all created case IDs,
    all skipped duplicates, all errored rows. Owner-only (404 for
    foreign imports so the existence of the import isn't leaked)."""
    row = await db[_BULK_IMPORTS_COLL].find_one(
        {"import_id": import_id, "user_id": current.user_id},
        {"_id": 0},
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Import not found, or not owned by this account.",
        )
    return {
        "import_id": row.get("import_id"),
        "variant": row.get("variant") or "single",
        "filename": row.get("filename"),
        "default_assessment_type": row.get("default_assessment_type"),
        "default_reminder_note": row.get("default_reminder_note"),
        "started_at": _iso(row.get("started_at")) if row.get("started_at") else None,
        "finished_at": _iso(row.get("finished_at")) if row.get("finished_at") else None,
        "total_rows": row.get("total_rows", 0),
        "created_count": row.get("created_count", 0),
        "skipped_count": row.get("skipped_count", 0),
        "errored_count": row.get("errored_count", 0),
        "case_ids": row.get("case_ids") or [],
        "skipped_case_ids": row.get("skipped_case_ids") or [],
        "errored_rows": row.get("errored_rows") or [],
    }


@router.get("/professional/joint-alignment/digest-pref")
async def get_digest_pref(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Read the caller's Monday-digest preference. Default is
    `opted_in=True` — every mediator is opted in the moment they
    mint their first case, matching the copy on the email itself
    ("Reply STOP to opt out"). A UI toggle simply flips this row.
    """
    row = await db["weekly_case_analytics_prefs"].find_one(
        {"user_id": current.user_id},
        {"_id": 0, "opted_in": 1, "updated_at": 1},
    ) or {}
    return {
        "opted_in": bool(row.get("opted_in", True)),
        "updated_at": _iso(row.get("updated_at")),
    }


class DigestPrefRequest(BaseModel):
    opted_in: bool


@router.post("/professional/joint-alignment/digest-pref")
async def set_digest_pref(
    body: DigestPrefRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Upsert the caller's Monday-digest preference. Idempotent:
    posting the same value twice is a no-op. Also mirrors the
    change into the `weekly_case_analytics_prefs` collection so
    the sweep loop can honour it without a routes-layer import.
    """
    now = _now()
    await db["weekly_case_analytics_prefs"].update_one(
        {"user_id": current.user_id},
        {"$set": {
            "user_id": current.user_id,
            "opted_in": bool(body.opted_in),
            "updated_at": now,
        }},
        upsert=True,
    )
    logger.info(
        "weekly-digest pref updated user=%s opted_in=%s",
        current.user_id, body.opted_in,
    )
    return {"opted_in": bool(body.opted_in), "updated_at": _iso(now)}


@router.get("/professional/joint-alignment/analytics")
async def professional_case_analytics(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Aggregate stats over every case the caller minted via the
    in-app flow — powers the analytics card on the `/mine` console.

    Returns:
      * `total_cases` — every case the caller ever created.
      * status breakdown (active / cancelled / completed).
      * `acceptance_rate` — % of invited parents who accepted their
        invitation (0..100, or None when no parents invited yet).
      * `avg_hours_to_first_accept` — mean hours from case creation
        to whichever parent accepted first. None when no case has
        had any acceptance yet.
      * `avg_hours_to_both_complete` — mean hours from case creation
        to the second-parent completion. None when no case has been
        `both_complete`.
      * `assessment_type_breakdown` — dict of lane → count.
      * `most_common_assessment_type` — the top lane by count, or
        None when no cases exist.

    Data-minimisation: only aggregate rollups — never per-case or
    per-parent detail — so a paralegal running analytics can't
    accidentally extract PHI from parents they shouldn't see.
    """
    query = {
        "$or": [
            {"professional_created_by": current.user_id},
            {"professional.id": current.user_id, "origin": "in_app_professional"},
        ]
    }
    cases = [c async for c in db[_CASES_COLL].find(query)]

    total_cases = len(cases)
    if total_cases == 0:
        return {
            "total_cases": 0,
            "active_cases": 0,
            "cancelled_cases": 0,
            "completed_cases": 0,
            "acceptance_rate": None,
            "avg_hours_to_first_accept": None,
            "avg_hours_to_both_complete": None,
            "assessment_type_breakdown": {},
            "most_common_assessment_type": None,
        }

    active_cases = sum(1 for c in cases if c.get("status") in ("pending", "in_progress"))
    cancelled_cases = sum(1 for c in cases if c.get("status") == "cancelled")
    completed_cases = sum(1 for c in cases if c.get("status") == "both_complete")

    # Acceptance rate: (accepted parents) / (invited parents).
    # Every parent doc represents an invited parent, so denominator
    # is just the total parents across every case.
    invited_parents = 0
    accepted_parents = 0
    for c in cases:
        for p in c.get("parents") or []:
            invited_parents += 1
            if p.get("accepted_at"):
                accepted_parents += 1
    acceptance_rate = (
        round(accepted_parents / invited_parents * 100, 1)
        if invited_parents > 0
        else None
    )

    # Time-to-first-accept: for each case that has any acceptance,
    # the delta from `created_at` to the EARLIEST parent's
    # `accepted_at` (in hours).
    first_accept_hours: List[float] = []
    for c in cases:
        created = _as_aware_utc(c.get("created_at"))
        if not created:
            continue
        accepts = [
            _as_aware_utc(p.get("accepted_at"))
            for p in (c.get("parents") or [])
            if p.get("accepted_at")
        ]
        accepts = [a for a in accepts if a]
        if accepts:
            first_accept_hours.append((min(accepts) - created).total_seconds() / 3600.0)
    avg_hours_to_first_accept = (
        round(sum(first_accept_hours) / len(first_accept_hours), 1)
        if first_accept_hours
        else None
    )

    # Time-to-both-complete: only cases where both parents completed
    # — delta from `created_at` to the LATER `assessment_completed_at`.
    both_complete_hours: List[float] = []
    for c in cases:
        created = _as_aware_utc(c.get("created_at"))
        if not created:
            continue
        completions = [
            _as_aware_utc(p.get("assessment_completed_at"))
            for p in (c.get("parents") or [])
            if p.get("assessment_completed_at")
        ]
        completions = [x for x in completions if x]
        if len(completions) >= 2:
            both_complete_hours.append((max(completions) - created).total_seconds() / 3600.0)
    avg_hours_to_both_complete = (
        round(sum(both_complete_hours) / len(both_complete_hours), 1)
        if both_complete_hours
        else None
    )

    # Assessment-lane breakdown.
    breakdown: Dict[str, int] = {}
    for c in cases:
        lane = (c.get("assessment_type") or "unknown")
        breakdown[lane] = breakdown.get(lane, 0) + 1
    most_common = (
        max(breakdown.items(), key=lambda kv: kv[1])[0]
        if breakdown
        else None
    )

    return {
        "total_cases": total_cases,
        "active_cases": active_cases,
        "cancelled_cases": cancelled_cases,
        "completed_cases": completed_cases,
        "acceptance_rate": acceptance_rate,
        "avg_hours_to_first_accept": avg_hours_to_first_accept,
        "avg_hours_to_both_complete": avg_hours_to_both_complete,
        "assessment_type_breakdown": breakdown,
        "most_common_assessment_type": most_common,
    }


@router.get("/professional/joint-alignment/cases-i-created")
async def list_cases_i_created(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated. Returns the cases the current user minted via
    the in-app professional flow. Never surfaces cases the caller was
    invited to as a parent — those live on `/joint-alignment/mine`
    and are shaped for a different UI. Data-minimisation guardrail:
    parent answers are never surfaced, only status + timestamps.
    """
    query = {
        "$or": [
            {"professional_created_by": current.user_id},
            {"professional.id": current.user_id, "origin": "in_app_professional"},
        ]
    }
    cursor = db[_CASES_COLL].find(query).sort("created_at", -1).limit(100)
    cases = []
    join_base = _join_base()
    async for case in cursor:
        shape = _case_public_shape(case)
        # Because the caller minted the case, they can see the raw
        # invitation URLs (until expiry). This is what makes the
        # "resend the link" copy-paste flow possible for them.
        shape["reminder_note"] = case.get("reminder_note")
        # Private internal notes — never surfaced on any parent-facing
        # payload. Only ever included in the mediator-authenticated
        # /mine listing (this cursor).
        shape["case_notes"] = case.get("case_notes")
        # Directory-invite acceptances — mediator-only. Each row logs
        # a `sacoparentsalign.com` professional who accepted a bind
        # invite for this case. Never leaked to parent-facing shapes.
        shape["directory_invite_acceptances"] = [
            {
                "invite_id": r.get("invite_id"),
                "professional_name": r.get("professional_name"),
                "professional_email": r.get("professional_email"),
                "accepted_at": _iso(r.get("accepted_at")),
            }
            for r in (case.get("directory_invite_acceptances") or [])
        ]
        shape["parents"] = [
            {
                **_parent_public_shape(p),
                "email": p.get("email"),
                "invitation_url": (
                    f"{join_base}/{p['invitation_token']}"
                    if p.get("invitation_token") and not _is_expired(p.get("token_expires_at"))
                    else None
                ),
                "token_expires_at": _iso(p.get("token_expires_at")),
            }
            for p in (case.get("parents") or [])
        ]
        cases.append(shape)
    return {"cases": cases}


@router.post(
    "/integrations/joint-alignment/cases",
    response_model=CreateCaseResponse,
)
async def integration_create_case(
    body: CreateCaseRequest,
    x_integration_key: Optional[str] = Header(default=None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Server-to-server. Align creates a Joint Alignment Case and
    receives back the SA-XXXXXX case_id plus each parent's
    invitation URL. Align is then responsible for emailing those
    URLs to the parents.
    """
    _verify_integration_key(x_integration_key)
    assessment_type = _validate_assessment_type(body.assessment_type)

    if len(body.parents) != 2:
        raise HTTPException(
            status_code=400,
            detail="A Joint Alignment Case requires exactly two parents.",
        )
    emails = {p.email.lower() for p in body.parents}
    if len(emails) != 2:
        raise HTTPException(
            status_code=400,
            detail="Parent emails must be distinct.",
        )

    case_id = await _mint_unique_case_id(db)
    now = _now()
    token_exp = now + timedelta(days=_INVITATION_TTL_DAYS)
    case_exp = now + timedelta(days=_CASE_TTL_DAYS)

    parent_docs = []
    parent_response_rows: List[CreateCaseParentResponse] = []
    join_base = _join_base()
    for idx, parent in enumerate(body.parents):
        token = _mint_invitation_token()
        parent_docs.append(
            {
                "parent_slot": "A" if idx == 0 else "B",
                "email": parent.email.lower(),
                "name": parent.name,
                "invitation_token": token,
                "token_expires_at": token_exp,
                "accepted_at": None,
                "user_id": None,
                "assessment_completed_at": None,
                "assessment_ref": None,
            }
        )
        parent_response_rows.append(
            CreateCaseParentResponse(
                email=parent.email,
                invitation_url=f"{join_base}/{token}",
                token_expires_at=_iso(token_exp),
            )
        )

    case_doc = {
        "case_id": case_id,
        "assessment_type": assessment_type,
        "professional": body.professional.model_dump(),
        "align_case_reference": body.align_case_reference,
        "parents": parent_docs,
        "status": "pending",
        "created_at": now,
        "case_expires_at": case_exp,
    }
    await db[_CASES_COLL].insert_one(case_doc)
    logger.info(
        "joint-alignment case created case_id=%s assessment=%s",
        case_id,
        assessment_type,
    )
    return CreateCaseResponse(
        case_id=case_id,
        status="pending",
        assessment_type=assessment_type,
        created_at=_iso(now),
        case_expires_at=_iso(case_exp),
        parents=parent_response_rows,
    )


@router.get("/integrations/joint-alignment/cases/{case_id}")
async def integration_get_case(
    case_id: str = Path(..., min_length=1, max_length=20),
    x_integration_key: Optional[str] = Header(default=None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _verify_integration_key(x_integration_key)
    canonical = _normalise_case_id(case_id) or case_id
    case = await db[_CASES_COLL].find_one({"case_id": canonical})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    payload: Dict[str, Any] = _case_public_shape(case)
    payload["parents"] = [
        {
            **_parent_public_shape(p),
            # Align needs the email for reporting; parents never see this shape.
            "email": p.get("email"),
        }
        for p in (case.get("parents") or [])
    ]

    # When both parents have completed, include the data-minimised
    # assessment bundles.
    if payload["status"] == "both_complete":
        assessments = []
        for p in case.get("parents") or []:
            if p.get("user_id"):
                bundle = await _minimised_assessment_payload(
                    db, case["assessment_type"], p["user_id"]
                )
                assessments.append(
                    {
                        "email": p.get("email"),
                        "parent_slot": p.get("parent_slot"),
                        "assessment": bundle,
                        "assessment_completed_at": _iso(
                            p.get("assessment_completed_at")
                        ),
                    }
                )
        payload["assessments"] = assessments
        payload["schema_version"] = 1

    return payload


# =========================== parent-facing endpoints =========================== #

@router.get("/joint-alignment/invitation/{token}")
async def get_invitation_preview(
    token: str = Path(..., min_length=8, max_length=128),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    No auth required. Returns the minimal preview shown on the
    /join/:token landing page BEFORE the parent signs in. Never
    reveals the co-parent's email, the professional's email, or any
    assessment content. Deliberately does NOT reveal whether the
    token exists at all — returns 404 on bad token so an attacker
    can't enumerate valid tokens.
    """
    case = await db[_CASES_COLL].find_one({"parents.invitation_token": token})
    if not case:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    parent = next(
        (p for p in case.get("parents") or [] if p.get("invitation_token") == token),
        None,
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    expires_at: Optional[datetime] = parent.get("token_expires_at")
    if _is_expired(expires_at):
        raise HTTPException(status_code=410, detail="Invitation expired")

    return {
        "case_id": case["case_id"],
        "assessment_type": case["assessment_type"],
        "professional_name": (case.get("professional") or {}).get("name"),
        "token_expires_at": _iso(expires_at),
        "already_accepted": bool(parent.get("accepted_at")),
        "assessment_completed": bool(parent.get("assessment_completed_at")),
    }


@router.post("/joint-alignment/invitation/{token}/accept")
async def accept_invitation(
    token: str = Path(..., min_length=8, max_length=128),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT required. Associates the invitation with the authenticated
    parent's account. Guardrail: the authenticated user's email must
    match the invitation email — this is the mechanism that stops
    the wrong person from claiming a stray token.
    """
    case = await db[_CASES_COLL].find_one({"parents.invitation_token": token})
    if not case:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    parent = next(
        (p for p in case.get("parents") or [] if p.get("invitation_token") == token),
        None,
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")

    expires_at: Optional[datetime] = parent.get("token_expires_at")
    if _is_expired(expires_at):
        raise HTTPException(status_code=410, detail="Invitation expired")

    if parent.get("email", "").lower() != (current.email or "").lower():
        # Explicitly a different HTTP code from "expired" so the
        # frontend can distinguish "wrong account" from "please try
        # again with a fresh token".
        raise HTTPException(
            status_code=403,
            detail="This invitation was sent to a different email address.",
        )

    if parent.get("user_id") and parent["user_id"] != current.user_id:
        raise HTTPException(
            status_code=409,
            detail="This invitation is already linked to another SA CoParents account.",
        )

    await db[_CASES_COLL].update_one(
        {"case_id": case["case_id"], "parents.invitation_token": token},
        {
            "$set": {
                "parents.$.accepted_at": _now(),
                "parents.$.user_id": current.user_id,
            }
        },
    )
    logger.info(
        "joint-alignment invitation accepted case_id=%s user=%s",
        case["case_id"],
        current.user_id,
    )

    fresh = await db[_CASES_COLL].find_one({"case_id": case["case_id"]})
    return _case_public_shape(fresh)


@router.post("/joint-alignment/manual-code")
async def manual_code(
    body: ManualCodeRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT required. Alternate entry for parents who only have the
    visible `SA-XXXXXX` case_id and don't have the emailed link. The
    email-match guardrail is identical to the accept-token flow —
    typing the case_id alone is never enough.
    """
    canonical = _normalise_case_id(body.code)
    if not canonical:
        raise HTTPException(status_code=404, detail="Case not found or expired")

    case = await db[_CASES_COLL].find_one({"case_id": canonical})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or expired")

    parent = next(
        (
            p
            for p in case.get("parents") or []
            if (p.get("email") or "").lower() == (current.email or "").lower()
        ),
        None,
    )
    if not parent:
        raise HTTPException(
            status_code=403,
            detail="This Alignment Code was not issued for your email address.",
        )

    if parent.get("user_id") and parent["user_id"] != current.user_id:
        raise HTTPException(
            status_code=409,
            detail="This invitation is already linked to another SA CoParents account.",
        )

    await db[_CASES_COLL].update_one(
        {"case_id": case["case_id"], "parents.email": parent["email"]},
        {
            "$set": {
                "parents.$.accepted_at": parent.get("accepted_at") or _now(),
                "parents.$.user_id": current.user_id,
            }
        },
    )
    fresh = await db[_CASES_COLL].find_one({"case_id": case["case_id"]})
    return _case_public_shape(fresh)


@router.get("/joint-alignment/mine")
async def list_my_cases(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT required. Powers the Dashboard "Joint Alignment Requests"
    section. Returns cases where the authenticated parent's email or
    user_id appears — but never the co-parent's answers.
    """
    query = {
        "$or": [
            {"parents.email": (current.email or "").lower()},
            {"parents.user_id": current.user_id},
        ]
    }
    cursor = db[_CASES_COLL].find(query).sort("created_at", -1).limit(50)
    cases = []
    async for case in cursor:
        shape = _case_public_shape(case)
        parents = case.get("parents") or []
        me = next(
            (
                p
                for p in parents
                if (p.get("email") or "").lower() == (current.email or "").lower()
                or p.get("user_id") == current.user_id
            ),
            None,
        )
        coparent = next(
            (
                p
                for p in parents
                if not (
                    (p.get("email") or "").lower() == (current.email or "").lower()
                    or p.get("user_id") == current.user_id
                )
            ),
            None,
        )
        if me:
            shape["my_status"] = (
                "completed"
                if me.get("assessment_completed_at")
                else "in_progress"
                if me.get("accepted_at")
                else "invited"
            )
        # Surface co-parent milestone timestamps (not their answers) so
        # the App can render a "your co-parent finished — your turn"
        # toast without exposing anything the co-parent typed.
        if coparent:
            shape["coparent"] = {
                "name": coparent.get("name"),
                "completed_at": _iso(coparent.get("assessment_completed_at")),
            }
        cases.append(shape)
    return {"cases": cases}


# =========================== completion + webhook =========================== #

def _webhook_signature(body_bytes: bytes) -> str:
    """
    HMAC-SHA256 of the outgoing webhook body, using the same shared
    secret Align already knows. Align verifies this on their inbound
    endpoint so a spoofed webhook can't mark a case complete.
    """
    secret = _shared_secret() or ""
    return hmac.new(
        secret.encode("utf-8"), body_bytes, hashlib.sha256
    ).hexdigest()


async def _notify_align_completion(payload: Dict[str, Any]) -> None:
    """
    Best-effort POST to Align's inbound completion webhook. Never
    raises — assessment completion in the App must not fail because
    a downstream partner is unreachable. Retry / durable delivery
    lives in Phase C+ once we have a real URL to wire.
    """
    url = os.environ.get("ALIGN_COMPLETION_WEBHOOK_URL")
    if not url:
        logger.info(
            "align completion webhook skipped (no ALIGN_COMPLETION_WEBHOOK_URL); payload=%s",
            payload,
        )
        return
    body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = _webhook_signature(body_bytes)
    try:
        async with httpx.AsyncClient(timeout=8.0) as http:
            r = await http.post(
                url,
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Integration-Signature": signature,
                },
            )
            logger.info(
                "align completion webhook posted case=%s status=%s",
                payload.get("case_id"),
                r.status_code,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("align completion webhook failed: %s", exc)


async def mark_assessment_completed(
    db: AsyncIOMotorDatabase,
    user_id: str,
    assessment_type: str,
    assessment_ref: Optional[str] = None,
) -> List[str]:
    """
    Public helper called from anywhere an assessment finalises
    (deep-dive report generation, SNC v2 completion, etc.). Marks
    the authenticated parent's slot as `assessment_completed` on
    every open case that matches the assessment_type, and fires the
    outbound webhook to Align for each. Idempotent — a second call
    for the same user + type will still mark the case as completed
    with an updated timestamp, but Align's webhook receiver should
    treat repeated notifications as a no-op.

    Returns the list of case_ids that were updated (useful for logs
    and for the frontend "your case advanced" nudge).
    """
    if assessment_type not in _ASSESSMENT_TYPES:
        return []
    now = _now()
    updated: List[str] = []
    async for case in db[_CASES_COLL].find(
        {
            "assessment_type": assessment_type,
            "status": {"$nin": ["expired", "cancelled"]},
            # $elemMatch so BOTH conditions apply to the same parent
            # slot — otherwise the query matches docs where user A's
            # slot is completed and user B's slot is not, and the
            # `parents.$` update targets the wrong slot.
            "parents": {
                "$elemMatch": {
                    "user_id": user_id,
                    "assessment_completed_at": None,
                }
            },
        }
    ):
        result = await db[_CASES_COLL].update_one(
            {
                "_id": case["_id"],
                "parents": {
                    "$elemMatch": {
                        "user_id": user_id,
                        "assessment_completed_at": None,
                    }
                },
            },
            {
                "$set": {
                    "parents.$.assessment_completed_at": now,
                    "parents.$.assessment_ref": assessment_ref,
                }
            },
        )
        if result.modified_count == 0:
            continue
        updated.append(case["case_id"])

        # Compute the fresh status and, if both are done, flip the
        # top-level status too so pollers see it without recomputing.
        fresh = await db[_CASES_COLL].find_one({"_id": case["_id"]})
        parents = (fresh or {}).get("parents") or []
        both_done = all(p.get("assessment_completed_at") for p in parents) and parents
        if both_done and fresh.get("status") not in ("cancelled", "expired"):
            await db[_CASES_COLL].update_one(
                {"_id": case["_id"]},
                {"$set": {"status": "both_complete"}},
            )

        await _notify_align_completion(
            {
                "event": "assessment_completed",
                "case_id": case["case_id"],
                "assessment_type": assessment_type,
                "parent": {
                    "email": next(
                        (
                            p.get("email")
                            for p in parents
                            if p.get("user_id") == user_id
                        ),
                        None,
                    ),
                    "slot": next(
                        (
                            p.get("parent_slot")
                            for p in parents
                            if p.get("user_id") == user_id
                        ),
                        None,
                    ),
                },
                "both_complete": bool(both_done),
                "completed_at": _iso(now),
            }
        )
    if updated:
        logger.info(
            "assessment completion propagated user=%s type=%s cases=%s",
            user_id,
            assessment_type,
            updated,
        )
    return updated


# =========================== cancellation endpoint =========================== #

class CancelCaseRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=280)


class ReminderNoteRequest(BaseModel):
    reminder_note: Optional[str] = Field(default=None, max_length=240)


@router.patch("/professional/joint-alignment/cases/{case_id}/reminder-note")
async def professional_update_reminder_note(
    body: ReminderNoteRequest,
    case_id: str = Path(..., min_length=1, max_length=20),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated, owner-only. Update (or clear with `null`)
    the mediator's one-line personal note that gets injected into
    the 5-day invitation-reminder email. Idempotent — same value
    posted twice is a no-op.
    """
    canonical = _normalise_case_id(case_id) or case_id
    normalized = (body.reminder_note or "").strip() or None
    result = await db[_CASES_COLL].update_one(
        {
            "case_id": canonical,
            "$or": [
                {"professional_created_by": current.user_id},
                {"professional.id": current.user_id, "origin": "in_app_professional"},
            ],
        },
        {"$set": {"reminder_note": normalized}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Case not found, or not owned by this account.",
        )
    return {"case_id": canonical, "reminder_note": normalized}


# =========================== reminder-note templates =========================== #
# Mediators repeat the same reminder-note copy across cases — "See you
# Thursday · takes about 15 minutes" for the intake pattern, "One more
# nudge, promise it's the last one" for follow-ups. Saved templates
# eliminate the retype.

_REMINDER_TEMPLATES_COLL = "reminder_note_templates"
_REMINDER_TEMPLATES_MAX_PER_USER = 12


class ReminderTemplateCreate(BaseModel):
    """Body for `POST /api/professional/reminder-note-templates`."""
    label: str = Field(..., min_length=1, max_length=60)
    body: str = Field(..., min_length=1, max_length=240)


@router.get("/professional/reminder-note-templates")
async def list_reminder_note_templates(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List the caller's saved reminder-note templates, alphabetised
    by label. Capped at 12 rows per mediator."""
    cursor = (
        db[_REMINDER_TEMPLATES_COLL]
        .find({"user_id": current.user_id}, {"_id": 0, "user_id": 0})
        .sort("label", 1)
    )
    templates: List[Dict[str, Any]] = []
    async for row in cursor:
        templates.append({
            "template_id": row.get("template_id"),
            "label": row.get("label"),
            "body": row.get("body"),
            "created_at": _iso(row.get("created_at")),
        })
    return {"templates": templates}


@router.post("/professional/reminder-note-templates")
async def create_reminder_note_template(
    body: ReminderTemplateCreate,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Save a reusable reminder-note template. Duplicate labels are
    rejected (409) so the picker UI doesn't show two identical
    entries. Hard cap of 12 templates per mediator."""
    label = body.label.strip()
    text = body.body.strip()
    if not label or not text:
        raise HTTPException(
            status_code=400,
            detail="Both `label` and `body` are required.",
        )

    count = await db[_REMINDER_TEMPLATES_COLL].count_documents(
        {"user_id": current.user_id},
    )
    if count >= _REMINDER_TEMPLATES_MAX_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have {_REMINDER_TEMPLATES_MAX_PER_USER} "
                "reminder-note templates saved. Delete one to add another."
            ),
        )

    dup = await db[_REMINDER_TEMPLATES_COLL].find_one(
        {"user_id": current.user_id, "label": label},
        {"_id": 1},
    )
    if dup:
        raise HTTPException(
            status_code=409,
            detail=f"A template with label “{label}” already exists.",
        )

    template_id = uuid.uuid4().hex[:12]
    now = _now()
    await db[_REMINDER_TEMPLATES_COLL].insert_one({
        "template_id": template_id,
        "user_id": current.user_id,
        "label": label,
        "body": text,
        "created_at": now,
    })
    return {
        "template_id": template_id,
        "label": label,
        "body": text,
        "created_at": _iso(now),
    }


@router.delete("/professional/reminder-note-templates/{template_id}")
async def delete_reminder_note_template(
    template_id: str = Path(..., min_length=1, max_length=64),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete a template owned by the caller. Foreign template_ids
    return 404 (never leak whether an id ever existed)."""
    result = await db[_REMINDER_TEMPLATES_COLL].delete_one({
        "template_id": template_id,
        "user_id": current.user_id,
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found.")
    return {"template_id": template_id, "deleted": True}


@router.get("/professional/joint-alignment/cases/{case_id}/reminder-preview")
async def professional_reminder_preview(
    case_id: str = Path(..., min_length=1, max_length=20),
    parent_index: int = 0,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Render the 5-day gentle-nudge email exactly as the parent will
    receive it, WITHOUT sending anything. Owner-only, JWT required.

    Powers the "Preview" pill next to the reminder-note field on the
    mediator's `/mine` console so they can sanity-check the exact
    wording their personal note lands in — including the mediator's
    display name, assessment lane, case ID and one-tap invitation URL.

    Query params:
      * `parent_index` (0 or 1) — pick which parent's copy to render.
        Defaults to 0 (first invited parent). If the requested parent
        has already accepted, we still render the email so the
        mediator can see "what the reminder would say" for QA.

    Never dispatches to Resend. Never records a PHI-access log
    (it's a pure UI-side preview against the mediator's own case).
    """
    from email_service import render_joint_alignment_invitation_reminder

    canonical = _normalise_case_id(case_id) or case_id
    case = await db[_CASES_COLL].find_one(
        {
            "case_id": canonical,
            "$or": [
                {"professional_created_by": current.user_id},
                {"professional.id": current.user_id, "origin": "in_app_professional"},
            ],
        },
        {"_id": 0},
    )
    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found, or not owned by this account.",
        )
    parents = case.get("parents") or []
    if not parents:
        raise HTTPException(
            status_code=409,
            detail="This case has no invited parents on record.",
        )
    if parent_index < 0 or parent_index >= len(parents):
        raise HTTPException(
            status_code=400,
            detail=f"parent_index must be 0…{len(parents) - 1} for this case.",
        )
    parent = parents[parent_index]
    professional = case.get("professional") or {}
    professional_name = (
        professional.get("name")
        or professional.get("email")
        or None
    )
    rendered = render_joint_alignment_invitation_reminder(
        invitation_url=parent.get("invitation_url") or "",
        case_id=canonical,
        professional_name=professional_name,
        parent_name=parent.get("name") or None,
        assessment_type=case.get("assessment_type") or None,
        reminder_note=case.get("reminder_note") or None,
    )
    return {
        "case_id": canonical,
        "parent_index": parent_index,
        "parent_email": parent.get("email"),
        "parent_name": parent.get("name") or None,
        "parent_accepted": bool(parent.get("accepted_at")),
        "has_reminder_note": bool((case.get("reminder_note") or "").strip()),
        "subject": rendered["subject"],
        "html": rendered["html"],
        "text": rendered["text"],
    }


# Rate limit: keep test-send friendly for QA but not a spam vector.
_REMINDER_TEST_SEND_HOURLY_LIMIT = int(
    os.environ.get("REMINDER_TEST_SEND_HOURLY_LIMIT", "10")
)


@router.post("/professional/joint-alignment/cases/{case_id}/reminder-preview/send-test")
async def professional_reminder_send_test(
    case_id: str = Path(..., min_length=1, max_length=20),
    parent_index: int = 0,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send the rendered reminder email to the MEDIATOR'S OWN inbox
    so they can see what it looks like in their real mail client
    (spam filtering, mobile Gmail rendering, dark-mode inversion,
    etc.) BEFORE the 5-day sweep dispatches to the parent.

    Never touches the parent's inbox. Never counts against the
    parent's rate limits. Owner-only, JWT required.

    Rate-limited to 10 test-sends / hour per mediator to keep this
    from becoming an accidental spam vector.
    """
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        render_joint_alignment_invitation_reminder,
        _send,  # low-level dispatcher — bypasses the parent-facing send helper.
    )

    canonical = _normalise_case_id(case_id) or case_id
    case = await db[_CASES_COLL].find_one(
        {
            "case_id": canonical,
            "$or": [
                {"professional_created_by": current.user_id},
                {"professional.id": current.user_id, "origin": "in_app_professional"},
            ],
        },
        {"_id": 0},
    )
    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found, or not owned by this account.",
        )
    mediator_email = (current.email or "").strip().lower()
    if not mediator_email:
        raise HTTPException(
            status_code=400,
            detail="Your account has no email on file — can't send a test.",
        )

    # Simple per-mediator hourly rate limit backed by a lightweight
    # counter collection. Keeps this endpoint from becoming spam.
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    recent = await db.reminder_preview_test_sends.count_documents({
        "user_id": current.user_id,
        "sent_at": {"$gte": window_start},
    })
    if recent >= _REMINDER_TEST_SEND_HOURLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Test-send limit reached — {_REMINDER_TEST_SEND_HOURLY_LIMIT} per hour. "
                "Try again shortly."
            ),
        )

    parents = case.get("parents") or []
    if not parents:
        raise HTTPException(
            status_code=409,
            detail="This case has no invited parents on record.",
        )
    if parent_index < 0 or parent_index >= len(parents):
        raise HTTPException(
            status_code=400,
            detail=f"parent_index must be 0…{len(parents) - 1} for this case.",
        )
    parent = parents[parent_index]
    professional = case.get("professional") or {}
    professional_name = professional.get("name") or professional.get("email") or None

    rendered = render_joint_alignment_invitation_reminder(
        invitation_url=parent.get("invitation_url") or "",
        case_id=canonical,
        professional_name=professional_name,
        parent_name=parent.get("name") or None,
        assessment_type=case.get("assessment_type") or None,
        reminder_note=case.get("reminder_note") or None,
    )
    # Re-brand the subject so the mediator can spot the test in
    # their inbox (and never mistakes it for a live send).
    test_subject = f"[TEST PREVIEW] {rendered['subject']}"

    try:
        _send(
            to_email=mediator_email,
            subject=test_subject,
            html=rendered["html"],
            text=(
                "This is a TEST preview — the real recipient did NOT receive "
                "this email. It's here so you can QA the rendering in your "
                "actual mail client.\n\n"
                + rendered["text"]
            ),
            failure_message="Couldn't send the test right now.",
        )
    except EmailNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="Email isn't configured on this environment yet.",
        ) from exc
    except EmailSendError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc) or "Could not send the test right now.",
        ) from exc

    # Audit row for the rate limit + support forensics.
    await db.reminder_preview_test_sends.insert_one({
        "user_id": current.user_id,
        "case_id": canonical,
        "parent_index": parent_index,
        "mediator_email": mediator_email,
        "sent_at": now,
    })
    return {
        "ok": True,
        "delivered_to": mediator_email,
        "remaining_this_hour": max(
            0, _REMINDER_TEST_SEND_HOURLY_LIMIT - recent - 1,
        ),
    }


class CaseNotesRequest(BaseModel):
    case_notes: Optional[str] = Field(default=None, max_length=2000)


@router.patch("/professional/joint-alignment/cases/{case_id}/case-notes")
async def professional_update_case_notes(
    body: CaseNotesRequest,
    case_id: str = Path(..., min_length=1, max_length=20),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated, owner-only. Update (or clear with `null`) the
    mediator's PRIVATE internal notes about this case.

    Distinct from `reminder_note`:
      * `reminder_note` (240 chars, parent-visible)  → gets injected
        into the 5-day nudge email a parent receives.
      * `case_notes`   (2000 chars, private)         → mediator-only,
        never surfaced in ANY parent-facing payload (invitation
        emails, nudge emails, joint report). Meant for internal
        session context ("Alex wants short pickup windows", "Case
        moving to court in April", etc.).

    Idempotent — same value posted twice is a no-op.
    """
    canonical = _normalise_case_id(case_id) or case_id
    normalized = (body.case_notes or "").strip() or None
    result = await db[_CASES_COLL].update_one(
        {
            "case_id": canonical,
            "$or": [
                {"professional_created_by": current.user_id},
                {"professional.id": current.user_id, "origin": "in_app_professional"},
            ],
        },
        {"$set": {"case_notes": normalized}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Case not found, or not owned by this account.",
        )
    return {"case_id": canonical, "case_notes": normalized}


@router.get("/professional/joint-alignment/cases/{case_id}/status-report.pdf")
async def professional_case_status_pdf(
    case_id: str = Path(..., min_length=1, max_length=20),
    firm: Optional[str] = None,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated, owner-only PDF download from the /mine
    console. Returns a small case-status PDF watermarked with the
    professional's firm name (query param `?firm=...`) and the
    UTC download timestamp on every page — so a downstream
    recipient can trace which copy they received.

    Falls back to the caller's account name if `firm` is omitted.
    """
    canonical = _normalise_case_id(case_id) or case_id
    case = await db[_CASES_COLL].find_one({
        "case_id": canonical,
        "$or": [
            {"professional_created_by": current.user_id},
            {"professional.id": current.user_id, "origin": "in_app_professional"},
        ],
    })
    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found, or not owned by this account.",
        )

    watermark = (firm or current.name or current.email or "").strip() or None

    from case_status_pdf import build_case_status_pdf
    pdf_bytes = build_case_status_pdf(case, watermark_firm_name=watermark)

    filename = f"{canonical}-status-report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/professional/joint-alignment/cases/{case_id}/cancel")
async def professional_cancel_case(
    body: CancelCaseRequest,
    case_id: str = Path(..., min_length=1, max_length=20),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    JWT-authenticated variant of `integration_cancel_case`. Only the
    caller who minted the case can cancel it — never another
    professional. Cancels the case, expires every unclaimed
    invitation on it, records the cancellation reason. Idempotent
    404 on a second cancel.
    """
    canonical = _normalise_case_id(case_id) or case_id
    now = _now()
    result = await db[_CASES_COLL].update_one(
        {
            "case_id": canonical,
            "status": {"$nin": ["cancelled", "expired"]},
            "$or": [
                {"professional_created_by": current.user_id},
                {"professional.id": current.user_id, "origin": "in_app_professional"},
            ],
        },
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "cancelled_reason": body.reason,
                "cancelled_by_user_id": current.user_id,
                "parents.$[unclaimed].token_expires_at": now,
            }
        },
        array_filters=[{"unclaimed.accepted_at": None}],
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Case not found, already cancelled, or not owned by this account.",
        )
    logger.info(
        "in-app professional cancel case_id=%s user=%s reason=%s",
        canonical, current.user_id, body.reason,
    )
    fresh = await db[_CASES_COLL].find_one({"case_id": canonical})
    return _case_public_shape(fresh)


@router.post("/integrations/joint-alignment/cases/{case_id}/cancel")
async def integration_cancel_case(
    body: CancelCaseRequest,
    case_id: str = Path(..., min_length=1, max_length=20),
    x_integration_key: Optional[str] = Header(default=None, alias="X-Integration-Key"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Server-to-server. Align cancels a case (professional retracted
    it, wrong parents, dispute settled outside the process, etc.).
    Marks the case `cancelled` and expires every unclaimed
    invitation on it. A cancelled case never advances again.
    """
    _verify_integration_key(x_integration_key)
    canonical = _normalise_case_id(case_id) or case_id
    now = _now()
    result = await db[_CASES_COLL].update_one(
        {"case_id": canonical, "status": {"$nin": ["cancelled", "expired"]}},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "cancelled_reason": body.reason,
                "parents.$[unclaimed].token_expires_at": now,
            }
        },
        array_filters=[{"unclaimed.accepted_at": None}],
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found or already cancelled")
    logger.info("joint-alignment case cancelled case_id=%s reason=%s", canonical, body.reason)
    fresh = await db[_CASES_COLL].find_one({"case_id": canonical})
    return _case_public_shape(fresh)



# ============ Professional directory (sacoparentsalign.com) ============
# Directory-backed invitations. A mediator on `/mine` picks a
# professional from the sibling-site directory and dispatches an
# invitation email. The recipient lands on `sacoparentsalign.com/join`
# to accept — no SA CoParents login required, because the sibling
# site owns the professional's account. See
# `/app/memory/INTEGRATION_TODO_sacoparentsalign.md` for the future
# API contract; today the directory is served from a hardcoded roster.

_DIRECTORY_INVITE_HOURLY_LIMIT = int(
    os.environ.get("PROFESSIONAL_DIRECTORY_INVITE_HOURLY_LIMIT", "20")
)


@router.get("/professional/directory")
async def get_professional_directory(
    q: Optional[str] = None,
    specialty: Optional[str] = None,
    current: UserPublic = Depends(get_current_user),
):
    """List professionals from the sacoparentsalign.com directory.
    JWT-required — the directory is a paid partner list, not public
    marketing.

    Query params:
      * `q` — free-text substring (matches name, title, city,
        specialties).
      * `specialty` — exact specialty tag.
    """
    from professional_directory import list_directory
    _ = current  # auth guard only
    return {
        "professionals": await list_directory(query=q, specialty=specialty),
    }


class DirectoryInviteBody(BaseModel):
    """Body for `POST /professional/directory/invite`."""
    professional_id: str = Field(..., min_length=1, max_length=40)
    case_id: Optional[str] = Field(default=None, max_length=20)
    personal_note: Optional[str] = Field(default=None, max_length=500)


@router.post("/professional/directory/invite")
async def invite_professional_from_directory(
    body: DirectoryInviteBody,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """A mediator picks a professional from the sacoparentsalign.com
    directory and asks us to email them an invitation to co-manage a
    case. The email points at
    `sacoparentsalign.com/join?case={case_id}&token=...` so the
    sibling site handles onboarding — nothing to do on our side
    beyond dispatching the email and logging the audit row.

    Guardrails:
      * Rate-limited to 20 invitations per hour per mediator.
      * A duplicate invitation to the same (mediator, professional)
        pair within 24 hours 409s.
      * When `case_id` is supplied it must belong to the calling
        mediator — foreign cases 404.
    """
    from professional_directory import (
        align_join_url_for,
        count_recent_invitations_to,
        get_professional,
        record_invitation,
    )
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        send_professional_directory_invitation,
    )

    professional = await get_professional(body.professional_id)
    if not professional:
        raise HTTPException(
            status_code=404,
            detail="Professional not found in the directory.",
        )
    to_email = (professional.get("contact_email") or "").strip().lower()
    if not to_email:
        raise HTTPException(
            status_code=409,
            detail="This professional has no contact email on file yet.",
        )

    # Optional: bind to a case the mediator owns.
    case_id: Optional[str] = None
    if body.case_id and body.case_id.strip():
        case_id = _normalise_case_id(body.case_id) or body.case_id.strip()
        owned = await db[_CASES_COLL].find_one(
            {
                "case_id": case_id,
                "$or": [
                    {"professional_created_by": current.user_id},
                    {"professional.id": current.user_id, "origin": "in_app_professional"},
                ],
            },
            {"_id": 0, "case_id": 1},
        )
        if not owned:
            raise HTTPException(
                status_code=404,
                detail="Case not found, or not owned by this account.",
            )

    # Hourly rate limit — belt to the per-pair 24h duplicate check.
    now = _now()
    hour_ago = now - timedelta(hours=1)
    recent_hour = await db.professional_directory_invites.count_documents({
        "inviter_user_id": current.user_id,
        "created_at": {"$gte": hour_ago},
    })
    if recent_hour >= _DIRECTORY_INVITE_HOURLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've hit the {_DIRECTORY_INVITE_HOURLY_LIMIT}/hour "
                "invite limit. Try again shortly."
            ),
        )

    # Duplicate guard — same mediator + same pro within 24h is a
    # fat-finger, not a real second invitation.
    dup = await count_recent_invitations_to(
        db,
        inviter_user_id=current.user_id,
        professional_id=body.professional_id,
        within_hours=24,
    )
    if dup > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "You've already invited this professional in the last 24 hours. "
                "Give them a moment to respond before re-sending."
            ),
        )

    # Mint a short opaque join token — the sibling site validates it
    # when the professional lands on /join. We don't need to sign it
    # heavily today because the sibling side owns the accept flow;
    # `secrets.token_urlsafe` is plenty of entropy.
    invite_token = secrets.token_urlsafe(24)
    invite_id = uuid.uuid4().hex[:12]
    join_url = align_join_url_for(case_id=case_id, token=invite_token)

    try:
        send_professional_directory_invitation(
            to_email=to_email,
            professional_name=professional.get("name") or "",
            inviter_name=current.name or "",
            inviter_email=current.email or "",
            case_id=case_id,
            personal_note=body.personal_note,
            join_url=join_url,
        )
    except EmailNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="Email isn't configured on this environment yet.",
        ) from exc
    except EmailSendError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc) or "Could not send the invitation right now.",
        ) from exc

    await record_invitation(
        db,
        inviter_user_id=current.user_id,
        inviter_name=current.name,
        inviter_email=current.email,
        case_id=case_id,
        professional=professional,
        personal_note=body.personal_note,
        join_url=join_url,
        invite_id=invite_id,
        invite_token=invite_token,
    )

    return {
        "ok": True,
        "invite_id": invite_id,
        "delivered_to": to_email,
        "join_url": join_url,
        "case_id": case_id,
        "remaining_this_hour": max(
            0, _DIRECTORY_INVITE_HOURLY_LIMIT - recent_hour - 1,
        ),
    }



# ---------------------------------------------------------------------
# sacoparentsalign.com → SA CoParents accept webhook.
# When a professional accepts an invitation on the sibling site, that
# site calls us back on this endpoint so we can:
#   * flip the invite row to status=accepted (idempotent),
#   * if the invite was case-bound, append a `case_events` audit row
#     to the case doc so mediators see the acceptance on `/mine`.
# ---------------------------------------------------------------------

class AcceptWebhookBody(BaseModel):
    """Payload from sacoparentsalign.com when a pro accepts an invite."""
    token: str = Field(..., min_length=1, max_length=200)
    accepted_at: Optional[str] = Field(default=None, max_length=64)  # ISO-8601
    professional_id: Optional[str] = Field(default=None, max_length=80)
    professional_name: Optional[str] = Field(default=None, max_length=200)
    professional_email: Optional[str] = Field(default=None, max_length=200)


@router.post("/professional/directory/invite/accept-webhook")
async def professional_directory_invite_accept_webhook(
    request: Request,
    x_sacoparentsalign_signature: Optional[str] = Header(
        default=None, alias="X-Sacoparentsalign-Signature",
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Called by sacoparentsalign.com when a professional accepts an
    invitation dispatched via `/professional/directory/invite`.

    Auth: HMAC-SHA256 signature of the RAW request body, keyed by
    `SACOPARENTSALIGN_WEBHOOK_SECRET`, in header
    `X-Sacoparentsalign-Signature` (with or without `sha256=` prefix).

    Body shape:
      { token: str,                # invite_token minted at invite time
        accepted_at: str?,         # ISO-8601 UTC; server-time fallback
        professional_id: str?,     # sibling's canonical id (may differ)
        professional_name: str?,
        professional_email: str? }

    Responses:
      * 200 `{ok: true, status, case_id?, applied: bool}` — applied
        the flip (or the invite was already accepted → applied=false,
        idempotent).
      * 401 — bad or missing signature.
      * 404 — unknown token (never leak whether a token was ever valid).
      * 503 — server-side `SACOPARENTSALIGN_WEBHOOK_SECRET` not set.
    """
    from professional_directory import (
        webhook_secret,
        verify_webhook_signature,
        find_invite_by_token,
        mark_invite_accepted,
    )

    if not webhook_secret():
        raise HTTPException(
            status_code=503,
            detail="Accept webhook is not configured on this environment.",
        )

    raw = await request.body()
    if not verify_webhook_signature(
        raw_body=raw, signature_header=x_sacoparentsalign_signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature.")

    try:
        parsed = AcceptWebhookBody.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    invite = await find_invite_by_token(db, invite_token=parsed.token)
    if not invite:
        raise HTTPException(status_code=404, detail="Unknown invite token.")

    accepted_at: datetime
    if parsed.accepted_at:
        parsed_ts = _as_aware_utc(parsed.accepted_at)
        accepted_at = parsed_ts or _now()
    else:
        accepted_at = _now()

    applied = await mark_invite_accepted(
        db,
        invite_token=parsed.token,
        accepted_at=accepted_at,
        accepted_professional_id=parsed.professional_id,
        accepted_professional_name=parsed.professional_name,
        accepted_professional_email=parsed.professional_email,
    )

    # If the invite was bound to a case, append an event so mediators
    # see "Dr. Nomsa accepted on Sep 7" on the /mine console. Case
    # ownership was already enforced at invite time — this is a
    # trusted server-to-server callback.
    case_id = invite.get("case_id")
    if applied and case_id:
        try:
            display_name = (
                parsed.professional_name
                or invite.get("professional_name")
                or "Professional"
            )
            await db[_CASES_COLL].update_one(
                {"case_id": case_id},
                {"$push": {
                    "directory_invite_acceptances": {
                        "invite_id": invite.get("invite_id"),
                        "professional_name": display_name,
                        "professional_email": (
                            parsed.professional_email
                            or invite.get("professional_email")
                        ),
                        "accepted_at": accepted_at,
                    },
                }},
            )
        except Exception:
            logger.exception(
                "directory-invite accept case-event append failed "
                "invite_id=%s case_id=%s",
                invite.get("invite_id"), case_id,
            )

    return {
        "ok": True,
        "status": "accepted",
        "case_id": case_id,
        "applied": applied,
    }


@router.get("/professional/directory/invites")
async def list_professional_directory_invites(
    limit: int = 50,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the caller's most recent invitations (both pending and
    accepted). Powers the mediator-facing "Who did I invite?" audit
    view. Raw invite_token is stripped so a compromised session
    cannot forge acceptance webhooks."""
    from professional_directory import list_invites_for_inviter

    rows = await list_invites_for_inviter(
        db, inviter_user_id=current.user_id, limit=limit,
    )
    return {
        "invites": [
            {
                "invite_id": row.get("invite_id"),
                "case_id": row.get("case_id"),
                "professional_id": row.get("professional_id"),
                "professional_name": row.get("professional_name"),
                "professional_email": row.get("professional_email"),
                "personal_note": row.get("personal_note"),
                "status": row.get("status") or "pending",
                "created_at": _iso(row.get("created_at")),
                "accepted_at": _iso(row.get("accepted_at")) if row.get("accepted_at") else None,
                "accepted_professional_name": row.get("accepted_professional_name"),
            }
            for row in rows
        ],
    }



# =========================== Joint Alignment consent split =========================== #
# Per the family-safety spec, comparison and professional-release are
# TWO distinct actions requiring TWO separate consents:
#
#   * `comparison_consent` — parent authorises the app to compare
#     their answers with their co-parent's. Does not authorise anyone
#     outside the household to see the resulting report.
#   * `release_consent` — parent authorises the app to hand the
#     Joint Alignment Report to a NAMED professional. Requires a
#     matching consent from the co-parent for the same professional
#     before the release actually happens.
#
# Guardrails:
#   * Consent to comparison DOES NOT auto-authorise professional access.
#   * A parent can revoke either consent at any time before release.
#   * Every consent row records `consent_version` verbatim so future
#     legal-copy edits don't retroactively rewrite what was agreed.
#

_JA_COMPARISON_CONSENT_TEXT = (
    "I authorize SA CoParents to compare the selected completed reports "
    "from both participating parents for the limited purpose of "
    "identifying shared child-focused goals, different perspectives, "
    "and topics that may benefit from professional discussion. I "
    "understand that the comparison is not a determination of truth, "
    "parental fitness, custody, or the best interests of the child."
)
_JA_RELEASE_CONSENT_TEXT_TEMPLATE = (
    "I authorize the completed Joint Alignment Report to be made "
    "available to {professional_name} through SA CoParents Align. "
    "This authorization applies only to the completed Joint Alignment "
    "Report and does not provide access to my raw answers, private "
    "journal, AI Coach conversations, protected safety responses, or "
    "other unselected reports."
)
_JA_CONSENT_VERSION = "2026-09-08"


class ComparisonConsentBody(BaseModel):
    consented: bool = True
    """Set to `false` to revoke a previously-recorded consent. Default
    `true` because the wizard is affirmative-action only."""


class ReleaseConsentBody(BaseModel):
    professional_name: str = Field(..., min_length=1, max_length=160)
    """The exact display name of the professional the parent is
    releasing the Joint Alignment Report to. Case-insensitive when
    the sibling app resolves eligibility, but stored verbatim for
    audit."""
    consented: bool = True


async def _resolve_parent_in_case(
    db: AsyncIOMotorDatabase, *, case_id: str, current_email: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Fetch the case + locate the parent row whose email matches the
    caller. Raises 404 when the case is missing / the caller isn't a
    party."""
    case = await db[_CASES_COLL].find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    email_lower = (current_email or "").lower()
    parent = next(
        (p for p in case.get("parents") or []
         if (p.get("email") or "").lower() == email_lower),
        None,
    )
    if not parent:
        raise HTTPException(
            status_code=403,
            detail="You are not a party to this case.",
        )
    return case, parent


def _consent_shape(parent: Dict[str, Any]) -> Dict[str, Any]:
    """Public per-parent consent shape."""
    return {
        "email": parent.get("email"),
        "name": parent.get("name"),
        "comparison": {
            "consented": bool(parent.get("comparison_consent_at")),
            "consented_at": _iso(parent.get("comparison_consent_at")),
            "revoked_at": _iso(parent.get("comparison_consent_revoked_at"))
                if parent.get("comparison_consent_revoked_at") else None,
            "version": parent.get("comparison_consent_version"),
        },
        "release": {
            "consented": bool(parent.get("release_consent_at")),
            "consented_at": _iso(parent.get("release_consent_at")),
            "revoked_at": _iso(parent.get("release_consent_revoked_at"))
                if parent.get("release_consent_revoked_at") else None,
            "professional_name": parent.get("release_consent_professional_name"),
            "version": parent.get("release_consent_version"),
        },
    }


@router.post("/joint-alignment/cases/{case_id}/comparison-consent")
async def record_comparison_consent(
    body: ComparisonConsentBody,
    case_id: str = Path(..., min_length=6, max_length=32),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """The caller records (or revokes) their consent to have their
    answers compared with the co-parent's. Independent from
    release-to-professional consent."""
    case, parent = await _resolve_parent_in_case(
        db, case_id=case_id, current_email=current.email or "",
    )
    now = _now()
    parent_email_lower = (parent.get("email") or "").lower()
    set_fields: Dict[str, Any] = {}
    if body.consented:
        set_fields["parents.$.comparison_consent_at"] = now
        set_fields["parents.$.comparison_consent_version"] = _JA_CONSENT_VERSION
        set_fields["parents.$.comparison_consent_revoked_at"] = None
    else:
        # Revoke — keep original consent-at for audit, add revoked_at.
        set_fields["parents.$.comparison_consent_revoked_at"] = now

    await db[_CASES_COLL].update_one(
        {"case_id": case_id, "parents.email": parent.get("email")},
        {"$set": set_fields},
    )
    fresh = await db[_CASES_COLL].find_one({"case_id": case_id})
    fresh_parent = next(
        (p for p in fresh.get("parents") or []
         if (p.get("email") or "").lower() == parent_email_lower),
        parent,
    )
    return {
        "case_id": case_id,
        "consent": _consent_shape(fresh_parent),
        "consent_text": _JA_COMPARISON_CONSENT_TEXT,
    }


@router.post("/joint-alignment/cases/{case_id}/release-consent")
async def record_release_consent(
    body: ReleaseConsentBody,
    case_id: str = Path(..., min_length=6, max_length=32),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """The caller records (or revokes) their consent to release the
    resulting Joint Alignment Report to a NAMED professional.
    Distinct from comparison consent — a parent may consent to
    compare without consenting to release."""
    professional_name = body.professional_name.strip()
    case, parent = await _resolve_parent_in_case(
        db, case_id=case_id, current_email=current.email or "",
    )
    now = _now()
    parent_email_lower = (parent.get("email") or "").lower()
    set_fields: Dict[str, Any] = {}
    if body.consented:
        set_fields["parents.$.release_consent_at"] = now
        set_fields["parents.$.release_consent_professional_name"] = professional_name
        set_fields["parents.$.release_consent_version"] = _JA_CONSENT_VERSION
        set_fields["parents.$.release_consent_revoked_at"] = None
    else:
        set_fields["parents.$.release_consent_revoked_at"] = now

    await db[_CASES_COLL].update_one(
        {"case_id": case_id, "parents.email": parent.get("email")},
        {"$set": set_fields},
    )
    fresh = await db[_CASES_COLL].find_one({"case_id": case_id})
    fresh_parent = next(
        (p for p in fresh.get("parents") or []
         if (p.get("email") or "").lower() == parent_email_lower),
        parent,
    )
    return {
        "case_id": case_id,
        "consent": _consent_shape(fresh_parent),
        "consent_text": _JA_RELEASE_CONSENT_TEXT_TEMPLATE.format(
            professional_name=professional_name,
        ),
    }


@router.get("/joint-alignment/cases/{case_id}/consent-status")
async def get_case_consent_status(
    case_id: str = Path(..., min_length=6, max_length=32),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the consent state for BOTH parents on this case.
    Accessible to any party in the case OR the case mediator so the
    /mine console can show progress.

    Eligibility flags rolled up at the top of the response:
      * `comparison_eligible` — both parents' `comparison.consented`
        AND neither has revoked.
      * `release_eligible` — both parents' `release.consented` for
        the SAME professional_name AND neither has revoked.
    """
    case = await db[_CASES_COLL].find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    parties = {
        (p.get("email") or "").lower() for p in case.get("parents") or []
    }
    mediator_id = (case.get("professional") or {}).get("user_id")
    caller_email = (current.email or "").lower()
    is_party = caller_email in parties
    is_mediator = bool(mediator_id and mediator_id == current.user_id)
    if not (is_party or is_mediator):
        raise HTTPException(
            status_code=403,
            detail="You are not a party to this case.",
        )

    per_parent = [_consent_shape(p) for p in case.get("parents") or []]

    def _consent_active(row: Dict[str, Any], kind: str) -> bool:
        block = row.get(kind) or {}
        return bool(block.get("consented")) and not block.get("revoked_at")

    all_comp = all(_consent_active(r, "comparison") for r in per_parent)
    comparison_eligible = bool(per_parent) and all_comp

    release_pros = {r["release"]["professional_name"] for r in per_parent
                    if _consent_active(r, "release")}
    release_eligible = (
        bool(per_parent)
        and all(_consent_active(r, "release") for r in per_parent)
        and len(release_pros) == 1
    )
    return {
        "case_id": case_id,
        "consent_version": _JA_CONSENT_VERSION,
        "parents": per_parent,
        "comparison_eligible": comparison_eligible,
        "release_eligible": release_eligible,
        "release_professional_name": (
            next(iter(release_pros)) if release_eligible else None
        ),
        "consent_texts": {
            "comparison": _JA_COMPARISON_CONSENT_TEXT,
            "release_template": _JA_RELEASE_CONSENT_TEXT_TEMPLATE,
        },
    }


# =========================== Joint Alignment on-screen preview =========================== #
# On-screen "did we agree?" preview shown between the comparison-
# consent step and the release-consent step. Per the family-safety
# spec, this stage MUST NOT leak either parent's raw content — the
# preview is agreement-flag-only ("agree" / "differ" / "incomplete")
# per structural topic derived from the minimised payload.
#
# Only viewable by the two parents on the case (never the mediator).
# Both parents must have active `comparison_consent`. Preview does
# NOT flip status to `released` and never sends the report to any
# professional. That still requires the separate `release_consent`
# from both parents.

def _stable_hash(v: Any) -> str:
    """
    Deterministic canonical hash of any JSON-serialisable value.
    Sorted keys / no whitespace so two structurally-identical
    payloads always hash the same.

    Recursively strips volatile timestamp fields (`updated_at`,
    `generated_at`) that reflect *when* a parent saved a section,
    not *what* they saved — otherwise two identical answers submitted
    seconds apart would compare as `differ`.
    """
    def _strip(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: _strip(val) for k, val in obj.items()
                if k not in ("updated_at", "generated_at")
            }
        if isinstance(obj, list):
            return [_strip(x) for x in obj]
        return obj

    return hashlib.sha256(
        json.dumps(
            _strip(v), sort_keys=True, separators=(",", ":"), default=str,
        ).encode("utf-8"),
    ).hexdigest()


def _topic_label(assessment_type: str, key: str) -> str:
    """Pretty label per topic key. Falls back to Title Case."""
    labels = {
        "assessment": "Co-Parenting Assessment",
        "foundation_statement": "Foundation Statement",
        "mediation_statement": "Mediation Statement",
        "mediation_preparation": "Mediation Preparation",
        "profile": "Child Profile",
        "questions_for_school_or_parent": "Questions for School",
        "questions_for_provider": "Questions for Provider",
        "questions_for_therapist": "Questions for Therapist",
        "rating_areas": "Rating Areas",
        "signals": "Signal Flags",
    }
    return labels.get(key) or key.replace("_", " ").title()


def _topic_order(assessment_type: str) -> List[str]:
    """Stable topic order per assessment_type so the preview reads
    the same for both parents."""
    if assessment_type == "co-parenting":
        return [
            "assessment", "foundation_statement",
            "mediation_statement", "mediation_preparation",
        ]
    return [
        "profile", "foundation_statement", "rating_areas", "signals",
        "questions_for_school_or_parent",
        "questions_for_provider", "questions_for_therapist",
    ]


def _derive_preview_topics(
    assessment_type: str,
    payload_a: Optional[Dict[str, Any]],
    payload_b: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build the per-topic agreement flags list. Never returns raw
    content — only a flag string per topic.
    """
    a = payload_a or {}
    b = payload_b or {}
    order = _topic_order(assessment_type)
    # Union of predicted order + any extras the payload may add.
    seen = set(order)
    for extra in list(a.keys()) + list(b.keys()):
        if extra not in seen and extra != "pathway_version" and extra != "generated_at":
            order.append(extra)
            seen.add(extra)

    out: List[Dict[str, Any]] = []
    for key in order:
        va = a.get(key)
        vb = b.get(key)
        a_done = va not in (None, {}, [], "")
        b_done = vb not in (None, {}, [], "")
        if not a_done and not b_done:
            # Neither parent produced anything for this topic — skip
            # entirely so the parent isn't shown noise.
            continue
        if not (a_done and b_done):
            alignment = "incomplete"
        else:
            alignment = "agree" if _stable_hash(va) == _stable_hash(vb) else "differ"
        out.append({
            "topic_key": key,
            "topic_label": _topic_label(assessment_type, key),
            "alignment": alignment,
            "parent_a_completed": a_done,
            "parent_b_completed": b_done,
        })
    return out


@router.get("/joint-alignment/cases/{case_id}/preview")
async def get_case_alignment_preview(
    case_id: str = Path(..., min_length=6, max_length=32),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Agreement-flag-only preview of the two parents' completed
    assessments. Runs the same compare as the final Joint Alignment
    Report but returns ONLY per-topic `agree / differ / incomplete`
    flags — never the underlying content. Powers the on-screen
    review step between comparison-consent and release-consent.

    Guards:
      * Case must exist and not be `expired`/`cancelled`.
      * Caller must be one of the two parents on the case. Mediators
        cannot see this preview — they see the final release-gated
        report instead.
      * Both parents must have active `comparison_consent` (not
        revoked). Missing on either side → 403.
      * Both parents must have completed the assessment
        (`assessment_completed_at`). Missing on either side → 409.

    Response never includes:
      * Any parent's raw answers, journal entries, safety data, or
        AI Coach content.
      * The other parent's identity beyond the display name already
        available from `_case_public_shape`.
    """
    case = await db[_CASES_COLL].find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.get("status") in ("expired", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Case is {case.get('status')}.",
        )

    caller_email = (current.email or "").lower()
    parents = case.get("parents") or []
    if not any(
        (p.get("email") or "").lower() == caller_email for p in parents
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a party to this case.",
        )

    # Consent gate — BOTH parents must have active comparison consent.
    def _comp_active(p: Dict[str, Any]) -> bool:
        return bool(p.get("comparison_consent_at")) and not p.get(
            "comparison_consent_revoked_at",
        )
    if not (parents and all(_comp_active(p) for p in parents)):
        raise HTTPException(
            status_code=403,
            detail=(
                "Both parents must record their comparison consent "
                "before the preview is available."
            ),
        )

    # Completion gate — both parents must have finished their assessment.
    if not all(p.get("assessment_completed_at") for p in parents):
        raise HTTPException(
            status_code=409,
            detail="Both parents must complete their assessment first.",
        )

    assessment_type = case.get("assessment_type") or ""
    payloads: List[Optional[Dict[str, Any]]] = []
    for p in parents:
        uid = p.get("user_id")
        if not uid:
            payloads.append(None)
            continue
        payloads.append(
            await _minimised_assessment_payload(db, assessment_type, uid),
        )
    while len(payloads) < 2:
        payloads.append(None)

    topics = _derive_preview_topics(
        assessment_type, payloads[0], payloads[1],
    )
    counts = {"total": len(topics), "agreed": 0, "differed": 0, "incomplete": 0}
    for t in topics:
        if t["alignment"] == "agree":
            counts["agreed"] += 1
        elif t["alignment"] == "differ":
            counts["differed"] += 1
        else:
            counts["incomplete"] += 1

    return {
        "case_id": case_id,
        "assessment_type": assessment_type,
        "generated_at": _iso(_now()),
        "parents": [
            {"name": p.get("name"), "email": p.get("email")} for p in parents
        ],
        "topics": topics,
        "summary": counts,
        "preview_notice": (
            "Nothing has been shared with anyone outside your household. "
            "This is a private, agreement-flag-only preview. To release "
            "the full Joint Alignment Report to a named professional you "
            "both need to record separate release consent."
        ),
    }
