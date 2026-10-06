"""Align Assistant — advisory, session-scoped decision-support chat (Gemini 3 Flash). Never files, decides or recommends custody."""
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import db
from joint_engine import generate_joint_report
from joint_helpers import case_status
from lens_data import PATHWAYS, recommended_pathway

MODEL = ("gemini", "gemini-3-flash-preview")
HISTORY_LIMIT = 24
SYSTEM = (
    "You are Align Assistant, a decision-support aide for family-law professionals using SA CoParents Align. Three competencies: (1) Case intake & routing — say which parent has "
    "completed their assessment and what is blocking the next step; (2) Alignment & delta analysis — describe the two parents' assessments in three buckets: Agreed, Minor Gap, High "
    "Discrepancy, using ONLY the CASE BRIEF provided; (3) Drafting & pathway options — suggest structured next steps from the pathway library and offer to draft neutral memo text that "
    "the professional pastes into the Professional Report editor. Hard rules: you are advisory only; the professional reviews and decides everything. Never recommend custody or "
    "possession outcomes, never diagnose, never judge credibility, never say which parent is right, never state legal conclusions. Describe differences as differences in perspective. "
    "Use 'may consider' / 'one option is', never 'should be ordered'. Safety or family-violence indicators route to safety / parallel-parenting safeguards, not ordinary conflict "
    "pathways. Parent invitations are sent by email only (no SMS) via the Invite Parents flow; do not offer SMS. Nothing you write is filed with a court — the professional exports and "
    "files. Keep answers concise (under 180 words unless drafting), plain text, no markdown headers. If the brief lacks data, say what is missing instead of guessing. "
    "DRAFTING FORMAT: when the professional asks you to draft text for the Professional Report, wrap ONLY the draft body in markers on their own lines: "
    "[[DRAFT section=<key>]] on the line before and [[/DRAFT]] on the line after, where <key> is exactly one of: " + ", ".join(
        f"{k} ({v})" for k, v in {"professional_summary": "Professional statement", "court_summary_text": "Concise court summary", "alignment_summary": "Alignment summary",
                                  "joint_notes": "Joint dynamic summary", "shared_concerns": "Shared concerns", "pathway_rationale": "Pathway rationale", "short_term_goals": "30–90 day goals",
                                  "long_term_goals": "6–12 month goals", "safety_takeaway": "Safety takeaway", "issues_requiring_attention": "Issues requiring attention",
                                  "agreement_building_opportunities": "Agreement-building opportunities"}.items()) + ". One draft per marker block; the professional reviews before anything is saved."
)
DRAFT_SECTIONS = {"professional_summary": "Professional statement (§10)", "court_summary_text": "Concise court summary (§11)", "alignment_summary": "Alignment summary (§5)",
                  "joint_notes": "Joint dynamic summary (§5)", "shared_concerns": "Shared concerns (§5)", "pathway_rationale": "Pathway rationale (§8)", "short_term_goals": "30–90 day goals (§10)",
                  "long_term_goals": "6–12 month goals (§10)", "safety_takeaway": "Safety takeaway (§2)", "issues_requiring_attention": "Issues requiring attention (§9)",
                  "agreement_building_opportunities": "Agreement-building opportunities (§9)"}
TRIGGERS = {
    "invite": "I'm about to invite the parents. Walk me through what the standard intake email says and what I should check first for this case (e.g. any safety indicators).",
    "review": "Give me the alignment delta for this case: what is Agreed, Minor Gap and High Discrepancy, and should I generate a discrepancy summary?",
    "pathway": "Based on the assessment delta, which conflict-resolution pathways from the library fit this case, and can you outline a 3-stage agenda that starts with agreed items?",
    "report": "I'm ready to compile the Professional Report. What do I still need to fill in, and would a concise court summary or a detailed mediation workplan fit better here?",
}


class ChatIn(BaseModel):
    session_id: str
    message: str
    case_id: str | None = None


class DraftInsertIn(BaseModel):
    case_id: str
    field: str
    text: str


class DraftAcceptIn(BaseModel):
    case_id: str
    field: str


def _pro(user):
    if user.get("role") not in ("professional", "admin") or (user.get("role") == "professional" and not user.get("approved")):
        raise HTTPException(status_code=403, detail="Approved professional access required.")


def _bucket(status: str) -> str:
    s = (status or "").lower()
    return "Agreed" if "strong" in s else "Minor Gap" if "moderate" in s else "High Discrepancy"


def _participants(doc: dict) -> dict:
    return {r: {"name": (doc["participants"].get(r) or {}).get("name") or f"Parent {r.upper()}", "completed": bool((doc.get("responses") or {}).get(r)),
                "accepted": bool((doc["participants"].get(r) or {}).get("user_id"))} for r in ("a", "b")}


def _alignment_buckets(doc: dict, both: bool) -> dict:
    buckets = {"Agreed": [], "Minor Gap": [], "High Discrepancy": []}
    if both and doc.get("kind", "joint_report") == "joint_report":
        for row in generate_joint_report(doc).get("alignment_map") or []:
            buckets[_bucket(row.get("status"))].append(row.get("area"))
    return buckets


def _state(done: bool, active: bool) -> str:
    return "done" if done else "active" if active else "todo"


def _tick(ok: bool) -> str:
    return "✓" if ok else "⏳"


def _pathway_names(keys: list) -> str:
    return ", ".join(next((p["name"] for p in PATHWAYS if p["key"] == k), k) for k in keys)


def _steps(doc: dict, rep: dict, parts: dict, both: bool) -> list[dict]:
    generated = bool(doc.get("report_generated_at"))
    any_started = any(parts[r]["completed"] or parts[r]["accepted"] for r in ("a", "b"))
    pathways = rep.get("conflict_pathways") or []
    rec = recommended_pathway(rep.get("joint_rating"))
    ticked = [k for k, v in (rep.get("child_focus") or {}).items() if isinstance(v, dict) and v.get("checked")]
    resources = rep.get("resource_rows") or []
    status = rep.get("status")
    pathway_detail = _pathway_names(pathways) if pathways else f"Library suggests {rec['name']}" if rec else "Rate joint alignment first"
    return [
        {"key": "individual", "label": "Individual Assessments", "state": _state(both, any_started), "detail": f"Parent A: {_tick(parts['a']['completed'])} · Parent B: {_tick(parts['b']['completed'])}"},
        {"key": "joint", "label": "Joint Assessment", "state": _state(generated, both), "detail": "Report generated" if generated else "Ready for synthesis" if both else "Waiting on assessments"},
        {"key": "resources", "label": "Options & Resources", "state": _state(bool(resources or ticked), generated), "detail": f"{len(resources)} resources · {len(ticked)} child-focused issues" if rep else "Not started"},
        {"key": "pathway", "label": "Conflict-Resolution Pathway", "state": _state(bool(pathways), bool(rep.get("joint_rating"))), "detail": pathway_detail},
        {"key": "report", "label": "Professional Report", "state": _state(status in ("final", "submitted_to_court"), bool(rep)), "detail": (status or "not started").replace("_", " ").title()},
    ]


async def case_brief(doc: dict) -> dict:
    """Deterministic, neutral snapshot of one case for the stepper and the assistant. No raw parent answers."""
    rep = await db.professional_reports.find_one({"case_id": doc["id"]}, {"_id": 0, "status": 1, "joint_rating": 1, "conflict_pathways": 1, "resource_rows": 1, "child_focus": 1}) or {}
    parts = _participants(doc)
    both = parts["a"]["completed"] and parts["b"]["completed"]
    buckets = _alignment_buckets(doc, both)
    total = sum(len(v) for v in buckets.values())
    rec = recommended_pathway(rep.get("joint_rating"))
    return {"case_id": doc["id"], "case_code": doc.get("case_code"), "subject_label": doc.get("subject_label"), "child_name": doc.get("child_name"), "case_status": case_status(doc), "is_safety": bool(doc.get("is_safety")),
            "safety_route": any((doc.get("responses", {}).get(s) or {}).get("safety_route") or (doc.get("safety_flags") or {}).get(s) for s in ("a", "b")), "participants": parts, "buckets": buckets,
            "agreed_pct": round(len(buckets["Agreed"]) / total * 100) if total else None, "joint_rating": rep.get("joint_rating"), "pathways": rep.get("conflict_pathways") or [],
            "suggested_pathway": rec["name"] if rec else None, "report_status": rep.get("status") or "not_started", "steps": _steps(doc, rep, parts, both)}


async def _own_case(cid: str, user: dict) -> dict:
    q = {"id": cid} if user.get("role") == "admin" else {"id": cid, "$or": [{"created_by": user["_id"]}, {"professional_id": user["_id"]}]}
    doc = await db.joint_reports.find_one(q, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Case not found")
    return doc


def build_router(get_current_user) -> APIRouter:
    r = APIRouter(prefix="/assistant")

    @r.get("/case-brief/{cid}")
    async def brief(cid: str, user=Depends(get_current_user)):
        _pro(user)
        return await case_brief(await _own_case(cid, user))

    @r.get("/triggers")
    async def triggers(user=Depends(get_current_user)):
        _pro(user)
        return TRIGGERS

    @r.get("/draft-sections")
    async def draft_sections(user=Depends(get_current_user)):
        _pro(user)
        return DRAFT_SECTIONS

    @r.post("/insert-draft")
    async def insert_draft(body: DraftInsertIn, user=Depends(get_current_user)):
        """Drop an assistant draft into a Professional Report section as an AI draft awaiting professional review (never finalizes)."""
        from core import _log_lifecycle
        from legal_lens import LensStore
        _pro(user)
        if body.field not in DRAFT_SECTIONS:
            raise HTTPException(status_code=400, detail="That section cannot be drafted by the assistant")
        text = body.text.strip()[:6000]
        if not text:
            raise HTTPException(status_code=400, detail="Draft is empty")
        store = LensStore(db, _log_lifecycle)
        doc = await store.own_case(body.case_id, user)
        rep = await store.get_or_create(doc, user)
        now = datetime.now(timezone.utc).isoformat()
        drafts = {**(rep.get("ai_drafts") or {}), body.field: {"text": text, "model": f"Align Assistant ({MODEL[1]})", "at": now}}
        await db.professional_reports.update_one({"case_id": body.case_id}, {"$set": {body.field: text, "ai_drafts": drafts, "updated_at": now}})
        await _log_lifecycle(body.case_id, f"LEGAL_LENS_AI_DRAFT (Align Assistant, {DRAFT_SECTIONS[body.field]})", user)
        return {"ok": True, "field": body.field, "label": DRAFT_SECTIONS[body.field], "editor_url": f"/cases/{body.case_id}/professional-report#{body.field}"}

    @r.post("/accept-draft")
    async def accept_draft(body: DraftAcceptIn, user=Depends(get_current_user)):
        """Professional explicitly accepts an AI draft as their own text; the disclosure appendix still records the AI origin."""
        from core import _log_lifecycle
        from legal_lens import LensStore
        _pro(user)
        store = LensStore(db, _log_lifecycle)
        doc = await store.own_case(body.case_id, user)
        rep = await store.get_or_create(doc, user)
        drafts = rep.get("ai_drafts") or {}
        if body.field not in drafts:
            raise HTTPException(status_code=404, detail="No AI draft for that section")
        drafts[body.field]["accepted_at"] = datetime.now(timezone.utc).isoformat()
        await db.professional_reports.update_one({"case_id": body.case_id}, {"$set": {"ai_drafts": drafts}})
        await _log_lifecycle(body.case_id, f"LEGAL_LENS_AI_DRAFT_ACCEPTED ({body.field})", user)
        return {"ok": True, "ai_drafts": drafts}

    @r.get("/history")
    async def history(session_id: str, user=Depends(get_current_user)):
        _pro(user)
        return await db.assistant_messages.find({"session_id": session_id, "user_id": user["_id"]}, {"_id": 0}).sort("at", 1).to_list(200)

    @r.post("/chat")
    async def chat(body: ChatIn, user=Depends(get_current_user)):
        _pro(user)
        from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage
        text = body.message.strip()[:4000]
        if not text:
            raise HTTPException(status_code=400, detail="Message is empty")
        brief_ctx = await case_brief(await _own_case(body.case_id, user)) if body.case_id else None
        prior = await db.assistant_messages.find({"session_id": body.session_id, "user_id": user["_id"]}, {"_id": 0, "role": 1, "content": 1}).sort("at", -1).to_list(HISTORY_LIMIT)
        transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in reversed(prior))
        system = SYSTEM + ("\n\nCASE BRIEF (neutral, system-generated):\n" + json.dumps(brief_ctx, ensure_ascii=False) if brief_ctx else "\n\nNo case selected — ask the professional to pick a case for case-specific analysis.")
        if transcript:
            system += "\n\nCONVERSATION SO FAR:\n" + transcript
        now = datetime.now(timezone.utc).isoformat()
        await db.assistant_messages.insert_one({"id": str(uuid.uuid4()), "session_id": body.session_id, "user_id": user["_id"], "case_id": body.case_id, "role": "user", "content": text, "at": now})
        llm = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=body.session_id, system_message=system).with_model(*MODEL)

        async def gen():
            out = []
            try:
                async for ev in llm.stream_message(UserMessage(text=text)):
                    if isinstance(ev, TextDelta):
                        out.append(ev.content)
                        yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                    elif isinstance(ev, StreamDone):
                        break
            except Exception as e:  # noqa: BLE001
                yield f"data: {json.dumps({'error': f'Assistant unavailable: {type(e).__name__}'})}\n\n"
            reply = "".join(out).strip()
            if reply:
                await db.assistant_messages.insert_one({"id": str(uuid.uuid4()), "session_id": body.session_id, "user_id": user["_id"], "case_id": body.case_id, "role": "assistant", "content": reply, "model": MODEL[1], "at": datetime.now(timezone.utc).isoformat()})
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return r
