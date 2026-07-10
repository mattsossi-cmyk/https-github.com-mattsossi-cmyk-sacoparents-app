"""Claude Sonnet 4.5 powered AI service via emergentintegrations."""
import json
import os
import uuid
import re
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage


CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
PROVIDER = "anthropic"


# ============ Universal safety + scope guardrail ============
# Prepended to every system prompt. Centralises Apple/Google review-friendly
# guardrails so the AI cannot give legal advice, validate aggression, or
# minimise safety concerns.
SAFETY_GUARDRAIL = (
    "CRITICAL SAFETY & SCOPE RULES — apply these to every response:\n"
    "1. You are NOT a lawyer, therapist, or licensed mediator. Never give legal "
    "advice, custody-outcome predictions, or therapeutic diagnoses. If the parent "
    "asks 'what will the court do' or 'do I have a case', redirect them to consult "
    "a qualified family attorney or mediator.\n"
    "2. Never validate, soften, or rationalise aggression, threats, control, "
    "intimidation, or any form of abuse — physical, sexual, emotional, verbal, or "
    "financial. If the parent's input contains language suggesting domestic violence, "
    "stalking, suicidal ideation, or threats to harm anyone (including children, "
    "themselves, or the co-parent), gently surface that the National DV Hotline "
    "(1-800-799-7233) and Suicide & Crisis Lifeline (988) are available 24/7. Do not "
    "lecture; just acknowledge and resource.\n"
    "3. Never write content that disparages the co-parent personally. Stay focused on "
    "behaviours, patterns, and the child's wellbeing — not character judgements.\n"
    "4. If the parent describes a high-conflict or unsafe pattern, gently note that "
    "parallel parenting (minimal contact, structured communication) may be more "
    "appropriate than traditional co-parenting. Do not push reconciliation.\n"
    "5. Centre every recommendation on the child's emotional safety and developmental "
    "needs — not on what is 'fair' between the parents.\n"
    "6. Output strict JSON only when the response schema requires it — no prose "
    "outside the JSON, no apologies, no preamble.\n\n"
)


def _make_chat(system_prompt: str) -> LlmChat:
    return LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"sa-coparents-{uuid.uuid4().hex[:10]}",
        system_message=SAFETY_GUARDRAIL + system_prompt,
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


def _previous_context_block(previous: Optional[Dict[str, Any]], scope: str) -> str:
    """Render the previous doc as a compact 'baseline' block for the AI prompt.

    `scope` controls which slice of the prep_snapshot is included:
      - 'full'        — child_goals, issues, priority, comm_style, readiness
      - 'agreement'   — child_goals, issues, priority only
      - 'improvement' — comm_style, readiness only
    """
    if not previous or not previous.get("prep_snapshot"):
        return ""
    snap = previous["prep_snapshot"]
    if scope == "agreement":
        snap = {k: snap.get(k) for k in ("child_goals", "issues", "priority")}
    elif scope == "improvement":
        snap = {k: snap.get(k) for k in ("comm_style", "readiness")}
    return f"""
=== PREVIOUS PREPARATION (baseline for comparison) ===
Generated on: {previous.get("generated_at", "unknown date")}
Previous prep data:
{json.dumps(snap, indent=2, default=str)}
"""


_CHANGES_INSTRUCTION = """
This parent has a previous version of this document. Compare the CURRENT prep data
to the PREVIOUS PREPARATION above. Populate the `changes_since_last` field with a
warm, SPECIFIC summary of what has shifted — written as if speaking directly to the
parent. Cite concrete deltas (e.g., "your readiness on listening shifted from 2 to
4", "you added Geographic Restriction as urgent", "your top concern shifted from X
to Y"). Acknowledge growth without flattery. If nothing meaningful changed, set
`changes_since_last` to "" (empty string).
"""


# ============ Section-level coaching (Readiness / Comm Style / Safety) ============
# The user-facing intent: replace "your score is 68" with a coaching card that
# names strengths first, gently surfaces one growth area, and offers ONE
# specific next step. All three sections that produce a score feed into the
# same synthesis function to keep the tone identical across the app.
COACHING_SYSTEM = (
    "You are a compassionate, objective, child-focused, non-judgmental, hopeful "
    "co-parenting coach — not a scorekeeper. You speak directly to the parent "
    "using 'you'. You NEVER lead with the number. You always start with a real "
    "strength, then acknowledge one gentle growth area (framed as an opportunity, "
    "never a deficit), then offer ONE specific, small, this-week-doable next step. "
    "Output strict JSON only. No preamble."
)

_SECTION_LENSES = {
    "readiness": (
        "Section context: Mediation Readiness Check — a self-report where the "
        "parent scored themselves 1-5 across five sections (Emotional Preparation, "
        "Practical Preparation, Communication Skills, Child-Focused Mindset, "
        "Mediation Readiness). The `pct` is 0-100. Low sub-scores show growth "
        "areas; the highest sub-score points to a genuine strength."
    ),
    "comm-style": (
        "Section context: Communication Style Assessment. The `style_label` "
        "captures the parent's dominant communication pattern (Avoider, "
        "Escalator, Defensive Responder, Over-Explainer, Passive Communicator, "
        "or Balanced). The `score` is 1-10 mediation-readiness. Their strengths "
        "and growth_areas are the parent's own listed traits."
    ),
    "safety": (
        "Section context: IPV / Safety Assessment pathway. The `level` is one of "
        "Green (healthy communication ok), Yellow (structured co-parenting with "
        "boundaries), Red (parallel parenting / safety-first / professional "
        "support). NEVER encourage direct communication if level=Red. Prioritise "
        "child safety over co-parenting harmony."
    ),
    "overall": (
        "Section context: WHOLE-JOURNEY snapshot. The payload aggregates every "
        "module the parent has completed — child goals, issues, priorities, "
        "communication style, foundation statement, readiness check, and safety "
        "assessment. Zoom out and coach on the pattern across everything, not "
        "one section. `opener` should acknowledge the whole journey."
    ),
}


async def generate_section_coaching(section: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return three coaching insights for a scored section.

    Response schema (strict JSON):
      {
        "strengths":  "1-2 warm sentences naming what the parent is doing well",
        "attention":  "1-2 sentences naming ONE growth area, non-judgmental",
        "next_step":  "One specific, do-this-week action, single sentence",
        "opener":     "A single sentence framing the coaching (no score, no label)"
      }
    """
    lens = _SECTION_LENSES.get(section, "")
    chat = _make_chat(COACHING_SYSTEM + "\n\n" + lens)
    prompt = f"""The parent just completed the {section} section. Their raw data:

{json.dumps(payload, indent=2, default=str)}

Write coaching feedback that a caring mediator would give. Do NOT quote the
score. Do NOT list the answers back to them. Instead, translate the data into
three insights. Address the parent directly as "you".

Return strict JSON only:
{{
  "opener": "one warm framing sentence — no score, no label",
  "strengths": "1 to 2 sentences naming a specific strength",
  "attention": "1 to 2 sentences naming ONE growth area with kindness",
  "next_step": "one specific, small, this-week-doable action"
}}
"""
    response = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(response)
    # Coerce to strings (defensive — Claude sometimes returns arrays for these keys).
    for key in ("opener", "strengths", "attention", "next_step"):
        val = data.get(key)
        if isinstance(val, list):
            data[key] = " ".join(str(v) for v in val)
        elif val is None:
            data[key] = ""
        else:
            data[key] = str(val)
    return data



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


async def generate_summary(
    prep: Dict[str, Any],
    user_name: str,
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    chat = _make_chat(SUMMARY_SYSTEM)
    prev_block = _previous_context_block(previous, scope="full")
    changes_instruction = _CHANGES_INSTRUCTION if previous else ""
    prompt = f"""Generate a mediation prep summary for {user_name}.

Their CURRENT preparation data:
{json.dumps(prep, indent=2, default=str)}
{prev_block}
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
  "readiness_score": integer 1-100,
  "changes_since_last": "ONLY if a previous version exists — a warm, specific summary of what has changed. Otherwise empty string."
}}
{changes_instruction}"""
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


# ============ Things I Can Improve On (compiled from comm + readiness) ============
IMPROVEMENT_SYSTEM = (
    "You are a compassionate co-parenting coach. You take a parent's communication "
    "self-assessment and their readiness-for-mediation self-ratings and turn them "
    "into a short, actionable, warm action plan — written directly to the parent. "
    "You never blame, never moralize, and always frame growth as a kindness to "
    "themselves and their child. You give SPECIFIC, do-this-tomorrow advice — not "
    "generic life-coach language. Output strict JSON only."
)


async def generate_improvement_plan(
    comm_style: Dict[str, Any] | None,
    readiness: Dict[str, Any] | None,
    user_name: str,
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compile a 'Things I Can Improve On' plan from communication + readiness data."""
    chat = _make_chat(IMPROVEMENT_SYSTEM)
    prev_block = _previous_context_block(previous, scope="improvement")
    changes_instruction = _CHANGES_INSTRUCTION if previous else ""
    prompt = f"""Generate a personalized "Things I Can Improve On" action plan for {user_name}.

Use ONLY these two inputs:

Communication self-assessment (3 questions, each tagged with one of:
avoider, escalator, defensive, over_explainer, passive, balanced):
{json.dumps(comm_style or {{}}, indent=2, default=str)}

Readiness self-ratings (6 questions, 1=Not yet, 2=Sometimes, 3=Often, 4=Usually, 5=Yes consistently):
- listen: can listen without interrupting
- past: can discuss without raising past relationship pain
- future: willing to focus on future solutions
- separate: can separate parenting from personal hurt
- calm: have strategies to stay calm under pressure
- respect: can speak respectfully even when disagreeing

Data:
{json.dumps(readiness or {{}}, indent=2, default=str)}
{prev_block}
Return strict JSON only with these exact keys:
{{
  "headline": "1 warm sentence that names the 1-2 biggest growth areas without judgment",
  "focus_areas": [
    {{
      "title": "short title of the growth area (e.g. 'Pausing before responding')",
      "why_it_matters": "1 sentence on how this affects your child and your day-to-day",
      "communication_tips": ["3 SPECIFIC tips for messages/conversations — actionable phrases or rituals"],
      "quality_of_life_tips": ["2 SPECIFIC tips for self-care, regulation, or habits that support this growth area"]
    }}
  ],
  "this_week": ["3 small, concrete actions to try in the next 7 days — each starts with a verb"],
  "encouragement": "1-2 warm sentences acknowledging the courage of doing this work",
  "changes_since_last": "ONLY if a previous version exists — a warm, specific note on what shifted. Call out growth (a ratings jump) AND new areas surfacing. Otherwise empty string."
}}

Important:
- Pick 2-4 focus_areas based on the WEAKEST patterns in their data — do not list everything.
- A 'balanced' answer or a 4-5 rating is a STRENGTH, not a growth area — only flag genuine gaps.
- Tips must reference real-life co-parenting scenarios (exchanges, texts, child's school events, holidays, etc).
- Avoid clichés ('be the bigger person', 'communication is key', 'practice mindfulness').
- If both inputs are mostly empty, return focus_areas=[] and put a gentle note in 'headline' that more reflection is needed.
{changes_instruction}"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)

AGREEMENT_SYSTEM = (
    "You are a co-parenting agreement drafting assistant. Take what each parent has "
    "captured during their preparation and translate it into a CALM, NEUTRAL, "
    "CHILD-CENTERED DRAFT agreement that two co-parents could review together. "
    "This is NOT a legal document — it is a starting point for discussion. "
    "Use first-person plural ('we', 'our') where natural. Avoid blame, never name "
    "either parent. Keep each clause short, factual, and constructive. "
    "Output strict JSON only — no prose outside the JSON."
)


async def generate_agreement_draft(
    prep: Dict[str, Any],
    user_name: str,
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    chat = _make_chat(AGREEMENT_SYSTEM)
    prev_block = _previous_context_block(previous, scope="agreement")
    changes_instruction = _CHANGES_INSTRUCTION if previous else ""
    prompt = f"""Draft a co-parenting agreement for {user_name} based ONLY on this
preparation data (ignore any communication-style or readiness data).

CURRENT preparation data:
{json.dumps(prep, indent=2, default=str)}
{prev_block}
Return strict JSON only with these exact keys:
{{
  "overview": "1-2 sentence warm intro framing this as a child-centered draft",
  "shared_goals": ["3-6 short statements of what we want our child to experience"],
  "communication": [
    {{"area": "Texting|Response times|Emergency|Other", "agreement": "one neutral sentence"}}
  ],
  "child_needs": [
    {{"area": "School|Therapy|Medical|Activities|Other", "agreement": "one neutral sentence"}}
  ],
  "household_rules": [
    {{"area": "Discipline|Screen time|Bedtime|Homework|Other", "agreement": "one neutral sentence"}}
  ],
  "priority_items": [
    {{"rank": 1, "topic": "...", "category": "urgent|difficult|easy|compromise"}}
  ],
  "open_for_discussion": ["topics where no clear agreement was captured yet"],
  "closing_note": "one warm sentence framing this as a living draft to revisit together",
  "changes_since_last": "ONLY if a previous version exists — a short neutral list-style summary of what changed (new clauses, removed clauses, refined wording). Otherwise empty string."
}}

Important:
- Do NOT include any parenting-schedule or financial clauses, even if such data was captured. Those topics will be handled separately.
- If a section has NO captured input, return an empty array [] (do NOT invent content).
- Spell every co-parent input faithfully; do not add legal-sounding language.
- Keep each "agreement" clause under ~24 words.
{changes_instruction}"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)



# ============ Journal weekly recap ============
async def generate_journal_weekly_recap(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize the past week of journal entries into 2–4 reflective
    sentences plus 3–5 short theme tags. Tone is warm, calm, and
    non-judgmental — this is for the parent's own eyes only.

    `entries` is a chronological list of dicts:
        { kind, content, prompt_text, created_at }
    """
    if not entries:
        return {"recap_text": None, "themes": []}

    rendered_entries = []
    for e in entries:
        when = (e.get("created_at") or "")[:10]
        prompt = e.get("prompt_text")
        kind = e.get("kind") or "daily"
        body = (e.get("content") or "").strip()
        if not body:
            continue
        header = f"[{when} · {kind}]"
        if prompt:
            header += f" Prompt: {prompt}"
        rendered_entries.append(f"{header}\n{body}")
    journal_block = "\n\n".join(rendered_entries[-30:])  # safety cap

    system_prompt = (
        "You are a gentle, encouraging journaling companion writing a weekly "
        "recap for a co-parent navigating mediation prep. You write in a warm, "
        "calm, non-judgmental voice. You do not give legal or mental-health "
        "advice. You speak in plain second-person ('you wrote about…')."
    )
    chat = _make_chat(system_prompt)
    prompt = f"""Below are the parent's journal entries from the past week.
Write a 2–4 sentence recap of what showed up most — the feelings, the themes,
and any small wins or hard moments. Be kind. Speak to them directly using "you".
Then list 3–5 short, lowercase theme tags (1–3 words each) describing what
came up. Do not quote them verbatim. Do not give advice.

=== ENTRIES ===
{journal_block}

Return ONLY valid JSON in this exact shape:
{{
  "recap_text": "string — 2 to 4 sentences",
  "themes": ["tag one", "tag two", "tag three"]
}}
"""
    response = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(response)
    recap_text = (data.get("recap_text") or "").strip() or None
    themes = data.get("themes") or []
    if not isinstance(themes, list):
        themes = []
    themes = [str(t).strip().lower() for t in themes if str(t).strip()][:6]
    return {"recap_text": recap_text, "themes": themes}
