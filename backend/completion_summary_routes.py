"""Parent's "You've finished what your professional asked for" summary: download, or send it to the professional
through the secure link + one-time-code flow. Dates only, never answers."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

from auth import get_current_user, get_db
from court_checklist import REQUESTABLE, progress_rows
from models import UserPublic
from progress_pdf import build_progress_pdf

router = APIRouter(prefix="/court-path", tags=["completion-summary"])

FILENAME = "SA_CoParents_Completion_Summary.pdf"
SENDS_PER_DAY = 5


async def _summary(db: AsyncIOMotorDatabase, user: UserPublic) -> Dict[str, Any]:
    from court_checklist import _sync_professional_requests

    req = await _sync_professional_requests(db, user.user_id)
    keys = [k for k in REQUESTABLE if k in (req.get("keys") or [])]
    rows = await progress_rows(db, user.user_id, keys)
    if not rows or any(r["status"] != "done" for r in rows):
        raise HTTPException(status_code=409, detail="Your summary unlocks once everything your professional asked for is finished.")
    ps = await db.portal_state.find_one({"user_id": user.user_id}, {"_id": 0, "court_key": 1, "court_legal_name": 1}) or {}
    name = (ps.get("court_legal_name") or "").strip() or user.name or "Parent"
    bits = [f"Case {ps['court_key']}" if ps.get("court_key") else "", f"Professional: {req['pro_name']}" if req.get("pro_name") else ""]
    return {
        "title": "Completion Summary", "tagline": "SA CoParents  ·  Requested assessments finished",
        "heading": "You've finished what your professional asked for.", "ref": "", "label": "", "kind": "",
        "state": "  ·  ".join(b for b in bits if b), "generated_at": datetime.now(timezone.utc).isoformat(), "filename": FILENAME,
        "parents": [{"name": name, "assessments": rows}],
        "closing": "This summary confirms only that each requested assessment is finished, with the date. It does not include "
                   "any of your answers. You can share it with your professional if you'd like.",
    }


async def _recipients(db: AsyncIOMotorDatabase, uid: str) -> Tuple[List[Dict[str, str]], bool]:
    """Professionals we already know an email for (in-app codes + joint cases), and whether the parent may type one."""
    from completion_alerts import _sources

    known, seen = [], set()
    for s in await _sources(db, uid):
        pro = await db.users.find_one({"user_id": s["pro"]}, {"_id": 0, "email": 1, "name": 1}) or {}
        email = (pro.get("email") or s["fallback_email"] or "").strip().lower()
        if email and email not in seen:
            seen.add(email)
            known.append({"ref": s["ref"], "name": s["name"] or pro.get("name") or "Your professional", "email": email})
    ps = await db.portal_state.find_one({"user_id": uid}, {"_id": 0, "court_key": 1}) or {}
    ck = (ps.get("court_key") or "").strip()
    align_code = bool(ck) and bool(await db.portal_court_keys.find_one({"case_id": ck, "created_by": {"$exists": False}}, {"_id": 1}))
    return known, align_code or not known


@router.get("/completion-summary.pdf")
async def completion_summary_pdf(user: UserPublic = Depends(get_current_user),
                                 db: AsyncIOMotorDatabase = Depends(get_db)) -> StreamingResponse:
    pdf = build_progress_pdf(await _summary(db, user))
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{FILENAME}"'})


@router.get("/completion-summary/recipients")
async def summary_recipients(user: UserPublic = Depends(get_current_user),
                             db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    known, typed = await _recipients(db, user.user_id)
    return {"professionals": [{"ref": k["ref"], "name": k["name"]} for k in known], "can_type_email": typed}


class SendBody(BaseModel):
    ref: Optional[str] = None
    email: Optional[EmailStr] = None


@router.post("/completion-summary/send")
async def send_summary(body: SendBody, user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    from email_service import EmailNotConfigured, EmailSendError, send_completion_summary

    known, typed = await _recipients(db, user.user_id)
    if body.ref:
        match = next((k for k in known if k["ref"] == body.ref), None)
        if not match:
            raise HTTPException(status_code=404, detail="We couldn't find that professional.")
        to_email, to_name = match["email"], match["name"]
    elif body.email and typed:
        to_email, to_name = str(body.email).lower(), str(body.email)
    else:
        raise HTTPException(status_code=422, detail="Choose your professional to send it to.")
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    if await db.completion_summary_sends.count_documents({"user_id": user.user_id, "sent_at": {"$gte": since}}) >= SENDS_PER_DAY:
        raise HTTPException(status_code=429, detail="You've sent your summary several times today. Please try again tomorrow.")
    pdf = build_progress_pdf(await _summary(db, user))
    try:
        await asyncio.to_thread(send_completion_summary, to_email=to_email, pdf_bytes=pdf)
    except EmailNotConfigured:
        raise HTTPException(status_code=503, detail="Email isn't set up right now. Please download the summary instead.")
    except EmailSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    await db.completion_summary_sends.insert_one({"user_id": user.user_id, "ref": body.ref or "", "typed": not body.ref,
                                                  "sent_at": datetime.now(timezone.utc).isoformat()})
    return {"ok": True, "sent_to": to_name}
