"""Server-side legal-acknowledgment audit trail.

Captures who acknowledged the legal disclaimer and when. The frontend modal
still gates the UI client-side via localStorage; this is the durable
audit record for compliance / liability defense.

Records the ack version, the user's IP + user-agent (best-effort, useful for
liability defense), and the user_id if signed in (guest sessions still get
their guest user_id recorded).

Endpoints:
  - POST /api/legal/acknowledge         (any auth — including guests)
  - GET  /api/legal/admin/acks          (admin only — recent acks + counts)
  - GET  /api/legal/admin/acks.csv      (admin only — CSV export)
"""
import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from analytics_routes import require_admin
from auth import get_current_user, get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import UserPublic


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/legal", tags=["legal"])

CURRENT_VERSION = "v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client_ip(request: Request) -> Optional[str]:
    """Honor x-forwarded-for when behind ingress, fall back to client.host."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # First entry is the original client.
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


class AckRequest(BaseModel):
    version: str = Field(default=CURRENT_VERSION, max_length=24)


@router.post("/acknowledge")
async def acknowledge_legal(
    request: Request,
    body: AckRequest,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Record a legal acknowledgment for the signed-in user (incl. guest).
    Idempotent per (user_id, version): re-acking just refreshes the row."""
    now = _now_iso()
    user_agent = (request.headers.get("user-agent") or "")[:512]
    payload = {
        "ack_id": f"ack_{uuid.uuid4().hex[:12]}",
        "user_id": current.user_id,
        "email": current.email,
        "name": current.name or "",
        "is_guest": bool(current.is_guest),
        "version": (body.version or CURRENT_VERSION)[:24],
        "ip": _client_ip(request),
        "user_agent": user_agent,
        "acknowledged_at": now,
    }
    # Upsert by (user_id, version) so a refresh doesn't bloat the table.
    await db.legal_acknowledgments.update_one(
        {"user_id": current.user_id, "version": payload["version"]},
        {
            "$set": {
                "email": payload["email"],
                "name": payload["name"],
                "is_guest": payload["is_guest"],
                "ip": payload["ip"],
                "user_agent": payload["user_agent"],
                "acknowledged_at": now,
            },
            "$setOnInsert": {
                "ack_id": payload["ack_id"],
                "user_id": payload["user_id"],
                "version": payload["version"],
                "first_acknowledged_at": now,
            },
        },
        upsert=True,
    )
    return {"ok": True, "acknowledged_at": now, "version": payload["version"]}


@router.get("/admin/acks")
async def admin_list_acks(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
    limit: int = 200,
):
    db = request.app.state.db
    limit = max(1, min(limit, 500))
    cursor = db.legal_acknowledgments.find({}, {"_id": 0}).sort(
        "acknowledged_at", -1
    ).limit(limit)
    rows = await cursor.to_list(limit)
    total = await db.legal_acknowledgments.count_documents({})
    guests = sum(1 for r in rows if r.get("is_guest"))
    return {
        "total": total,
        "shown": len(rows),
        "guests_in_shown": guests,
        "current_version": CURRENT_VERSION,
        "rows": rows,
    }


@router.get("/admin/acks.csv")
async def admin_export_acks_csv(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    db = request.app.state.db
    cursor = db.legal_acknowledgments.find({}, {"_id": 0}).sort("acknowledged_at", -1)
    rows = await cursor.to_list(5000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "acknowledged_at",
        "first_acknowledged_at",
        "user_id",
        "email",
        "name",
        "is_guest",
        "version",
        "ip",
        "user_agent",
    ])
    for r in rows:
        writer.writerow([
            r.get("acknowledged_at") or "",
            r.get("first_acknowledged_at") or r.get("acknowledged_at") or "",
            r.get("user_id") or "",
            r.get("email") or "",
            r.get("name") or "",
            "yes" if r.get("is_guest") else "no",
            r.get("version") or "",
            r.get("ip") or "",
            r.get("user_agent") or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="legal-acknowledgments.csv"'
        },
    )
