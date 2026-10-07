"""Admin view + manual trigger for the post-release smoke check."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from analytics_routes import require_admin
from auth import UserPublic, get_db
from release_check import RUNS, origin_from_request, remember_origin, run_release_check

router = APIRouter(prefix="/admin/release-checks", tags=["admin"])


@router.get("")
async def list_release_checks(
    request: Request,
    limit: int = 10,
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    await remember_origin(db, origin_from_request(request))
    rows = await db[RUNS].find({}, {"_id": 0}).sort("started_at", -1).limit(max(1, min(limit, 50))).to_list(None)
    return {"runs": rows}


@router.post("/run")
async def run_release_check_now(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    origin = origin_from_request(request)
    await remember_origin(db, origin)
    return await run_release_check(db, base_url=origin, trigger="manual")
