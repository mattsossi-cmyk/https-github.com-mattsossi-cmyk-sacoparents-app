"""GPT 5.6 Terra alternate for the AI executive summary.

Companion to `ai_summary.py`. Uses the exact same prompt/signals shape
so the two summaries are apples-to-apples for the parent choosing
between them.

Why a second model at all: mediators and parents sometimes want a
second read on a report. Offering both Claude Sonnet 4.5 (default)
and GPT 5.6 Terra (alt) is the smallest surface change that lets a
parent pick which voice they find clearer without changing any
existing behaviour.

Constraints inherited from `ai_summary.py`:
  * Neutral, parent-attributed tone.
  * Non-diagnostic, non-adjudicative, no medical/legal advice.
  * Length controlled by `length` arg (short / standard / long).

Uses the Emergent Universal LLM Key — the same key that already
powers Claude summaries. No new API key required.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_summary import (
    _LENGTH_TARGETS, _system_message, _extract_signals,
)


logger = logging.getLogger(__name__)

# Default model. The playbook recommends `gpt-5.4` but the user
# explicitly asked for GPT 5.6 tier — Terra offers the best
# quality/cost balance for a ~200-word neutral summary.
_MODEL_PROVIDER = "openai"
_MODEL_NAME = "gpt-5.6-terra"


async def generate_executive_summary_gpt(
    *, product_name: str,
    report: Dict[str, Any],
    length: str = "standard",
) -> Optional[str]:
    """GPT 5.6 Terra variant of `ai_summary.generate_executive_summary`.

    Same signature, same signals, same guardrails. Never raises — the
    caller falls back to the Claude-generated version on failure so
    the parent's regenerate button always resolves.
    """
    length_key = length if length in _LENGTH_TARGETS else "standard"
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY not configured — cannot regenerate with GPT")
        return None
    signals = _extract_signals(report)
    prompt = (
        f"Product: {product_name}\n"
        "Structured report JSON follows. Produce the one-page executive "
        "summary for a mediator / family professional using the rules "
        "in your system message.\n\n"
        f"{json.dumps(signals, ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"exec-summary-gpt-{uuid.uuid4().hex[:10]}",
            system_message=_system_message(length_key),
        ).with_model(_MODEL_PROVIDER, _MODEL_NAME)
        text = await chat.send_message(UserMessage(text=prompt))
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return None
        # Match the defensive length caps `ai_summary.py` uses so
        # regenerated text can't blow up the report layout.
        cap = 1200 if length_key == "short" else (2400 if length_key == "standard" else 4200)
        if len(text) > cap:
            text = text[:cap].rsplit(" ", 1)[0].rstrip(",.:;") + "\u2026"
        return text
    except Exception as e:  # noqa: BLE001
        logger.warning("GPT executive summary regeneration failed: %s", e)
        return None
