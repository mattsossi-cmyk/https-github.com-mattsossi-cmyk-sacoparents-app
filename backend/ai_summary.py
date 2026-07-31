"""AI-generated one-page executive summary for deep-dive reports.

Uses Claude Sonnet 4.5 via the Emergent LLM key. Non-streaming — called once
during report generation and cached inside the report document.

Constraints (strict):
  * Neutral, parent-attributed language ("Alex reports…").
  * Non-diagnostic, non-adjudicative, no medical/legal advice.
  * ~200 words, plain language, aimed at a mediator or family professional.
  * No sensitive personal detail beyond what already exists in the report.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage


logger = logging.getLogger(__name__)

_MODEL_PROVIDER = "anthropic"
_MODEL_NAME = "claude-sonnet-4-5-20250929"

_SYSTEM = (
    "You are a neutral co-parenting mediation writer. You produce short "
    "plain-language executive summaries on top of structured co-parenting "
    "assessment reports. Rules you must always follow:\n"
    "  1. Neutral, parent-attributed tone. Never take sides.\n"
    "  2. Non-diagnostic. Never suggest diagnoses, prognoses, or treatments.\n"
    "  3. Non-adjudicative. Never suggest one parent is 'right' or a 'better' parent.\n"
    "  4. No medical, legal, or psychological advice. Suggest talking to qualified professionals when relevant.\n"
    "  5. Around 180-220 words. Plain language. No jargon.\n"
    "  6. Structure: (a) one-sentence framing, (b) 2-3 strengths, (c) 2-3 areas to develop, (d) one child-focused closing line.\n"
    "  7. If the report contains safety signals, name them plainly and suggest speaking with the prescriber, school nurse, or a qualified professional promptly.\n"
    "  8. Never include the parent's or child's real name unless it is already provided in the report.\n"
    "  9. Do not fabricate details. Only use what is in the structured report."
)


def _extract_signals(report: Dict[str, Any]) -> Dict[str, Any]:
    """Pull only the essential structured signals from the deep-dive report."""
    summary = report.get("summary") or {}
    sections = []
    for s in (report.get("sections") or []):
        sections.append({
            "name": s.get("name"),
            "is_flagged": s.get("is_flagged"),
            "is_strength": s.get("is_strength"),
            "flag_reasons": s.get("flag_reasons") or [],
            "strength_reasons": s.get("strength_reasons") or [],
            "risk_signals": s.get("risk_signals") or [],
        })
    return {
        "cover": report.get("cover") or {},
        "profile": report.get("profile") or {},
        "summary": {
            "answered_sections": summary.get("answered_sections"),
            "flagged_sections": summary.get("flagged_sections"),
            "strength_sections": summary.get("strength_sections"),
            "risk_signals": summary.get("risk_signals") or [],
            "flagged_names": summary.get("flagged_names") or [],
            "strength_names": summary.get("strength_names") or [],
        },
        "sections": sections,
    }


async def generate_executive_summary(*, product_name: str,
                                     report: Dict[str, Any]) -> Optional[str]:
    """Return a short plain-language narrative, or None on failure.

    Never raises: the caller falls back to a report-without-narrative if the
    LLM call fails so report generation stays reliable.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY not configured — skipping AI summary")
        return None
    signals = _extract_signals(report)
    prompt = (
        f"Product: {product_name}\n"
        "Structured report JSON follows. Produce the one-page executive summary "
        "for a mediator / family professional using the rules in your system message.\n\n"
        f"{json.dumps(signals, ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"exec-summary-{uuid.uuid4().hex[:10]}",
            system_message=_SYSTEM,
        ).with_model(_MODEL_PROVIDER, _MODEL_NAME)
        text = await chat.send_message(UserMessage(text=prompt))
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return None
        # Very defensive length guard so the report layout stays clean.
        if len(text) > 2400:
            text = text[:2400].rsplit(" ", 1)[0].rstrip(",.:;") + "…"
        return text
    except Exception as e:  # noqa: BLE001
        logger.warning("AI summary generation failed: %s", e)
        return None
