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


# ============ Longitudinal growth ============
DIMENSION_KEYS = ("communication", "trust", "child_alignment", "conflict")
DIMENSION_LABELS = {
    "communication": "Communication",
    "trust": "Trust",
    "child_alignment": "Child alignment",
    "conflict": "Conflict (managed)",
}


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _summary_to_point(doc: dict) -> Optional[dict]:
    """Turn a stored summary doc into a chart-ready point.

    Prefers the persisted `readiness` bundle (dimensions + overall) which
    every new summary carries; falls back to computing from prep_snapshot
    for older summaries that pre-date the deterministic scorer.
    """
    when = doc.get("generated_at")
    readiness = doc.get("readiness") or {}
    overall = readiness.get("overall") or doc.get("readiness_score")
    label = readiness.get("label") or doc.get("readiness_label")
    dims = readiness.get("dimensions") or {}

    if overall is None:
        # Older doc — try to reconstruct from the raw prep snapshot.
        snap = doc.get("prep_snapshot") or {}
        answers = (snap.get("readiness") or {}).get("answers") or {}
        overall = _readiness_score(answers)
        if overall is None:
            return None

    point = {
        "at": when,
        "summary_id": doc.get("summary_id"),
        "overall": overall,
        "label": label,
    }
    for k in DIMENSION_KEYS:
        d = dims.get(k) or {}
        point[k] = d.get("score")
    return point


def _pick_baseline(points: list, window_days: int) -> Optional[dict]:
    """Choose the point closest to `window_days` ago (but no newer than
    today - window_days). Points come in chronological order."""
    if len(points) < 2:
        return None
    target = _now() - timedelta(days=window_days)
    older = [p for p in points if _parse_iso(p.get("at")) and _parse_iso(p["at"]) <= target]
    if not older:
        # Not enough history for this window — fall back to the earliest
        # point so we can still surface an "all-time" delta downstream.
        return points[0]
    # Pick the most recent point on-or-before the target (closest to the window).
    older.sort(key=lambda p: _parse_iso(p["at"]))
    return older[-1]


def _delta(current: Optional[int], baseline: Optional[int]) -> Optional[int]:
    if current is None or baseline is None:
        return None
    return int(current) - int(baseline)


def _build_window(points: list, current: dict, days: int) -> Optional[dict]:
    baseline = _pick_baseline(points, days)
    if baseline is None or baseline.get("summary_id") == current.get("summary_id"):
        return None
    return {
        "days": days,
        "from_at": baseline.get("at"),
        "to_at": current.get("at"),
        "overall": {
            "from": baseline.get("overall"),
            "to": current.get("overall"),
            "delta": _delta(current.get("overall"), baseline.get("overall")),
        },
        "dimensions": {
            k: {
                "from": baseline.get(k),
                "to": current.get(k),
                "delta": _delta(current.get(k), baseline.get(k)),
                "label": DIMENSION_LABELS[k],
            }
            for k in DIMENSION_KEYS
        },
    }


def _build_insights(points: list, windows: dict) -> list:
    """Pick 1-3 short human-readable insights for the dashboard callout.

    Priority order:
      1. Milestone crossings (crossed 55 → Moderately Ready, or 75 → Prepared)
      2. Biggest gain across any window (need +5 or more to matter)
      3. Biggest drop across any window (need -5 or worse to flag)
    """
    insights: list = []
    if len(points) < 2:
        return insights

    current = points[-1]
    previous = points[-2]

    # 1. Threshold crossings on the overall score.
    curr_overall, prev_overall = current.get("overall"), previous.get("overall")
    if curr_overall is not None and prev_overall is not None:
        if prev_overall < 75 <= curr_overall:
            insights.append({
                "kind": "milestone",
                "message": "You just crossed into Prepared for Mediation. This is a big deal — the shift shows up in how you talk about your child.",
            })
        elif prev_overall < 55 <= curr_overall:
            insights.append({
                "kind": "milestone",
                "message": "You've moved into Moderately Ready. Your foundation is starting to hold.",
            })

    # 2. Biggest gain across all windows.
    best = None
    worst = None
    for w in windows.values():
        if not w:
            continue
        for k, dim in w["dimensions"].items():
            d = dim.get("delta")
            if d is None:
                continue
            if best is None or d > best["delta"]:
                best = {"delta": d, "key": k, "label": dim["label"], "days": w["days"]}
            if worst is None or d < worst["delta"]:
                worst = {"delta": d, "key": k, "label": dim["label"], "days": w["days"]}

    if best and best["delta"] >= 5:
        insights.append({
            "kind": "gain",
            "message": f"You've grown {best['delta']} points in {best['label']} over the last {best['days']} days. That's real, measurable movement.",
        })
    if worst and worst["delta"] <= -5:
        insights.append({
            "kind": "watch",
            "message": f"{worst['label']} has dipped {abs(worst['delta'])} points over the last {worst['days']} days — a good area to bring to your coach.",
        })

    return insights[:3]


@router.get("/growth")
async def personal_growth(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Longitudinal growth tracking for the signed-in parent.

    Returns a timeline of readiness snapshots (from every generated summary)
    with dimension-level scores, plus 30/60/90-day comparison windows and a
    short list of coaching insights derived from meaningful movement.
    """
    db = request.app.state.db
    user_id = current.user_id

    cursor = db.summaries.find(
        {"user_id": user_id},
        {
            "_id": 0,
            "summary_id": 1,
            "generated_at": 1,
            "readiness_score": 1,
            "readiness_label": 1,
            "readiness": 1,
            "prep_snapshot": 1,
        },
    ).sort("generated_at", 1)
    docs = await cursor.to_list(500)

    points = [p for p in (_summary_to_point(d) for d in docs) if p is not None]

    if not points:
        return {
            "has_history": False,
            "points": [],
            "windows": {},
            "insights": [],
            "current": None,
            "first_snapshot_at": None,
            "days_tracked": 0,
        }

    current_point = points[-1]
    first_at = _parse_iso(points[0].get("at"))
    days_tracked = max(0, (_now() - first_at).days) if first_at else 0

    windows = {
        "30d": _build_window(points, current_point, 30),
        "60d": _build_window(points, current_point, 60),
        "90d": _build_window(points, current_point, 90),
    }

    insights = _build_insights(points, windows)

    return {
        "has_history": len(points) >= 2,
        "points": points,
        "windows": windows,
        "insights": insights,
        "current": current_point,
        "first_snapshot_at": points[0].get("at"),
        "days_tracked": days_tracked,
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

    # Consent analytics (iter187) — how many parents have toggled the
    # Child Needs share-consent on their joint cases, and how many
    # cases have BOTH parents opted in (i.e. how often the escape
    # hatch actually unlocks section 5 in a joint report).
    #   * `child_needs_share_consent_parents` counts distinct
    #     parents-list ENTRIES with a truthy `child_needs_share_consent_at`
    #     — a single parent on multiple cases counts once per case.
    #   * `child_needs_share_consent_cases_both` counts cases where
    #     BOTH parents on the case have consented. This is the number
    #     that actually matters: it's how many joint reports currently
    #     show Section 5 highlights.
    consent_pipeline = [
        {"$project": {
            "_id": 0,
            "a_in": {
                "$cond": [
                    {"$ifNull": [
                        {"$getField": {"field": "child_needs_share_consent_at",
                                        "input": {"$arrayElemAt": ["$parents", 0]}}},
                        False,
                    ]}, 1, 0,
                ],
            },
            "b_in": {
                "$cond": [
                    {"$ifNull": [
                        {"$getField": {"field": "child_needs_share_consent_at",
                                        "input": {"$arrayElemAt": ["$parents", 1]}}},
                        False,
                    ]}, 1, 0,
                ],
            },
        }},
        {"$group": {
            "_id": None,
            "parents_consented": {"$sum": {"$add": ["$a_in", "$b_in"]}},
            "cases_both_consented": {"$sum": {
                "$cond": [{"$and": [{"$eq": ["$a_in", 1]}, {"$eq": ["$b_in", 1]}]}, 1, 0]
            }},
            "cases_total": {"$sum": 1},
        }},
    ]
    consent_row = await db.joint_alignment_cases.aggregate(consent_pipeline).to_list(1)
    if consent_row:
        parents_consented = consent_row[0].get("parents_consented", 0)
        cases_both = consent_row[0].get("cases_both_consented", 0)
        cases_total = consent_row[0].get("cases_total", 0)
    else:
        parents_consented = cases_both = cases_total = 0

    # Nudge dismiss telemetry (iter189) — how many parents hit the ✕
    # on the SNCv2 report page nudge tile. Split into "first dismiss"
    # (will get the 7-day retry) vs "retry dismiss" (permanent hide).
    # Fires alongside the consent numbers so admins can spot friction:
    # a growing `dismiss_permanent_count` with a flat consent count
    # means the retry cadence isn't converting hesitant parents.
    nudge_first = await db[
        "child_needs_share_nudge_dismisses"
    ].count_documents({"is_retry_dismissal": False})
    nudge_permanent = await db[
        "child_needs_share_nudge_dismisses"
    ].count_documents({"is_retry_dismissal": True})
    nudge_first_7d = await db[
        "child_needs_share_nudge_dismisses"
    ].count_documents({
        "is_retry_dismissal": False,
        "created_at": {"$gte": now - timedelta(days=7)},
    })
    nudge_permanent_7d = await db[
        "child_needs_share_nudge_dismisses"
    ].count_documents({
        "is_retry_dismissal": True,
        "created_at": {"$gte": now - timedelta(days=7)},
    })

    consent_analytics = {
        "child_needs_share": {
            "parents_consented": int(parents_consented),
            "cases_both_consented": int(cases_both),
            "cases_total": int(cases_total),
            # Unlock rate = how many joint cases currently show
            # Section 5 highlights, as a percentage of all joint
            # cases with two accepted parents. 0 when denominator is 0.
            "unlock_rate_pct": (
                round((cases_both / cases_total) * 100) if cases_total else 0
            ),
            "nudge_dismisses": {
                "first_total": int(nudge_first),
                "permanent_total": int(nudge_permanent),
                "first_7d": int(nudge_first_7d),
                "permanent_7d": int(nudge_permanent_7d),
            },
        },
    }

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
        "consent": consent_analytics,
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

    # Batch-fetch progress + summary counts in two queries total (was N+1
    # per user). For the summary counts we group at the DB layer so we
    # never pull document bodies over the wire.
    user_ids = [u["user_id"] for u in users]

    prep_map: dict[str, dict] = {}
    if user_ids:
        prep_cursor = db.prep_data.find(
            {"user_id": {"$in": user_ids}},
            {"_id": 0, "user_id": 1, "completed": 1},
        )
        async for p in prep_cursor:
            prep_map[p["user_id"]] = p.get("completed") or {}

    summary_counts: dict[str, int] = {}
    if user_ids:
        pipeline = [
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        ]
        async for row in db.summaries.aggregate(pipeline):
            summary_counts[row["_id"]] = row["count"]

    enriched = []
    for u in users:
        completed_map = prep_map.get(u["user_id"], {})
        steps_done = sum(1 for s in PREP_SECTIONS if completed_map.get(s))
        enriched.append({
            **u,
            "steps_done": steps_done,
            "steps_total": len(PREP_SECTIONS),
            "summaries": summary_counts.get(u["user_id"], 0),
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



# ============ User management (admin) ============
from fastapi import Body  # noqa: E402
from pydantic import BaseModel  # noqa: E402

try:
    from email_service import send_magic_link as _send_magic_link  # noqa: E402
    from email_service import EmailNotConfigured, EmailSendError  # noqa: E402
except Exception:  # pragma: no cover
    _send_magic_link = None  # type: ignore
    EmailNotConfigured = EmailSendError = Exception  # type: ignore

import secrets as _secrets  # noqa: E402


def _public_user(doc: dict) -> dict:
    """Strip the user doc to fields safe for the admin panel."""
    return {
        "user_id": doc.get("user_id"),
        "email": doc.get("email"),
        "name": doc.get("name") or "",
        "auth_method": doc.get("auth_method", "jwt"),
        "is_guest": bool(doc.get("is_guest", False)),
        "guest_expires_at": doc.get("guest_expires_at"),
        "created_at": doc.get("created_at"),
        "suspended": bool(doc.get("suspended", False)),
        "suspended_at": doc.get("suspended_at"),
        "suspended_reason": doc.get("suspended_reason"),
    }


@router.get("/admin/users")
async def admin_list_users(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
    q: Optional[str] = None,
    suspended: Optional[bool] = None,
    include_guests: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """Paginated user list with optional name/email search + suspended filter."""
    db = request.app.state.db
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    query: dict = {}
    if not include_guests:
        query["is_guest"] = {"$ne": True}
    if suspended is True:
        query["suspended"] = True
    elif suspended is False:
        query["suspended"] = {"$ne": True}
    if q:
        q_safe = q.strip()
        if q_safe:
            esc = "".join(("\\" + c if c in r".*+?^$()[]{}|\\" else c) for c in q_safe)
            query["$or"] = [
                {"email": {"$regex": esc, "$options": "i"}},
                {"name": {"$regex": esc, "$options": "i"}},
            ]

    total = await db.users.count_documents(query)
    cursor = (
        db.users.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    rows = [_public_user(u) async for u in cursor]
    return {"users": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/admin/users/{user_id}")
async def admin_user_detail(
    user_id: str,
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    db = request.app.state.db
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found.")
    prep = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0}) or {}
    completed = prep.get("completed") or {}
    return {
        "user": _public_user(doc),
        "progress": {
            "completed": [k for k in PREP_SECTIONS if completed.get(k)],
            "remaining": [k for k in PREP_SECTIONS if not completed.get(k)],
            "steps_done": sum(1 for k in PREP_SECTIONS if completed.get(k)),
            "steps_total": len(PREP_SECTIONS),
        },
        "counts": {
            "summaries": await db.summaries.count_documents({"user_id": user_id}),
            "agreements": await db.agreements.count_documents({"user_id": user_id}),
            "improvement_plans": await db.improvement_plans.count_documents({"user_id": user_id}),
            "mediator_emails": await db.mediator_emails.count_documents({"user_id": user_id}),
            "journal_entries": await db.journal_entries.count_documents({"user_id": user_id}),
        },
    }


class SuspendBody(BaseModel):
    reason: Optional[str] = None


@router.post("/admin/users/{user_id}/suspend")
async def admin_suspend(
    user_id: str,
    request: Request,
    body: SuspendBody = Body(default_factory=SuspendBody),
    admin: UserPublic = Depends(require_admin),
):
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="You can't suspend your own account.")
    db = request.app.state.db
    res = await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "suspended": True,
                "suspended_at": _iso(_now()),
                "suspended_reason": (body.reason or "").strip() or None,
                "suspended_by": admin.email,
            }
        },
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"ok": True, "user_id": user_id, "suspended": True}


@router.post("/admin/users/{user_id}/unsuspend")
async def admin_unsuspend(
    user_id: str,
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    db = request.app.state.db
    res = await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {"suspended": False},
            "$unset": {"suspended_at": "", "suspended_reason": "", "suspended_by": ""},
        },
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"ok": True, "user_id": user_id, "suspended": False}


class ResetBody(BaseModel):
    expires_minutes: int = 60


@router.post("/admin/users/{user_id}/send-reset-link")
async def admin_send_reset_link(
    user_id: str,
    request: Request,
    body: ResetBody = Body(default_factory=ResetBody),
    _admin: UserPublic = Depends(require_admin),
):
    """Email the user a magic-link they can use to log in / reset their password.
    Reuses the existing magic-link infrastructure.
    """
    db = request.app.state.db
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found.")
    email = doc.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="User has no email on file.")

    token = _secrets.token_urlsafe(32)
    minutes = max(5, min(int(body.expires_minutes or 60), 60 * 24))
    expires = _now() + timedelta(minutes=minutes)
    await db.magic_links.insert_one({
        "token": token,
        "email": email.lower(),
        "mode": "signin",
        "used": False,
        "created_at": _iso(_now()),
        "expires_at": _iso(expires),
    })

    public_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
    link = f"{public_url}/auth/magic?token={token}" if public_url else f"/auth/magic?token={token}"

    if _send_magic_link is None:
        return {"ok": True, "emailed": False, "reason": "email-service-unavailable", "link": link}
    try:
        _send_magic_link(to_email=email, link_url=link, user_name=doc.get("name") or "")
    except EmailNotConfigured:
        return {"ok": True, "emailed": False, "reason": "smtp-not-configured", "link": link}
    except EmailSendError as exc:
        return {"ok": True, "emailed": False, "reason": f"smtp-error:{exc}"[:200], "link": link}
    return {"ok": True, "emailed": True, "expires_at": _iso(expires)}
