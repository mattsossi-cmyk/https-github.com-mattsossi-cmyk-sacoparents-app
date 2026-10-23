"""FastAPI routes for the SA CoParents 10-section Co-Parenting Assessment.

Mounted at /api/coparenting.

Endpoints:
  GET   /schema                     Returns the 10-section schema + response scale
  GET   /me                         The current user's most recent assessment (answers + scores)
  POST  /answer                     Save a single answer
  POST  /answers/bulk               Save many answers at once
  POST  /complete                   Mark the assessment complete, compute and persist scores
  GET   /scores                     Compute-and-return scores for the current user's saved answers
  DELETE /me                        Reset the current user's assessment (start over)

  POST  /report/generate                Build (or rebuild) the dynamic Co-Parenting report
  GET   /report                         Return the current user's stored report doc
  GET   /report/pdf                     Download the current report as a US Letter PDF
  PATCH /report/visibility              Persist the parent's excluded-section preference
  POST  /report/{report_id}/share-link  Create a signed public share token
  GET   /report/shared/{token}          Public read (json or pdf) using a share token
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db, create_share_token, decode_share_token
from share_routes import record_share_token, is_share_token_revoked
from coparenting_questions import RESPONSE_SCALE, SECTIONS, find_question, total_question_count
from coparenting_scoring import compute_scores, validate_answers
import cp_report_content
import cp_report_pdf
import cp_report_history
import cp_progress_pdf
import cp_preview_profile_pdf
import progress_share_analytics
import report_visibility


router = APIRouter(prefix="/coparenting", tags=["coparenting"])
logger = logging.getLogger(__name__)

COLLECTION = "cp_assessments"
REPORTS_COLLECTION = "cp_reports"


async def _shared_concern(db, user_id: str) -> bool:
    """The parent shared safety concerns: their own Self Journey pick, or the app's existing safety flag."""
    from self_assessment_reminders import is_safety_flagged

    sj = await db.self_journey_progress.find_one({"user_id": user_id}, {"_id": 0, "progress.safety.status": 1})
    if (((sj or {}).get("progress") or {}).get("safety") or {}).get("status") == "concern":
        return True
    return await is_safety_flagged(db, user_id)


async def _safer(db, user_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Stored report as every reader sees it: joint suggestions swapped when the parent shared concerns."""
    if doc.get("report") and await _shared_concern(db, user_id):
        return {**doc, "report": cp_report_content.safer_report(doc["report"])}
    return doc


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    """Mirror of the helper used by the main report PDF route — keep
    only alnum, dash, underscore so a parent name never breaks the
    Content-Disposition header."""
    out = []
    for ch in (name or "").strip():
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        elif ch == " ":
            out.append("_")
    return ("".join(out) or "me")[:40]


# ============================================================
# Pydantic models
# ============================================================
class AnswerIn(BaseModel):
    question_id: str = Field(..., description="Question id, e.g. s1q3")
    value: int = Field(..., ge=0, le=4, description="Likert value 0-4 (Never..Always)")


class AnswersBulkIn(BaseModel):
    answers: Dict[str, int] = Field(..., description="Map of question_id -> value")


# ============================================================
# Helpers
# ============================================================
async def _get_or_create_doc(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user_id, "completed": {"$ne": True}})
    if doc:
        return doc
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        "user_id": user_id,
        "answers": {},
        "completed": False,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
        "scores": None,
    }
    result = await db[COLLECTION].insert_one(new_doc)
    new_doc["_id"] = result.inserted_id
    return new_doc


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = str(doc.get("_id")) if doc.get("_id") is not None else None
    return out


# ============================================================
# Endpoints
# ============================================================
@router.get("/schema")
async def get_schema() -> Dict[str, Any]:
    """Return the full assessment schema for the UI to render."""
    return {
        "response_scale": RESPONSE_SCALE,
        "sections": SECTIONS,
        "total_questions": total_question_count(),
    }


@router.get("/me")
async def get_my_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the current user's in-progress OR most recent completed assessment."""
    doc = await db[COLLECTION].find_one(
        {"user_id": user.user_id}, sort=[("updated_at", -1)]
    )
    if not doc:
        return {"exists": False}
    return {"exists": True, **_serialize(doc)}


@router.post("/answer")
async def save_answer(
    body: AnswerIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    if find_question(body.question_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown question id: {body.question_id}")
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"][body.question_id] = body.value
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}},
    )
    return {"ok": True, "answered": len(doc["answers"]), "total": total_question_count()}


@router.post("/answers/bulk")
async def save_answers_bulk(
    body: AnswersBulkIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    ok, err = validate_answers(body.answers)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"].update(body.answers)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}},
    )
    return {"ok": True, "answered": len(doc["answers"]), "total": total_question_count()}


@router.post("/complete")
async def complete_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id, "completed": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="No in-progress assessment for this user.")
    scores = compute_scores(doc.get("answers") or {})
    now = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "completed": True,
                "completed_at": now,
                "updated_at": now,
                "scores": scores,
            }
        },
    )
    doc["completed"] = True
    doc["completed_at"] = now
    doc["updated_at"] = now
    doc["scores"] = scores
    return {"ok": True, **_serialize(doc)}


@router.get("/scores")
async def get_scores(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id}, sort=[("updated_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment found for this user.")
    if doc.get("scores"):
        return doc["scores"]
    return compute_scores(doc.get("answers") or {})


@router.delete("/me")
async def reset_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Delete all of the user's assessments (both in-progress and completed)."""
    result = await db[COLLECTION].delete_many({"user_id": user.user_id})
    return {"ok": True, "deleted": result.deleted_count}



# ============================================================
# Report generation, retrieval, PDF, visibility, and sharing
# ============================================================
class CPVisibilityBody(BaseModel):
    excluded: List[str] = Field(default_factory=list)


class CPShareBody(BaseModel):
    excluded: Optional[List[str]] = None
    expire_days: Optional[int] = 7  # 1 | 7 | 30 | None ("never")
    label: Optional[str] = None


async def _load_source_assessment(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    """Return the user's most-recent (completed if present, else in-progress) assessment doc.
    Raises 400/404 if no answers are on file."""
    doc = await db[COLLECTION].find_one(
        {"user_id": user_id, "completed": True}, sort=[("completed_at", -1)]
    )
    if not doc:
        doc = await db[COLLECTION].find_one(
            {"user_id": user_id}, sort=[("updated_at", -1)]
        )
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment on file — take the Co-Parenting Assessment first.")
    if not (doc.get("answers") or {}):
        raise HTTPException(status_code=400, detail="Please answer some questions before generating the report.")
    return doc


@router.post("/report/generate")
async def generate_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Build (or rebuild) the deterministic Co-Parenting report from the
    user's saved answers. Stored one-per-user in `cp_reports` (upsert)."""
    source = await _load_source_assessment(db, user.user_id)
    answers: Dict[str, int] = source.get("answers") or {}
    scores = source.get("scores") or compute_scores(answers)
    report = cp_report_content.build_report(
        scores=scores,
        answers=answers,
        parent_name=user.name,
    )
    report_id = f"cp_{uuid.uuid4().hex[:12]}"
    doc_out = {
        "report_id": report_id,
        "user_id": user.user_id,
        "generated_at": _now_iso(),
        "scores": scores,
        "report": report,
        "answered": len(answers),
        "total": total_question_count(),
    }
    await db[REPORTS_COLLECTION].replace_one(
        {"user_id": user.user_id}, doc_out, upsert=True
    )
    # Iter234 — append a lightweight snapshot to the user's history
    # doc so Alignment & Tools can draw a progress chart + fire the
    # 60-day retake nudge. Fire-and-forget semantics: a history
    # failure never breaks the parent's save.
    try:
        await cp_report_history.append_history(
            db,
            user_id=user.user_id,
            scores=scores,
            answered=len(answers),
            total=total_question_count(),
        )
    except Exception as hist_err:  # pragma: no cover — belt + braces
        logger.warning("cp_report_history append failed: %s", hist_err)
    from completion_alerts import schedule_completion_check
    schedule_completion_check(db, user.user_id)
    doc_out.pop("_id", None)
    return await _safer(db, user.user_id, doc_out)


@router.get("/report/progress")
async def get_report_progress(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Iter234 — progress payload for the Alignment & Tools progress
    tile: sparkline series, per-section movers, radar baseline vs
    recent, days-since-last, and the retake-due flag. Returns the
    same shape even when no history exists yet so the frontend can
    render its empty-state cleanly."""
    return await cp_report_history.build_progress_payload(
        db, user_id=user.user_id
    )


def _safe_filename(name: str) -> str:
    """Mirror of the helper used by the main report PDF route — keep
    only alnum, dash, underscore so a parent name never breaks the
    Content-Disposition header."""
    out = []
    for ch in (name or "").strip():
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        elif ch == " ":
            out.append("_")
    return ("".join(out) or "me")[:40]


@router.get("/report/progress/pdf")
async def download_report_progress_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    mediator_name: Optional[str] = None,
    note: Optional[str] = None,
    include_safety: bool = False,
    include_biff: bool = False,
):
    """Iter235 — download the one-page Progress Snapshot PDF for
    the current parent. Same payload the share-email route uses, but
    returned to the browser so the parent can preview / save a copy
    before sending it on."""
    progress = await cp_report_history.build_progress_payload(
        db, user_id=user.user_id,
    )
    if not (progress.get("snapshots") or []):
        raise HTTPException(
            status_code=404,
            detail="Take the Co-Parenting Assessment first — no progress yet.",
        )
    pdf_bytes = cp_progress_pdf.build_progress_pdf(
        parent_name=user.name or "a parent",
        progress=progress,
        mediator_name=(mediator_name or None),
        note=(note or None),
        **(await _progress_extras(db, user.user_id, include_safety, include_biff)),
    )
    filename = f"Progress_Snapshot_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


class ProgressShareRequest(BaseModel):
    to_email: str = Field(..., min_length=3)
    mediator_name: Optional[str] = Field(default=None, max_length=120)
    note: Optional[str] = Field(default=None, max_length=1200)
    include_safety: bool = False
    include_biff: bool = False


async def _progress_extras(db, user_id: str, include_safety: bool, include_biff: bool) -> Dict[str, Any]:
    """Opt-in Mediator PDF extras; omitted entirely unless the parent ticked them."""
    import cp_progress_extras

    extras: Dict[str, Any] = {}
    if include_safety:
        extras["safety_timeline"] = await cp_progress_extras.load_grey_rock_timeline(db, user_id)
    if include_biff:
        extras["biff_pairs"] = await cp_progress_extras.load_biff_pairs(db, user_id)
    return extras


@router.post("/report/progress/share")
async def share_report_progress(
    body: ProgressShareRequest,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Iter235 — email the one-page Progress Snapshot PDF to a
    mediator or other professional the parent names. The parent's
    own email is set as Reply-To so the mediator can respond
    directly."""
    to_email = (body.to_email or "").strip().lower()
    if "@" not in to_email or "." not in to_email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email.")

    progress = await cp_report_history.build_progress_payload(
        db, user_id=user.user_id,
    )
    if not (progress.get("snapshots") or []):
        raise HTTPException(
            status_code=400,
            detail="Take the Co-Parenting Assessment first — nothing to share yet.",
        )
    pdf_bytes = cp_progress_pdf.build_progress_pdf(
        parent_name=user.name or "a parent",
        progress=progress,
        mediator_name=(body.mediator_name or None),
        note=(body.note or None),
        **(await _progress_extras(db, user.user_id, body.include_safety, body.include_biff)),
    )

    # Import inline so an email misconfig in dev doesn't break the
    # /report/progress read path above.
    try:
        from email_service import send_cp_progress_share, EmailNotConfigured, EmailSendError
    except Exception as e:  # pragma: no cover
        logger.exception("progress-share email import failed")
        raise HTTPException(status_code=500, detail="Email service unavailable.") from e

    # iter237 — mint the share_id BEFORE sending so the open-tracking
    # pixel URL can be embedded in the outbound HTML. The share doc
    # is persisted up-front; a send failure below just leaves an
    # orphan "sent but not delivered" row, which the parent will see
    # as "Sent · never opened" — honest and self-explanatory.
    share_id = progress_share_analytics.mint_share_id()
    await progress_share_analytics.record_share(
        db,
        share_id=share_id,
        user_id=user.user_id,
        parent_name=user.name,
        to_email=to_email,
        mediator_name=body.mediator_name,
    )
    backend_base = os.environ.get("PUBLIC_BACKEND_URL", "").rstrip("/")
    if not backend_base:
        # Fall back to a relative URL — some email clients will still
        # resolve it against the From domain. Better: have ops set
        # PUBLIC_BACKEND_URL so the pixel always points at the
        # externally reachable preview/prod host.
        backend_base = ""
    pixel_url = (
        f"{backend_base}/api/coparenting/progress-share/{share_id}/pixel.gif"
        if backend_base
        else None
    )

    try:
        send_cp_progress_share(
            to_email=to_email,
            parent_name=user.name or "a parent",
            parent_email=getattr(user, "email", None),
            mediator_name=body.mediator_name,
            note=body.note,
            pdf_bytes=pdf_bytes,
            filename=f"Progress_Snapshot_{_safe_filename(user.name or 'me')}.pdf",
            tracking_pixel_url=pixel_url,
        )
    except EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Email delivery isn't configured yet. You can still "
                "download the PDF and send it from your own inbox."
            ),
        )
    except EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "ok": True,
        "to_email": to_email,
        "attached_bytes": len(pdf_bytes),
        "share_id": share_id,
    }


# ---- iter237 · Progress-share open-tracking pixel + list ----

# 1x1 transparent GIF used for the tracking pixel. Keeping this
# literal here means the pixel endpoint has zero file-system
# dependency.
_PIXEL_GIF = bytes.fromhex(
    "47494638396101000100800000ffffff00000021f9040100000000"
    "2c00000000010001000002024401003b"
)


@router.get("/progress-share/{share_id}/pixel.gif", include_in_schema=False)
async def progress_share_pixel(
    share_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Public (no-auth) 1x1 open-tracking pixel for shared Progress
    Snapshot emails. Always returns a 200 image/gif so bad clients
    never break — a mangled share_id just records nothing."""
    from fastapi.responses import Response
    try:
        await progress_share_analytics.record_open(db, share_id=share_id)
    except Exception as e:  # pragma: no cover
        logger.warning("progress pixel record_open failed: %s", e)
    return Response(
        content=_PIXEL_GIF,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/report/progress/shares")
async def list_progress_shares(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Iter237 — recent Progress-Snapshot shares with open status.
    Powers the "Share history" strip on the Alignment & Tools
    progress tile ("Opened by Dr. Rivera 2h ago")."""
    rows = await progress_share_analytics.recent_shares_for(
        db, user_id=user.user_id
    )
    return {"shares": rows}


# ========================================================================
# Iter241 — 40-question Preview Profile: branded PDF + save-to-account
# ========================================================================
class PreviewProfileScoreRow(BaseModel):
    domain: str = Field(..., max_length=120)
    score: float = Field(..., ge=0, le=5)


class PreviewProfileReflection(BaseModel):
    whats_working: Optional[str] = Field(default=None, max_length=2000)
    to_improve: Optional[str] = Field(default=None, max_length=2000)
    one_change: Optional[str] = Field(default=None, max_length=2000)


class PreviewProfileRequest(BaseModel):
    """Shape posted by `/coparenting-self-assessment-preview.html`."""
    parent_name: Optional[str] = Field(default=None, max_length=120)
    scores: List[PreviewProfileScoreRow] = Field(..., min_length=1, max_length=20)
    reflection: Optional[PreviewProfileReflection] = Field(default=None)


@router.post("/preview-profile/pdf")
async def download_preview_profile_pdf(body: PreviewProfileRequest):
    """Iter241 · Branded one-page PDF for the 40-question Preview
    Profile. Public (no auth): the HTML form on
    /coparenting-self-assessment-preview.html can be used without
    an account; the parent should still be able to download their
    profile."""
    pdf_bytes = cp_preview_profile_pdf.build_preview_profile_pdf(
        parent_name=(body.parent_name or "a parent"),
        scores=[s.model_dump() for s in body.scores],
        reflection=(body.reflection.model_dump() if body.reflection else {}),
        completed_at=datetime.utcnow().strftime("%b %d, %Y"),
    )
    filename = f"Coparenting_Preview_Profile_{_safe_filename(body.parent_name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/preview-profile/save")
async def save_preview_profile(
    body: PreviewProfileRequest,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Iter241 · Save a completed 40-question Preview Profile to the
    parent's account. We write a lightweight snapshot into the SAME
    `cp_report_history` collection the 70-question flow uses, tagged
    with `source="preview"` so the Alignment & Tools progress tile
    can render it alongside full-report snapshots.

    Section ids `d_0..d_7` are stable and distinct from the
    70-question `s1..s10` ids, so `_pick_baseline` / `_section_movers`
    only match preview-to-preview and report-to-report — mixing is
    silently ignored, which is the correct behaviour (a preview run
    is not comparable to a thorough run)."""
    scores_rows = [s.model_dump() for s in body.scores]
    avgs = [float(r["score"]) for r in scores_rows]
    overall_avg = sum(avgs) / len(avgs) if avgs else 0.0

    def _rate(a: float) -> str:
        if a >= 4.25: return "Excellent"
        if a >= 3.5:  return "Good"
        if a >= 2.75: return "Fair"
        if a >= 2.0:  return "Fair"
        return "Needs Improvement"

    scores_bundle = {
        "overall_rating": _rate(overall_avg),
        "sections": [
            {
                "id":     f"d_{i}",
                "number": i + 1,
                "name":   r["domain"],
                "rating": _rate(r["score"]),
                "avg":    round(float(r["score"]), 2),
            }
            for i, r in enumerate(scores_rows)
        ],
    }
    snapshot = await cp_report_history.append_history(
        db,
        user_id=user.user_id,
        scores=scores_bundle,
        answered=len(scores_rows) * 5,  # 5 Likert per domain
        total=len(scores_rows) * 5,
    )
    # Stamp the source so analytics / future-us can tell preview
    # snapshots apart. We update the just-appended row by
    # `submitted_at` — tiny race window, fine for a reflection tool.
    await db[cp_report_history.HISTORY_COLLECTION].update_one(
        {
            "_id": user.user_id,
            "snapshots.submitted_at": snapshot["submitted_at"],
        },
        {
            "$set": {
                "snapshots.$.source": "preview",
                "snapshots.$.reflection": (
                    body.reflection.model_dump() if body.reflection else None
                ),
            }
        },
    )
    return {
        "ok": True,
        "submitted_at": snapshot["submitted_at"],
        "overall_rating": snapshot["overall_rating"],
        "overall_value": snapshot["overall_value"],
        "domains": len(scores_rows),
    }


@router.get("/report")
async def get_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[REPORTS_COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"report": None}
    return await _safer(db, user.user_id, doc)


@router.get("/report/pdf")
async def download_report_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    excluded: Optional[str] = None,
):
    doc = await db[REPORTS_COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    doc = await _safer(db, user.user_id, doc)
    if excluded is not None:
        raw: List[str] = [x for x in excluded.split(",") if x]
    else:
        raw = list(((doc.get("visibility") or {}).get("excluded") or []))
    ex_list = report_visibility.clean_excluded("cp_report", raw)
    report = cp_report_pdf.filter_cp_report(doc.get("report") or {}, ex_list)
    pdf_bytes = cp_report_pdf.build_coparenting_pdf(
        user_name=user.name or "",
        report=report,
        excluded_sections=ex_list,
    )
    filename = f"CoParenting_Report_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/report/visibility")
async def update_visibility(
    body: CPVisibilityBody,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    ex = report_visibility.clean_excluded("cp_report", body.excluded)
    result = await db[REPORTS_COLLECTION].update_one(
        {"user_id": user.user_id},
        {"$set": {"visibility": {"excluded": ex, "updated_at": _now_iso()}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No report to update. Generate one first.")
    return {"excluded": ex}


@router.post("/report/{report_id}/share-link")
async def create_report_share_link(
    report_id: str,
    body: Optional[CPShareBody] = None,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[REPORTS_COLLECTION].find_one(
        {"report_id": report_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    incoming = body.excluded if body else None
    if incoming is None:
        incoming = (doc.get("visibility") or {}).get("excluded") or []
    ex = report_visibility.clean_excluded("cp_report", incoming)
    expire_days = body.expire_days if body else 7
    token = create_share_token(
        "cp_report", report_id, user.user_id,
        excluded_sections=ex, expire_days=expire_days,
    )
    payload = decode_share_token(token) or {}
    expires_at = None
    if payload.get("exp"):
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    await record_share_token(
        db,
        jti=payload.get("jti"),
        user_id=user.user_id,
        doc_type="cp_report",
        doc_id=report_id,
        expires_at=expires_at,
        label=(body.label if body else None),
    )
    return {
        "token": token,
        "jti": payload.get("jti"),
        "path": f"/api/coparenting/report/shared/{token}",
        "viewer_path": f"/shared/coparenting/{token}",
        "excluded": ex,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@router.get("/report/shared/{token}")
async def shared_report(
    token: str,
    request: Request,
    format: str = "pdf",
):
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "cp_report":
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db = request.app.state.db
    if await is_share_token_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=404, detail="This link has been revoked by the sender.")
    owner = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not owner:
        raise HTTPException(status_code=404, detail="This link is no longer valid.")
    doc = await db[REPORTS_COLLECTION].find_one(
        {"report_id": payload["doc_id"], "user_id": owner["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    doc = await _safer(db, owner["user_id"], doc)

    ex_list = report_visibility.clean_excluded("cp_report", payload.get("ex") or [])
    filtered = cp_report_pdf.filter_cp_report(doc.get("report") or {}, ex_list)

    if format == "json":
        return {
            "report_id": doc.get("report_id"),
            "generated_at": doc.get("generated_at"),
            "scores": doc.get("scores"),
            "report": filtered,
            "excluded_sections": ex_list,
            "shared_by": owner.get("name") or "A co-parent",
        }

    pdf_bytes = cp_report_pdf.build_coparenting_pdf(
        user_name=owner.get("name") or "",
        report=filtered,
        excluded_sections=ex_list,
    )
    filename = f"CoParenting_Report_shared_{_safe_filename(owner.get('name') or 'coparent')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
