"""Admin ND Risk Coordinator Dashboard.

Aggregates every parent's *latest* ND Risk Assessment into:

    * a 4x4 heatmap (threat_score 1..4  x  vulnerability_score 1..4),
      each cell holding the count of parents landing there + the tier
      that cell resolves to.
    * an "active cases" list — the latest assessment per parent whose
      tier is ``high`` or ``critical``. Ordered by tier severity then
      total_score desc.
    * summary counters + coordinator-alert email-send counts.

Only accessible to ADMIN_EMAILS members (delegates to
``analytics_routes.require_admin``). Guest users are refused.

The route is intentionally read-only. No PII beyond target_name /
coparent_name is exposed and target_user_id is passed through so the
admin can jump to individual case history.
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic
from analytics_routes import require_admin


router = APIRouter(prefix="/admin/nd-risk-coordinator", tags=["admin-nd-coordinator"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


ASSESSMENTS_COLLECTION = "nd_assessments"
ALERTS_COLLECTION = "nd_coordinator_alerts"

# Same tier boundaries as `nd_risk_routes._tier`. Duplicated here as a
# constant table because we bucket a 4x4 grid at load time — importing
# the function would work but the values are stable enough to inline
# and make explicit for anyone reading the endpoint.
def _cell_tier(threat: int, vuln: int) -> str:
    total = threat * vuln
    if total <= 3:  return "low"
    if total <= 8:  return "medium"
    if total <= 12: return "high"
    return "critical"


TIER_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


async def _latest_per_parent(db: AsyncIOMotorDatabase) -> List[Dict[str, Any]]:
    """Return the newest ND assessment per target_user_id.

    We deliberately fetch every doc and reduce in memory rather than run
    a $group aggregation — the dataset for this platform is small (one
    assessment per parent every few weeks at most) and this keeps the
    tier-scoring logic identical to what the individual endpoint uses.
    """
    cursor = db[ASSESSMENTS_COLLECTION].find(
        {}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    seen: Dict[str, Dict[str, Any]] = {}
    async for doc in cursor:
        tid = doc.get("target_user_id")
        if not tid or tid in seen:
            continue
        seen[tid] = doc
    return list(seen.values())


def _build_heatmap(cases: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Build the 4x4 grid. Row index = vulnerability score (1..4 top to
    bottom on the UI), column index = threat score (1..4 left to right).
    """
    grid: List[List[Dict[str, Any]]] = [
        [
            {
                "threat":     t,
                "vulnerability": v,
                "tier":       _cell_tier(t, v),
                "count":      0,
                "total_score": t * v,
            }
            for t in (1, 2, 3, 4)
        ]
        for v in (1, 2, 3, 4)
    ]
    for c in cases:
        s = c.get("scoring") or {}
        try:
            t = int(s.get("threat_score") or 0)
            v = int(s.get("vulnerability_score") or 0)
        except (TypeError, ValueError):
            continue
        if 1 <= t <= 4 and 1 <= v <= 4:
            grid[v - 1][t - 1]["count"] += 1
    return grid


def _summarise(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for c in cases:
        tier = (c.get("scoring") or {}).get("tier")
        if tier in counts:
            counts[tier] += 1
    return counts


@router.get("")
async def admin_coordinator_dashboard(
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the coordinator's global heatmap + active-cases feed."""
    cases = await _latest_per_parent(db)
    heatmap = _build_heatmap(cases)
    summary = _summarise(cases)

    # Active cases = latest-per-parent whose tier is high or critical.
    active_raw = [
        c for c in cases
        if (c.get("scoring") or {}).get("tier") in ("high", "critical")
    ]
    active_raw.sort(
        key=lambda c: (
            TIER_ORDER.get((c.get("scoring") or {}).get("tier"), 9),
            -int((c.get("scoring") or {}).get("total_score") or 0),
            c.get("created_at") or "",
        ),
    )
    active = [
        {
            "assessment_id":  c.get("assessment_id"),
            "target_user_id": c.get("target_user_id"),
            "target_name":    c.get("target_name") or "Parent",
            "coparent_name":  c.get("coparent_name") or "",
            "tier":           (c.get("scoring") or {}).get("tier"),
            "tier_label":     (c.get("scoring") or {}).get("tier_label"),
            "threat_score":   (c.get("scoring") or {}).get("threat_score"),
            "vulnerability_score": (c.get("scoring") or {}).get("vulnerability_score"),
            "total_score":    (c.get("scoring") or {}).get("total_score"),
            "status":         c.get("status"),
            "created_at":     c.get("created_at"),
        }
        for c in active_raw
    ]

    # Total number of coordinator email alerts on record (audit trail).
    alerts_total = await db[ALERTS_COLLECTION].count_documents({})
    alerts_recent = await db[ALERTS_COLLECTION].count_documents({"email_ok": True})

    return {
        "total_parents":         len(cases),
        "tier_counts":           summary,
        "active_case_count":     len(active),
        "heatmap":               heatmap,
        "active_cases":          active,
        "coordinator_alerts": {
            "total":   int(alerts_total),
            "emailed": int(alerts_recent),
        },
    }
