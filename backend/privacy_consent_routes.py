"""Record Privacy Notice consent for a signed-in user (existing accounts, guests, Google sign-ins).

POST /api/privacy-consent           {ack_privacy_notice, consent_sensitive_info}
GET  /api/privacy-consent/version   public, current notice version
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from auth import get_current_user, get_db
from models import UserPublic
from privacy_consent import PRIVACY_NOTICE_VERSION, consent_fields, log_consent

router = APIRouter(prefix="/privacy-consent", tags=["privacy"])


class ConsentBody(BaseModel):
    ack_privacy_notice: bool = False
    consent_sensitive_info: bool = False


@router.get("/version")
async def consent_version():
    return {"version": PRIVACY_NOTICE_VERSION}


@router.post("")
async def record_consent(body: ConsentBody, request: Request, current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    fields = consent_fields(body.ack_privacy_notice, body.consent_sensitive_info)
    await db.users.update_one({"user_id": current.user_id}, {"$set": fields})
    await log_consent(db, current.dict(), fields, "gate", request)
    return {"ok": True, "version": fields["privacy_notice_version"], "consent_at": fields["consent_at"]}
