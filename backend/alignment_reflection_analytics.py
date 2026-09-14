"""Alignment Reflection Reminder Analytics — Iter194.

Adds open-tracking (transparent 1x1 GIF) and click-tracking (302
redirect through a URL wrapper) to the `alignment_reflection_reminders`
collection. The analytics endpoint aggregates opens / clicks per
subject so we can prove the reminder lifts the
`waiting_on_coparent` → `ready` conversion.

Endpoints (mounted under `/api/insights`):
  * `GET /track/reminder-open/{rid}.gif`   — transparent GIF, marks opened_at
  * `GET /track/reminder-click/{rid}`      — 302 redirect, marks clicked_at

Admin analytics (mounted under `/api/admin`):
  * `GET /alignment-reflections/analytics` — aggregate open/click rates
                                             per subject + overall

Design notes:
  * The tracker endpoints are ALWAYS 200 (GIF) or 302 (redirect) even
    when the reminder_id is unknown — a stale email link should never
    dead-end a co-parent halfway to the reflection form.
  * `opened_at` and `clicked_at` are set with $setOnInsert semantics
    so a second open/click never overwrites the first — first-touch
    wins for conversion attribution.
  * We NEVER expose reminder details on either tracker endpoint — the
    GIF is byte-identical for every reminder, and the redirect target
    is on the reminder row, never in the request.
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_db


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["alignment-reflection-analytics"])

_REMINDER_COLL = "alignment_reflection_reminders"


# 1x1 transparent GIF. Inline base64 so we never depend on a file on
# disk — deploys stay hermetic.
_PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs="
)


def _bson_object_id(rid: str) -> Optional[Any]:
    """Convert a hex string to an ObjectId, returning None on failure.
    Kept in a helper so both tracker endpoints handle "shape-invalid"
    ids the same way — silently no-op instead of erroring."""
    try:
        from bson import ObjectId
        return ObjectId(rid)
    except Exception:  # noqa: BLE001
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _mark_opened(db: AsyncIOMotorDatabase, rid: str) -> None:
    oid = _bson_object_id(rid)
    if not oid:
        return
    try:
        # $setOnInsert semantics via an update with upsert=False: only
        # set opened_at when the key is missing. Second open on the
        # same reminder does not overwrite the first — first-touch
        # attribution.
        await db[_REMINDER_COLL].update_one(
            {"_id": oid, "opened_at": {"$exists": False}},
            {"$set": {"opened_at": _now()}},
        )
    except Exception:  # noqa: BLE001
        logger.exception("mark_opened failed for %s", rid)


async def _mark_clicked(db: AsyncIOMotorDatabase, rid: str) -> Optional[str]:
    """Mark `clicked_at` and return the redirect target for this
    reminder. Falls back to the SA CoParents subject picker when the
    row is missing so a stale email link still lands on a useful
    page."""
    oid = _bson_object_id(rid)
    if not oid:
        return None
    try:
        doc = await db[_REMINDER_COLL].find_one_and_update(
            {"_id": oid, "clicked_at": {"$exists": False}},
            {"$set": {"clicked_at": _now()}},
            return_document=True,  # ignored on newer motor, harmless
        ) or await db[_REMINDER_COLL].find_one({"_id": oid})
    except Exception:  # noqa: BLE001
        logger.exception("mark_clicked failed for %s", rid)
        return None
    if not doc:
        return None
    subject = doc.get("subject") or "co_parenting"
    return f"/alignment/reflect/{subject}"


# ---------------------------------------------------------------------------
# Endpoints — mounted at /api/insights.
# ---------------------------------------------------------------------------

@router.get("/track/reminder-open/{rid}.gif")
async def track_reminder_open(
    rid: str, db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Transparent 1x1 GIF that marks the reminder as opened.
    Always returns 200 — never surface tracking state to the caller."""
    await _mark_opened(db, rid)
    return Response(
        content=_PIXEL_GIF,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            # Prevent link-preview scrapers from consuming the pixel
            # and prematurely marking the email as "opened".
            "Referrer-Policy": "no-referrer",
        },
    )


def _safe_public_base_url() -> str:
    """Public URL the redirect target is prefixed with. Same logic as
    the reminder module — env-var first, then a stable fallback."""
    import os
    base = (
        os.environ.get("PUBLIC_APP_URL")
        or os.environ.get("FRONTEND_URL")
        or "https://sacoparents.com"
    ).rstrip("/")
    return base


@router.get("/track/reminder-click/{rid}")
async def track_reminder_click(
    rid: str, db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Record the click, then 302-redirect to the reflection form."""
    path = await _mark_clicked(db, rid)
    target = f"{_safe_public_base_url()}{path or '/alignment/subjects'}"
    return RedirectResponse(url=target, status_code=302)


# ---------------------------------------------------------------------------
# Admin analytics.
# ---------------------------------------------------------------------------

def build_reminder_url(*, api_base: str, rid: str, kind: str) -> str:
    """Helper used by the reminder module when composing the HTML/
    text bodies so the pixel + click URLs stay in one place. `kind`
    is 'open' or 'click'."""
    api = (api_base or "").rstrip("/")
    if kind == "open":
        return f"{api}/api/insights/track/reminder-open/{rid}.gif"
    if kind == "click":
        return f"{api}/api/insights/track/reminder-click/{rid}"
    raise ValueError(f"Unknown tracker kind: {kind}")


async def compute_reminder_analytics(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Aggregate open + click rates from the reminder collection.
    Returns per-subject rows + a summary line. Kept as a plain
    function so tests + the admin route share the same code path.
    """
    rows = await db[_REMINDER_COLL].find().to_list(length=None)
    per_subject: Dict[str, Dict[str, int]] = {}
    total = {"sent": 0, "opened": 0, "clicked": 0}
    for row in rows:
        subj = row.get("subject") or "unknown"
        bucket = per_subject.setdefault(subj, {"sent": 0, "opened": 0, "clicked": 0})
        bucket["sent"] += 1
        total["sent"] += 1
        if row.get("opened_at"):
            bucket["opened"] += 1
            total["opened"] += 1
        if row.get("clicked_at"):
            bucket["clicked"] += 1
            total["clicked"] += 1

    def _pct(n: int, d: int) -> float:
        if d <= 0:
            return 0.0
        return round(100.0 * n / d, 1)

    subjects_out = []
    for subj, b in sorted(per_subject.items()):
        subjects_out.append({
            "subject":      subj,
            "sent":         b["sent"],
            "opened":       b["opened"],
            "clicked":      b["clicked"],
            "open_rate":    _pct(b["opened"], b["sent"]),
            "click_rate":   _pct(b["clicked"], b["sent"]),
            "click_through_open": _pct(b["clicked"], b["opened"]),
        })
    return {
        "subjects": subjects_out,
        "total": {
            **total,
            "open_rate":  _pct(total["opened"], total["sent"]),
            "click_rate": _pct(total["clicked"], total["sent"]),
            "click_through_open": _pct(total["clicked"], total["opened"]),
        },
    }
