"""Iter 190 — Co-Parenting Agreement (Step One - Alignment Before
Agreement) structure lock.

Verifies that the payload + PDF renderer produce the sacoparentsalign
10-section flow (Purpose / Both Agree / Perspectives Differ / Child's
Needs / Alignment Map / Areas for Conversation / Options / Potential
Alignment / Questions / Next Steps) plus the "Alignment Before
Agreement" closing page. Also locks the neutral colour-band vocabulary
on the Alignment Map so a future refactor does not silently drift.
"""
from __future__ import annotations

import io

import pytest

from joint_agreement import build_joint_agreement
from joint_agreement_pdf import build_joint_agreement_pdf


try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover — pypdf pinned in requirements
    from PyPDF2 import PdfReader


def _fixture_payload():
    """Build a realistic joint agreement payload with a mix of shared,
    diverging, and open clauses so every alignment band surfaces."""
    a = {
        "agreement_id":       "agr_a_iter190",
        "generated_at":       "2026-09-13T00:00:00Z",
        "shared_goals":       ["Both homes prioritize consistent bedtime routines."],
        "communication":      [{"area": "Weekly check-ins",
                                "agreement": "Sunday 8pm check-in to align on the coming week."}],
        "child_needs":        [{"area": "Emotional support",
                                "agreement": "Both parents actively listen when Maya expresses big feelings."}],
        "household_rules":    [{"area": "Screen time",
                                "agreement": "Screen time capped at 90 minutes weeknights."}],
        "priority_items":     [{"area": "School transitions",
                                "agreement": "Prioritize smooth Monday morning drop-offs."}],
        "open_for_discussion": ["Weekend flexibility around family events"],
    }
    b = {
        "agreement_id":       "agr_b_iter190",
        "generated_at":       "2026-09-13T00:00:01Z",
        "shared_goals":       ["Both homes prioritize consistent bedtime routines."],
        "communication":      [{"area": "Handoff notes",
                                "agreement": "Share a two-line handoff note at each exchange."}],
        "child_needs":        [{"area": "Emotional support",
                                "agreement": "Both parents actively listen when Maya expresses big feelings."}],
        "household_rules":    [{"area": "Homework routine",
                                "agreement": "Homework is done before dinner in both homes."}],
        "priority_items":     [{"area": "Homework consistency",
                                "agreement": "Keep homework routine identical in both homes."}],
        "open_for_discussion": ["Weekend flexibility around family events",
                                "Holiday transport"],
    }
    return build_joint_agreement(
        share_id="sh_iter190",
        parent_a_name="Alex R.",
        parent_b_name="Sam R.",
        agreement_a=a,
        agreement_b=b,
    )


# ---------------------------------------------------------------------------
# Payload contract — the alignment-report additive fields must be present
# so PDF / frontend / consumers can render the new flow without falling
# back to defaults.
# ---------------------------------------------------------------------------

def test_payload_reports_alignment_report_type():
    """The report is now framed as the Co-Parenting Agreement, not the
    older Joint Co-Parenting Agreement Draft. Consumers key off
    `report_type` so this string is a hard contract."""
    payload = _fixture_payload()
    assert payload["report_type"] == "joint_alignment_report"
    assert payload["report_title"] == "Step One - Alignment Before Agreement"
    assert payload["report_subtitle"] == "Co-Parenting Agreement"
    assert "neutral map" in payload["report_tagline"].lower()


def test_payload_carries_alignment_report_block():
    """The `alignment_report` block is the primary source of truth for
    the 10-section flow. Every downstream renderer keys off these
    fields; a missing key would blank a section."""
    payload = _fixture_payload()
    ar = payload["alignment_report"]
    assert set(ar.keys()) >= {
        "purpose_note",
        "alignment_map",
        "child_identified_needs",
        "potential_alignment",
        "possible_next_steps",
        "closing_quote",
        "closing_line",
    }


def test_alignment_map_covers_every_merged_section():
    """Alignment map must have one row per merged section so the PDF
    never renders a partial grid. Order is locked to the canonical
    section order — the PDF renders top-to-bottom in this exact
    sequence."""
    payload = _fixture_payload()
    keys = [row["key"] for row in payload["alignment_report"]["alignment_map"]]
    assert keys == [
        "shared_goals",
        "communication",
        "child_needs",
        "household_rules",
        "priority_items",
        "open_for_discussion",
    ]


@pytest.mark.parametrize("band", ["strong", "moderate", "needs_discussion", "not_enough_data"])
def test_alignment_map_uses_locked_band_vocabulary(band):
    """Alignment band vocabulary is a hard contract with the PDF colour
    key and the frontend chip renderer. Adding or renaming a band
    without touching both would ship a broken map."""
    from joint_agreement_pdf import _ALIGNMENT_BAND_LABELS
    assert band in _ALIGNMENT_BAND_LABELS


def test_alignment_map_scores_reflect_data():
    """Fixture has both parents proposing the same bedtime clause
    (strong) and each parent proposing different communication
    clauses (needs discussion). Lock the arithmetic so a future
    threshold tweak surfaces here first."""
    payload = _fixture_payload()
    by_key = {row["key"]: row for row in payload["alignment_report"]["alignment_map"]}
    assert by_key["shared_goals"]["alignment"] == "strong"
    assert by_key["shared_goals"]["both_count"] == 1
    assert by_key["shared_goals"]["total_count"] == 1
    assert by_key["communication"]["alignment"] == "needs_discussion"
    assert by_key["communication"]["both_count"] == 0
    assert by_key["communication"]["total_count"] == 2


def test_child_identified_needs_backfills_from_defaults():
    """Even with light data the section must render at least 5
    bullets so the PDF page never looks sparse. Fallback pulls from
    the SA CoParents neutral defaults."""
    payload = _fixture_payload()
    needs = payload["alignment_report"]["child_identified_needs"]
    assert 5 <= len(needs) <= 8


def test_possible_next_steps_static_list():
    """The next-steps block is static so parents get the same options
    regardless of how much data flowed in."""
    payload = _fixture_payload()
    titles = [s["title"] for s in payload["alignment_report"]["possible_next_steps"]]
    assert titles == [
        "Continue Parent Discussion",
        "Discuss With Mediator",
        "Consult Teacher / School Counselor",
        "Consult Child's Professional",
        "Develop Written Parenting Protocol",
        "Create Another Joint Report",
    ]


# ---------------------------------------------------------------------------
# PDF contract — the 10-section flow, section headings, and closing page
# must all appear on disk. Text-extraction is deliberately loose (single
# substring match) so a font-swap doesn't break the test.
# ---------------------------------------------------------------------------

_EXPECTED_HEADINGS = [
    "1. Purpose of This Report",
    "2. What Both Parents Agree About",
    "3. Where the Parents See Things Differently",
    "4. Child's Identified Needs",
    "5. Alignment Map",
    "6. Areas for Conversation",
    "7. Options and Resources",
    "8. Potential Areas of Alignment",
    "9. Questions for the Parents",
    "10. Possible Next Steps",
]


def _pdf_full_text(pdf_bytes: bytes) -> str:
    r = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((p.extract_text() or "") for p in r.pages)


def test_pdf_renders_all_ten_section_headings():
    """Every §1..§10 heading must land in the rendered PDF or the flow
    is broken. This is the primary "did the refactor land?" test."""
    payload = _fixture_payload()
    pdf_bytes = build_joint_agreement_pdf(payload)
    text = _pdf_full_text(pdf_bytes)
    for heading in _EXPECTED_HEADINGS:
        assert heading in text, f"Missing PDF section heading: {heading}"


def test_pdf_renders_closing_alignment_before_agreement_page():
    """The thematic closing page ("Alignment Before Agreement") is the
    signature moment of the report — a mediator handed the PDF should
    see it as the last content page before the appendix."""
    payload = _fixture_payload()
    pdf_bytes = build_joint_agreement_pdf(payload)
    text = _pdf_full_text(pdf_bytes)
    assert "Alignment Before Agreement" in text
    # The closing thematic line + the pull-quote should both land.
    assert "You don't have to see everything the same way" in text
    assert "how well it supports the child" in text


def test_pdf_still_carries_appendix_a_for_professionals():
    """Appendix A (per-section clause breakdown) is kept for attorneys
    and mediators who need the raw draft. Removing it would break the
    Iter123 share-link contract with professionals."""
    payload = _fixture_payload()
    pdf_bytes = build_joint_agreement_pdf(payload)
    text = _pdf_full_text(pdf_bytes)
    assert "Appendix A - Detailed Item Breakdown" in text


def test_pdf_header_uses_new_framing():
    """The running header on every non-cover page shows "Step One -
    Alignment Before Agreement". Any consumer scraping the header
    (e.g. email preview) keys off this string."""
    payload = _fixture_payload()
    pdf_bytes = build_joint_agreement_pdf(payload)
    text = _pdf_full_text(pdf_bytes)
    assert "Step One - Alignment Before Agreement" in text
