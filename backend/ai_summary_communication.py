"""
LLM-authored neutral summary for a Communication Alignment compare.

Same conventions as `ai_summary.py`:
  * Emergent LLM Key.
  * Claude Sonnet 4.5 by default; optional swap to GPT-5.6 Terra when
    the caller passes `model="gpt"`.
  * Never raises — returns `None` on failure so the compare page can
    render its data-only fallback.
  * Strict guardrails: neutral, non-adjudicative, parent-attributed,
    no medical/legal advice.

Output shape: a single short block (~150–220 words) with the founder-
requested structure: one framing line, then "what you already share",
then "where you differ", then a one-line neutral suggestion. No
prescriptive "you should do X" language, no naming the co-parent's
score as wrong or right.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_models import resolve_model


logger = logging.getLogger(__name__)


def _system_message() -> str:
    return (
        "You are a neutral co-parenting mediation writer producing a "
        "Communication Alignment executive summary. Follow every rule:\n"
        "  1. Neutral tone. Never say one parent is doing 'better'.\n"
        "  2. Attribute claims: 'you report…', 'your co-parent reports…'.\n"
        "  3. Never diagnose, adjudicate, or give legal / medical advice.\n"
        "  4. Never invent specifics beyond what appears in the JSON.\n"
        "  5. Around 150-220 words. Plain, hopeful, mediator-ready.\n"
        "  6. Structure exactly:\n"
        "        (a) one sentence framing the two-parent picture,\n"
        "        (b) one short paragraph on 'what you already share',\n"
        "        (c) one short paragraph on 'where you see this differently',\n"
        "        (d) one closing line — a child-focused, structured invitation,\n"
        "            never a directive.\n"
        "  7. Never label a dimension score as 'good' or 'bad'. Use gentle "
        "phrasing: 'more aligned', 'further apart', 'still forming'.\n"
        "  8. Never mention diagnosis words like ADHD, PTSD, DV — those "
        "belong on the Safety pathway, not here.\n"
        "  9. If the JSON contains an `intake_choice` of 'unsafe', return the "
        "single sentence: 'This pathway does not produce an alignment summary "
        "when either parent reports communication feels unsafe — please open "
        "the Safety pathway instead.'"
    )


def _summarise_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip the compare payload to the structured signals the LLM needs.
    Free-text notes are intentionally NOT included — the parent's raw
    words don't belong in a neutral joint artefact.
    """
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


async def generate_communication_summary(
    payload: Dict[str, Any], model: Optional[str] = None
) -> Optional[str]:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning(
            "EMERGENT_LLM_KEY not configured — skipping Communication summary"
        )
        return None

    signals = _summarise_payload(payload)

    # Explicit short-circuit for the unsafe intake choice — never
    # trust the LLM to catch this. The system message tells the model
    # to produce the safety sentence in that case, but we also
    # hard-code the answer here so the API surface is deterministic.
    if signals.get("self_intake") == "unsafe" or signals.get("coparent_intake") == "unsafe":
        return (
            "This pathway does not produce an alignment summary when either "
            "parent reports communication feels unsafe — please open the "
            "Safety pathway instead."
        )

    provider, model_name = resolve_model(model)
    prompt = (
        "Product: Communication Alignment Report\n"
        "Compare signals JSON follows. Produce the short summary using the "
        "structure and guardrails in your system message.\n\n"
        f"{json.dumps(signals, ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"comm-align-{uuid.uuid4().hex[:10]}",
            system_message=_system_message(),
        ).with_model(provider, model_name)
        text = await chat.send_message(UserMessage(text=prompt))
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return None
        # Length guard so the report layout stays clean.
        if len(text) > 2400:
            text = text[:2400].rsplit(" ", 1)[0].rstrip(",.:;") + "…"
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("Communication summary generation failed: %s", exc)
        return None
