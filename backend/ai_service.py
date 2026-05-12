"""Claude Sonnet 4.5 powered AI service via emergentintegrations."""
import json
import os
import uuid
import re
from typing import Any, Dict, List

from emergentintegrations.llm.chat import LlmChat, UserMessage


CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
PROVIDER = "anthropic"


def _make_chat(system_prompt: str) -> LlmChat:
    return LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"sa-coparents-{uuid.uuid4().hex[:10]}",
        system_message=system_prompt,
    ).with_model(PROVIDER, CLAUDE_MODEL)


def _extract_json(text: str) -> Any:
    """Best-effort JSON extraction from a Claude response."""
    # Try ```json fenced block
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try first {...} or [...]
    for pattern in (r"(\{.*\})", r"(\[.*\])"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON found in response")


# ============ Communication Style Analysis ============
COMM_SYSTEM = (
    "You are a compassionate co-parenting mediation coach. Your tone is warm, "
    "non-judgmental, and focused on the child's wellbeing. You speak directly to the "
    "parent. Never blame; always coach toward calmer, fact-based, child-centered "
    "communication. Always respond in strict JSON only — no prose outside the JSON."
)


async def analyze_communication(quiz_answers: Dict[str, str], free_text: str = "") -> Dict[str, Any]:
    chat = _make_chat(COMM_SYSTEM)
    prompt = f"""Analyze this co-parent's communication style based on their self-assessment.

Quiz answers (questionId -> chosen pattern):
{json.dumps(quiz_answers, indent=2)}

Optional sample message they wrote to their co-parent:
\"\"\"{free_text}\"\"\"

Return strict JSON with these exact keys:
{{
  "style_label": "one of: Avoider, Escalator, Defensive Responder, Over-Explainer, Passive Communicator, or Balanced",
  "summary": "2-3 warm sentences describing their style, addressed to 'you'",
  "strengths": ["2-3 specific strengths"],
  "growth_areas": ["2-3 specific growth areas, framed positively"],
  "suggestions": ["4 concrete, child-centered communication tips, each 1 sentence"],
  "score": integer 1-10 (10 = most mediation-ready)
}}
"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)


# ============ Mediation Summary ============
SUMMARY_SYSTEM = (
    "You are a relational mediation specialist preparing a parent for a co-parenting "
    "mediation session. You write with warmth, dignity, and focus on the child. "
    "You never assign blame. You synthesize the parent's preparation into a clear, "
    "balanced document the mediator can read in 2 minutes. Output strict JSON only."
)


async def generate_summary(prep: Dict[str, Any], user_name: str) -> Dict[str, Any]:
    chat = _make_chat(SUMMARY_SYSTEM)
    prompt = f"""Generate a mediation prep summary for {user_name}.

Their preparation data:
{json.dumps(prep, indent=2, default=str)}

Return strict JSON only with these exact keys:
{{
  "child_goals_summary": "1-2 sentence synthesis of their child-centered goals",
  "top_concerns": ["3-5 top concerns, each a short phrase"],
  "priority_agenda": [
    {{"rank": 1, "topic": "...", "category": "urgent|difficult|easy|compromise"}}
  ],
  "flexibility_areas": ["areas where the parent is open to compromise"],
  "communication_goals": ["3 short communication intentions for the session"],
  "notes_for_mediator": "2-3 sentences of context the mediator should know, neutral tone",
  "readiness_label": "one of: Needs Support, Moderately Ready, Prepared for Mediation",
  "readiness_score": integer 1-100
}}
"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)


# ============ Reframe a sentence ============
REFRAME_SYSTEM = (
    "You are a co-parenting communication coach. Rewrite reactive messages into calm, "
    "fact-based, child-centered alternatives. Output strict JSON only."
)


async def reframe_message(original: str) -> Dict[str, Any]:
    chat = _make_chat(REFRAME_SYSTEM)
    prompt = f"""The parent wrote this message:
\"\"\"{original}\"\"\"

Return strict JSON:
{{
  "reactive_patterns": ["pattern 1", "pattern 2"],
  "reframed": "the calmer, child-centered version",
  "explanation": "1 sentence explaining the shift"
}}
"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)
