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

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field


router = APIRouter(prefix="/verify/pathway", tags=["pathway-verify"])

COLLECTION = "pathway_signatures"
COMMENTS_COLLECTION = "pathway_report_comments"


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


# ---------------------------------------------------------------------------
# Reviewer comments.
#
# A professional (mediator / PFAL / court / attorney / therapist) who
# scans the QR in a pathway report PDF lands on the public verify page
# and can leave a signed comment for the parent who sent it. Design
# principles:
#
#   * Public POST — no login required. The QR IS the ticket. Requiring
#     an SA CoParents account would kill the closed-loop workflow.
#   * Rate-limited by a salted IP hash so a single reviewer can't spam
#     one sig_id (30 comments/day cap per hash / sig_id combo).
#   * Comments are IMMUTABLE once posted. If a reviewer sends the
#     wrong text they need to post a follow-up correction — this makes
#     the artefact court-defensible.
#   * The PARENT who owns the sig_id sees these on their dashboard via
#     `GET /pathway-report/comments/mine` (see pathway_report_routes).
#     The verify page also shows previously-posted comments so a
#     second reviewer knows what the first said.
# ---------------------------------------------------------------------------

ReviewerRole = Literal[
    "mediator", "parent_facilitator_ad_litem", "trial_court",
    "attorney", "therapist", "other",
]


class ReviewerCommentBody(BaseModel):
    reviewer_name: str = Field(..., min_length=1, max_length=120)
    reviewer_role: ReviewerRole
    reviewer_org:  Optional[str] = Field(None, max_length=160)
    comment_text:  str = Field(..., min_length=4, max_length=4000)


def _hash_ip(request: Request) -> str:
    """Return a stable, non-reversible hash of the caller's IP. Used
    only for rate-limiting; not stored raw and not exposed publicly."""
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "")
        or "unknown"
    )
    salt = uuid.NAMESPACE_DNS.hex  # stable per-deploy — non-secret salt
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


async def _sig_row(db: AsyncIOMotorDatabase, sig_id: str) -> Optional[Dict[str, Any]]:
    if not sig_id or len(sig_id) > 32:
        return None
    if not all(c in "0123456789abcdefABCDEF" for c in sig_id):
        return None
    return await db[COLLECTION].find_one({"sig_id": sig_id.lower()})


def _public_comment(row: Dict[str, Any]) -> Dict[str, Any]:
    """Public projection — never exposes the IP hash."""
    return {
        "comment_id":    row.get("comment_id"),
        "reviewer_name": row.get("reviewer_name"),
        "reviewer_role": row.get("reviewer_role"),
        "reviewer_org":  row.get("reviewer_org") or "",
        "comment_text":  row.get("comment_text"),
        "created_at":    row.get("created_at"),
    }


@router.get("/{sig_id}/comments")
async def list_pathway_comments(sig_id: str, request: Request):
    """Return every reviewer comment left on this pathway report id.

    Public read — the sig_id is the ticket. Never leaks the poster's IP
    hash or the parent's identity. Newest-first ordering.
    """
    db: AsyncIOMotorDatabase = request.app.state.db
    sig = await _sig_row(db, sig_id)
    if not sig:
        # Same shape as a real response so the UI can render cleanly.
        return {"issued": False, "sig_id": sig_id, "comments": []}
    cursor = db[COMMENTS_COLLECTION].find(
        {"sig_id": sig_id.lower()}, {"_id": 0},
    ).sort("created_at", -1)
    rows = [_public_comment(r) async for r in cursor]
    return {"issued": True, "sig_id": sig_id, "comments": rows}


@router.post("/{sig_id}/comments")
async def post_pathway_comment(
    sig_id: str,
    body: ReviewerCommentBody,
    request: Request,
):
    """Attach a signed reviewer comment to an issued pathway report id.

    Refuses if:
        * sig_id is not on file (404)
        * IP hash has already posted more than 30 comments for this sig_id
          in the last 24h (429 — accidental resend / abuse guard)
    """
    db: AsyncIOMotorDatabase = request.app.state.db
    sig = await _sig_row(db, sig_id)
    if not sig:
        raise HTTPException(404, "This pathway report id is not on record.")

    ip_hash = _hash_ip(request)
    now = datetime.now(timezone.utc)
    # Rate-limit: count comments from this IP hash on this sig_id in the
    # last 24h. We use a plain ISO comparison because created_at is
    # stored as a fixed-width UTC ISO string.
    from datetime import timedelta
    cutoff_iso = (now - timedelta(days=1)).isoformat()
    recent = await db[COMMENTS_COLLECTION].count_documents({
        "sig_id":  sig_id.lower(),
        "ip_hash": ip_hash,
        "created_at": {"$gte": cutoff_iso},
    })
    if recent >= 30:
        raise HTTPException(
            429,
            "Too many comments from this location in the last day. "
            "Please try again later.",
        )

    comment_id = uuid.uuid4().hex[:16]
    doc = {
        "comment_id":     comment_id,
        "sig_id":         sig_id.lower(),
        "parent_user_id": sig.get("user_id"),   # who OWNS this pathway id
        "reviewer_name":  body.reviewer_name.strip(),
        "reviewer_role":  body.reviewer_role,
        "reviewer_org":   (body.reviewer_org or "").strip() or None,
        "comment_text":   body.comment_text.strip(),
        "ip_hash":        ip_hash,               # internal only
        "created_at":     now.isoformat(),
    }
    await db[COMMENTS_COLLECTION].insert_one(doc)
    return {"ok": True, "comment": _public_comment(doc)}


# ---------------------------------------------------------------------------
# Authenticated fetch — the parent who owns the sig_ids reads comments
# left on their reports. Bound here rather than in pathway_report_routes
# because the storage collection lives beside signatures.
# ---------------------------------------------------------------------------

async def list_comments_for_user(
    db: AsyncIOMotorDatabase, user_id: str, *, limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return newest-first comments left on any pathway report issued
    to this user. Used by pathway_report_routes for the dashboard card
    endpoint."""
    cursor = db[COMMENTS_COLLECTION].find(
        {"parent_user_id": user_id}, {"_id": 0},
    ).sort("created_at", -1).limit(limit)
    return [
        {**_public_comment(r), "sig_id": r.get("sig_id")}
        async for r in cursor
    ]
