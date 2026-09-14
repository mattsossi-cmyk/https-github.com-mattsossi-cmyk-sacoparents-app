"""Court ⇄ Professional case-specific communication with AI communication summary (gpt-5.4-mini, rule fallback)."""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Depends, HTTPException

from agreement_ai import _extract_json

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = (
    "You summarize a case-specific message thread between a court and the assigned professional on SA CoParents Align, for a judge who reopens the case weeks later. "
    "Write 2-4 neutral, procedural sentences: what was asked, when, what was answered, and what is currently outstanding. Use dates. "
    "Never characterize parents, credibility, fitness, or legal merits. Return ONLY JSON: {\"summary\": \"...\", \"outstanding\": \"...\" or null}."
)
SUMMARY_DISCLAIMER = "Communication summary generated from the court–professional thread only. It is procedural, contains no findings, and is not a judicial recommendation."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rule_summary(msgs: list[dict]) -> dict:
    if not msgs:
        return {"summary": "No court–professional communication yet.", "outstanding": None}
    last = msgs[-1]
    courts = [m for m in msgs if m["from_role"] == "court"]
    pros = [m for m in msgs if m["from_role"] == "professional"]
    parts = []
    if courts:
        parts.append(f"The Court sent {len(courts)} message{'s' if len(courts) != 1 else ''}; most recent on {courts[-1]['at'][:10]}.")
    if pros:
        parts.append(f"The professional replied {len(pros)} time{'s' if len(pros) != 1 else ''}; most recent on {pros[-1]['at'][:10]}.")
    outstanding = f"Awaiting a reply from the {'professional' if last['from_role'] == 'court' else 'Court'} to the {last['at'][:10]} message." if msgs else None
    return {"summary": " ".join(parts), "outstanding": outstanding}


async def summarize_thread(msgs: list[dict], ref: dict) -> dict:
    key = os.environ.get("EMERGENT_LLM_KEY")
    result = None
    if key and msgs:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(api_key=key, session_id=f"court-thread-{ref['id']}", system_message=SUMMARY_SYSTEM).with_model("openai", "gpt-5.4-mini")
            payload = {"cause_number": ref.get("cause_number"), "messages": [{"from": m["from_role"], "name": m["from_name"], "at": m["at"][:16], "text": m["text"]} for m in msgs[-30:]]}
            text = await chat.send_message(UserMessage(text=json.dumps(payload, ensure_ascii=False)))
            data = _extract_json(text or "")
            if data and data.get("summary"):
                result = {"summary": str(data["summary"])[:1500], "outstanding": (str(data.get("outstanding"))[:500] if data.get("outstanding") else None), "model": "gpt-5.4-mini"}
        except Exception as exc:
            logger.warning("court thread AI summary unavailable: %s", exc)
    if result is None:
        result = {**_rule_summary(msgs), "model": "rules"}
    return {**result, "message_count": len(msgs), "generated_at": _now(), "disclaimer": SUMMARY_DISCLAIMER}


def build_router(db, get_current_user, app_url, send_email, email_from_name, require_judge, require_pro) -> APIRouter:
    r = APIRouter()

    def public(m: dict) -> dict:
        return {k: m.get(k) for k in ("id", "from_role", "from_name", "text", "at")}

    async def thread(ref_id: str) -> list[dict]:
        return await db.court_messages.find({"referral_id": ref_id}, {"_id": 0}).sort("at", 1).to_list(500)

    async def notify(ref: dict, user: dict, role: str, text: str) -> None:
        if role == "court":
            pro = await db.users.find_one({"_id": ref["professional_id"]}, {"email": 1, "name": 1}) or {}
            to, to_role, link = pro.get("email"), "Professional", f"{app_url()}/dashboard#court-referrals"
        else:
            to, to_role, link = ref.get("judge_email"), "Court", f"{app_url()}/court/case/{ref['id']}"
        if not to:
            return
        try:
            await send_email(to=to, case_id=ref.get("case_id") or ref["id"], kind="court_message", to_role=to_role, subject=f"Court communication - Cause No. {ref.get('cause_number', '')}",
                             html=('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                                   f"<p>New message from {escape(user.get('name', ''))} ({'the Court' if role == 'court' else 'assigned professional'}) regarding Cause No. {escape(ref.get('cause_number', ''))}:</p>"
                                   f'<blockquote style="border-left:3px solid #5B2A86;margin:0;padding:8px 12px;color:#333">{escape(text)}</blockquote>'
                                   f'<p><a href="{link}" style="color:#5B2A86">Open the case</a></p>'
                                   f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>'))
        except Exception as exc:
            logger.warning("court message email failed: %s", exc)

    async def post(ref: dict, user: dict, role: str, text: str) -> dict:
        text = (text or "").strip()[:4000]
        if not text:
            raise HTTPException(status_code=400, detail="Message is empty")
        msg = {"id": str(uuid.uuid4()), "referral_id": ref["id"], "case_id": ref.get("case_id"), "from_role": role, "from_user": user["_id"], "from_name": user.get("name", ""), "text": text, "at": _now()}
        await db.court_messages.insert_one(msg)
        summary = await summarize_thread(await thread(ref["id"]), ref)
        await db.court_referrals.update_one({"id": ref["id"]}, {"$set": {"communication_summary": summary}})
        if ref.get("case_id"):
            who = "the Court" if role == "court" else "the professional"
            await db.access_events.insert_one({"report_id": ref["case_id"], "kind": "court", "action": f"Court communication: message from {who} ({user.get('name', '')})",
                                               "at": msg["at"], "by": user["_id"], "by_name": user.get("name", ""), "by_role": "Court" if role == "court" else "Professional"})
        await notify(ref, user, role, text)
        return {"message": public(msg), "summary": summary}

    async def load_ref(ref_id: str, query: dict) -> dict:
        ref = await db.court_referrals.find_one({"id": ref_id, **query}, {"_id": 0})
        if not ref:
            raise HTTPException(status_code=404, detail="Referral not found")
        return ref

    def thread_view(ref: dict, msgs: list) -> dict:
        return {"messages": [public(m) for m in msgs], "summary": ref.get("communication_summary")}

    _judge_routes(r, get_current_user, require_judge, load_ref, thread, thread_view, post)
    _pro_routes(r, get_current_user, require_pro, load_ref, thread, thread_view, post)
    return r


def _judge_routes(r: APIRouter, get_current_user, require_judge, load_ref, thread, thread_view, post) -> None:
    @r.get("/court-dashboard/cases/{ref_id}/messages")
    async def judge_thread(ref_id: str, user=Depends(get_current_user)):
        await require_judge(user)
        ref = await load_ref(ref_id, {"judge_id": user["_id"]})
        return thread_view(ref, await thread(ref_id))

    @r.post("/court-dashboard/cases/{ref_id}/messages")
    async def judge_post(ref_id: str, body: dict, user=Depends(get_current_user)):
        await require_judge(user)
        ref = await load_ref(ref_id, {"judge_id": user["_id"]})
        return await post(ref, user, "court", body.get("text", ""))



def _pro_routes(r: APIRouter, get_current_user, require_pro, load_ref, thread, thread_view, post) -> None:
    @r.get("/professional/court-referrals/{ref_id}/messages")
    async def pro_thread(ref_id: str, user=Depends(get_current_user)):
        require_pro(user)
        ref = await load_ref(ref_id, {"professional_id": user["_id"]})
        return thread_view(ref, await thread(ref_id))

    @r.post("/professional/court-referrals/{ref_id}/messages")
    async def pro_post(ref_id: str, body: dict, user=Depends(get_current_user)):
        require_pro(user)
        ref = await load_ref(ref_id, {"professional_id": user["_id"], "status": {"$in": ["accepted", "submitted"]}})
        return await post(ref, user, "professional", body.get("text", ""))
