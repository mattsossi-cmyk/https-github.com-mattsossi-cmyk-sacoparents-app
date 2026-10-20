"""Professional tools: a one-tap gentle nudge to one parent, and the completion-alert on/off preference.

The nudge names no assessment. It's never sent to safety-flagged parents or parents who turned reminders off, but the
professional always gets the same answer so neither state is revealed. Once every 7 days per parent per case.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import get_current_user, get_db
from court_checklist import REQUESTABLE, case_requested_keys, progress_rows
from models import UserPublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/professional", tags=["professional-tools"])

NUDGE_EVERY = timedelta(days=7)


def nudge_pid(ref: str, uid: str) -> str:
    """Opaque per-parent id for the UI, so user ids never leave the server."""
    return hashlib.sha256(f"nudge:{ref}:{uid}".encode()).hexdigest()[:12]


async def nudge_next_at(db: AsyncIOMotorDatabase, ref: str, uid: str) -> Optional[str]:
    last = await db.professional_nudges.find_one({"ref": ref, "user_id": uid}, {"_id": 0, "sent_at": 1}, sort=[("sent_at", -1)])
    if not last:
        return None
    nxt = datetime.fromisoformat(last["sent_at"]) + NUDGE_EVERY
    return nxt.isoformat() if nxt > datetime.now(timezone.utc) else None


async def nudge_info(db: AsyncIOMotorDatabase, ref: str, uid: str) -> Dict[str, Any]:
    """Per-parent nudge history for the professional's cards (suppressed nudges count too, so nothing is revealed)."""
    last = await db.professional_nudges.find_one({"ref": ref, "user_id": uid}, {"_id": 0, "sent_at": 1}, sort=[("sent_at", -1)])
    return {
        "nudge_next_at": await nudge_next_at(db, ref, uid) if last else None,
        "nudge_last_at": last["sent_at"] if last else None,
        "nudge_count": await db.professional_nudges.count_documents({"ref": ref, "user_id": uid}) if last else 0,
    }


async def _owned(db: AsyncIOMotorDatabase, ref: str, pro_uid: str) -> Tuple[List[str], List[str]]:
    """(parent user ids, requested keys) for a court code or joint case this professional created."""
    kd = await db.portal_court_keys.find_one({"case_id": ref, "created_by": pro_uid}, {"_id": 0, "requested": 1})
    if kd:
        uids = await db.portal_state.distinct("user_id", {"court_key": ref})
        return uids, [k for k in REQUESTABLE if k in (kd.get("requested") or [])]
    case = await db.joint_alignment_cases.find_one({"case_id": ref, "professional_created_by": pro_uid}, {"_id": 0})
    if case:
        return [p["user_id"] for p in case.get("parents") or [] if p.get("user_id")], case_requested_keys(case)
    raise HTTPException(status_code=404, detail="Case not found.")


class NudgeBody(BaseModel):
    ref: str = Field(..., min_length=1, max_length=80)
    pid: str = Field(..., min_length=6, max_length=40)


@router.post("/nudges")
async def send_nudge(body: NudgeBody, user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    from email_service import EmailNotConfigured, EmailSendError, send_requested_reminder
    from requested_reminders import _links
    from held_emails import record_held
    from self_assessment_reminders import is_safety_flagged

    uids, keys = await _owned(db, body.ref, user.user_id)
    uid = next((u for u in uids if nudge_pid(body.ref, u) == body.pid), None)
    if not uid:
        raise HTTPException(status_code=404, detail="Parent not found on this case.")
    waiting = sum(r["status"] != "done" for r in await progress_rows(db, uid, keys))
    if not waiting:
        raise HTTPException(status_code=409, detail="This parent has already finished everything you asked for.")
    if await nudge_next_at(db, body.ref, uid):
        raise HTTPException(status_code=429, detail="You've nudged this parent in the last 7 days.")
    now = datetime.now(timezone.utc)
    status = "sent"
    req = await db.court_requested.find_one({"user_id": uid}, {"_id": 0, "reminders_off": 1}) or {}
    parent = await db.users.find_one({"user_id": uid}, {"_id": 0, "email": 1, "name": 1, "email_bounced": 1}) or {}
    if req.get("reminders_off"):
        status = "suppressed_unsubscribed"
    elif await is_safety_flagged(db, uid):
        status = "suppressed_safety"
        await record_held(db, "pro_nudge", uid, now.isoformat())
    elif not parent.get("email") or parent.get("email_bounced"):
        status = "suppressed_no_email"
    else:
        links = _links(uid)
        try:
            await asyncio.to_thread(send_requested_reminder, to_email=parent["email"], waiting=waiting, cta_url=links["cta"],
                                    unsubscribe_url=links["unsubscribe"], from_professional=True,
                                    first_name=(parent.get("name") or "").split(" ")[0] or None)
        except (EmailNotConfigured, EmailSendError) as exc:
            logger.warning("nudge send failed for %s: %s", body.ref, exc)
            raise HTTPException(status_code=502, detail="We couldn't send the nudge right now. Please try again shortly.")
    await db.professional_nudges.insert_one({"ref": body.ref, "user_id": uid, "pro_user_id": user.user_id,
                                             "status": status, "sent_at": now.isoformat()})
    # Same reply whatever happened, so a parent's safety flag or opt-out is never revealed.
    return {"ok": True, "next_at": (now + NUDGE_EVERY).isoformat()}


class AlertPrefBody(BaseModel):
    enabled: bool


async def _is_creator(db: AsyncIOMotorDatabase, uid: str) -> bool:
    return bool(await db.portal_court_keys.find_one({"created_by": uid}, {"_id": 1})
                or await db.joint_alignment_cases.find_one({"professional_created_by": uid}, {"_id": 1}))


@router.get("/completion-alerts")
async def get_alert_pref(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    pref = await db.professional_prefs.find_one({"user_id": user.user_id}, {"_id": 0, "completion_alerts_off": 1}) or {}
    return {"eligible": await _is_creator(db, user.user_id), "enabled": not pref.get("completion_alerts_off")}


@router.put("/completion-alerts")
async def put_alert_pref(body: AlertPrefBody, user: UserPublic = Depends(get_current_user),
                         db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    await db.professional_prefs.update_one({"user_id": user.user_id}, {"$set": {"completion_alerts_off": not body.enabled}}, upsert=True)
    return {"eligible": await _is_creator(db, user.user_id), "enabled": body.enabled}


class ArchiveBody(BaseModel):
    ref: str = Field(..., min_length=1, max_length=80)
    archived: bool


@router.put("/archive")
async def set_archived(body: ArchiveBody, user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Tidy My cases. Professional's view only: parents, reminders, alerts and PDFs are unaffected."""
    at = datetime.now(timezone.utc).isoformat() if body.archived else None
    res = await db.portal_court_keys.update_one({"case_id": body.ref, "created_by": user.user_id}, {"$set": {"archived_at": at}})
    if not res.matched_count:
        res = await db.joint_alignment_cases.update_one({"case_id": body.ref, "professional_created_by": user.user_id},
                                                        {"$set": {"professional_archived_at": at}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Case not found.")
    return {"ref": body.ref, "archived_at": at}


class FinishedBody(BaseModel):
    kind: Literal["codes", "cases"]


async def _finished_refs(db: AsyncIOMotorDatabase, uid: str, kind: str) -> List[str]:
    """Codes: revoked, expired, or every linked parent done. Cases: both complete, cancelled or expired."""
    from court_codes_routes import linked_parents
    from joint_alignment_routes import _derived_status

    now = datetime.now(timezone.utc).isoformat()
    refs = []
    if kind == "cases":
        async for case in db.joint_alignment_cases.find({"professional_created_by": uid, "professional_archived_at": None}, {"_id": 0}):
            if _derived_status(case) in ("both_complete", "cancelled", "expired"):
                refs.append(case["case_id"])
        return refs
    async for d in db.portal_court_keys.find({"created_by": uid, "archived_at": None},
                                             {"_id": 0, "case_id": 1, "requested": 1, "revoked_at": 1, "expires_at": 1}):
        if d.get("revoked_at") or (d.get("expires_at") and d["expires_at"] < now):
            refs.append(d["case_id"])
            continue
        parents = await linked_parents(db, d["case_id"], [k for k in REQUESTABLE if k in (d.get("requested") or [])])
        if parents and all(r["status"] == "done" for p in parents for r in p["assessments"]):
            refs.append(d["case_id"])
    return refs


@router.post("/archive/finished")
async def archive_finished(body: FinishedBody, user: UserPublic = Depends(get_current_user),
                           db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    refs = await _finished_refs(db, user.user_id, body.kind)
    if refs:
        await _bulk(db, user.user_id, refs, datetime.now(timezone.utc).isoformat())
    return {"refs": refs}


class BulkBody(BaseModel):
    refs: List[str] = Field(..., min_length=1, max_length=500)
    archived: bool


async def _bulk(db: AsyncIOMotorDatabase, uid: str, refs: List[str], at: Optional[str]) -> int:
    a = await db.portal_court_keys.update_many({"case_id": {"$in": refs}, "created_by": uid}, {"$set": {"archived_at": at}})
    b = await db.joint_alignment_cases.update_many({"case_id": {"$in": refs}, "professional_created_by": uid},
                                                   {"$set": {"professional_archived_at": at}})
    return a.matched_count + b.matched_count


@router.put("/archive/bulk")
async def archive_bulk(body: BulkBody, user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Used for Undo after "Archive finished"."""
    at = datetime.now(timezone.utc).isoformat() if body.archived else None
    return {"count": await _bulk(db, user.user_id, body.refs, at)}
