"""Deep-dive dashboard aggregator: returns per-user status for the three
optional deep dives (Educational, Psychological, Medical).

Read-only aggregator over existing collections:
  edu_deep_assessments   / edu_deep_reports
  psych_deep_assessments / psych_deep_reports
  med_deep_assessments   / med_deep_reports
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user, get_db


router = APIRouter(prefix="/deep-dives", tags=["deep-dives"])


DEEP_DIVES = [
    {
        "id": "educational",
        "name": "Educational Needs",
        "assessment_collection": "edu_deep_assessments",
        "report_collection": "edu_deep_reports",
        "shares_collection": "edu_deep_shares",
        "route": "/special-needs-v2/educational-deep-dive",
        "report_route": "/special-needs-v2/educational-deep-dive/report",
        "compare_route": "/special-needs-v2/educational-deep-dive/compare",
    },
    {
        "id": "psychological",
        "name": "Psychological / Behavioural",
        "assessment_collection": "psych_deep_assessments",
        "report_collection": "psych_deep_reports",
        "shares_collection": "psych_deep_shares",
        "route": "/special-needs-v2/psychological-deep-dive",
        "report_route": "/special-needs-v2/psychological-deep-dive/report",
        "compare_route": "/special-needs-v2/psychological-deep-dive/compare",
    },
    {
        "id": "medical",
        "name": "Medical · Prescription & Medication",
        "assessment_collection": "med_deep_assessments",
        "report_collection": "med_deep_reports",
        "shares_collection": "med_deep_shares",
        "route": "/special-needs-v2/medical-deep-dive",
        "report_route": "/special-needs-v2/medical-deep-dive/report",
        "compare_route": "/special-needs-v2/medical-deep-dive/compare",
    },
]


@router.get("/status")
async def deep_dive_status(user: UserPublic = Depends(get_current_user),
                           db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Return status for every optional deep dive for the current user."""
    out = []
    for dd in DEEP_DIVES:
        assessment = await db[dd["assessment_collection"]].find_one(
            {"user_id": user.user_id}, {"_id": 0, "completed": 1, "updated_at": 1, "responses": 1}
        )
        report = await db[dd["report_collection"]].find_one(
            {"user_id": user.user_id}, {"_id": 0, "generated_at": 1, "stale": 1}
        )
        answered_count = 0
        if assessment:
            responses = assessment.get("responses") or {}
            answered_count = sum(
                1 for v in responses.values()
                if v not in (None, "", [])
            )
        out.append({
            "id": dd["id"],
            "name": dd["name"],
            "route": dd["route"],
            "report_route": dd["report_route"],
            "has_assessment": bool(assessment),
            "completed": bool(assessment and assessment.get("completed")),
            "answered_count": answered_count,
            "has_report": bool(report),
            "report_stale": bool(report and report.get("stale")),
            "updated_at": (assessment or {}).get("updated_at"),
            "generated_at": (report or {}).get("generated_at"),
        })
    started = sum(1 for d in out if d["has_assessment"])
    finished = sum(1 for d in out if d["completed"])
    return {"deep_dives": out, "started": started, "completed": finished, "total": len(out)}


async def _compare_counts(db: AsyncIOMotorDatabase, user_id: str,
                          dd: Dict[str, Any]) -> Dict[str, Any]:
    """Count active + ready-to-view compare shares in a pathway for the user.

    "active" = any non-revoked share the user participates in (creator OR
    partner). "ready_to_view" = both parents consented AND both assessments
    completed. Same logic as the compare-router hydrate helper, kept lean
    here because the Dashboard tile calls this on every mount.
    """
    cursor = db[dd["shares_collection"]].find(
        {"user_pair": user_id, "status": {"$ne": "revoked"}}, {"_id": 0},
    )
    active = 0
    ready = 0
    async for share in cursor:
        active += 1
        if not (share.get("creator_consent") and share.get("partner_consent")):
            continue
        # Both consented; are both assessments complete?
        me_a = await db[dd["assessment_collection"]].find_one(
            {"user_id": user_id}, {"_id": 0, "completed": 1}
        )
        partner_id = (share.get("partner_user_id") if share.get("creator_user_id") == user_id
                      else share.get("creator_user_id"))
        partner_a = await db[dd["assessment_collection"]].find_one(
            {"user_id": partner_id}, {"_id": 0, "completed": 1}
        )
        if (me_a and me_a.get("completed")) and (partner_a and partner_a.get("completed")):
            ready += 1
    return {"active": active, "ready_to_view": ready}


@router.get("/compare-status")
async def compare_status(user: UserPublic = Depends(get_current_user),
                         db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Per-pathway counts for the Dashboard 'Compare with co-parent' tile."""
    per_pathway = []
    total_active = 0
    total_ready = 0
    for dd in DEEP_DIVES:
        counts = await _compare_counts(db, user.user_id, dd)
        per_pathway.append({
            "id": dd["id"],
            "name": dd["name"],
            "compare_route": dd["compare_route"],
            "active": counts["active"],
            "ready_to_view": counts["ready_to_view"],
        })
        total_active += counts["active"]
        total_ready += counts["ready_to_view"]
    return {
        "pathways": per_pathway,
        "total_active": total_active,
        "total_ready_to_view": total_ready,
    }
