"""Professionals intro — voice playback for the /for-professionals page.

Streams a shimmer-voiced audio explainer of what SA CoParents is and how
it fits into a mediation / attorney / therapist practice. The script is
FIXED (marketing copy, same for every visitor) so we cache one global
MP3 per (script_sha, voice, model) tuple in MongoDB and re-serve it
without re-billing.

Public endpoint — the /for-professionals page is a marketing surface,
no auth required.

Design decisions:
  * Global cache (not per-user) — the script is identical for every
    visitor. Cache key is `script_sha|voice|model|response_format`.
  * ~60-second neutral-clinical read, matching the strict guardrail
    the /for-professionals page already enforces (no marketing fluff,
    no adjudicative language, no diagnostic claims).
  * Reuses the same `emergentintegrations.llm.openai.OpenAITextToSpeech`
    wrapper as the Foundation Statement voice module, so no new SDK
    surface or key surface is introduced.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Tuple

from bson.binary import Binary
from motor.motor_asyncio import AsyncIOMotorDatabase


# The intro script. Clinical-neutral tone deliberately mirrors the
# /for-professionals page copy: what the platform IS, what it PRODUCES,
# and the four-step Align workflow — Invite, Compare, Identify
# Alignment, Guide Conversation. Kept under ~180 words so the audio is
# roughly 60 seconds at OpenAI TTS default cadence.
INTRO_SCRIPT: str = (
    "Welcome. This is a short introduction to SA CoParents "
    "for professionals. "
    "SA CoParents is an advisory preparation tool for parents who are "
    "separating or co-parenting. It produces neutral, non-diagnostic "
    "reflection artefacts — a Foundation Statement, a Co-Parenting "
    "Assessment Report, and a Child Needs Statement — that a mediator, "
    "attorney, or therapist can use to structure a session. "
    "Nothing the app produces is intended for court submission without "
    "your professional review. "
    "When you use SA CoParents Align, the workflow has four steps. "
    "First, invite. You send both parents a secure invitation link. "
    "Second, compare. Each parent completes their reflection "
    "independently, in their own time. "
    "Third, identify alignment. Align generates a side-by-side view "
    "of shared understanding and differences worth discussing. "
    "Fourth, guide conversation. You bring the Joint Alignment Report "
    "into your session and use it to focus the conversation on the "
    "child. "
    "Thank you for reviewing SA CoParents."
)

SUPPORTED_VOICES: Tuple[str, ...] = ("shimmer", "nova", "alloy", "fable")
DEFAULT_VOICE = "shimmer"

DEFAULT_MODEL = "tts-1"
SUPPORTED_MODELS: Tuple[str, ...] = ("tts-1", "tts-1-hd")

RESPONSE_FORMAT = "mp3"
MEDIA_TYPE = "audio/mpeg"

_CACHE_COLLECTION = "professionals_intro_voice_cache"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalise_voice(raw: str | None) -> str:
    v = (raw or "").strip().lower()
    return v if v in SUPPORTED_VOICES else DEFAULT_VOICE


def normalise_model(raw: str | None) -> str:
    m = (raw or "").strip().lower()
    return m if m in SUPPORTED_MODELS else DEFAULT_MODEL


def _cache_key(*, voice: str, model: str) -> str:
    payload = f"{_sha(INTRO_SCRIPT)}|{voice}|{model}|{RESPONSE_FORMAT}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _read_cached(db: AsyncIOMotorDatabase, *, key: str) -> bytes | None:
    doc = await db[_CACHE_COLLECTION].find_one({"key": key}, {"_id": 0, "audio": 1})
    if doc and isinstance(doc.get("audio"), (bytes, bytearray, Binary)):
        return bytes(doc["audio"])
    return None


async def _write_cached(
    db: AsyncIOMotorDatabase,
    *,
    key: str,
    voice: str,
    model: str,
    audio: bytes,
) -> None:
    await db[_CACHE_COLLECTION].update_one(
        {"key": key},
        {
            "$set": {
                "audio": Binary(audio),
                "voice": voice,
                "model": model,
                "format": RESPONSE_FORMAT,
                "script_sha": _sha(INTRO_SCRIPT),
                "byte_size": len(audio),
                "cached_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )


async def _openai_tts_bytes(*, text: str, voice: str, model: str) -> bytes:
    """Call OpenAI TTS via emergentintegrations. Lazy import matches
    the Foundation Statement voice module — tests that never invoke
    voice don't pay the import cost."""
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


async def get_or_generate_intro_audio(
    db: AsyncIOMotorDatabase,
    *,
    voice: str,
    model: str,
) -> Tuple[bytes, bool]:
    """Return (audio_bytes, cache_hit). Global cache — same audio
    served to every /for-professionals visitor."""
    key = _cache_key(voice=voice, model=model)
    cached = await _read_cached(db, key=key)
    if cached is not None:
        return cached, True
    audio = await _openai_tts_bytes(text=INTRO_SCRIPT, voice=voice, model=model)
    await _write_cached(db, key=key, voice=voice, model=model, audio=audio)
    return audio, False
