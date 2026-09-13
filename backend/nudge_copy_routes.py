"""Nudge Copy config — admin-editable microcopy for the
Child-Needs share nudge on the SNCv2 report page.

Product intent: after a few weeks of `iter189` telemetry (retry
vs permanent-dismiss counts on the admin tile), the team may want
to test alternative headline/subhead wording without cutting a
new build. This module ships:

  * GET  /api/public/nudge-copy/child-needs-share   (unauth)
      Returns the current headline + subhead. Falls back to the
      hardcoded defaults if no admin has customised them.
      Fire-and-forget from the nudge component on mount.

  * POST /api/admin/nudge-copy/child-needs-share    (admin only)
      Body `{ headline: str, subhead: str, note?: str }` — persists
      to the `nudge_copy_config` collection. `note` is a free-text
      audit field ("softer variant, week of 2026-09-15" etc).

Storage: singleton doc per `key`, upserted, tracked with
`updated_at`/`updated_by`. Never returns admin identity to the
public endpoint.

Not an A/B framework — a manual override. If the team wants
per-user variant assignment later, we can add a `variants: [...]`
array + hash(user_id) → variant selection on top of this schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from analytics_routes import require_admin
from auth import UserPublic


router = APIRouter(tags=["nudge-copy"])

_COLL = "nudge_copy_config"
_KEY_CHILD_NEEDS_SHARE = "child_needs_share_nudge"

_DEFAULTS = {
    _KEY_CHILD_NEEDS_SHARE: {
        "headline": "Share these highlights with your co-parent's joint report?",
        "subhead": (
            "By default your Child Needs highlights stay private. If you "
            "toggle this on for a case, section 5 of the joint Complete "
            "Alignment Report only surfaces your highlights *after* your "
            "co-parent also toggles it on. You can revoke anytime."
        ),
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


class NudgeCopyPayload(BaseModel):
    """Admin update body. Both fields are trimmed and length-capped so
    an oversized headline can't blow up the nudge card layout."""
    headline: str = Field(..., min_length=6, max_length=120)
    subhead: str = Field(..., min_length=10, max_length=600)
    note: Optional[str] = Field(default=None, max_length=200)

    @field_validator("headline", "subhead")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class NudgeCopyPublic(BaseModel):
    headline: str
    subhead: str
    is_default: bool  # True when no admin has customised → fell back to defaults


async def _resolve(db: AsyncIOMotorDatabase, key: str) -> NudgeCopyPublic:
    row = await db[_COLL].find_one({"key": key}, {"_id": 0})
    if row and row.get("headline") and row.get("subhead"):
        return NudgeCopyPublic(
            headline=row["headline"],
            subhead=row["subhead"],
            is_default=False,
        )
    d = _DEFAULTS.get(key) or _DEFAULTS[_KEY_CHILD_NEEDS_SHARE]
    return NudgeCopyPublic(
        headline=d["headline"], subhead=d["subhead"], is_default=True,
    )


# ------------------------------ Public read ------------------------------ #

@router.get("/public/nudge-copy/child-needs-share", response_model=NudgeCopyPublic)
async def get_child_needs_share_nudge_copy(
    db: AsyncIOMotorDatabase = Depends(_get_db),
):
    """Public — no auth. The nudge component fetches this on mount and
    falls back to its hardcoded defaults if the endpoint 5xx's. So
    tolerance to admin errors is high, but a cached CDN response
    should NEVER outlive an admin edit → `Cache-Control: no-store`.

    Uses `no-store` via header on the response (FastAPI's default is
    no cache header — we set it explicitly for clarity)."""
    from fastapi.responses import JSONResponse
    copy = await _resolve(db, _KEY_CHILD_NEEDS_SHARE)
    return JSONResponse(copy.model_dump(), headers={"Cache-Control": "no-store"})


# ------------------------------ Admin write ------------------------------ #

@router.post("/admin/nudge-copy/child-needs-share", response_model=NudgeCopyPublic)
async def set_child_needs_share_nudge_copy(
    payload: NudgeCopyPayload,
    request: Request,
    admin: UserPublic = Depends(require_admin),
):
    """Admin override. Upserts the singleton row, records who + when.

    Returns the new resolved copy (identical fields the public
    endpoint would return on the next fetch) so the admin UI can
    render an "updated" state without a second round-trip.
    """
    db = _get_db(request)
    await db[_COLL].update_one(
        {"key": _KEY_CHILD_NEEDS_SHARE},
        {
            "$set": {
                "headline": payload.headline,
                "subhead": payload.subhead,
                "note": payload.note,
                "updated_at": _now(),
                "updated_by": admin.email,
            },
            "$setOnInsert": {"key": _KEY_CHILD_NEEDS_SHARE, "created_at": _now()},
        },
        upsert=True,
    )
    return await _resolve(db, _KEY_CHILD_NEEDS_SHARE)


@router.post("/admin/nudge-copy/child-needs-share/reset", response_model=NudgeCopyPublic)
async def reset_child_needs_share_nudge_copy(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Nuke the admin override → the public endpoint falls back to
    the hardcoded defaults. Useful when a copy experiment goes
    sideways and you want to revert in one click."""
    db = _get_db(request)
    await db[_COLL].delete_one({"key": _KEY_CHILD_NEEDS_SHARE})
    return await _resolve(db, _KEY_CHILD_NEEDS_SHARE)
