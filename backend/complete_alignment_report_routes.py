"""Complete Alignment Report — HTTP routes.

Mounts four endpoints under `/api/complete-report`:

  * GET /complete-report/mine
        JSON view for the SIGNED-IN parent - aggregates every lane
        they have completed on SA CoParents so the frontend can
        render a live viewer page. Data-minimised.

  * GET /complete-report/mine.pdf
        Downloadable PDF of the individual variant. Latin-1 safe,
        follows the same 10-section sacoparentsalign.com skeleton
        as the joint report so parents and professionals always
        know where to look.

  * GET /complete-report/joint/{case_id}
        JSON view of a Joint Complete Alignment Report. Gated on
        the caller being one of the two parents on the case, OR
        the professional who created it. Never exposes the other
        parent's answer bodies - only lane completion states +
        Child Needs highlights (already shared surface).

  * GET /complete-report/joint/{case_id}.pdf
        PDF variant of the same, joint layout.

Clinical guardrails (baked in):
  * No adjudicative language in any response body.
  * Reports repeatedly self-label "Educational and organizational
    tool, not a diagnosis or court submission".
  * Safety lane visibility follows the platform's existing safety
    policy - completion state is shown but no answer bodies are
    surfaced in the report.
"""
from __future__ import annotations

import logging
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import UserPublic, get_current_user, get_db
from complete_alignment_aggregator import (
    aggregate_for_case,
    aggregate_for_user,
)
from complete_alignment_report_pdf import (
    render_individual_pdf,
    render_joint_pdf,
)


router = APIRouter(tags=["complete-alignment-report"])
logger = logging.getLogger(__name__)

_CASES_COLL = "joint_alignment_cases"


async def _resolve_parent_name(
    db: AsyncIOMotorDatabase, user_id: str,
) -> str:
    """Best-effort human name for a signed-in parent. Falls back to
    empty string so the PDF renderer swaps in "you"."""
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1, "full_name": 1, "email": 1}) or {}
    for k in ("name", "full_name"):
        v = u.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    email = u.get("email")
    if isinstance(email, str) and "@" in email:
        return email.split("@", 1)[0]
    return ""


# --------------------------- Individual variant --------------------------- #

@router.get("/complete-report/mine")
async def complete_report_mine(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Aggregate every lane the signed-in parent has completed and
    return the JSON envelope the frontend viewer renders."""
    agg = await aggregate_for_user(db, user_id=current.user_id)
    parent_name = await _resolve_parent_name(db, current.user_id)
    return {
        "variant": "individual",
        "parent_name": parent_name or "You",
        **agg,
    }


@router.get("/complete-report/mine.pdf")
async def complete_report_mine_pdf(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    agg = await aggregate_for_user(db, user_id=current.user_id)
    parent_name = await _resolve_parent_name(db, current.user_id)
    pdf_bytes = render_individual_pdf(agg, parent_name=parent_name)
    filename = "SA-CoParents-Complete-Alignment-Report.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


# ------------------------------- Joint variant ---------------------------- #

async def _load_case_and_members(
    db: AsyncIOMotorDatabase, *, case_id: str, caller_user_id: str,
) -> dict:
    """Return the case doc if the caller is authorised - one of the
    two parents on the case OR the professional who created it. Raise
    404 (not 403) if unauthorised so we never confirm case_id existence
    to callers who shouldn't know."""
    case = await db[_CASES_COLL].find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    parents = case.get("parents") or []
    parent_user_ids = [p.get("user_id") for p in parents if p.get("user_id")]
    prof_id = case.get("professional_created_by") or (case.get("professional") or {}).get("id")
    if caller_user_id not in parent_user_ids and caller_user_id != prof_id:
        # 404 rather than 403 - don't leak case existence.
        raise HTTPException(status_code=404, detail="Case not found.")
    if len(parents) < 2 or not all(p.get("user_id") for p in parents[:2]):
        raise HTTPException(
            status_code=409,
            detail="Both parents have not accepted the invitation yet.",
        )
    return case


def _parent_display_name(parent: dict, fallback: str) -> str:
    n = (parent.get("name") or "").strip()
    if n:
        return n
    email = parent.get("email") or ""
    if "@" in email:
        return email.split("@", 1)[0]
    return fallback


@router.get("/complete-report/joint/{case_id}.pdf")
async def complete_report_joint_pdf(
    case_id: str = Path(..., pattern=r"^SA-[A-Z0-9]{4,10}(?:\.pdf)?$"),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # This route MUST be registered before the sibling `/joint/{case_id}`
    # JSON route — starlette's `str` path converter is greedy up to the
    # next slash, so `/joint/SA-XX.pdf` would otherwise be captured by
    # the JSON route with `case_id="SA-XX.pdf"` and fail its regex.
    # Some starlette versions still hand us the `.pdf` suffix in the
    # captured value; the regex above accepts both forms and we strip
    # the suffix below.
    if case_id.endswith(".pdf"):
        case_id = case_id[:-4]
    case = await _load_case_and_members(
        db, case_id=case_id, caller_user_id=current.user_id,
    )
    a, b = case["parents"][0], case["parents"][1]
    agg = await aggregate_for_case(
        db,
        parent_a_user_id=a["user_id"],
        parent_b_user_id=b["user_id"],
    )
    names = [
        _parent_display_name(a, "Parent A"),
        _parent_display_name(b, "Parent B"),
    ]
    pdf_bytes = render_joint_pdf(agg, parents=names)
    filename = f"SA-CoParents-Complete-Alignment-{case_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/complete-report/joint/{case_id}")
async def complete_report_joint(
    case_id: str = Path(..., pattern=r"^SA-[A-Z0-9]{4,10}$"),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    case = await _load_case_and_members(
        db, case_id=case_id, caller_user_id=current.user_id,
    )
    a, b = case["parents"][0], case["parents"][1]
    agg = await aggregate_for_case(
        db,
        parent_a_user_id=a["user_id"],
        parent_b_user_id=b["user_id"],
    )
    return {
        "variant": "joint",
        "case_id": case_id,
        "parents": [
            _parent_display_name(a, "Parent A"),
            _parent_display_name(b, "Parent B"),
        ],
        **agg,
    }
