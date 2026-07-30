"""FastAPI routes for the SA CoParents Family Report.

Mounted at /api/family-report. Mirrors the surface of the CP and SN v3
report endpoints so all three reports share one consistent client API.
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
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db, create_share_token, decode_share_token
import family_report_content
import family_report_pdf


router = APIRouter(prefix="/family-report", tags=["family-report"])
logger = logging.getLogger(__name__)

COLLECTION = "family_reports"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (name or "report")).strip("_") or "report"


async def _load_sources(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, Any]:
    cp = await db.cp_reports.find_one({"user_id": user_id}, {"_id": 0})
    safety = await db.safety_assessments.find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)]
    )
    return {"cp": cp, "safety": safety}


@router.get("/status")
async def status(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    srcs = await _load_sources(db, user.user_id)
    cp, safety = srcs["cp"], srcs["safety"]
    fam = await db[COLLECTION].find_one({"user_id": user.user_id}, {"_id": 1})
    completed_count = sum(1 for x in [cp, safety] if x)
    return {
        "cp":     {"completed": bool(cp),     "generated_at": (cp or {}).get("generated_at"),   "label": "Co-Parenting Assessment",  "path": "/coparenting"},
        "safety": {"completed": bool(safety), "generated_at": (safety or {}).get("created_at"), "label": "Family Violence & Safety", "path": "/safety-assessment"},
        "completed_count": completed_count,
        "can_generate": completed_count >= 1,
        "has_family_report": bool(fam),
    }


@router.post("/generate")
async def generate_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    srcs = await _load_sources(db, user.user_id)
    if not any([srcs["cp"], srcs["safety"]]):
        raise HTTPException(
            status_code=400,
            detail="Complete at least one assessment (Co-Parenting or Safety) before generating a Family Report.",
        )
    report = family_report_content.build_family_report(
        parent_name=user.name,
        cp_doc=srcs["cp"],
        safety_doc=srcs["safety"],
    )
    report_id = f"fam_{uuid.uuid4().hex[:12]}"
    doc_out = {
        "report_id": report_id,
        "user_id": user.user_id,
        "generated_at": _now_iso(),
        "report": report,
    }
    await db[COLLECTION].replace_one({"user_id": user.user_id}, doc_out, upsert=True)
    doc_out.pop("_id", None)
    return doc_out


@router.get("")
async def get_report(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return {"report": None}
    return doc


@router.get("/pdf")
async def download_report_pdf(
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db[COLLECTION].find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Generate the Family Report first.")
    pdf_bytes = family_report_pdf.build_family_pdf(
        user_name=user.name or "",
        report=doc.get("report") or {},
    )
    filename = f"Family_Report_{_safe_filename(user.name or 'me')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class FamilyShareBody(BaseModel):
    excluded: Optional[List[str]] = None


@router.post("/{report_id}/share-link")
async def create_family_share_link(
    report_id: str,
    body: Optional[FamilyShareBody] = None,
    user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one(
        {"report_id": report_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    token = create_share_token("family_report", report_id, user.user_id, excluded_sections=[])
    return {
        "token": token,
        "path": f"/api/family-report/shared/{token}",
        "viewer_path": f"/shared/family/{token}",
    }


@router.get("/shared/{token}")
async def shared_family_report(
    token: str,
    request: Request,
    format: str = "pdf",
):
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "family_report":
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db = request.app.state.db
    owner = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not owner:
        raise HTTPException(status_code=404, detail="This link is no longer valid.")
    doc = await db[COLLECTION].find_one(
        {"report_id": payload["doc_id"], "user_id": owner["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    report = doc.get("report") or {}
    if format == "json":
        return {
            "report_id": doc.get("report_id"),
            "generated_at": doc.get("generated_at"),
            "report": report,
            "shared_by": owner.get("name") or "A co-parent",
        }
    pdf_bytes = family_report_pdf.build_family_pdf(
        user_name=owner.get("name") or "",
        report=report,
    )
    filename = f"Family_Report_shared_{_safe_filename(owner.get('name') or 'coparent')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
