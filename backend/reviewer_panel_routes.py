"""Reviewer Panel — public transparency endpoint listing which independent
professionals have reviewed the Safety Screen content.

Data lives in a JSON file (`reviewer_panel.json`) rather than the database
because it needs to be human-editable + version-controlled: the operator
adds a reviewer entry ONLY once that reviewer has signed off in writing.
Editable schema per entry:

    {
      "name":       "Full Name, Credentials",   # required
      "role":       "DV advocate | forensic psychologist | family-law attorney | other",
      "org":        "Optional organisation",
      "review_date":"YYYY-MM-DD",              # required
      "review_scope": "Which parts of the screen were reviewed",
      "attestation": "Short public quote or note from the reviewer"
    }

Also exposes a `/packet` endpoint that returns a single PDF reviewer
packet (current questions + scoring rules + methodology + review
checklist) — one file to hand to each candidate reviewer.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

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
    reviewers.sort(key=lambda r: r.get("review_date") or "", reverse=True)
    data["reviewers"] = reviewers
    return data


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
