"""Tests for the SNC comparison PDF renderer.

Ensures:
  * output is a valid PDF (%PDF- header, non-trivial size)
  * safety notice appears in text
  * Section 11 category id is never embedded in the PDF bytes
  * verbatim narrative sentinels are never embedded
  * no winner-language phrases are embedded
"""
from __future__ import annotations

from snc_comparison import compare_reports
from snc_comparison_pdf import build_snc_comparison_pdf


def _row(cid, name, score, classification):
    return {
        "id": cid, "category": name, "score": score,
        "classification": classification, "primary_finding": "",
    }


def _report(rows, questions=None, coordination=None):
    return {
        "category_summary": rows,
        "questions_for_other_parent": questions or [],
        "at_a_glance": {"coordination_areas": coordination or []},
    }


def _rich_comparison():
    a = _report(
        [
            _row("s2", "Understanding and Acceptance", 4.6, "Established strength"),
            _row("s3", "Medical and Mental Healthcare", 3.0, "Coordination opportunity"),
            _row("s5", "Transitions, Pickup, and Drop-Off", 4.5, "Established strength"),
            _row("s11", "Safety considerations", "Not scored", "Separate review"),  # must be dropped
        ],
        questions=["Is the IEP timing consistent?", "What does OT progress look like?"],
        coordination=["Align medication schedules across homes."],
    )
    b = _report(
        [
            _row("s2", "Understanding and Acceptance", 4.4, "Established strength"),
            _row("s3", "Medical and Mental Healthcare", 3.1, "Coordination opportunity"),
            _row("s5", "Transitions, Pickup, and Drop-Off", 2.0, "Priority concern"),
        ],
        questions=["Is the IEP timing consistent?", "How can we simplify Sunday handoffs?"],
        coordination=["Introduce a shared parenting app."],
    )
    # Add sentinel narrative fields that must NEVER leak into the PDF text.
    a["narratives"] = {"s1_strengths": "PARENT_A_NARRATIVE_SENTINEL_ABC"}
    b["narratives"] = {"s1_strengths": "PARENT_B_NARRATIVE_SENTINEL_XYZ"}
    return compare_reports(
        parent_a_name="Alex", parent_b_name="Blair",
        report_a=a, report_b=b,
    )


def test_pdf_signature_and_size():
    cmp = _rich_comparison()
    out = build_snc_comparison_pdf(comparison=cmp)
    assert isinstance(out, (bytes, bytearray))
    assert out[:5] == b"%PDF-"
    assert len(out) > 5000


def test_pdf_never_embeds_section_11():
    cmp = _rich_comparison()
    out = build_snc_comparison_pdf(comparison=cmp)
    # s11 id must not appear anywhere
    assert b"s11" not in out
    # The safety category name must not appear (we only mention it in the
    # safety-notice sentence, which uses "Family Violence" phrasing).
    assert b"Safety considerations" not in out


def test_pdf_never_embeds_verbatim_narratives():
    cmp = _rich_comparison()
    out = build_snc_comparison_pdf(comparison=cmp)
    assert b"PARENT_A_NARRATIVE_SENTINEL_ABC" not in out
    assert b"PARENT_B_NARRATIVE_SENTINEL_XYZ" not in out


def test_pdf_never_labels_a_parent_correct_or_wrong():
    cmp = _rich_comparison()
    out = build_snc_comparison_pdf(comparison=cmp)
    low = out.lower()
    for bad in (b"correct parent", b"wrong parent", b"winner", b"right parent", b"incorrect parent"):
        assert bad not in low


def test_pdf_contains_safety_notice_and_bucket_titles():
    cmp = _rich_comparison()
    out = build_snc_comparison_pdf(comparison=cmp)
    assert b"Neutral Side-by-Side" in out
    assert b"Where you agree" in out
    assert b"Where you see it differently" in out
    assert b"Where more information would help" in out
    # Safety notice line — verify the "kept private" phrasing exists in the PDF.
    assert b"kept private" in out


def test_pdf_contains_professional_questions_and_coordination():
    cmp = _rich_comparison()
    out = build_snc_comparison_pdf(comparison=cmp)
    assert b"Professional questions" in out
    assert b"Practical coordination areas" in out
    # Dedup: the same question appears in both parents' reports
    # but must only be listed once.
    assert out.count(b"Is the IEP timing consistent") == 1
