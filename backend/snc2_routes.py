"""SA CoParents Special Needs Co-Parenting v2 API.

Mounted at /api/snc2.

Endpoints:
  GET  /schema?pathways=medical,educational        Public schema for the picker + full schema for the selection
  GET  /pathways                                    Catalog of the 4 pathways
  GET  /me                                          Current parent's assessment doc
  POST /select                                      Save the pathway picker
  POST /answer                                      Save a single answer
  POST /answers/bulk                                Save many answers
  POST /complete                                    Mark completed
  DELETE /me                                        Reset
  GET  /scores                                      Computed scores
  GET  /report                                      Cached report (or null)
  GET  /report/status                               Cache metadata + stale flag
  POST /report/generate                             Return-or-build cached report
  POST /report/regenerate                           Force rebuild
  GET  /report/pdf                                  Download PDF
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
from snc2_questions import (
    ASSESSMENT_VERSION, PATHWAYS, RESPONSE_SCALE, build_schema, resolve_pathways,
)
from snc2_scoring import compute_scores, validate_answer
from snc2_report_content import build_report
from snc2_report_pdf import build_snc2_pdf


router = APIRouter(prefix="/snc2", tags=["snc2"])
logger = logging.getLogger(__name__)

ASSESSMENTS = "snc2_assessments"
REPORTS = "snc2_reports"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "report")).strip("_") or "report"


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in doc.items() if k != "_id"} | ({"id": str(doc["_id"])} if doc.get("_id") else {})


# ------------ Pydantic ------------
class SelectIn(BaseModel):
    pathways: List[str] = Field(..., description="Any of: medical, educational, psychological, multiple")
    child_name: Optional[str] = Field(default=None, max_length=120)


class AnswerIn(BaseModel):
    question_id: str
    value: Any


class BulkIn(BaseModel):
    answers: Dict[str, Any]


# ------------ helpers ------------
async def _get_or_create(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user_id})
    if doc:
        return doc
    now = _now_iso()
    doc = {
        "user_id": user_id,
        "selected_pathways": [],
        "child_name": None,
        "answers": {},
        "completed": False,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
        "version": ASSESSMENT_VERSION,
    }
    result = await db[ASSESSMENTS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def _mark_stale(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db[REPORTS].update_one({"user_id": user_id}, {"$set": {"stale": True}})


def _coerce(value: Any) -> Any:
    """Coerce numeric Likert strings to int; leave other types alone."""
    if isinstance(value, str):
        try:
            n = int(value)
            if 1 <= n <= 5:
                return n
        except ValueError:
            pass
    return value


# ============ Schema / pathways ============
@router.get("/pathways")
async def get_pathways() -> Dict[str, Any]:
    return {"response_scale": RESPONSE_SCALE, "pathways": PATHWAYS,
            "assessment_version": ASSESSMENT_VERSION}


@router.get("/schema")
async def get_schema(pathways: str = "") -> Dict[str, Any]:
    selected = [p.strip() for p in pathways.split(",") if p.strip()]
    if not selected:
        return {"response_scale": RESPONSE_SCALE, "pathways_catalog": PATHWAYS,
                "assessment_version": ASSESSMENT_VERSION, "steps": []}
    try:
        return build_schema(selected)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Me / selection / answers ============
@router.get("/me")
async def get_me(user: UserPublic = Depends(get_current_user),
                 db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    if not doc:
        return {"exists": False}
    return {"exists": True, **_serialize(doc)}


@router.post("/select")
async def select_pathways(body: SelectIn,
                          user: UserPublic = Depends(get_current_user),
                          db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    pathways = resolve_pathways(body.pathways)
    if not pathways:
        raise HTTPException(status_code=400, detail="Pick at least one needs category.")
    doc = await _get_or_create(db, user.user_id)
    update = {"selected_pathways": body.pathways, "updated_at": _now_iso()}
    if body.child_name is not None:
        update["child_name"] = body.child_name.strip() or None
    await db[ASSESSMENTS].update_one({"_id": doc["_id"]}, {"$set": update})
    await _mark_stale(db, user.user_id)
    doc.update(update)
    return _serialize(doc)


@router.post("/answer")
async def save_answer(body: AnswerIn,
                      user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    value = _coerce(body.value)
    if not validate_answer(body.question_id, value):
        raise HTTPException(status_code=400, detail=f"Invalid answer for {body.question_id}.")
    doc = await _get_or_create(db, user.user_id)
    doc["answers"][body.question_id] = value
    doc["updated_at"] = _now_iso()
    await db[ASSESSMENTS].update_one({"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}})
    await _mark_stale(db, user.user_id)
    return {"ok": True, "answered": len(doc["answers"])}


@router.post("/answers/bulk")
async def save_bulk(body: BulkIn,
                    user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await _get_or_create(db, user.user_id)
    coerced: Dict[str, Any] = {}
    for k, v in (body.answers or {}).items():
        cv = _coerce(v)
        if not validate_answer(k, cv):
            raise HTTPException(status_code=400, detail=f"Invalid answer for {k}.")
        coerced[k] = cv
    doc["answers"].update(coerced)
    doc["updated_at"] = _now_iso()
    await db[ASSESSMENTS].update_one({"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}})
    await _mark_stale(db, user.user_id)
    return {"ok": True, "answered": len(doc["answers"])}


@router.post("/complete")
async def complete(user: UserPublic = Depends(get_current_user),
                   db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment on file.")
    now = _now_iso()
    scores = compute_scores(doc.get("selected_pathways") or [], doc.get("answers") or {})
    await db[ASSESSMENTS].update_one({"_id": doc["_id"]},
        {"$set": {"completed": True, "completed_at": now, "updated_at": now, "scores": scores}})
    await _mark_stale(db, user.user_id)
    doc.update({"completed": True, "completed_at": now, "updated_at": now, "scores": scores})
    return _serialize(doc)


@router.delete("/me")
async def reset(user: UserPublic = Depends(get_current_user),
                db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    a = await db[ASSESSMENTS].delete_many({"user_id": user.user_id})
    r = await db[REPORTS].delete_many({"user_id": user.user_id})
    return {"ok": True, "assessments_deleted": a.deleted_count, "reports_deleted": r.deleted_count}


@router.get("/scores")
async def get_scores(user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment on file.")
    return compute_scores(doc.get("selected_pathways") or [], doc.get("answers") or {})


# ============ Report ============
async def _cached(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db[REPORTS].find_one({"user_id": user_id}, {"_id": 0})


def _is_stale(assessment: Dict[str, Any], report: Optional[Dict[str, Any]]) -> bool:
    if not report:
        return True
    if report.get("stale") is True:
        return True
    src = report.get("source_updated_at") or ""
    return (assessment.get("updated_at") or "") > src


async def _build_and_cache(db: AsyncIOMotorDatabase, user: UserPublic,
                           assessment: Dict[str, Any]) -> Dict[str, Any]:
    if not assessment.get("selected_pathways"):
        raise HTTPException(status_code=400, detail="Please pick at least one needs category first.")
    report_content = build_report(
        parent_name=user.name,
        child_name=assessment.get("child_name"),
        selected_pathways=assessment.get("selected_pathways") or [],
        answers=assessment.get("answers") or {},
    )
    doc = {
        "report_id": f"snc2_{uuid.uuid4().hex[:12]}",
        "user_id": user.user_id,
        "assessment_id": str(assessment.get("_id")) if assessment.get("_id") else None,
        "source_updated_at": assessment.get("updated_at"),
        "generated_at": _now_iso(),
        "assessment_version": ASSESSMENT_VERSION,
        "stale": False,
        "report": report_content,
    }
    await db[REPORTS].replace_one({"user_id": user.user_id}, doc, upsert=True)
    doc.pop("_id", None)
    return doc


@router.get("/report/status")
async def report_status(user: UserPublic = Depends(get_current_user),
                        db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    assessment = await db[ASSESSMENTS].find_one({"user_id": user.user_id})
    report = await _cached(db, user.user_id)
    if not assessment:
        return {"has_assessment": False, "has_report": False}
    return {
        "has_assessment": True,
        "assessment_completed": bool(assessment.get("completed")),
        "assessment_updated_at": assessment.get("updated_at"),
        "selected_pathways": assessment.get("selected_pathways") or [],
        "has_report": report is not None,
        "generated_at": (report or {}).get("generated_at"),
        "stale": _is_stale(assessment, report),
    }


async def _load_assessment(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[ASSESSMENTS].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Take the assessment first.")
    if not (doc.get("selected_pathways")):
        raise HTTPException(status_code=400, detail="Please pick at least one needs category first.")
    if not (doc.get("answers") or {}):
        raise HTTPException(status_code=400, detail="Please answer some questions first.")
    return doc


@router.post("/report/generate")
async def generate(user: UserPublic = Depends(get_current_user),
                   db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    assessment = await _load_assessment(db, user.user_id)
    report = await _cached(db, user.user_id)
    if report and not _is_stale(assessment, report):
        return {"cached": True, **report}
    doc = await _build_and_cache(db, user, assessment)
    return {"cached": False, **doc}


@router.post("/report/regenerate")
async def regenerate(user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    assessment = await _load_assessment(db, user.user_id)
    doc = await _build_and_cache(db, user, assessment)
    return {"cached": False, **doc}


@router.get("/report")
async def get_report(user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    r = await _cached(db, user.user_id)
    if not r:
        return {"report": None}
    return r


@router.get("/report/pdf")
async def report_pdf(user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)):
    r = await _cached(db, user.user_id)
    if not r:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    pdf_bytes = build_snc2_pdf(report=r.get("report") or {})
    filename = f"Special_Needs_Report_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
