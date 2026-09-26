"""Gemini-drafted Joint Report narrative (professional review-gated; rule-based engine is the fallback and the default)."""
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from joint_engine import generate_joint_report

logger = logging.getLogger("joint_ai")

MODEL = ("gemini", "gemini-3.1-pro-preview", "Gemini 3.1 Pro")
LIST_KEYS = ("alignment_statements", "child_needs", "conversation", "questions", "next_steps")
AI_KEYS = LIST_KEYS + ("differences", "alignment_paragraph")

SYSTEM = """You are drafting the SA CoParents Align Joint Parenting Alignment Report from two parents' private assessment answers, for an authorized professional who will review, edit and approve it before either parent or any court sees it.
You are an organizational and drafting tool, NOT the decision-maker.
RULES:
1. Neutral, child-focused, court-appropriate language. Never declare either parent right, wrong, credible or uncooperative.
2. Describe differences as different perspectives ("Parent A describes...", "Parent B describes..."). Never convert a statement into a finding of fact.
3. No diagnoses, no legal conclusions, no custody or possession recommendations, no predictions about court outcomes.
4. Do not characterize a parent as abusive, alienating, narcissistic, unstable or dishonest.
5. Areas of agreement are listed separately from differences. Focus on the child's practical needs.
6. If safety-related content appears, do not suggest joint sessions or direct contact; keep to safety-aware, parallel options.
Return ONLY JSON with keys:
alignment_statements: 3-6 strings, each "Both parents ..." sentences describing shared ground.
differences: 0-6 objects {area, parent_a, parent_b, reframe} where parent_a/parent_b are 1-2 neutral sentences in the parent's own framing and reframe is one child-centred sentence starting "For {child}, ...".
child_needs: 4-8 short phrases naming the child's practical needs evidenced by both sets of answers.
alignment_paragraph: 2-3 sentences summarizing what the parents share around the child.
conversation: 3-5 short prompts a professional could use to open a constructive conversation.
questions: 3-5 neutral reflection questions for each parent.
next_steps: 3-5 concrete, neutral next steps."""


def _answers(doc: dict, side: str) -> dict:
    r = doc["responses"].get(side) or {}
    return r.get("answers") or {"imported_material": str(r.get("external") or "")[:6000]}


def _clean(data: dict, child: str) -> dict:
    out = {}
    for k in LIST_KEYS:
        v = data.get(k)
        if isinstance(v, list) and all(isinstance(x, str) for x in v) and v:
            out[k] = [x.strip()[:400] for x in v][:8]
    d = data.get("differences")
    if isinstance(d, list):
        rows = [{"area": str(x.get("area", ""))[:80], "parent_a": str(x.get("parent_a", ""))[:600], "parent_b": str(x.get("parent_b", ""))[:600],
                 "reframe": str(x.get("reframe") or f"For {child}, both perspectives point to a need worth discussing.")[:400]} for x in d if isinstance(x, dict) and x.get("area")]
        out["differences"] = rows[:6]
    if isinstance(data.get("alignment_paragraph"), str) and data["alignment_paragraph"].strip():
        out["alignment_paragraph"] = data["alignment_paragraph"].strip()[:1200]
    return out


async def draft_joint_fields(doc: dict) -> dict:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="AI drafting is not configured")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    base = generate_joint_report(doc)
    payload = {"subject": base["subject_label"], "child": base["child_name"], "parent_a": base["parent_a_name"], "parent_b": base["parent_b_name"], "is_safety": base["is_safety"],
               "parent_a_answers": _answers(doc, "a"), "parent_b_answers": _answers(doc, "b"), "rule_based_alignment_map": base["alignment_map"], "subject_child_needs_reference": base["child_needs"]}
    chat = LlmChat(api_key=key, session_id=f"joint-ai-{doc['id']}-{uuid.uuid4().hex[:6]}", system_message=SYSTEM).with_model(MODEL[0], MODEL[1])
    text = (await chat.send_message(UserMessage(text=json.dumps(payload)))).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    fields = _clean(json.loads(text), base["child_name"])
    if not fields.get("alignment_statements"):
        raise HTTPException(status_code=502, detail="The AI draft was incomplete; please try again")
    return fields


def effective_joint_report(doc: dict) -> dict:
    """Rule-based report, overlaid with the professional-approved AI draft when one exists."""
    rep = generate_joint_report(doc)
    draft = doc.get("ai_joint_draft") or {}
    if draft.get("status") == "approved":
        rep.update({k: v for k, v in (draft.get("fields") or {}).items() if k in AI_KEYS})
        rep["ai_assisted"] = True
        rep["ai_model"] = draft.get("model", MODEL[2])
        rep["ai_reviewed_by"] = draft.get("reviewed_by_name", "")
    return rep


class DraftEdit(BaseModel):
    fields: dict


def build_router(db, get_current_user, get_joint_report_doc) -> APIRouter:
    r = APIRouter()

    async def _own_ready_case(rid: str, user: dict) -> dict:
        doc = await get_joint_report_doc(rid, user)
        if doc.get("created_by") != user["_id"]:
            raise HTTPException(status_code=403, detail="Only the case professional can manage the AI draft")
        if doc.get("kind") in ("agreement", "foundation") or not (doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b")):
            raise HTTPException(status_code=400, detail="The AI draft is available once both parents have completed their assessments")
        return doc

    def _public(doc: dict) -> dict:
        d = doc.get("ai_joint_draft") or {}
        return {"status": d.get("status", "none"), "fields": d.get("fields", {}), "model": d.get("model", MODEL[2]), "created_at": d.get("created_at"), "reviewed_at": d.get("reviewed_at"),
                "rule_based": {k: v for k, v in generate_joint_report(doc).items() if k in AI_KEYS}, "label": "AI-ASSISTED DRAFT — PROFESSIONAL REVIEW REQUIRED"}

    @r.get("/joint/reports/{rid}/ai-joint-draft")
    async def get_draft(rid: str, user=Depends(get_current_user)):
        return _public(await _own_ready_case(rid, user))

    @r.post("/joint/reports/{rid}/ai-joint-draft")
    async def create_draft(rid: str, user=Depends(get_current_user)):
        doc = await _own_ready_case(rid, user)
        try:
            fields = await draft_joint_fields(doc)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("joint AI draft failed: %s", exc)
            raise HTTPException(status_code=502, detail="AI drafting is temporarily unavailable; the rule-based Joint Report remains in effect")
        draft = {"status": "draft", "fields": fields, "model": MODEL[2], "created_at": datetime.now(timezone.utc).isoformat()}
        await db.joint_reports.update_one({"id": rid}, {"$set": {"ai_joint_draft": draft}})
        return _public({**doc, "ai_joint_draft": draft})

    @r.put("/joint/reports/{rid}/ai-joint-draft")
    async def edit_draft(rid: str, body: DraftEdit, user=Depends(get_current_user)):
        doc = await _own_ready_case(rid, user)
        d = doc.get("ai_joint_draft") or {}
        if d.get("status") not in ("draft", "approved"):
            raise HTTPException(status_code=400, detail="No AI draft to edit")
        fields = {**d["fields"], **_clean(body.fields, doc.get("child_name") or "the child")}
        await db.joint_reports.update_one({"id": rid}, {"$set": {"ai_joint_draft.fields": fields, "ai_joint_draft.status": "draft"}})
        return _public({**doc, "ai_joint_draft": {**d, "fields": fields, "status": "draft"}})

    @r.post("/joint/reports/{rid}/ai-joint-draft/approve")
    async def approve_draft(rid: str, user=Depends(get_current_user)):
        doc = await _own_ready_case(rid, user)
        d = doc.get("ai_joint_draft") or {}
        if d.get("status") not in ("draft", "approved"):
            raise HTTPException(status_code=400, detail="Generate an AI draft first")
        upd = {"ai_joint_draft.status": "approved", "ai_joint_draft.reviewed_at": datetime.now(timezone.utc).isoformat(), "ai_joint_draft.reviewed_by": user["_id"], "ai_joint_draft.reviewed_by_name": user.get("name", "")}
        await db.joint_reports.update_one({"id": rid}, {"$set": upd})
        return _public({**doc, "ai_joint_draft": {**d, "status": "approved"}})

    @r.post("/joint/reports/{rid}/ai-joint-draft/discard")
    async def discard_draft(rid: str, user=Depends(get_current_user)):
        await _own_ready_case(rid, user)
        await db.joint_reports.update_one({"id": rid}, {"$unset": {"ai_joint_draft": ""}})
        return {"status": "none"}

    return r
