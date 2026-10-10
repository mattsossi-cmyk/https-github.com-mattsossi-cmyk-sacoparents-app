"""Open securely-sent documents: one-time email code (or signed-in recipient), then download. Senders can cancel."""
from __future__ import annotations

import hmac
import mimetypes
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field

import email_service
from auth import JWT_ALGO, JWT_SECRET, UserPublic, get_current_user, get_db
from secure_docs import (
    CODE_MINUTES, FILES_BUCKET, MAX_CODE_ATTEMPTS, MAX_CODES_PER_HOUR, hash_value,
)

router = APIRouter(prefix="/secure-docs", tags=["secure-docs"])
GRANT_MINUTES = 30


class DocInfo(BaseModel):
    sender_name: str
    masked_email: str
    expires_at: str
    status: str
    file_count: int


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class FileOut(BaseModel):
    index: int
    name: str
    size: int


class SentDoc(BaseModel):
    doc_id: str
    recipient_email: str
    label: str
    created_at: str
    expires_at: str
    opened_at: Optional[str] = None
    status: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _status(doc: dict) -> str:
    if doc.get("revoked_at"):
        return "cancelled"
    if datetime.fromisoformat(doc["expires_at"]) <= _now():
        return "expired"
    return "ready"


def _mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


async def _by_token(db, token: str) -> dict:
    doc = await db.secure_documents.find_one({"token_hash": hash_value(token)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "This link isn't valid.")
    return doc


def _require_ready(doc: dict) -> None:
    status = _status(doc)
    if status == "cancelled":
        raise HTTPException(410, "The sender cancelled this document.")
    if status == "expired":
        raise HTTPException(410, "This link has expired. Ask the sender to send it again.")


async def _grant(db, doc: dict) -> dict:
    if not doc.get("opened_at"):
        await db.secure_documents.update_one({"doc_id": doc["doc_id"]}, {"$set": {"opened_at": _now().isoformat()}})
    exp = _now() + timedelta(minutes=GRANT_MINUTES)
    return {"grant": jwt.encode({"kind": "secure_doc", "did": doc["doc_id"], "exp": exp}, JWT_SECRET, algorithm=JWT_ALGO)}


def _check_grant(grant: str, doc: dict) -> None:
    try:
        data = jwt.decode(grant, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Please confirm your code again.")
    if data.get("kind") != "secure_doc" or data.get("did") != doc["doc_id"]:
        raise HTTPException(401, "Please confirm your code again.")


@router.get("/open/{token}", response_model=DocInfo)
async def doc_info(token: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await _by_token(db, token)
    return DocInfo(
        sender_name=doc["sender_name"], masked_email=_mask(doc["recipient_email"]),
        expires_at=doc["expires_at"], status=_status(doc), file_count=len(doc["files"]),
    )


@router.post("/open/{token}/code")
async def send_code(token: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await _by_token(db, token)
    _require_ready(doc)
    hour_ago = _now() - timedelta(hours=1)
    recent = [t for t in doc.get("code_sends", []) if datetime.fromisoformat(t) > hour_ago]
    if len(recent) >= MAX_CODES_PER_HOUR:
        raise HTTPException(429, "Too many codes asked for. Please try again in an hour.")
    code = f"{secrets.randbelow(10**6):06d}"
    await db.secure_documents.update_one({"doc_id": doc["doc_id"]}, {"$set": {
        "code_hash": hash_value(doc["doc_id"] + code),
        "code_expires_at": (_now() + timedelta(minutes=CODE_MINUTES)).isoformat(),
        "code_attempts": 0,
        "code_sends": recent + [_now().isoformat()],
    }})
    try:
        await run_in_threadpool(email_service.send_document_code, to_email=doc["recipient_email"], code=code)
    except (email_service.EmailNotConfigured, email_service.EmailSendError):
        raise HTTPException(503, "We couldn't send the code right now. Please try again in a moment.")
    return {"sent": True, "masked_email": _mask(doc["recipient_email"])}


@router.post("/open/{token}/verify")
async def verify_code(token: str, body: CodeIn, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await _by_token(db, token)
    _require_ready(doc)
    if not doc.get("code_hash") or datetime.fromisoformat(doc["code_expires_at"]) <= _now():
        raise HTTPException(400, "That code has expired. Ask for a new one.")
    if doc.get("code_attempts", 0) >= MAX_CODE_ATTEMPTS:
        raise HTTPException(429, "Too many tries. Ask for a new code.")
    if not hmac.compare_digest(hash_value(doc["doc_id"] + body.code), doc["code_hash"]):
        await db.secure_documents.update_one({"doc_id": doc["doc_id"]}, {"$inc": {"code_attempts": 1}})
        raise HTTPException(400, "That code isn't right. Check the email and try again.")
    await db.secure_documents.update_one({"doc_id": doc["doc_id"]}, {"$set": {"code_hash": None}})
    return await _grant(db, doc)


@router.post("/open/{token}/signed-in")
async def open_signed_in(token: str, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await _by_token(db, token)
    _require_ready(doc)
    if (user.email or "").strip().lower() != doc["recipient_email"]:
        raise HTTPException(403, "This document was sent to a different email address.")
    return await _grant(db, doc)


@router.get("/open/{token}/files", response_model=List[FileOut])
async def list_files(token: str, x_doc_grant: str = Header(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await _by_token(db, token)
    _require_ready(doc)
    _check_grant(x_doc_grant, doc)
    return [FileOut(index=i, name=f["name"], size=f["size"]) for i, f in enumerate(doc["files"])]


@router.get("/open/{token}/files/{index}")
async def download_file(token: str, index: int, x_doc_grant: str = Header(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await _by_token(db, token)
    _require_ready(doc)
    _check_grant(x_doc_grant, doc)
    if index < 0 or index >= len(doc["files"]):
        raise HTTPException(404, "File not found.")
    f = doc["files"][index]
    stream = await AsyncIOMotorGridFSBucket(db, bucket_name=FILES_BUCKET).open_download_stream(ObjectId(f["file_id"]))
    data = await stream.read()
    media = mimetypes.guess_type(f["name"])[0] or "application/octet-stream"
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{f["name"]}"', "Cache-Control": "no-store",
    })


@router.get("/sent", response_model=List[SentDoc])
async def sent_docs(user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db.secure_documents.find(
        {"sender_user_id": user.user_id},
        {"_id": 0, "files": 0, "token_hash": 0, "code_hash": 0},
    ).sort("created_at", -1).to_list(100)
    return [SentDoc(**{k: d.get(k) for k in SentDoc.model_fields if k != "status"}, status=_status(d)) for d in docs]


@router.post("/sent/{doc_id}/cancel")
async def cancel_doc(doc_id: str, user: UserPublic = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    res = await db.secure_documents.update_one(
        {"doc_id": doc_id, "sender_user_id": user.user_id, "revoked_at": None},
        {"$set": {"revoked_at": _now().isoformat()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Document not found or already cancelled.")
    return {"cancelled": True}
