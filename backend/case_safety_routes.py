"""Safety Gate HTTP surface.

POST /api/internal/safety-status     signed server-to-server update from SACOparentsAlign (not in API docs)
GET  /api/case-settings              resolved feature flags + plain-language settings (same bytes for both parents)
GET  /api/support/case-settings/{id} support staff: current mode only
GET  /api/admin/safety-audit-log/export  admins only; every export is logged
"""
import csv
import hashlib
import hmac
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from pymongo.errors import DuplicateKeyError

import case_safety as cs
from analytics_routes import ADMIN_EMAILS, require_admin
from auth import get_current_user, get_db
from models import UserPublic

logger = logging.getLogger(__name__)
router = APIRouter(tags=["case-settings"])
internal_router = APIRouter(include_in_schema=False)

MAX_AGE_SECONDS = 300
SIGNATURE_HEADER = "X-Align-Signature"
NO_STORE = {"Cache-Control": "no-store"}
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
    try:
        if isinstance(ts, (int, float)) and not isinstance(ts, bool):
            at = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            at = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if at.tzinfo is None:
                return False
    except (ValueError, OverflowError, OSError):
        return False
    return abs((datetime.now(timezone.utc) - at).total_seconds()) <= MAX_AGE_SECONDS


@internal_router.post("/internal/safety-status")
async def receive_safety_status(request: Request, db=Depends(get_db)):
    raw = await request.body()
    if not _signature_ok(raw, request.headers.get(SIGNATURE_HEADER, "")):
        raise _unauthorized()
    try:
        body = SafetyStatusIn.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid body.")
    if not _fresh(body.timestamp):
        raise _unauthorized()
    try:
        await db[cs.SEEN].insert_one({"_id": hashlib.sha256(raw).hexdigest(), "seen_at": datetime.now(timezone.utc)})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Replayed request.")
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
    "export": "downloads",
}


@router.get("/admin/safety-audit-log/daily-counts")
async def safety_daily_counts(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    """Counts only, per UTC day for the last 30 days. No case IDs or details."""
    await cs.audit(db, "admin", current.user_id, "view_daily_counts", None)
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(30)]
    rows = {d: {"date": d, "applied": 0, "ignored": 0, "downloads": 0} for d in days}
    pipeline = [
        {"$match": {"at": {"$gte": days[-1]}, "action": {"$in": list(COUNT_COLUMNS)}}},
        {"$group": {"_id": {"day": {"$substrBytes": ["$at", 0, 10]}, "action": "$action"}, "n": {"$sum": 1}}},
    ]
    async for g in db[cs.AUDIT].aggregate(pipeline):
        day = rows.get(g["_id"]["day"])
        if day:
            day[COUNT_COLUMNS[g["_id"]["action"]]] += g["n"]
    return JSONResponse({"days": [rows[d] for d in days]}, headers=NO_STORE)
