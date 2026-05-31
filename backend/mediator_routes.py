"""Mediator partner routes.

A small public endpoint that records each time a mediator generates an
embed badge from the public /mediator-badge page. This gives the SA
Coparents team a simple audit of who is actively promoting the app.
No auth required — this is a community-facing tool.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, EmailStr

router = APIRouter(prefix="/mediator", tags=["mediator"])


class BadgeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    practice_url: str = Field(..., min_length=4, max_length=300)
    variant: str = Field(default="light", max_length=20)
    email: Optional[EmailStr] = None


class BadgeAck(BaseModel):
    ok: bool
    saved: bool


@router.post("/badge", response_model=BadgeAck)
async def log_badge_generation(body: BadgeRequest, request: Request):
    """Best-effort logging. Always returns 200 so client-side never blocks."""
    db = request.app.state.db
    try:
        await db.mediator_badges.insert_one({
            "name": body.name.strip(),
            "practice_url": body.practice_url.strip(),
            "variant": body.variant.strip().lower(),
            "email": (body.email.lower() if body.email else None),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return BadgeAck(ok=True, saved=True)
    except Exception:
        # Never block the mediator's flow on a logging hiccup.
        return BadgeAck(ok=True, saved=False)
