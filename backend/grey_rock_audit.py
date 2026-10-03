"""Grey-rock audit log — iter245 Backend Audit Log.

Tracks every transition in/out of grey-rock mode so the mediator PDF
(generated in `cp_progress_pdf.py`) can render a safety-mode timeline.

Clinical significance: a repeated oscillation in and out of grey-rock
mode is a signal professionals use to detect escalating / de-
escalating interpersonal risk between parents. Capturing this with a
tamper-evident timestamp (server-side `datetime.now(timezone.utc)`)
gives the mediator a clinical artifact rather than a parent's
self-report.

Routes mounted under `/api/portal/grey-rock/*`:
- POST /audit  → append a transition event
- GET /audit   → list the current user's transitions (newest first)

Collection: `grey_rock_audit`
Document shape:
    {
      "_id": ObjectId,
      "user_id": str,
      "event": "on" | "off",
      "source": str,          # "safety_screen" | "toggle_chip" | "import"
      "at": ISO 8601 str,
    }
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user, get_db
from models import UserPublic


logger = logging.getLogger(__name__)

# NOTE: the parent `portal_router` already carries the `/portal` prefix,
# so this router adds `/grey-rock` on top; final paths are
# `/api/portal/grey-rock/audit`.
router = APIRouter(prefix="/portal/grey-rock", tags=["grey-rock-audit"])


_EventName = Literal["on", "off"]
_SourceName = Literal["safety_screen", "toggle_chip", "import"]


class GreyRockAuditIn(BaseModel):
    event: _EventName
    source: _SourceName = Field(
        default="toggle_chip",
        description=(
            "Where in the UI the transition was invoked: 'safety_screen' "
            "when the Safety-First flow set the flag, 'toggle_chip' for "
            "the Alignment & Tools grey-rock toggle, 'import' for a "
            "server-side backfill."
        ),
    )


class GreyRockAuditEvent(BaseModel):
    event: _EventName
    source: _SourceName
    at: str  # ISO 8601 UTC


class GreyRockAuditList(BaseModel):
    events: List[GreyRockAuditEvent]


@router.post("/audit", response_model=GreyRockAuditEvent)
async def record_transition(
    payload: GreyRockAuditIn,
    user: UserPublic = Depends(get_current_user),
    db=Depends(get_db),
) -> GreyRockAuditEvent:
    """Append one grey-rock transition event for the signed-in user.

    Idempotency: callers are expected to only post when they KNOW the
    flag transitioned (e.g. the Safety-First flow just flipped it on,
    or the toggle chip's two-step confirm just cleared it). We don't
    de-dupe server-side because a legitimate re-flag two minutes
    later is itself clinically meaningful.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user.user_id,
        "event": payload.event,
        "source": payload.source,
        "at": now_iso,
    }
    try:
        await db.grey_rock_audit.insert_one(doc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("grey-rock audit insert failed")
        raise HTTPException(status_code=500, detail="audit_write_failed") from exc

    return GreyRockAuditEvent(event=payload.event, source=payload.source, at=now_iso)


@router.get("/audit", response_model=GreyRockAuditList)
async def list_transitions(
    user: UserPublic = Depends(get_current_user),
    db=Depends(get_db),
) -> GreyRockAuditList:
    """Return this user's grey-rock timeline (newest first, capped
    at 200 events — more than enough for the mediator PDF)."""
    try:
        cursor = (
            db.grey_rock_audit.find({"user_id": user.user_id})
            .sort("at", -1)
            .limit(200)
        )
        rows = await cursor.to_list(length=200)
    except Exception as exc:  # noqa: BLE001
        logger.exception("grey-rock audit list failed")
        raise HTTPException(status_code=500, detail="audit_read_failed") from exc

    events = [
        GreyRockAuditEvent(
            event=row.get("event"),
            source=row.get("source", "toggle_chip"),
            at=row.get("at"),
        )
        for row in rows
        if row.get("event") in ("on", "off")
    ]
    return GreyRockAuditList(events=events)
