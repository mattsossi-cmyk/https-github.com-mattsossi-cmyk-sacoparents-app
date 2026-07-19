"""Mediation prep routes: save/load prep data, AI analysis, summary, PDF export."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_current_user, create_share_token, decode_share_token, require_active_user

# Daily email cap for demo/guest accounts. Permanent accounts are uncapped.
# Overridable via env so an admin can dial this without a redeploy.
GUEST_EMAIL_DAILY_LIMIT = int(os.environ.get("GUEST_EMAIL_DAILY_LIMIT", "1"))
from models import (
    ChildGoalsPayload,
    IssuesPayload,
    PriorityPayload,
    CommStylePayload,
    ReadinessPayload,
    ReflectionPayload,
    CommAnalysisRequest,
    UserPublic,
)
import ai_service
import pdf_service
import certificate_service
import email_service
import journal_routes
from pydantic import BaseModel, EmailStr, Field


router = APIRouter(prefix="/mediation", tags=["mediation"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _save_section(db, user_id: str, section: str, payload: dict):
    await db.prep_data.update_one(
        {"user_id": user_id},
        {
            "$set": {
                section: payload,
                "updated_at": _now(),
                f"completed.{section}": True,
            },
            "$setOnInsert": {"user_id": user_id, "created_at": _now()},
        },
        upsert=True,
    )


async def _load_prep(db, user_id: str) -> Dict[str, Any]:
    doc = await db.prep_data.find_one({"user_id": user_id}, {"_id": 0})
    return doc or {"user_id": user_id, "completed": {}}


def _snapshot_prep(prep: Dict[str, Any]) -> Dict[str, Any]:
    """Freeze the parts of prep we want to compare across summaries."""
    return {
        "child_goals": prep.get("child_goals"),
        "issues": prep.get("issues"),
        "priority": prep.get("priority"),
        "comm_style": prep.get("comm_style"),
        "readiness": prep.get("readiness"),
    }


async def _previous_doc(db, collection: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Most recent doc of that type for the user — used as the comparison baseline."""
    return await db[collection].find_one(
        {"user_id": user_id, "prep_snapshot": {"$exists": True}},
        {"_id": 0},
        sort=[("generated_at", -1)],
    )


# ============ Save endpoints ============
@router.put("/child-goals")
async def save_child_goals(
    body: ChildGoalsPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "child_goals", body.dict())
    return {"ok": True}


@router.put("/issues")
async def save_issues(
    body: IssuesPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "issues", body.dict())
    return {"ok": True}


@router.put("/priority")
async def save_priority(
    body: PriorityPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "priority", body.dict())
    return {"ok": True}


@router.put("/comm-style")
async def save_comm_style(
    body: CommStylePayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "comm_style", body.dict())
    return {"ok": True}


@router.put("/readiness")
async def save_readiness(
    body: ReadinessPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    await _save_section(request.app.state.db, current.user_id, "readiness", body.dict())
    return {"ok": True}


@router.put("/reflection")
async def save_reflection(
    body: ReflectionPayload,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    payload = body.dict()
    db = request.app.state.db
    await _save_section(db, current.user_id, "reflection", payload)
    # Quietly archive a journal snapshot if the content changed since last save.
    await journal_routes.maybe_snapshot_reflection(db, current.user_id, payload)
    return {"ok": True}


@router.get("/prep")
async def get_prep(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    return await _load_prep(request.app.state.db, current.user_id)


# ============ AI endpoints ============
@router.post("/analyze-communication")
async def analyze_communication(
    body: CommAnalysisRequest,
    current: UserPublic = Depends(get_current_user),
):
    try:
        result = await ai_service.analyze_communication(
            body.answers or {}, body.text or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")


@router.post("/reframe")
async def reframe(
    body: dict,
    current: UserPublic = Depends(get_current_user),
):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    try:
        return await ai_service.reframe_message(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI reframe failed: {e}")


# Section-level coaching insights — replaces bare scores with 3 warm insights
# (strength, growth area, next step). Called from ReadinessCheck, CommStyle,
# and SafetyAssessment result cards. Section values: readiness | comm-style | safety
_ALLOWED_COACHING_SECTIONS = {"readiness", "comm-style", "safety", "overall"}


@router.post("/section-coaching")
async def section_coaching(
    body: dict,
    current: UserPublic = Depends(get_current_user),
):
    section = (body.get("section") or "").strip()
    payload = body.get("data") or {}
    if section not in _ALLOWED_COACHING_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"section must be one of {sorted(_ALLOWED_COACHING_SECTIONS)}",
        )
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="data must be a non-empty object")
    try:
        return await ai_service.generate_section_coaching(section, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coaching failed: {e}")


@router.post("/summary")
async def generate_summary(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    if not prep.get("child_goals") and not prep.get("issues"):
        raise HTTPException(
            status_code=400,
            detail="Please complete at least Child Goals or Issues first.",
        )
    previous = await _previous_doc(db, "summaries", current.user_id)
    # Compute deterministic readiness scores from raw prep data (0-100 per
    # dimension, plus overall). The AI narrative interprets these numbers
    # but never changes them.
    from readiness_scoring import compute_readiness  # local import
    readiness = compute_readiness(prep)
    try:
        summary = await ai_service.generate_summary(prep, current.name, previous, readiness=readiness)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summary failed: {e}")

    # Force the deterministic values onto the summary — trust the math, not the LLM.
    summary["readiness_score"] = readiness["overall"]
    summary["readiness_label"] = readiness["label"]
    summary["readiness"] = readiness

    summary_id = f"sum_{uuid.uuid4().hex[:12]}"
    doc = {
        **summary,
        "summary_id": summary_id,
        "user_id": current.user_id,
        "generated_at": _now(),
        "prep_snapshot": _snapshot_prep(prep),
        "previous_summary_id": previous.get("summary_id") if previous else None,
    }
    await db.summaries.insert_one(doc.copy())
    doc.pop("_id", None)

    # Schedule a 7-day post-event "How was mediation?" survey (idempotent —
    # only the first summary per user actually creates a doc; subsequent
    # summaries no-op).
    try:
        import survey_routes  # local import to avoid circular at module load
        await survey_routes.schedule_post_event_survey(
            db,
            user_id=current.user_id,
            email=current.email if not current.is_guest else None,
            name=current.name,
            summary_id=summary_id,
        )
    except Exception:  # noqa: BLE001
        # Survey scheduling must never block summary generation.
        pass

    # Also schedule a 14-day check-in with a personalised journal recap.
    try:
        import checkin_routes
        await checkin_routes.schedule_post_summary_checkin(
            db,
            user_id=current.user_id,
            email=current.email if not current.is_guest else None,
            name=current.name,
            summary_id=summary_id,
        )
    except Exception:  # noqa: BLE001
        pass

    return doc


@router.get("/summaries")
async def list_summaries(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.summaries.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/summary/{summary_id}/pdf")
async def download_summary_pdf(
    summary_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    summary = await db.summaries.find_one(
        {"summary_id": summary_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    prep = await _load_prep(db, current.user_id)
    pdf_bytes = pdf_service.build_summary_pdf(
        user_name=current.name,
        summary=summary,
        child_goals=prep.get("child_goals"),
        mediation_date=current.mediation_date,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="mediation_summary_{summary_id}.pdf"'
        },
    )


# ============ Certificate of Completion ============
class CertificateRequest(BaseModel):
    # Optional override — parents can dedicate the certificate to a display
    # name that differs from their account name (e.g. married name, preferred
    # name). Falls back to the account name when omitted or blank.
    name: Optional[str] = Field(default=None, max_length=120)


@router.get("/certificate/eligibility")
async def certificate_eligibility(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Report whether the parent has completed enough of the program to earn
    a certificate. The threshold is intentionally forgiving: 5 of 6 core prep
    steps done. Demo/guest users are always eligible so they can preview.
    """
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    completed = prep.get("completed") or {}
    core_steps = ["child_goals", "issues", "priority", "comm_style", "readiness", "reflection"]
    done = [k for k in core_steps if completed.get(k)]
    threshold = 5
    is_eligible = current.is_guest or len(done) >= threshold
    return {
        "eligible": is_eligible,
        "is_guest": current.is_guest,
        "completed_steps": done,
        "required_steps": core_steps,
        "threshold": threshold,
        "display_name": current.name or "",
    }


@router.get("/certificate/preview")
async def preview_certificate(
    request: Request,
    current: UserPublic = Depends(get_current_user),
    name: Optional[str] = None,
):
    """Return the composed certificate as an inline PNG for on-screen preview."""
    display = (name or current.name or "").strip()
    png = certificate_service.build_certificate_png(display)
    return StreamingResponse(
        BytesIO(png),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/certificate/download")
async def download_certificate(
    body: CertificateRequest,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    """Return the certificate as a downloadable PDF. Any authenticated user
    (including a demo/guest) can generate one; the demo watermark on the
    account itself communicates the sandbox state, not this document."""
    display = (body.name or current.name or "").strip()
    if not display:
        display = "Committed Co-Parent"
    pdf_bytes = certificate_service.build_certificate_pdf(display)

    # Best-effort audit trail — never fail the download over logging.
    try:
        await request.app.state.db.certificates_issued.insert_one(
            {
                "user_id": current.user_id,
                "display_name": display,
                "is_guest": current.is_guest,
                "issued_at": _now(),
            }
        )
    except Exception:  # noqa: BLE001
        pass

    safe_name = "".join(c if c.isalnum() else "_" for c in display).strip("_") or "certificate"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SA_CoParents_Certificate_{safe_name}.pdf"'
        },
    )


# ============ Co-Parenting Agreement Draft ============
@router.post("/agreement")
async def generate_agreement(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    if not prep.get("child_goals") and not prep.get("issues"):
        raise HTTPException(
            status_code=400,
            detail="Please complete at least Child Goals or Issues first.",
        )
    # Build a focused subset — goals, issues, priority only.
    focused = {
        "child_goals": prep.get("child_goals"),
        "issues": prep.get("issues"),
        "priority": prep.get("priority"),
    }
    previous = await _previous_doc(db, "agreements", current.user_id)
    from readiness_scoring import compute_readiness  # local import
    readiness = compute_readiness(prep)
    try:
        agreement = await ai_service.generate_agreement_draft(
            focused, current.name, previous, readiness=readiness
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI agreement failed: {e}")

    # Attach the deterministic readiness bundle so the frontend can draw bars.
    agreement["readiness"] = readiness

    agreement_id = f"agr_{uuid.uuid4().hex[:12]}"
    doc = {
        **agreement,
        "agreement_id": agreement_id,
        "user_id": current.user_id,
        "generated_at": _now(),
        "prep_snapshot": _snapshot_prep(prep),
        "previous_agreement_id": previous.get("agreement_id") if previous else None,
    }
    await db.agreements.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/agreements")
async def list_agreements(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.agreements.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


@router.get("/agreement/{agreement_id}/pdf")
async def download_agreement_pdf(
    agreement_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    agreement = await db.agreements.find_one(
        {"agreement_id": agreement_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    pdf_bytes = pdf_service.build_agreement_pdf(
        user_name=current.name,
        agreement=agreement,
        mediation_date=current.mediation_date,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="coparenting_agreement_{agreement_id}.pdf"'
        },
    )


# ============ Shareable download links (no-auth, signed) ============
@router.post("/summary/{summary_id}/share-link")
async def create_summary_share_link(
    summary_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    exists = await db.summaries.find_one(
        {"summary_id": summary_id, "user_id": current.user_id}, {"_id": 0, "summary_id": 1}
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Summary not found")
    token = create_share_token("summary", summary_id, current.user_id)
    return {"token": token, "path": f"/api/mediation/shared/{token}"}


@router.post("/agreement/{agreement_id}/share-link")
async def create_agreement_share_link(
    agreement_id: str,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    exists = await db.agreements.find_one(
        {"agreement_id": agreement_id, "user_id": current.user_id},
        {"_id": 0, "agreement_id": 1},
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Agreement not found")
    token = create_share_token("agreement", agreement_id, current.user_id)
    return {"token": token, "path": f"/api/mediation/shared/{token}"}


@router.get("/shared/{token}")
async def download_shared_pdf(
    token: str,
    request: Request,
):
    """Public endpoint: anyone with a valid signed token can download the PDF."""
    payload = decode_share_token(token)
    if not payload:
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db = request.app.state.db
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="This link is no longer valid.")

    doc_type = payload["doc_type"]
    doc_id = payload["doc_id"]
    if doc_type == "summary":
        doc = await db.summaries.find_one(
            {"summary_id": doc_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Summary not found")
        prep = await _load_prep(db, user["user_id"])
        pdf_bytes = pdf_service.build_summary_pdf(
            user_name=user.get("name", ""),
            summary=doc,
            child_goals=prep.get("child_goals"),
            mediation_date=user.get("mediation_date"),
        )
        filename = f"mediation_summary_{doc_id}.pdf"
    elif doc_type == "agreement":
        doc = await db.agreements.find_one(
            {"agreement_id": doc_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Agreement not found")
        pdf_bytes = pdf_service.build_agreement_pdf(
            user_name=user.get("name", ""),
            agreement=doc,
            mediation_date=user.get("mediation_date"),
        )
        filename = f"coparenting_agreement_{doc_id}.pdf"
    else:
        raise HTTPException(status_code=404, detail="Unknown document type")

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ============ Things I Can Improve On ============
@router.post("/improvement-plan")
async def generate_improvement_plan_route(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    prep = await _load_prep(db, current.user_id)
    comm = prep.get("comm_style")
    readiness = prep.get("readiness")
    if not comm and not readiness:
        raise HTTPException(
            status_code=400,
            detail="Please complete the Communication and Readiness steps first.",
        )
    previous = await _previous_doc(db, "improvement_plans", current.user_id)
    from readiness_scoring import compute_readiness  # local import
    readiness_scores = compute_readiness(prep)
    try:
        plan = await ai_service.generate_improvement_plan(
            comm, readiness, current.name, previous, readiness_scores=readiness_scores
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI plan failed: {e}")

    plan["readiness"] = readiness_scores

    plan_id = f"imp_{uuid.uuid4().hex[:12]}"
    doc = {
        **plan,
        "plan_id": plan_id,
        "user_id": current.user_id,
        "generated_at": _now(),
        "prep_snapshot": _snapshot_prep(prep),
        "previous_plan_id": previous.get("plan_id") if previous else None,
    }
    await db.improvement_plans.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/improvement-plans")
async def list_improvement_plans(
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    cursor = request.app.state.db.improvement_plans.find(
        {"user_id": current.user_id}, {"_id": 0}
    ).sort("generated_at", -1).limit(20)
    return await cursor.to_list(20)


# ============ Device registration (mobile push notifications) ============
class DeviceRegistration(BaseModel):
    token: str = Field(min_length=4, max_length=4096)
    platform: str = Field(min_length=1, max_length=20)  # "ios" | "android" | "web"


@router.post("/devices/register")
async def register_device(
    body: DeviceRegistration,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db
    # Upsert by (user_id, token) so re-registration is idempotent.
    await db.devices.update_one(
        {"user_id": current.user_id, "token": body.token},
        {
            "$set": {
                "user_id": current.user_id,
                "token": body.token,
                "platform": body.platform,
                "updated_at": _now(),
            },
            "$setOnInsert": {"registered_at": _now()},
        },
        upsert=True,
    )
    return {"ok": True}


# ============ Email to mediator ============
class MediatorEmailRequest(BaseModel):
    mediator_email: EmailStr
    mediator_name: Optional[str] = Field(default=None, max_length=120)
    summary_id: Optional[str] = None
    agreement_id: Optional[str] = None


@router.get("/email/status")
async def email_status(current: UserPublic = Depends(get_current_user)):
    return {"configured": email_service.is_configured()}


@router.post("/email-mediator")
async def email_mediator(
    body: MediatorEmailRequest,
    request: Request,
    current: UserPublic = Depends(get_current_user),
):
    db = request.app.state.db

    # Spam guardrail for demo/guest accounts. Permanent accounts have no
    # daily cap — they're identified, so misuse is recoverable.
    if current.is_guest:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        recent = await db.mediator_emails.count_documents(
            {"user_id": current.user_id, "sent_at": {"$gte": since}}
        )
        if recent >= GUEST_EMAIL_DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"You've already sent {recent} email(s) today from a demo session. "
                    "Set up a free account to send more."
                ),
            )

    if not body.summary_id and not body.agreement_id:
        raise HTTPException(
            status_code=400,
            detail="Please choose at least one document to attach.",
        )

    attachments: list = []
    doc_labels: list = []

    if body.summary_id:
        summary = await db.summaries.find_one(
            {"summary_id": body.summary_id, "user_id": current.user_id},
            {"_id": 0},
        )
        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")
        prep = await _load_prep(db, current.user_id)
        pdf_bytes = pdf_service.build_summary_pdf(
            user_name=current.name,
            summary=summary,
            child_goals=prep.get("child_goals"),
            mediation_date=current.mediation_date,
        )
        attachments.append(
            (f"mediation_summary_{body.summary_id}.pdf", pdf_bytes)
        )
        doc_labels.append("Mediation Summary")

    if body.agreement_id:
        agreement = await db.agreements.find_one(
            {"agreement_id": body.agreement_id, "user_id": current.user_id},
            {"_id": 0},
        )
        if not agreement:
            raise HTTPException(status_code=404, detail="Agreement draft not found")
        pdf_bytes = pdf_service.build_agreement_pdf(
            user_name=current.name,
            agreement=agreement,
            mediation_date=current.mediation_date,
        )
        attachments.append(
            (f"coparenting_agreement_{body.agreement_id}.pdf", pdf_bytes)
        )
        doc_labels.append("Co-Parenting Agreement Draft")

    try:
        email_service.send_mediator_email(
            to_email=body.mediator_email,
            mediator_name=body.mediator_name,
            user_name=current.name or "",
            user_email=current.email,
            attachments=attachments,
            doc_labels=doc_labels,
        )
    except email_service.EmailNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
    except email_service.EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Log the send (best-effort, not fatal).
    try:
        await db.mediator_emails.insert_one(
            {
                "user_id": current.user_id,
                "mediator_email": body.mediator_email,
                "mediator_name": body.mediator_name,
                "summary_id": body.summary_id,
                "agreement_id": body.agreement_id,
                "doc_labels": doc_labels,
                "sent_at": _now(),
            }
        )
    except Exception:
        pass

    return {"ok": True, "sent_to": body.mediator_email, "documents": doc_labels}


# ============ Resources (static seed) ============
RESOURCES = [
    {
        "id": "r2",
        "category": "High Conflict",
        "title": "Disengaging from Provocation",
        "description": "How to recognize bait and respond from a place of calm.",
        "kind": "video",
        "url": "https://youtu.be/7gjQnnUxLBs?si=ITTTAndKFYDaqugb",
    },
    {
        "id": "r8",
        "category": "Parallel Parenting",
        "title": "Parallel Parenting Explained (Video)",
        "description": "A clear walkthrough of how parallel parenting works in high-conflict situations and why it can be safer for the child than traditional co-parenting.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=b0IL8baFUmQ",
    },
    {
        "id": "r10",
        "category": "Parallel Parenting",
        "title": "Moving from Co-Parenting to Parallel Parenting (Video)",
        "description": "When traditional co-parenting isn't working, this walkthrough explains how to transition to a parallel parenting model and what to expect along the way.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=Tj9zCQgLnxA",
    },
    {
        "id": "r4",
        "category": "Communication",
        "title": "I-Statements for Co-Parents (Video)",
        "description": "A short walkthrough on using I-statements to express needs without triggering defensiveness — a key skill for keeping co-parenting conversations productive.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=gG25Kq_3gmg",
    },
    {
        "id": "r5",
        "category": "Rebuilding Trust",
        "title": "Small Consistent Wins (Video)",
        "description": "Trust is rebuilt through small, predictable actions over time. This short video unpacks how repeated, low-stakes follow-through rebuilds credibility with your co-parent and your child.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=k-k8lTJLFVU",
    },
    {
        "id": "r6",
        "category": "Parenting After Divorce",
        "title": "Helping Your Child Feel Safe",
        "description": "Practical scripts and rituals that anchor your child during transitions.",
        "kind": "video",
        "url": "https://youtu.be/oKd7PI_GjSs?si=xhm3g3pUjW1NLU3c",
    },
    {
        "id": "r7",
        "category": "Communication",
        "title": "BIFF Response Method — Bill Eddy",
        "description": "Watch Bill Eddy walk through the BIFF method (Brief, Informative, Friendly, Firm) for replying to high-conflict messages without escalating.",
        "kind": "video",
        "url": "https://www.youtube.com/watch?v=ggXhQLihi54",
    },
    {
        "id": "r9",
        "category": "Communication",
        "title": "BIFF — Bill Eddy's book (Amazon)",
        "description": "Get Bill Eddy's pocket-sized guide to writing Brief, Informative, Friendly, Firm responses to hostile emails, texts, and social media — perfect for high-conflict co-parenting.",
        "kind": "article",
        "url": "https://www.amazon.com/s?k=Bill+Eddy+BIFF&i=stripbooks",
    },
]


@router.get("/resources")
async def get_resources():
    return RESOURCES
