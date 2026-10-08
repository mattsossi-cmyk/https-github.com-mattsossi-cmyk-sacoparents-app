"""Weekly Self Journey note: one-tap unsubscribe, tracked CTA, admin stats."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from analytics_routes import require_admin
from auth import UserPublic, get_db
from release_check import origin_from_request
from self_assessment_routes import _UNSUB_PAGE
from self_journey_weekly import (
    NOTES,
    PREFS,
    build_highlights,
    make_unsubscribe_token,
    read_click_token,
    read_unsubscribe_token,
    weekly_stats,
)

SAMPLE_ACTIVITY = {
    "sa": 1,
    "days": {"d1", "d2", "d3"},
    "streak": 3,
    "cp": 1,
    "cn": ["Medical", "Educational"],
    "fb": True,
}

router = APIRouter(prefix="/self-journey", tags=["self-journey"])
admin_router = APIRouter(prefix="/admin/self-journey-weekly", tags=["admin"])


class SampleBody(BaseModel):
    # Progress types to include (sa, checkins, cp, cn, fb); omitted = all five.
    types: Optional[Dict[str, bool]] = None


def _sample_activity(types: Optional[Dict[str, bool]]) -> Dict[str, Any]:
    def on(key: str) -> bool:
        return types is None or bool(types.get(key))

    return {
        "sa": SAMPLE_ACTIVITY["sa"] if on("sa") else 0,
        "days": set(SAMPLE_ACTIVITY["days"]) if on("checkins") else set(),
        "streak": SAMPLE_ACTIVITY["streak"] if on("checkins") else 0,
        "cp": SAMPLE_ACTIVITY["cp"] if on("cp") else 0,
        "cn": list(SAMPLE_ACTIVITY["cn"]) if on("cn") else [],
        "fb": on("fb"),
    }


def _first_name(admin: UserPublic) -> Optional[str]:
    return (admin.name or "").split(" ")[0] or None


@router.get("/weekly-note/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_weekly_note(token: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> HTMLResponse:
    user_id = read_unsubscribe_token(token)
    if not user_id:
        return HTMLResponse(_UNSUB_PAGE.format(title="Link not valid",
                                               body="This unsubscribe link isn't valid."), status_code=400)
    await db[PREFS].update_one(
        {"user_id": user_id},
        {"$set": {"unsubscribed": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return HTMLResponse(_UNSUB_PAGE.format(
        title="You're unsubscribed",
        body="You won't receive weekly notes anymore. Everything you've saved stays in your account.",
    ))


@router.get("/weekly-note/open")
async def open_from_weekly_note(
    request: Request, token: str = "", db: AsyncIOMotorDatabase = Depends(get_db),
) -> RedirectResponse:
    """Records the first click on the note's button, then always lands on the dashboard."""
    payload = read_click_token(token)
    if payload:
        await db[NOTES].update_one(
            {"user_id": payload["sub"], "week_key": payload["wk"], "clicked_at": {"$exists": False}},
            {"$set": {"clicked_at": datetime.now(timezone.utc).isoformat()}},
        )
    return RedirectResponse(f"{origin_from_request(request)}/dashboard", status_code=302)


@admin_router.get("/stats")
async def weekly_note_stats(
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    return await weekly_stats(db)


@admin_router.post("/preview")
async def preview_weekly_note(
    request: Request,
    body: SampleBody,
    admin: UserPublic = Depends(require_admin),
) -> Dict[str, Any]:
    """Renders the weekly note for the chosen progress types without sending it (links are inert)."""
    from email_service import render_self_journey_weekly_note

    highlights = build_highlights(_sample_activity(body.types))
    if not highlights:
        return {"highlights": [], "subject": None, "html": None, "text": None, "sent_to": admin.email}
    note = render_self_journey_weekly_note(
        first_name=_first_name(admin),
        highlights=highlights,
        cta_url=f"{origin_from_request(request)}/dashboard",
        unsubscribe_url="#unsubscribe-preview",
    )
    return {**note, "highlights": highlights, "sent_to": admin.email}


@admin_router.post("/sample")
async def send_weekly_note_sample(
    request: Request,
    body: Optional[SampleBody] = None,
    admin: UserPublic = Depends(require_admin),
) -> Dict[str, Any]:
    """Emails the admin a sample weekly note (all five kinds of progress unless `types` narrows it)."""
    from email_service import EmailNotConfigured, EmailSendError, send_self_journey_weekly_note

    highlights = build_highlights(_sample_activity(body.types if body else None))
    if not highlights:
        raise HTTPException(status_code=400, detail="Turn on at least one kind of progress first.")
    origin = origin_from_request(request)
    try:
        send_self_journey_weekly_note(
            to_email=admin.email,
            first_name=_first_name(admin),
            highlights=highlights,
            cta_url=f"{origin}/dashboard",
            unsubscribe_url=f"{origin}/api/self-journey/weekly-note/unsubscribe?token={make_unsubscribe_token(admin.user_id)}",
        )
    except (EmailNotConfigured, EmailSendError) as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't send the sample: {exc}")
    return {"ok": True, "sent_to": admin.email}
