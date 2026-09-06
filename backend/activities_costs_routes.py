"""
Activity Cost Splitter — API endpoints.

Mounted at `/api/activities-costs`.

Both parents log their share of an activity-related expense (uniforms,
league fees, camps, tutoring, transport, gear) against their own
account. The compare endpoint returns each parent's running total so
the two see a running side-by-side ledger — but never each other's
free-text notes (matches the Alignment-report privacy pattern).

Endpoints
---------
GET    /activities-costs/mine       — list the caller's entries
POST   /activities-costs            — add an entry
DELETE /activities-costs/{cost_id}  — remove one of the caller's entries
GET    /activities-costs/compare?coparent_email=… — you-vs-coparent totals

Storage: `activity_costs` collection. Each row is scoped by `user_id`
so a delete or list can never cross accounts.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from auth import UserPublic, get_current_user, get_db


router = APIRouter(tags=["activities-costs"], prefix="/activities-costs")
logger = logging.getLogger(__name__)

_COLL = "activity_costs"

# Categories the parents pick from — keeps the compare payload
# aggregable without free-text ambiguity ("Piano" vs "piano lessons").
CATEGORIES = [
    {"key": "sports", "label": "Sports"},
    {"key": "arts", "label": "Arts / Music"},
    {"key": "tutoring", "label": "Tutoring / Academic"},
    {"key": "camps", "label": "Camps / Programs"},
    {"key": "faith", "label": "Faith / Community"},
    {"key": "gear", "label": "Gear / Equipment"},
    {"key": "transport", "label": "Transport"},
    {"key": "other", "label": "Other"},
]
_CATEGORY_KEYS = {c["key"] for c in CATEGORIES}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v


class CostCreate(BaseModel):
    activity_label: str = Field(..., min_length=1, max_length=120)
    category: str = Field(default="other")
    amount_cents: int = Field(..., ge=1, le=1_00_000_00)  # ≤ $1M sanity cap
    currency: str = Field(default="USD", min_length=3, max_length=3)
    incurred_on: Optional[str] = Field(default=None, description="ISO date; defaults to today.")
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("category")
    @classmethod
    def _norm_category(cls, v: str) -> str:
        key = (v or "other").strip().lower()
        if key not in _CATEGORY_KEYS:
            return "other"
        return key

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return (v or "USD").upper()

    @field_validator("incurred_on")
    @classmethod
    def _valid_date(cls, v):
        if v is None or v == "":
            return None
        try:
            date.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError("incurred_on must be YYYY-MM-DD")
        return v


def _shape_row(doc: Dict[str, Any], *, redact_note: bool = False) -> Dict[str, Any]:
    return {
        "cost_id": doc.get("cost_id"),
        "activity_label": doc.get("activity_label"),
        "category": doc.get("category") or "other",
        "amount_cents": int(doc.get("amount_cents") or 0),
        "currency": doc.get("currency") or "USD",
        "incurred_on": doc.get("incurred_on"),
        "note": None if redact_note else (doc.get("note") or None),
        "created_at": _iso(doc.get("created_at")),
    }


@router.get("/categories")
async def list_categories():
    """Public list of allowed category chips so the UI stays in sync."""
    return {"categories": CATEGORIES}


@router.get("/mine")
async def list_mine(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db[_COLL].find(
        {"user_id": current.user_id},
        sort=[("incurred_on", -1), ("created_at", -1)],
    )
    rows: List[Dict[str, Any]] = []
    total = 0
    async for doc in cursor:
        rows.append(_shape_row(doc))
        total += int(doc.get("amount_cents") or 0)
    return {
        "rows": rows,
        "total_cents": total,
        "count": len(rows),
        "categories": CATEGORIES,
    }


@router.post("")
async def create_cost(
    body: CostCreate,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if current.is_guest:
        raise HTTPException(status_code=403, detail="Guest accounts cannot log costs.")
    doc = {
        "cost_id": f"AC-{uuid.uuid4().hex[:10].upper()}",
        "user_id": current.user_id,
        "email": current.email,
        "activity_label": body.activity_label.strip()[:120],
        "category": body.category,
        "amount_cents": int(body.amount_cents),
        "currency": body.currency,
        "incurred_on": body.incurred_on or _now().date().isoformat(),
        "note": (body.note or "").strip()[:500] or None,
        "created_at": _now(),
    }
    await db[_COLL].insert_one(doc)
    return {"ok": True, "cost": _shape_row(doc)}


@router.delete("/{cost_id}")
async def delete_cost(
    cost_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await db[_COLL].delete_one(
        {"cost_id": cost_id, "user_id": current.user_id},
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cost entry not found.")
    return {"ok": True}


async def _load_bundle(
    db: AsyncIOMotorDatabase, user_id: str, *, redact: bool
) -> Dict[str, Any]:
    """Return one parent's rows + running totals for the compare endpoint."""
    cursor = db[_COLL].find(
        {"user_id": user_id},
        sort=[("incurred_on", -1), ("created_at", -1)],
    )
    rows: List[Dict[str, Any]] = []
    per_cat: Dict[str, int] = {}
    total = 0
    async for doc in cursor:
        row = _shape_row(doc, redact_note=redact)
        rows.append(row)
        total += row["amount_cents"]
        per_cat[row["category"]] = per_cat.get(row["category"], 0) + row["amount_cents"]
    return {
        "rows": rows,
        "total_cents": total,
        "per_category": per_cat,
        "count": len(rows),
    }


def _pair_categories(
    self_per_cat: Dict[str, int], coparent_per_cat: Dict[str, int]
) -> List[Dict[str, Any]]:
    """Merge the two parents' per-category totals into a side-by-side view."""
    all_keys = sorted(set(self_per_cat) | set(coparent_per_cat))
    label_by_key = {c["key"]: c["label"] for c in CATEGORIES}
    return [
        {
            "key": k,
            "label": label_by_key.get(k, k),
            "self_cents": self_per_cat.get(k, 0),
            "coparent_cents": coparent_per_cat.get(k, 0),
        }
        for k in all_keys
    ]


@router.get("/compare")
async def compare(
    coparent_email: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Return each parent's totals, per-category breakdowns, and per-row
    entries. Notes are redacted for the co-parent's rows — the parent's
    own free-text stays private. Totals themselves are always visible.
    """
    if not coparent_email:
        raise HTTPException(status_code=400, detail="coparent_email required")

    coparent = await db.users.find_one(
        {"email": coparent_email.strip().lower()},
        {"user_id": 1, "email": 1, "name": 1},
    )
    if not coparent:
        raise HTTPException(status_code=404, detail="Co-parent account not found")

    self_b = await _load_bundle(db, current.user_id, redact=False)
    coparent_b = await _load_bundle(db, coparent["user_id"], redact=True)

    return {
        "self": {"email": current.email, **self_b},
        "coparent": {
            "email": coparent["email"],
            "name": coparent.get("name"),
            **coparent_b,
        },
        "combined_total_cents": self_b["total_cents"] + coparent_b["total_cents"],
        "per_category_pair": _pair_categories(
            self_b["per_category"], coparent_b["per_category"]
        ),
        "generated_at": _iso(_now()),
    }
