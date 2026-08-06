"""Intervention Compliance Log — weekly check-in on which enforced
interventions a parent is actually following.

Interventions come from three sources on the app:
    * Safety Assessment       -> `result.recommendations`
    * ND Risk Assessment      -> `scoring.interventions`
    * Dimension Companion     -> per-dimension `interventions`

At request time we aggregate the parent's LATEST assessment from each
source and mint a stable `intervention_key` = md5(source|text)[:16].
The parent then ticks off each item per calendar week (Mon 00:00 UTC).

Storage:
    intervention_compliance  — one document per (user_id, week_start,
                              intervention_key). Idempotent upsert.

Endpoints:
    GET  /api/interventions/log                — current week + items
    POST /api/interventions/log                — upsert one item
    GET  /api/interventions/log/history?weeks=N — % followed for last N weeks
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


router = APIRouter(prefix="/interventions", tags=["interventions"])
COLLECTION = "intervention_compliance"

Source = Literal["safety", "nd_risk", "companion"]


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _week_start(dt: Optional[datetime] = None) -> str:
    """Return ISO date (YYYY-MM-DD) of the Monday of the given UTC datetime."""
    d = (dt or datetime.now(timezone.utc)).astimezone(timezone.utc)
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _key(source: str, text: str) -> str:
    """Stable intervention key across re-assessments — as long as the
    source + wording stay the same, the parent's tick persists."""
    return hashlib.md5(f"{source}|{text.strip()}".encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# AGGREGATION — build the current-week checklist from latest assessments.
# ---------------------------------------------------------------------------

async def _load_latest_interventions(
    db: AsyncIOMotorDatabase, user_id: str
) -> List[Dict[str, Any]]:
    """Return a flat list of {key, source, group, text} across the parent's
    latest Safety + ND Risk + Companion assessments."""
    items: List[Dict[str, Any]] = []

    # Safety
    safety = await db.safety_assessments.find_one(
        {"user_id": user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if safety:
        recs = ((safety.get("result") or {}).get("recommendations") or [])
        level = (safety.get("result") or {}).get("level")
        for txt in recs:
            items.append({
                "key":    _key("safety", txt),
                "source": "safety",
                "group":  f"Dimension 1 · Safety (Level {level})" if level else "Dimension 1 · Safety",
                "text":   txt,
            })

    # ND Risk (most recent)
    nd = await db.nd_assessments.find_one(
        {"target_user_id": user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if nd:
        tier_label = ((nd.get("scoring") or {}).get("tier_label") or "").strip() or "?"
        for txt in ((nd.get("scoring") or {}).get("interventions") or []):
            items.append({
                "key":    _key("nd_risk", txt),
                "source": "nd_risk",
                "group":  f"ND Risk · {tier_label} tier",
                "text":   txt,
            })

    # Companion
    comp = await db.dimension_companion_assessments.find_one(
        {"user_id": user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if comp:
        dims = ((comp.get("scoring") or {}).get("dimensions") or {})
        # Preserve numerical order.
        for k, num, label in (
            ("communication",        "2", "Communication"),
            ("emotional_regulation", "3", "Emotional regulation"),
            ("executive_function",   "4", "Executive function"),
        ):
            d = dims.get(k) or {}
            tier_label = d.get("tier_label") or "-"
            for txt in (d.get("interventions") or []):
                items.append({
                    "key":    _key("companion", txt),
                    "source": "companion",
                    "group":  f"Dimension {num} · {label} ({tier_label})",
                    "text":   txt,
                })
    return items


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class LogEntryPatch(BaseModel):
    intervention_key: str = Field(..., min_length=8, max_length=32)
    source:           Source
    text:             str = Field(..., min_length=1, max_length=1000)
    group:            Optional[str] = Field(None, max_length=200)
    followed:         bool
    notes:            Optional[str] = Field(None, max_length=800)
    week_start:       Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@router.get("/log")
async def get_current_log(
    week_start: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the merged checklist for the current (or specified) week.

    Response shape:
        {
          week_start,
          items: [{key, source, group, text, followed, notes, updated_at}],
          summary: {total, followed, compliance_pct},
        }
    """
    wk = week_start or _week_start()
    catalog = await _load_latest_interventions(db, user.user_id)

    # Batch-fetch existing ticks for this week.
    existing_cursor = db[COLLECTION].find(
        {"user_id": user.user_id, "week_start": wk},
        {"_id": 0},
    )
    existing_by_key: Dict[str, Dict[str, Any]] = {}
    async for row in existing_cursor:
        existing_by_key[row["intervention_key"]] = row

    items: List[Dict[str, Any]] = []
    followed_count = 0
    for c in catalog:
        prior = existing_by_key.get(c["key"]) or {}
        followed = bool(prior.get("followed"))
        if followed:
            followed_count += 1
        items.append({
            **c,
            "followed":   followed,
            "notes":      prior.get("notes"),
            "updated_at": prior.get("updated_at"),
        })

    total = len(items)
    return {
        "week_start": wk,
        "items":      items,
        "summary": {
            "total":          total,
            "followed":       followed_count,
            "compliance_pct": round((followed_count / total) * 100, 1) if total else 0.0,
        },
    }


@router.post("/log")
async def upsert_log_entry(
    body: LogEntryPatch,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    wk = body.week_start or _week_start()
    now = datetime.now(timezone.utc).isoformat()
    result = await db[COLLECTION].update_one(
        {
            "user_id":          user.user_id,
            "week_start":       wk,
            "intervention_key": body.intervention_key,
        },
        {
            "$set": {
                "source":     body.source,
                "text":       body.text,
                "group":      body.group,
                "followed":   body.followed,
                "notes":      body.notes,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return {
        "ok":         True,
        "week_start": wk,
        "matched":    result.matched_count,
        "modified":   result.modified_count,
        "upserted":   bool(result.upserted_id),
    }


@router.get("/log/history")
async def get_history(
    weeks: int = Query(8, ge=1, le=26),
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Weekly compliance % for the last `weeks` weeks (oldest first).

    We compute the denominator per-week from the entries the parent
    actually engaged with that week — this avoids penalising a parent
    whose intervention catalog grew due to a re-assessment. If a week
    has zero recorded ticks, compliance_pct is `null` (rendered as an
    empty bar on the sparkline).
    """
    today = datetime.now(timezone.utc)
    cutoff_date = today - timedelta(days=weeks * 7)
    cursor = db[COLLECTION].find(
        {
            "user_id":    user.user_id,
            "week_start": {"$gte": _week_start(cutoff_date)},
        },
        {"_id": 0, "week_start": 1, "followed": 1},
    )
    by_week: Dict[str, Dict[str, int]] = {}
    async for row in cursor:
        w = row["week_start"]
        bucket = by_week.setdefault(w, {"total": 0, "followed": 0})
        bucket["total"] += 1
        if row.get("followed"):
            bucket["followed"] += 1

    # Emit weeks in chronological order, filling gaps with nulls.
    out: List[Dict[str, Any]] = []
    for i in range(weeks - 1, -1, -1):
        d = today - timedelta(days=i * 7)
        wk = _week_start(d)
        b = by_week.get(wk)
        if not b:
            out.append({"week_start": wk, "total": 0, "followed": 0, "compliance_pct": None})
        else:
            out.append({
                "week_start":     wk,
                "total":          b["total"],
                "followed":       b["followed"],
                "compliance_pct": round((b["followed"] / b["total"]) * 100, 1) if b["total"] else None,
            })
    return {"weeks": out}
