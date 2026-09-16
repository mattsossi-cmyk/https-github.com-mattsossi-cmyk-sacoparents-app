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
      audit field ("softer variant, week of 2026-09-15" etc). Every
      successful save also appends a row to `nudge_copy_history` so
      admins can restore prior wording without retyping.

  * GET  /api/admin/nudge-copy/child-needs-share/history (admin only)
      Last N versions from `nudge_copy_history`, newest-first. The
      editor renders these as "Restore" buttons so an admin who ran
      an unsuccessful copy experiment can roll back in one click.

Storage: singleton doc per `key`, upserted, tracked with
`updated_at`/`updated_by`. Never returns admin identity to the
public endpoint.

Not an A/B framework — a manual override. If the team wants
per-user variant assignment later, we can add a `variants: [...]`
array + hash(user_id) → variant selection on top of this schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from analytics_routes import require_admin
from auth import UserPublic


router = APIRouter(tags=["nudge-copy"])

_COLL = "nudge_copy_config"
_HISTORY_COLL = "nudge_copy_history"
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


class NudgeCopyHistoryEntry(BaseModel):
    """One historical revision. `updated_by` is safe to surface here
    because the endpoint is admin-only."""
    headline: str
    subhead: str
    note: Optional[str] = None
    updated_at: str
    updated_by: str


class NudgeCopyHistoryResponse(BaseModel):
    entries: List[NudgeCopyHistoryEntry]


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


async def _append_history(
    db: AsyncIOMotorDatabase,
    *,
    key: str,
    headline: str,
    subhead: str,
    note: Optional[str],
    updated_by: str,
) -> None:
    """Append-only revision log. Called on every successful save.
    We deliberately store the RESOLVED headline/subhead (post-trim)
    so a restore just re-uses the row's fields verbatim."""
    await db[_HISTORY_COLL].insert_one({
        "key": key,
        "headline": headline,
        "subhead": subhead,
        "note": note,
        "updated_at": _now(),
        "updated_by": updated_by,
    })


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
    """Admin override. Upserts the singleton row, records who + when,
    and appends a revision log entry so the editor can offer a
    one-click restore of a previous headline/subhead pair.

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
    await _append_history(
        db,
        key=_KEY_CHILD_NEEDS_SHARE,
        headline=payload.headline,
        subhead=payload.subhead,
        note=payload.note,
        updated_by=admin.email,
    )
    return await _resolve(db, _KEY_CHILD_NEEDS_SHARE)


@router.post("/admin/nudge-copy/child-needs-share/reset", response_model=NudgeCopyPublic)
async def reset_child_needs_share_nudge_copy(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Nuke the admin override → the public endpoint falls back to
    the hardcoded defaults. Useful when a copy experiment goes
    sideways and you want to revert in one click.

    Does NOT truncate the history log — an admin who resets can
    still restore a prior version from the editor page."""
    db = _get_db(request)
    await db[_COLL].delete_one({"key": _KEY_CHILD_NEEDS_SHARE})
    return await _resolve(db, _KEY_CHILD_NEEDS_SHARE)


# ------------------------------ History read ---------------------------- #

@router.get(
    "/admin/nudge-copy/child-needs-share/history",
    response_model=NudgeCopyHistoryResponse,
)
async def get_child_needs_share_nudge_copy_history(
    request: Request,
    limit: int = Query(5, ge=1, le=20),
    _admin: UserPublic = Depends(require_admin),
):
    """Last N revisions, newest-first. Admin-gated because
    `updated_by` (an admin email) is surfaced. The editor calls this
    with `limit=5` by default and renders each row as a small
    "Restore" button that populates the textareas without saving —
    the admin still clicks Save to actually flip the live copy."""
    db = _get_db(request)
    cursor = (
        db[_HISTORY_COLL]
        .find({"key": _KEY_CHILD_NEEDS_SHARE}, {"_id": 0})
        .sort("updated_at", -1)
        .limit(limit)
    )
    entries: List[NudgeCopyHistoryEntry] = []
    async for row in cursor:
        ts = row.get("updated_at")
        entries.append(NudgeCopyHistoryEntry(
            headline=row.get("headline") or "",
            subhead=row.get("subhead") or "",
            note=row.get("note"),
            updated_at=(
                ts.isoformat() if hasattr(ts, "isoformat") else str(ts or "")
            ),
            updated_by=row.get("updated_by") or "",
        ))
    return NudgeCopyHistoryResponse(entries=entries)


# ---------------------------------------------------------------------------
# Iter199 · Individual → Joint bridge — variant copy + CTR tracking.
#
# The Landing "When you're ready to go further" bridge section (and its
# mirror inside the Safety Assessment cleared companion CTA) supports
# TWO variants — chosen client-side based on the caller's most recent
# safety-screen level:
#
#   cleared    (level 3/4) → "no concerns about family violence" copy
#   concerned  (level 1/2) → "safe paths for when family violence is
#                             present" — routes to individual-only tools
#
# Both variants sit under a single config row keyed by
# `individual_to_joint_bridge`. Impressions and clicks are recorded in
# `nudge_copy_events` so ops can measure whether the new copy lifts
# "See sample joint preview" CTR vs. the baseline.
# ---------------------------------------------------------------------------

_KEY_JOINT_BRIDGE = "individual_to_joint_bridge"
_EVENTS_COLL = "nudge_copy_events"
_VARIANT_KEYS = ("cleared", "concerned")

_DEFAULTS_JOINT_BRIDGE = {
    "cleared": {
        "eyebrow": "When you're ready to go further — no concerns about family violence",
        "headline": "Want to compare perspectives?",
        "body": (
            "Invite your co-parent — or connect with a mediator, "
            "attorney or therapist — to move from individual reflection "
            "into joint alignment."
        ),
        "cta_label": "See a sample joint preview",
        "cta_route": "/samples",
    },
    "concerned": {
        "eyebrow": "When you're ready, on your own timeline — safe paths for when family violence is present",
        "headline": "Keep working on your own — safely, at your pace.",
        "body": (
            "Joint tools aren't the next step for you right now. Continue "
            "building your private reflection, journal, and safety plan — "
            "and connect with a domestic-violence advocate whenever it "
            "feels right."
        ),
        "cta_label": "See safe individual paths",
        "cta_route": "/safety",
    },
}


class BridgeVariant(BaseModel):
    """Configurable copy for ONE variant of the Individual→Joint
    bridge. `cta_route` is a same-origin path — validated to prevent
    a malicious admin from setting an off-site redirect."""
    eyebrow: str = Field(..., min_length=6, max_length=180)
    headline: str = Field(..., min_length=6, max_length=180)
    body: str = Field(..., min_length=10, max_length=600)
    cta_label: str = Field(..., min_length=2, max_length=80)
    cta_route: str = Field(..., min_length=1, max_length=120)

    @field_validator("cta_route")
    @classmethod
    def _same_origin(cls, v: str) -> str:
        v = (v or "").strip()
        if not v.startswith("/") or v.startswith("//"):
            raise ValueError("cta_route must be a same-origin relative path (start with '/')")
        return v

    @field_validator("eyebrow", "headline", "body", "cta_label")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class JointBridgePublic(BaseModel):
    cleared: BridgeVariant
    concerned: BridgeVariant
    is_default: bool


class JointBridgeUpdate(BaseModel):
    """Admin update body — either variant can be omitted so ops can
    tweak one lane without re-typing the other."""
    cleared: Optional[BridgeVariant] = None
    concerned: Optional[BridgeVariant] = None
    note: Optional[str] = Field(default=None, max_length=200)


class NudgeEventPayload(BaseModel):
    variant: str  # 'cleared' or 'concerned' — validated below
    event: str    # 'impression' | 'click'
    target: Optional[str] = Field(default=None, max_length=120)

    @field_validator("variant")
    @classmethod
    def _known_variant(cls, v: str) -> str:
        if v not in _VARIANT_KEYS:
            raise ValueError(f"variant must be one of {_VARIANT_KEYS}")
        return v

    @field_validator("event")
    @classmethod
    def _known_event(cls, v: str) -> str:
        if v not in ("impression", "click"):
            raise ValueError("event must be 'impression' or 'click'")
        return v


async def _resolve_bridge(db: AsyncIOMotorDatabase) -> JointBridgePublic:
    row = await db[_COLL].find_one({"key": _KEY_JOINT_BRIDGE}, {"_id": 0})
    is_default = True
    variants = {k: dict(v) for k, v in _DEFAULTS_JOINT_BRIDGE.items()}
    if row and isinstance(row.get("variants"), dict):
        for v_key in _VARIANT_KEYS:
            override = row["variants"].get(v_key)
            if isinstance(override, dict) and override.get("headline"):
                variants[v_key] = {
                    "eyebrow": override.get("eyebrow") or variants[v_key]["eyebrow"],
                    "headline": override.get("headline") or variants[v_key]["headline"],
                    "body": override.get("body") or variants[v_key]["body"],
                    "cta_label": override.get("cta_label") or variants[v_key]["cta_label"],
                    "cta_route": override.get("cta_route") or variants[v_key]["cta_route"],
                }
                is_default = False
    return JointBridgePublic(
        cleared=BridgeVariant(**variants["cleared"]),
        concerned=BridgeVariant(**variants["concerned"]),
        is_default=is_default,
    )


@router.get("/public/nudge-copy/individual-to-joint-bridge",
            response_model=JointBridgePublic)
async def get_joint_bridge_copy(db: AsyncIOMotorDatabase = Depends(_get_db)):
    """Public read. Cache-Control no-store so an admin tweak is live
    on next page load. The frontend picks the variant client-side
    from the parent's most recent safety level (>=3 → cleared)."""
    from fastapi.responses import JSONResponse
    copy = await _resolve_bridge(db)
    return JSONResponse(copy.model_dump(), headers={"Cache-Control": "no-store"})


@router.post("/admin/nudge-copy/individual-to-joint-bridge",
             response_model=JointBridgePublic)
async def update_joint_bridge_copy(
    body: JointBridgeUpdate,
    db: AsyncIOMotorDatabase = Depends(_get_db),
    admin: UserPublic = Depends(require_admin),
):
    """Admin write. Merges the submitted variants over the existing
    config so ops can update one lane at a time. Every save appends a
    history row per variant for restore + audit."""
    if body.cleared is None and body.concerned is None:
        raise HTTPException(
            status_code=400,
            detail="At least one variant (cleared or concerned) must be provided.",
        )
    row = await db[_COLL].find_one({"key": _KEY_JOINT_BRIDGE}) or {}
    variants = dict(row.get("variants") or {})
    now = _now()
    for v_key, override in (("cleared", body.cleared), ("concerned", body.concerned)):
        if override is None:
            continue
        variants[v_key] = override.model_dump()
        # Append a history row per updated variant.
        await db[_HISTORY_COLL].insert_one({
            "key": _KEY_JOINT_BRIDGE,
            "variant": v_key,
            "headline": override.headline,
            "subhead": override.body,
            "eyebrow": override.eyebrow,
            "cta_label": override.cta_label,
            "cta_route": override.cta_route,
            "note": body.note,
            "updated_at": now,
            "updated_by": (admin.email or admin.user_id or "unknown"),
        })
    await db[_COLL].update_one(
        {"key": _KEY_JOINT_BRIDGE},
        {"$set": {
            "key": _KEY_JOINT_BRIDGE,
            "variants": variants,
            "updated_at": now,
            "updated_by": (admin.email or admin.user_id or "unknown"),
        }},
        upsert=True,
    )
    return await _resolve_bridge(db)


@router.post("/public/nudge-copy/individual-to-joint-bridge/track",
             status_code=204)
async def track_bridge_event(
    body: NudgeEventPayload,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(_get_db),
):
    """Anonymous impression + click logger. Public because the copy
    itself is public. We deliberately do NOT associate the event with
    a `user_id` — parents on the marketing page haven't consented to
    per-user tracking. Analytics rollups aggregate anonymously.

    Fire-and-forget shape: the client doesn't wait on this beyond a
    204, and a failure never blocks the CTA."""
    await db[_EVENTS_COLL].insert_one({
        "key": _KEY_JOINT_BRIDGE,
        "variant": body.variant,
        "event": body.event,
        "target": body.target,
        "created_at": _now(),
    })
    return None


@router.get("/admin/nudge-copy/individual-to-joint-bridge/analytics")
async def bridge_analytics(
    db: AsyncIOMotorDatabase = Depends(_get_db),
    _admin: UserPublic = Depends(require_admin),
):
    """Ops metric: per-variant impression + click counts and CTR.
    Same-day cohort — the collection is small so we return the
    all-time roll-up. Ops can slice by date later if it matters."""
    pipeline = [
        {"$match": {"key": _KEY_JOINT_BRIDGE}},
        {"$group": {
            "_id": {"variant": "$variant", "event": "$event"},
            "count": {"$sum": 1},
        }},
    ]
    rows = [r async for r in db[_EVENTS_COLL].aggregate(pipeline)]
    per: Dict[str, Dict[str, int]] = {v: {"impressions": 0, "clicks": 0} for v in _VARIANT_KEYS}
    for r in rows:
        v = (r["_id"] or {}).get("variant")
        e = (r["_id"] or {}).get("event")
        if v in per and e in ("impression", "click"):
            per[v]["impressions" if e == "impression" else "clicks"] += r["count"]
    out = {}
    for v_key, counts in per.items():
        imp = counts["impressions"]
        clk = counts["clicks"]
        ctr = round((clk / imp) * 100, 1) if imp > 0 else 0.0
        out[v_key] = {
            "impressions": imp,
            "clicks": clk,
            "ctr": ctr,
        }
    return {"variants": out}

