"""Privacy Notice consent: required to create an account and re-asked whenever the version changes.

No auth imports here so auth.py / invite_routes.py can use it without circular imports.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request

# The one place the Privacy Notice version lives. Bump it whenever /privacy-notice changes
# (tests/test_privacy_consent.py fails if the notice text changes without a bump).
PRIVACY_NOTICE_VERSION = "2026-10-19-v4"
PRIVACY_NOTICE_TEXT_SHA256 = "fb436b7c4dd2af2bab3d056e5752a2ea9259e5b175e91d621318f00eebb0dc99"
# Version of the first-visit "Just so we're on the same page" pop-up, recorded together with consent.
LEGAL_ACK_VERSION = "v1"

CONSENT_MISSING = (
    "Please tick both boxes: that you have read the Privacy Notice, and that you consent to "
    "SA CoParents storing the sensitive family information you choose to enter."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def consent_fields(ack_privacy_notice: Optional[bool], consent_sensitive_info: Optional[bool]) -> dict:
    """The four per-user fields. Raises 422 unless both boxes are ticked. Timestamp is server-set."""
    if ack_privacy_notice is not True or consent_sensitive_info is not True:
        raise HTTPException(status_code=422, detail=CONSENT_MISSING)
    return {
        "ack_privacy_notice": True,
        "consent_sensitive_info": True,
        "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        "consent_at": now_iso(),
    }


def has_current_consent(doc: dict) -> bool:
    return (
        doc.get("ack_privacy_notice") is True
        and doc.get("consent_sensitive_info") is True
        and doc.get("privacy_notice_version") == PRIVACY_NOTICE_VERSION
    )


def client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


async def upsert_legal_ack(db, user: dict, request: Optional[Request], version: str = LEGAL_ACK_VERSION) -> str:
    """Record the first-visit pop-up acknowledgement (idempotent per user + version)."""
    now = now_iso()
    await db.legal_acknowledgments.update_one(
        {"user_id": user["user_id"], "version": version},
        {
            "$set": {
                "email": user.get("email"),
                "name": user.get("name") or "",
                "is_guest": bool(user.get("is_guest")),
                "ip": client_ip(request),
                "user_agent": ((request.headers.get("user-agent") if request else "") or "")[:512],
                "acknowledged_at": now,
            },
            "$setOnInsert": {"ack_id": f"ack_{uuid.uuid4().hex[:12]}", "user_id": user["user_id"], "version": version, "first_acknowledged_at": now},
        },
        upsert=True,
    )
    return now


async def log_consent(db, user: dict, fields: dict, source: str, request: Optional[Request]) -> None:
    """Append-only consent history (survives version bumps) + the pop-up acknowledgement."""
    await db.privacy_consents.insert_one({"user_id": user["user_id"], **fields, "source": source})
    await upsert_legal_ack(db, user, request)
