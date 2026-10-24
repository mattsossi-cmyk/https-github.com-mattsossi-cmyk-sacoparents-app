"""Anonymous counts of which ready-made Journey Guide questions parents tap.

Only the question id, where it was tapped (reading / guided) and the day are kept, as a daily counter.
No user id, session, IP or device is stored or logged.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal

from fastapi import APIRouter, Depends, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from analytics_routes import require_admin
from auth import UserPublic, get_db

TREND_WEEKS = 8
QUESTION_IDS = ("safety", "coparenting", "parallel", "choose", "pages", "switch", "report", "help")
_COLL = "guide_question_tap_counts"

router = APIRouter(prefix="/guide-questions", tags=["guide-questions"])
admin_router = APIRouter(prefix="/admin/guide-questions", tags=["admin"])


class TapIn(BaseModel):
    question_id: Literal["safety", "coparenting", "parallel", "choose", "pages", "switch", "report", "help"]
    where: Literal["reading", "guided"]


@router.post("/tap", status_code=204, response_class=Response)
async def count_tap(body: TapIn, db: AsyncIOMotorDatabase = Depends(get_db)) -> Response:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db[_COLL].update_one(
        {"day": day, "question_id": body.question_id, "where": body.where},
        {"$inc": {"count": 1}},
        upsert=True,
    )
    return Response(status_code=204)


class QuestionStat(BaseModel):
    question_id: str
    all_time: int
    last_30_days: int
    reading: int
    guided: int
    weekly: List[int]  # taps per 7-day week, oldest first; the last entry is the current week (today and the 6 days before)


class StatsOut(BaseModel):
    questions: List[QuestionStat]
    total_all_time: int
    total_last_30_days: int


@admin_router.get("/stats", response_model=StatsOut)
async def tap_stats(
    _admin: UserPublic = Depends(require_admin), db: AsyncIOMotorDatabase = Depends(get_db)
) -> StatsOut:
    today = datetime.now(timezone.utc).date()
    since = (today - timedelta(days=29)).isoformat()
    totals: Dict[str, Dict] = {
        q: {"all_time": 0, "last_30_days": 0, "reading": 0, "guided": 0, "weekly": [0] * TREND_WEEKS} for q in QUESTION_IDS
    }
    async for d in db[_COLL].find({}, {"_id": 0, "day": 1, "question_id": 1, "where": 1, "count": 1}):
        t = totals.get(d.get("question_id"))
        if t is None:
            continue
        n = int(d.get("count") or 0)
        t["all_time"] += n
        t[d.get("where") if d.get("where") in ("reading", "guided") else "reading"] += n
        if (d.get("day") or "") >= since:
            t["last_30_days"] += n
        try:
            weeks_ago = (today - datetime.strptime(d.get("day") or "", "%Y-%m-%d").date()).days // 7
        except ValueError:
            continue
        if 0 <= weeks_ago < TREND_WEEKS:
            t["weekly"][TREND_WEEKS - 1 - weeks_ago] += n
    rows = sorted(
        (QuestionStat(question_id=q, **v) for q, v in totals.items()),
        key=lambda r: (-r.all_time, -r.last_30_days, QUESTION_IDS.index(r.question_id)),
    )
    return StatsOut(
        questions=rows,
        total_all_time=sum(r.all_time for r in rows),
        total_last_30_days=sum(r.last_30_days for r in rows),
    )
