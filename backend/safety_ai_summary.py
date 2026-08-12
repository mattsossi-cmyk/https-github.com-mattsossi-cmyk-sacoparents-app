"""AI summaries for the Family Violence & Communication Safety Assessment
report.

Mirrors `ai_summary.py` (the deep-dive executive summary) but produces
FOUR distinct short narratives:

  * `overall`     — one-paragraph executive summary at the top of the
                    report (mediator / family professional audience)
  * `pathway`     — 2-3 sentences framing why the recommended pathway
                    (self-directed / structured mediation / court-only)
                    was chosen from THIS parent's safety-level tier
  * `section_1`   — narrative of the immediate safety screen answers
  * `section_2`   — narrative of the communication readiness answers

Constraints (strict — same as `ai_summary.py`):
  * Neutral, parent-attributed language ("Alex reports…").
  * Non-diagnostic, non-adjudicative, no legal or medical advice.
  * Plain language, no jargon, no personally identifying details
    beyond what the parent themselves provided.
  * **Never** minimise or "explain away" concrete safety indicators.
  * When any safety indicator is present, gently name it and suggest
    speaking to a qualified family-violence advocate or attorney.

The function returns `{overall, pathway, section_1, section_2}` where
each value is either a non-empty string OR `None` (LLM unavailable / a
particular section had nothing to summarise). Callers must handle
`None` gracefully — the PDF layout still needs to render if the
Emergent LLM key is missing or a call fails.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage


logger = logging.getLogger(__name__)

_MODEL_PROVIDER = "anthropic"
_MODEL_NAME = "claude-sonnet-4-5-20250929"

# Character caps so a runaway LLM response can't blow the PDF layout.
_CAP_OVERALL   = 2400
_CAP_PATHWAY   = 900
_CAP_SECTION   = 1600


def _system_message() -> str:
    return (
        "You are a neutral co-parenting mediation writer producing short "
        "plain-language narratives on top of a structured Family Violence "
        "& Communication Safety Assessment report for the parent who "
        "completed it. The report is framed by the Trauma-Informed Safety "
        "and Functioning Lens (TISFL). You MUST write inside the lens.\n\n"
        "Rules you must always follow:\n"
        "  1. Neutral, parent-attributed tone. Never take sides. Never "
        "     characterise the other parent from the questionnaire — the "
        "     answering parent's own perspective is all we have.\n"
        "  2. Non-diagnostic. Never suggest diagnoses, prognoses, or "
        "     treatments for either parent. Never use words like PTSD, "
        "     personality disorder, narcissist, borderline, bipolar, etc.\n"
        "  3. Non-adjudicative. Never suggest one parent is 'right' or "
        "     'a better parent'.\n"
        "  4. No legal advice. No medical advice. When appropriate, "
        "     suggest speaking to a qualified family-violence advocate, "
        "     attorney, or court professional.\n"
        "  5. NEVER minimise, dismiss, or reframe a concrete safety "
        "     indicator (physical harm, coercive control, stalking, "
        "     threats). If one is present in the data, name it plainly "
        "     and suggest professional support.\n"
        "  6. NEVER mutualise abuse. If the data reports coercive-control "
        "     or high-concern behaviour, describe that behaviour on its "
        "     own — do NOT reframe it as 'conflict between the parents' "
        "     or 'each of you contributed'.\n"
        "  7. Trauma responses are protective adaptations, not evidence of "
        "     unfitness. When describing communication-readiness signals, "
        "     name them as behavioural/functional context — not as "
        "     character flaws.\n"
        "  8. A history of trauma does not excuse coercion, intimidation, "
        "     or harmful parenting behaviour. If both are present, name "
        "     them separately — do not collapse them.\n"
        "  9. Plain language. No jargon. Short sentences.\n"
        " 10. Do NOT include the parent's or child's real name unless "
        "     it is already in the structured data.\n"
        " 11. Do not fabricate details. Only use what is in the "
        "     structured data provided."
    )


def _signals(doc: Dict[str, Any],
             section_1_rows: List[Dict[str, str]],
             section_2_rows: List[Dict[str, str]]) -> Dict[str, Any]:
    """Compact, non-sensitive projection of the assessment doc for the LLM."""
    result = doc.get("result") or {}
    return {
        "safety_level":         result.get("safety_level"),
        "safety_level_label":   result.get("safety_level_label"),
        "recommended_pathway":  result.get("recommended_pathway"),
        "pathway_label":        result.get("pathway_label"),
        "pathway_summary":      result.get("summary") or result.get("pathway_summary"),
        "flags":                result.get("flags") or [],
        "section_1": [
            {"q": r.get("text"), "a": r.get("answer")}
            for r in (section_1_rows or [])
        ],
        "section_2": [
            {"q": r.get("text"), "a": r.get("answer")}
            for r in (section_2_rows or [])
        ],
    }


async def _one_shot(prompt: str, cap: int) -> Optional[str]:
    """Send a single prompt, apply a character cap, return trimmed text
    or None on any failure. Never raises."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY not configured — skipping safety AI summary")
        return None
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"safety-summary-{uuid.uuid4().hex[:10]}",
            system_message=_system_message(),
        ).with_model(_MODEL_PROVIDER, _MODEL_NAME)
        text = await chat.send_message(UserMessage(text=prompt))
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return None
        if len(text) > cap:
            text = text[:cap].rsplit(" ", 1)[0].rstrip(",.:;") + "…"
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("safety AI summary failed: %s", exc)
        return None


async def generate_safety_summaries(
    *,
    doc: Dict[str, Any],
    section_1_rows: List[Dict[str, str]],
    section_2_rows: List[Dict[str, str]],
) -> Dict[str, Optional[str]]:
    """Produce the four AI narratives for the Safety Assessment PDF.

    Returns a dict with keys `overall`, `pathway`, `section_1`,
    `section_2`. Any key may be `None` when the LLM is unavailable or a
    particular section has no answers on file — the caller must render
    the PDF cleanly in that case.
    """
    sig = _signals(doc, section_1_rows, section_2_rows)
    sig_json = json.dumps(sig, ensure_ascii=False)

    # Section-specific prompts. Each is deliberately short so the LLM
    # doesn't drift into overall commentary when we only want that
    # section's angle.
    overall_prompt = (
        "Produce a ~180-word executive summary of the assessment below "
        "for a mediator or family-law professional. Cover: (a) one "
        "framing sentence, (b) what the safety indicators show at a "
        "glance, (c) what the communication-readiness answers show, "
        "(d) whether the recommended pathway is a fit given the data, "
        "(e) one child-focused closing line.\n\n"
        f"Data:\n{sig_json}"
    )
    pathway_prompt = (
        "In 2-3 sentences, explain why the recommended pathway "
        "(mediation, structured mediation, or court-only) is a fit "
        "given the safety level and the concrete answers below. Do NOT "
        "minimise safety indicators. Do NOT give legal advice.\n\n"
        f"Data:\n{sig_json}"
    )
    section_1_prompt = (
        "In ~90 words, write a plain-language narrative of what the "
        "Section 1 IMMEDIATE SAFETY SCREEN answers show for this "
        "parent. Name concrete safety indicators plainly. Never "
        "minimise. Never re-characterise the other parent from the "
        "questionnaire.\n\n"
        f"Data:\n{sig_json}"
    )
    section_2_prompt = (
        "In ~90 words, write a plain-language narrative of what the "
        "Section 2 COMMUNICATION READINESS answers show for this "
        "parent. Focus on strengths and areas that would need "
        "structured support before consensual co-parent communication "
        "is likely to hold.\n\n"
        f"Data:\n{sig_json}"
    )

    # Sequential (not gather) so a slow LLM only doubles perceived
    # latency, not quadruples it, if any one call hangs. Emergent LLM
    # provider handles concurrency at its side; overlapping four calls
    # from one session hasn't been observed to be faster in practice.
    overall   = await _one_shot(overall_prompt,   _CAP_OVERALL)
    pathway   = await _one_shot(pathway_prompt,   _CAP_PATHWAY)
    section_1 = await _one_shot(section_1_prompt, _CAP_SECTION) if section_1_rows else None
    section_2 = await _one_shot(section_2_prompt, _CAP_SECTION) if section_2_rows else None

    return {
        "overall":   overall,
        "pathway":   pathway,
        "section_1": section_1,
        "section_2": section_2,
    }
