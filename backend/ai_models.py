"""Shared AI-model configuration for every LLM surface in the app.

App-wide default is GPT (`gpt-5.4` via the Emergent LLM Key) with
Claude Sonnet 4.5 as the on-demand fallback. Individual callers can
override per-request by passing a preference string ("gpt" or
"claude") — usually sourced from a `?model=` query parameter — so
users can switch tone on any surface that exposes the toggle.

Design notes
------------
* `EMERGENT_LLM_KEY` is a single universal key that works with both
  providers, so no per-provider key routing is needed at this layer.
* `AI_PRIMARY_MODEL` env var flips the *default* used when no
  per-request preference is given. Set to `claude` to revert.
* This module is intentionally tiny — resolve model, done. All prompt
  building, retry, JSON extraction stays in the callers.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

# ------- Model catalogue (kept in one place so bumps are one line) -------
GPT_PROVIDER = "openai"
GPT_MODEL = "gpt-5.4"  # Emergent LLM playbook recommended default

CLAUDE_PROVIDER = "anthropic"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


def _normalise(pref: Optional[str]) -> str:
    """Return `gpt` or `claude` — anything else falls back to primary."""
    if not pref:
        return _primary_env()
    p = pref.strip().lower()
    if p in ("gpt", "openai", "chatgpt"):
        return "gpt"
    if p in ("claude", "anthropic"):
        return "claude"
    return _primary_env()


def _primary_env() -> str:
    return (os.environ.get("AI_PRIMARY_MODEL", "gpt") or "gpt").strip().lower()


def resolve_model(preference: Optional[str] = None) -> Tuple[str, str]:
    """Return the `(provider, model_name)` tuple to use for this call.

    * `preference=None`     → app-wide primary (env-controlled)
    * `preference="gpt"`    → force GPT for this call
    * `preference="claude"` → force Claude for this call
    """
    choice = _normalise(preference)
    if choice == "claude":
        return CLAUDE_PROVIDER, CLAUDE_MODEL
    return GPT_PROVIDER, GPT_MODEL


def resolve_primary() -> Tuple[str, str]:
    """Shorthand for `resolve_model(None)` — always returns the
    current app-wide primary."""
    return resolve_model(None)
