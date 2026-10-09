"""Privacy Notification — shown on first sign-in and whenever PRIVACY_NOTICE_VERSION changes. Acceptance stored per user with timestamp + version."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

PRIVACY_NOTICE_VERSION = "2026-10-09.1"
SUBHEAD = "Private by Default. Shared by Choice."  # PENDING user decision — single string, easy to change
NOTICE = {
    "version": PRIVACY_NOTICE_VERSION,
    "tagline": "Start with Safety",
    "title": "Your Privacy Matters",
    "subhead": SUBHEAD,
    "intro": "Your preparation is private and under your control.",
    "points": [
        {"heading": "Your individual answers remain private.", "body": "Your co-parent does not automatically see your assessments, personal reflections, or journal entries."},
        {"heading": "You control what you share.", "body": "In the Self Journey, you choose which completed reports to share and with whom. Separate consent rules apply to joint and court-ordered participation."},
        {"heading": "Reports are different from raw answers.", "body": "Sharing a selected report does not automatically provide access to your entire account or private journal."},
        {"heading": "Safety comes first.", "body": "Family violence and communication safety concerns may require separate participation and additional safeguards."},
        {"heading": "Professionals and courts receive the information you authorize, or what the law or a court order requires.", "body": "Assigned professionals may see individual screening answers."},
    ],
    "legal_heading": "Important Legal Notice",
    "legal": "Using SA CoParents does not automatically create an attorney-client, therapist-patient, or other legally privileged relationship. Information may be subject to lawful disclosure requirements.",
    "checkbox": "I have read and understand this privacy notification.",
    "continue": "Continue to SA CoParents",
    # Footer links intentionally absent until the Privacy Policy / Confidentiality / Sharing & Consent pages exist.
    "footer_links": [],
}


def needs_acceptance(user: dict) -> bool:
    acc = user.get("privacy_notice") or {}
    return acc.get("version") != PRIVACY_NOTICE_VERSION


class AcceptIn(BaseModel):
    version: str
    acknowledged: bool


def build_router(db, get_current_user) -> APIRouter:
    r = APIRouter()

    @r.get("/privacy-notice")
    async def get_notice(user=Depends(get_current_user)):
        full = await db.users.find_one({"_id": user["_id"]}, {"privacy_notice": 1})
        return {"notice": NOTICE, "needs_acceptance": needs_acceptance(full or {}), "accepted": (full or {}).get("privacy_notice")}

    @r.post("/privacy-notice/accept")
    async def accept(body: AcceptIn, user=Depends(get_current_user)):
        if not body.acknowledged:
            raise HTTPException(status_code=400, detail="Please confirm you have read the privacy notification")
        if body.version != PRIVACY_NOTICE_VERSION:
            raise HTTPException(status_code=409, detail="The privacy notification has been updated. Please review the current version.")
        rec = {"version": PRIVACY_NOTICE_VERSION, "accepted_at": datetime.now(timezone.utc).isoformat()}
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"privacy_notice": rec}, "$push": {"privacy_notice_history": rec}})
        return {"ok": True, **rec}

    return r
