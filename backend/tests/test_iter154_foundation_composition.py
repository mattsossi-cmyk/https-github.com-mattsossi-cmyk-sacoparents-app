"""Iteration 154 — regression: the AI coach context block must
compose the Foundation Statement from the four canonical Reflection
prompts, NOT from a non-existent `.text`/`.foundation` field.

Bug: `_coach_context_block` was reading `reflection.get("text")`.
The `Reflection.jsx` UI saves prompt strings under keys
`child_lens` / `own_part` / `best_outcome` / `coparent_feedback`,
so `.text` was ALWAYS empty and the coach never saw the parent's
Foundation Statement as context.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/app/backend")

from ai_service import _coach_context_block


def test_coach_reads_foundation_from_canonical_prompt_keys() -> None:
    """Canonical prompt keys → Foundation Statement excerpt appears
    in the coach context block."""
    ctx = _coach_context_block({
        "reflection": {
            "child_lens": "My child would say the last week felt loud.",
            "own_part": "I raised my voice when I should have paused.",
            "best_outcome": "Calmer handovers in the next six months.",
            "coparent_feedback": "Their other parent would say I over-explained.",
        },
    })
    assert "Foundation Statement" in ctx
    assert "loud" in ctx  # from child_lens
    assert "raised my voice" in ctx  # from own_part
    assert "Calmer handovers" in ctx  # from best_outcome


def test_coach_reads_foundation_from_legacy_keys() -> None:
    """Legacy prompt keys still surface for pre-2026 reflections."""
    ctx = _coach_context_block({
        "reflection": {
            "worry": "I'm anxious about the mediation next Thursday.",
            "calm_strategy": "Breathing exercise every morning.",
        },
    })
    assert "Foundation Statement" in ctx
    assert "anxious" in ctx


def test_coach_reads_foundation_from_monolith_fallback() -> None:
    """A hypothetical old row with a monolithic `text` field still works."""
    ctx = _coach_context_block({
        "reflection": {"text": "Legacy monolithic foundation string."},
    })
    assert "Foundation Statement" in ctx
    assert "Legacy monolithic" in ctx


def test_coach_omits_foundation_when_all_prompts_empty() -> None:
    """No prompts filled in → coach context has NO Foundation Statement line."""
    ctx = _coach_context_block({
        "reflection": {
            "child_lens": "",
            "own_part": "   ",
            "best_outcome": "",
            "coparent_feedback": "",
            "private": True,
        },
    })
    assert "Foundation Statement" not in ctx


def test_coach_composes_multiple_prompts_into_one_excerpt() -> None:
    """The composed excerpt must include content from more than one
    prompt when the parent has filled in multiple."""
    ctx = _coach_context_block({
        "reflection": {
            "child_lens": "AAA prompt one content.",
            "best_outcome": "BBB prompt three content.",
        },
    })
    assert "AAA" in ctx
    assert "BBB" in ctx


def test_coach_excerpt_is_length_capped() -> None:
    """The Foundation excerpt is capped at 280 chars to keep the
    coach prompt tight — a very long reflection must be truncated."""
    long_text = "x" * 1000
    ctx = _coach_context_block({
        "reflection": {"child_lens": long_text},
    })
    # The 280-char cap is enforced; the full 1000-char string should not appear.
    assert long_text not in ctx
    assert "xxxxx" in ctx
