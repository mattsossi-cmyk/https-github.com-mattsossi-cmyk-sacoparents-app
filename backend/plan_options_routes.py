"""Co-Parenting Option Builder. With a parallel_parenting referral (from the case settings) only parallel and
protective options are returned, for both parents alike. Picks are private to each parent."""
import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import case_safety as cs
from auth import get_current_user, get_db
from models import UserPublic

router = APIRouter(prefix="/plan-options", tags=["plan-options"])
CONTENT = json.loads((Path(__file__).parent / "plan_options_content.json").read_text())
PICKS = "plan_option_picks"
NO_STORE = {"Cache-Control": "no-store"}


async def _visible(db, user: UserPublic):
    ids = await cs.case_ids_for(db, user.user_id)
    res = cs.combine([await cs.resolved_for_case(db, c, "user", user.user_id) for c in ids])
    parallel_only = res["referral"] == "parallel_parenting"
    return [
        {"key": c["key"], "label": c["label"], "options": [
            {"id": o["id"], "title": o["title"], "description": o["description"]}
            for o in c["options"] if not parallel_only or o["kind"] == "parallel"
        ]}
        for c in CONTENT["categories"]
    ]


def _ids(categories) -> set:
    return {o["id"] for c in categories for o in c["options"]}


@router.get("")
async def plan_options(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    return JSONResponse({"categories": await _visible(db, current)}, headers=NO_STORE)


class PicksIn(BaseModel):
    picks: List[str] = Field(default_factory=list, max_length=50)


@router.get("/picks")
async def get_picks(current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    visible = _ids(await _visible(db, current))
    doc = await db[PICKS].find_one({"user_id": current.user_id}, {"_id": 0, "picks": 1}) or {}
    return {"picks": [p for p in doc.get("picks", []) if p in visible]}


@router.put("/picks")
async def save_picks(body: PicksIn, current: UserPublic = Depends(get_current_user), db=Depends(get_db)):
    visible = _ids(await _visible(db, current))
    picks = [p for p in dict.fromkeys(body.picks) if p in visible]
    await db[PICKS].update_one(
        {"user_id": current.user_id}, {"$set": {"picks": picks, "updated_at": cs.now_iso()}}, upsert=True
    )
    return {"picks": picks}
