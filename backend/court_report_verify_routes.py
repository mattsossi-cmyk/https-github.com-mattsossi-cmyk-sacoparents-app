"""Reviewer Co-Sign Portal for the Trauma-Informed Safety and Functioning
Lens Court Report.

Workflow:

  1. The parent taps "Get co-sign QR" on the results card. Frontend
     hits `POST /api/safety-assessment/{assessment_id}/prepare-cosign`
     which:
       * writes a `court_report_signatures` row keyed by `sig_id`
       * stamps a QR into a freshly-generated court report PDF that
         resolves to  <preview>/verify/court-report/{sig_id}
       * returns { sig_id, verify_url, qr_png_data_url }

  2. The mediator / DV practitioner scans the QR (or clicks the link)
     and lands on the public verify page. They:
       * see the report headlines (never raw behavioural language)
       * see who issued it + when
       * add printed name, role, and optional notes
       * submit the co-signature via `POST /api/verify/court-report/{sig_id}/cosign`

  3. Anyone with the sig_id (parent or reviewer) can re-download the
     co-signed court report from `GET /api/verify/court-report/{sig_id}/pdf`.
     The reviewer's printed name, role, notes, and signed-at timestamp
     are baked into the signature block. No re-generation required.

Privacy: the public verify endpoint intentionally mirrors the
pathway-verify stance — minimal metadata + headlines, never raw
behavioural language. sig_id is unguessable (16 hex chars, uuid4).
"""
from __future__ import annotations

import base64
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field


router = APIRouter(prefix="/verify/court-report", tags=["court-report-verify"])

SIGNATURES_COLLECTION = "court_report_signatures"


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _public_base_url() -> str:
    return (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")


def build_verify_url(sig_id: str) -> str:
    base = _public_base_url()
    return f"{base}/verify/court-report/{sig_id}" if base else f"/verify/court-report/{sig_id}"


def _qr_data_url(text: str) -> str:
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _valid_sig_id(sig_id: str) -> bool:
    return (
        bool(sig_id)
        and 0 < len(sig_id) <= 32
        and all(c in "0123456789abcdefABCDEF" for c in sig_id)
    )


async def create_court_report_signature(
    db: AsyncIOMotorDatabase,
    *,
    assessment_id: str,
    user_id: str,
    parent_name: str,
) -> Dict[str, str]:
    sig_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc)
    doc = {
        "sig_id":        sig_id,
        "assessment_id": assessment_id,
        "user_id":       user_id,
        "parent_name":   parent_name,
        "created_at":    now.isoformat(),
        "issued_on":     now.strftime("%Y-%m-%d"),
        # Co-sign fields — filled in later by the reviewer.
        "cosigner_name":  None,
        "cosigner_role":  None,
        "cosigner_notes": None,
        "cosigned_at":    None,
    }
    await db[SIGNATURES_COLLECTION].insert_one(doc)
    verify_url = build_verify_url(sig_id)
    return {
        "sig_id":          sig_id,
        "verify_url":      verify_url,
        "qr_png_data_url": _qr_data_url(verify_url),
    }


async def load_signature(
    db: AsyncIOMotorDatabase, sig_id: str
) -> Optional[Dict[str, Any]]:
    if not _valid_sig_id(sig_id):
        return None
    return await db[SIGNATURES_COLLECTION].find_one(
        {"sig_id": sig_id.lower()}, {"_id": 0}
    )


# ---------------------------------------------------------------------------
# Public: verify + co-sign
# ---------------------------------------------------------------------------

class CoSignBody(BaseModel):
    reviewer_name: str = Field(..., min_length=2, max_length=120)
    reviewer_role: str = Field(..., min_length=2, max_length=120)
    reviewer_notes: str = Field(default="", max_length=2000)


@router.get("/{sig_id}")
async def verify_court_report(
    sig_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Public verify endpoint. Returns only the metadata a mediator
    needs to decide whether to co-sign. Never leaks raw behavioural
    language from Section 1."""
    row = await load_signature(db, sig_id)
    if not row:
        return {"issued": False, "sig_id": sig_id}
    # Fetch findings headlines for the reviewer preview.
    doc = await db.safety_assessments.find_one(
        {"assessment_id": row["assessment_id"]},
        {"_id": 0, "result.lens.findings": 1},
    )
    findings_headlines: Dict[str, str] = {}
    if doc:
        findings = ((doc.get("result") or {}).get("lens") or {}).get("findings") or {}
        for k, block in findings.items():
            if isinstance(block, dict) and block.get("headline"):
                findings_headlines[k] = block["headline"]
    return {
        "issued":       True,
        "sig_id":       sig_id,
        "issued_on":    row.get("issued_on"),
        "parent_name":  row.get("parent_name") or "",
        "cosigned":     bool(row.get("cosigned_at")),
        "cosigner": {
            "name":       row.get("cosigner_name") or "",
            "role":       row.get("cosigner_role") or "",
            "notes":      row.get("cosigner_notes") or "",
            "cosigned_at": row.get("cosigned_at") or "",
        } if row.get("cosigned_at") else None,
        "findings_headlines": findings_headlines,
    }


@router.post("/{sig_id}/cosign")
async def cosign_court_report(
    sig_id: str,
    body: CoSignBody,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Reviewer submits their co-signature. One co-signature per sig_id
    — a reviewer who wants to update their notes must contact the
    parent to reissue. This keeps the audit trail clean and prevents
    an anonymous scanner from overwriting a legitimate co-signature."""
    row = await load_signature(db, sig_id)
    if not row:
        raise HTTPException(status_code=404, detail="Signature not found")
    if row.get("cosigned_at"):
        raise HTTPException(
            status_code=409,
            detail="This report has already been co-signed. Ask the parent to reissue a fresh QR if updates are needed.",
        )
    now = datetime.now(timezone.utc).isoformat()
    await db[SIGNATURES_COLLECTION].update_one(
        {"sig_id": sig_id.lower()},
        {"$set": {
            "cosigner_name":  body.reviewer_name.strip(),
            "cosigner_role":  body.reviewer_role.strip(),
            "cosigner_notes": (body.reviewer_notes or "").strip(),
            "cosigned_at":    now,
        }},
    )
    return {"ok": True, "cosigned_at": now}


@router.get("/{sig_id}/pdf")
async def download_cosigned_court_report(
    sig_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Anyone with the sig_id can re-download the court report. When a
    co-signature has been recorded, it is baked into the signature
    block. When it has not, the reviewer signature line is left blank
    exactly as on the original download."""
    from fastapi import Response
    from safety_court_report_pdf import build_court_report_pdf
    from trauma_lens import PROCEDURAL_SAFEGUARDS, build_findings

    row = await load_signature(db, sig_id)
    if not row:
        raise HTTPException(status_code=404, detail="Signature not found")
    assessment = await db.safety_assessments.find_one(
        {"assessment_id": row["assessment_id"]}, {"_id": 0},
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Underlying assessment not found")
    result = assessment.get("result") or {}
    if not result.get("lens"):
        try:
            result = dict(result)
            result["lens"] = build_findings(result)
        except Exception:  # noqa: BLE001
            pass
    reviewer_display = ""
    if row.get("cosigned_at"):
        parts = [row.get("cosigner_name") or "", row.get("cosigner_role") or ""]
        reviewer_display = " · ".join([p for p in parts if p])
    pdf_bytes = build_court_report_pdf(
        user_name=row.get("parent_name") or "",
        generated_at=assessment.get("created_at") or datetime.now(timezone.utc).isoformat(),
        assessment_id=row["assessment_id"],
        result=result,
        safeguards=PROCEDURAL_SAFEGUARDS,
        reviewer_name=reviewer_display,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="tisfl-court-report-{sig_id}.pdf"'
            ),
            "Cache-Control": "no-store",
        },
    )
