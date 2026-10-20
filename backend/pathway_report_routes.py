"""API surface for the Dispute Resolution Pathway Report.

Two endpoints:
  * GET /pathway-report/preview           — single-parent preview using
    the caller's own data. Always available, always caveated.
  * GET /pathway-report/dual/{share_id}   — full 2-parent report. Only
    resolves when an existing `deep_dive_compare` share for this caller
    is status="active" (i.e. both parents have already consented in the
    Compare flow). Reads both parents' Safety + Companion + ND Risk +
    Compliance from Mongo directly using the share's user_pair.

Rationale for the consent gate: forcing a brand-new consent flow just
for this feature would ship a big UX + a lot of new state. The Compare
share flow already carries mutual, explicit, revocable consent between
two co-parents — which is exactly the trust surface this report needs.
An active Compare share IS the mutual consent for a pathway analysis
of both parents' data.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user
from pathway_report import (
    DualPartyContext, SinglePartyContext,
    score_pathway_dual, score_pathway_single,
)


router = APIRouter(prefix="/pathway-report", tags=["pathway-report"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


# ---------------------------------------------------------------------------
# Data collection helpers.
# ---------------------------------------------------------------------------

_COERCIVE_TRIGGER_KEYS = {
    "coercive_control", "isolation", "financial_control", "monitoring",
    "gaslighting_pattern", "threats_pattern",
}
_PHYSICAL_TRIGGER_KEYS = {
    "physical_safety", "recent_incident", "recent_physical",
    "weapon_present", "child_endangerment",
}


def _has_trigger(safety_doc: Optional[Dict[str, Any]], trigger_set: set) -> bool:
    """Look for named triggers inside a safety_doc's `result.triggers` list
    OR the `result.flags` list. Kept forgiving because the safety-screen
    scoring engine has evolved its output shape over time."""
    if not safety_doc:
        return False
    result = safety_doc.get("result") or {}
    for k in ("triggers", "flags", "high_concern"):
        for t in (result.get(k) or []):
            if isinstance(t, str) and t.lower() in trigger_set:
                return True
            if isinstance(t, dict):
                name = str(t.get("key") or t.get("name") or "").lower()
                if name in trigger_set:
                    return True
    return False


async def _load_party_context(
    db: AsyncIOMotorDatabase, user_id: str
) -> SinglePartyContext:
    """Aggregate one parent's inputs from Mongo."""
    profile = await db.users.find_one(
        {"user_id": user_id}, {"_id": 0, "name": 1},
    ) or {}
    safety = None  # in-app safety screen is off
    # NOTE: the Dimension Companion assessment persists to
    # `dimension_companion_assessments` (see dimension_companion_routes.py
    # `COLLECTION`). The old `dimension_companion` name is unused legacy.
    companion = await db.dimension_companion_assessments.find_one(
        {"user_id": user_id}, sort=[("created_at", -1)],
    )
    nd = await db.nd_assessments.find_one(
        {"target_user_id": user_id}, sort=[("created_at", -1)],
    )

    # Companion tiers.
    dim_tiers: Dict[str, Optional[str]] = {"communication": None, "emotional_regulation": None, "executive_function": None}
    if companion:
        dims = (((companion.get("scoring") or {}).get("dimensions")) or {})
        for k in dim_tiers:
            dim_tiers[k] = ((dims.get(k) or {}).get("tier"))

    # Compliance streak.
    streak = 0
    current_pct: Optional[float] = None
    try:
        from intervention_compliance_routes import build_compliance_snapshot
        snap = await build_compliance_snapshot(db, user_id)
        streak = int(((snap or {}).get("streak") or {}).get("current_streak") or 0)
        current_pct = ((snap or {}).get("current_week") or {}).get("compliance_pct")
    except Exception:  # noqa: BLE001
        pass

    safety_result = (safety or {}).get("result") or {}
    return SinglePartyContext(
        safety_level=safety_result.get("level"),
        safety_pathway_title=safety_result.get("pathway_title"),
        safety_coercive_trigger=_has_trigger(safety, _COERCIVE_TRIGGER_KEYS),
        safety_physical_trigger=_has_trigger(safety, _PHYSICAL_TRIGGER_KEYS),
        dim2_communication_tier=dim_tiers["communication"],
        dim3_emotional_reg_tier=dim_tiers["emotional_regulation"],
        dim4_executive_fn_tier=dim_tiers["executive_function"],
        nd_risk_tier=((nd or {}).get("scoring") or {}).get("tier"),
        nd_risk_score=((nd or {}).get("scoring") or {}).get("total_score"),
        compliance_streak_weeks=streak,
        compliance_current_pct=current_pct,
        display_name=profile.get("name") or "",
    )


async def _find_active_share(
    db: AsyncIOMotorDatabase, share_id: str, user_id: str,
) -> Dict[str, Any]:
    """Find an active Compare share the caller is a participant in.

    The Compare feature is realised by several parallel share collections
    — one per deep-dive pathway plus the SNC2 flow. Each carries the
    same shape: `{share_id, user_pair: [u1, u2], status, aligned_pct?}`.
    We iterate through them in order and return the first hit.
    """
    for collection_name in (
        "edu_deep_shares",
        "med_deep_shares",
        "psych_deep_shares",
        "snc2_shares",
        # Legacy fallback names — safe to include in case future flows
        # reuse them; no-ops if the collection is absent.
        "compare_shares",
    ):
        row = await db[collection_name].find_one(
            {"share_id": share_id}, {"_id": 0},
        )
        if row:
            break
    else:
        raise HTTPException(404, "Compare share not found.")

    if row.get("status") != "active":
        raise HTTPException(
            409,
            "This Compare share is not yet fully consented — the pathway "
            "report needs both parents' explicit consent through the "
            "Compare flow before it can be generated.",
        )
    if user_id not in (row.get("user_pair") or []):
        raise HTTPException(403, "You are not a participant in this share.")
    return row


# ---------------------------------------------------------------------------
# Routes.
# ---------------------------------------------------------------------------

@router.get("/preview")
async def preview_pathway_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """One-parent preview using only the caller's data. Always caveated."""
    ctx = await _load_party_context(db, user.user_id)
    result = score_pathway_single(ctx)
    out = result.to_public_dict()
    out["caller_display_name"] = ctx.display_name or ""
    out["data_inputs_present"] = {
        "dimension_companion": any([
            ctx.dim2_communication_tier,
            ctx.dim3_emotional_reg_tier,
            ctx.dim4_executive_fn_tier,
        ]),
        "nd_risk":           ctx.nd_risk_tier is not None,
        "compliance":        ctx.compliance_streak_weeks > 0,
    }
    return out


@router.get("/dual/{share_id}")
async def dual_pathway_report(
    share_id: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Full 2-parent report — gated behind an active Compare share."""
    share = await _find_active_share(db, share_id, user.user_id)
    pair: List[str] = list(share.get("user_pair") or [])
    if len(pair) != 2:
        raise HTTPException(500, "Share pair is malformed; cannot resolve both parents.")

    # Order pair so caller is always parent_a for label consistency.
    other = [uid for uid in pair if uid != user.user_id][0]
    ctx_a = await _load_party_context(db, user.user_id)
    ctx_b = await _load_party_context(db, other)

    # Compare-alignment: read the share's own snapshot if available.
    align_pct = share.get("aligned_pct")
    if align_pct is None:
        align_pct = (share.get("scoring") or {}).get("aligned_pct")

    ctx = DualPartyContext(
        parent_a=ctx_a, parent_b=ctx_b,
        compare_alignment_pct=(float(align_pct) if align_pct is not None else None),
        child_centered_alignment=None,
    )
    result = score_pathway_dual(ctx)
    out = result.to_public_dict()
    out["share_id"] = share_id
    # Never leak the co-parent's raw safety data — surface only that a
    # hard-lock fired without saying which parent tripped it.
    return out


# ---------------------------------------------------------------------------
# PDF export — same JSON payload as above, but rendered via
# `pathway_report_pdf.build_pathway_report_pdf` for handoff to a mediator
# or family-law attorney.
# ---------------------------------------------------------------------------

def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pathway_snapshot(result: Dict[str, Any]) -> Dict[str, Any]:
    """Small internal-only summary of what a given pathway PDF asserted.

    Recorded on `pathway_signatures` so operators can reconstruct a
    disputed report. Never exposed to the public verify endpoint.
    """
    return {
        "primary_key":      result.get("primary_pathway_key"),
        "primary_label":    result.get("primary_pathway_label"),
        "hard_locked":      bool(result.get("hard_locked_by")),
        "is_dual_party":    bool(result.get("is_dual_party")),
    }


@router.get("/preview/pdf")
async def preview_pathway_report_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Single-parent preview as a downloadable PDF."""
    from pathway_report_pdf import build_pathway_report_pdf
    from pathway_verify_routes import record_pathway_signature

    ctx = await _load_party_context(db, user.user_id)
    result = score_pathway_single(ctx)
    out = result.to_public_dict()

    # Record verify signature BEFORE building the PDF so the QR resolves
    # to the public "issued by SA CoParents" verify page.
    sig = await record_pathway_signature(
        db,
        user_id=user.user_id,
        is_dual_party=False,
        share_id=None,
        snapshot=_pathway_snapshot(out),
    )

    pdf_bytes = build_pathway_report_pdf(
        result=out,
        caller_display_name=ctx.display_name or "",
        data_inputs_present={
            "dimension_companion": any([
                ctx.dim2_communication_tier,
                ctx.dim3_emotional_reg_tier,
                ctx.dim4_executive_fn_tier,
            ]),
            "nd_risk":             ctx.nd_risk_tier is not None,
            "compliance":          ctx.compliance_streak_weeks > 0,
        },
        pathway_sig_id=sig["sig_id"],
        pathway_verify_url=sig["verify_url"],
    )
    return _pdf_response(pdf_bytes, "pathway-report-preview.pdf")


@router.get("/dual/{share_id}/pdf")
async def dual_pathway_report_pdf(
    share_id: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Full two-parent report as a downloadable PDF — same consent gate
    as the JSON endpoint (`_find_active_share`)."""
    from pathway_report_pdf import build_pathway_report_pdf
    from pathway_verify_routes import record_pathway_signature

    share = await _find_active_share(db, share_id, user.user_id)
    pair: List[str] = list(share.get("user_pair") or [])
    if len(pair) != 2:
        raise HTTPException(500, "Share pair is malformed; cannot resolve both parents.")
    other = [uid for uid in pair if uid != user.user_id][0]
    ctx_a = await _load_party_context(db, user.user_id)
    ctx_b = await _load_party_context(db, other)
    align_pct = share.get("aligned_pct")
    if align_pct is None:
        align_pct = (share.get("scoring") or {}).get("aligned_pct")

    ctx = DualPartyContext(
        parent_a=ctx_a, parent_b=ctx_b,
        compare_alignment_pct=(float(align_pct) if align_pct is not None else None),
        child_centered_alignment=None,
    )
    result = score_pathway_dual(ctx)
    out = result.to_public_dict()
    out["share_id"] = share_id

    sig = await record_pathway_signature(
        db,
        user_id=user.user_id,
        is_dual_party=True,
        share_id=share_id,
        snapshot=_pathway_snapshot(out),
    )

    pdf_bytes = build_pathway_report_pdf(
        result=out,
        caller_display_name=ctx_a.display_name or "",
        # Never leak per-input state for the other parent — surface only
        # the caller's own presence flags in the "data inputs used" block.
        data_inputs_present={
            "dimension_companion": any([
                ctx_a.dim2_communication_tier,
                ctx_a.dim3_emotional_reg_tier,
                ctx_a.dim4_executive_fn_tier,
            ]),
            "nd_risk":             ctx_a.nd_risk_tier is not None,
            "compliance":          ctx_a.compliance_streak_weeks > 0,
        },
        share_id=share_id,
        pathway_sig_id=sig["sig_id"],
        pathway_verify_url=sig["verify_url"],
    )
    return _pdf_response(pdf_bytes, f"pathway-report-{share_id}.pdf")


# ---------------------------------------------------------------------------
# Email export — send the pathway PDF directly to a mediator, attorney,
# etc. Mirrors the 4-Dimension Briefing email pattern in
# `dimension_companion_routes.email_four_dimension_briefing`.
# ---------------------------------------------------------------------------

_ROLE_TO_AUDIENCE = {
    "mediator":                    "Mediator",
    "parent_facilitator_ad_litem": "Parent Facilitator Ad Litem",
    "trial_court":                 "Trial Court",
    "attorney":                    "Family Law Attorney",
    "therapist":                   "Therapist / Counsellor",
    "other":                       "Mediator / Attorney / Trial Court",
}


class PathwayEmailBody(BaseModel):
    recipient_email: str = Field(..., max_length=200)
    recipient_name:  Optional[str] = Field(None, max_length=120)
    recipient_role:  Optional[Literal[
        "mediator", "parent_facilitator_ad_litem", "trial_court",
        "attorney", "therapist", "other",
    ]] = None
    audience_label:  Optional[str] = Field(None, max_length=120)
    parent_message:  Optional[str] = Field(None, max_length=1200)
    share_id:        Optional[str] = Field(
        None, max_length=64,
        description="If set, emails the two-parent report gated by this "
                    "active Compare share. Otherwise sends the single-"
                    "parent preview.",
    )


@router.post("/email")
async def email_pathway_report(
    body: PathwayEmailBody,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate the caller's Pathway Report PDF and email it directly to
    their mediator / attorney / court / therapist. Reply-to is the
    parent's email so the recipient can respond without an intermediary.

    Same consent gate as `/dual/{share_id}` — if a share_id is passed the
    endpoint refuses unless the Compare share is `active`.
    """
    from datetime import datetime, timezone
    from pathway_report_pdf import build_pathway_report_pdf
    from pathway_verify_routes import record_pathway_signature
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        send_pathway_report,
    )

    # ---- Validate inputs ---------------------------------------------------
    to_email = (body.recipient_email or "").strip().lower()
    if "@" not in to_email or "." not in to_email.split("@")[-1]:
        raise HTTPException(400, "That doesn't look like a valid email address.")
    if to_email.endswith("@demo.local"):
        raise HTTPException(400, "Please use your recipient's real email address.")

    parent_email = (user.email or "").strip().lower()
    if not parent_email or parent_email.endswith("@demo.local"):
        raise HTTPException(
            400,
            "Save your work first — add a real email to your account so the "
            "recipient can reply to you.",
        )

    audience = body.audience_label or _ROLE_TO_AUDIENCE.get(
        body.recipient_role or "other", _ROLE_TO_AUDIENCE["other"]
    )

    # ---- Score the pathway (preview vs dual) -------------------------------
    ctx_a = await _load_party_context(db, user.user_id)
    if body.share_id:
        share = await _find_active_share(db, body.share_id, user.user_id)
        pair: List[str] = list(share.get("user_pair") or [])
        if len(pair) != 2:
            raise HTTPException(500, "Share pair is malformed; cannot resolve both parents.")
        other = [uid for uid in pair if uid != user.user_id][0]
        ctx_b = await _load_party_context(db, other)
        align_pct = share.get("aligned_pct")
        if align_pct is None:
            align_pct = (share.get("scoring") or {}).get("aligned_pct")
        ctx = DualPartyContext(
            parent_a=ctx_a, parent_b=ctx_b,
            compare_alignment_pct=(float(align_pct) if align_pct is not None else None),
            child_centered_alignment=None,
        )
        result = score_pathway_dual(ctx)
        out = result.to_public_dict()
        out["share_id"] = body.share_id
        is_dual = True
    else:
        # Refuse the preview if the parent has literally nothing on file —
        # otherwise we'd email a mediator a report saying "nothing on
        # file" which looks like the app is broken.
        if (ctx_a.safety_level is None
                and not any([ctx_a.dim2_communication_tier,
                             ctx_a.dim3_emotional_reg_tier,
                             ctx_a.dim4_executive_fn_tier])
                and ctx_a.nd_risk_tier is None):
            raise HTTPException(
                404,
                "You have no assessment data on file yet. Complete the "
                "Dimension Companion first.",
            )
        result = score_pathway_single(ctx_a)
        out = result.to_public_dict()
        is_dual = False

    # ---- Record signature + build PDF --------------------------------------
    sig = await record_pathway_signature(
        db,
        user_id=user.user_id,
        is_dual_party=is_dual,
        share_id=body.share_id,
        snapshot=_pathway_snapshot(out),
    )

    pdf_bytes = build_pathway_report_pdf(
        result=out,
        caller_display_name=ctx_a.display_name or "",
        data_inputs_present={
            "dimension_companion": any([
                ctx_a.dim2_communication_tier,
                ctx_a.dim3_emotional_reg_tier,
                ctx_a.dim4_executive_fn_tier,
            ]),
            "nd_risk":             ctx_a.nd_risk_tier is not None,
            "compliance":          ctx_a.compliance_streak_weeks > 0,
        },
        share_id=body.share_id,
        pathway_sig_id=sig["sig_id"],
        pathway_verify_url=sig["verify_url"],
    )

    # ---- Send --------------------------------------------------------------
    try:
        send_pathway_report(
            to_email=to_email,
            recipient_name=(body.recipient_name or "").strip(),
            recipient_role=audience,
            parent_name=user.name or "",
            parent_email=parent_email,
            parent_message=(body.parent_message or "").strip(),
            is_dual_party=is_dual,
            primary_pathway_label=out.get("primary_pathway_label", ""),
            hard_locked=bool(out.get("hard_locked_by")),
            pdf_bytes=pdf_bytes,
        )
    except EmailNotConfigured as e:
        raise HTTPException(
            503,
            "Email isn't configured on this environment. Download the PDF "
            "and share it directly.",
        ) from e
    except EmailSendError as e:
        raise HTTPException(
            503,
            "Couldn't send the pathway report right now. Please try again "
            "in a moment.",
        ) from e

    # ---- Audit log ---------------------------------------------------------
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.pathway_report_emails.insert_one({
        "user_id":        user.user_id,
        "to_email":       to_email,
        "recipient_name": (body.recipient_name or "").strip(),
        "recipient_role": body.recipient_role,
        "audience":       audience,
        "share_id":       body.share_id or "",
        "is_dual_party":  is_dual,
        "sig_id":         sig["sig_id"],
        "sent_at":        now_iso,
    })
    return {
        "ok": True,
        "emailed_to": to_email,
        "audience": audience,
        "sig_id": sig["sig_id"],
        "is_dual_party": is_dual,
    }


# ---------------------------------------------------------------------------
# Reviewer comments — parent-facing feed.
#
# Every comment a professional leaves via the public verify page lives
# in the `pathway_report_comments` collection. This endpoint pulls the
# newest comments left across ANY pathway report the caller has issued
# (single-parent preview OR dual). Used by the Dashboard card to close
# the loop between the emailed report and the parent's next login.
# ---------------------------------------------------------------------------

@router.get("/comments/mine")
async def my_pathway_comments(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return every reviewer comment left on any pathway report issued
    to the caller. Newest-first, capped at 50 rows."""
    from pathway_verify_routes import list_comments_for_user
    rows = await list_comments_for_user(db, user.user_id, limit=50)
    return {"total": len(rows), "comments": rows}

