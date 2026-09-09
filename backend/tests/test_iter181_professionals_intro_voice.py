"""Iteration 181 — Professionals intro voice.

Covers the public /for-professionals/intro-audio endpoints:
  * `/manifest` returns the transcript + audio URL + default shimmer voice.
  * `_cache_key` is deterministic across calls.
  * `INTRO_SCRIPT` contains all four workflow verbs (Invite, Compare,
    Identify alignment, Guide conversation) so the audio stays in
    lockstep with the visible 4-step card grid on the same page.
  * `normalise_voice` / `normalise_model` fall back to defaults for
    unsupported input (so a query-string of `?voice=darth` never
    proxies through to the OpenAI TTS endpoint).

The actual audio streaming endpoint is NOT invoked here — it would
consume real OpenAI TTS credits and depends on network. The manifest +
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


def test_manifest_returns_shimmer_voice_and_workflow_transcript():
    r = requests.get(f"{BASE_URL}/api/for-professionals/intro-audio/manifest", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["voice"] == "shimmer"
    assert data["model"] in ("tts-1", "tts-1-hd")
    assert "shimmer" in data["supported_voices"]
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


def test_manifest_is_public_no_auth_required():
    # Explicit assertion — the marketing page is public.
    r = requests.get(f"{BASE_URL}/api/for-professionals/intro-audio/manifest", timeout=10)
    assert r.status_code == 200


def test_cache_key_deterministic_and_voice_sensitive():
    from professionals_intro_voice import _cache_key
    k1 = _cache_key(voice="shimmer", model="tts-1")
    k2 = _cache_key(voice="shimmer", model="tts-1")
    k3 = _cache_key(voice="nova", model="tts-1")
    k4 = _cache_key(voice="shimmer", model="tts-1-hd")
    assert k1 == k2, "Same input must produce same cache key"
    assert k1 != k3, "Different voice must produce different cache key"
    assert k1 != k4, "Different model must produce different cache key"


def test_normalise_voice_falls_back_to_shimmer():
    from professionals_intro_voice import normalise_voice, DEFAULT_VOICE
    assert normalise_voice("shimmer") == "shimmer"
    assert normalise_voice("NOVA") == "nova"
    assert normalise_voice(" fable ") == "fable"
    # Anything outside the supported set falls back to the default.
    assert normalise_voice("darth") == DEFAULT_VOICE
    assert normalise_voice(None) == DEFAULT_VOICE
    assert normalise_voice("") == DEFAULT_VOICE


def test_normalise_model_falls_back_to_tts1():
    from professionals_intro_voice import normalise_model, DEFAULT_MODEL
    assert normalise_model("tts-1") == "tts-1"
    assert normalise_model("tts-1-hd") == "tts-1-hd"
    assert normalise_model("tts-9000") == DEFAULT_MODEL
    assert normalise_model(None) == DEFAULT_MODEL
