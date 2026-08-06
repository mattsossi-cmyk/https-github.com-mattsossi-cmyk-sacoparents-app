"""Dimension Companion Assessment — covers Dimensions 2, 3 & 4 of the
four-dimension co-parenting model (Communication, Emotional Regulation,
Executive Function).

Design rules:
    * The Safety Assessment (Dim 1) MUST have been completed and cleared
      (level 3 or 4) before a parent enters this companion. That gate is
      enforced on the frontend result page; this router is idempotent and
      trusts the caller.
    * 5 Likert questions per dimension (1 = never … 5 = always). Some
      items are reverse-scored (marked in `reverse=True`) so a "5" on a
      strength-worded question counts as low concern.
    * Per-dimension raw score is averaged to 1..5, then bucketed into a
      tier: strong / steady / stretched / strained.
    * Overall pathway is derived from the WORST dimension (conservative).
    * Stored alongside safety in `dimension_companion_assessments`.

Routes:
    GET  /api/dimension-companion/questions   — question bank
    POST /api/dimension-companion              — submit + score
    GET  /api/dimension-companion/me           — latest for caller
    GET  /api/dimension-companion/{aid}        — single record
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, conint

from auth import UserPublic, get_current_user


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


router = APIRouter(prefix="/dimension-companion", tags=["dimension-companion"])

COLLECTION = "dimension_companion_assessments"

Dimension = Literal["communication", "emotional_regulation", "executive_function"]
Tier      = Literal["strong", "steady", "stretched", "strained"]


# ---------------------------------------------------------------------------
# QUESTION BANK — Dim 2 / 3 / 4
# ---------------------------------------------------------------------------
# Every question is Likert 1..5. `reverse=True` means the higher the answer
# the LOWER the concern (i.e., we invert before averaging).

QUESTIONS: Dict[Dimension, List[Dict[str, Any]]] = {
    "communication": [
        {"id": "c1", "text": "We can exchange logistics (pickup, medical, school) without it escalating.",     "reverse": True},
        {"id": "c2", "text": "Messages between us stay focused on the child, not on each other.",             "reverse": True},
        {"id": "c3", "text": "I feel I have to re-read or re-phrase my messages several times before sending.", "reverse": False},
        {"id": "c4", "text": "The other parent responds within a reasonable timeframe (within 24-48 hours).",   "reverse": True},
        {"id": "c5", "text": "Conversations spiral into blame, sarcasm, or long back-and-forth threads.",       "reverse": False},
    ],
    "emotional_regulation": [
        {"id": "e1", "text": "I notice when my stress is rising and can pause before responding.",             "reverse": True},
        {"id": "e2", "text": "After a difficult exchange, I can settle myself within an hour.",                "reverse": True},
        {"id": "e3", "text": "I feel physically activated (heart pounding, tight chest) when the other parent contacts me.", "reverse": False},
        {"id": "e4", "text": "I ruminate about co-parenting conflict long after the exchange is over.",       "reverse": False},
        {"id": "e5", "text": "I can put strong feelings aside long enough to make a child-focused decision.",  "reverse": True},
    ],
    "executive_function": [
        {"id": "x1", "text": "I can track custody schedule, appointments, and child activities without missing key items.", "reverse": True},
        {"id": "x2", "text": "I finish co-parenting tasks (forms, sign-offs, replies) before their deadlines.", "reverse": True},
        {"id": "x3", "text": "Small planning tasks (packing, transitions, paperwork) feel overwhelming.",     "reverse": False},
        {"id": "x4", "text": "I lose track of what was agreed verbally and rely on written records.",          "reverse": False},
        {"id": "x5", "text": "I can hold two competing priorities (child's needs vs. work) without collapsing one.", "reverse": True},
    ],
}


TIER_META: Dict[Tier, Dict[str, Any]] = {
    "strong": {
        "label": "Strong",
        "summary": "This dimension is working in your favor. Keep the habits that got you here.",
        "color": "#1F5C3B",
    },
    "steady": {
        "label": "Steady",
        "summary": "You have solid footing but there is room to sharpen a few habits.",
        "color": "#2D7A4A",
    },
    "stretched": {
        "label": "Stretched",
        "summary": "You are managing but running close to your limits. Targeted supports will help.",
        "color": "#8A5B00",
    },
    "strained": {
        "label": "Strained",
        "summary": "This dimension is a bottleneck. Focused interventions are strongly recommended.",
        "color": "#B02A2A",
    },
}


INTERVENTIONS_BY_TIER: Dict[Dimension, Dict[Tier, List[str]]] = {
    "communication": {
        "strong":    ["Keep your written-record habit — you don't need extra guardrails right now."],
        "steady":    ["Use the platform's message templates for logistics so tone stays neutral.",
                     "Batch replies into two windows per day to prevent thread spirals."],
        "stretched": ["Route ALL logistics through the platform — no verbal edits, no side channels.",
                     "Turn on the 30-minute cool-down between rapid replies.",
                     "Use headline-only subject lines (Pickup Friday 5pm) — no context in the body."],
        "strained":  ["Restrict to text-only templates; no free-form messages.",
                     "Enforce a 24-hour minimum response window; anything faster is optional.",
                     "Ask your coordinator to review outbound messages before delivery."],
    },
    "emotional_regulation": {
        "strong":    ["Continue your existing regulation practice; log which tools help you most."],
        "steady":    ["Add a 60-second breathing check before opening co-parent messages.",
                     "Journal one sentence per week about which trigger surprised you."],
        "stretched": ["Introduce a mandatory pause: read → wait 20 minutes → then draft your reply.",
                     "Book a weekly 20-minute wind-down slot on your calendar for co-parenting stress.",
                     "Use the platform's grounding prompt before responding to anything after 8pm."],
        "strained":  ["Consider a licensed therapist experienced in high-conflict co-parenting.",
                     "Adopt the 'no reply after 6pm' rule for at least 30 days.",
                     "Route emotionally charged exchanges to a co-parenting coach or coordinator."],
    },
    "executive_function": {
        "strong":    ["Keep your shared calendar as the single source of truth."],
        "steady":    ["Move recurring items (school pickups, medical) to a locked, unmodifiable calendar.",
                     "Set 24-hour advance reminders for every custody transition."],
        "stretched": ["Adopt the platform's checklist templates for pickup/drop-off/handoff.",
                     "Never accept verbal changes — always confirm in writing within an hour.",
                     "Break every co-parenting task into a single next physical action."],
        "strained":  ["Delegate scheduling to the platform's automated calendar — remove the mental load.",
                     "Ask for accommodations (deadlines, formatting) in writing from the other parent.",
                     "Consider an executive-function coach or ADHD specialist for supplementary support."],
    },
}


DIMENSION_META: Dict[Dimension, Dict[str, str]] = {
    "communication":         {"key": "communication",         "number": "2", "label": "Communication",         "hint": "Message tone, cadence, and clarity between co-parents."},
    "emotional_regulation":  {"key": "emotional_regulation",  "number": "3", "label": "Emotional regulation",  "hint": "How you handle stress and conflict activation."},
    "executive_function":    {"key": "executive_function",    "number": "4", "label": "Executive function",    "hint": "Planning, follow-through, task-switching capacity."},
}


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class DimensionAnswers(BaseModel):
    """One 1..5 Likert answer per question id."""
    communication:        Dict[str, conint(ge=1, le=5)]  # type: ignore[valid-type]
    emotional_regulation: Dict[str, conint(ge=1, le=5)]  # type: ignore[valid-type]
    executive_function:   Dict[str, conint(ge=1, le=5)]  # type: ignore[valid-type]


class CompanionSubmit(BaseModel):
    answers: DimensionAnswers
    notes:   Optional[str] = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------

def _score_dimension(dim: Dimension, answers: Dict[str, int]) -> Dict[str, Any]:
    """Return raw + normalized score + tier for a single dimension."""
    total_normalized = 0
    counted = 0
    per_item: List[Dict[str, Any]] = []
    for q in QUESTIONS[dim]:
        raw = answers.get(q["id"])
        if raw is None:
            continue
        # Reverse-scored items: 5 → 1 concern, 1 → 5 concern. Non-reverse
        # items already read "higher = more concern".
        concern = (6 - raw) if q["reverse"] else raw
        total_normalized += concern
        counted += 1
        per_item.append({"id": q["id"], "raw": raw, "concern": concern})

    if counted == 0:
        raise ValueError(f"No answers provided for dimension {dim}")

    avg = total_normalized / counted  # 1..5
    if avg <  2.0:  tier: Tier = "strong"
    elif avg < 3.0: tier = "steady"
    elif avg < 4.0: tier = "stretched"
    else:           tier = "strained"

    meta = TIER_META[tier]
    dmeta = DIMENSION_META[dim]
    return {
        "dimension":     dim,
        "dimension_num": dmeta["number"],
        "label":         dmeta["label"],
        "score":         round(avg, 2),
        "tier":          tier,
        "tier_label":    meta["label"],
        "summary":       meta["summary"],
        "interventions": INTERVENTIONS_BY_TIER[dim][tier],
        "per_item":      per_item,
    }


def score_companion(payload: CompanionSubmit) -> Dict[str, Any]:
    """Full scoring across the 3 companion dimensions."""
    a = payload.answers
    dims = {
        "communication":        _score_dimension("communication",        a.communication),
        "emotional_regulation": _score_dimension("emotional_regulation", a.emotional_regulation),
        "executive_function":   _score_dimension("executive_function",   a.executive_function),
    }
    tier_rank = {"strong": 0, "steady": 1, "stretched": 2, "strained": 3}
    worst = max(dims.values(), key=lambda d: tier_rank[d["tier"]])
    return {
        "dimensions":   dims,
        "worst_tier":   worst["tier"],
        "worst_label":  worst["label"],
        "overall_note": (
            "Your co-parenting bottleneck right now is "
            f"{worst['label']} ({worst['tier_label']}). Focus your energy there first."
        ),
    }


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@router.get("/questions")
async def get_questions():
    return {
        "dimensions": [
            {**DIMENSION_META[d], "questions": QUESTIONS[d]}
            for d in ("communication", "emotional_regulation", "executive_function")
        ],
        "likert_labels": [
            {"value": 1, "label": "Never / Not at all"},
            {"value": 2, "label": "Rarely"},
            {"value": 3, "label": "Sometimes"},
            {"value": 4, "label": "Often"},
            {"value": 5, "label": "Always / Every time"},
        ],
        "tiers": TIER_META,
    }


@router.post("")
async def submit_companion(
    body: CompanionSubmit,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        scored = score_companion(body)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    aid = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "assessment_id":  aid,
        "user_id":        user.user_id,
        "user_name":      user.name or "Parent",
        "created_at":     now,
        "answers":        body.answers.model_dump(),
        "scoring":        scored,
        "notes":          body.notes,
    }
    await db[COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/me")
async def latest_for_me(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db[COLLECTION].find_one(
        {"user_id": user.user_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    return {"latest": doc}


class BriefingEmailBody(BaseModel):
    recipient_email: str = Field(..., max_length=200)
    recipient_name:  Optional[str] = Field(None, max_length=120)
    recipient_role:  Optional[Literal["mediator", "parent_facilitator_ad_litem", "trial_court", "attorney", "therapist", "other"]] = None
    audience_label:  Optional[str] = Field(None, max_length=120,
        description="Free-form audience line stamped on the PDF cover. Defaults from role.")
    parent_message:  Optional[str] = Field(None, max_length=1200)


ROLE_TO_AUDIENCE = {
    "mediator":                    "Mediator",
    "parent_facilitator_ad_litem": "Parent Facilitator Ad Litem",
    "trial_court":                 "Trial Court",
    "attorney":                    "Family Law Attorney",
    "therapist":                   "Therapist / Counsellor",
    "other":                       "Mediator / Parent Facilitator Ad Litem / Trial Court",
}


def _briefing_snapshot(
    safety_doc: Optional[Dict[str, Any]],
    companion_doc: Optional[Dict[str, Any]],
    compliance: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Small internal-only summary of what a given briefing PDF asserted.

    Recorded on the `briefing_signatures` row so operators can reconstruct
    a disputed briefing without re-running the PDF builder. NEVER exposed
    to the public verify endpoint (privacy decision — the public page
    only confirms issued/not-issued + issue date).
    """
    snap: Dict[str, Any] = {}
    if safety_doc:
        r = (safety_doc.get("result") or {})
        snap["safety"] = {
            "level":          r.get("level"),
            "pathway_title":  r.get("pathway_title"),
        }
    if companion_doc:
        dims = ((companion_doc.get("scoring") or {}).get("dimensions") or {})
        snap["dimensions"] = {
            k: {"tier": (v or {}).get("tier"), "score": (v or {}).get("score")}
            for k, v in dims.items()
        }
    if compliance:
        snap["follow_through_pct"] = compliance.get("percent")
    return snap


@router.post("/four-dimension-briefing/email")
async def email_four_dimension_briefing(
    body: BriefingEmailBody,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate the parent's 4-Dimension Briefing and email it directly
    to their mediator, PFAL, trial court, attorney, or therapist. The
    parent's real email is used as reply-to so the recipient can respond
    without an intermediary.
    """
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from four_dimension_briefing_pdf import build_four_dimension_briefing_pdf
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        send_four_dimension_briefing,
    )

    # ---- Validate inputs ----------------------------------------------------
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

    # ---- Load latest Safety + Companion ------------------------------------
    safety_doc = await db.safety_assessments.find_one(
        {"user_id": user.user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    companion_doc = await db[COLLECTION].find_one(
        {"user_id": user.user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if not safety_doc and not companion_doc:
        raise HTTPException(
            404,
            "No Safety or Companion assessment on file yet. Complete at "
            "least one before emailing the briefing.",
        )

    audience = body.audience_label or ROLE_TO_AUDIENCE.get(body.recipient_role or "other", ROLE_TO_AUDIENCE["other"])

    # Follow-through snapshot for the email PDF too.
    from intervention_compliance_routes import build_compliance_snapshot
    try:
        compliance = await build_compliance_snapshot(db, user.user_id)
    except Exception:
        compliance = None

    # Record a briefing signature BEFORE building the PDF so the QR
    # stamped in the footer resolves to a public "issued by SA CoParents"
    # verify page.
    from briefing_verify_routes import record_briefing_signature
    sig_snapshot = _briefing_snapshot(safety_doc, companion_doc, compliance)
    sig = await record_briefing_signature(
        db,
        user_id=user.user_id,
        parent_name=user.name or "",
        audience=audience,
        snapshot=sig_snapshot,
    )

    pdf_bytes = build_four_dimension_briefing_pdf(
        parent_name=user.name or "Parent",
        audience=audience,
        safety_doc=safety_doc,
        companion_doc=companion_doc,
        compliance=compliance,
        generated_at=datetime.now(timezone.utc).isoformat(),
        briefing_sig_id=sig["sig_id"],
        briefing_verify_url=sig["verify_url"],
    )

    # ---- Send --------------------------------------------------------------
    try:
        send_four_dimension_briefing(
            to_email=to_email,
            recipient_name=(body.recipient_name or "").strip(),
            recipient_role=audience,
            parent_name=user.name or "",
            parent_email=parent_email,
            parent_message=(body.parent_message or "").strip(),
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
            "Couldn't send the briefing right now. Please try again in a moment.",
        ) from e

    # ---- Audit log ---------------------------------------------------------
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.four_dimension_briefing_emails.insert_one({
        "user_id":       user.user_id,
        "to_email":      to_email,
        "recipient_name": (body.recipient_name or "").strip(),
        "recipient_role": body.recipient_role,
        "audience":      audience,
        "sent_at":       now_iso,
    })
    return {"ok": True, "emailed_to": to_email, "audience": audience}


@router.get("/{aid}")
async def get_by_id(
    aid: str,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db[COLLECTION].find_one(
        {"assessment_id": aid, "user_id": user.user_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Assessment not found")
    return doc


# ---------------------------------------------------------------------------
# Combined 4-Dimension Briefing PDF — Safety + Companion in one document.
# Lives on this router (rather than a new one) because it depends on the
# Companion collection and this router is already registered under the
# authenticated /api namespace.
# ---------------------------------------------------------------------------

@router.get("/four-dimension-briefing/pdf")
async def download_four_dimension_briefing(
    audience: str = Query(
        "Mediator / Parent Facilitator Ad Litem / Trial Court",
        max_length=120,
        description="Free-form audience line printed on the cover page.",
    ),
    sign: bool = Query(False, description="Include signature line + verify QR."),
    signed_note: Optional[str] = Query(None, max_length=120),
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    from datetime import datetime, timezone
    from fastapi.responses import Response
    from four_dimension_briefing_pdf import build_four_dimension_briefing_pdf
    from pdf_signing import sign_kwargs

    safety_doc = await db.safety_assessments.find_one(
        {"user_id": user.user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    companion_doc = await db[COLLECTION].find_one(
        {"user_id": user.user_id}, {"_id": 0},
        sort=[("created_at", -1)],
    )
    if not safety_doc and not companion_doc:
        raise HTTPException(
            404,
            "No Safety or Companion assessment on file yet. Complete at least "
            "one before generating the four-dimension briefing.",
        )

    kwargs = sign_kwargs(sign, user.name, signed_note)

    # Include follow-through snapshot so the mediator sees compliance
    # alongside tier data.
    from intervention_compliance_routes import build_compliance_snapshot
    try:
        compliance = await build_compliance_snapshot(db, user.user_id)
    except Exception:
        compliance = None

    # Record a briefing signature BEFORE building the PDF so the footer
    # QR resolves to the public "issued by SA CoParents" verify page.
    from briefing_verify_routes import record_briefing_signature
    sig_snapshot = _briefing_snapshot(safety_doc, companion_doc, compliance)
    sig = await record_briefing_signature(
        db,
        user_id=user.user_id,
        parent_name=user.name or "",
        audience=audience,
        snapshot=sig_snapshot,
    )

    pdf_bytes = build_four_dimension_briefing_pdf(
        parent_name=user.name or "Parent",
        audience=audience,
        safety_doc=safety_doc,
        companion_doc=companion_doc,
        compliance=compliance,
        generated_at=datetime.now(timezone.utc).isoformat(),
        briefing_sig_id=sig["sig_id"],
        briefing_verify_url=sig["verify_url"],
        **kwargs,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                'attachment; filename="four-dimension-briefing.pdf"',
        },
    )
