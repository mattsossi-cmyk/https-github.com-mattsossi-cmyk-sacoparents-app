"""AI drafting of concrete agreement clauses from both parents' follow-up answers (gpt-5.4-mini via Emergent key)."""
import hashlib
import json
import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM = (
    "You draft neutral, child-focused co-parenting agreement clauses for SA CoParents Align. "
    "You receive, per section, both parents' general proposals and their answers to numbered follow-up items (each has an 'id'). "
    "Rules: never decide who is right; never recommend custody; never invent facts. For EVERY item with at least one answer, return exactly one verdict: "
    "'agreed' when both parents' answers point the same way — then write one concrete clause in plain 'Parents will…' / 'Each parent will…' language including method, timing, and who acts; "
    "'open' when the answers materially differ or only one parent answered — then write a neutral one-sentence description of the difference, never a merged clause. "
    "Also return communication_method / decision_process / review_trigger (string or null) ONLY from agreed items. "
    "Return ONLY JSON: {\"sections\": {\"<key>\": {\"items\": [{\"id\": \"<id>\", \"verdict\": \"agreed\"|\"open\", \"text\": \"...\"}], "
    "\"communication_method\": \"..\" or null, \"decision_process\": \"..\" or null, \"review_trigger\": \"..\" or null}}}."
)


def answers_signature(doc: dict) -> str:
    ra = (doc.get("responses", {}).get("a") or {}).get("answers") or {}
    rb = (doc.get("responses", {}).get("b") or {}).get("answers") or {}
    return hashlib.sha256(json.dumps([ra, rb], sort_keys=True).encode()).hexdigest()[:24]


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def draft_agreement_clauses(sections_payload: list[dict], session_id: str) -> dict | None:
    """Returns {section_key: {...}} or None when the model is unavailable/unparseable (caller falls back to rules)."""
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=f"agreement-{session_id}", system_message=SYSTEM).with_model("openai", "gpt-5.4-mini")
        text = await chat.send_message(UserMessage(text=json.dumps({"sections": sections_payload}, ensure_ascii=False)))
        data = _extract_json(text or "")
        sections = (data or {}).get("sections")
        if not isinstance(sections, dict):
            return None
        return {k: _normalize(v) for k, v in sections.items() if isinstance(v, dict)}
    except Exception as exc:
        logger.warning("agreement AI drafting unavailable: %s", exc)
        return None


def _normalize(sec: dict) -> dict:
    """Item verdicts → disjoint specific/open lists; an item can never be in both."""
    specific, open_issues = [], []
    for it in sec.get("items") or []:
        if not isinstance(it, dict) or not (it.get("text") or "").strip():
            continue
        (specific if it.get("verdict") == "agreed" else open_issues).append(it["text"].strip())
    return {"specific": specific, "open_issues": open_issues,
            "communication_method": sec.get("communication_method") or None, "decision_process": sec.get("decision_process") or None, "review_trigger": sec.get("review_trigger") or None}
