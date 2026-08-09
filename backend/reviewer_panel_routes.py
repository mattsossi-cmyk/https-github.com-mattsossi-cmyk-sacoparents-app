"""Reviewer Panel — public transparency endpoint listing which independent
professionals have reviewed the Safety Screen content.

Data lives in a JSON file (`reviewer_panel.json`) rather than the database
because it needs to be human-editable + version-controlled: the operator
adds a reviewer entry ONLY once that reviewer has signed off in writing.
Editable schema per entry:

    {
      "id":         "auto-generated uuid hex[:12]",  # stable id for PATCH/DELETE
      "name":       "Full Name, Credentials",   # required
      "role":       "dv_advocate | forensic_psychologist | family_law_attorney | clinician | other",
      "org":        "Optional organisation",
      "review_date":"YYYY-MM-DD",              # required
      "review_scope": "Which parts of the screen were reviewed",
      "attestation": "Short public quote or note from the reviewer"
    }

Also exposes a `/packet` endpoint that returns a single PDF reviewer
packet (current questions + scoring rules + methodology + review
checklist) — one file to hand to each candidate reviewer.

Iter 88: added operator-gated CRUD (POST/PATCH/DELETE `/reviewers*`)
so the operator can add/edit/remove entries from an in-app admin form
instead of hand-editing this JSON file.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


router = APIRouter(prefix="/reviewer-panel", tags=["reviewer-panel"])

DATA_PATH = os.path.join(os.path.dirname(__file__), "reviewer_panel.json")


def _load() -> Dict[str, Any]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"review_scope": "", "review_scope_version": "", "reviewers": []}
    reviewers = list(data.get("reviewers") or [])
    # Back-fill an `id` on any legacy entries so PATCH/DELETE can address
    # them stably. If we had to back-fill anything, persist immediately —
    # otherwise the next _load() would generate different random ids and
    # any PATCH/DELETE using the previously-returned id would 404
    # (LOW finding from the iter 87-93 code review).
    backfilled = False
    for r in reviewers:
        if not r.get("id"):
            r["id"] = uuid.uuid4().hex[:12]
            backfilled = True
    reviewers.sort(key=lambda r: r.get("review_date") or "", reverse=True)
    data["reviewers"] = reviewers
    if backfilled:
        try:
            _save(data)
        except Exception:  # noqa: BLE001
            # Non-fatal — worst case the next read regenerates. Public
            # GET must still succeed even if the disk is momentarily
            # read-only.
            pass
    return data


def _save(data: Dict[str, Any]) -> None:
    """Persist the panel atomically (tmp-file + rename).

    Bumps `last_updated` to today's UTC date on every write so the
    public transparency card shows an accurate "last touched" line.
    """
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dir_ = os.path.dirname(DATA_PATH) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".reviewer_panel.", suffix=".json", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, DATA_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


@router.get("")
async def get_reviewer_panel():
    data = _load()
    return {
        "review_scope":         data.get("review_scope", ""),
        "review_scope_version": data.get("review_scope_version", ""),
        "last_updated":         data.get("last_updated", ""),
        "reviewers":            data.get("reviewers", []),
        "count":                len(data.get("reviewers") or []),
        "status":               "reviewed" if data.get("reviewers") else "pending",
    }


@router.get("/is-operator")
async def is_operator(user: UserPublic = Depends(get_current_user)):
    """Return whether the caller is the site operator (frontend gates
    the reviewer send dialog on this)."""
    try:
        _require_operator(user)
        return {"is_operator": True, "operator_email": _operator_email()}
    except HTTPException:
        return {"is_operator": False, "operator_email": None}


@router.get("/packet")
async def get_reviewer_packet():
    """Generate a single PDF containing everything a candidate reviewer
    needs to evaluate: the current screen questions, scoring rules, a
    sample of the generated output, and a review checklist keyed to the
    MASIC-S coverage gaps.
    """
    try:
        from reviewer_packet_pdf import build_reviewer_packet_pdf
    except ImportError as e:
        raise HTTPException(500, f"Reviewer packet generator unavailable: {e}") from e

    pdf_bytes = build_reviewer_packet_pdf(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                'attachment; filename="sa-coparents-safety-screen-reviewer-packet.pdf"',
        },
    )


# ---------------------------------------------------------------------------
# Send the packet — operator-only.
# ---------------------------------------------------------------------------

ROLE_LABEL = {
    "dv_advocate":            "Domestic-violence advocate",
    "forensic_psychologist":  "Forensic psychologist",
    "family_law_attorney":    "Family-law attorney (Texas)",
    "clinician":              "Licensed clinician",
    "other":                  "Independent reviewer",
}


class ReviewerSendBody(BaseModel):
    recipient_email: EmailStr
    recipient_name:  str = Field("", max_length=120)
    recipient_role:  str = Field("other", max_length=60)
    personal_note:   str = Field("", max_length=1200)


def _operator_email() -> str:
    return (os.environ.get("OPERATOR_EMAIL") or "").strip().lower()


def _require_operator(user: UserPublic) -> None:
    """Only the configured OPERATOR_EMAIL account may send reviewer
    invitations. Guest accounts are always rejected."""
    op = _operator_email()
    if user.is_guest:
        raise HTTPException(403, "Only the site operator can send reviewer invitations.")
    if not op:
        raise HTTPException(503, "OPERATOR_EMAIL is not configured on this environment.")
    if (user.email or "").strip().lower() != op:
        raise HTTPException(403, "Only the site operator can send reviewer invitations.")


@router.post("/send")
async def send_packet(
    body: ReviewerSendBody,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _require_operator(user)

    from reviewer_packet_pdf import build_reviewer_packet_pdf
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        send_reviewer_packet,
    )

    to_email = body.recipient_email.strip().lower()
    if to_email.endswith("@demo.local"):
        raise HTTPException(400, "Please use the reviewer's real email address.")

    pdf_bytes = build_reviewer_packet_pdf(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        send_reviewer_packet(
            to_email=to_email,
            recipient_name=body.recipient_name.strip(),
            recipient_role_label=ROLE_LABEL.get(body.recipient_role, ROLE_LABEL["other"]),
            operator_name=user.name or "",
            operator_email=user.email or _operator_email(),
            personal_note=body.personal_note.strip(),
            pdf_bytes=pdf_bytes,
        )
    except EmailNotConfigured as e:
        raise HTTPException(503, "Email service isn't configured on this environment.") from e
    except EmailSendError as e:
        raise HTTPException(503, "Couldn't send the packet right now. Please try again.") from e

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.reviewer_packet_sends.insert_one({
        "sent_by":         user.user_id,
        "recipient_email": to_email,
        "recipient_name":  body.recipient_name.strip(),
        "recipient_role":  body.recipient_role,
        "sent_at":         now_iso,
    })
    return {"ok": True, "emailed_to": to_email, "role": body.recipient_role}


@router.get("/sends")
async def list_sends(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Operator-only audit list of previous reviewer packet sends."""
    _require_operator(user)
    cursor = db.reviewer_packet_sends.find(
        {}, {"_id": 0},
    ).sort("sent_at", -1).limit(50)
    return {"sends": [d async for d in cursor]}


# ---------------------------------------------------------------------------
# Operator-only CRUD — add/edit/remove reviewer entries in reviewer_panel.json.
# ---------------------------------------------------------------------------

ROLE_KEYS = tuple(ROLE_LABEL.keys())  # dv_advocate, forensic_psychologist, ...


class ReviewerCreate(BaseModel):
    name:          str = Field(..., min_length=2, max_length=140)
    role:          str = Field(..., max_length=60)
    org:           Optional[str] = Field(None, max_length=140)
    review_date:   str = Field(..., min_length=8, max_length=10,
                               description="ISO-like YYYY-MM-DD")
    review_scope:  Optional[str] = Field(None, max_length=400)
    attestation:   Optional[str] = Field(None, max_length=600)


class ReviewerUpdate(BaseModel):
    """Same fields as create but every field is optional (PATCH semantics)."""
    name:          Optional[str] = Field(None, min_length=2, max_length=140)
    role:          Optional[str] = Field(None, max_length=60)
    org:           Optional[str] = Field(None, max_length=140)
    review_date:   Optional[str] = Field(None, min_length=8, max_length=10)
    review_scope:  Optional[str] = Field(None, max_length=400)
    attestation:   Optional[str] = Field(None, max_length=600)


def _validate_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role not in ROLE_KEYS:
        raise HTTPException(400, f"Role must be one of: {', '.join(ROLE_KEYS)}.")
    return role


def _validate_review_date(review_date: str) -> str:
    review_date = (review_date or "").strip()
    try:
        datetime.strptime(review_date, "%Y-%m-%d")
    except ValueError as e:
        raise HTTPException(400, "review_date must be in YYYY-MM-DD format.") from e
    return review_date


@router.post("/reviewers")
async def add_reviewer(
    body: ReviewerCreate,
    user: UserPublic = Depends(get_current_user),
):
    """Add a new reviewer entry. Operator-only."""
    _require_operator(user)
    role = _validate_role(body.role)
    review_date = _validate_review_date(body.review_date)

    data = _load()
    entry = {
        "id":            uuid.uuid4().hex[:12],
        "name":          body.name.strip(),
        "role":          role,
        "org":           (body.org or "").strip() or None,
        "review_date":   review_date,
        "review_scope":  (body.review_scope or "").strip() or None,
        "attestation":   (body.attestation or "").strip() or None,
    }
    reviewers = list(data.get("reviewers") or [])
    reviewers.append(entry)
    data["reviewers"] = reviewers
    _save(data)
    return {"ok": True, "reviewer": entry}


@router.patch("/reviewers/{reviewer_id}")
async def edit_reviewer(
    reviewer_id: str,
    body: ReviewerUpdate,
    user: UserPublic = Depends(get_current_user),
):
    """Edit any subset of fields on an existing reviewer. Operator-only."""
    _require_operator(user)
    data = _load()
    reviewers = list(data.get("reviewers") or [])
    for r in reviewers:
        if r.get("id") == reviewer_id:
            if body.name is not None:
                r["name"] = body.name.strip()
            if body.role is not None:
                r["role"] = _validate_role(body.role)
            if body.org is not None:
                r["org"] = body.org.strip() or None
            if body.review_date is not None:
                r["review_date"] = _validate_review_date(body.review_date)
            if body.review_scope is not None:
                r["review_scope"] = body.review_scope.strip() or None
            if body.attestation is not None:
                r["attestation"] = body.attestation.strip() or None
            data["reviewers"] = reviewers
            _save(data)
            return {"ok": True, "reviewer": r}
    raise HTTPException(404, "Reviewer not found.")


@router.delete("/reviewers/{reviewer_id}")
async def remove_reviewer(
    reviewer_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """Remove a reviewer entry from the public panel. Operator-only."""
    _require_operator(user)
    data = _load()
    reviewers = list(data.get("reviewers") or [])
    filtered = [r for r in reviewers if r.get("id") != reviewer_id]
    if len(filtered) == len(reviewers):
        raise HTTPException(404, "Reviewer not found.")
    data["reviewers"] = filtered
    _save(data)
    return {"ok": True, "removed_id": reviewer_id}


@router.get("/reviewers/roles")
async def list_roles():
    """Public — role keys + human labels used by the admin form."""
    return {"roles": [{"key": k, "label": v} for k, v in ROLE_LABEL.items()]}
