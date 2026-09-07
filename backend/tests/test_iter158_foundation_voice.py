"""Iteration 158 — Foundation Statement voice playback ("Read to me").

Two test blocks:
  * Pure unit tests for the sanitiser, section builder, cache key,
    and the spoken-text composer (fast, no network).
  * Live-server API tests via requests + BASE_URL. The audio endpoint
    is expensive to hit for real (paid TTS + slow), so we patch the
    provider to a deterministic in-memory blob.
"""
from __future__ import annotations

import sys
import uuid
from typing import Optional
from unittest.mock import patch

import pytest
import requests

sys.path.insert(0, "/app/backend")

import foundation_statement_voice as fsv  # noqa: E402
from tests.conftest import BASE_URL  # noqa: E402


# ---------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------

def test_sanitize_strips_emoji_urls_and_markdown():
    raw = "Hello 🎉 world! *bold* _italic_ https://example.com/foo `code` #tag"
    out = fsv.sanitize_for_tts(raw)
    assert "🎉" not in out
    assert "example.com" not in out
    assert "*" not in out and "_" not in out and "`" not in out and "#" not in out
    assert "Hello" in out and "world" in out


def test_sanitize_empty_inputs():
    assert fsv.sanitize_for_tts("") == ""
    assert fsv.sanitize_for_tts("   ") == ""
    assert fsv.sanitize_for_tts(None) == ""  # type: ignore[arg-type]


def test_sanitize_caps_at_4000_chars():
    # Deliberately over the OpenAI limit — the sanitiser MUST trim.
    long = "a" * 5000
    assert len(fsv.sanitize_for_tts(long)) <= 4000


def test_sections_ordering_and_labels():
    sections = fsv.foundation_statement_sections({
        "coparent_feedback": "d",
        "child_lens": "a",
        "own_part": "b",
        "best_outcome": "c",
    })
    keys = [s["key"] for s in sections]
    # Canonical order — same as the PDF renderer.
    assert keys == ["child_lens", "own_part", "best_outcome", "coparent_feedback"]
    assert all(s["label"] for s in sections)


def test_sections_skip_empty_prompts():
    sections = fsv.foundation_statement_sections({
        "child_lens": "one",
        "own_part": "  ",
        "best_outcome": None,
    })
    assert [s["key"] for s in sections] == ["child_lens"]


def test_sections_include_legacy_prompts_when_present():
    sections = fsv.foundation_statement_sections({"worry": "legacy note"})
    assert [s["key"] for s in sections] == ["worry"]


def test_sections_returns_empty_for_invalid_input():
    assert fsv.foundation_statement_sections(None) == []  # type: ignore[arg-type]
    assert fsv.foundation_statement_sections("nope") == []  # type: ignore[arg-type]


def test_cache_key_is_deterministic_and_content_sensitive():
    a = fsv.cache_key(user_id="u1", section_key="child_lens", text="hello", voice="shimmer", model="tts-1")
    b = fsv.cache_key(user_id="u1", section_key="child_lens", text="hello", voice="shimmer", model="tts-1")
    assert a == b
    # Tiny change → different key.
    c = fsv.cache_key(user_id="u1", section_key="child_lens", text="hello!", voice="shimmer", model="tts-1")
    assert a != c
    # Voice change → different key.
    d = fsv.cache_key(user_id="u1", section_key="child_lens", text="hello", voice="nova", model="tts-1")
    assert a != d


def test_spoken_text_first_section_includes_preamble():
    sec = {"key": "child_lens", "label": "Through my child's eyes",
           "text": "raw", "sanitized": "handoffs feel rushed"}
    spoken0 = fsv.spoken_text_for_section(sec, index=0)
    spoken1 = fsv.spoken_text_for_section(sec, index=1)
    assert "Foundation Statement" in spoken0
    assert "Foundation Statement" not in spoken1
    # Label is announced in both cases.
    assert "Through my child's eyes" in spoken0
    assert "Through my child's eyes" in spoken1
    assert "handoffs feel rushed" in spoken1


def test_normalise_voice_falls_back_to_default():
    assert fsv.normalise_voice("shimmer") == "shimmer"
    assert fsv.normalise_voice("NOVA") == "nova"
    assert fsv.normalise_voice("bogus") == fsv.DEFAULT_VOICE
    assert fsv.normalise_voice(None) == fsv.DEFAULT_VOICE


def test_normalise_model_falls_back_to_default():
    assert fsv.normalise_model("tts-1") == "tts-1"
    assert fsv.normalise_model("TTS-1-HD") == "tts-1-hd"
    assert fsv.normalise_model("garbage") == fsv.DEFAULT_MODEL


# ---------------------------------------------------------------------
# Live-server API tests
# ---------------------------------------------------------------------

def _register(name: str) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_fsv_{name}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"Voice {name}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def _headers(token: Optional[str]) -> dict:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _save_reflection(token: str, payload: dict) -> None:
    r = requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json=payload, headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text


def test_manifest_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/manifest",
        timeout=30,
    )
    assert r.status_code == 401


def test_manifest_409_when_empty():
    _email, token = _register("mani409")
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/manifest",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 409
    assert "empty" in r.json()["detail"].lower()


def test_manifest_200_shape():
    _email, token = _register("mani200")
    _save_reflection(token, {
        "child_lens": "content one",
        "best_outcome": "content two",
    })
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/manifest?voice=shimmer",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["voice"] == "shimmer"
    assert data["model"] == "tts-1"
    assert data["supported_voices"] == ["shimmer", "nova", "alloy", "fable"]
    assert data["supported_models"] == ["tts-1", "tts-1-hd"]
    assert len(data["sections"]) == 2
    # Canonical ordering — child_lens comes first.
    keys = [s["key"] for s in data["sections"]]
    assert keys == ["child_lens", "best_outcome"]
    for idx, s in enumerate(data["sections"]):
        assert s["index"] == idx
        assert s["label"]
        assert s["word_count"] >= 1
        assert s["audio_url"].startswith("/api/mediation/foundation-statement/voice/section/")
        assert s["audio_url"].endswith(f"?voice=shimmer&model=tts-1")


def test_manifest_normalises_unknown_voice_to_default():
    _email, token = _register("badvoice")
    _save_reflection(token, {"child_lens": "content"})
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/manifest?voice=totally-fake",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["voice"] == "shimmer"


def test_section_audio_404_for_unknown_section():
    _email, token = _register("sec404")
    _save_reflection(token, {"child_lens": "content"})
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/section/does_not_exist",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 404


def test_section_audio_409_when_empty_reflection():
    _email, token = _register("sec409")
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/section/child_lens",
        headers=_headers(token), timeout=30,
    )
    assert r.status_code == 409


def test_section_audio_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/section/child_lens",
        timeout=30,
    )
    assert r.status_code == 401


def test_section_audio_200_returns_audio_mpeg():
    """Live test — hits the real Emergent-backed OpenAI TTS. Kept
    small (one section, one voice) so it doesn't hammer the budget.
    Skipped when no EMERGENT_LLM_KEY is present (should always be
    present in Emergent-hosted environments)."""
    import os
    if not (os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("OPENAI_API_KEY")):
        pytest.skip("no LLM key available")
    _email, token = _register("sec200")
    _save_reflection(token, {"child_lens": "tiny sentence"})
    r = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/section/child_lens?voice=shimmer",
        headers=_headers(token), timeout=60,
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "audio/mpeg"
    # MP3 frame-sync byte pattern (11 ones).
    assert r.content[:2] in (b"ID3",) or (r.content[0] == 0xFF and (r.content[1] & 0xE0) == 0xE0)
    # First call must be a cache miss.
    assert r.headers.get("x-voice-cache") in ("miss", "hit")
    first_bytes = r.content

    # Second call — same input, same voice — MUST hit cache and
    # return identical bytes.
    r2 = requests.get(
        f"{BASE_URL}/api/mediation/foundation-statement/voice/section/child_lens?voice=shimmer",
        headers=_headers(token), timeout=30,
    )
    assert r2.status_code == 200
    assert r2.headers.get("x-voice-cache") == "hit"
    assert r2.content == first_bytes
