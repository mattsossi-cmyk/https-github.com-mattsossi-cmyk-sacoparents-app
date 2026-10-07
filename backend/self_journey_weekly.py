"""Weekly Self Journey note — Sunday 5pm Central, only for parents who made progress that week.

Same safety rules as the reassess reminders: safety-flagged parents never get it,
plain subject line, one-tap unsubscribe, at most one note per user per ISO week.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import JWT_ALGO, JWT_SECRET
from self_assessment_reminders import is_safety_flagged

logger = logging.getLogger(__name__)

UNSUB_KIND = "sj_weekly_unsub"
CLICK_KIND = "sj_weekly_click"
NOTES = "self_journey_weekly_notes"
PREFS = "self_journey_weekly_prefs"
CN_NAMES = {"medical": "Medical", "educational": "Educational", "psychological": "Psychological"}
RETURN_WINDOW = timedelta(days=7)


def make_unsubscribe_token(user_id: str) -> str:
    return jwt.encode({"kind": UNSUB_KIND, "sub": user_id}, JWT_SECRET, algorithm=JWT_ALGO)


def make_click_token(user_id: str, week_key: str) -> str:
    return jwt.encode({"kind": CLICK_KIND, "sub": user_id, "wk": week_key}, JWT_SECRET, algorithm=JWT_ALGO)


def read_click_token(token: str) -> Optional[Dict[str, str]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"require": ["kind", "sub", "wk"]})
    except jwt.PyJWTError:
        return None
    return payload if payload.get("kind") == CLICK_KIND else None


def read_unsubscribe_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"require": ["kind", "sub"]})
    except jwt.PyJWTError:
        return None
    return payload["sub"] if payload.get("kind") == UNSUB_KIND else None


def _week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y:04d}-W{w:02d}"


def _streak(dates: List[str]) -> int:
    days = sorted({date.fromisoformat(d) for d in dates}, reverse=True)
    run = 1 if days else 0
    for a, b in zip(days, days[1:]):
        if a - b != timedelta(days=1):
            break
        run += 1
    return run


def _join(names: List[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


async def collect_activity(db: AsyncIOMotorDatabase, now: datetime) -> Dict[str, Dict[str, Any]]:
    start = now - timedelta(days=7)
    since, since_day = start.isoformat(), start.date().isoformat()
    acts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"sa": 0, "days": set(), "streak": 0, "cp": 0, "cn": [], "fb": False})
    async for r in db.self_assessment_history.find({"completed_at": {"$gte": since}}, {"_id": 0, "user_id": 1}):
        acts[r["user_id"]]["sa"] += 1
    async for r in db.self_assessment_checkins.find({"date": {"$gte": since_day}}, {"_id": 0, "user_id": 1, "date": 1}):
        acts[r["user_id"]]["days"].add(r["date"])
    async for r in db.cp_report_history.find({"snapshots.submitted_at": {"$gte": since}}, {"snapshots.submitted_at": 1}):
        acts[r["_id"]]["cp"] = sum((s.get("submitted_at") or "") >= since for s in r.get("snapshots") or [])
    async for r in db.child_needs_assessments.find({"updated_at": {"$gte": since}}, {"_id": 0, "user_id": 1, "completed_at": 1}):
        done = [CN_NAMES[k] for k, v in (r.get("completed_at") or {}).items() if k in CN_NAMES and (v or "") >= since]
        if done:
            acts[r["user_id"]]["cn"] = done
    async for r in db.foundation_builder.find({"updated_at": {"$gte": since}}, {"_id": 0, "user_id": 1}):
        acts[r["user_id"]]["fb"] = True
    for uid, a in acts.items():
        if a["days"]:
            rows = await db.self_assessment_checkins.find({"user_id": uid}, {"_id": 0, "date": 1}).to_list(2000)
            a["streak"] = _streak([x["date"] for x in rows if x["date"] <= max(a["days"])])
    return acts


def build_highlights(a: Dict[str, Any]) -> List[str]:
    out = []
    if a["sa"]:
        out.append("Completed a Self-Assessment" if a["sa"] == 1 else f"Completed {a['sa']} Self-Assessments")
    if a["days"]:
        n = len(a["days"])
        line = f"Practised your personal goal on {n} day{'s' if n != 1 else ''}"
        out.append(line + (f", with a {a['streak']}-day streak" if a["streak"] >= 2 else ""))
    if a["cp"]:
        out.append("Completed the Co-Parenting Relationship assessment")
    if a["cn"]:
        out.append(f"Completed the {_join(a['cn'])} needs assessment{'s' if len(a['cn']) > 1 else ''}")
    if a["fb"]:
        out.append("Worked on your Foundation Statement")
    return out


async def send_weekly_notes(
    db: AsyncIOMotorDatabase, *, api_url: str, now: Optional[datetime] = None,
) -> Dict[str, int]:
    from email_service import EmailNotConfigured, EmailSendError, send_self_journey_weekly_note

    now = now or datetime.now(timezone.utc)
    week = _week_key(now)
    stats = {"active": 0, "sent": 0, "failed": 0, "skipped_safety": 0, "skipped_unsubscribed": 0,
             "skipped_no_email": 0, "already_sent": 0}
    for user_id, a in (await collect_activity(db, now)).items():
        highlights = build_highlights(a)
        if not highlights:
            continue
        stats["active"] += 1
        if await db[NOTES].find_one({"user_id": user_id, "week_key": week, "status": "sent"}):
            stats["already_sent"] += 1
            continue
        if await db[PREFS].find_one({"user_id": user_id, "unsubscribed": True}):
            stats["skipped_unsubscribed"] += 1
            continue
        if await is_safety_flagged(db, user_id):
            stats["skipped_safety"] += 1
            continue
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1, "name": 1, "is_guest": 1,
                                                                "email_bounced": 1, "email_complained": 1})
        if not user or not user.get("email") or user.get("is_guest") or user.get("email_bounced") \
                or user.get("email_complained"):
            stats["skipped_no_email"] += 1
            continue
        status = "sent"
        try:
            send_self_journey_weekly_note(
                to_email=user["email"],
                first_name=(user.get("name") or "").split(" ")[0] or None,
                highlights=highlights,
                cta_url=f"{api_url.rstrip('/')}/api/self-journey/weekly-note/open?token={make_click_token(user_id, week)}",
                unsubscribe_url=f"{api_url.rstrip('/')}/api/self-journey/weekly-note/unsubscribe"
                                f"?token={make_unsubscribe_token(user_id)}",
            )
            stats["sent"] += 1
        except (EmailNotConfigured, EmailSendError) as exc:
            status = "failed"
            stats["failed"] += 1
            logger.warning("self-journey weekly note failed for %s: %s", user_id, exc)
        await db[NOTES].update_one(
            {"user_id": user_id, "week_key": week},
            {"$set": {"status": status, "sent_at": now.isoformat(), "highlights": highlights}},
            upsert=True,
        )
    return stats


async def came_back(db: AsyncIOMotorDatabase, user_id: str, start: str, end: str) -> bool:
    rng = {"$gt": start, "$lte": end}
    if await db.self_assessment_history.find_one({"user_id": user_id, "completed_at": rng}, {"_id": 1}):
        return True
    if await db.self_assessment_checkins.find_one({"user_id": user_id, "created_at": rng}, {"_id": 1}):
        return True
    if await db.cp_report_history.find_one({"_id": user_id, "snapshots": {"$elemMatch": {"submitted_at": rng}}}, {"_id": 1}):
        return True
    for coll in ("child_needs_assessments", "foundation_builder"):
        if await db[coll].find_one({"user_id": user_id, "updated_at": rng}, {"_id": 1}):
            return True
    return False


async def weekly_stats(db: AsyncIOMotorDatabase, *, weeks: int = 8, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    keys = sorted(await db[NOTES].distinct("week_key", {"status": "sent"}), reverse=True)[:weeks]
    rows = []
    for wk in keys:
        notes = await db[NOTES].find({"week_key": wk, "status": "sent"}, {"_id": 0}).to_list(10000)
        progressed = 0
        for n in notes:
            end = (datetime.fromisoformat(n["sent_at"]) + RETURN_WINDOW).isoformat()
            progressed += await came_back(db, n["user_id"], n["sent_at"], end)
        first = min(n["sent_at"] for n in notes)
        rows.append({
            "week_key": wk,
            "sent_on": first,
            "sent": len(notes),
            "progressed": progressed,
            "clicked": sum(1 for n in notes if n.get("clicked_at")),
            "counting": now < datetime.fromisoformat(max(n["sent_at"] for n in notes)) + RETURN_WINDOW,
        })
    totals = {k: sum(r[k] for r in rows) for k in ("sent", "progressed", "clicked")}
    return {"weeks": rows, "totals": totals}
