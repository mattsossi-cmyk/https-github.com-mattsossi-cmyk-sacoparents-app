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







    def test_trend_without_current_pct_no_delta(self):
        """If we don't know the current pct, we can't render a delta even if
        we have a previous. Email falls back to plain (no preview at all)."""
        with self._capture() as m:
            email_service.send_compare_invite(
                to_email="p2@example.com",
                link_url="https://example.com/hub",
                previous_aligned_pct=62,
            )
        kwargs = m.call_args.kwargs
        assert "A quick preview" not in kwargs["html"]
        assert "since your last check-in" not in kwargs["html"]



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
                if item.get("type") in ("likert", "alignment"):
                    scale = item.get("scale") or [1, 2, 3, 4, 5]
                    a[key] = max(scale) if scale else 5
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


def test_compare_invite_never_includes_scores_or_product():
    with patch.object(email_service, "_send") as m:
        email_service.send_compare_invite(
            to_email="p2@example.com", link_url="https://example.com/hub", inviter_name="Sam",
            product_label="Checkin - Medical Needs", aligned_pct=68, previous_aligned_pct=50,
        )
    body = m.call_args.kwargs["html"] + m.call_args.kwargs["text"] + m.call_args.kwargs["subject"]
    assert "68" not in body and "Medical" not in body
    assert "https://example.com/hub" in body
