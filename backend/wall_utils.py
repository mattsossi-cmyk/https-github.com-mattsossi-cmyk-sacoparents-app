"""Wall utilities — anonymised badge-logging helpers reused by the
Public Milestone Wall route AND the Progress Dashboard route.

This module exists so that `progress_dashboard_routes.py` and
`wall_routes.py` don't need to import each other at module load time
(previously a circular import: wall imported `compute_progress`, and
progress imported the `maybe_log_*` helpers).

Only pure helpers live here — no FastAPI routes.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


# ---------------------------------------------------------------------------
# Collection / badge constants
# ---------------------------------------------------------------------------
OPT_IN_COLLECTION = "wall_opt_in"
EVENTS_COLLECTION = "wall_events"
CHEERS_COLLECTION = "wall_cheers"

BADGE_FOUNDATION_READY = "foundation_ready"
BADGE_FIRST_COMPARE = "first_compare"
BADGE_HIGH_ALIGNMENT_90 = "high_alignment_90"
BADGE_COMMUNICATION_MASTER = "communication_master"
BADGE_WEEK_STREAK_7 = "week_streak_7"
BADGE_MONTH_STREAK_30 = "month_streak_30"
BADGE_HUNDRED_DAY_STREAK = "hundred_day_streak"

_ANON_SALT_ENV = "WALL_ANON_SALT"

# Human labels for badge types shown on the feed AND inside the weekly email.
BADGE_LABELS: Dict[str, str] = {
    BADGE_FOUNDATION_READY:     "lit all five milestones — Foundation Ready.",
    BADGE_FIRST_COMPARE:        "ran their first co-parent comparison.",
    BADGE_HIGH_ALIGNMENT_90:    "hit 90%+ alignment with their co-parent.",
    BADGE_COMMUNICATION_MASTER: "completed every mediation-prep section — Communication Master.",
    BADGE_WEEK_STREAK_7:        "showed up 7 days in a row — Consistent Coparent.",
    BADGE_MONTH_STREAK_30:      "showed up 30 days in a row — Month of Steadiness.",
    BADGE_HUNDRED_DAY_STREAK:   "showed up 100 days in a row — Century of Care.",
}

# Badges we only ever want to log once per parent (life-time). Others use a
# 24-hour de-dupe so a flicker back-and-forth doesn't spam the wall but a
# re-earn a week later still shows up. The 30- and 100-day streaks are so
# rare (and represent so much sustained work) that we treat them as
# lifetime — even if the streak breaks and is rebuilt, the *first* time a
# parent hit it is the achievement worth celebrating.
LIFETIME_BADGES = frozenset({
    BADGE_FIRST_COMPARE,
    BADGE_COMMUNICATION_MASTER,
    BADGE_MONTH_STREAK_30,
    BADGE_HUNDRED_DAY_STREAK,
})


# Category filter groupings for the wall feed. Keys are the query-param
# values the frontend chip row sends; values are the list of badge_type
# strings that belong to that chip. Sub-groups are DISJOINT so per-
# category counts don't double-count a single event. `milestones` is
# the union of the three sub-groups — the "just the streak-and-badge
# stories" chip parents can tap to zoom past casual noise.
CATEGORY_BADGES: Dict[str, list] = {
    "streaks": [
        BADGE_WEEK_STREAK_7,
        BADGE_MONTH_STREAK_30,
        BADGE_HUNDRED_DAY_STREAK,
    ],
    "foundations": [
        BADGE_FOUNDATION_READY,
        BADGE_FIRST_COMPARE,
        BADGE_COMMUNICATION_MASTER,
    ],
    "alignment": [
        BADGE_HIGH_ALIGNMENT_90,
    ],
}
CATEGORY_BADGES["milestones"] = (
    CATEGORY_BADGES["streaks"]
    + CATEGORY_BADGES["foundations"]
    + CATEGORY_BADGES["alignment"]
)


def anon_hash(user_id: str) -> str:
    """Stable, non-reversible hash of the user_id. Combined with a salt
    from the environment so a stolen DB copy can't be joined back to
    users. Falls back to a deterministic placeholder salt in dev so the
    hash stays consistent across process restarts."""
    salt = os.environ.get(_ANON_SALT_ENV) or "sacop-wall-anon-salt-dev-only"
    return hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()[:16]


async def get_opt_in(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    row = await db[OPT_IN_COLLECTION].find_one({"user_id": user_id}, {"_id": 0})
    return bool(row and row.get("opt_in"))


async def set_opt_in(db: AsyncIOMotorDatabase, user_id: str, opt_in: bool) -> None:
    await db[OPT_IN_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "opt_in": bool(opt_in),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def log_event_once(db: AsyncIOMotorDatabase, user_id: str,
                         badge_type: str) -> Optional[Dict[str, Any]]:
    """Log a badge event iff (1) the user is opted-in AND (2) they haven't
    logged this badge in the dedupe window. Lifetime badges (first_compare,
    communication_master) never re-log; other badges use a 24-hour window so
    a flicker at 4/5 → 5/5 → 4/5 → 5/5 doesn't spam the wall."""
    if not await get_opt_in(db, user_id):
        return None
    if badge_type in LIFETIME_BADGES:
        prior = await db[EVENTS_COLLECTION].find_one(
            {"user_id": user_id, "badge_type": badge_type}, {"_id": 1},
        )
        if prior:
            return None
    else:
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        recent = await db[EVENTS_COLLECTION].find_one({
            "user_id": user_id,
            "badge_type": badge_type,
            "created_at": {"$gte": twenty_four_hours_ago.isoformat()},
        }, {"_id": 1})
        if recent:
            return None
    now = datetime.now(timezone.utc)
    doc = {
        "event_id": f"wall_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "user_hash": anon_hash(user_id),
        "badge_type": badge_type,
        "created_at": now.isoformat(),
    }
    await db[EVENTS_COLLECTION].insert_one(doc)
    return doc


# ---------------------------------------------------------------------------
# Public "maybe_log_*" helpers — called from other routes on every relevant
# transition. Each one is a safe no-op unless the user is opted-in.
# ---------------------------------------------------------------------------
async def maybe_log_foundation_ready(db: AsyncIOMotorDatabase, user_id: str,
                                     foundation_ready: bool) -> None:
    """No-op unless the user is opted-in AND currently Foundation-Ready."""
    if not foundation_ready:
        return
    try:
        await log_event_once(db, user_id, BADGE_FOUNDATION_READY)
    except Exception:  # noqa: BLE001
        # Never let a wall-side failure break the dashboard.
        pass


async def maybe_log_first_compare(db: AsyncIOMotorDatabase,
                                  user_ids: List[str]) -> None:
    """Log a first_compare badge for each participant that has never
    earned it before. Called when a compare share transitions to
    both-consented ("active")."""
    for uid in user_ids or []:
        if not uid:
            continue
        try:
            await log_event_once(db, uid, BADGE_FIRST_COMPARE)
        except Exception:  # noqa: BLE001
            pass


async def maybe_log_high_alignment(db: AsyncIOMotorDatabase,
                                   user_ids: List[str],
                                   aligned_pct: Optional[int]) -> None:
    """Log a 90%+ alignment badge for each participant. Called when a
    compare snapshot is persisted."""
    if aligned_pct is None or aligned_pct < 90:
        return
    for uid in user_ids or []:
        if not uid:
            continue
        try:
            await log_event_once(db, uid, BADGE_HIGH_ALIGNMENT_90)
        except Exception:  # noqa: BLE001
            pass


async def maybe_log_communication_master(db: AsyncIOMotorDatabase,
                                         user_id: str,
                                         saved_prep_sections: int,
                                         total_prep_sections: int) -> None:
    """Log a Communication Master badge once when a parent has saved every
    mediation-prep section."""
    if total_prep_sections <= 0 or saved_prep_sections < total_prep_sections:
        return
    try:
        await log_event_once(db, user_id, BADGE_COMMUNICATION_MASTER)
    except Exception:  # noqa: BLE001
        pass


async def maybe_log_week_streak(db: AsyncIOMotorDatabase, user_id: str,
                                streak_days: int) -> None:
    """Log a 7-day streak badge when the parent hits a full week of
    consecutive dashboard visits. 24-hour de-dupe on the wall event so
    a parent who breaks the streak and re-earns later still gets a fresh
    celebration."""
    if streak_days < 7:
        return
    try:
        await log_event_once(db, user_id, BADGE_WEEK_STREAK_7)
    except Exception:  # noqa: BLE001
        pass


async def maybe_log_month_streak(db: AsyncIOMotorDatabase, user_id: str,
                                 streak_days: int) -> None:
    """Log the 30-day streak badge when the parent first hits a full
    month of consecutive dashboard visits. Lifetime — never re-logs."""
    if streak_days < 30:
        return
    try:
        await log_event_once(db, user_id, BADGE_MONTH_STREAK_30)
    except Exception:  # noqa: BLE001
        pass


async def maybe_log_hundred_day_streak(db: AsyncIOMotorDatabase, user_id: str,
                                       streak_days: int) -> None:
    """Log the 100-day streak badge when the parent first hits a full
    hundred consecutive days of dashboard visits. Lifetime — never
    re-logs. This one is rare and worth marking permanently."""
    if streak_days < 100:
        return
    try:
        await log_event_once(db, user_id, BADGE_HUNDRED_DAY_STREAK)
    except Exception:  # noqa: BLE001
        pass


async def build_weekly_cheer_digest(db: AsyncIOMotorDatabase, user_id: str,
                                    week_start: datetime,
                                    ) -> Dict[str, Any]:
    """Build the 'community cheers' block for a parent's Sunday weekly
    email. Returns two lists:

    * ``cheers_received`` — one row per badge the parent has earned in
      the last 30 days, with the count of cheers landed on that badge
      SINCE ``week_start``. Only badges that got at least one cheer this
      week appear. Cheerer identity is NEVER included (respects the
      wall anonymity model).
    * ``community_pulse`` — up to three most-cheered PUBLIC badges
      earned by ANY parent this week (anonymised). Included even if the
      parent isn't opted-in themselves, so opted-out parents still feel
      the community momentum.

    Also returns ``opted_in`` so the email/preview can label the block
    correctly (private users see only community_pulse).
    """
    opted_in = await get_opt_in(db, user_id)
    week_start_iso = week_start.isoformat()
    thirty_days_ago = (week_start - timedelta(days=23)).isoformat()

    cheers_received: List[Dict[str, Any]] = []
    if opted_in:
        events_cursor = db[EVENTS_COLLECTION].find(
            {"user_id": user_id, "created_at": {"$gte": thirty_days_ago}},
            {"_id": 0, "event_id": 1, "badge_type": 1, "created_at": 1},
        )
        my_events = [row async for row in events_cursor]
        if my_events:
            event_ids = [e["event_id"] for e in my_events]
            pipeline = [
                {"$match": {
                    "event_id": {"$in": event_ids},
                    "created_at": {"$gte": week_start_iso},
                }},
                {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
            ]
            counts: Dict[str, int] = {}
            async for row in db[CHEERS_COLLECTION].aggregate(pipeline):
                counts[row["_id"]] = int(row["n"])
            for ev in my_events:
                n = counts.get(ev["event_id"], 0)
                if n <= 0:
                    continue
                cheers_received.append({
                    "badge_type":  ev["badge_type"],
                    "badge_label": BADGE_LABELS.get(ev["badge_type"], ev["badge_type"]),
                    "cheer_count": n,
                    "earned_at":   ev["created_at"],
                })
            cheers_received.sort(key=lambda r: (-r["cheer_count"], r["earned_at"]))

    community_pulse: List[Dict[str, Any]] = []
    pulse_pipeline = [
        {"$match": {"created_at": {"$gte": week_start_iso}}},
        {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 8},  # narrow, then join in Python for viewer_id filter
    ]
    top_rows = [row async for row in db[CHEERS_COLLECTION].aggregate(pulse_pipeline)]
    if top_rows:
        top_event_ids = [r["_id"] for r in top_rows]
        counts_by_id = {r["_id"]: int(r["n"]) for r in top_rows}
        # Drop events that belong to the viewer — no point telling them
        # "someone cheered your own badge" twice; we already handled that
        # in cheers_received.
        events_cursor = db[EVENTS_COLLECTION].find(
            {"event_id": {"$in": top_event_ids}},
            {"_id": 0, "event_id": 1, "badge_type": 1, "user_id": 1, "user_hash": 1},
        )
        found = 0
        async for ev in events_cursor:
            if ev.get("user_id") == user_id:
                continue
            community_pulse.append({
                "badge_type":  ev["badge_type"],
                "badge_label": BADGE_LABELS.get(ev["badge_type"], ev["badge_type"]),
                "cheer_count": counts_by_id.get(ev["event_id"], 0),
                "user_hash":   ev["user_hash"],
            })
            found += 1
            if found >= 3:
                break
        community_pulse.sort(key=lambda r: -r["cheer_count"])

    return {
        "opted_in":         bool(opted_in),
        "cheers_received":  cheers_received,
        "community_pulse":  community_pulse,
        "week_start":       week_start.isoformat(),
    }
