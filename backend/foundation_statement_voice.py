"""Foundation Statement — voice playback ("Read to me").

Generates OpenAI TTS MP3 bytes for each canonical Foundation Statement
prompt so a parent (or mediator viewing a shared statement) can listen
to the reflection instead of reading it. Accessibility win for parents
who process better by ear, and for anyone driving / on the move.

Design choices:
  * Per-section audio. We render one MP3 per non-empty prompt so the
    frontend can highlight the current section as it plays, and so a
    parent tapping "restart current section" doesn't re-generate the
    whole statement.
  * Idempotent MongoDB cache keyed on
    (user_id, section_key, text_sha, voice, model, response_format).
    Same content + same voice = cached. Tweak the text and only that
    section is re-billed on the next play.
  * Sanitisation strips emoji, URLs and stray markdown before the
    TTS call — a Foundation Statement written on a phone frequently
    has stray markdown asterisks / smart quotes / emojis that read
    weird when spoken.
  * Neutral, non-adjudicative wording only. We add a short spoken
    intro ("Here is your Foundation Statement...") so the recording
    is self-contained if forwarded.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import emoji  # type: ignore
from bson.binary import Binary
from motor.motor_asyncio import AsyncIOMotorDatabase


# The 4 voices we surface in the UI dropdown. This is intentionally a
# SUBSET of OpenAI's 9 voices — the four the user picked for this
# release. Any voice outside this set 400s so the endpoint isn't a
# free-for-all TTS proxy.
SUPPORTED_VOICES: Tuple[str, ...] = ("shimmer", "nova", "alloy", "fable")
DEFAULT_VOICE = "shimmer"

# tts-1 (standard) is snappier + cheaper than tts-1-hd. For a warm
# read of a ~500-word reflection standard quality is indistinguishable
# from HD to a parent playing it on a phone speaker.
DEFAULT_MODEL = "tts-1"
SUPPORTED_MODELS: Tuple[str, ...] = ("tts-1", "tts-1-hd")

RESPONSE_FORMAT = "mp3"
MEDIA_TYPE = "audio/mpeg"

# OpenAI TTS caps at 4096 chars per request. Foundation Statement
# sections are almost always well under this, but we guard defensively.
_MAX_TTS_CHARS = 4000


# Ordered list of the four canonical Reflection prompts + their
# spoken-aloud labels. The spoken label uses first-person framing
# ("through my child's eyes") because we're reading the parent's
# own statement aloud, so their voice ("mine") is correct.
_CANONICAL_PROMPTS: List[Tuple[str, str]] = [
    ("child_lens", "Through my child's eyes"),
    ("own_part", "My own part"),
    ("best_outcome", "My best-case outcome"),
    ("coparent_feedback", "Through my co-parent's eyes"),
]
_LEGACY_PROMPTS: List[Tuple[str, str]] = [
    ("worry", "What I'm worried about"),
    ("triggers", "My triggers"),
    ("calm_strategy", "How I stay calm"),
    ("appreciation", "What I appreciate"),
    ("release", "What I'm releasing"),
]

_CACHE_COLLECTION = "foundation_statement_voice_cache"


def sanitize_for_tts(text: str) -> str:
    """Strip emoji, URLs, and stray markdown so the reader doesn't
    read "broken heart" or "asterisk" aloud. Keep punctuation and
    everyday quotes intact so the cadence is natural."""
    if not isinstance(text, str) or not text.strip():
        return ""
    t = emoji.replace_emoji(text, replace="")
    t = re.sub(r"https?://\S+", "", t)                # drop URLs
    t = re.sub(r"`{1,3}[^`]*`{1,3}", "", t)           # code spans
    t = re.sub(r"[*_#>~|]", "", t)                    # markdown marks
    t = re.sub(r"\s+", " ", t).strip()
    return t[:_MAX_TTS_CHARS]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_key(
    *,
    user_id: str,
    section_key: str,
    text: str,
    voice: str,
    model: str,
) -> str:
    """Deterministic cache key. Includes user_id so two parents with
    identical text still get their own entries (belt-and-braces —
    text alone would be enough, but this keeps the ownership boundary
    explicit)."""
    payload = f"{user_id}|{section_key}|{_sha(text)}|{voice}|{model}|{RESPONSE_FORMAT}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def foundation_statement_sections(reflection: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return ordered [{key, label, text, sanitized}] for every prompt
    the parent actually filled in. Canonical prompts first, then any
    legacy prompts. Same ordering as the PDF renderer so the audio
    and the PDF stay in lockstep."""
    out: List[Dict[str, str]] = []
    if not isinstance(reflection, dict):
        return out
    for key, label in _CANONICAL_PROMPTS + _LEGACY_PROMPTS:
        raw = reflection.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        cleaned = sanitize_for_tts(raw)
        if not cleaned:
            continue
        out.append({
            "key": key,
            "label": label,
            "text": raw.strip(),
            "sanitized": cleaned,
        })
    return out


def spoken_text_for_section(section: Dict[str, str], *, index: int) -> str:
    """Compose the actual string sent to TTS for a section. The label
    is read aloud as an eyebrow ("Through my child's eyes.") so a
    listener can follow which prompt they're hearing. Section 0 also
    gets a short "Here is your Foundation Statement" preamble so the
    recording is self-contained when forwarded."""
    label = section["label"]
    body = section["sanitized"]
    parts: List[str] = []
    if index == 0:
        parts.append(
            "Here is your Foundation Statement. "
            "A short reflection you wrote to prepare for a co-parenting conversation."
        )
    parts.append(f"{label}.")
    parts.append(body)
    return " ".join(parts)[:_MAX_TTS_CHARS]


async def _read_cached(
    db: AsyncIOMotorDatabase,
    *,
    key: str,
) -> Optional[bytes]:
    doc = await db[_CACHE_COLLECTION].find_one({"key": key}, {"_id": 0, "audio": 1})
    if doc and isinstance(doc.get("audio"), (bytes, bytearray, Binary)):
        return bytes(doc["audio"])
    return None


async def _write_cached(
    db: AsyncIOMotorDatabase,
    *,
    key: str,
    user_id: str,
    section_key: str,
    voice: str,
    model: str,
    audio: bytes,
) -> None:
    await db[_CACHE_COLLECTION].update_one(
        {"key": key},
        {
            "$set": {
                "audio": Binary(audio),
                "user_id": user_id,
                "section_key": section_key,
                "voice": voice,
                "model": model,
                "format": RESPONSE_FORMAT,
                "byte_size": len(audio),
                "cached_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )


async def _openai_tts_bytes(
    *,
    text: str,
    voice: str,
    model: str,
) -> bytes:
    """Call OpenAI TTS via emergentintegrations. Import lazily so a
    unit test that never invokes voice doesn't pay the import cost."""
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    api_key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY is not configured on this environment.")
    tts = OpenAITextToSpeech(api_key=api_key)
    audio = await tts.generate_speech(
        text=text,
        model=model,
        voice=voice,
        response_format=RESPONSE_FORMAT,
    )
    if not isinstance(audio, (bytes, bytearray)):
        raise RuntimeError("TTS provider returned a non-bytes payload.")
    return bytes(audio)


async def get_or_generate_section_audio(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    section: Dict[str, str],
    section_index: int,
    voice: str,
    model: str,
) -> Tuple[bytes, bool]:
    """Return (audio_bytes, cache_hit). Guarantees per-section
    idempotence: two calls with identical input hit the cache."""
    spoken = spoken_text_for_section(section, index=section_index)
    key = cache_key(
        user_id=user_id,
        section_key=section["key"],
        text=spoken,
        voice=voice,
        model=model,
    )
    cached = await _read_cached(db, key=key)
    if cached is not None:
        return cached, True
    audio = await _openai_tts_bytes(text=spoken, voice=voice, model=model)
    await _write_cached(
        db,
        key=key,
        user_id=user_id,
        section_key=section["key"],
        voice=voice,
        model=model,
        audio=audio,
    )
    return audio, False


def normalise_voice(raw: Optional[str]) -> str:
    v = (raw or "").strip().lower()
    if v in SUPPORTED_VOICES:
        return v
    return DEFAULT_VOICE


def normalise_model(raw: Optional[str]) -> str:
    m = (raw or "").strip().lower()
    if m in SUPPORTED_MODELS:
        return m
    return DEFAULT_MODEL
