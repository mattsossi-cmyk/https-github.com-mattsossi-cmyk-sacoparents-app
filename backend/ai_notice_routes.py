"""AI privacy notice acknowledgment + "Send anyway" record.

GET  /api/ai-notice/version
POST /api/ai-notice/ack            -> users.ai_notice_version, users.ai_notice_ack_at (server UTC)
POST /api/ai-notice/send-anyway    {feature, labels} -> ai_send_anyway_log (user id, time, version, feature, labels only)

`require_ai_notice` guards every AI endpoint: 428 until the current version is acknowledged.
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ai_notice import AI_FEATURES, AI_NOTICE_LABELS, AI_NOTICE_VERSION, has_ai_notice
from auth import get_current_user, get_db
from models import UserPublic

router = APIRouter(prefix="/ai-notice", tags=["ai-notice"])

# Plain-string detail so existing error toasts can show it; 428 is only ever used for this.
AI_NOTICE_REQUIRED = "Please read and accept the AI privacy notice before using AI features."


def ensure_ai_notice(user: UserPublic) -> None:
    if not user or not user.ai_notice_current:
        raise HTTPException(status_code=428, detail=AI_NOTICE_REQUIRED)


async def require_ai_notice(current: UserPublic = Depends(get_current_user)) -> UserPublic:
    ensure_ai_notice(current)
    return current


async def user_has_ai_notice(db, user_id: str) -> bool:
    """For AI work that runs without a request user (PDFs, scheduled emails)."""
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "ai_notice_version": 1, "ai_notice_ack_at": 1}) or {}
    return has_ai_notice(doc)


class SendAnywayBody(BaseModel):
    feature: str
    labels: List[str] = Field(default_factory=list, max_length=len(AI_NOTICE_LABELS))


@router.get("/version")
async def ai_notice_version():
    return {"version": AI_NOTICE_VERSION}


@router.post("/ack")
async def ack_ai_notice(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    # "Before you continue" (current Privacy Notice + sensitive-info consent) must come first.
    if not current.consent_current:
        raise HTTPException(status_code=409, detail="Please accept the Privacy Notice on the \"Before you continue\" screen first.")
    at = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"user_id": current.user_id}, {"$set": {"ai_notice_version": AI_NOTICE_VERSION, "ai_notice_ack_at": at}})
    return {"ok": True, "version": AI_NOTICE_VERSION, "ack_at": at}


@router.post("/send-anyway")
async def log_send_anyway(body: SendAnywayBody, current: UserPublic = Depends(require_ai_notice), db=Depends(get_db)):
    labels = list(dict.fromkeys(body.labels))
    if body.feature not in AI_FEATURES or not labels or any(lb not in AI_NOTICE_LABELS for lb in labels):
        raise HTTPException(status_code=422, detail="Unknown feature or category label.")
    await db.ai_send_anyway_log.insert_one({
        "user_id": current.user_id,
        "at": datetime.now(timezone.utc).isoformat(),
        "notice_version": AI_NOTICE_VERSION,
        "feature": body.feature,
        "labels": labels,
    })
    return {"ok": True}
