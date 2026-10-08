"""Weekly Self Journey note: one-tap unsubscribe, tracked CTA, admin stats."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

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


@admin_router.post("/sample")
async def send_weekly_note_sample(
    request: Request,
    admin: UserPublic = Depends(require_admin),
) -> Dict[str, Any]:
    """Emails the admin a sample weekly note showing all five kinds of progress."""
    from email_service import EmailNotConfigured, EmailSendError, send_self_journey_weekly_note

    origin = origin_from_request(request)
    try:
        send_self_journey_weekly_note(
            to_email=admin.email,
            first_name=(admin.name or "").split(" ")[0] or None,
            highlights=build_highlights(SAMPLE_ACTIVITY),
            cta_url=f"{origin}/dashboard",
            unsubscribe_url=f"{origin}/api/self-journey/weekly-note/unsubscribe?token={make_unsubscribe_token(admin.user_id)}",
        )
    except (EmailNotConfigured, EmailSendError) as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't send the sample: {exc}")
    return {"ok": True, "sent_to": admin.email}
