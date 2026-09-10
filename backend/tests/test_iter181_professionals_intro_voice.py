"""Iteration 181 — Professionals intro voice (ElevenLabs).

Covers the public /for-professionals/intro-audio endpoints:
  * `/manifest` returns the transcript + audio URL + default rachel voice.
  * `_cache_key` is deterministic across calls and provider-tagged.
  * `INTRO_SCRIPT` contains all four workflow verbs (Invite, Compare,
    Identify alignment, Guide conversation) so the audio stays in
    lockstep with the visible 4-step card grid on the same page.
  * `normalise_voice` / `normalise_model` fall back to defaults for
    unsupported input (so a query-string of `?voice=darth` never
    proxies through to the ElevenLabs endpoint).

The actual audio streaming endpoint is NOT invoked here — it would
consume real ElevenLabs credits and depends on network. The manifest +
unit-level assertions cover everything that can be verified hermetically.
"""
from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from tests.conftest import BASE_URL  # noqa: E402


def test_manifest_returns_rachel_voice_and_workflow_transcript():
    r = requests.get(f"{BASE_URL}/api/for-professionals/intro-audio/manifest", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["voice"] == "rachel"
    assert data["model"] in ("eleven_multilingual_v2", "eleven_turbo_v2_5")
    assert "rachel" in data["supported_voices"]
    # Preview URL base is exposed so the frontend chip row can build
    # per-voice preview URLs without hard-coding the path.
    assert "preview_url_base" in data
    assert data["preview_url_base"].startswith("/api/for-professionals/intro-audio/preview")
    # All four curated voices exposed to the frontend picker.
    for expected in ("rachel", "adam", "bella", "antoni"):
        assert expected in data["supported_voices"], f"{expected!r} missing from supported_voices"
    assert data["audio_url"].startswith("/api/for-professionals/intro-audio")
    transcript = data["transcript"].lower()
    # The four-step Align workflow must all be spoken in the intro,
    # matching the visible step cards on /for-professionals.
    assert "invite" in transcript
    assert "compare" in transcript
    assert "identify alignment" in transcript
    assert "guide conversation" in transcript
    # Neutrality check — the intro must never claim court admissibility.
    assert "adjudicative" not in transcript or "non-adjudicative" in transcript
    assert "court submission" in transcript  # explicit disclaimer surface


def test_preview_endpoint_serves_audio_and_is_cache_sensitive():
    """The /preview endpoint returns a short (~50KB) MP3 keyed per
    voice. Second call with the same voice must be a cache-hit."""
    r1 = requests.get(
        f"{BASE_URL}/api/for-professionals/intro-audio/preview?voice=rachel",
        timeout=30,
    )
    assert r1.status_code == 200, r1.text[:400]
    assert r1.headers.get("content-type") == "audio/mpeg"
    assert r1.headers.get("x-voice-kind") == "preview"
    body = r1.content
    assert body[:3] == b"ID3" or body[:2] == b"\xff\xfb" or len(body) > 1000, (
        f"Unexpected preview payload header/size: {body[:8]!r} / {len(body)}"
    )
    # Second call — must be a cache hit.
    r2 = requests.get(
        f"{BASE_URL}/api/for-professionals/intro-audio/preview?voice=rachel",
        timeout=15,
    )
    assert r2.status_code == 200
    assert r2.headers.get("x-voice-cache") == "hit"
    # Bad voice string falls back to the default, still 200.
    r3 = requests.get(
        f"{BASE_URL}/api/for-professionals/intro-audio/preview?voice=darth",
        timeout=15,
    )
    assert r3.status_code == 200


def test_preview_cache_key_isolates_from_full_intro():
    """The preview cache key must NOT collide with the full-intro
    cache key — swapping providers or scripts would otherwise
    resurface a stale preview payload."""
    from professionals_intro_voice import _cache_key, _preview_cache_key
    intro_key = _cache_key(voice="rachel", model="eleven_multilingual_v2")
    preview_key = _preview_cache_key(voice="rachel", model="eleven_multilingual_v2")
    assert intro_key != preview_key


def test_manifest_is_public_no_auth_required():
    # Explicit assertion — the marketing page is public.
    r = requests.get(f"{BASE_URL}/api/for-professionals/intro-audio/manifest", timeout=10)
    assert r.status_code == 200


def test_cache_key_deterministic_and_voice_sensitive():
    from professionals_intro_voice import _cache_key
    k1 = _cache_key(voice="rachel", model="eleven_multilingual_v2")
    k2 = _cache_key(voice="rachel", model="eleven_multilingual_v2")
    k3 = _cache_key(voice="adam", model="eleven_multilingual_v2")
    k4 = _cache_key(voice="rachel", model="eleven_turbo_v2_5")
    assert k1 == k2, "Same input must produce same cache key"
    assert k1 != k3, "Different voice must produce different cache key"
    assert k1 != k4, "Different model must produce different cache key"


def test_normalise_voice_falls_back_to_rachel():
    from professionals_intro_voice import normalise_voice, DEFAULT_VOICE
    assert normalise_voice("rachel") == "rachel"
    assert normalise_voice("ADAM") == "adam"
    assert normalise_voice(" bella ") == "bella"
    assert normalise_voice("antoni") == "antoni"
    # Anything outside the supported set falls back to the default.
    assert normalise_voice("darth") == DEFAULT_VOICE
    assert normalise_voice("shimmer") == DEFAULT_VOICE  # legacy OpenAI name → default
    assert normalise_voice(None) == DEFAULT_VOICE
    assert normalise_voice("") == DEFAULT_VOICE


def test_normalise_model_falls_back_to_multilingual_v2():
    from professionals_intro_voice import normalise_model, DEFAULT_MODEL
    assert normalise_model("eleven_multilingual_v2") == "eleven_multilingual_v2"
    assert normalise_model("eleven_turbo_v2_5") == "eleven_turbo_v2_5"
    assert normalise_model("tts-1") == DEFAULT_MODEL  # legacy OpenAI id → default
    assert normalise_model("eleven-9000") == DEFAULT_MODEL
    assert normalise_model(None) == DEFAULT_MODEL


def test_voice_ids_present_for_all_supported_voices():
    """Every voice string exposed to the frontend must resolve to an
    immutable ElevenLabs voice_id — otherwise a `?voice=rachel` request
    would 502 at the ElevenLabs call site."""
    from professionals_intro_voice import SUPPORTED_VOICES, VOICE_IDS
    for v in SUPPORTED_VOICES:
        assert v in VOICE_IDS, f"{v!r} listed in SUPPORTED_VOICES but has no voice_id mapping"
        assert VOICE_IDS[v], f"{v!r} has empty voice_id"


def test_elevenlabs_api_key_configured():
    """A missing key would surface as a 502 at play-time — assert it's
    present in the environment so the deploy pipeline catches misconfig
    before a professional hits Play."""
    assert os.environ.get("ELEVENLABS_API_KEY"), "ELEVENLABS_API_KEY must be set in backend/.env"
