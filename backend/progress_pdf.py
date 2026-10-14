"""One-page, status-only progress PDF for a professional's case file (court codes + joint cases). Never answers."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from motor.motor_asyncio import AsyncIOMotorDatabase

from auth import get_current_user, get_db
from court_checklist import (AMBER, EMERALD, INK, MUTED, PURPLE, REQUESTABLE, _ChecklistPDF, _box, _day, _safe,
                             case_requested_keys, progress_rows)
from court_codes_routes import linked_parents
from models import UserPublic

router = APIRouter(prefix="/professional", tags=["progress-pdf"])

_LABEL = {"done": "Done", "in_progress": "In progress", "todo": "Not started"}


def _header(pdf: FPDF, d: Dict[str, Any]) -> None:
    pdf.set_fill_color(*PURPLE)
    pdf.rect(0, 0, pdf.w, 25, "F")
    pdf.set_xy(16, 6.5)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, d.get("title", "Assessment Progress"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(16)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(221, 214, 254)
    pdf.cell(0, 5, _safe(d.get("tagline", "SA CoParents  ·  Status only: never answers")))
    pdf.set_xy(16, 31)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*INK)
    heading = d.get("heading") or f"{d['kind']} {d['ref']}" + (f"  ·  {d['label']}" if d["label"] else "")
    pdf.cell(0, 6, _safe(heading), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, _safe(f"{d['state']}     Prepared {_day(d['generated_at'])}".strip()), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _parent(pdf: FPDF, p: Dict[str, Any]) -> None:
    rows = p["assessments"]
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PURPLE)
    if rows is None:
        pdf.cell(0, 6, _safe(f"{p['name']}  ·  hasn't joined yet"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        return
    done = sum(r["status"] == "done" for r in rows)
    pdf.cell(0, 6, _safe(f"{p['name']}  ·  {done} of {len(rows)} done"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.5)
    for r in rows:
        y = pdf.get_y()
        _box(pdf, pdf.l_margin, y + 0.6, r["status"])
        pdf.set_xy(pdf.l_margin + 8, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*INK)
        pdf.cell(95, 5.8, _safe(r["title"]))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*(EMERALD if r["status"] == "done" else AMBER if r["status"] == "in_progress" else MUTED))
        tail = f" · {_day(r['finished_at'])}" if r["status"] == "done" and r.get("finished_at") else ""
        pdf.cell(0, 5.8, _safe(_LABEL[r["status"]] + tail), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(236, 232, 245)
        pdf.line(pdf.l_margin, pdf.get_y() + 1.2, pdf.w - pdf.r_margin, pdf.get_y() + 1.2)
        pdf.set_y(pdf.get_y() + 2.6)
    pdf.ln(3)


def build_progress_pdf(d: Dict[str, Any]) -> bytes:
    pdf = _ChecklistPDF(format="Letter")
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    _header(pdf, d)
    if not d["parents"]:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, "No parent has entered this code yet.", new_x="LMARGIN", new_y="NEXT")
    for p in d["parents"]:
        _parent(pdf, p)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.6, _safe(d.get("closing", "This page shows only whether each assessment you asked for is done, in "
                                             "progress or not started. SA CoParents never shares a parent's answers.")))
    return bytes(pdf.output())


def _pdf_response(d: Dict[str, Any]) -> StreamingResponse:
    name = d.get("filename") or f"SA_CoParents_Progress_{d['ref']}.pdf"
    return StreamingResponse(BytesIO(build_progress_pdf(d)), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/court-codes/{case_id}/progress.pdf")
async def court_code_progress_pdf(case_id: str, user: UserPublic = Depends(get_current_user),
                                  db: AsyncIOMotorDatabase = Depends(get_db)) -> StreamingResponse:
    doc = await db.portal_court_keys.find_one({"case_id": case_id, "created_by": user.user_id}, {"_id": 0, "key_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Court code not found.")
    keys = [k for k in REQUESTABLE if k in (doc.get("requested") or [])]
    expired = doc.get("expires_at") and doc["expires_at"] < _now()
    return _pdf_response({
        "kind": "Court code", "ref": case_id, "label": doc.get("label") or "", "generated_at": _now(),
        "state": "Revoked" if doc.get("revoked_at") else "Expired" if expired else "Active",
        "parents": await linked_parents(db, case_id, keys),
    })


@router.get("/joint-alignment/cases/{case_id}/progress.pdf")
async def joint_case_progress_pdf(case_id: str, user: UserPublic = Depends(get_current_user),
                                  db: AsyncIOMotorDatabase = Depends(get_db)) -> StreamingResponse:
    case = await db.joint_alignment_cases.find_one({"case_id": case_id, "professional_created_by": user.user_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    keys = case_requested_keys(case)
    parents: List[Dict[str, Any]] = [
        {"name": p.get("name") or f"Parent {i + 1}",
         "assessments": await progress_rows(db, p["user_id"], keys) if p.get("user_id") else None}
        for i, p in enumerate(case.get("parents") or [])
    ]
    return _pdf_response({
        "kind": "Joint case", "ref": case_id, "label": case.get("align_case_reference") or "", "generated_at": _now(),
        "state": (case.get("status") or "").replace("_", " ").capitalize(), "parents": parents,
    })

