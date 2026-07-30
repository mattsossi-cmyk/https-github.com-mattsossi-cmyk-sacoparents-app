"""FastAPI routes for the SA CoParents Special Needs Co-Parenting (SNC) product.

Mounted at /api/snc.

Endpoints:
  GET   /schema                Returns the 13-section schema + response scales
  GET   /me                    The current user's assessment doc (or {"exists": False})
  POST  /answer                Save a single answer
  POST  /answers/bulk          Save many answers at once
  POST  /complete              Mark the assessment complete
  GET   /scores                Compute-and-return scores for the current user
  DELETE /me                   Reset the current user's assessment

  GET   /report/status         Current cached report metadata + stale flag
  POST  /report/generate       Build (or return cached) individual parent report
  POST  /report/regenerate     Force-rebuild the report regardless of cache state
  GET   /report/pdf            Download the current cached report as a PDF
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db
from snc_questions import (
    RESPONSE_SCALE, CONSISTENCY_SCALE, SECTIONS, find_item, total_scored_items,
)
from snc_scoring import compute_scores, validate_answers
from snc_report_content import build_individual_report
from snc_report_pdf import build_snc_pdf
import email_service


router = APIRouter(prefix="/snc", tags=["snc"])
logger = logging.getLogger(__name__)

ASSESSMENTS = "snc_assessments"
REPORTS = "snc_reports"
ASSESSMENT_VERSION = "snc-2026-1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "report")).strip("_") or "report"


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = str(doc["_id"]) if doc.get("_id") is not None else None
    return out


# ============================================================
# Pydantic models
# ============================================================
class AnswerIn(BaseModel):
    question_id: str = Field(..., description="Question id, e.g. s2_q1")
    value: Any = Field(..., description="Answer value (int, str, list, or 'na')")


class AnswersBulkIn(BaseModel):
    answers: Dict[str, Any] = Field(..., description="Map of question_id -> value")


# ============================================================
# Helpers
# ============================================================
async def _get_or_create_doc(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user_id})
    if doc:
        return doc
    now = _now_iso()
    new_doc: Dict[str, Any] = {
        "user_id": user_id,
        "answers": {},
        "completed": False,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
        "version": ASSESSMENT_VERSION,
    }
    result = await db[ASSESSMENTS].insert_one(new_doc)
    new_doc["_id"] = result.inserted_id
    return new_doc


async def _touch_report_stale(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """When answers change, mark any cached report stale."""
    await db[REPORTS].update_one(
        {"user_id": user_id}, {"$set": {"stale": True}}
    )


def _coerce_value(item: Dict[str, Any], raw: Any) -> Any:
    """Best-effort coercion so callers can pass numeric strings for Likert/consistency."""
    itype = item.get("type")
    if itype in ("likert", "consistency"):
        if isinstance(raw, str) and raw not in ("na", "unknown"):
            try:
                return int(raw)
            except ValueError:
                return raw
    return raw


# ============================================================
# Assessment endpoints
# ============================================================
@router.get("/schema")
async def get_schema() -> Dict[str, Any]:
    return {
        "response_scale": RESPONSE_SCALE,
        "consistency_scale": CONSISTENCY_SCALE,
        "sections": SECTIONS,
        "total_scored_items": total_scored_items(),
        "assessment_version": ASSESSMENT_VERSION,
    }


@router.get("/me")
async def get_my_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    if not doc:
        return {"exists": False}
    return {"exists": True, **_serialize(doc)}


@router.post("/answer")
async def save_answer(
    body: AnswerIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    item = find_item(body.question_id)
    if item is None:
        raise HTTPException(status_code=400, detail=f"Unknown question id: {body.question_id}")
    value = _coerce_value(item, body.value)
    ok, err = validate_answers({body.question_id: value})
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"][body.question_id] = value
    doc["updated_at"] = _now_iso()
    await db[ASSESSMENTS].update_one(
        {"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}},
    )
    await _touch_report_stale(db, user.user_id)
    return {"ok": True, "answered": len(doc["answers"])}


@router.post("/answers/bulk")
async def save_answers_bulk(
    body: AnswersBulkIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    coerced: Dict[str, Any] = {}
    for qid, v in body.answers.items():
        item = find_item(qid)
        coerced[qid] = _coerce_value(item, v) if item else v
    ok, err = validate_answers(coerced)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"].update(coerced)
    doc["updated_at"] = _now_iso()
    await db[ASSESSMENTS].update_one(
        {"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}},
    )
    await _touch_report_stale(db, user.user_id)
    return {"ok": True, "answered": len(doc["answers"])}


@router.post("/complete")
async def complete_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment on file — answer some questions first.")
    now = _now_iso()
    scores = compute_scores(doc.get("answers") or {})
    await db[ASSESSMENTS].update_one(
        {"_id": doc["_id"]},
        {"$set": {"completed": True, "completed_at": now, "updated_at": now, "scores": scores}},
    )
    await _touch_report_stale(db, user.user_id)
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
    doc = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment on file.")
    return compute_scores(doc.get("answers") or {})


@router.delete("/me")
async def reset_assessment(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    deleted_a = await db[ASSESSMENTS].delete_many({"user_id": user.user_id})
    deleted_r = await db[REPORTS].delete_many({"user_id": user.user_id})
    return {"ok": True, "assessments_deleted": deleted_a.deleted_count,
            "reports_deleted": deleted_r.deleted_count}


# ============================================================
# Report generation / caching
# ============================================================
async def _load_assessment(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Take the Special Needs Co-Parenting Assessment first.")
    if not (doc.get("answers") or {}):
        raise HTTPException(status_code=400, detail="Please answer some questions before generating the report.")
    return doc


async def _cached_report(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db[REPORTS].find_one({"user_id": user_id}, {"_id": 0})


def _is_stale(assessment: Dict[str, Any], report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return True
    if report.get("stale") is True:
        return True
    src = report.get("source_updated_at")
    if not src:
        return True
    return (assessment.get("updated_at") or "") > src


async def _build_and_cache(
    db: AsyncIOMotorDatabase,
    user: UserPublic,
    assessment: Dict[str, Any],
    *,
    preserve_notified: bool = True,
) -> Dict[str, Any]:
    answers: Dict[str, Any] = assessment.get("answers") or {}
    scores = compute_scores(answers)
    report_content = build_individual_report(
        parent_name=user.name,
        answers=answers,
        scores=scores,
        include_safety=True,
        assessment_version=ASSESSMENT_VERSION,
    )
    existing = await db[REPORTS].find_one({"user_id": user.user_id}, {"notified_at": 1})
    notified_at = (existing or {}).get("notified_at") if preserve_notified else None
    doc_out: Dict[str, Any] = {
        "report_id": f"snc_{uuid.uuid4().hex[:12]}",
        "user_id": user.user_id,
        "assessment_id": str(assessment.get("_id")) if assessment.get("_id") else None,
        "source_updated_at": assessment.get("updated_at"),
        "generated_at": _now_iso(),
        "assessment_version": ASSESSMENT_VERSION,
        "stale": False,
        "scores": scores,
        "report": report_content,
        "answered": len(answers),
        "notified_at": notified_at,
    }
    await db[REPORTS].replace_one({"user_id": user.user_id}, doc_out, upsert=True)
    doc_out.pop("_id", None)
    return doc_out


def _notify_report_ready(
    db: AsyncIOMotorDatabase,
    user: UserPublic,
    doc_out: Dict[str, Any],
) -> Optional[str]:
    """Send the one-time 'your report is ready' email with the PDF attached.

    Silently degrades when Resend is not configured (e.g. tests) or when the
    user has no email address.  Returns the ISO timestamp of the successful
    send or None on skip/failure.
    """
    to_email = getattr(user, "email", None)
    if not to_email or not email_service.is_configured():
        return None
    try:
        report = doc_out.get("report") or {}
        pdf_bytes = build_snc_pdf(report=report)
        child = report.get("child_profile") or {}
        child_name = (child.get("age_grade") or "").split(",")[0].strip() or None
        priority = ((report.get("at_a_glance") or {}).get("priority_concerns")) or []
        open_url = f"https://sacoparentsapp.online/special-needs/report"
        email_service.send_snc_report_ready(
            to_email=to_email,
            user_name=getattr(user, "name", None),
            child_first_name=None if not child_name or len(child_name) > 40 else child_name,
            priority_concerns=priority,
            open_report_url=open_url,
            pdf_bytes=pdf_bytes,
        )
        return _now_iso()
    except Exception:  # noqa: BLE001
        logger.exception("SNC report-ready email failed for %s", user.user_id)
        return None


@router.get("/report/status")
async def report_status(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    assessment = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    report = await _cached_report(db, user.user_id)
    if not assessment:
        return {"has_assessment": False, "has_report": False}
    return {
        "has_assessment": True,
        "assessment_updated_at": assessment.get("updated_at"),
        "assessment_completed": bool(assessment.get("completed")),
        "has_report": report is not None,
        "generated_at": (report or {}).get("generated_at"),
        "notified_at": (report or {}).get("notified_at"),
        "stale": _is_stale(assessment, report),
        "report_id": (report or {}).get("report_id"),
    }


@router.post("/report/generate")
async def generate_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return the cached report when fresh; otherwise build a new one and cache it.

    The first time a fresh report is cached, the parent is emailed a
    "your report is ready" note with the PDF attached (single one-time send).
    """
    assessment = await _load_assessment(db, user.user_id)
    report = await _cached_report(db, user.user_id)
    if report and not _is_stale(assessment, report):
        return {"cached": True, **report}
    doc = await _build_and_cache(db, user, assessment)
    if not doc.get("notified_at"):
        sent_at = _notify_report_ready(db, user, doc)
        if sent_at:
            doc["notified_at"] = sent_at
            await db[REPORTS].update_one(
                {"user_id": user.user_id}, {"$set": {"notified_at": sent_at}}
            )
    return {"cached": False, **doc}


@router.post("/report/regenerate")
async def regenerate_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Force a fresh build regardless of cache state (no email — the parent
    already received the one-time 'report ready' notification)."""
    assessment = await _load_assessment(db, user.user_id)
    doc = await _build_and_cache(db, user, assessment)
    return {"cached": False, **doc}


@router.post("/report/email")
async def email_report_to_me(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Re-send the "your report is ready" email to the parent on demand.

    Returns HTTP 200 with a `sent` boolean so the frontend can render a
    friendly message even when the Resend account/domain isn't fully set up.
    """
    if not getattr(user, "email", None):
        return {"sent": False, "reason": "Add an email address to your profile first."}
    if not email_service.is_configured():
        return {"sent": False, "reason": "Email is not configured on this deployment."}
    assessment = await _load_assessment(db, user.user_id)
    report = await _cached_report(db, user.user_id)
    if not report or _is_stale(assessment, report):
        report = await _build_and_cache(db, user, assessment)
    sent_at = _notify_report_ready(db, user, report)
    if not sent_at:
        return {
            "sent": False,
            "reason": "Your report couldn't be delivered right now. "
                      "Download the PDF from this page and share it directly.",
        }
    await db[REPORTS].update_one(
        {"user_id": user.user_id}, {"$set": {"notified_at": sent_at}}
    )
    return {"sent": True, "sent_at": sent_at, "to": user.email}


@router.get("/report")
async def get_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    report = await _cached_report(db, user.user_id)
    if not report:
        return {"report": None}
    return report


@router.get("/report/pdf")
async def download_report_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    report = await _cached_report(db, user.user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    pdf_bytes = build_snc_pdf(report=report.get("report") or {})
    filename = f"Special_Needs_Report_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
