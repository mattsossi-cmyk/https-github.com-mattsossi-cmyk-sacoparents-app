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
from dual_consent import record_consent


router = APIRouter(tags=["complete-alignment-report"])
logger = logging.getLogger(__name__)

_CASES_COLL = "joint_alignment_cases"

# Cross-parent-share consent keys stored on the case's parents-list
# entry. Adding a new consent key here is the ONLY way to unlock a
# new cross-parent-share surface — the aggregator strips everything
# by default, and the route only asks to preserve a field if BOTH
# parents on the case have the matching consent-at timestamp set.
_CONSENT_KEY_CHILD_NEEDS = "child_needs_share_consent_at"


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


@router.get("/complete-report/my-active-cases")
async def complete_report_my_active_cases(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """List the joint cases the caller is a parent on, together with
    the caller's own Child Needs share-consent state per case.

    Used by the post-completion onboarding nudge on the Child Needs
    Statement report page — so a parent who just finished can toggle
    "share these highlights" per case in one place, right when the
    context is freshest.

    Returns cases sorted most-recent-first, capped at 20. Never
    exposes the co-parent's raw consent timestamp — only a boolean.
    """
    cursor = db[_CASES_COLL].find(
        {"parents.user_id": current.user_id},
        {"_id": 0, "case_id": 1, "parents": 1, "created_at": 1, "status": 1},
    ).sort("created_at", -1).limit(20)
    out: list[dict] = []
    async for case in cursor:
        parents = case.get("parents") or []
        if len(parents) < 2:
            continue
        # Locate the caller's slot; skip cases where they're not on the
        # parents list (defensive — the DB filter should have handled
        # this but a race between token refresh + case invite could
        # theoretically leak an unrelated case).
        my_slot: int | None = None
        for i, p in enumerate(parents[:2]):
            if p.get("user_id") == current.user_id:
                my_slot = i
                break
        if my_slot is None:
            continue
        other = parents[1 - my_slot]
        coparent_name = (
            (other.get("name") or "").strip()
            or ((other.get("email") or "").split("@", 1)[0] if "@" in (other.get("email") or "") else None)
            or "Your co-parent"
        )
        out.append({
            "case_id": case["case_id"],
            "coparent_name": coparent_name,
            "status": case.get("status") or "active",
            "my_consent_at": parents[my_slot].get(_CONSENT_KEY_CHILD_NEEDS),
            "coparent_has_consented": bool(other.get(_CONSENT_KEY_CHILD_NEEDS)),
        })
    return {"cases": out}


def _preserve_fields_for_case(case: dict) -> tuple[str, ...]:
    """Inspect the case document's parents-list for cross-parent-share
    consent flags. Returns the tuple of aggregator-lane-fields that
    BOTH parents have opted-in to share; the aggregator strips
    everything else.

    Contract: this helper is the ONLY place a consent key is mapped
    to an aggregator field. Adding a new key here + one line in the
    aggregator's `_JOINT_STRIPPED_LANE_FIELDS` is all it takes to
    plumb a new opt-in share surface.
    """
    parents = case.get("parents") or []
    if len(parents) < 2:
        return ()
    a, b = parents[0], parents[1]
    preserved: list[str] = []
    if a.get(_CONSENT_KEY_CHILD_NEEDS) and b.get(_CONSENT_KEY_CHILD_NEEDS):
        preserved.append("highlights")
    return tuple(preserved)


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
        preserve_fields=_preserve_fields_for_case(case),
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
    preserved = _preserve_fields_for_case(case)
    agg = await aggregate_for_case(
        db,
        parent_a_user_id=a["user_id"],
        parent_b_user_id=b["user_id"],
        preserve_fields=preserved,
    )
    # Surface the CALLER's per-lane consent state so the frontend
    # toggle can render "on" / "waiting for co-parent" / "off"
    # without a second round-trip. Only the caller's own flag is
    # exposed — never the co-parent's timestamp values.
    caller_is_a = current.user_id == a.get("user_id")
    my_parent = a if caller_is_a else b
    other_parent = b if caller_is_a else a
    consent = {
        "child_needs": {
            "my_consent_at": my_parent.get(_CONSENT_KEY_CHILD_NEEDS),
            "coparent_has_consented": bool(other_parent.get(_CONSENT_KEY_CHILD_NEEDS)),
            "unlocked": "highlights" in preserved,
        },
    }
    return {
        "variant": "joint",
        "case_id": case_id,
        "parents": [
            _parent_display_name(a, "Parent A"),
            _parent_display_name(b, "Parent B"),
        ],
        "my_consent": consent,
        **agg,
    }


@router.post("/complete-report/joint/{case_id}/consent/child-needs")
async def complete_report_toggle_child_needs_consent(
    case_id: str = Path(..., pattern=r"^SA-[A-Z0-9]{4,10}$"),
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Toggle the caller's `child_needs_share_consent_at` flag on
    this case. If the flag is currently set we CLEAR it (undo);
    otherwise we record the current UTC ISO timestamp.

    Returns the caller's own new state + whether the joint view is
    now unlocked (both parents have consented). Never exposes the
    co-parent's timestamp — only a boolean "have they also consented?"
    """
    from datetime import datetime, timezone as _tz
    # Membership + acceptance gate (also raises 404 for non-members
    # so case_id existence is never leaked).
    await _load_case_and_members(
        db, case_id=case_id, caller_user_id=current.user_id,
    )
    # Look up the caller's current flag so we can implement a toggle
    # rather than a set-only endpoint.
    case = await db[_CASES_COLL].find_one({"case_id": case_id}, {"parents": 1}) or {}
    parents = case.get("parents") or []
    my_current: str | None = None
    for p in parents[:2]:
        if p.get("user_id") == current.user_id:
            my_current = p.get(_CONSENT_KEY_CHILD_NEEDS)
            break
    if my_current:
        # Clear (revoke consent)
        slot = 0 if parents[0].get("user_id") == current.user_id else 1
        await db[_CASES_COLL].update_one(
            {"case_id": case_id},
            {"$unset": {f"parents.{slot}.{_CONSENT_KEY_CHILD_NEEDS}": ""}},
        )
        return {"my_consent_at": None, "unlocked": False}
    # Record new consent
    now_iso = datetime.now(_tz.utc).isoformat()
    _, both = await record_consent(
        db,
        case_id=case_id,
        caller_user_id=current.user_id,
        consent_key=_CONSENT_KEY_CHILD_NEEDS,
        consent_iso=now_iso,
    )
    return {"my_consent_at": now_iso, "unlocked": both}
