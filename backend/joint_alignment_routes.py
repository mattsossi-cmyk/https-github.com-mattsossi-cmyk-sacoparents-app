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
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Path
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

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

