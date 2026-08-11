"""Iter 102 — AI summaries for the Family Violence & Communication
Safety Assessment PDF (four components).

Locks:
    * `build_safety_assessment_pdf` accepts an `ai_summaries` kwarg
      with keys `overall`, `pathway`, `section_1`, `section_2` — the
      four components the product spec calls for. Missing / empty
      keys must not crash the renderer.
    * Each summary text materially increases the rendered PDF size —
      proves the copy is actually landing on the page (a silent no-op
      would leave byte counts unchanged).
    * `generate_safety_summaries` returns the four-key dict shape
      even when the LLM key is missing (all four values = None). The
      caller (route handler) can safely spread the return value into
      the PDF builder either way.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

from safety_assessment_pdf import build_safety_assessment_pdf  # noqa: E402
from safety_ai_summary import generate_safety_summaries  # noqa: E402


def _stub_result():
    return {
        "level":           3,
        "safety_level":    3,
        "pathway_title":   "Structured mediation with a family-violence-informed mediator",
        "pathway_summary": "Recommended pathway from the deterministic rule engine.",
        "pathway_tone":    "warning",
        "recommendations": ["Speak with a qualified advocate before mediation."],
    }


def _stub_section_1():
    return [
        {"text": "Has your co-parent physically harmed you in the past 12 months?",
         "answer": "No"},
        {"text": "Has your co-parent threatened, stalked, or intimidated you?",
         "answer": "Yes"},
    ]


def _stub_section_2():
    return [
        {"text": "Can you communicate without fear of retaliation?", "answer": "Sometimes"},
        {"text": "Are text messages usable for scheduling?",         "answer": "Yes"},
    ]


# ---------- Renderer contract ----------

def test_builder_accepts_ai_summaries_kwarg_and_renders_valid_pdf():
    out = build_safety_assessment_pdf(
        user_name="Test Parent",
        generated_at="2026-02-10T12:00:00Z",
        result=_stub_result(),
        section_1_rows=_stub_section_1(),
        section_2_rows=_stub_section_2(),
        texas_resource_block="Texas 24-hour hotlines and shelters go here.",
        ai_summaries={
            "overall":   "This is the overall executive summary text.",
            "pathway":   "This 2-3 sentence pathway explanation lives here.",
            "section_1": "This is the section 1 immediate safety narrative.",
            "section_2": "This is the section 2 communication readiness narrative.",
        },
    )
    assert out.startswith(b"%PDF-")
    assert len(out) > 1500


def test_builder_still_renders_without_ai_summaries_kwarg():
    """Missing kwarg must not raise — the PDF must still generate cleanly
    if the LLM was unavailable at request time."""
    out = build_safety_assessment_pdf(
        user_name="Test Parent",
        generated_at="2026-02-10T12:00:00Z",
        result=_stub_result(),
        section_1_rows=_stub_section_1(),
        section_2_rows=_stub_section_2(),
        texas_resource_block="Texas resources.",
    )
    assert out.startswith(b"%PDF-")


def test_builder_handles_empty_or_missing_summary_keys():
    """Partial dicts (only some of the four keys) must render the
    provided ones and skip the empty ones without layout artefacts."""
    out = build_safety_assessment_pdf(
        user_name="Test Parent",
        generated_at="2026-02-10T12:00:00Z",
        result=_stub_result(),
        section_1_rows=_stub_section_1(),
        section_2_rows=_stub_section_2(),
        texas_resource_block="Texas resources.",
        ai_summaries={
            "overall":   "Only the overall summary is present.",
            "pathway":   "",      # explicitly empty — render nothing
            # section_1 and section_2 missing entirely
        },
    )
    assert out.startswith(b"%PDF-")


def test_summary_text_materially_increases_pdf_size():
    """Prove the AI copy is actually landing on the page. A silent
    no-op renderer would leave byte counts identical."""
    without = build_safety_assessment_pdf(
        user_name="Test Parent",
        generated_at="2026-02-10T12:00:00Z",
        result=_stub_result(),
        section_1_rows=_stub_section_1(),
        section_2_rows=_stub_section_2(),
        texas_resource_block="Texas resources.",
    )
    long_para = "This is a long narrative summary. " * 20
    with_ai = build_safety_assessment_pdf(
        user_name="Test Parent",
        generated_at="2026-02-10T12:00:00Z",
        result=_stub_result(),
        section_1_rows=_stub_section_1(),
        section_2_rows=_stub_section_2(),
        texas_resource_block="Texas resources.",
        ai_summaries={
            "overall":   long_para,
            "pathway":   long_para,
            "section_1": long_para,
            "section_2": long_para,
        },
    )
    assert len(with_ai) > len(without) + 300, (
        f"AI copy should measurably increase the PDF ({len(with_ai)} vs {len(without)})"
    )


# ---------- Generator contract ----------

def test_generate_safety_summaries_shape_with_no_llm_key():
    """When the LLM key is missing, all four keys must still be
    present in the return dict (with `None` values). This lets the
    route handler always spread the result into the PDF builder."""
    prev = os.environ.pop("EMERGENT_LLM_KEY", None)
    try:
        doc = {"result": _stub_result()}
        got = asyncio.get_event_loop().run_until_complete(
            generate_safety_summaries(
                doc=doc,
                section_1_rows=_stub_section_1(),
                section_2_rows=_stub_section_2(),
            )
        )
        assert set(got.keys()) == {"overall", "pathway", "section_1", "section_2"}
        # All None when the key is missing — but the shape is stable.
        for k, v in got.items():
            assert v is None, f"{k} should be None when LLM key missing, got {v!r}"
    finally:
        if prev is not None:
            os.environ["EMERGENT_LLM_KEY"] = prev


def test_generate_safety_summaries_skips_empty_sections():
    """If a section has no rows we shouldn't waste an LLM call on it —
    the return dict should surface `None` for that key."""
    prev = os.environ.pop("EMERGENT_LLM_KEY", None)
    try:
        got = asyncio.get_event_loop().run_until_complete(
            generate_safety_summaries(
                doc={"result": _stub_result()},
                section_1_rows=[],
                section_2_rows=[],
            )
        )
        # Section keys explicitly None when rows are empty — this is the
        # short-circuit path in `generate_safety_summaries`.
        assert got["section_1"] is None
        assert got["section_2"] is None
    finally:
        if prev is not None:
            os.environ["EMERGENT_LLM_KEY"] = prev
