"""Safety Gate HTTP surface.

POST /api/internal/safety-status     signed server-to-server update from SACOparentsAlign (not in API docs)
GET  /api/case-settings              resolved feature flags + plain-language settings (same bytes for both parents)
GET  /api/support/case-settings/{id} support staff: current mode only
GET  /api/admin/safety-audit-log/export  admins only; every export is logged
GET  /api/admin/safety-audit-log/daily-counts  admins only; counts per day, no case details
GET  /api/admin/safety-audit-log/align-status  admins only; last Align update and refused attempts, no case details
Signed bodies with "test": true are link tests only (see align_ping.py) and never change a case.
"""
import csv
import hashlib
import hmac
import io
import json
import logging
import re
import os
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from pymongo.errors import DuplicateKeyError

import case_safety as cs
from align_ref import backfill_align_refs, missing_align_refs
from analytics_routes import ADMIN_EMAILS, require_admin
from auth import get_current_user, get_db
from held_emails import held_counts
from models import UserPublic

logger = logging.getLogger(__name__)
router = APIRouter(tags=["case-settings"])
internal_router = APIRouter(include_in_schema=False)

MAX_AGE_SECONDS = 300
SIGNATURE_HEADER = "X-Align-Signature"
NO_STORE = {"Cache-Control": "no-store"}
THANKS = "family_checkin_thanks"
REMINDER = "family_checkin_reminder"
WEEK = timedelta(days=7)
SUPPORT_EMAILS = {e.strip().lower() for e in os.environ["SUPPORT_EMAILS"].split(",") if e.strip()}


class SafetyStatusIn(BaseModel):
    case_id: str = Field(min_length=1, max_length=64)
    safety_mode: Literal["standard", "structured", "restricted"]
    set_by: Literal["default", "auto_red", "professional"]
    professional_name: Optional[str] = Field(default=None, max_length=200)
    referral: Literal["none", "parallel_parenting"]
    screening_offered: bool
    version: int = Field(ge=1)
    timestamp: Union[int, float, str]
    note_review: bool = False


class TestPingIn(BaseModel):
    test: Literal[True]
    test_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    timestamp: Union[int, float, str]


def _is_test(raw: bytes) -> bool:
    try:
        parsed = json.loads(raw)
    except ValueError:
        return False
    return isinstance(parsed, dict) and parsed.get("test") is True


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Unauthorized.")


def _signature_ok(raw: bytes, provided: str) -> bool:
    secret = os.environ.get("ALIGN_WEBHOOK_SECRET")
    if not secret:
        logger.error("ALIGN_WEBHOOK_SECRET is not set; refusing safety-status request")
        return False
    provided = (provided or "").strip()
    if provided.startswith("sha256="):
        provided = provided[7:]
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return bool(provided) and hmac.compare_digest(expected, provided.lower())


def _fresh(ts: Union[int, float, str]) -> bool:
    """Unix seconds or milliseconds (number or digits in quotes), or an ISO date with a timezone; within 5 minutes."""
    if isinstance(ts, bool):
        return False
    try:
        if isinstance(ts, str) and re.fullmatch(r"\d+(\.\d+)?", ts.strip()):
            ts = float(ts)
        if isinstance(ts, (int, float)):
            at = datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts, tz=timezone.utc)
        else:
            at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if at.tzinfo is None:
                return False
    except (ValueError, OverflowError, OSError):
        return False
    return abs((datetime.now(timezone.utc) - at).total_seconds()) <= MAX_AGE_SECONDS


@internal_router.post("/internal/safety-status")
async def receive_safety_status(request: Request, db=Depends(get_db)):
    if not os.environ.get("ALIGN_WEBHOOK_SECRET"):
        # Webhook is off until a secret is set; nothing is read or changed.
        await cs.record_reject(db, "webhook_off")
        raise HTTPException(status_code=503, detail="Unavailable.")
    raw = await request.body()
    if not _signature_ok(raw, request.headers.get(SIGNATURE_HEADER, "")):
        await cs.record_reject(db, "bad_signature")
        raise _unauthorized()
    return await handle_signed(db, raw)


async def handle_signed(db, raw: bytes) -> dict:
    """Everything after the signature check. Automatic restrictions and unnamed professional changes are refused and logged."""
    is_test = _is_test(raw)
    try:
        body = (TestPingIn if is_test else SafetyStatusIn).model_validate_json(raw)
    except ValidationError:
        await cs.record_reject(db, "invalid_body")
        raise HTTPException(status_code=422, detail="Invalid body.")
    if not _fresh(body.timestamp):
        await cs.record_reject(db, "old_timestamp")
        raise _unauthorized()
    if not is_test and body.set_by == "auto_red":
        await cs.record_reject(db, "auto_red_refused")
        raise HTTPException(status_code=422, detail="Automatic restrictions are not accepted.")
    if not is_test and body.set_by == "professional" and not (body.professional_name or "").strip():
        await cs.record_reject(db, "no_professional_name")
        raise HTTPException(status_code=422, detail="A professional's name is required.")
    try:
        await db[cs.SEEN].insert_one({"_id": hashlib.sha256(raw).hexdigest(), "seen_at": datetime.now(timezone.utc)})
    except DuplicateKeyError:
        await cs.record_reject(db, "replay")
        raise HTTPException(status_code=409, detail="Replayed request.")
    if is_test:
        await cs.record_test(db, body.test_id)
        return {"ok": True}
    await cs.apply_update(db, body.model_dump())
    return {"ok": True}


@router.get("/case-settings")
async def case_settings(case_id: Optional[str] = None, current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    ids = await cs.case_ids_for(db, current.user_id)
    if case_id is not None:
        if case_id not in ids:
            raise HTTPException(status_code=404, detail="Not found.")
        ids = [case_id]
    resolved = [await cs.resolved_for_case(db, c, "user", current.user_id) for c in ids]
    return JSONResponse(cs.payload(cs.combine(resolved)), headers=NO_STORE)

# The shared case code for the Align check-in link (same for both parents); the first unfinished case if there are several.
@router.get("/family-checkin/link")
async def checkin_link(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    ids = await cs.case_ids_for(db, current.user_id)
    done = {c: (await cs.resolved_for_case(db, c, "user", current.user_id))["setup_complete"] for c in ids}
    pick = next((c for c in ids if not done[c]), ids[0] if ids else None)
    return JSONResponse({"case_id": pick}, headers=NO_STORE)


# Gentle in-card reminder: a week after the case was linked and still not done; a close hides it for another week.
@router.get("/family-checkin/reminder")
async def checkin_reminder(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    linked = await cs.linked_at_for(db, current.user_id)
    show = linked is not None and now - linked >= WEEK
    if show:
        hid = await db[REMINDER].find_one({"user_id": current.user_id}, {"_id": 0, "dismissed_at": 1})
        show = not hid or now - cs.as_utc(hid["dismissed_at"]) >= WEEK
    if show:
        show = not await cs.setup_complete_for(db, current.user_id)
    return JSONResponse({"show": show}, headers=NO_STORE)


@router.post("/family-checkin/reminder/dismiss")
async def checkin_reminder_dismiss(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    await db[REMINDER].update_one({"user_id": current.user_id},
                                  {"$set": {"user_id": current.user_id, "dismissed_at": cs.now_iso()}}, upsert=True)
    return {"ok": True}


# Admin-only, run by hand after a database backup: fills align_ref where missing (never changes an existing one).
@router.get("/admin/align-refs")
async def align_refs_status(_: UserPublic = Depends(require_admin), db=Depends(get_db)):
    return JSONResponse(await missing_align_refs(db), headers=NO_STORE)


@router.post("/admin/align-refs/backfill")
async def align_refs_backfill(admin: UserPublic = Depends(require_admin), db=Depends(get_db)):
    done = await backfill_align_refs(db)
    logger.info("align_ref backfill run by admin %s: %s", admin.user_id, done)
    return JSONResponse({**done, **await missing_align_refs(db)}, headers=NO_STORE)


# One-time "Thanks, your check-in is done" note, per parent account. Only a seen time is stored.
@router.get("/family-checkin/thanks")
async def checkin_thanks(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    if await db[THANKS].find_one({"user_id": current.user_id}, {"_id": 1}):
        return JSONResponse({"show": False}, headers=NO_STORE)
    return JSONResponse({"show": await cs.setup_complete_for(db, current.user_id)}, headers=NO_STORE)


@router.post("/family-checkin/thanks/seen")
async def checkin_thanks_seen(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    await db[THANKS].update_one({"user_id": current.user_id},
                                {"$setOnInsert": {"user_id": current.user_id, "seen_at": cs.now_iso()}}, upsert=True)
    return {"ok": True}




def require_support(current: UserPublic = Depends(get_current_user)) -> UserPublic:
    email = (current.email or "").lower()
    if current.is_guest or (email not in SUPPORT_EMAILS and email not in ADMIN_EMAILS):
        raise HTTPException(status_code=403, detail="Support access required.")
    return current


@router.get("/support/case-settings/{case_id}")
async def support_case_settings(case_id: str, current: UserPublic = Depends(require_support), db=Depends(get_db)):
    res = await cs.resolved_for_case(db, case_id, "support", current.user_id)
    return JSONResponse({"case_id": case_id, "safety_mode": res["mode"]}, headers=NO_STORE)


@router.get("/admin/safety-audit-log/export")
async def export_safety_audit_log(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    await cs.audit(db, "admin", current.user_id, "export", None)
    buf = io.StringIO()
    out = csv.writer(buf)
    out.writerow(["at", "actor_type", "actor_id", "action", "case_id"])
    async for row in db[cs.AUDIT].find({}, {"_id": 0}).sort("at", 1):
        out.writerow([row.get("at"), row.get("actor_type"), row.get("actor_id"), row.get("action"), row.get("case_id") or ""])
    headers = {**NO_STORE, "Content-Disposition": 'attachment; filename="safety_audit_log.csv"'}
    return Response(buf.getvalue(), media_type="text/csv", headers=headers)


COUNT_COLUMNS = {
    "write": "applied",
    "write_ignored_stale_version": "ignored",
    "write_ignored_until_professional": "ignored",
    "write_refused": "ignored",
    "export": "downloads",
}


@router.get("/admin/safety-audit-log/daily-counts")
async def safety_daily_counts(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    """Counts only, per UTC day for the last 30 days. No case IDs or details."""
    await cs.audit(db, "admin", current.user_id, "view_daily_counts", None)
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(30)]
    rows = {d: {"date": d, "applied": 0, "ignored": 0, "downloads": 0, "rejected": 0} for d in days}
    pipeline = [
        {"$match": {"at": {"$gte": days[-1]}, "action": {"$in": list(COUNT_COLUMNS)}}},
        {"$group": {"_id": {"day": {"$substrBytes": ["$at", 0, 10]}, "action": "$action"}, "n": {"$sum": 1}}},
    ]
    async for g in db[cs.AUDIT].aggregate(pipeline):
        day = rows.get(g["_id"]["day"])
        if day:
            day[COUNT_COLUMNS[g["_id"]["action"]]] += g["n"]
    by_day = [{"$match": {"at": {"$gte": days[-1]}}}, {"$group": {"_id": {"$substrBytes": ["$at", 0, 10]}, "n": {"$sum": 1}}}]
    async for g in db[cs.REJECTS].aggregate(by_day):
        if g["_id"] in rows:
            rows[g["_id"]]["rejected"] = g["n"]
    return JSONResponse({"days": [rows[d] for d in days]}, headers=NO_STORE)


APPLIED_ACTIONS = ["write", "write_ignored_stale_version", "write_ignored_until_professional"]
REJECT_REASONS = ("bad_signature", "old_timestamp", "invalid_body", "replay", "webhook_off", "auto_red_refused", "no_professional_name")


@router.get("/admin/safety-audit-log/align-status")
async def align_status(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    """Whether Align's updates are arriving. Times, results and refusal reasons only."""
    await cs.audit(db, "admin", current.user_id, "view_align_status", None)
    since = (datetime.now(timezone.utc).date() - timedelta(days=29)).isoformat()
    last = await db[cs.AUDIT].find_one({"action": {"$in": APPLIED_ACTIONS}}, {"_id": 0, "at": 1, "action": 1}, sort=[("at", -1)])
    last_applied = await db[cs.AUDIT].find_one({"action": "write"}, {"_id": 0, "at": 1}, sort=[("at", -1)])
    last_reject = await db[cs.REJECTS].find_one({}, {"_id": 0, "at": 1, "reason": 1}, sort=[("at", -1)])
    last_test = await db[cs.TESTS].find_one(
        {"received_at": {"$exists": True}}, {"_id": 0, "received_at": 1, "source": 1, "round_trip_ms": 1}, sort=[("received_at", -1)]
    )
    totals = {r: 0 for r in REJECT_REASONS}
    async for g in db[cs.REJECTS].aggregate([{"$match": {"at": {"$gte": since}}}, {"$group": {"_id": "$reason", "n": {"$sum": 1}}}]):
        if g["_id"] in totals:
            totals[g["_id"]] = g["n"]
    return JSONResponse({
        "last_update": {"at": last["at"], "result": "applied" if last["action"] == "write" else "ignored"} if last else None,
        "last_applied_at": last_applied["at"] if last_applied else None,
        "last_rejected": last_reject,
        "rejected_30d": totals,
        "silence": cs.silence_status(last["at"] if last else None, datetime.now(timezone.utc)),
        "last_test": last_test,
        "webhook_on": bool(os.environ.get("ALIGN_WEBHOOK_SECRET")),
    }, headers=NO_STORE)


@router.get("/admin/safety-audit-log/auto-restricted")
async def auto_restricted(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    return JSONResponse({"count": await cs.count_auto_restricted(db)}, headers=NO_STORE)


@router.get("/admin/safety-audit-log/held-emails")
async def held_emails_count(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    """Reminder emails held back for safety in the last 30 days, by type. Counts only; under 5 shows as "fewer than 5"."""
    return JSONResponse(await held_counts(db), headers=NO_STORE)


@router.get("/admin/safety-audit-log/link-health")
async def link_health(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    """Green/amber for the admin menu dot. A yes/no only; not logged because it loads with every admin page."""
    now = datetime.now(timezone.utc)
    week = (now - timedelta(days=cs.SILENCE_DAYS)).isoformat()
    day = (now - timedelta(days=1)).isoformat()
    webhook_on = bool(os.environ.get("ALIGN_WEBHOOK_SECRET"))
    heard = bool(
        await db[cs.AUDIT].find_one({"action": {"$in": APPLIED_ACTIONS}, "at": {"$gte": week}}, {"_id": 1})
        or await db[cs.TESTS].find_one({"received_at": {"$gte": week}}, {"_id": 1})
    )
    refused = bool(await db[cs.REJECTS].find_one({"at": {"$gte": day}}, {"_id": 1}))
    return JSONResponse({"ok": webhook_on and heard and not refused}, headers=NO_STORE)

