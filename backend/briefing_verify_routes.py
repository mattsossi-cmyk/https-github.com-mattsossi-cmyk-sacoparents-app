"""Public verification endpoint for Four-Dimension Briefing PDFs.

When a briefing is generated (download or email), a row is written to
`briefing_signatures` with a fresh `sig_id`. A tiny QR code stamped in
the PDF footer resolves to a public URL:

    <preview>/verify/briefing/{sig_id}

The frontend page hits `GET /api/verify/briefing/{sig_id}` here to
confirm whether SA CoParents issued that briefing.

PRIVACY: per product decision (protects survivors + keeps public
verify URL safe to share), the public response is intentionally
minimal — it only confirms *whether* the id was issued and the
UTC issue date. It never leaks scores, tiers, parent names, or the
recipient audience. The full snapshot is stored in Mongo for internal
audit / troubleshooting only.

Note: this is an operator-issued attestation ("we generated this PDF
here on this date"), not a byte-for-byte hash check. The parent
snapshot recorded here is what the mediator would visually compare
against the printed report if they wanted to escalate a suspected
edit — but that comparison is a support-side workflow, not a public
one.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from motor.motor_asyncio import AsyncIOMotorDatabase


router = APIRouter(prefix="/verify/briefing", tags=["briefing-verify"])

COLLECTION = "briefing_signatures"


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


# ---------------------------------------------------------------------------
# Helper — called by dimension_companion_routes when a briefing is generated.
# ---------------------------------------------------------------------------

def _public_base_url() -> str:
    import os
    return (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")


def build_verify_url(sig_id: str) -> str:
    base = _public_base_url()
    return f"{base}/verify/briefing/{sig_id}" if base else f"/verify/briefing/{sig_id}"


async def record_briefing_signature(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    parent_name: str,
    audience: str,
    snapshot: Dict[str, Any],
) -> Dict[str, str]:
    """Insert a new briefing signature row and return `{sig_id, verify_url}`.

    Snapshot is an internal-only dict — never returned to the public
    verify endpoint. Callers pass in the safety tier/level + companion
    tier labels + follow-through % so operators can reconstruct what
    was on the PDF if a mediator later disputes it.
    """
    sig_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc)
    doc = {
        "sig_id":       sig_id,
        "user_id":      user_id,
        "parent_name":  parent_name or "",
        "audience":     audience or "",
        "generated_at": now.isoformat(),
        "issued_on":    now.strftime("%Y-%m-%d"),   # UTC calendar date (public)
        "snapshot":     snapshot or {},              # internal audit only
    }
    await db[COLLECTION].insert_one(doc)
    return {"sig_id": sig_id, "verify_url": build_verify_url(sig_id)}


# ---------------------------------------------------------------------------
# Public verify endpoint.
# ---------------------------------------------------------------------------

@router.get("/{sig_id}")
async def verify_briefing(sig_id: str, request: Request):
    """Return whether the sig_id was issued by SA CoParents.

    Response shape is intentionally minimal:
        - `issued`   : bool
        - `issued_on`: "YYYY-MM-DD" (UTC) when issued, else None
        - `sig_id`   : echoed back for the UI
    Nothing else is exposed publicly.
    """
    # Basic shape check — hex, 16 chars.
    if not sig_id or len(sig_id) > 32 or not all(
        c in "0123456789abcdefABCDEF" for c in sig_id
    ):
        return {"issued": False, "issued_on": None, "sig_id": sig_id}

    db: AsyncIOMotorDatabase = request.app.state.db
    doc = await db[COLLECTION].find_one(
        {"sig_id": sig_id.lower()},
        {"_id": 0, "issued_on": 1},
    )
    if not doc:
        return {"issued": False, "issued_on": None, "sig_id": sig_id}
    return {
        "issued":    True,
        "issued_on": doc.get("issued_on"),
        "sig_id":    sig_id,
    }
