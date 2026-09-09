"""Per-user email delivery status for parent-facing reports.

Tracks the last successful email send per (user_id, report_type)
in the `report_deliveries` collection so the frontend can render
a "✓ Sent to X · 2 min ago" badge next to each Email me button and
parents don't tap send twice.

Delivery records store:
    {
        "user_id": str,
        "report_type": str,          # foundation_statement | snc_report | edu_deep | med_deep | psych_deep
        "last_sent_at": datetime,    # UTC
        "last_sent_to": str,         # lowercased email
    }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user

REPORT_DELIVERIES_COLL = "report_deliveries"

REPORT_TYPES = (
    "foundation_statement",
    "snc_report",
    "edu_deep",
    "med_deep",
    "psych_deep",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def record_email_delivery(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    report_type: str,
    to_email: str,
) -> None:
    """Best-effort write of a delivery receipt. Never crashes the
    caller's email dispatch — swallowed on error since the parent
    already got the email."""
    if not user_id or not report_type or not to_email:
        return
    if report_type not in REPORT_TYPES:
        return
    try:
        await db[REPORT_DELIVERIES_COLL].update_one(
            {"user_id": user_id, "report_type": report_type},
            {"$set": {
                "user_id": user_id,
                "report_type": report_type,
                "last_sent_at": _now(),
                "last_sent_to": (to_email or "").strip().lower(),
            }},
            upsert=True,
        )
    except Exception:  # noqa: BLE001 — never crash the caller
        return


router = APIRouter()


@router.get("/report-deliveries")
async def list_my_report_deliveries(
    request: Request,
    current: UserPublic = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the caller's delivery status for each report_type.

    Shape:
        {
          "foundation_statement": {last_sent_at, last_sent_to} | null,
          "snc_report": ...
          ...
        }
    """
    db: AsyncIOMotorDatabase = request.app.state.db
    cursor = db[REPORT_DELIVERIES_COLL].find(
        {"user_id": current.user_id},
        {"_id": 0, "user_id": 0},
    )
    out: Dict[str, Optional[Dict[str, Any]]] = {rt: None for rt in REPORT_TYPES}
    async for row in cursor:
        rt = row.get("report_type")
        if rt in out:
            out[rt] = {
                "last_sent_at": _iso(row.get("last_sent_at")),
                "last_sent_to": row.get("last_sent_to"),
            }
    return out
