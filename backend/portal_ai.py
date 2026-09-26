"""Portal AI — BIFF refinement helper.

Called by `portal_routes.refine_biff_endpoint` to convert a raw
co-parent message into a BIFF (Brief, Informative, Friendly, Firm)
rewrite via Claude Sonnet through the Emergent LLM Key. Returns
`{ biff, flags, risk }`.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_models import resolve_model
from ai_service import SAFETY_GUARDRAIL, _extract_json


logger = logging.getLogger(__name__)


_BIFF_SYSTEM = (
    SAFETY_GUARDRAIL
    + "You are the BIFF Communication Coach for the SA CoParents portal. "
    "The parent will paste a draft message they are considering sending to "
    "their co-parent. Your job is to (a) detect any escalation cues in the "
    "draft, and (b) rewrite the message in strict BIFF style:\n"
    "  • Brief — one or two short sentences per idea.\n"
    "  • Informative — sticks to observable facts, times, and logistics.\n"
    "  • Friendly — opens neutrally (e.g. 'Thanks for letting me know'), "
    "closes politely.\n"
    "  • Firm — states the request or boundary without hostility, blame, "
    "or 'always/never' generalisations.\n\n"
    "Preserve any specific facts (times, dates, dollar amounts, child names) "
    "the parent supplied. Do NOT invent new facts. Do NOT add legal or "
    "clinical framing.\n\n"
    "Return STRICT JSON only, matching exactly this shape:\n"
    "{\n"
    '  "biff": "<the rewritten BIFF message, plain text, no bullets>",\n'
    '  "flags": ["<short label per escalation cue you found>", ...],\n'
    '  "risk": "Escalation Flag" | "Low Risk"\n'
    "}\n\n"
    "Set `risk` to 'Escalation Flag' if `flags` is non-empty, otherwise "
    "'Low Risk'. Typical flag labels: 'Hostile tone', 'Accusatory phrasing', "
    "'Blame language', 'High intensity', 'Personal attack', 'Passive "
    "aggressive comment', 'Demanding tone'. Never emit prose outside the "
    "JSON object."
)


# Grey-rock variant: used when the parent's own Quick Safety Check
# flagged coercion / intimidation / device-monitoring risk. Same JSON
# shape, but the rewrite guidance leans into DV-safe grey-rock replies
# — factual only, no warmth, no "thanks", no engagement with the
# coercive framing. Keeping the coach voice consistent lets the parent
# swap between the two variants without a UI re-learning cost.
_BIFF_GREYROCK_SYSTEM = (
    SAFETY_GUARDRAIL
    + "You are the BIFF Communication Coach for the SA CoParents portal. "
    "IMPORTANT SAFETY CONTEXT: The parent has indicated to us that there "
    "may be intimidation, coercion, financial control, or monitoring in "
    "their co-parenting relationship. Warm openers (e.g. 'Thanks for "
    "letting me know'), apologies, and emotion words can be used by a "
    "coercive co-parent as ammunition or as bait for further engagement. "
    "Rewrite the parent's draft in a GREY-ROCK BIFF variant:\n"
    "  • Brief — one or two short sentences, absolute minimum words.\n"
    "  • Informative — bare observable facts (times, dates, amounts, "
    "logistics). No opinions, no explanations, no justifications.\n"
    "  • Neutral (NOT friendly) — no 'thanks', no 'I appreciate', no "
    "'I understand', no emotion words at all. No sign-off other than the "
    "parent's own name if they included it. If the parent wrote a warm "
    "opener, REMOVE it.\n"
    "  • Firm — state the fact or the decision once. Do not re-explain or "
    "hedge. Do not agree to anything not already agreed. Do not ask "
    "questions that invite further contact unless a decision is required.\n"
    "  • Never repeat the co-parent's inflammatory phrases back to them.\n"
    "  • Never disclose the parent's location, plans, feelings, or the "
    "child's plans beyond the immediate custody logistics being discussed.\n\n"
    "Preserve any specific facts (times, dates, dollar amounts, child names) "
    "the parent supplied. Do NOT invent new facts. Do NOT add legal or "
    "clinical framing.\n\n"
    "Return STRICT JSON only, matching exactly this shape:\n"
    "{\n"
    '  "biff": "<the rewritten grey-rock BIFF message, plain text, no bullets>",\n'
    '  "flags": ["<short label per escalation cue you found>", ...],\n'
    '  "risk": "Escalation Flag" | "Low Risk"\n'
    "}\n\n"
    "Because the safety flag is set, `risk` should almost always be "
    "'Escalation Flag' unless the draft is already extremely neutral. "
    "Typical flag labels are the same as the regular BIFF coach. "
    "Never emit prose outside the JSON object."
)


async def refine_biff(
    raw_message: str, *, safety_flagged: bool = False
) -> Dict[str, Any]:
    """Send `raw_message` to Claude and return `{biff, flags, risk}`.

    When `safety_flagged=True` (the parent's own Quick Safety Check
    returned any risk signal), we switch to the grey-rock system
    prompt so replies stay minimal, factual, and safe to send to a
    coercive co-parent.

    Raises `Exception` on network / provider failure; caller wraps as 502.
    """
    if not raw_message or not raw_message.strip():
        return {"biff": "", "flags": [], "risk": "Neutral"}

    system_message = _BIFF_GREYROCK_SYSTEM if safety_flagged else _BIFF_SYSTEM

    # BIFF is the empathetic voice — pin to Claude for warmth.
    provider, model_name = resolve_model("claude")
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"sa-coparents-biff-{uuid.uuid4().hex[:10]}",
        system_message=system_message,
    ).with_model(provider, model_name)

    response = await chat.send_message(
        UserMessage(text=raw_message.strip()[:1000])
    )
    data = _extract_json(response) or {}
    biff = (data.get("biff") or "").strip()
    flags_raw = data.get("flags") or []
    if not isinstance(flags_raw, list):
        flags_raw = []
    flags: List[str] = [str(f).strip() for f in flags_raw if str(f).strip()][:6]
    risk = (data.get("risk") or "").strip()
    if risk not in {"Escalation Flag", "Low Risk"}:
        risk = "Escalation Flag" if flags else "Low Risk"

    if not biff:
        # Bare fallback so the caller never sees an empty rewrite.
        stripped = re.sub(r"\s+", " ", raw_message.strip())[:200]
        if safety_flagged:
            biff = f"Received. Follow-up in writing. — {stripped[:120]}"
        else:
            biff = (
                f"Thanks for the update. Regarding — {stripped} — let's keep the "
                "focus on the child's schedule and follow up in writing. Thanks."
            )

    return {"biff": biff, "flags": flags, "risk": risk}


# ---------------------------------------------------------------------------
# Guided Journey (iter220) — one-question-at-a-time chat wizard for the six
# Coparenting Journey Toolkit topics. Every topic ships with its own
# ~5-question script; Claude answers as a warm coach (grey-rock voice when
# safety_flagged=True); the client keeps the history and calls back for
# each turn.
# ---------------------------------------------------------------------------

# Ordered scripts for each topic. `save_key` tells the caller where to
# funnel the aggregated answers when the parent taps "Save & continue".
_GUIDED_SCRIPTS: Dict[str, Dict[str, Any]] = {
    "foundation": {
        "save_key": "foundation_text",
        "intro": (
            "Hi — I'm your Coparenting Coach. Let's build a Foundation "
            "Statement together in five short questions. The final result "
            "goes onto a one-page PDF you can share, print, or keep private."
        ),
        "questions": [
            "What matters most for your child right now? (age, school, health, hobbies — anything you'd want a stranger to know first)",
            "What promise do you want to hold yourself to when tempers run hot? (e.g. 'never argue in front of the kids', 'take a 24-hour pause before big decisions')",
            "How would you like communication with your co-parent to feel in six months? Give me an image, not a rule.",
            "What's one thing you deeply appreciate about your co-parent as a parent, even if the relationship is hard right now?",
            "If your child read this Foundation Statement at 18, what one line would you most want them to remember?",
        ],
    },
    "safety": {
        "save_key": "safety_ack",
        "intro": (
            "Before you build anything joint, let's do a fast wellbeing "
            "check. Three questions. Your answers stay on your device."
        ),
        "questions": [
            "Right now, do you feel physically safe in your home and in handoffs? (Yes / mostly / no — tell me anything you want to add)",
            "Has there been intimidation, coercion, control of money, or physical harm from your co-parent? You can say 'prefer not to say'.",
            "Is this device private — no one else can read what you type here? (Yes / no / unsure)",
        ],
    },
    "coparenting": {
        "save_key": "cop_assessment_note",
        "intro": (
            "Let's take a quick self-assessment of your co-parenting today. "
            "Five short reflections — no scores, just your honest read."
        ),
        "questions": [
            "How would you describe your current communication with your co-parent in one sentence?",
            "On a scale of 1-10, how consistent do the two households feel to your child?",
            "What's one recurring friction point you'd love to solve in the next 30 days?",
            "What has already improved in the last 90 days that's worth naming?",
            "If a mediator read your answers, what's the one context they'd need to understand your situation?",
        ],
    },
    "medical": {
        "save_key": "align_record",
        "category": "Medical",
        "intro": (
            "Let's capture your child's medical picture as one Align "
            "Before Agreement record. Four quick questions."
        ),
        "questions": [
            "Who is your child's primary care doctor, and where do they practise?",
            "Any current diagnoses, allergies, or medications the other parent must know?",
            "What upcoming appointments or referrals are on the calendar?",
            "Anything else a paediatrician or attorney should know to keep your child safe?",
        ],
    },
    "educational": {
        "save_key": "align_record",
        "category": "Educational",
        "intro": (
            "Let's capture the school picture as one Align Before "
            "Agreement record. Four short questions."
        ),
        "questions": [
            "What school / grade / teacher, and what's the child's current strength there?",
            "Any IEP, 504, tutor, or specialist support in place?",
            "What academic or behavioural concern is currently open?",
            "What's the ideal next-year plan — same school, transfer, home-school?",
        ],
    },
    "psychological": {
        "save_key": "align_record",
        "category": "Psychological",
        "intro": (
            "Let's capture the emotional and psychological picture as "
            "one Align Before Agreement record. Four questions."
        ),
        "questions": [
            "Is your child currently seeing a therapist, counsellor, or psychologist? Who, and how often?",
            "Any diagnoses, evaluations, or behavioural patterns worth naming?",
            "What emotional support seems to work best across both homes?",
            "What's the one thing you most want the co-parent to align on around your child's emotional wellbeing?",
        ],
    },
}


_GUIDED_COACH_WARM = (
    SAFETY_GUARDRAIL
    + "You are the Coparenting Coach for sacoparentsapp.online. You run a "
    "warm, short, one-question-at-a-time chat wizard. You have already "
    "asked the parent a scripted question; they've now answered.\n\n"
    "Your job on this turn is to:\n"
    "  1. Reflect ONE sentence of empathy or observation on what the parent "
    "     just said. Keep it grounded, not saccharine.\n"
    "  2. If the parent asked a clarifying question, answer it briefly.\n"
    "  3. Then invite them into the NEXT scripted question if one exists, "
    "     OR — if this was the final question — tell them we're done and "
    "     that the next screen will let them save the summary.\n\n"
    "NEVER give clinical or legal advice. NEVER invent facts about the "
    "child, the co-parent, or the mediator. Keep total reply under 60 words."
)


_GUIDED_COACH_GREYROCK = (
    SAFETY_GUARDRAIL
    + "You are the Coparenting Coach for sacoparentsapp.online. The parent "
    "has flagged safety concerns (coercion, intimidation, or device "
    "privacy). Run a MINIMAL, grey-rock version of the guided chat: no "
    "warmth words, no 'thanks', no emotion — just short factual acknowledgement "
    "and the next scripted question. On this turn:\n"
    "  1. Acknowledge in one short factual sentence (e.g. 'Got it.', "
    "     'Understood.', 'Noted.').\n"
    "  2. Ask the NEXT scripted question if one exists, OR say we're done "
    "     and the next screen will offer a save option.\n\n"
    "NEVER give clinical or legal advice. Keep total reply under 30 words."
)


def _resolve_next_question(topic: str, next_index: int) -> Optional[str]:
    script = _GUIDED_SCRIPTS.get(topic)
    if not script:
        return None
    qs = script["questions"]
    if next_index < 0 or next_index >= len(qs):
        return None
    return qs[next_index]


async def guided_journey_step(
    *,
    topic: str,
    step_index: int,
    parent_answer: str,
    safety_flagged: bool = False,
) -> Dict[str, Any]:
    """One turn of the guided-journey chat.

    Args:
        topic: one of the keys in _GUIDED_SCRIPTS.
        step_index: 0-based index of the question the parent JUST answered.
                    -1 signals the very first turn — the coach greets +
                    asks question 0.
        parent_answer: the parent's text reply (ignored when step_index=-1).
        safety_flagged: switch to grey-rock voice.

    Returns:
        `{coach_message, next_question, step_number, total_steps, is_final,
          save_key, category?}`
    """
    script = _GUIDED_SCRIPTS.get(topic)
    if not script:
        raise ValueError(f"Unknown guided-journey topic: {topic}")

    total_steps = len(script["questions"])

    if step_index < 0:
        # First turn — send the scripted intro + question 0, no LLM.
        return {
            "coach_message": script["intro"],
            "next_question": script["questions"][0],
            "step_number": 1,
            "total_steps": total_steps,
            "is_final": False,
            "save_key": script["save_key"],
            "category": script.get("category"),
        }

    next_index = step_index + 1
    is_final = next_index >= total_steps
    next_q = None if is_final else _resolve_next_question(topic, next_index)

    system = _GUIDED_COACH_GREYROCK if safety_flagged else _GUIDED_COACH_WARM
    last_q = script["questions"][step_index] if 0 <= step_index < total_steps else ""

    user_text = (
        f"Previous question I asked: {last_q}\n"
        f"Parent's answer: {parent_answer.strip()[:800]}\n"
        + (
            f"Next scripted question: {next_q}\n"
            "Reflect on their answer briefly, then invite them into the next question."
            if next_q
            else "This was the final question. Tell them we're done and the save panel is next."
        )
    )

    provider, model_name = resolve_model("claude")
    coach_text = ""
    try:
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"sa-coparents-guided-{topic}-{uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model(provider, model_name)
        response = await chat.send_message(UserMessage(text=user_text))
        coach_text = (response or "").strip()
    except Exception:  # pragma: no cover - degrades gracefully
        logger.warning("guided_journey_step LLM call failed", exc_info=True)
        coach_text = ""

    if not coach_text:
        # Deterministic fallback so the chat never hangs.
        if safety_flagged:
            coach_text = "Noted." + (f" Next: {next_q}" if next_q else " We're done.")
        else:
            coach_text = (
                "Thanks for sharing that. " + (f"Next: {next_q}" if next_q else "That's the last one — nice work.")
            )

    return {
        "coach_message": coach_text,
        "next_question": next_q,
        "step_number": min(next_index + 1, total_steps),
        "total_steps": total_steps,
        "is_final": is_final,
        "save_key": script["save_key"],
        "category": script.get("category"),
    }



# --------------------------------------------------------------------- #
# iter222 · Voice Note transcription (whisper-1 via Emergent LLM Key)
# --------------------------------------------------------------------- #
async def transcribe_voice_note(audio_bytes: bytes, filename: str) -> str:
    """Transcribe a short co-parent voice note into text via Whisper.

    Takes the raw bytes of the audio (browser MediaRecorder → webm
    typically) plus a filename hint so Whisper knows the container.
    Nothing is persisted to disk — the bytes stay in memory and are
    handed straight to the OpenAI SDK.

    Returns the plain text on success, raises ValueError on empty
    input, and lets any Whisper SDK exception bubble up for the
    endpoint to translate into a 502.
    """
    if not audio_bytes:
        raise ValueError("empty audio payload")

    try:
        from emergentintegrations.llm.openai import OpenAISpeechToText
    except ImportError as exc:  # pragma: no cover - integration missing
        raise RuntimeError("emergentintegrations not installed") from exc

    key = os.getenv("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    stt = OpenAISpeechToText(api_key=key)
    import io

    # OpenAISpeechToText.transcribe reads .name off the file-like to
    # pick the correct multipart content-type. Give it something
    # sensible so webm blobs from the browser stay webm.
    stream = io.BytesIO(audio_bytes)
    stream.name = filename or "voice_note.webm"

    response = await stt.transcribe(
        file=stream,
        model="whisper-1",
        response_format="json",
        language="en",
    )
    text = getattr(response, "text", "") or ""
    return text.strip()

