"""Iteration 156 — shared AI-model config + Claude→GPT default flip.

Covers:
  * `ai_models.resolve_model` returns the right (provider, model) tuple
    for every combination of env var + per-call preference.
  * `AI_PRIMARY_MODEL` env var flips the app-wide default.
  * The `/api/coach/sessions/{id}/message` endpoint accepts an optional
    `model` field and passes it through to `generate_coach_reply`.

The end-to-end LLM call (live GPT reply) is proven via the coach
smoke test in the previous session and not repeated here — this
suite is deterministic and doesn't burn tokens.
"""
from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
# Load backend/.env so JWT_SECRET and friends are available when we
# import `coach_routes` → `auth` in the endpoint test below.
load_dotenv("/app/backend/.env", override=False)


def _reload_models(env_value: str | None):
    """Reload `ai_models` under a specific env var, so the module
    picks up the new `AI_PRIMARY_MODEL` at resolve-time."""
    if env_value is None:
        os.environ.pop("AI_PRIMARY_MODEL", None)
    else:
        os.environ["AI_PRIMARY_MODEL"] = env_value
    if "ai_models" in sys.modules:
        return importlib.reload(sys.modules["ai_models"])
    import ai_models
    return ai_models


# ---------------------------------------------------------------------
# Pure config tests
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "env_value,preference,expected_provider,expected_model_kind",
    [
        # Default env → GPT primary.
        (None,     None,    "openai",    "gpt"),
        ("gpt",    None,    "openai",    "gpt"),
        ("openai", None,    "openai",    "gpt"),
        ("claude", None,    "anthropic", "claude"),
        # Per-call preference overrides env.
        ("gpt",    "claude","anthropic", "claude"),
        ("claude", "gpt",   "openai",    "gpt"),
        # Unknown preference falls back to env-derived primary.
        ("gpt",    "rubbish","openai",   "gpt"),
        ("claude", "rubbish","anthropic","claude"),
    ],
)
def test_resolve_model_matrix(env_value, preference, expected_provider, expected_model_kind):
    mod = _reload_models(env_value)
    provider, model_name = mod.resolve_model(preference)
    assert provider == expected_provider
    if expected_model_kind == "gpt":
        assert model_name.startswith("gpt-"), model_name
    else:
        assert model_name.startswith("claude-"), model_name


def test_resolve_primary_matches_resolve_model_none():
    mod = _reload_models("gpt")
    assert mod.resolve_primary() == mod.resolve_model(None)


def test_default_gpt_model_matches_playbook_recommendation():
    """The playbook explicitly recommends `gpt-5.4` as the default
    GPT model. Guard against silent bumps."""
    mod = _reload_models(None)
    provider, model_name = mod.resolve_model(None)
    assert (provider, model_name) == ("openai", "gpt-5.4")


def test_fallback_claude_model_pinned():
    mod = _reload_models(None)
    provider, model_name = mod.resolve_model("claude")
    assert provider == "anthropic"
    assert model_name == "claude-sonnet-4-5-20250929"


# ---------------------------------------------------------------------
# Coach endpoint passes model preference through
# ---------------------------------------------------------------------

def test_coach_send_passes_model_preference_through():
    """The `/api/coach/sessions/{id}/message` route must forward the
    `model` field on the body straight to `generate_coach_reply`.
    Uses a fresh event loop so we don't collide with the shared
    loop other test files rely on."""
    # Reload after resetting so no lingering env from earlier tests.
    _reload_models("gpt")

    from coach_routes import send_message, SendMessageBody

    # Fake user + minimal fake db
    class _User:
        user_id = "user_x"

    class _SessionColl:
        async def find_one(self, q, proj=None):
            return {
                "session_id": q["session_id"],
                "user_id": q["user_id"],
                "title": "New conversation",
                "message_count": 0,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "safety_flag": False,
            }

        def find(self, q, proj=None):
            class _Cur:
                async def to_list(self, n): return []
                def sort(self, *_a, **_k): return self
                def limit(self, *_a, **_k): return self
            return _Cur()

        async def insert_one(self, d): pass
        async def update_one(self, q, u): pass
        async def delete_one(self, q): pass

    class _NoopColl:
        async def find_one(self, q, proj=None): return None
        def find(self, q, proj=None):
            class _Cur:
                async def to_list(self, n): return []
                def sort(self, *_a, **_k): return self
                def limit(self, *_a, **_k): return self
            return _Cur()
        async def insert_one(self, d): pass
        async def update_one(self, q, u): pass
        async def delete_one(self, q): pass

    class _DB:
        coach_sessions = _SessionColl()
        coach_messages = _NoopColl()
        prep_data = _NoopColl()

    class _App:
        class state:  # noqa: N801 — mimicking FastAPI's app.state
            db = _DB()

    class _Req:
        app = _App()

    import asyncio

    async def _run() -> None:
        with patch(
            "ai_service.generate_coach_reply",
            new=AsyncMock(return_value={
                "reply": "OK",
                "suggested_followups": [],
                "safety_flag": False,
            }),
        ) as mock_reply:
            await send_message(
                session_id="coach_abc",
                body=SendMessageBody(content="Hello", model="claude"),
                request=_Req(),
                current=_User(),
            )
            kwargs = mock_reply.call_args.kwargs
            assert kwargs["model_preference"] == "claude"
            assert kwargs["user_message"] == "Hello"

        with patch(
            "ai_service.generate_coach_reply",
            new=AsyncMock(return_value={
                "reply": "OK",
                "suggested_followups": [],
                "safety_flag": False,
            }),
        ) as mock_reply:
            await send_message(
                session_id="coach_abc",
                body=SendMessageBody(content="Hello again"),
                request=_Req(),
                current=_User(),
            )
            assert mock_reply.call_args.kwargs["model_preference"] is None

    # New loop, cleanly closed — doesn't disturb the default loop
    # other test files create in module-scoped fixtures.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()
