"""Joint Co-Parenting Summary for Professional Review — API surface.

Two endpoints:
  * GET /api/joint-professional-report/{share_id}       — JSON
  * GET /api/joint-professional-report/{share_id}/pdf   — PDF

Both are gated behind an active Compare share the caller is a
participant in. The same consent model the Pathway Report uses — an
active Compare share IS the mutual consent for a joint report. No
new consent flow is introduced.

Data pulled per parent:
  * SNC v2 comparison (via `snc2_comparison.build_comparison`).
  * Mediation prep (`prep_data` — child_goals + priority).
  * Dimension Companion latest assessment (communication + emotional-
    regulation tiers).
  * TISFL Finding 3 ONLY (Parenting-Plan Implications). Findings 1 & 2
    remain private to the parent that completed the safety screen.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user, get_db
from joint_professional_report import build_joint_report
from snc2_comparison import build_comparison
from trauma_lens import redact_for_compare


router = APIRouter(prefix="/joint-professional-report", tags=["joint-professional-report"])


# ---------------------------------------------------------------------------
# Consent gate — reuses the Compare-share pattern from pathway_report_routes.
# ---------------------------------------------------------------------------

_SHARE_COLLECTIONS = (
    "snc2_shares",
    "edu_deep_shares",
    "med_deep_shares",
    "psych_deep_shares",
    "compare_shares",  # legacy fallback
)


async def _find_active_share(
    db: AsyncIOMotorDatabase, share_id: str, user_id: str,
) -> Dict[str, Any]:
    """Locate an active Compare share the caller is a participant in.

    Different SNC v2 shares use different `user_pair` vs
    `creator_user_id`/`partner_user_id` shapes. Both are handled below.
    """
    row: Optional[Dict[str, Any]] = None
    for collection in _SHARE_COLLECTIONS:
        row = await db[collection].find_one(
            {"share_id": share_id}, {"_id": 0},
        )
        if row:
            break
    if not row:
        raise HTTPException(404, "Compare share not found.")

    # Two share shapes exist in the codebase — normalise them.
    pair: List[str] = list(row.get("user_pair") or [])
    if not pair:
        creator = row.get("creator_user_id")
        partner = row.get("partner_user_id")
        pair = [x for x in (creator, partner) if x]
    row["_user_pair"] = pair

    # SNC v2 shares use two `creator_consent` / `partner_consent` flags
    # plus a `status` field. Pathway shares use `status="active"`. Handle
    # both so the report unlocks whenever both parents have consented.
    is_active = (row.get("status") == "active") or (
        bool(row.get("creator_consent")) and bool(row.get("partner_consent"))
        and row.get("status") != "revoked"
    )
    if not is_active:
        raise HTTPException(
            409,
            "This Compare share is not yet fully consented — the Joint "
            "Professional Report needs both parents' explicit consent "
            "through the Compare flow before it can be generated.",
        )
    if user_id not in pair:
        raise HTTPException(403, "You are not a participant in this share.")
    return row


# ---------------------------------------------------------------------------
# Loaders.
# ---------------------------------------------------------------------------

async def _load_snc2_assessment(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    return await db["snc2_assessments"].find_one(
        {"user_id": user_id}, {"_id": 0},
    ) or {}


async def _load_prep(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    return await db["prep_data"].find_one(
        {"user_id": user_id}, {"_id": 0},
    ) or {}


async def _load_dim_companion(
    db: AsyncIOMotorDatabase, user_id: str,
) -> Optional[Dict[str, Any]]:
    return await db["dimension_companion_assessments"].find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)],
    )


async def _load_finding3(
    db: AsyncIOMotorDatabase, user_id: str,
) -> Optional[Dict[str, Any]]:
    """Return Finding 3 (Parenting-Plan Implications) only. Never Findings 1/2."""
    doc = await db["safety_assessments"].find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)],
    )
    if not doc:
        return None
    lens = (doc.get("result") or {}).get("lens") or {}
    redacted = redact_for_compare(lens)
    return (redacted.get("findings") or {}).get("parenting_plan_implications")


async def _load_user_display_name(
    db: AsyncIOMotorDatabase, user_id: str, fallback: str,
) -> str:
    doc = await db["users"].find_one({"user_id": user_id}, {"_id": 0, "name": 1})
    return ((doc or {}).get("name") or fallback).strip()


async def _resolve_pair_names(
    db: AsyncIOMotorDatabase, share: Dict[str, Any], caller_id: str,
) -> Dict[str, str]:
    """Return {'a_id','b_id','a_name','b_name'} with caller as parent A."""
    pair: List[str] = list(share.get("_user_pair") or [])
    other = [uid for uid in pair if uid != caller_id][0]
    a_name = await _load_user_display_name(db, caller_id, "Parent A")
    b_name = await _load_user_display_name(db, other, "Parent B")
    return {"a_id": caller_id, "b_id": other, "a_name": a_name, "b_name": b_name}


# ---------------------------------------------------------------------------
# Business logic — assemble the aggregated payload.
# ---------------------------------------------------------------------------

async def _assemble_report(
    db: AsyncIOMotorDatabase, share: Dict[str, Any], caller_id: str, share_id: str,
) -> Dict[str, Any]:
    names = await _resolve_pair_names(db, share, caller_id)
    snc_a = await _load_snc2_assessment(db, names["a_id"])
    snc_b = await _load_snc2_assessment(db, names["b_id"])
    prep_a = await _load_prep(db, names["a_id"])
    prep_b = await _load_prep(db, names["b_id"])
    dim_a = await _load_dim_companion(db, names["a_id"])
    dim_b = await _load_dim_companion(db, names["b_id"])
    lens3_a = await _load_finding3(db, names["a_id"])
    lens3_b = await _load_finding3(db, names["b_id"])

    # Build the SNC v2 comparison. If either parent has not completed the
    # SNC v2 assessment we still produce the report, but comparison-driven
    # sections will be empty with a helpful `empty_reason`.
    comparison: Dict[str, Any]
    if (
        snc_a and snc_b
        and snc_a.get("completed") and snc_b.get("completed")
    ):
        comparison = build_comparison(
            parent_a_name=names["a_name"],
            parent_b_name=names["b_name"],
            a_pathways=snc_a.get("selected_pathways") or [],
            b_pathways=snc_b.get("selected_pathways") or [],
            a_answers=snc_a.get("answers") or {},
            b_answers=snc_b.get("answers") or {},
        )
    else:
        comparison = {
            "shared_pathways": [],
            "steps": [],
            "highlights": [],
            "summary": {"total_items": 0, "aligned_pct": 0, "divergent_pct": 0, "counts": {}},
        }

    return build_joint_report(
        parent_a_name=names["a_name"],
        parent_b_name=names["b_name"],
        share_id=share_id,
        comparison=comparison,
        prep_a=prep_a,
        prep_b=prep_b,
        dim_a=dim_a,
        dim_b=dim_b,
        lens_finding3_a=lens3_a,
        lens_finding3_b=lens3_b,
    )


# ---------------------------------------------------------------------------
# Routes.
# ---------------------------------------------------------------------------

@router.get("/{share_id}")
async def get_joint_report(
    share_id: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """JSON payload of the Joint Co-Parenting Summary for Professional Review."""
    share = await _find_active_share(db, share_id, user.user_id)
    return await _assemble_report(db, share, user.user_id, share_id)


@router.get("/{share_id}/pdf")
async def get_joint_report_pdf(
    share_id: str,
    request: Request,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Branded PDF of the joint report — attorney/mediator-ready."""
    from joint_professional_report_pdf import build_joint_report_pdf

    share = await _find_active_share(db, share_id, user.user_id)
    payload = await _assemble_report(db, share, user.user_id, share_id)
    pdf_bytes = build_joint_report_pdf(payload)
    filename = f"joint-professional-report-{share_id[:10]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
