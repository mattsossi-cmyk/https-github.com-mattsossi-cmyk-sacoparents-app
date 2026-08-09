"""Public verification endpoint for Dispute Resolution Pathway Report PDFs.

Mirrors briefing_verify_routes.py exactly — same privacy stance, same
minimal public response shape. A row is written to `pathway_signatures`
whenever a pathway PDF is generated (download or email). A QR stamped
in the PDF footer resolves to a public URL:

    <preview>/verify/pathway/{sig_id}

The frontend page hits `GET /api/verify/pathway/{sig_id}` here to
confirm whether SA CoParents issued that pathway report.

PRIVACY: same as briefing verification — response is intentionally
minimal (issued yes/no + issue date + whether it was the single-parent
preview or the two-parent report). Never leaks the underlying pathway
recommendation, hard-lock reasons, or parent identities.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from motor.motor_asyncio import AsyncIOMotorDatabase


router = APIRouter(prefix="/verify/pathway", tags=["pathway-verify"])

COLLECTION = "pathway_signatures"


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


# ---------------------------------------------------------------------------
# Helper — called by pathway_report_routes when a PDF is generated.
# ---------------------------------------------------------------------------

def _public_base_url() -> str:
    import os
    return (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")


def build_verify_url(sig_id: str) -> str:
    base = _public_base_url()
    return f"{base}/verify/pathway/{sig_id}" if base else f"/verify/pathway/{sig_id}"


async def record_pathway_signature(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    is_dual_party: bool,
    share_id: Optional[str],
    snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Insert a new pathway signature row and return `{sig_id, verify_url}`.

    Snapshot is an internal-only dict — never returned to the public
    verify endpoint. We stash the primary pathway key + a boolean for
    whether a hard-lock fired so operators can reconstruct a disputed
    report without re-running the algorithm.
    """
    sig_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc)
    doc = {
        "sig_id":        sig_id,
        "user_id":       user_id,
        "is_dual_party": bool(is_dual_party),
        "share_id":      share_id or "",
        "generated_at":  now.isoformat(),
        "issued_on":     now.strftime("%Y-%m-%d"),   # UTC calendar date (public)
        "snapshot":      snapshot or {},              # internal audit only
    }
    await db[COLLECTION].insert_one(doc)
    return {"sig_id": sig_id, "verify_url": build_verify_url(sig_id)}


# ---------------------------------------------------------------------------
# Public verify endpoint.
# ---------------------------------------------------------------------------

@router.get("/{sig_id}")
async def verify_pathway(sig_id: str, request: Request):
    """Return whether the sig_id was issued by SA CoParents.

    Response shape (intentionally minimal):
        - `issued`        : bool
        - `issued_on`     : "YYYY-MM-DD" (UTC) when issued, else None
        - `is_dual_party` : bool — was this a single-parent preview
                            or a full 2-parent report?
        - `sig_id`        : echoed back for the UI
    Nothing else is exposed publicly.
    """
    if not sig_id or len(sig_id) > 32 or not all(
        c in "0123456789abcdefABCDEF" for c in sig_id
    ):
        return {
            "issued": False, "issued_on": None,
            "is_dual_party": False, "sig_id": sig_id,
        }

    db: AsyncIOMotorDatabase = request.app.state.db
    doc = await db[COLLECTION].find_one(
        {"sig_id": sig_id.lower()},
        {"_id": 0, "issued_on": 1, "is_dual_party": 1},
    )
    if not doc:
        return {
            "issued": False, "issued_on": None,
            "is_dual_party": False, "sig_id": sig_id,
        }
    return {
        "issued":        True,
        "issued_on":     doc.get("issued_on"),
        "is_dual_party": bool(doc.get("is_dual_party")),
        "sig_id":        sig_id,
    }
