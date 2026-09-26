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
from typing import Any, Dict, List

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
