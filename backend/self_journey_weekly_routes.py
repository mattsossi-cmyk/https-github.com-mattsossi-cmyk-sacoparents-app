"""Weekly Self Journey note: one-tap unsubscribe, tracked CTA, admin stats."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from analytics_routes import require_admin
from auth import UserPublic, get_db
from release_check import origin_from_request
from self_assessment_routes import _UNSUB_PAGE
from self_journey_weekly import NOTES, PREFS, read_click_token, read_unsubscribe_token, weekly_stats

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
