"""SAFE-ND(TM) Functional Map — staff-only practitioner reviews (owner 2026-10-24).

SAFE-ND(TM) (c) Trisha Wright, www.atipcommunity.com. Used with permission. Content lives in the frontend data file.
Access: signed-in professional or admin only. Parents and judges: 403. Review contents are AES-256-GCM encrypted at rest
(key derived from SAFE_ND_ENC_KEY) and never written to logs, error messages or the access record.
"""
import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, HTTPException, Request

from auth import get_current_user
from core import db, logger

router = APIRouter()
STAFF_ROLES = ("professional", "admin")
MAX_BYTES = 500 * 1024
COLLECTION = "safe_nd_reviews"
ACCESS_COLLECTION = "safe_nd_access"


def _key() -> bytes:
    raw = os.environ.get("SAFE_ND_ENC_KEY", "")
    if len(raw) < 16:
        raise HTTPException(status_code=503, detail="SAFE-ND reviews are not configured on this server")
    return hashlib.sha256(raw.encode()).digest()


def _encrypt(data: dict) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_key()).encrypt(nonce, json.dumps(data, ensure_ascii=False).encode(), b"safe-nd")
    return base64.b64encode(nonce + ct).decode()


def _decrypt(blob: str) -> dict:
    raw = base64.b64decode(blob)
    try:
        return json.loads(AESGCM(_key()).decrypt(raw[:12], raw[12:], b"safe-nd"))
    except InvalidTag:
        raise HTTPException(status_code=503, detail="This review cannot be opened with the current encryption key")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _staff(user=Depends(get_current_user)) -> dict:
    if user.get("role") not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff sign-in required")
    return user


async def _record(review_id: str, user: dict, action: str) -> None:
    await db[ACCESS_COLLECTION].insert_one({"review_id": review_id, "user_id": user["_id"], "role": user.get("role"), "action": action, "at": _now()})


async def _read_data(request: Request) -> dict:
    if "application/json" not in (request.headers.get("content-type") or ""):
        raise HTTPException(status_code=415, detail="JSON only")
    body = await request.body()
    if len(body) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Review too large (max 500 KB)")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="'data' must be an object")
    return data


async def _load(review_id: str) -> dict:
    doc = await db[COLLECTION].find_one({"id": review_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Review not found")
    return doc


def _case_fields(data: dict) -> tuple[str, str]:
    case = data.get("case") if isinstance(data.get("case"), dict) else {}
    return str(case.get("child") or ""), str(case.get("reviewDate") or "")


@router.get("/safe-nd/reviews")
async def list_reviews(user=Depends(_staff)):
    out = []
    async for d in db[COLLECTION].find({}, {"_id": 0, "id": 1, "status": 1, "updated_at": 1, "data_enc": 1}).sort("updated_at", -1):
        try:
            child, review_date = _case_fields(_decrypt(d["data_enc"]))
        except HTTPException:
            child, review_date = "", ""
        out.append({"id": d["id"], "child": child, "reviewDate": review_date, "status": d["status"], "updatedAt": d["updated_at"]})
    return out


@router.get("/safe-nd/reviews/{review_id}")
async def get_review(review_id: str, user=Depends(_staff)):
    doc = await _load(review_id)
    data = _decrypt(doc["data_enc"])
    await _record(review_id, user, "opened")
    return {"id": doc["id"], "status": doc["status"], "data": data, "updatedAt": doc["updated_at"]}


@router.post("/safe-nd/reviews", status_code=201)
async def create_review(request: Request, user=Depends(_staff)):
    data = await _read_data(request)
    now = _now()
    review_id = str(uuid.uuid4())
    await db[COLLECTION].insert_one({"id": review_id, "status": "draft", "data_enc": _encrypt(data), "created_by": user["_id"], "created_at": now,
                                     "updated_at": now, "finalized_by": None, "finalized_at": None})
    await _record(review_id, user, "created")
    return {"id": review_id}


@router.put("/safe-nd/reviews/{review_id}")
async def update_review(review_id: str, request: Request, user=Depends(_staff)):
    doc = await _load(review_id)
    if doc["status"] == "final":
        raise HTTPException(status_code=409, detail="This review is final and cannot be edited")
    data = await _read_data(request)
    await db[COLLECTION].update_one({"id": review_id, "status": "draft"}, {"$set": {"data_enc": _encrypt(data), "updated_at": _now()}})
    await _record(review_id, user, "saved")
    return {"ok": True}


@router.post("/safe-nd/reviews/{review_id}/finalize")
async def finalize_review(review_id: str, user=Depends(_staff)):
    doc = await _load(review_id)
    if doc["status"] == "final":
        raise HTTPException(status_code=409, detail="This review is already final")
    disposition = (_decrypt(doc["data_enc"]).get("disposition") or {})
    if not str(disposition.get("signature") or "").strip() or not disposition.get("signedDate"):
        raise HTTPException(status_code=400, detail="Reviewer signature and date are required before finalizing")
    now = _now()
    await db[COLLECTION].update_one({"id": review_id, "status": "draft"}, {"$set": {"status": "final", "finalized_by": user["_id"], "finalized_at": now, "updated_at": now}})
    await _record(review_id, user, "finalized")
    return {"ok": True}


@router.delete("/safe-nd/reviews/{review_id}")
async def delete_review(review_id: str, user=Depends(_staff)):
    """Legal/compliance deletion only: SA CoParents administrators."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only an administrator can delete a review")
    await _load(review_id)
    await db[COLLECTION].delete_one({"id": review_id})
    await _record(review_id, user, "deleted")
    logger.info("SAFE-ND review %s deleted by admin", review_id)
    return {"ok": True}
