"""Educational Deep Dive API — mounted at /api/edu-deep.

Endpoints (all authenticated JWT):
  GET    /schema            Full section schema for the React UI
  GET    /me                Current user's saved assessment
  POST   /answer            Save a single answer
  POST   /answers/bulk      Save many answers in one call
  POST   /complete          Mark as complete
  DELETE /me                Reset the user's deep-dive assessment
  GET    /score             Live scoring / concern detection
  POST   /report/generate   Generate (or return cached) report
  GET    /report/pdf        Branded Letter PDF of the report

Guest users can persist a draft. Only claimed accounts can generate a report
(so we always attribute the report to a real name).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from ai_summary import generate_executive_summary
from ai_summary_gpt import generate_executive_summary_gpt
from deep_dive_section_coach import load_or_generate_section_coach
from edu_deep_questions import (
    DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION, public_schema, validate_answer,
)
from edu_deep_report import build_deep_dive_pdf, build_deep_dive_report
from edu_deep_scoring import score_deep_dive


router = APIRouter(prefix="/edu-deep", tags=["edu-deep"])
logger = logging.getLogger(__name__)

ASSESSMENTS = "edu_deep_assessments"
REPORTS = "edu_deep_reports"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "me")).strip("_") or "me"


async def _load(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db[ASSESSMENTS].find_one({"user_id": user_id}, {"_id": 0})


async def _upsert(db: AsyncIOMotorDatabase, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    now = _now_iso()
    updates.setdefault("updated_at", now)
    existing = await _load(db, user_id)
    if existing:
        await db[ASSESSMENTS].update_one({"user_id": user_id}, {"$set": updates})
        return {**existing, **updates}
    doc = {
        "assessment_id": f"edu_deep_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "completed": False,
        "responses": {},
        "deep_dive_version": DEEP_DIVE_VERSION,
    }
    doc.update(updates)
    await db[ASSESSMENTS].insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


# ---- Pydantic ----
class AnswerIn(BaseModel):
    question_id: str
    value: Any


class BulkAnswerIn(BaseModel):
    answers: Dict[str, Any]


class ProfileIn(BaseModel):
    child_name: Optional[str] = None


# ---- Endpoints ----
@router.get("/schema")
async def schema(_user: UserPublic = Depends(get_current_user)) -> Dict[str, Any]:
    return public_schema()


@router.get("/me")
async def me(user: UserPublic = Depends(get_current_user),
             db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await _load(db, user.user_id)
    if not doc:
        return {"has_assessment": False, "assessment": None}
    # v2 schema drop — silently discard any legacy v1 answer keys so the
    # frontend never repopulates a question that no longer exists in the
    # new schema.
    from edu_deep_questions import is_v2_key
    raw = dict(doc.get("responses") or {})
    filtered = {k: v for k, v in raw.items() if is_v2_key(k)}
    dropped = len(raw) - len(filtered)
    if dropped:
        await _upsert(db, user.user_id,
                     {"responses": filtered, "completed": False})
        doc["responses"] = filtered
        doc["completed"] = False
    return {"has_assessment": bool(doc), "assessment": doc}


@router.post("/profile")
async def set_profile(body: ProfileIn,
                      user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await _upsert(db, user.user_id, {"child_name": body.child_name})
    return {"ok": True, "assessment": doc}


@router.post("/answer")
async def answer(body: AnswerIn,
                 user: UserPublic = Depends(get_current_user),
                 db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    if not validate_answer(body.question_id, body.value):
        raise HTTPException(status_code=400,
                            detail=f"Invalid answer for {body.question_id}.")
    existing = await _load(db, user.user_id) or {}
    responses = dict(existing.get("responses") or {})
    responses[body.question_id] = body.value
    await _upsert(db, user.user_id, {"responses": responses})
    return {"ok": True, "question_id": body.question_id}


@router.post("/answers/bulk")
async def answers_bulk(body: BulkAnswerIn,
                       user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    valid = {}
    rejected = []
    for k, v in (body.answers or {}).items():
        if validate_answer(k, v):
            valid[k] = v
        else:
            rejected.append(k)
    existing = await _load(db, user.user_id) or {}
    responses = dict(existing.get("responses") or {})
    responses.update(valid)
    await _upsert(db, user.user_id, {"responses": responses})
    return {"ok": True, "answered": len(valid), "rejected": rejected}


@router.post("/complete")
async def complete(user: UserPublic = Depends(get_current_user),
                   db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await _load(db, user.user_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Please answer some questions first.")
    await _upsert(db, user.user_id, {"completed": True})
    return {"ok": True, "completed": True}


@router.delete("/me")
async def delete_me(user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    a = await db[ASSESSMENTS].delete_many({"user_id": user.user_id})
    r = await db[REPORTS].delete_many({"user_id": user.user_id})
    return {"ok": True, "deleted_assessments": a.deleted_count, "deleted_reports": r.deleted_count}


@router.get("/score")
async def score(user: UserPublic = Depends(get_current_user),
                db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await _load(db, user.user_id)
    if not doc:
        return {"has_assessment": False}
    return {"has_assessment": True, "score": score_deep_dive(doc.get("responses") or {})}


async def _cached_report(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db[REPORTS].find_one({"user_id": user_id}, {"_id": 0})


def _is_stale(doc: Dict[str, Any], report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return True
    if report.get("stale"):
        return True
    return (doc.get("updated_at") or "") > (report.get("source_updated_at") or "")


async def _build_and_cache(db, user, doc):
    responses = doc.get("responses") or {}
    if not responses:
        raise HTTPException(status_code=400, detail="Please answer some questions first.")
    if user.is_guest:
        raise HTTPException(status_code=403, detail="Please claim an account before generating your report.")
    content = build_deep_dive_report(
        parent_name=user.name,
        child_name=doc.get("child_name"),
        responses=responses,
    )
    ai_summary = await generate_executive_summary(
        product_name="Educational Needs Deep Dive",
        report=content,
    )
    if ai_summary:
        content["ai_summary"] = ai_summary
    record = {
        "report_id": f"edu_deep_r_{uuid.uuid4().hex[:12]}",
        "user_id": user.user_id,
        "assessment_id": doc.get("assessment_id"),
        "source_updated_at": doc.get("updated_at"),
        "generated_at": _now_iso(),
        "deep_dive_version": DEEP_DIVE_VERSION,
        "stale": False,
        "report": content,
    }
    await db[REPORTS].replace_one({"user_id": user.user_id}, record, upsert=True)
    record.pop("_id", None)
    return record


@router.post("/report/generate")
async def generate(user: UserPublic = Depends(get_current_user),
                   db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await _load(db, user.user_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Please answer some questions first.")
    cached = await _cached_report(db, user.user_id)
    if cached and not _is_stale(doc, cached):
        try:
            from joint_alignment_routes import mark_assessment_completed  # noqa: WPS433
            await mark_assessment_completed(db, user.user_id, "educational")
        except Exception:  # noqa: BLE001
            pass
        return {"cached": True, **cached}
    fresh = await _build_and_cache(db, user, doc)
    try:
        from joint_alignment_routes import mark_assessment_completed  # noqa: WPS433
        await mark_assessment_completed(db, user.user_id, "educational")
    except Exception:  # noqa: BLE001
        pass
    return {"cached": False, **fresh}


class RegenSummaryIn(BaseModel):
    length: Optional[str] = "standard"
    # "claude" (default) or "gpt". Lets a parent regenerate the same
    # summary through either model and compare voices. Iter130.
    model: Optional[str] = "claude"


@router.post("/report/regen-summary")
async def regen_summary(body: RegenSummaryIn = RegenSummaryIn(),
                        user: UserPublic = Depends(get_current_user),
                        db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    if user.is_guest:
        raise HTTPException(status_code=403, detail="Please claim an account before generating your report.")
    cached = await _cached_report(db, user.user_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    report = cached.get("report") or {}
    length = (body.length or "standard").lower()
    if length not in ("short", "standard", "long"):
        length = "standard"
    model_choice = (body.model or "claude").lower()
    if model_choice not in ("claude", "gpt"):
        model_choice = "claude"
    generator = (
        generate_executive_summary_gpt if model_choice == "gpt"
        else generate_executive_summary
    )
    new_summary = await generator(
        product_name="Educational Needs Deep Dive",
        report=report,
        length=length,
    )
    if not new_summary:
        raise HTTPException(status_code=503, detail="AI summary is unavailable right now. Please try again shortly.")
    now = _now_iso()
    report["ai_summary"] = new_summary
    report["ai_summary_length"] = length
    report["ai_summary_model"] = model_choice
    report["ai_summary_regenerated_at"] = now
    await db[REPORTS].update_one(
        {"user_id": user.user_id},
        {"$set": {
            "report": report,
            "ai_summary_regenerated_at": now,
            "ai_summary_length": length,
            "ai_summary_model": model_choice,
        }},
    )
    cached["report"] = report
    cached["ai_summary_regenerated_at"] = now
    cached["ai_summary_model"] = model_choice
    return {"ok": True, **cached}


@router.get("/report/pdf")
async def report_pdf(sign: bool = False, note: str = "",
                     user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)):
    cached = await _cached_report(db, user.user_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    from pdf_signing import sign_kwargs
    pdf_bytes = build_deep_dive_pdf(
        report=cached.get("report") or {}, **sign_kwargs(sign, user.name, note),
    )
    filename = f"Educational_Deep_Dive_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class EmailReportIn(BaseModel):
    to_email: Optional[str] = None


@router.post("/report/email")
async def report_email(
    body: EmailReportIn,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Email the parent their own Educational deep-dive report."""
    import email_service
    if user.is_guest:
        raise HTTPException(
            status_code=403,
            detail="Please claim an account before emailing your report.",
        )
    to_email = (body.to_email or user.email or "").strip().lower()
    if not to_email:
        raise HTTPException(status_code=400, detail="No email address on file.")
    cached = await _cached_report(db, user.user_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    pdf_bytes = build_deep_dive_pdf(report=cached.get("report") or {})
    filename = f"Educational_Deep_Dive_{_safe_filename(user.name or 'me')}.pdf"
    try:
        email_service.send_deep_dive_report_pdf(
            variant="educational",
            to_email=to_email,
            user_name=user.name,
            pdf_bytes=pdf_bytes,
            pdf_filename=filename,
        )
    except email_service.EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Email delivery isn't configured on this environment.",
        )
    except email_service.EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))
    from report_deliveries import record_email_delivery
    await record_email_delivery(
        db, user_id=user.user_id,
        report_type="edu_deep", to_email=to_email,
    )
    return {"ok": True, "sent_to": to_email, "filename": filename}



class SectionCoachIn(BaseModel):
    force: Optional[bool] = False


@router.post("/section/{section_id}/coach")
async def section_coach(section_id: str,
                        body: SectionCoachIn = SectionCoachIn(),
                        user: UserPublic = Depends(get_current_user),
                        db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """AI Personal Coach for a single Educational Deep Dive section."""
    doc = await _load(db, user.user_id) or {}
    responses = dict(doc.get("responses") or {})
    try:
        result = await load_or_generate_section_coach(
            db=db,
            user_id=user.user_id,
            sections_spec=DEEP_DIVE_SECTIONS,
            product_label="Educational Needs Deep Dive",
            pathway_id="edu-deep",
            section_id=section_id,
            responses=responses,
            force=bool(body.force),
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve
    if not result.get("ok"):
        raise HTTPException(
            status_code=503,
            detail="Your AI coach is resting right now. Please try again in a moment.",
        )
    return result
