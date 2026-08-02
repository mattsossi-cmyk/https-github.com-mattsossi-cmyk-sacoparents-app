"""Progress Dashboard — five visual pills for /dashboard.

Read-only aggregator over existing collections. Each pill turns ✓ when
its criterion is met. Criteria are intentionally low-friction so parents
see progress early and stay motivated.

Pills:
  * foundation_completed     — safety assessment completed + user has a name
  * child_needs_identified   — at least one deep dive completed OR an SNC v2 report exists
  * communication_readiness  — mediation prep `comm_style` section saved
  * mediation_readiness      — 3+ mediation prep sections saved (any of child_goals,
                               issues, priority, comm_style, readiness, reflection)
  * conflict_reduced         — most-recent compare snapshot for the user has
                               aligned_pct >= 60 (across any pathway)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user, get_db


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


_MEDIATION_PREP_SECTIONS = ("child_goals", "issues", "priority", "comm_style",
                            "readiness", "reflection")

_DEEP_DIVE_ASSESSMENTS = ("edu_deep_assessments", "psych_deep_assessments",
                          "med_deep_assessments")

_DEEP_DIVE_SHARES = ("edu_deep_shares", "psych_deep_shares", "med_deep_shares")

_ALIGNMENT_THRESHOLD = 60
_HISTORY_COLLECTION = "progress_daily_history"
_HISTORY_DAYS = 30


async def _has_completed_safety(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """A safety assessment doc exists for the user (any level)."""
    row = await db["safety_assessments"].find_one({"user_id": user_id}, {"_id": 1})
    return bool(row)


async def _any_child_needs_signal(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """Either any deep dive completed, or an SNC v2 report exists."""
    for coll in _DEEP_DIVE_ASSESSMENTS:
        row = await db[coll].find_one({"user_id": user_id, "completed": True}, {"_id": 1})
        if row:
            return True
    row = await db["snc2_reports"].find_one({"user_id": user_id}, {"_id": 1})
    return bool(row)


def _saved_prep_sections(prep: Dict[str, Any]) -> List[str]:
    """Return the list of prep sections that have at least one saved value."""
    saved = []
    for k in _MEDIATION_PREP_SECTIONS:
        val = prep.get(k)
        # A prep section is "saved" if it exists as a non-empty dict / non-empty value.
        if isinstance(val, dict) and val:
            saved.append(k)
        elif isinstance(val, (list, str)) and val:
            saved.append(k)
    return saved


async def _latest_alignment_pct(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Find the user's most recent compare snapshot across all three
    pathways. Returns {aligned_pct: int|None, pathway: str|None}."""
    # Gather every share_id the user participates in across all pathways.
    share_id_to_pathway: Dict[str, str] = {}
    for coll in _DEEP_DIVE_SHARES:
        cursor = db[coll].find(
            {"user_pair": user_id, "status": {"$ne": "revoked"}},
            {"_id": 0, "share_id": 1},
        )
        pathway_key = coll.split("_", 1)[0]  # "edu" | "psych" | "med"
        async for s in cursor:
            share_id_to_pathway[s["share_id"]] = pathway_key
    if not share_id_to_pathway:
        return {"aligned_pct": None, "pathway": None}
    snap = await db["deep_dive_compare_snapshots"].find_one(
        {"share_id": {"$in": list(share_id_to_pathway.keys())}},
        {"_id": 0, "share_id": 1, "summary": 1},
        sort=[("created_at", -1)],
    )
    if not snap:
        return {"aligned_pct": None, "pathway": None}
    pct = (snap.get("summary") or {}).get("aligned_pct")
    try:
        pct = int(pct) if pct is not None else None
    except Exception:  # noqa: BLE001
        pct = None
    return {"aligned_pct": pct, "pathway": share_id_to_pathway.get(snap.get("share_id"))}


async def compute_progress(db: AsyncIOMotorDatabase, user: UserPublic) -> Dict[str, Any]:
    """Compute the five progress pills for a single user. Pure — no DB
    writes — so it can be reused by /progress AND certificate rendering.

    Return payload matches the /progress endpoint (minus history)."""
    prep = await db["prep_data"].find_one({"user_id": user.user_id}, {"_id": 0}) or {}

    has_safety = await _has_completed_safety(db, user.user_id)
    has_name = bool((user.name or "").strip())
    foundation_completed = has_safety and has_name

    child_needs_identified = await _any_child_needs_signal(db, user.user_id)

    saved_sections = _saved_prep_sections(prep)
    communication_readiness = "comm_style" in saved_sections
    mediation_readiness = len(saved_sections) >= 3

    alignment = await _latest_alignment_pct(db, user.user_id)
    conflict_reduced = (
        alignment["aligned_pct"] is not None
        and alignment["aligned_pct"] >= _ALIGNMENT_THRESHOLD
    )

    pills = [
        {
            "id": "foundation_completed",
            "label": "Foundation completed",
            "done": foundation_completed,
            "detail": (
                "Safety assessment saved + profile filled."
                if foundation_completed
                else ("Add your name in profile." if has_safety
                      else "Complete the Family Safety Assessment.")
            ),
        },
        {
            "id": "child_needs_identified",
            "label": "Child needs identified",
            "done": child_needs_identified,
            "detail": (
                "You've mapped your child's needs at least once."
                if child_needs_identified
                else "Finish one Special Needs deep dive or the Special Needs Compass."
            ),
        },
        {
            "id": "communication_readiness",
            "label": "Communication readiness",
            "done": communication_readiness,
            "detail": (
                "Communication Style module completed."
                if communication_readiness
                else "Complete the Communication Style prep module."
            ),
        },
        {
            "id": "mediation_readiness",
            "label": "Mediation readiness",
            "done": mediation_readiness,
            "detail": (
                f"{len(saved_sections)} of {len(_MEDIATION_PREP_SECTIONS)} prep sections saved."
                if mediation_readiness
                else f"Complete 3 prep sections (you have {len(saved_sections)})."
            ),
        },
        {
            "id": "conflict_reduced",
            "label": "Conflict reduced",
            "done": conflict_reduced,
            "detail": (
                f"Latest alignment: {alignment['aligned_pct']}%."
                if alignment["aligned_pct"] is not None
                else "Run a co-parent comparison to see your alignment."
            ),
        },
    ]
    completed_count = sum(1 for p in pills if p["done"])
    total = len(pills)
    return {
        "pills": pills,
        "completed_count": completed_count,
        "total": total,
        "foundation_ready": completed_count == total,
        "alignment_pct": alignment["aligned_pct"],
        "alignment_pathway": alignment["pathway"],
        "alignment_threshold": _ALIGNMENT_THRESHOLD,
    }


async def _upsert_today_history(db: AsyncIOMotorDatabase, user_id: str,
                                completed_count: int, total: int) -> None:
    """Persist today's completed_count so we can render a sparkline of
    momentum over time. Idempotent — one row per user per UTC date, updated
    whenever the user hits the /progress endpoint."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db[_HISTORY_COLLECTION].update_one(
        {"user_id": user_id, "date": today},
        {"$set": {
            "user_id": user_id,
            "date": today,
            "completed_count": int(completed_count),
            "total": int(total),
            "ready": completed_count == total,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def _read_history_series(db: AsyncIOMotorDatabase, user_id: str,
                               days: int = _HISTORY_DAYS) -> List[Dict[str, Any]]:
    """Return the last `days` days of history as a dense list — one entry
    per date from (today - days + 1) to today. Missing days are backfilled
    with the last known value so the sparkline stays continuous."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    cursor = db[_HISTORY_COLLECTION].find(
        {"user_id": user_id,
         "date": {"$gte": start.strftime("%Y-%m-%d"),
                  "$lte": end.strftime("%Y-%m-%d")}},
        {"_id": 0, "date": 1, "completed_count": 1, "total": 1, "ready": 1},
    ).sort("date", 1)
    by_date = {row["date"]: row async for row in cursor}
    series: List[Dict[str, Any]] = []
    last_done = 0
    last_total = 5
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        row = by_date.get(d)
        if row:
            last_done = int(row.get("completed_count") or 0)
            last_total = int(row.get("total") or 5)
        series.append({
            "date": d,
            "done": last_done,
            "total": last_total,
            "ready": last_done == last_total and last_total > 0,
        })
    return series


@router.get("/progress")
async def get_progress(user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Return the five progress pills for the /dashboard visual, plus a
    30-day sparkline of momentum. Upserts today's snapshot as a side effect
    so the history stays fresh without a separate cron job. Also logs a
    Public Milestone Wall event when a Foundation-Ready parent has opted
    in — silently, no-op for anyone who hasn't opted in."""
    body = await compute_progress(db, user)
    # Persist today's snapshot for the sparkline. Fire-and-forget for
    # resilience: a Mongo hiccup on the history collection must never
    # break the dashboard.
    try:
        await _upsert_today_history(db, user.user_id,
                                    body["completed_count"], body["total"])
    except Exception:  # noqa: BLE001
        pass
    try:
        history = await _read_history_series(db, user.user_id, days=_HISTORY_DAYS)
    except Exception:  # noqa: BLE001
        history = []
    body["history"] = history
    body["history_days"] = _HISTORY_DAYS
    # Public Milestone Wall — safe no-op unless opted in.
    try:
        from wall_routes import (
            maybe_log_foundation_ready, maybe_log_communication_master,
        )
        await maybe_log_foundation_ready(db, user.user_id,
                                         bool(body.get("foundation_ready")))
        # Communication Master badge: all 6 mediation-prep sections saved.
        prep = await db["prep_data"].find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        saved = _saved_prep_sections(prep)
        await maybe_log_communication_master(
            db, user.user_id, len(saved), len(_MEDIATION_PREP_SECTIONS),
        )
    except Exception:  # noqa: BLE001
        pass
    return body
