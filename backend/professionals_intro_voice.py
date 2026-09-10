"""Professionals intro — voice playback for the /for-professionals page.

Streams an ElevenLabs-voiced audio explainer of what SA CoParents is
and how it fits into a mediation / attorney / therapist practice.
The script is FIXED (marketing copy, same for every visitor) so we
cache one global MP3 per (script_sha, voice, model, provider) tuple
in MongoDB and re-serve it without re-billing.

Public endpoint — the /for-professionals page is a marketing surface,
no auth required.

Design decisions:
  * Global cache (not per-user) — the script is identical for every
    visitor. Cache key is `sha256(script_sha|voice|model|format|provider)`.
  * ~60-second neutral-clinical read, matching the strict guardrail
    the /for-professionals page already enforces (no marketing fluff,
    no adjudicative language, no diagnostic claims).
  * ElevenLabs default library voices — free on any plan, stable IDs,
    no per-workspace cloning required.
  * ElevenLabs SDK is called synchronously inside `asyncio.to_thread`
    to avoid blocking the FastAPI event loop, matching the pattern
    used in the Foundation Statement voice module.
"""
from __future__ import annotations

import asyncio
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
# roughly 60 seconds at ElevenLabs default cadence.
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

# ElevenLabs default library voices — public, stable voice IDs that
# work on every plan (no cloning, no workspace-specific setup).
# The name -> voice_id map lets the frontend keep sending short human
# labels (?voice=rachel) while the backend resolves to the immutable
# ElevenLabs voice_id.
VOICE_IDS: dict[str, str] = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",   # calm, female — default
    "adam": "pNInz6obpgDQGcFmaJgB",     # grounded, male
    "bella": "EXAVITQu4vr4xnSDxMaL",    # soft warmth, female
    "antoni": "ErXwobaYiN019PkySvjV",   # professional, male
}
SUPPORTED_VOICES: Tuple[str, ...] = tuple(VOICE_IDS.keys())
DEFAULT_VOICE = "rachel"

# ElevenLabs models — `multilingual_v2` = highest quality, higher cost;
# `turbo_v2_5` = faster / cheaper fallback if a professional wants a
# quick preview.
DEFAULT_MODEL = "eleven_multilingual_v2"
SUPPORTED_MODELS: Tuple[str, ...] = (
    "eleven_multilingual_v2",
    "eleven_turbo_v2_5",
)

RESPONSE_FORMAT = "mp3"
MEDIA_TYPE = "audio/mpeg"
# ElevenLabs stream output format code — 44.1kHz / 128kbps mp3 is
# universally supported and produces well-compressed cached bytes for
# our ~60-second script.
_OUTPUT_FORMAT = "mp3_44100_128"

_PROVIDER = "elevenlabs"
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
    # `_PROVIDER` is included so a future provider swap invalidates the
    # cache automatically without a manual purge.
    payload = f"{_sha(INTRO_SCRIPT)}|{voice}|{model}|{RESPONSE_FORMAT}|{_PROVIDER}"
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
                "provider": _PROVIDER,
                "format": RESPONSE_FORMAT,
                "script_sha": _sha(INTRO_SCRIPT),
                "byte_size": len(audio),
                "cached_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )


def _elevenlabs_tts_bytes_sync(*, text: str, voice_id: str, model_id: str) -> bytes:
    """Blocking ElevenLabs call. Lazy-imported inside the function so
    tests that never invoke voice don't pay the import cost."""
    from elevenlabs.client import ElevenLabs

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured on this environment.")
    client = ElevenLabs(api_key=api_key)
    audio_iter = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=_OUTPUT_FORMAT,
    )
    buf = bytearray()
    for chunk in audio_iter:
        if chunk:
            buf.extend(chunk)
    if not buf:
        raise RuntimeError("ElevenLabs returned an empty audio payload.")
    return bytes(buf)


async def _elevenlabs_tts_bytes(*, text: str, voice: str, model: str) -> bytes:
    voice_id = VOICE_IDS.get(voice) or VOICE_IDS[DEFAULT_VOICE]
    return await asyncio.to_thread(
        _elevenlabs_tts_bytes_sync,
        text=text,
        voice_id=voice_id,
        model_id=model,
    )


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
    audio = await _elevenlabs_tts_bytes(text=INTRO_SCRIPT, voice=voice, model=model)
    await _write_cached(db, key=key, voice=voice, model=model, audio=audio)
    return audio, False
