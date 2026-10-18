"""Admin link tests between this app and SACOparentsAlign. No case data is sent or changed.

POST /api/admin/safety-audit-log/self-test          signs a test message and posts it to our own public webhook
POST /api/admin/safety-audit-log/align-ping         asks Align (ALIGN_PING_URL) to send a signed test message back
GET  /api/admin/safety-audit-log/test-status/{id}   whether that test message has arrived
"""
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse

import case_safety as cs
from analytics_routes import require_admin
from auth import get_db
from case_safety_routes import NO_STORE, SIGNATURE_HEADER
from models import UserPublic

router = APIRouter(prefix="/admin/safety-audit-log", tags=["case-settings"])

OUTBOUND_SIGNATURE_HEADER = "X-SACO-Signature"
PING_COOLDOWN_SECONDS = 15


def _sign(raw: bytes) -> str:
    return hmac.new(os.environ["ALIGN_WEBHOOK_SECRET"].encode(), raw, hashlib.sha256).hexdigest()


def _webhook_url() -> str:
    return f"{os.environ['PUBLIC_BACKEND_URL'].rstrip('/')}/api/internal/safety-status"


def _configured() -> bool:
    return bool(os.environ.get("ALIGN_WEBHOOK_SECRET") and os.environ.get("PUBLIC_BACKEND_URL"))


async def _new_test(db, prefix: str) -> str:
    test_id = f"{prefix}-{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    await db[cs.TESTS].insert_one({"_id": test_id, "requested_at": now.isoformat(), "created": now})
    return test_id


@router.post("/self-test")
async def self_test(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    await cs.audit(db, "admin", current.user_id, "self_test", None)
    if not _configured():
        return JSONResponse({"ok": False, "reason": "not_configured"}, headers=NO_STORE)
    test_id = await _new_test(db, "self")
    raw = json.dumps({"test": True, "test_id": test_id, "timestamp": int(time.time())}, separators=(",", ":")).encode()
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(_webhook_url(), content=raw, headers={"Content-Type": "application/json", SIGNATURE_HEADER: _sign(raw)})
    except httpx.HTTPError:
        return JSONResponse({"ok": False, "reason": "unreachable", "webhook_url": _webhook_url()}, headers=NO_STORE)
    took = round((time.monotonic() - started) * 1000)
    arrived = await db[cs.TESTS].find_one({"_id": test_id, "received_at": {"$exists": True}})
    reason = None if r.status_code == 200 and arrived else ("refused_signature" if r.status_code == 401 else "failed")
    return JSONResponse(
        {"ok": reason is None, "reason": reason, "status_code": r.status_code, "round_trip_ms": took, "webhook_url": _webhook_url()},
        headers=NO_STORE,
    )


@router.post("/align-ping")
async def align_ping(current: UserPublic = Depends(require_admin), db=Depends(get_db)):
    await cs.audit(db, "admin", current.user_id, "align_ping", None)
    url = (os.environ.get("ALIGN_PING_URL") or "").strip()
    if not url or not url.startswith("https://") or not _configured():
        return JSONResponse({"configured": False}, headers=NO_STORE)
    recent = datetime.now(timezone.utc) - timedelta(seconds=PING_COOLDOWN_SECONDS)
    if await db[cs.TESTS].find_one({"_id": {"$regex": "^align-"}, "created": {"$gte": recent}}):
        raise HTTPException(status_code=429, detail="Please wait a few seconds before asking again.")
    test_id = await _new_test(db, "align")
    raw = json.dumps(
        {"test_id": test_id, "timestamp": int(time.time()), "callback_url": _webhook_url()}, separators=(",", ":")
    ).encode()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, content=raw, headers={"Content-Type": "application/json", OUTBOUND_SIGNATURE_HEADER: _sign(raw)})
    except httpx.HTTPError:
        return JSONResponse({"configured": True, "accepted": False, "reason": "unreachable"}, headers=NO_STORE)
    accepted = 200 <= r.status_code < 300
    return JSONResponse({"configured": True, "accepted": accepted, "status_code": r.status_code, "test_id": test_id}, headers=NO_STORE)


@router.get("/test-status/{test_id}")
async def test_status(
    test_id: str = Path(max_length=80, pattern=r"^(self|align)-[a-f0-9]{32}$"),
    current: UserPublic = Depends(require_admin),
    db=Depends(get_db),
):
    doc = await db[cs.TESTS].find_one({"_id": test_id}, {"_id": 0, "received_at": 1, "round_trip_ms": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Unknown test.")
    return JSONResponse({"received": "received_at" in doc, **doc}, headers=NO_STORE)
