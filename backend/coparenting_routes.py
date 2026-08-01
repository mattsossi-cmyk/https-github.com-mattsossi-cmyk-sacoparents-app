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
import report_visibility


router = APIRouter(prefix="/coparenting", tags=["coparenting"])
logger = logging.getLogger(__name__)

COLLECTION = "cp_assessments"
REPORTS_COLLECTION = "cp_reports"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "report")).strip("_") or "report"


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
