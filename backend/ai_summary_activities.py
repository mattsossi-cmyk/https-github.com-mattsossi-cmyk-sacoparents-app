"""
LLM-authored neutral summary for an Activities Alignment compare.

Same conventions as `ai_summary_communication.py`. Neutral,
parent-attributed, ~150-220 words, three-part structure.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage


logger = logging.getLogger(__name__)

_CLAUDE_PROVIDER = "anthropic"
_CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

_GPT_PROVIDER = "openai"
_GPT_MODEL = "gpt-5.6-terra"


def _system_message() -> str:
    return (
        "You are a neutral co-parenting mediation writer producing an "
        "Activities Alignment executive summary. Follow every rule:\n"
        "  1. Neutral tone. Never say one parent is doing 'better'.\n"
        "  2. Attribute claims: 'you report…', 'your co-parent reports…'.\n"
        "  3. Never diagnose, adjudicate, or give legal / medical advice.\n"
        "  4. Never invent specifics beyond what appears in the JSON.\n"
        "  5. Around 150-220 words. Plain, hopeful, mediator-ready.\n"
        "  6. Structure exactly:\n"
        "        (a) one sentence framing the two-parent picture around "
        "kids' extracurricular activities,\n"
        "        (b) one short paragraph on 'what you already share',\n"
        "        (c) one short paragraph on 'where you see this differently',\n"
        "        (d) one closing line — a child-focused, structured invitation,\n"
        "            never a directive.\n"
        "  7. Scope: sports, arts, faith, tutoring, camps, social plans. "
        "Never medical, educational, or therapeutic decisions.\n"
        "  8. Never label a dimension score as 'good' or 'bad'. Use gentle "
        "phrasing: 'more aligned', 'further apart', 'still forming'.\n"
        "  9. If the JSON contains an `intake_choice` of 'unsafe', return the "
        "single sentence: 'This pathway does not produce an alignment summary "
        "when either parent reports safety concerns — please open the Safety "
        "pathway instead.'"
    )


def _summarise_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    self_score = ((payload.get("self") or {}).get("score") or {})
    coparent_score = ((payload.get("coparent") or {}).get("score") or {})
    return {
        "self_intake": (payload.get("self") or {}).get("intake_choice"),
        "coparent_intake": (payload.get("coparent") or {}).get("intake_choice"),
        "self_overall": self_score.get("overall"),
        "coparent_overall": coparent_score.get("overall"),
        "shared": [
            {
                "label": r.get("label"),
                "self_score": r.get("self_score"),
                "coparent_score": r.get("coparent_score"),
            }
            for r in (payload.get("shared") or [])
        ],
        "gaps": [
            {
                "label": r.get("label"),
                "self_score": r.get("self_score"),
                "coparent_score": r.get("coparent_score"),
                "delta": r.get("delta"),
            }
            for r in (payload.get("gaps") or [])
        ],
    }


async def generate_activities_summary(
    payload: Dict[str, Any], model: str = "claude"
) -> Optional[str]:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning(
            "EMERGENT_LLM_KEY not configured — skipping Activities summary"
        )
        return None

    signals = _summarise_payload(payload)

    if signals.get("self_intake") == "unsafe" or signals.get("coparent_intake") == "unsafe":
        return (
            "This pathway does not produce an alignment summary when either "
            "parent reports safety concerns — please open the Safety pathway "
            "instead."
        )

    provider, model_name = (
        (_GPT_PROVIDER, _GPT_MODEL) if model == "gpt" else (_CLAUDE_PROVIDER, _CLAUDE_MODEL)
    )
    prompt = (
        "Product: Activities Alignment Report\n"
        "Compare signals JSON follows. Produce the short summary using the "
        "structure and guardrails in your system message.\n\n"
        f"{json.dumps(signals, ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"activities-align-{uuid.uuid4().hex[:10]}",
            system_message=_system_message(),
        ).with_model(provider, model_name)
        text = await chat.send_message(UserMessage(text=prompt))
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return None
        if len(text) > 2400:
            text = text[:2400].rsplit(" ", 1)[0].rstrip(",.:;") + "…"
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("Activities summary generation failed: %s", exc)
        return None
