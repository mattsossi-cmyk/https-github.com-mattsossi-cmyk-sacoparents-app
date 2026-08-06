"""Neurodivergent Coparenting Risk Assessment — data models, scoring
engine, and REST routes.

Structure:
    /api/nd-risk/profile           — GET / PUT the caller's parent profile
    /api/nd-risk/assessment        — POST a new assessment (returns tier)
    /api/nd-risk/assessment/{id}   — GET a single assessment
    /api/nd-risk/assessments/me    — list caller's assessments
    /api/nd-risk/coordinator       — coordinator dashboard summary

Scoring:
    Each axis (Threat, Vulnerability) has 3 sub-dimensions rated 1..4.
    Axis score = max(sub-dimensions)   -- conservative for safety.
    Overall  = threat_score * vulnerability_score  -> 1..16 range.
    Tier     = Low (1-3) / Medium (4-8) / High (9-12) / Critical (13-16).

Storage: Mongo, three collections:
    nd_parent_profiles     — one per user_id
    nd_assessments         — one document per completed assessment
    (matrix responses are embedded on the assessment document — no need
     for a separate collection since they always travel together)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, conint

from auth import UserPublic, get_current_user
from db import get_db


router = APIRouter(prefix="/nd-risk", tags=["nd-risk"])

PROFILES_COLLECTION = "nd_parent_profiles"
ASSESSMENTS_COLLECTION = "nd_assessments"


# ---------------------------------------------------------------------------
#  MODELS
# ---------------------------------------------------------------------------

Role = Literal["target_parent", "coparent"]
Status = Literal["pending", "completed", "flagged"]
NDLabel = Literal["adhd", "autism", "auditory_processing", "none_other"]
Tier = Literal["low", "medium", "high", "critical"]


class NDParentProfile(BaseModel):
    """The parent's own neurodivergent + communication profile."""
    name: str = Field(..., min_length=1, max_length=80)
    role: Role
    nd_labels: List[NDLabel] = Field(default_factory=list)
    communication_preferences: Optional[str] = Field(None, max_length=500)


class MatrixResponse(BaseModel):
    """Sub-dimension ratings on each axis. Each entry is 1..4."""
    # Threat Axis (the coparent's behaviour)
    threat_scheduling_disruption: conint(ge=1, le=4)  # type: ignore[valid-type]
    threat_gaslighting: conint(ge=1, le=4)            # type: ignore[valid-type]
    threat_sensory_overload: conint(ge=1, le=4)       # type: ignore[valid-type]
    # Vulnerability Axis (the target parent's state)
    vuln_executive_burnout: conint(ge=1, le=4)        # type: ignore[valid-type]
    vuln_memory_fragmentation: conint(ge=1, le=4)     # type: ignore[valid-type]
    vuln_communication_bottleneck: conint(ge=1, le=4) # type: ignore[valid-type]


class AssessmentSubmission(BaseModel):
    coparent_name: str = Field(..., min_length=1, max_length=80)
    matrix: MatrixResponse
    notes: Optional[str] = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
#  SCORING ENGINE
# ---------------------------------------------------------------------------

# Sub-dimension metadata used by the frontend heatmap + interventions view.
THREAT_DIMENSIONS = [
    ("threat_scheduling_disruption", "Scheduling disruption",
     "Coparent uses last-minute changes, no-shows, or calendar chaos as a lever."),
    ("threat_gaslighting", "Memory manipulation / gaslighting",
     "Coparent denies agreed events, rewrites history, or distorts what was said."),
    ("threat_sensory_overload", "Intentional sensory overload",
     "Coparent uses volume, environments, or timing to overwhelm you deliberately."),
]

VULNERABILITY_DIMENSIONS = [
    ("vuln_executive_burnout", "Executive burnout",
     "Your capacity for planning, task-switching, and follow-through is depleted."),
    ("vuln_memory_fragmentation", "Trauma-induced memory fragmentation",
     "Your recall of recent exchanges is patchy or dissociative under stress."),
    ("vuln_communication_bottleneck", "Communication bottleneck",
     "You struggle to formulate a reply in real time under pressure."),
]


# Required-interventions per tier — surfaced on the individual result
# page AND on the coordinator dashboard.
INTERVENTIONS: Dict[Tier, List[str]] = {
    "low": [
        "Enforce Standard Parallel Parenting via the platform's unmodifiable calendar.",
        "Turn on 24-hour reminders for every custody transition.",
        "Log all schedule changes through the platform (no verbal edits).",
    ],
    "medium": [
        "Enforce Monitored Messaging: all coparent messages routed through the platform.",
        "Restrict communication to defined hours (e.g. 08:00-20:00 CT).",
        "Auto-flag tone triggers (all-caps, insult tokens) for a coordinator review.",
        "Turn on a 30-minute cool-down between rapid replies.",
    ],
    "high": [
        "Enforce Asynchronous Hand-Offs — no synchronous back-and-forth allowed.",
        "Block direct messaging between coparents on the platform.",
        "Mandate strict text-only templates for logistics (pickup, drop-off, medical).",
        "24-hour maximum response window; anything faster is optional.",
        "Every message reviewed by a coordinator before delivery.",
    ],
    "critical": [
        "Restrict platform messaging entirely.",
        "Route communication to legal representatives only.",
        "Enable emergency-only broadcast channel (child health/safety events).",
        "Notify the assigned family court liaison automatically.",
        "Coordinator schedules a same-day check-in with the target parent.",
    ],
}


def _axis_score(values: List[int]) -> int:
    """Axis score = max sub-dimension (most conservative for safety)."""
    return max(values) if values else 1


def _tier(score: int) -> Tier:
    if score <= 3:  return "low"
    if score <= 8:  return "medium"
    if score <= 12: return "high"
    return "critical"


def score_assessment(matrix: MatrixResponse) -> Dict[str, Any]:
    """Return the full scoring breakdown for a matrix submission."""
    threat_values = [
        matrix.threat_scheduling_disruption,
        matrix.threat_gaslighting,
        matrix.threat_sensory_overload,
    ]
    vuln_values = [
        matrix.vuln_executive_burnout,
        matrix.vuln_memory_fragmentation,
        matrix.vuln_communication_bottleneck,
    ]
    threat = _axis_score(threat_values)
    vuln = _axis_score(vuln_values)
    total = threat * vuln
    tier = _tier(total)
    return {
        "threat_score":      threat,
        "vulnerability_score": vuln,
        "total_score":       total,
        "tier":              tier,
        "tier_label": {
            "low":      "Low",
            "medium":   "Medium",
            "high":     "High",
            "critical": "Critical",
        }[tier],
        "interventions":     INTERVENTIONS[tier],
        "sub_scores": {
            "threat": {k: getattr(matrix, k) for k, _, _ in THREAT_DIMENSIONS},
            "vulnerability": {k: getattr(matrix, k) for k, _, _ in VULNERABILITY_DIMENSIONS},
        },
    }


# ---------------------------------------------------------------------------
#  PROFILE ROUTES
# ---------------------------------------------------------------------------

@router.get("/profile")
async def get_profile(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the caller's ND parent profile — or `null` if none yet."""
    doc = await db[PROFILES_COLLECTION].find_one(
        {"user_id": user.user_id}, {"_id": 0, "user_id": 0},
    )
    return {"profile": doc}


@router.put("/profile")
async def put_profile(
    body: NDParentProfile,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        **body.model_dump(),
        "user_id":    user.user_id,
        "updated_at": now,
    }
    await db[PROFILES_COLLECTION].update_one(
        {"user_id": user.user_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"ok": True, "profile": body.model_dump()}


# ---------------------------------------------------------------------------
#  ASSESSMENT ROUTES
# ---------------------------------------------------------------------------

@router.post("/assessment")
async def submit_assessment(
    body: AssessmentSubmission,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a completed assessment. Idempotency: each POST creates a
    fresh record — parents may re-assess as conditions change."""
    scored = score_assessment(body.matrix)
    aid = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    profile = await db[PROFILES_COLLECTION].find_one(
        {"user_id": user.user_id}, {"_id": 0, "name": 1, "role": 1},
    )
    doc = {
        "assessment_id":  aid,
        "target_user_id": user.user_id,
        "target_name":    (profile or {}).get("name") or user.name or "Target Parent",
        "coparent_name":  body.coparent_name,
        "created_at":     now,
        "status":         "flagged" if scored["tier"] in ("high", "critical") else "completed",
        "matrix":         body.matrix.model_dump(),
        "scoring":        scored,
        "notes":          body.notes,
    }
    await db[ASSESSMENTS_COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/assessment/{aid}")
async def get_assessment(
    aid: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return an assessment. Parents can only fetch their own; users with
    a `role == 'admin'` (coordinators) can fetch any."""
    q: Dict[str, Any] = {"assessment_id": aid}
    if getattr(user, "role", None) != "admin":
        q["target_user_id"] = user.user_id
    doc = await db[ASSESSMENTS_COLLECTION].find_one(q, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Assessment not found")
    return doc


@router.get("/assessments/me")
async def list_my_assessments(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    cursor = db[ASSESSMENTS_COLLECTION].find(
        {"target_user_id": user.user_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit)
    items = [row async for row in cursor]
    return {"items": items, "total": len(items)}


@router.get("/coordinator")
async def coordinator_summary(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """Multi-location coordinator view.

    Admins see every case; every other role sees only their own record
    but still gets the full dashboard shape (single-case view). The
    frontend renders identical UI in both scopes.
    """
    is_admin = getattr(user, "role", None) == "admin"
    q: Dict[str, Any] = {} if is_admin else {"target_user_id": user.user_id}
    cursor = db[ASSESSMENTS_COLLECTION].find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    cases = [row async for row in cursor]

    # Live 4×4 heatmap: counts[threat-1][vuln-1] = number of cases in
    # that grid cell. Populated from the most-recent assessment per
    # target_user_id so a parent who re-assessed doesn't double-count.
    latest_per_target: Dict[str, Dict[str, Any]] = {}
    for c in cases:
        tid = c.get("target_user_id")
        if tid and tid not in latest_per_target:
            latest_per_target[tid] = c
    heatmap = [[0] * 4 for _ in range(4)]
    for c in latest_per_target.values():
        sc = c.get("scoring") or {}
        t = int(sc.get("threat_score", 0)) - 1
        v = int(sc.get("vulnerability_score", 0)) - 1
        if 0 <= t <= 3 and 0 <= v <= 3:
            heatmap[t][v] += 1

    tier_counts: Dict[Tier, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for c in latest_per_target.values():
        tier = (c.get("scoring") or {}).get("tier")
        if tier in tier_counts:
            tier_counts[tier] += 1  # type: ignore[index]

    return {
        "is_admin":     is_admin,
        "cases":        cases,
        "case_count":   len(latest_per_target),
        "heatmap":      heatmap,
        "tier_counts":  tier_counts,
        "threat_dimensions":         [{"key": k, "label": l, "hint": h} for k, l, h in THREAT_DIMENSIONS],
        "vulnerability_dimensions":  [{"key": k, "label": l, "hint": h} for k, l, h in VULNERABILITY_DIMENSIONS],
        "interventions_by_tier":     INTERVENTIONS,
    }
