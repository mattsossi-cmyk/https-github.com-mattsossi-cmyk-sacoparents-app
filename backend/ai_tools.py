"""Review-gated AI helpers: Jev checks (neutrality, blame, child-focus tags), Claude Parallel Parenting summary, parent attachments."""
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

import jev
from legal_ai import AI_LABEL
from storage import ALLOWED, APP_NAME, MAX_UPLOAD, get_object, put_object

logger = logging.getLogger("ai_tools")
NEUTRALITY_FIELDS = ("professional_summary", "court_summary_text", "joint_notes", "shared_concerns", "pathway_rationale", "safety_takeaway", "short_term_goals", "long_term_goals", "success_indicators")
PARALLEL_SYSTEM = ("You draft a neutral Parallel Parenting summary for a family-court professional from structured agreement data. Rules: no custody recommendation, no diagnosis, no credibility "
                   "judgment, no legal conclusion; describe structure (written app-only communication, neutral-site exchanges, no direct negotiation, dispute ladder, review interval) and the "
                   "areas of alignment / open items as parent-reported. 4-6 sentences, court-appropriate. Begin with 'AI-Assisted Draft — Professional Review Required.' Return plain text only.")


class FieldsIn(BaseModel):
    fields: dict = {}


class LinesIn(BaseModel):
    lines: list[str] = []


def _pro(user):
    if user.get("role") not in ("professional", "admin") or (user.get("role") == "professional" and not user.get("approved")):
        raise HTTPException(status_code=403, detail="Approved professional access required.")


async def _claude(system: str, payload: dict, session: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=session, system_message=system).with_model("anthropic", "claude-sonnet-4-6")
    return (await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False)))).strip()


def _joint_text(doc: dict) -> str:
    out = []
    for side in ("a", "b"):
        for k, v in (((doc.get("responses") or {}).get(side) or {}).get("answers") or {}).items():
            out.append(f"{k}: {v}")
    return "\n".join(out)


def build_router(db, get_current_user, own_case, get_joint_report_doc, report_role) -> APIRouter:
    r = APIRouter()
    _jev_routes(r, db, get_current_user, own_case)
    _attachment_routes(r, db, get_current_user, get_joint_report_doc, report_role)
    return r


def _jev_routes(r: APIRouter, db, get_current_user, own_case) -> None:
    """Review-gated Jev / Claude helpers for the Professional Alignment Report and parent Foundation Statement."""

    @r.post("/cases/{rid}/professional-report/neutrality-check")
    async def neutrality(rid: str, body: FieldsIn, user=Depends(get_current_user)):
        await own_case(rid, user)
        flags = await jev.neutrality_check({k: v for k, v in body.fields.items() if k in NEUTRALITY_FIELDS and isinstance(v, str)})
        return {"flags": flags, "checked_fields": [k for k in body.fields if k in NEUTRALITY_FIELDS], "note": "Advisory only — Jev flags sentences for your review; nothing is edited or blocked."}

    @r.post("/cases/{rid}/professional-report/child-focus-suggest")
    async def child_focus(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        text = _joint_text(doc)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No Joint Report text available yet")
        return {"suggestions": await jev.child_focus_tags(text), "note": "Suggested from Joint Report text. Accept or reject each category."}

    @r.post("/cases/{rid}/parallel-summary-draft")
    async def parallel_summary(rid: str, user=Depends(get_current_user)):
        doc = await own_case(rid, user)
        from agreement_model import court_agreement_card
        from safety_gate import PARALLEL, _emails, apply_parallel, safety_status
        safety = await safety_status(db, _emails(doc), doc.get("created_by"))
        card = apply_parallel(court_agreement_card(doc, safety), safety) if doc.get("kind") == "agreement" else {}
        structure = {k: card.get(k) or PARALLEL.get(k) for k in ("communication", "transitions", "conflict_steps", "options", "needs_aligned", "needs_open")}
        payload = {"case_code": doc.get("case_code"), "child_initial": (doc.get("child_name") or "")[:1], "safety_flagged": safety.get("flagged"), "reasons": safety.get("reasons"), "structure": structure}
        try:
            text = await _claude(PARALLEL_SYSTEM, payload, f"parallel-summary-{rid}")
            text = text if text.lower().startswith("ai-assisted draft") else f"{AI_LABEL}. {text}"
            model = "Claude Sonnet 4.6"
        except Exception as exc:
            logger.warning("claude parallel summary unavailable: %s", exc)
            text = (f"{AI_LABEL}. Safety indicators were identified for these parents; a Parallel Parenting structure applies: written app-only communication limited to child logistics, neutral-site or "
                    "third-party exchanges with staggered arrival, no direct negotiation, disputes escalated through a parenting coordinator, attorney-assisted process and court motion, with reassessment in 90–180 days.")
            model = "rule-based fallback"
        return {"text": text, "model": model, "safety": safety, "label": "AI-Assisted Draft — Professional Review Required"}

    @r.post("/foundation/mine/blame-check")
    async def blame(body: LinesIn, user=Depends(get_current_user)):
        return {"results": await jev.blame_check(body.lines[:12]), "note": "Nudge only — you decide the final wording."}


def _pub(f: dict) -> dict:
    return {k: f.get(k) for k in ("id", "original_filename", "content_type", "size", "created_at")}


def _attachment_routes(r: APIRouter, db, get_current_user, get_joint_report_doc, report_role) -> None:
    """Parent attachments — private to the owner and the assigned professional on a case the statement was shared into."""

    @r.post("/foundation/mine/attachments")
    async def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
        ct = (file.content_type or "").split(";")[0]
        if ct not in ALLOWED:
            raise HTTPException(status_code=400, detail="Only PDF, JPG, PNG or WebP files are accepted")
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="File too large (10 MB max)")
        if await db.files.count_documents({"user_id": user["_id"], "is_deleted": False}) >= 10:
            raise HTTPException(status_code=400, detail="You can attach up to 10 documents")
        fid = str(uuid.uuid4())
        try:
            res = put_object(f"{APP_NAME}/uploads/{user['_id']}/{fid}.{ALLOWED[ct]}", data, ct)
        except Exception as exc:
            logger.warning("upload failed: %s", exc)
            raise HTTPException(status_code=502, detail="File storage is unavailable right now")
        rec = {"id": fid, "user_id": user["_id"], "storage_path": res["path"], "original_filename": (file.filename or "document")[:200], "content_type": ct, "size": res.get("size", len(data)),
               "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()}
        await db.files.insert_one(dict(rec))
        return _pub(rec)

    @r.get("/foundation/mine/attachments")
    async def mine(user=Depends(get_current_user)):
        return {"files": [_pub(f) async for f in db.files.find({"user_id": user["_id"], "is_deleted": False}, {"_id": 0}).sort("created_at", 1)]}

    @r.delete("/foundation/mine/attachments/{fid}")
    async def remove(fid: str, user=Depends(get_current_user)):
        res = await db.files.update_one({"id": fid, "user_id": user["_id"]}, {"$set": {"is_deleted": True}})
        if not res.matched_count:
            raise HTTPException(status_code=404, detail="File not found")
        return {"ok": True}

    async def _case_parent_ids(doc: dict) -> dict:
        emails = {s: ((doc.get("participants") or {}).get(s) or {}).get("email", "").lower() for s in ("a", "b")}
        out = {}
        for s, e in emails.items():
            if e and (doc.get("responses") or {}).get(s, {}).get("foundation"):
                u = await db.users.find_one({"email": e}, {"_id": 1})
                if u:
                    out[s] = u["_id"]
        return out

    @r.get("/joint/reports/{rid}/attachments")
    async def case_files(rid: str, user=Depends(get_current_user)):
        doc = await get_joint_report_doc(rid, user)
        if report_role(doc, user["_id"]) or user.get("role") not in ("professional", "admin"):
            raise HTTPException(status_code=403, detail="Professional access only")
        ids = await _case_parent_ids(doc)
        files = [{**_pub(f), "side": s} for s, uid in ids.items() async for f in db.files.find({"user_id": uid, "is_deleted": False}, {"_id": 0})]
        return {"files": files}

    @r.get("/files/{fid}")
    async def download(fid: str, case: str = "", user=Depends(get_current_user)):
        rec = await db.files.find_one({"id": fid, "is_deleted": False}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="File not found")
        if rec["user_id"] != user["_id"]:
            if not case:
                raise HTTPException(status_code=403, detail="Not allowed")
            doc = await get_joint_report_doc(case, user)
            if report_role(doc, user["_id"]) or rec["user_id"] not in (await _case_parent_ids(doc)).values():
                raise HTTPException(status_code=403, detail="Not allowed")
        data, ct = get_object(rec["storage_path"])
        return Response(content=data, media_type=rec.get("content_type") or ct, headers={"Content-Disposition": f'inline; filename="{rec["original_filename"]}"'})

