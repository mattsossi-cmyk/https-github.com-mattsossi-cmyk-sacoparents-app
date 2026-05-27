"""Analytics routes.

- /api/analytics/me        → personal dashboard for the signed-in user
- /api/analytics/admin/*   → owner-only metrics (gated on ADMIN_EMAILS)

Designed to be cheap MongoDB reads — primarily count_documents and small
aggregations on already-indexed-by-user-id collections.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_current_user
from models import UserPublic

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ============ Admin gating ============
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "mattsossi@bsossi.com").split(",")
    if e.strip()
}


def require_admin(current: UserPublic = Depends(get_current_user)) -> UserPublic:
    if current.is_guest or current.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current


# ============ Personal analytics ============
PREP_SECTIONS = ("child_goals", "issues", "priority", "comm_style", "readiness")


def _readiness_score(answers: dict) -> Optional[int]:
    """Mirror the calculation used on the Readiness page: avg of 1-5 answers scaled to 0-100."""
    if not answers:
        return None
    vals = [v for v in answers.values() if isinstance(v, (int, float))]
    if not vals:
        return None
    avg = sum(vals) / len(vals)
    return round((avg / 5) * 100)


@router.get("/me")
async def personal_analytics(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    user_id = current.user_id

    prep = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0}) or {}
    completed_map = prep.get("completed") or {}
    steps_done = [s for s in PREP_SECTIONS if completed_map.get(s)]

    readiness_answers = (prep.get("readiness") or {}).get("answers") or {}
    current_readiness = _readiness_score(readiness_answers)

    # Counts (cheap)
    summaries_count = await db.summaries.count_documents({"user_id": user_id})
    agreements_count = await db.agreements.count_documents({"user_id": user_id})
    improvement_count = await db.improvement_plans.count_documents({"user_id": user_id})
    emails_count = await db.mediator_emails.count_documents({"user_id": user_id})

    # Latest summary (for "last activity") + readiness trend from snapshots
    recent_summaries_cursor = db.summaries.find(
        {"user_id": user_id},
        {"_id": 0, "summary_id": 1, "generated_at": 1, "readiness_score": 1, "prep_snapshot": 1},
    ).sort("generated_at", -1).limit(10)
    recent_summaries = await recent_summaries_cursor.to_list(10)

    readiness_trend = []
    for s in reversed(recent_summaries):
        snap_readiness = (s.get("prep_snapshot") or {}).get("readiness") or {}
        score = _readiness_score(snap_readiness.get("answers") or {})
        if score is not None:
            readiness_trend.append({
                "at": s.get("generated_at"),
                "score": score,
            })

    last_summary = recent_summaries[0] if recent_summaries else None
    last_activity = (
        last_summary.get("generated_at") if last_summary
        else prep.get("updated_at") or current.created_at
    )

    return {
        "user": {
            "name": current.name,
            "email": current.email,
            "created_at": current.created_at,
            "mediation_date": current.mediation_date,
            "is_guest": current.is_guest,
        },
        "progress": {
            "completed": [s for s in PREP_SECTIONS if completed_map.get(s)],
            "remaining": [s for s in PREP_SECTIONS if not completed_map.get(s)],
            "steps_done": len(steps_done),
            "steps_total": len(PREP_SECTIONS),
            "pct": round(len(steps_done) / len(PREP_SECTIONS) * 100),
        },
        "readiness": {
            "current": current_readiness,
            "trend": readiness_trend,
        },
        "activity": {
            "summaries": summaries_count,
            "agreements": agreements_count,
            "improvement_plans": improvement_count,
            "mediator_emails": emails_count,
            "last_activity_at": last_activity,
        },
        "recent_summaries": [
            {
                "summary_id": s.get("summary_id"),
                "generated_at": s.get("generated_at"),
                "readiness_score": s.get("readiness_score"),
            }
            for s in recent_summaries
        ],
    }


# ============ Admin analytics ============
@router.get("/admin/overview")
async def admin_overview(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    db = request.app.state.db
    now = _now()
    iso_7d = _iso(now - timedelta(days=7))
    iso_30d = _iso(now - timedelta(days=30))

    # User counts
    total_users = await db.users.count_documents({"is_guest": {"$ne": True}})
    total_guests = await db.users.count_documents({"is_guest": True})

    new_users_7d = await db.users.count_documents(
        {"is_guest": {"$ne": True}, "created_at": {"$gte": iso_7d}}
    )
    new_users_30d = await db.users.count_documents(
        {"is_guest": {"$ne": True}, "created_at": {"$gte": iso_30d}}
    )
    new_guests_7d = await db.users.count_documents(
        {"is_guest": True, "created_at": {"$gte": iso_7d}}
    )

    # Auth methods (jwt = password, google = social, guest)
    auth_breakdown_cursor = db.users.aggregate([
        {"$group": {"_id": "$auth_method", "n": {"$sum": 1}}},
    ])
    auth_breakdown = {row["_id"] or "unknown": row["n"] async for row in auth_breakdown_cursor}

    # AI / engagement counts
    summaries_total = await db.summaries.count_documents({})
    summaries_7d = await db.summaries.count_documents({"generated_at": {"$gte": iso_7d}})
    agreements_total = await db.agreements.count_documents({})
    agreements_7d = await db.agreements.count_documents({"generated_at": {"$gte": iso_7d}})
    improvement_total = await db.improvement_plans.count_documents({})
    mediator_emails_total = await db.mediator_emails.count_documents({})
    mediator_emails_7d = await db.mediator_emails.count_documents({"sent_at": {"$gte": iso_7d}})

    # Magic links: requested vs successfully consumed
    magic_requested = await db.magic_links.count_documents({})
    magic_used = await db.magic_links.count_documents({"used": True})

    # Funnel — count prep_data rows that have each section completed.
    funnel = {}
    for sec in PREP_SECTIONS:
        funnel[sec] = await db.prep_data.count_documents({f"completed.{sec}": True})

    # Guest → claim conversion: users whose user_id starts with "guest_"
    # would have had `is_guest` previously and now don't. Approximation:
    # count permanent users whose user_id starts with "guest_".
    claimed_guests = await db.users.count_documents(
        {"is_guest": {"$ne": True}, "user_id": {"$regex": "^guest_"}}
    )

    return {
        "generated_at": _iso(now),
        "users": {
            "total": total_users,
            "new_7d": new_users_7d,
            "new_30d": new_users_30d,
            "guests_active": total_guests,
            "guests_new_7d": new_guests_7d,
            "claimed_from_guest": claimed_guests,
            "auth_breakdown": auth_breakdown,
        },
        "engagement": {
            "summaries_total": summaries_total,
            "summaries_7d": summaries_7d,
            "agreements_total": agreements_total,
            "agreements_7d": agreements_7d,
            "improvement_plans_total": improvement_total,
            "mediator_emails_total": mediator_emails_total,
            "mediator_emails_7d": mediator_emails_7d,
        },
        "magic_links": {
            "requested": magic_requested,
            "used": magic_used,
            "conversion_pct": (
                round((magic_used / magic_requested) * 100) if magic_requested else 0
            ),
        },
        "funnel": funnel,
    }


@router.get("/admin/recent-users")
async def admin_recent_users(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
    limit: int = 25,
):
    db = request.app.state.db
    limit = max(1, min(limit, 100))
    cursor = db.users.find(
        {"is_guest": {"$ne": True}},
        {"_id": 0, "user_id": 1, "email": 1, "name": 1, "auth_method": 1, "created_at": 1},
    ).sort("created_at", -1).limit(limit)
    users = await cursor.to_list(limit)

    # Enrich each with their progress + AI counts (cheap parallelisable reads,
    # done sequentially to keep the code simple — typical limit is 25.)
    enriched = []
    for u in users:
        prep = await db.prep_data.find_one(
            {"user_id": u["user_id"]}, {"_id": 0, "completed": 1}
        )
        completed_map = (prep or {}).get("completed") or {}
        steps_done = sum(1 for s in PREP_SECTIONS if completed_map.get(s))
        summaries_count = await db.summaries.count_documents({"user_id": u["user_id"]})
        enriched.append({
            **u,
            "steps_done": steps_done,
            "steps_total": len(PREP_SECTIONS),
            "summaries": summaries_count,
        })
    return {"users": enriched}


@router.get("/admin/daily-signups")
async def admin_daily_signups(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
    days: int = 30,
):
    """Counts of new (non-guest) users per UTC day for the past N days."""
    db = request.app.state.db
    days = max(1, min(days, 90))
    since = _now() - timedelta(days=days)
    since_iso = _iso(since)

    cursor = db.users.find(
        {"is_guest": {"$ne": True}, "created_at": {"$gte": since_iso}},
        {"_id": 0, "created_at": 1},
    )
    buckets: dict[str, int] = {}
    async for u in cursor:
        ca = u.get("created_at")
        if not ca:
            continue
        try:
            day = ca[:10]  # ISO YYYY-MM-DD
            buckets[day] = buckets.get(day, 0) + 1
        except Exception:
            continue

    # Fill in zero days
    series = []
    for i in range(days - 1, -1, -1):
        d = (_now() - timedelta(days=i)).strftime("%Y-%m-%d")
        series.append({"date": d, "count": buckets.get(d, 0)})
    return {"days": days, "series": series}
