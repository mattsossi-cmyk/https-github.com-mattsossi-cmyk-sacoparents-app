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
    readiness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate the Co-Parenting Assessment report (court-respectable structure).

    The `readiness` argument is the deterministic rule-based score bundle
    from readiness_scoring.compute_readiness() — the AI interprets those
    numbers into narrative but does not invent them.
    """
    chat = _make_chat(SUMMARY_SYSTEM)
    prev_block = _previous_context_block(previous, scope="full")
    changes_instruction = _CHANGES_INSTRUCTION if previous else ""

    readiness_block = ""
    if readiness:
        readiness_block = f"""
=== READINESS SCORES (deterministic — do NOT change the numbers) ===
Overall: {readiness['overall']}/100 ({readiness['label']})
Communication:    {readiness['dimensions']['communication']['score']}/100
Trust:            {readiness['dimensions']['trust']['score']}/100
Child alignment:  {readiness['dimensions']['child_alignment']['score']}/100
Conflict (higher = better): {readiness['dimensions']['conflict']['score']}/100
Signals feeding the scores: {json.dumps({k: v['reasons'] for k, v in readiness['dimensions'].items()})}
"""

    prompt = f"""Generate a court-respectable Co-Parenting Assessment for {user_name}.

Their CURRENT preparation data:
{json.dumps(prep, indent=2, default=str)}
{prev_block}{readiness_block}
This report will be shared with mediators, therapists, and family lawyers.
It must read as a professional evaluation document — dignified, evidence-based,
and child-centred. Refer to the parent as "the parent" or by first name.
Never blame the other parent. Ground every claim in the parent's own answers.

Return strict JSON only with these exact keys:
{{
  "executive_summary": "2-3 sentences setting the scene: who is preparing, for what, and how they arrive at this moment. Neutral, dignified tone.",
  "child_priorities": ["3-6 short phrases describing what this parent is prioritising for their child — pulled from child_goals and priority answers"],
  "parent_strengths": ["3-5 short phrases naming the parent's demonstrated strengths (from goals articulated, communication self-awareness, safety awareness, willingness to prepare, etc.)"],
  "areas_of_concern": ["2-4 short phrases naming the areas the parent themselves has flagged as difficult or requiring support — never diagnostic, always in the parent's own frame"],
  "readiness_narrative": "2-3 sentence interpretation of the OVERALL readiness score in plain, warm language. Do NOT restate the number — describe what it means for how mediation might go.",
  "dimension_narratives": {{
    "communication": "1 sentence describing what this score means in practice",
    "trust": "1 sentence describing what this score means in practice",
    "child_alignment": "1 sentence describing what this score means in practice",
    "conflict": "1 sentence describing what this score means in practice"
  }},
  "recommended_next_steps": {{
    "this_week": ["2-3 concrete, specific actions the parent can take in the next 7 days — each starts with a verb"],
    "before_mediation": ["2-3 concrete preparation steps to complete before the actual mediation session"],
    "long_term": ["1-2 growth intentions to keep in view over the next 3 months"]
  }},
  "notes_for_mediator": "2-3 sentences of context a mediator should know — neutral, respectful, does not disparage the co-parent",
  "top_concerns": ["2-4 top logistical concerns to raise in session (schedule/communication/finances/safety) — legacy field, keep populated"],
  "priority_agenda": [
    {{"rank": 1, "topic": "...", "category": "urgent|difficult|easy|compromise"}}
  ],
  "flexibility_areas": ["3-5 short phrases describing where the parent has stated openness to compromise"],
  "communication_goals": ["3 short communication intentions the parent wants to hold in session"],
  "readiness_label": "one of: Needs Support, Moderately Ready, Prepared for Mediation",
  "readiness_score": integer 1-100,
  "changes_since_last": "ONLY if a previous version exists — a warm, specific summary of what has changed. Otherwise empty string."
}}

Constraints:
- Do NOT recompute readiness_score or readiness_label — use the deterministic values from the READINESS SCORES block above if provided.
- Every strength/priority/concern must be grounded in the parent's actual answers. No fabrication.
- Tone: warm, professional, evaluator-like. Never breezy, never clinical-cold.
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
    readiness_scores: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compile a 'Personal Growth Plan' from communication + readiness data.

    `readiness_scores` (optional) is the deterministic scoring bundle from
    readiness_scoring.compute_readiness() — used to inform Areas of Concern
    but never to replace the AI's own coaching guidance.
    """
    chat = _make_chat(IMPROVEMENT_SYSTEM)
    prev_block = _previous_context_block(previous, scope="improvement")
    changes_instruction = _CHANGES_INSTRUCTION if previous else ""

    scores_block = ""
    if readiness_scores:
        scores_block = f"""
=== READINESS SCORES (reference — do not restate the numbers verbatim) ===
Overall: {readiness_scores['overall']}/100 ({readiness_scores['label']})
Communication:    {readiness_scores['dimensions']['communication']['score']}/100
Trust:            {readiness_scores['dimensions']['trust']['score']}/100
Child alignment:  {readiness_scores['dimensions']['child_alignment']['score']}/100
Conflict (managed, higher = better): {readiness_scores['dimensions']['conflict']['score']}/100
"""

    prompt = f"""Generate a court-respectable Personal Growth Plan for {user_name}.

Use these inputs:

Communication self-assessment (tagged as avoider, escalator, defensive,
over_explainer, passive, or balanced):
{json.dumps(comm_style or {{}}, indent=2, default=str)}

Readiness self-ratings (1=Not yet, 2=Sometimes, 3=Often, 4=Usually, 5=Yes consistently):
- listen, past, future, separate, calm, respect
Data:
{json.dumps(readiness or {{}}, indent=2, default=str)}
{prev_block}{scores_block}
This report will be shared alongside the Co-Parenting Assessment and
Alignment Statement. It must read as a professional growth plan a
therapist or mediator would respect — never breezy, never punitive.

Return strict JSON only with these exact keys:
{{
  "executive_summary": "2-3 dignified sentences: what this growth plan is, where the parent is starting from, and how it complements the wider preparation.",
  "parent_strengths": ["3-5 short phrases naming the specific strengths visible in this data — balanced answers, high self-ratings, self-awareness itself"],
  "areas_of_concern": ["2-4 short phrases naming the growth areas the data itself points to — never judgmental, always the parent's own frame"],
  "headline": "1 warm sentence that names the 1-2 biggest growth areas without judgment",
  "focus_areas": [
    {{
      "title": "short title of the growth area (e.g. 'Pausing before responding')",
      "why_it_matters": "1 sentence on how this affects your child and your day-to-day",
      "communication_tips": ["3 SPECIFIC tips — actionable phrases or rituals"],
      "quality_of_life_tips": ["2 SPECIFIC tips for self-care, regulation, or habits"]
    }}
  ],
  "recommended_next_steps": {{
    "this_week": ["2-3 small, concrete actions to try in the next 7 days — each starts with a verb"],
    "before_mediation": ["2-3 preparation habits to establish before the next mediation session"],
    "long_term": ["1-2 growth intentions to keep in view over the next 3 months"]
  }},
  "encouragement": "1-2 warm sentences acknowledging the courage of doing this work",
  "changes_since_last": "ONLY if a previous version exists — a warm, specific note on what shifted. Otherwise empty string."
}}

Important:
- Pick 2-4 focus_areas based on the WEAKEST patterns — do not list everything.
- A 'balanced' answer or a 4-5 rating is a STRENGTH, not a growth area.
- Tips must reference real-life co-parenting scenarios (exchanges, texts, child's school events, holidays, etc).
- Avoid clichés ('be the bigger person', 'communication is key', 'practice mindfulness').
- If both inputs are mostly empty, return focus_areas=[] and put a gentle note in 'headline'.
- Tone: warm, professional, evaluator-grade.
{changes_instruction}"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)

AGREEMENT_SYSTEM = (
    "You are a co-parenting alignment specialist. You take what one parent has "
    "captured during their preparation and translate it into a CALM, NEUTRAL, "
    "CHILD-CENTERED Alignment Statement that two co-parents could bring to a "
    "mediator, therapist, or family lawyer as a starting point for discussion. "
    "This is NOT a legal document — it is a professionally-structured summary "
    "of where alignment already exists, where it is still needed, and what the "
    "parent proposes moving forward. Use first-person plural ('we', 'our') "
    "when talking about shared goals; use 'the parent' when describing that "
    "individual's proposals. Never blame, never name either parent. Keep every "
    "clause short, factual, and constructive. Output strict JSON only — no "
    "prose outside the JSON."
)


async def generate_agreement_draft(
    prep: Dict[str, Any],
    user_name: str,
    previous: Optional[Dict[str, Any]] = None,
    readiness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    chat = _make_chat(AGREEMENT_SYSTEM)
    prev_block = _previous_context_block(previous, scope="agreement")
    changes_instruction = _CHANGES_INSTRUCTION if previous else ""

    alignment_block = ""
    if readiness:
        alignment_block = f"""
=== ALIGNMENT SIGNALS (reference — do not restate the numbers) ===
Child alignment score: {readiness['dimensions']['child_alignment']['score']}/100
Overall readiness:     {readiness['overall']}/100 ({readiness['label']})
Signals: {json.dumps({k: v['reasons'] for k, v in readiness['dimensions'].items()})}
"""

    prompt = f"""Draft a court-respectable Alignment Statement for {user_name}.

CURRENT preparation data:
{json.dumps(prep, indent=2, default=str)}
{prev_block}{alignment_block}
This document will be shared with mediators and family professionals as an
evidence-based starting point for co-parenting conversations. It must read
as a dignified statement of intent — never sarcastic, never blaming, always
child-first.

Return strict JSON only with these exact keys:
{{
  "executive_summary": "2-3 sentence dignified opening — what this document is, what the parent is proposing, why the child is at the centre",
  "shared_goals": ["3-6 short statements of what we want our child to experience — pulled from child_goals"],
  "areas_of_alignment": [
    {{"area": "Communication|Child needs|Household rhythms|Other", "statement": "one neutral sentence — 'We agree that...' — max ~24 words"}}
  ],
  "areas_needing_discussion": ["3-6 short topics where clear alignment has NOT yet been captured — phrased neutrally as 'we still need to discuss X'"],
  "parent_strengths": ["3-4 short phrases naming what the parent brings to the conversation — grounded in their actual answers"],
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
  "recommended_next_steps": {{
    "this_week": ["2-3 concrete actions the parent proposes this week"],
    "before_next_conversation": ["2-3 items to prepare before the next co-parenting conversation"],
    "for_the_mediator": ["1-2 short things the parent asks the mediator to help facilitate"]
  }},
  "closing_note": "one warm sentence framing this as a living document that will grow with the conversation",
  "changes_since_last": "ONLY if a previous version exists — a short neutral list-style summary of what changed. Otherwise empty string."
}}

Important:
- Do NOT include any parenting-schedule or financial clauses, even if such data was captured.
- If a section has NO captured input, return an empty array [] (do NOT invent content).
- Do NOT add legal-sounding language.
- Keep each clause under ~24 words.
- Tone: dignified, warm, evaluator-grade.
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


# ============ Gmail Draft Assistant ============

async def draft_coparent_reply(
    *,
    original_body: str,
    original_subject: Optional[str] = None,
    original_from: Optional[str] = None,
    intent: Optional[str] = None,
    my_draft: Optional[str] = None,
) -> Dict[str, Any]:
    """Rewrite (or draft-from-scratch) a co-parenting email reply in a
    child-centered, calm, non-blaming tone.

    Args:
      original_body: the message the parent is replying to.
      original_subject / original_from: for context (optional).
      intent: what the parent wants to say, in their own words. Optional if
        they haven't written a draft yet.
      my_draft: the parent's current emotionally-loaded draft to rewrite.
        Optional; if absent we generate a fresh, factual reply.
    """
    system_prompt = (
        "You are a compassionate co-parenting communication coach. Your job is "
        "to help a separated parent respond to a message from their child's "
        "other parent in a way that is: (a) calm and non-defensive, (b) focused "
        "on the child's needs, (c) free of blame, character attacks, or "
        "sarcasm, (d) specific and logistical rather than emotional. You "
        "preserve the parent's core intent — you do NOT invent facts, agree to "
        "things they didn't agree to, or soften a legitimate boundary. If the "
        "original message contains threats, coercion, or abuse, you gently "
        "note that direct de-escalated replies may not be appropriate and "
        "point them to the Safety page and hotlines. Output strict JSON only."
    )

    intent_block = f"\n=== PARENT'S INTENT ===\n{intent.strip()}\n" if intent and intent.strip() else ""
    draft_block = f"\n=== PARENT'S CURRENT DRAFT (rewrite this) ===\n{my_draft.strip()}\n" if my_draft and my_draft.strip() else ""

    prompt = f"""Rewrite (or draft) a reply to the following co-parenting email.

=== ORIGINAL MESSAGE ===
From: {original_from or "co-parent"}
Subject: {original_subject or "(no subject)"}

{original_body.strip()[:4000]}
{intent_block}{draft_block}

Guidelines:
- Keep it short (aim for 3-8 short sentences).
- Lead with acknowledgement (one sentence), then the specifics (logistics,
  dates, boundaries), then a brief close.
- No character attacks, no "you always / you never", no sarcasm, no emojis.
- Use "our child" / the child's first name if provided in the original.
- If the original message is aggressive, model calm without capitulating.
- If safety is at risk (threats, coercion), set safety_flag=true and keep
  the reply minimal and neutral.

Return ONLY valid JSON in this exact shape:
{{
  "draft": "string — the rewritten reply body, plain text with newlines",
  "tone_notes": ["short bullet 1", "short bullet 2", "short bullet 3"],
  "safety_flag": false
}}
"""
    chat = _make_chat(system_prompt)
    response = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(response)
    draft = (data.get("draft") or "").strip()
    tone_notes = data.get("tone_notes") or []
    if not isinstance(tone_notes, list):
        tone_notes = []
    tone_notes = [str(t).strip() for t in tone_notes if str(t).strip()][:5]
    return {
        "draft": draft,
        "tone_notes": tone_notes,
        "safety_flag": bool(data.get("safety_flag", False)),
    }



# ============ Neurodivergent Child Pathway ============

_ND_REPORT_INSTRUCTIONS = {
    "needs_summary": {
        "role": (
            "You are a compassionate co-parenting educator helping a parent "
            "write a warm 'Child Needs & Strengths Summary' about their "
            "child, drawing on the 6-pillar Special Needs framework "
            "(Understanding My Child · Daily Care & Routines · Emotional & "
            "Behavioural Supports · Parent Alignment · Advocacy & Community "
            "· Long-term Wellbeing). This applies to any combination of "
            "neurodivergence, developmental disability, chronic medical, "
            "mental health, behavioural, or trauma-informed needs. This is "
            "a preparation document. It is NOT a diagnosis and NOT medical "
            "or legal advice."
        ),
        "goal": (
            "Produce a warm, plain-language 350-500 word summary that a "
            "co-parent, mediator, teacher, or therapist could read in under "
            "three minutes and immediately understand: (1) who this child is "
            "at their best (strengths first), (2) how they communicate and "
            "regulate, (3) daily care essentials, (4) supports already in "
            "place, (5) the small handful of things that reliably help."
        ),
        "structure": (
            "Use short paragraphs and gentle prose. Open with strengths. "
            "Follow the pillar structure loosely — do NOT copy the pillar "
            "labels verbatim; weave them into natural prose. Never diagnose. "
            "Refer to the child by the name the parent provided."
        ),
    },
    "two_home_plan": {
        "role": (
            "You are a compassionate co-parenting educator helping a parent "
            "draft a 'Two-Home Support & Transition Plan' — concrete, "
            "practical suggestions for keeping enough consistency between "
            "two households so their child feels understood and supported. "
            "Ground your suggestions in evidence-informed frameworks "
            "(Positive Behaviour Support, Collaborative & Proactive "
            "Solutions, Trauma-Informed Care) but use plain language, "
            "never jargon. This is NOT a legal document."
        ),
        "goal": (
            "Produce a practical plan (450-650 words) organised into the "
            "areas the parent's answers surfaced. Focus on: consistent "
            "routines, medical/therapy coordination, transitions, safety, "
            "and how the two homes communicate about the child. The goal is "
            "NOT to make both homes identical — it is enough consistency "
            "for the child to feel safe."
        ),
        "structure": (
            "Use short, scannable sections with clear headings like "
            "'Routines to keep consistent', 'Medical & therapy "
            "coordination', 'Handling transitions', 'When your child is "
            "overwhelmed', 'Safety plan', 'What we tell each other'. Use "
            "bullet lists where appropriate. Keep it child-centred, "
            "non-blaming, and specific."
        ),
    },
    "mediation_statement": {
        "role": (
            "You are a compassionate co-parenting educator helping a parent "
            "prepare a short 'Special Needs Mediation Statement' they can "
            "bring to a mediation session, family lawyer meeting, or "
            "parenting-plan discussion. This is a preparation tool. It is "
            "NOT legal advice."
        ),
        "goal": (
            "Produce a calm, dignified 300-450 word statement written in "
            "the parent's own voice ('I' / 'we'). It should state what the "
            "child needs, why consistency matters, and what the parent "
            "hopes the co-parent (and any professional) will help them "
            "protect. It must be firm but not adversarial — no blame, no "
            "character attacks. Draw on the parent's shared goals and "
            "long-term hopes to close on future vision."
        ),
        "structure": (
            "One paragraph introducing the child (name, age, brief "
            "description in the parent's language). One paragraph on what "
            "the child needs across both homes. One paragraph on what the "
            "parent hopes the parenting arrangement will preserve. Close "
            "with one sentence about the child's future — grounded in the "
            "quality-of-life vision the parent described. No headings, "
            "just flowing prose."
        ),
    },
}


def _format_nd_answers(answers: Dict[str, Any], questions: List[Dict[str, Any]]) -> str:
    """Render the answers as a readable Q&A block for the LLM."""
    lines: List[str] = []
    q_by_id = {q["id"]: q for q in questions}
    for qid, value in answers.items():
        q = q_by_id.get(qid)
        if not q:
            continue
        prompt = q["prompt"]
        if isinstance(value, list):
            v = ", ".join(str(x) for x in value if x is not None)
        elif value is None:
            v = "(no answer)"
        else:
            v = str(value)
        v = v.strip()
        if not v:
            continue
        lines.append(f"Q: {prompt}\nA: {v}\n")
    return "\n".join(lines) if lines else "(no answers yet)"


async def generate_nd_report(
    *,
    report_type: str,
    answers: Dict[str, Any],
    parent_name: Optional[str],
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a single neurodivergent-pathway report of the given type."""
    instructions = _ND_REPORT_INSTRUCTIONS.get(report_type)
    if not instructions:
        raise ValueError(f"Unknown report_type: {report_type}")

    system_prompt = (
        f"{instructions['role']} Output STRICT JSON only, no other text."
    )

    answers_block = _format_nd_answers(answers, questions)
    parent_line = f"The parent's name is {parent_name}." if parent_name else ""

    prompt = f"""{parent_line}

The parent has answered the following questions about their child. Some
answers may be short or missing — that's fine, work with what you have.

=== PARENT'S ANSWERS ===
{answers_block}

=== YOUR TASK ===
{instructions['goal']}

=== STRUCTURE ===
{instructions['structure']}

=== HARD CONSTRAINTS ===
- Do NOT invent facts the parent didn't say.
- Do NOT diagnose or use clinical language the parent didn't use themselves.
- Do NOT give medical or legal advice.
- Do NOT be preachy or use hedged corporate language.
- Refer to the child by the name the parent provided (or 'your child' if
  they didn't provide one).
- Warm, plain, specific. Written for a tired co-parent, not a committee.

Return ONLY valid JSON in this exact shape:
{{
  "content": "string — the full report body, plain text with newlines and simple markdown-style headings if the structure calls for them",
  "highlights": ["short bullet 1", "short bullet 2", "short bullet 3"]
}}
The 'highlights' field is 3-5 short bullets summarising the single most
important takeaways from this report (each ≤ 100 characters).
"""

    chat = _make_chat(system_prompt)
    response = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(response)
    # Defensive: Claude occasionally returns a list of sections instead of a
    # single {content, highlights} object — coerce back to our shape.
    if isinstance(data, list):
        # If the list looks like [{content:..., highlights:...}] use the first.
        if data and isinstance(data[0], dict) and ("content" in data[0] or "highlights" in data[0]):
            data = data[0]
        else:
            # Otherwise join list items as sections of the content.
            joined = []
            for item in data:
                if isinstance(item, dict):
                    heading = item.get("heading") or item.get("title") or ""
                    body = item.get("content") or item.get("body") or ""
                    if heading:
                        joined.append(f"## {heading}\n{body}")
                    elif body:
                        joined.append(str(body))
                else:
                    joined.append(str(item))
            data = {"content": "\n\n".join(joined), "highlights": []}
    if not isinstance(data, dict):
        data = {"content": str(data), "highlights": []}
    content = (data.get("content") or "").strip()
    highlights = data.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = []
    highlights = [str(h).strip() for h in highlights if str(h).strip()][:5]
    return {"content": content, "highlights": highlights}


# ============ Interactive AI Coach Chat (BIFF-first) ============

_COACH_SYSTEM_PROMPT = (
    "You are the SA CoParents AI Coach — a warm, grounded, non-judgemental "
    "co-parenting companion. You help a separated parent move from "
    "emotionally reactive to child-centered in the moments that matter "
    "most (right after a heated exchange, before a hard reply, when they "
    "feel stuck).\n\n"
    "Your operating principles:\n"
    "1. VALIDATE FIRST, ALWAYS. Before offering any suggestion, briefly "
    "reflect what the parent is feeling in ONE sentence. Never skip this.\n"
    "2. GROUND IN THE CHILD. Every practical suggestion must trace back to "
    "the child's emotional safety, developmental needs, and long-term "
    "wellbeing. When the parent shares their child's goals, use them.\n"
    "3. TEACH THE BIFF METHOD (Bill Eddy). When drafting a reply is on the "
    "table, structure suggestions as: Brief (2-4 short sentences), "
    "Informative (factual, dates and specifics), Friendly (courteous tone "
    "even under attack), Firm (a clear close that doesn't invite "
    "escalation). Label the BIFF pieces inline the first time you use them.\n"
    "4. NO CHARACTER ATTACKS. Never disparage the co-parent or diagnose "
    "them ('narcissist', 'unstable', etc.). Talk about behaviours and "
    "patterns, not identity.\n"
    "5. MAX 200 WORDS. Long walls of text lose parents in high emotion. "
    "Use short paragraphs, occasional bullets, and one clear next step.\n"
    "6. OFFER, DON'T DIRECT. Frame suggestions as 'you might try…' or "
    "'one option is…' — never 'you must' or 'you should'.\n"
    "7. SAFETY OVERRIDE. If the parent describes threats, coercion, "
    "stalking, or violence, drop the BIFF framing and gently name what "
    "you're seeing, then point them to the Safety page in-app, the "
    "National DV Hotline (1-800-799-7233), or 988. Set safety_flag=true.\n\n"
    "Output strict JSON in this shape:\n"
    "{\n"
    "  \"reply\": \"string — your response in Markdown. Use short paragraphs "
    "and light Markdown (bold, bullets). No headings above ##.\",\n"
    "  \"suggested_followups\": [\"short prompt 1\", \"short prompt 2\", "
    "\"short prompt 3\"],\n"
    "  \"safety_flag\": false\n"
    "}\n"
    "The suggested_followups are optional short prompts the parent might "
    "tap to continue the conversation (e.g., 'Draft the reply for me', "
    "'What if they don't respond?'). Return 2-4 of them, never more."
)


def _extract_goal_labels(goals: Any) -> List[str]:
    """Pull up to 6 child-centered goal labels from the prep snapshot."""
    if not isinstance(goals, dict):
        return []
    selected = goals.get("selected_goals") or goals.get("goals") or []
    labels = [
        g if isinstance(g, str) else (g.get("label") or g.get("id") or "")
        for g in selected
    ]
    return [str(l).strip() for l in labels if str(l).strip()][:6]


def _extract_priority_topics(priority: Any) -> List[str]:
    """Pull up to 3 top mediation-priority topic labels from the prep snapshot."""
    if not isinstance(priority, dict):
        return []
    top = priority.get("top_items") or priority.get("ranked") or []
    labels = [
        t if isinstance(t, str) else (t.get("label") or t.get("id") or "")
        for t in top[:3]
    ]
    return [str(t).strip() for t in labels if str(t).strip()]


def _coach_context_block(prep_context: Optional[Dict[str, Any]]) -> str:
    """Fold the parent's saved prep into a short context header the coach
    can reference. Skipped entirely when the parent hasn't started prep."""
    if not prep_context:
        return ""
    parts: List[str] = []

    goal_labels = _extract_goal_labels(prep_context.get("child_goals"))
    if goal_labels:
        parts.append("Child-centered goals this parent has committed to: " + "; ".join(goal_labels))

    # Foundation Statement — Reflection.jsx saves this as four labelled
    # prompt strings (child_lens / own_part / best_outcome /
    # coparent_feedback), not as a single `.text` field. Compose from
    # whichever canonical prompt keys the parent has actually filled in;
    # fall back to legacy keys so pre-2026 reflections still surface.
    reflection = prep_context.get("reflection") or {}
    if isinstance(reflection, dict):
        prompt_keys = [
            "child_lens", "own_part", "best_outcome", "coparent_feedback",
            "worry", "triggers", "calm_strategy", "appreciation", "release",
        ]
        composed_parts: List[str] = []
        for k in prompt_keys:
            v = reflection.get(k)
            if isinstance(v, str) and v.strip():
                composed_parts.append(v.strip())
        # Historical monolith field — retained as a last-resort fallback.
        if not composed_parts:
            for legacy_key in ("text", "foundation"):
                v = reflection.get(legacy_key)
                if isinstance(v, str) and v.strip():
                    composed_parts.append(v.strip())
                    break
        foundation = "\n\n".join(composed_parts)
        if foundation:
            parts.append(
                "Their Foundation Statement (excerpt): \""
                + foundation[:280] + "\""
            )

    priority_topics = _extract_priority_topics(prep_context.get("priority"))
    if priority_topics:
        parts.append("Their top mediation priorities: " + "; ".join(priority_topics))

    child_name = prep_context.get("child_name")
    if isinstance(child_name, str) and child_name.strip():
        parts.append(f"The parent refers to their child as \"{child_name.strip()[:40]}\".")

    if not parts:
        return ""
    return "\n\nPARENT CONTEXT (use lightly, do not recite verbatim):\n- " + "\n- ".join(parts)


async def generate_coach_reply(
    *,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    prep_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Multi-turn chat reply for the AI Coach.

    Args:
      user_message: what the parent just typed.
      history: prior turns as [{"role": "user"|"assistant", "content": str}, ...]
        in chronological order. The system message is prepended internally.
      prep_context: optional prep data snapshot (child_goals, reflection,
        priority) used to personalise the reply.
    """
    system_message = SAFETY_GUARDRAIL + _COACH_SYSTEM_PROMPT + _coach_context_block(prep_context)

    # Rebuild the conversation for LlmChat. `initial_messages` must include
    # the system message ourselves when we bypass the default constructor
    # path (see LlmChat.__init__).
    initial: List[Dict[str, Any]] = [{"role": "system", "content": system_message}]
    for turn in (history or [])[-20:]:  # cap history so prompts stay small
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            initial.append({"role": role, "content": content})

    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"sa-coparents-coach-{uuid.uuid4().hex[:10]}",
        system_message=system_message,
        initial_messages=initial,
    ).with_model(PROVIDER, CLAUDE_MODEL)

    response = await chat.send_message(UserMessage(text=user_message.strip()[:4000]))
    data = _extract_json(response) or {}
    reply = (data.get("reply") or "").strip()
    if not reply:
        # Bare fallback so the UI never renders an empty bubble.
        reply = (
            "I hear you. Take one slow breath before we work through this "
            "together — tell me a bit more about what just happened."
        )
    followups = data.get("suggested_followups") or []
    if not isinstance(followups, list):
        followups = []
    followups = [str(f).strip() for f in followups if str(f).strip()][:4]
    return {
        "reply": reply,
        "suggested_followups": followups,
        "safety_flag": bool(data.get("safety_flag", False)),
    }


# ============ Special Needs Assessment — v2 6-part report ============

_SN_V2_SYSTEM = (
    "You are a warm, grounded co-parenting coach writing a 6-part care plan "
    "for two parents who are preparing a mediation on their child with "
    "additional support needs. Your job is to move the parents from "
    "disagreement about the child to a coordinated plan for the child.\n\n"
    "Operating principles:\n"
    "1. LEAD WITH THE CHILD. Never define the child by limitations. The "
    "opening always names the child's strengths and interests first.\n"
    "2. DIAGNOSIS-NEUTRAL. Do not diagnose. When a concern is parent-observed "
    "but not documented, name the next professional step, not a label.\n"
    "3. COORDINATION, NOT PERFECTION. The report is about how the two homes "
    "coordinate, never about which parent is 'better'.\n"
    "4. USE THE PROVIDED NUMBERS. The 7 coordination scores are deterministic. "
    "Reference them explicitly; do not re-score.\n"
    "5. ACTIONABLE. Every gap must resolve into a specific action with an "
    "owner, an information channel, and a review date placeholder.\n"
    "6. NEVER LEGAL OR CLINICAL ADVICE. This is a planning document.\n\n"
    "Return STRICT JSON in this exact shape:\n"
    "{\n"
    "  \"child_profile\": { \"summary\": str, \"strengths\": [str,...], "
    "\"what_helps\": [str,...], \"support_needs\": [str,...] },\n"
    "  \"agreement_areas\": [ { \"title\": str, \"detail\": str } ],\n"
    "  \"coordination_gaps\": [ { \"title\": str, \"detail\": str, "
    "\"dimension\": str } ],\n"
    "  \"priorities\": { \"immediate\": [str,...], \"thirty_day\": [str,...], "
    "\"longer_term\": [str,...] },\n"
    "  \"structure_reasoning\": str,\n"
    "  \"action_plan\": [ { \"need\": str, \"action\": str, "
    "\"responsible\": str, \"channel\": str, \"review\": str } ],\n"
    "  \"disclaimer\": \"This assessment is a co-parenting and planning tool. "
    "It does not diagnose a child, determine parental fitness, replace a "
    "medical or psychological evaluation, or provide legal advice.\"\n"
    "}\n"
    "action_plan should carry 4-7 rows. immediate/thirty_day/longer_term "
    "should each carry 1-4 items."
)


def _sn_context(profile, concerns, scores, disagreement):
    parts = []
    child_name = (profile or {}).get("child_name") or "the child"
    parts.append(f"CHILD NAME: {child_name}")
    for k in ("child_age", "strengths", "what_helps", "child_communication", "child_voice"):
        v = (profile or {}).get(k)
        if v:
            parts.append(f"{k}: {str(v)[:600]}")
    for k, label in (
        ("documented_needs", "DOCUMENTED"),
        ("under_eval_needs", "UNDER EVALUATION"),
        ("parent_observed_needs", "PARENT-OBSERVED"),
    ):
        v = (concerns or {}).get(k)
        if v:
            parts.append(f"{label}: {str(v)[:400]}")
    dims = (scores or {}).get("dimensions") or {}
    dim_lines = []
    for k, d in dims.items():
        if d.get("no_signal"):
            dim_lines.append(f"  - {d['label']}: not enough answers")
        else:
            dim_lines.append(f"  - {d['label']}: {d['score']}/100 ({d['bucket']})")
    if dim_lines:
        parts.append("COORDINATION SCORES:\n" + "\n".join(dim_lines))
    structure = (scores or {}).get("structure") or {}
    if structure:
        parts.append(f"RECOMMENDED STRUCTURE: {structure.get('label')} — {structure.get('blurb','')}")
    if disagreement:
        parts.append(f"DISAGREEMENT-RESPONSE SELF-REFLECTION: {disagreement}")
    return "\n\n".join(parts)


async def generate_special_needs_report_v2(*, profile, concerns, scores, disagreement, parent_name=None):
    """Generate the 6-part Special Needs care plan.

    profile / concerns are dicts of the raw answers for those sections.
    scores is the output of special_needs_scoring.compute_scores().
    disagreement is the value from the concern_response single_select.
    """
    context = _sn_context(profile, concerns, scores, disagreement)
    prompt = (
        f"Parent preparing the report: {parent_name or 'the parent'}.\n\n"
        f"ASSESSMENT INPUT:\n{context}\n\n"
        "Write the 6-part care plan now. JSON only."
    )
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"sa-sn-v2-{uuid.uuid4().hex[:10]}",
        system_message=SAFETY_GUARDRAIL + _SN_V2_SYSTEM,
    ).with_model(PROVIDER, CLAUDE_MODEL)

    response = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(response) or {}
    # Defensive shaping so the frontend never has to handle missing keys.
    return {
        "child_profile": data.get("child_profile") or {},
        "agreement_areas": data.get("agreement_areas") or [],
        "coordination_gaps": data.get("coordination_gaps") or [],
        "priorities": data.get("priorities") or {"immediate": [], "thirty_day": [], "longer_term": []},
        "structure_reasoning": data.get("structure_reasoning") or "",
        "action_plan": data.get("action_plan") or [],
        "disclaimer": data.get("disclaimer") or (
            "This assessment is a co-parenting and planning tool. It does not diagnose a child, "
            "determine parental fitness, replace a medical or psychological evaluation, or provide legal advice."
        ),
    }
