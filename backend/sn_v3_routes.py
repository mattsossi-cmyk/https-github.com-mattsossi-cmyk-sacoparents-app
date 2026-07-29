"""FastAPI routes for the SA CoParents Special Needs 10-Principle Assessment.

Mounted at /api/special-needs-v3. Mirrors the surface of coparenting_routes.py.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db, create_share_token, decode_share_token
from sn_v3_questions import RESPONSE_SCALE, SECTIONS, find_question, total_question_count
from sn_v3_scoring import compute_scores, validate_answers
import sn_v3_report_content
import sn_v3_report_pdf
import report_visibility


router = APIRouter(prefix="/special-needs-v3", tags=["special-needs-v3"])
logger = logging.getLogger(__name__)
COLLECTION = "sn_v3_assessments"
REPORTS_COLLECTION = "sn_v3_reports"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "report")).strip("_") or "report"


class AnswerIn(BaseModel):
    question_id: str = Field(..., description="Question id, e.g. p3q4")
    value: int = Field(..., ge=0, le=4)


class AnswersBulkIn(BaseModel):
    answers: Dict[str, int]


async def _get_or_create_doc(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user_id, "completed": {"$ne": True}})
    if doc: return doc
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {"user_id": user_id, "answers": {}, "completed": False, "completed_at": None,
               "created_at": now, "updated_at": now, "scores": None}
    result = await db[COLLECTION].insert_one(new_doc)
    new_doc["_id"] = result.inserted_id
    return new_doc


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = str(doc.get("_id")) if doc.get("_id") is not None else None
    return out


@router.get("/schema")
async def get_schema() -> Dict[str, Any]:
    return {"response_scale": RESPONSE_SCALE, "sections": SECTIONS,
            "total_questions": total_question_count()}


@router.get("/me")
async def get_my_assessment(user: UserPublic = Depends(get_current_user),
                            db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id}, sort=[("updated_at", -1)])
    if not doc: return {"exists": False}
    return {"exists": True, **_serialize(doc)}


@router.post("/answer")
async def save_answer(body: AnswerIn, user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    if find_question(body.question_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown question id: {body.question_id}")
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"][body.question_id] = body.value
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one({"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}})
    return {"ok": True, "answered": len(doc["answers"]), "total": total_question_count()}


@router.post("/answers/bulk")
async def save_answers_bulk(body: AnswersBulkIn, user: UserPublic = Depends(get_current_user),
                             db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    ok, err = validate_answers(body.answers)
    if not ok: raise HTTPException(status_code=400, detail=err)
    doc = await _get_or_create_doc(db, user.user_id)
    doc["answers"].update(body.answers)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one({"_id": doc["_id"]},
        {"$set": {"answers": doc["answers"], "updated_at": doc["updated_at"]}})
    return {"ok": True, "answered": len(doc["answers"]), "total": total_question_count()}


@router.post("/complete")
async def complete_assessment(user: UserPublic = Depends(get_current_user),
                               db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id, "completed": {"$ne": True}})
    if not doc: raise HTTPException(status_code=404, detail="No in-progress assessment for this user.")
    scores = compute_scores(doc.get("answers") or {})
    now = datetime.now(timezone.utc).isoformat()
    await db[COLLECTION].update_one({"_id": doc["_id"]}, {"$set": {
        "completed": True, "completed_at": now, "updated_at": now, "scores": scores}})
    doc.update({"completed": True, "completed_at": now, "updated_at": now, "scores": scores})
    return {"ok": True, **_serialize(doc)}


@router.get("/scores")
async def get_scores(user: UserPublic = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id}, sort=[("updated_at", -1)])
    if not doc: raise HTTPException(status_code=404, detail="No assessment found for this user.")
    if doc.get("scores"): return doc["scores"]
    return compute_scores(doc.get("answers") or {})


@router.delete("/me")
async def reset_assessment(user: UserPublic = Depends(get_current_user),
                            db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    result = await db[COLLECTION].delete_many({"user_id": user.user_id})
    return {"ok": True, "deleted": result.deleted_count}


# ============================================================
# Report generation, retrieval, PDF, visibility, and sharing
# (Mirrors coparenting_routes.py 1:1)
# ============================================================
class SNVisibilityBody(BaseModel):
    excluded: List[str] = Field(default_factory=list)


class SNShareBody(BaseModel):
    excluded: Optional[List[str]] = None


async def _load_source_assessment(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one(
        {"user_id": user_id, "completed": True}, sort=[("completed_at", -1)]
    )
    if not doc:
        doc = await db[COLLECTION].find_one(
            {"user_id": user_id}, sort=[("updated_at", -1)]
        )
    if not doc:
        raise HTTPException(status_code=404, detail="No assessment on file - take the Special Needs Assessment first.")
    if not (doc.get("answers") or {}):
        raise HTTPException(status_code=400, detail="Please answer some questions before generating the report.")
    return doc


@router.post("/report/generate")
async def generate_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    source = await _load_source_assessment(db, user.user_id)
    answers: Dict[str, int] = source.get("answers") or {}
    scores = source.get("scores") or compute_scores(answers)
    report = sn_v3_report_content.build_report(
        scores=scores,
        answers=answers,
        parent_name=user.name,
    )
    report_id = f"sn_{uuid.uuid4().hex[:12]}"
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
    doc_out.pop("_id", None)
    return doc_out


@router.get("/report")
async def get_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[REPORTS_COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"report": None}
    return doc


@router.get("/report/pdf")
async def download_report_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    excluded: Optional[str] = None,
):
    doc = await db[REPORTS_COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    if excluded is not None:
        raw: List[str] = [x for x in excluded.split(",") if x]
    else:
        raw = list(((doc.get("visibility") or {}).get("excluded") or []))
    ex_list = report_visibility.clean_excluded("sn_v3_report", raw)
    report = sn_v3_report_pdf.filter_sn_v3_report(doc.get("report") or {}, ex_list)
    pdf_bytes = sn_v3_report_pdf.build_special_needs_pdf(
        user_name=user.name or "",
        report=report,
        excluded_sections=ex_list,
    )
    filename = f"Special_Needs_Report_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/report/visibility")
async def update_visibility(
    body: SNVisibilityBody,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    ex = report_visibility.clean_excluded("sn_v3_report", body.excluded)
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
    body: Optional[SNShareBody] = None,
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
    ex = report_visibility.clean_excluded("sn_v3_report", incoming)
    token = create_share_token("sn_v3_report", report_id, user.user_id, excluded_sections=ex)
    return {
        "token": token,
        "path": f"/api/special-needs-v3/report/shared/{token}",
        "viewer_path": f"/shared/special-needs/{token}",
        "excluded": ex,
    }


@router.get("/report/shared/{token}")
async def shared_report(
    token: str,
    request: Request,
    format: str = "pdf",
):
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "sn_v3_report":
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db = request.app.state.db
    owner = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not owner:
        raise HTTPException(status_code=404, detail="This link is no longer valid.")
    doc = await db[REPORTS_COLLECTION].find_one(
        {"report_id": payload["doc_id"], "user_id": owner["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    ex_list = report_visibility.clean_excluded("sn_v3_report", payload.get("ex") or [])
    filtered = sn_v3_report_pdf.filter_sn_v3_report(doc.get("report") or {}, ex_list)

    if format == "json":
        return {
            "report_id": doc.get("report_id"),
            "generated_at": doc.get("generated_at"),
            "scores": doc.get("scores"),
            "report": filtered,
            "excluded_sections": ex_list,
            "shared_by": owner.get("name") or "A co-parent",
        }

    pdf_bytes = sn_v3_report_pdf.build_special_needs_pdf(
        user_name=owner.get("name") or "",
        report=filtered,
        excluded_sections=ex_list,
    )
    filename = f"Special_Needs_Report_shared_{_safe_filename(owner.get('name') or 'coparent')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

