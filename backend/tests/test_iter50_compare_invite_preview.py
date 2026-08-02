"""Iteration 50 — Alignment Preview in the Compare-Invite email.

Verifies:
1. `send_compare_invite` renders the preview badge in both HTML and plain
   text when `aligned_pct` is provided, and stays quiet when it isn't.
2. Values are clamped to [0, 100] and floats are coerced to int.
3. `build_comparison` returns a well-formed `summary.aligned_pct` for
   identical answers (≥90) and for empty answers (0), which is the
   value `link_partner` teasers into the invite email.
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, "/app/backend")

import email_service  # noqa: E402
from deep_dive_comparison_core import build_comparison_from_spec  # noqa: E402


# ---------------------------------------------------------------------------
# UNIT: send_compare_invite renders the preview correctly
# ---------------------------------------------------------------------------
class TestSendCompareInvitePreview:
    def _capture(self):
        """Patch the low-level _send so we can inspect the rendered body."""
        return patch.object(email_service, "_send")

    def test_without_pct_no_preview_line(self):
        with self._capture() as m:
            email_service.send_compare_invite(
                to_email="p2@example.com",
                link_url="https://example.com/hub",
                inviter_name="Sam",
                product_label="Checkin - Psychological Needs",
            )
        assert m.call_count == 1
        kwargs = m.call_args.kwargs
        assert "A quick preview" not in kwargs["html"]
        assert "already agree on about" not in kwargs["text"]

    def test_with_pct_renders_badge(self):
        with self._capture() as m:
            email_service.send_compare_invite(
                to_email="p2@example.com",
                link_url="https://example.com/hub",
                inviter_name="Sam",
                product_label="Checkin - Medical Needs",
                aligned_pct=68,
            )
        kwargs = m.call_args.kwargs
        assert "A quick preview" in kwargs["html"]
        assert "68% of your answers" in kwargs["html"]
        assert "You already agree on about 68% of your answers." in kwargs["html"]
        # Plain text version too
        assert "68%" in kwargs["text"]
        # Explicit "no items leak" reassurance
        assert "no items are shared until you consent" in kwargs["html"].lower()

    def test_pct_zero_still_renders_badge(self):
        with self._capture() as m:
            email_service.send_compare_invite(
                to_email="p2@example.com",
                link_url="https://example.com/hub",
                aligned_pct=0,
            )
        kwargs = m.call_args.kwargs
        assert "0% of your answers" in kwargs["html"]

    @pytest.mark.parametrize("raw,expected", [
        (150, 100),   # clamp high
        (-5, 0),      # clamp low
        (73.4, 73),   # float -> int
    ])
    def test_pct_normalization(self, raw, expected):
        with self._capture() as m:
            email_service.send_compare_invite(
                to_email="p2@example.com",
                link_url="https://example.com/hub",
                aligned_pct=raw,
            )
        kwargs = m.call_args.kwargs
        assert f"{expected}% of your answers" in kwargs["html"], (
            f"raw={raw} should render as {expected}% — got: {kwargs['html'][:400]}"
        )


# ---------------------------------------------------------------------------
# UNIT: build_comparison summary.aligned_pct — the number `link_partner`
# passes into the email. Guarantees the preview will be a sensible integer.
# ---------------------------------------------------------------------------
class TestPreviewPctSource:
    @pytest.fixture(params=["edu", "psych", "med"])
    def spec_and_version(self, request):
        if request.param == "edu":
            from edu_deep_questions import DEEP_DIVE_SECTIONS as S, DEEP_DIVE_VERSION as V
        elif request.param == "psych":
            from psych_deep_questions import DEEP_DIVE_SECTIONS as S, DEEP_DIVE_VERSION as V
        else:
            from med_deep_questions import DEEP_DIVE_SECTIONS as S, DEEP_DIVE_VERSION as V
        return S, V

    def _all_matching_answers(self, sections):
        """Build identical answer dicts for both parents. `items` may be a
        list-of-dicts (with `id` on each item) or a dict keyed by item id."""
        a = {}
        for s in sections:
            raw_items = s.get("items") or []
            if isinstance(raw_items, dict):
                pairs = list(raw_items.items())            # (item_id, item)
            else:
                pairs = [(it.get("id"), it) for it in raw_items]
            for item_id, item in pairs:
                if not item_id:
                    continue
                key = f"{s['id']}_{item_id}"
                if item.get("type") == "likert":
                    a[key] = 5
                elif item.get("type") == "single":
                    opts = item.get("options") or []
                    if opts:
                        a[key] = opts[0]
        return a

    def test_identical_answers_yield_high_pct(self, spec_and_version):
        sections, version = spec_and_version
        ans = self._all_matching_answers(sections)
        result = build_comparison_from_spec(
            sections_spec=sections,
            assessment_version=version,
            product_name="X",
            parent_a_name="A",
            parent_b_name="B",
            a_answers=ans,
            b_answers=ans,
        )
        pct = result.get("summary", {}).get("aligned_pct")
        assert isinstance(pct, int)
        assert 0 <= pct <= 100
        # Identical inputs → high alignment (very likely ≥90 across pathways).
        assert pct >= 90

    def test_empty_answers_return_zero_pct(self, spec_and_version):
        sections, version = spec_and_version
        result = build_comparison_from_spec(
            sections_spec=sections,
            assessment_version=version,
            product_name="X",
            parent_a_name="A",
            parent_b_name="B",
            a_answers={},
            b_answers={},
        )
        pct = result.get("summary", {}).get("aligned_pct")
        assert isinstance(pct, int)
        assert pct == 0
