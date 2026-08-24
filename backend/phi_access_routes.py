"""PHI access logging + right-to-export / right-to-delete endpoints.

Voluntary HIPAA-alignment: SA CoParents is not a Covered Entity, but
we adopt the audit-log + individual-rights standards regardless.

  * `record_phi_access(...)` — appended to `phi_access_log` whenever a
    joint artefact, safety-lens finding, or SNC assessment is read or
    exported. Retained for 6 years (HIPAA §164.316(b)(2)(i)).
  * `GET  /api/me/export`         — full JSON export of the caller's
    data. HIPAA §164.524 "right of access".
  * `DELETE /api/me`              — wipes the caller's account and all
    associated records except the retained audit log (which is
    de-identified but kept for legal-hold reasons).
  * `GET  /api/me/access-log`     — the caller's own audit trail so
    they can see when their PHI-adjacent data was touched. HIPAA
    §164.528 "accounting of disclosures" — implemented as a
    self-serve endpoint rather than a written request.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user, get_db


router = APIRouter(prefix="/me", tags=["me"])


# Collections we consider PHI-adjacent. Deletion sweeps every one of them
# for the caller's user_id. Export reads every one. New collections that
# hold health-adjacent data MUST be added here.
_PHI_COLLECTIONS = (
    "prep_data",
    "child_goals",
    "reflections",
    "agreements",
    "safety_assessments",
    "snc2_assessments",
    "dimension_companion_assessments",
    "trauma_lens_findings",
    "readiness_snapshots",
    "compare_shares",
    "snc2_shares",
    "edu_deep_shares",
    "med_deep_shares",
    "psych_deep_shares",
    "joint_report_emails",
    "joint_agreement_emails",
    # Added post-audit (SEC-004): every remaining user_id-keyed
    # collection that carries PHI-adjacent or clinical-conversation data.
    "nd_assessments",
    "journal_entries",
    "journal_recaps",
    "summaries",
    "improvement_plans",
    "coach_messages",
    "coach_sessions",
    "next_steps",
    "problem_solving_worksheets",
    "cp_assessments",
    "post_summary_checkins",
    "mediator_emails",
    "pathway_report_comments",
    "devices",
    "legal_acknowledgments",
    "user_sessions",
)


async def record_phi_access(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    share_id: Optional[str] = None,
    request: Optional[Request] = None,
) -> None:
    """Append a single audit row. Never raises — audit failures must
    never block the primary request. Retention: 6 years (enforced by a
    Mongo TTL index created at first startup)."""
    try:
        row: Dict[str, Any] = {
            "user_id":       user_id,
            "action":        action,           # e.g. "read", "export", "email"
            "resource_type": resource_type,    # "joint_report" | "joint_agreement" | "safety_lens" | ...
            "resource_id":   resource_id,
            "share_id":      share_id,
            "at":            datetime.now(timezone.utc),
        }
        if request is not None:
            row["ip"] = request.client.host if request.client else None
            row["user_agent"] = request.headers.get("user-agent")
        await db.phi_access_log.insert_one(row)
    except Exception:
        # Deliberately swallow — audit-log durability is best-effort, we
        # never want a Mongo hiccup to break a user-facing endpoint.
        pass


@router.get("/export")
async def export_my_data(
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the caller's full dataset as JSON.

    Implements HIPAA §164.524 right-of-access. Includes account,
    every PHI-adjacent collection listed in `_PHI_COLLECTIONS`, and
    the caller's own access log so the audit trail travels with them.
    """
    out: Dict[str, Any] = {
        "user_id":     user.user_id,
        "email":       user.email,
        "name":        getattr(user, "name", None),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "collections": {},
    }
    for coll in _PHI_COLLECTIONS:
        rows = await db[coll].find(
            {"user_id": user.user_id}, {"_id": 0},
        ).to_list(length=None)
        out["collections"][coll] = rows
    # Include the caller's own access log entries.
    out["collections"]["phi_access_log"] = await db.phi_access_log.find(
        {"user_id": user.user_id}, {"_id": 0},
    ).to_list(length=None)
    await record_phi_access(
        db, user_id=user.user_id, action="export",
        resource_type="account_full", request=request,
    )
    return out


@router.delete("")
async def delete_my_account(
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Wipe the caller's account + every PHI-adjacent record.

    The `phi_access_log` collection is intentionally NOT wiped — the
    audit trail is legally protective for both the user and the
    platform. Rows are DE-IDENTIFIED (user_id replaced with a
    tombstone marker) so no linkable PHI remains.
    """
    tombstone_id = f"deleted_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    counts: Dict[str, int] = {}
    for coll in _PHI_COLLECTIONS:
        res = await db[coll].delete_many({"user_id": user.user_id})
        counts[coll] = res.deleted_count
    # De-identify audit log — do not delete.
    await db.phi_access_log.update_many(
        {"user_id": user.user_id},
        {"$set": {"user_id": tombstone_id, "deidentified_at": datetime.now(timezone.utc)}},
    )
    # Finally the account itself + any auth tokens.
    counts["users"] = (await db.users.delete_many({"user_id": user.user_id})).deleted_count
    counts["auth_tokens"] = (await db.auth_tokens.delete_many({"user_id": user.user_id})).deleted_count
    return {
        "ok":            True,
        "deleted_at":    datetime.now(timezone.utc).isoformat(),
        "tombstone_id":  tombstone_id,
        "record_counts": counts,
    }


@router.get("/access-log")
async def get_my_access_log(
    limit: int = 500,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the caller's own PHI-access audit rows.

    HIPAA §164.528 "accounting of disclosures" — implemented as a
    self-serve endpoint. Newest first, capped at 500 rows.
    """
    limit = max(1, min(500, int(limit)))
    rows: List[Dict[str, Any]] = await db.phi_access_log.find(
        {"user_id": user.user_id}, {"_id": 0},
    ).sort("at", -1).to_list(length=limit)
    return {
        "user_id": user.user_id,
        "count":   len(rows),
        "rows":    rows,
    }
