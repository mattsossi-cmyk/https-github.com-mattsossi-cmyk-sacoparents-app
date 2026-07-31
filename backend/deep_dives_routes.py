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
        "route": "/special-needs-v2/educational-deep-dive",
        "report_route": "/special-needs-v2/educational-deep-dive/report",
    },
    {
        "id": "psychological",
        "name": "Psychological / Behavioural",
        "assessment_collection": "psych_deep_assessments",
        "report_collection": "psych_deep_reports",
        "route": "/special-needs-v2/psychological-deep-dive",
        "report_route": "/special-needs-v2/psychological-deep-dive/report",
    },
    {
        "id": "medical",
        "name": "Medical · Prescription & Medication",
        "assessment_collection": "med_deep_assessments",
        "report_collection": "med_deep_reports",
        "route": "/special-needs-v2/medical-deep-dive",
        "report_route": "/special-needs-v2/medical-deep-dive/report",
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
