"""AI Personal Coach for Deep Dive sections.

Given a single section's questions + the parent's answers, ask Claude to
produce a short, neutral, four-block coach card:

    doing_well[]         — 1-3 short bullets recognising strengths
    coordination_gaps[]  — 1-3 short bullets naming friction *neutrally*
    next_steps[]         — 1-3 concrete, actionable suggestions
    resources[]          — 1-3 optional pointers ("Ask school for…" / "Talk
                           to your pharmacist about…" / "See our Communication
                           Style module"). Kept generic — no third-party URLs.

The result is cached inside the assessment document keyed by section + a
short hash of the answers, so revisiting a section with unchanged answers
doesn't cost an LLM round-trip. Any LLM failure returns a graceful null so
the caller can fall back to a "Try again later" nudge without breaking the
assessment flow.

Constraints (strict — mirror `ai_summary.py`):
  * Neutral, parent-attributed tone. Never take sides.
  * Non-diagnostic, non-adjudicative, no medical/legal advice.
  * Plain language. ~10-18 words per bullet.
  * Do not fabricate — only use what is in the parent's answers.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage


logger = logging.getLogger(__name__)

_MODEL_PROVIDER = "anthropic"
_MODEL_NAME = "claude-sonnet-4-5-20250929"

# Keys we accept back from the model. Anything else is dropped.
_COACH_KEYS = ("doing_well", "coordination_gaps", "next_steps", "resources")


def _system_message(product_label: str) -> str:
    return (
        "You are a neutral co-parenting coach who reads a single section "
        f"of a parent's {product_label} answers and writes a short, "
        "encouraging coach card. Rules you MUST follow:\n"
        "  1. Neutral, parent-attributed tone. Never take sides.\n"
        "  2. Non-diagnostic. Never suggest diagnoses or treatments.\n"
        "  3. Non-adjudicative. Never suggest one parent is right or wrong.\n"
        "  4. No medical, legal, or psychological advice. Recommend the parent talk to a qualified professional when relevant.\n"
        "  5. Plain language. Roughly 10-18 words per bullet.\n"
        "  6. Only use what is in the parent's answers. Do not fabricate.\n"
        "  7. Frame gaps as *coordination opportunities*, not personal failings.\n"
        "  8. Return STRICT JSON only — no prose before or after — with EXACTLY these keys: "
        '"doing_well", "coordination_gaps", "next_steps", "resources".\n'
        "  9. Each value is a JSON array of 0-3 short strings. Never null. Empty array is fine.\n"
        " 10. Resources are generic pointers (e.g. \"Ask the school counsellor for an ARD meeting\"). "
        "Never link to third-party sites. If our app has a matching module, mention it plainly (e.g. "
        '"See the Communication Style module in your dashboard").'
    )


def _snapshot_for_prompt(section: Dict[str, Any], responses: Dict[str, Any]) -> Dict[str, Any]:
    """Compact JSON to send to the model: item prompt + type + parent answer."""
    items = section.get("items") or []
    if isinstance(items, dict):
        pairs = list(items.items())
    else:
        pairs = [(it.get("id"), it) for it in items]
    entries: List[Dict[str, Any]] = []
    for item_id, item in pairs:
        if not item_id:
            continue
        key = f"{section.get('id')}_{item_id}"
        answer = responses.get(key)
        if answer is None or answer == "":
            continue  # skip unanswered — model doesn't need to guess
        entries.append({
            "prompt": item.get("prompt") or item.get("label") or item_id,
            "type":   item.get("type"),
            "answer": answer,
        })
    return {
        "section_id":     section.get("id"),
        "section_number": section.get("number"),
        "section_name":   section.get("name"),
        "purpose":        section.get("purpose"),
        "answers":        entries,
    }


def _answer_hash(section_id: str, responses: Dict[str, Any]) -> str:
    """Stable short hash of the answers keyed to this section only."""
    prefix = f"{section_id}_"
    scoped = {k: responses[k] for k in sorted(responses.keys()) if k.startswith(prefix)}
    payload = json.dumps(scoped, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _sanitize_output(raw: Any) -> Dict[str, List[str]]:
    """Coerce the model's response into the exact 4-list shape we expose."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            # Sometimes the model wraps JSON in ```json fences — strip them
            # and retry once.
            stripped = raw.strip().lstrip("`json").rstrip("`").strip()
            try:
                raw = json.loads(stripped)
            except Exception:  # noqa: BLE001
                return {k: [] for k in _COACH_KEYS}
    if not isinstance(raw, dict):
        return {k: [] for k in _COACH_KEYS}
    out: Dict[str, List[str]] = {}
    for k in _COACH_KEYS:
        vals = raw.get(k) or []
        if isinstance(vals, str):
            vals = [vals]
        cleaned: List[str] = []
        for v in vals:
            if not isinstance(v, (str, int, float)):
                continue
            s = str(v).strip()
            if not s:
                continue
            # Hard cap so a chatty model can't blow up the UI.
            if len(s) > 240:
                s = s[:237].rsplit(" ", 1)[0].rstrip(",.:;") + "…"
            cleaned.append(s)
            if len(cleaned) >= 3:
                break
        out[k] = cleaned
    return out


async def generate_section_coach(*, product_label: str,
                                 section: Dict[str, Any],
                                 responses: Dict[str, Any]) -> Optional[Dict[str, List[str]]]:
    """Return a 4-list coach card for one section, or None on failure.

    Never raises: the caller falls back to a "try again later" nudge if the
    LLM call fails so the assessment flow stays reliable.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY not configured — skipping section coach")
        return None
    snapshot = _snapshot_for_prompt(section, responses or {})
    if not snapshot["answers"]:
        # Nothing answered yet — no coaching to give.
        return {k: [] for k in _COACH_KEYS}
    prompt = (
        f"Product: {product_label}\n"
        "Section JSON follows. Produce the 4-list coach card described in "
        "your system message. Return ONLY the JSON object.\n\n"
        f"{json.dumps(snapshot, ensure_ascii=False)}"
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"section-coach-{uuid.uuid4().hex[:10]}",
            system_message=_system_message(product_label),
        ).with_model(_MODEL_PROVIDER, _MODEL_NAME)
        text = await chat.send_message(UserMessage(text=prompt))
        result = _sanitize_output(text)
        # If the model returned all four empty lists AND we had answers to
        # summarise, that's almost certainly a shape failure — treat as None
        # so the caller can retry.
        if all(not result[k] for k in _COACH_KEYS):
            logger.warning("Section coach returned empty payload for section %s", section.get("id"))
            return None
        return result
    except Exception as e:  # noqa: BLE001
        logger.warning("Section coach generation failed for section %s: %s", section.get("id"), e)
        return None


# ---------------------------------------------------------------------------
# Route-level helper — the three pathway routers all mount an identical
# `POST /section/{section_id}/coach` endpoint. This helper does the heavy
# lifting: find the section spec, load answers, hit the LLM (or serve a
# cached card if answers haven't changed), and shape the response.
# ---------------------------------------------------------------------------
COACH_CACHE_COLLECTION = "deep_dive_section_coach_cards"


async def load_or_generate_section_coach(
    *, db, user_id: str, sections_spec: List[Dict[str, Any]],
    product_label: str, pathway_id: str, section_id: str,
    responses: Dict[str, Any], force: bool = False,
) -> Dict[str, Any]:
    """End-to-end handler used by the three pathway route wrappers.

    Returns a dict of shape::

        {"ok": True, "section_id": ..., "coach": {...}, "cached": bool,
         "answer_hash": str, "generated_at": ISO8601, "no_answers": bool}

    On LLM failure, "coach" is None and the caller returns 503 with a
    friendly error string.
    """
    section = next((s for s in sections_spec if s.get("id") == section_id), None)
    if not section:
        raise ValueError(f"Unknown section: {section_id}")

    answer_hash = _answer_hash(section_id, responses or {})
    cache_key = {
        "user_id": user_id,
        "pathway_id": pathway_id,
        "section_id": section_id,
    }
    if not force:
        cached = await db[COACH_CACHE_COLLECTION].find_one(cache_key, {"_id": 0})
        if cached and cached.get("answer_hash") == answer_hash:
            return {
                "ok": True,
                "section_id": section_id,
                "coach": cached.get("coach"),
                "cached": True,
                "answer_hash": answer_hash,
                "generated_at": cached.get("generated_at"),
                "no_answers": not any(
                    k.startswith(f"{section_id}_") and (responses or {}).get(k) not in (None, "")
                    for k in (responses or {})
                ),
            }

    coach = await generate_section_coach(
        product_label=product_label,
        section=section,
        responses=responses or {},
    )
    if coach is None:
        return {
            "ok": False,
            "section_id": section_id,
            "coach": None,
            "cached": False,
            "answer_hash": answer_hash,
            "generated_at": None,
            "no_answers": False,
        }

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    no_answers = all(not v for v in coach.values())
    # Persist the freshly-baked card so a repeat visit is free.
    await db[COACH_CACHE_COLLECTION].update_one(
        cache_key,
        {"$set": {
            **cache_key,
            "answer_hash": answer_hash,
            "coach": coach,
            "generated_at": now,
            "product_label": product_label,
        }},
        upsert=True,
    )
    return {
        "ok": True,
        "section_id": section_id,
        "coach": coach,
        "cached": False,
        "answer_hash": answer_hash,
        "generated_at": now,
        "no_answers": no_answers,
    }
