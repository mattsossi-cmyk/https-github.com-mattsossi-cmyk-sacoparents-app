"""One-tap unsubscribe for the weekly Self Journey note."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_db
from self_assessment_routes import _UNSUB_PAGE
from self_journey_weekly import PREFS, read_unsubscribe_token

router = APIRouter(prefix="/self-journey", tags=["self-journey"])


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
