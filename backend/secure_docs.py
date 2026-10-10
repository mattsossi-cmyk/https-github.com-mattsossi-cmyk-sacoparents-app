"""Secure document drop: emails never carry files; recipients open them in the app with a one-time code."""
import contextvars
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import gridfs
from pymongo import MongoClient

EXPIRE_DAYS = 7
CODE_MINUTES = 10
MAX_CODE_ATTEMPTS = 5
MAX_CODES_PER_HOUR = 5
FILES_BUCKET = "secure_doc_files"

# Set per request by auth.get_current_user so email sends know who is sending.
sender_ctx: contextvars.ContextVar = contextvars.ContextVar("secure_doc_sender", default=None)
_db = None


def _sync_db():
    global _db
    if _db is None:
        client = MongoClient(os.environ["MONGO_URL"], maxPoolSize=4, serverSelectionTimeoutMS=5000)
        _db = client[os.environ["DB_NAME"]]
    return _db


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def set_sender(user, origin: Optional[str]) -> None:
    sender_ctx.set({
        "user_id": user.user_id,
        "name": user.name,
        "email": (user.email or "").strip().lower(),
        "origin": origin,
    })


def store(*, to_email: str, files: List[Tuple[str, bytes]], label: str) -> dict:
    """Save the files and return the link + details for the 'document waiting' email."""
    sender = sender_ctx.get() or {}
    db = _sync_db()
    fs = gridfs.GridFS(db, collection=FILES_BUCKET)
    token = secrets.token_urlsafe(32)
    recipient = to_email.strip().lower()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=EXPIRE_DAYS)
    sender_name = (sender.get("name") or "").strip() or "SA CoParents"
    db.secure_documents.insert_one({
        "doc_id": uuid.uuid4().hex,
        "token_hash": hash_value(token),
        "recipient_email": recipient,
        "sender_user_id": sender.get("user_id"),
        "sender_name": sender_name,
        "label": label,
        "files": [
            {"name": name, "file_id": fs.put(data, filename=name), "size": len(data)}
            for name, data in files
        ],
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "revoked_at": None,
        "opened_at": None,
        "code_hash": None,
        "code_expires_at": None,
        "code_attempts": 0,
        "code_sends": [],
    })
    base = (sender.get("origin") or os.environ["PUBLIC_APP_URL"]).rstrip("/")
    return {
        "url": f"{base}/doc/{token}",
        "sender_name": sender_name,
        "expires_at": expires,
        "is_self": bool(sender.get("email")) and sender.get("email") == recipient,
    }
