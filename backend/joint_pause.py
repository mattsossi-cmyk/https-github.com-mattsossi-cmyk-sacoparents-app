"""Pause / resume joint features for one case — professional decides, nothing automatic.

While paused: joint assessment responses, joint report generation/view, shared alignment report PDF and joint invitations are blocked.
Each parent can still work individually (own assessment, private screening, safety hub). Parents never see why; they only see NEUTRAL_MESSAGE.
No email, SMS or notification is ever sent about a pause or resume.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

NEUTRAL_MESSAGE = "This step isn't available right now. Your professional will follow up."
BLOCKED_STATUS = 423


class PauseIn(BaseModel):
    paused: bool
    note: str = Field(default="", max_length=2000)


def is_joint_paused(doc: dict | None) -> bool:
    return bool((doc or {}).get("joint_paused"))


def assert_joint_open(doc: dict) -> None:
    """Raise the neutral block for parents when joint features are paused."""
    if is_joint_paused(doc):
        raise HTTPException(status_code=BLOCKED_STATUS, detail=NEUTRAL_MESSAGE)


def parent_view(doc: dict, is_pro: bool) -> dict:
    """What each role may learn about the pause: professionals get the record; parents get only the neutral flag."""
    if is_pro:
        return {"joint_paused": doc.get("joint_paused")}
    return {"joint_blocked": is_joint_paused(doc), "joint_blocked_message": NEUTRAL_MESSAGE if is_joint_paused(doc) else None}


def build_router(db, get_current_user, get_joint_report_doc, log_access) -> APIRouter:
    r = APIRouter()

    def _is_pro(doc, user):
        return user.get("role") == "admin" or user["_id"] in (doc.get("professional_id"), doc.get("created_by"))

    @r.put("/joint/reports/{rid}/joint-pause")
    async def set_joint_pause(rid: str, body: PauseIn, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if not _is_pro(doc, user):
            raise HTTPException(status_code=403, detail="Only the assigned professional can pause or resume joint features")
        now = datetime.now(timezone.utc).isoformat()
        note = body.note.strip()
        if body.paused:
            rec = {"by": user["_id"], "by_name": user.get("name", ""), "at": now, "note": note}
            await db.joint_reports.update_one({"id": rid}, {"$set": {"joint_paused": rec}, "$push": {"joint_pause_history": {**rec, "action": "pause"}}})
            await log_access(doc, user, "Paused joint features" + (f" — note: {note}" if note else ""), "joint_pause")
        else:
            rec = {"by": user["_id"], "by_name": user.get("name", ""), "at": now, "note": note, "action": "resume"}
            await db.joint_reports.update_one({"id": rid}, {"$set": {"joint_paused": None}, "$push": {"joint_pause_history": rec}})
            await log_access(doc, user, "Resumed joint features" + (f" — note: {note}" if note else ""), "joint_pause")
        fresh = await db.joint_reports.find_one({"id": rid}, {"_id": 0, "joint_paused": 1, "joint_pause_history": 1})
        return {"joint_paused": fresh.get("joint_paused"), "history": fresh.get("joint_pause_history") or []}

    return r
