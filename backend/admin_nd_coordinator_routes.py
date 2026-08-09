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

The dashboard endpoint accepts an optional ``window_days`` query
parameter (30 / 60 / 90 / 180 / null) that clips both the assessments
feed AND the coordinator-alert audit counters to that trailing window.
This lets an operator hide stale risk that has since resolved without
losing the historical audit rows on disk.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic
from analytics_routes import require_admin


router = APIRouter(prefix="/admin/nd-risk-coordinator", tags=["admin-nd-coordinator"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


ASSESSMENTS_COLLECTION = "nd_assessments"
ALERTS_COLLECTION = "nd_coordinator_alerts"

# Allowed windows for the dashboard filter chip. `None` = all history.
# Values are days; we materialise a cutoff via `_cutoff_for_window`.
ALLOWED_WINDOWS = (30, 60, 90, 180)

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


async def _latest_per_parent(
    db: AsyncIOMotorDatabase,
    cutoff_iso: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the newest ND assessment per target_user_id.

    We deliberately fetch every doc and reduce in memory rather than run
    a $group aggregation — the dataset for this platform is small (one
    assessment per parent every few weeks at most) and this keeps the
    tier-scoring logic identical to what the individual endpoint uses.

    When ``cutoff_iso`` is provided, only assessments with
    ``created_at >= cutoff_iso`` are considered. Because ``created_at``
    values are stored as ISO-8601 UTC strings, a lexicographic string
    comparison is a correct chronological comparison (the format is
    fixed-width up to the timezone marker).
    """
    query: Dict[str, Any] = {}
    if cutoff_iso:
        query["created_at"] = {"$gte": cutoff_iso}
    cursor = db[ASSESSMENTS_COLLECTION].find(
        query, {"_id": 0},
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


def _cutoff_for_window(window_days: Optional[int]) -> Optional[str]:
    """Return the ISO-8601 UTC cutoff for a given trailing-days window.

    ``None`` when the caller passed no filter — this preserves the
    original "all history" behaviour of the endpoint.
    """
    if not window_days:
        return None
    if window_days not in ALLOWED_WINDOWS:
        raise HTTPException(
            400,
            f"window_days must be one of {sorted(ALLOWED_WINDOWS)} or omitted.",
        )
    return (
        datetime.now(timezone.utc) - timedelta(days=window_days)
    ).isoformat()


@router.get("")
async def admin_coordinator_dashboard(
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
    window_days: Optional[int] = Query(
        None,
        description=(
            "Trailing-days window for cases + alerts. Allowed: "
            "30, 60, 90, 180. Omit for all history."
        ),
    ),
):
    """Return the coordinator's global heatmap + active-cases feed.

    Supports an optional ``window_days`` trailing-window filter so
    admins can hide stale risk without archiving historical data.
    """
    cutoff = _cutoff_for_window(window_days)
    cases = await _latest_per_parent(db, cutoff)
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
    # Clip to the same trailing-days window as the assessments feed so
    # the KPI strip is internally consistent.
    alerts_query: Dict[str, Any] = {}
    alerts_query_emailed: Dict[str, Any] = {"email_ok": True}
    if cutoff:
        alerts_query["created_at"] = {"$gte": cutoff}
        alerts_query_emailed["created_at"] = {"$gte": cutoff}
    alerts_total = await db[ALERTS_COLLECTION].count_documents(alerts_query)
    alerts_recent = await db[ALERTS_COLLECTION].count_documents(alerts_query_emailed)

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
        "window_days":           window_days,
    }


@router.get("/case/{target_user_id}")
async def admin_case_history(
    target_user_id: str,
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return every ND Risk Assessment for a single parent, newest first,
    plus every coordinator email alert on record for them. Powers the
    admin-only case drilldown side panel on the coordinator dashboard.

    Refuses if the target parent has never completed an assessment (404)
    so the admin gets a clean signal rather than an empty panel.
    """
    cursor = db[ASSESSMENTS_COLLECTION].find(
        {"target_user_id": target_user_id}, {"_id": 0},
    ).sort("created_at", -1)
    history: List[Dict[str, Any]] = [row async for row in cursor]
    if not history:
        raise HTTPException(404, "No ND Risk assessments on file for this parent.")

    # Freeze the parent-facing name at the newest assessment; if that
    # row lacks it, fall back through history rather than showing "Parent".
    target_name = ""
    for row in history:
        if row.get("target_name"):
            target_name = row["target_name"]
            break

    # Coordinator alert audit trail for this parent — helps the admin
    # see whether an alert was actually delivered.
    alerts_cursor = db[ALERTS_COLLECTION].find(
        {"user_id": target_user_id}, {"_id": 0},
    ).sort("created_at", -1)
    alerts = [row async for row in alerts_cursor]

    # Compact history rows for the panel — never leak the raw matrix
    # unless the admin drills into a specific assessment.
    def _row(c: Dict[str, Any]) -> Dict[str, Any]:
        sc = c.get("scoring") or {}
        return {
            "assessment_id":       c.get("assessment_id"),
            "created_at":          c.get("created_at"),
            "status":              c.get("status"),
            "coparent_name":       c.get("coparent_name") or "",
            "tier":                sc.get("tier"),
            "tier_label":          sc.get("tier_label"),
            "threat_score":        sc.get("threat_score"),
            "vulnerability_score": sc.get("vulnerability_score"),
            "total_score":         sc.get("total_score"),
            "sub_scores":          sc.get("sub_scores") or {},
            "notes":               c.get("notes") or "",
        }

    return {
        "target_user_id":  target_user_id,
        "target_name":     target_name or "Parent",
        "assessment_count": len(history),
        "history":         [_row(c) for c in history],
        "alerts":          [
            {
                "assessment_id": a.get("assessment_id"),
                "tier":          a.get("tier"),
                "email_ok":      bool(a.get("email_ok")),
                "created_at":    a.get("created_at"),
            }
            for a in alerts
        ],
    }
