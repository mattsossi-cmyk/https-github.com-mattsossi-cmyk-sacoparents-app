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


class Threads:
    """Court ⇄ professional message thread service (storage, AI summary, notifications)."""

    def __init__(self, db, app_url, send_email, email_from_name):
        self.db, self.app_url, self.send_email, self.email_from_name = db, app_url, send_email, email_from_name

    @staticmethod
    def public(m: dict) -> dict:
        return {k: m.get(k) for k in ("id", "from_role", "from_name", "text", "at", "triage", "urgent_alert_sent_at")}

    async def thread(self, ref_id: str) -> list[dict]:
        return await self.db.court_messages.find({"referral_id": ref_id}, {"_id": 0}).sort("at", 1).to_list(500)

    def thread_view(self, ref: dict, msgs: list) -> dict:
        return {"messages": [self.public(m) for m in msgs], "summary": ref.get("communication_summary")}

    async def load_ref(self, ref_id: str, query: dict) -> dict:
        ref = await self.db.court_referrals.find_one({"id": ref_id, **query}, {"_id": 0})
        if not ref:
            raise HTTPException(status_code=404, detail="Referral not found")
        return ref

    async def _recipient(self, ref: dict, role: str) -> tuple[str | None, str, str]:
        if role == "court":
            pro = await self.db.users.find_one({"_id": ref["professional_id"]}, {"email": 1, "name": 1}) or {}
            return pro.get("email"), "Professional", f"{self.app_url()}/dashboard#court-referrals"
        return ref.get("judge_email"), "Court", f"{self.app_url()}/court/case/{ref['id']}"

    async def notify(self, ref: dict, user: dict, role: str, text: str, triage: dict | None = None) -> str | None:
        to, to_role, link = await self._recipient(ref, role)
        if not to:
            return None
        urgent = role == "professional" and (triage or {}).get("category") == "urgent_safety"
        subject = (f"URGENT — safety concern raised - Cause No. {ref.get('cause_number', '')}" if urgent else f"Court communication - Cause No. {ref.get('cause_number', '')}")
        try:
            await self.send_email(to=to, case_id=ref.get("case_id") or ref["id"], kind="court_urgent_safety" if urgent else "court_message", to_role=to_role, subject=subject,
                                  html=_message_email_html(ref, user, role, text, link, self.email_from_name, urgent))
        except Exception as exc:
            logger.warning("court message email failed: %s", exc)
            return None
        return "urgent" if urgent else "standard"

    async def post(self, ref: dict, user: dict, role: str, text: str) -> dict:
        text = (text or "").strip()[:4000]
        if not text:
            raise HTTPException(status_code=400, detail="Message is empty")
        from jev import message_triage
        msg = {"id": str(uuid.uuid4()), "referral_id": ref["id"], "case_id": ref.get("case_id"), "from_role": role, "from_user": user["_id"], "from_name": user.get("name", ""), "text": text, "at": _now(),
               "triage": await message_triage(text)}
        await self.db.court_messages.insert_one(dict(msg))
        summary = await summarize_thread(await self.thread(ref["id"]), ref)
        await self.db.court_referrals.update_one({"id": ref["id"]}, {"$set": {"communication_summary": summary}})
        if ref.get("case_id"):
            await self._audit(ref, user, role, msg["at"])
        sent = await self.notify(ref, user, role, text, msg["triage"])
        if sent == "urgent":
            msg["urgent_alert_sent_at"] = _now()
            upd = {"urgent_alert_sent_at": msg["urgent_alert_sent_at"]}
            await self.db.court_messages.update_one({"id": msg["id"]}, {"$set": upd})
        return {"message": self.public(msg), "summary": summary}


    async def _audit(self, ref: dict, user: dict, role: str, at: str) -> None:
        who = "the Court" if role == "court" else "the professional"
        await self.db.access_events.insert_one({"report_id": ref["case_id"], "kind": "court", "action": f"Court communication: message from {who} ({user.get('name', '')})",
                                                "at": at, "by": user["_id"], "by_name": user.get("name", ""), "by_role": "Court" if role == "court" else "Professional"})


def _message_email_html(ref: dict, user: dict, role: str, text: str, link: str, email_from_name: str, urgent: bool = False) -> str:
    banner = ('<div style="background:#b91c1c;color:#fff;padding:10px 14px;font-weight:bold;border-radius:6px;margin-bottom:12px">URGENT — SAFETY CONCERN RAISED BY THE ASSIGNED PROFESSIONAL<br>'
              '<span style="font-weight:normal;font-size:12px">Flagged automatically from the message wording (advisory triage). Please review and respond in the Judicial Portal.</span></div>' if urgent else "")
    return ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">' + banner +
            f"<p>New message from {escape(user.get('name', ''))} ({'the Court' if role == 'court' else 'assigned professional'}) regarding Cause No. {escape(ref.get('cause_number', ''))}:</p>"
            f'<blockquote style="border-left:3px solid {"#b91c1c" if urgent else "#5B2A86"};margin:0;padding:8px 12px;color:#333">{escape(text)}</blockquote>'
            f'<p><a href="{link}" style="color:#5B2A86">Open the case</a></p>'
            f'<p style="font-size:12px;color:#888">Sent by {escape(email_from_name)}.</p></td></tr></table>')


def build_router(db, get_current_user, app_url, send_email, email_from_name, require_judge, require_pro) -> APIRouter:
    r = APIRouter()
    t = Threads(db, app_url, send_email, email_from_name)
    _judge_routes(r, get_current_user, require_judge, t)
    _pro_routes(r, get_current_user, require_pro, t)
    return r





def _judge_routes(r: APIRouter, get_current_user, require_judge, t: Threads) -> None:
    """Judge-facing thread routes (urgent list, per-case messages) + professional thread routes."""

    @r.get("/court-dashboard/urgent-messages")
    async def judge_urgent(user=Depends(get_current_user)):
        """Professional messages Jev triaged as urgent_safety that the Court has not yet answered."""
        await require_judge(user)
        refs = {x["id"]: x async for x in t.db.court_referrals.find({"judge_id": user["_id"]}, {"_id": 0, "id": 1, "cause_number": 1, "case_id": 1})}
        if not refs:
            return {"items": []}
        msgs = await t.db.court_messages.find({"referral_id": {"$in": list(refs)}}, {"_id": 0}).sort("at", 1).to_list(5000)
        last_court = {}
        for m in msgs:
            if m["from_role"] == "court":
                last_court[m["referral_id"]] = m["at"]
        items = [{**t.public(m), "referral_id": m["referral_id"], "cause_number": refs[m["referral_id"]].get("cause_number")} for m in msgs
                 if m["from_role"] == "professional" and (m.get("triage") or {}).get("category") == "urgent_safety" and last_court.get(m["referral_id"], "") < m["at"]]
        return {"items": sorted(items, key=lambda x: x["at"], reverse=True)[:20]}

    @r.get("/court-dashboard/cases/{ref_id}/messages")
    async def judge_thread(ref_id: str, user=Depends(get_current_user)):
        await require_judge(user)
        ref = await t.load_ref(ref_id, {"judge_id": user["_id"]})
        return t.thread_view(ref, await t.thread(ref_id))

    @r.post("/court-dashboard/cases/{ref_id}/messages")
    async def judge_post(ref_id: str, body: dict, user=Depends(get_current_user)):
        await require_judge(user)
        ref = await t.load_ref(ref_id, {"judge_id": user["_id"]})
        return await t.post(ref, user, "court", body.get("text", ""))


def _pro_routes(r: APIRouter, get_current_user, require_pro, t: Threads) -> None:
    @r.get("/professional/court-referrals/{ref_id}/messages")
    async def pro_thread(ref_id: str, user=Depends(get_current_user)):
        require_pro(user)
        ref = await t.load_ref(ref_id, {"professional_id": user["_id"]})
        return t.thread_view(ref, await t.thread(ref_id))

    @r.post("/professional/court-referrals/{ref_id}/messages")
    async def pro_post(ref_id: str, body: dict, user=Depends(get_current_user)):
        require_pro(user)
        ref = await t.load_ref(ref_id, {"professional_id": user["_id"], "status": {"$in": ["accepted", "submitted"]}})
        return await t.post(ref, user, "professional", body.get("text", ""))
