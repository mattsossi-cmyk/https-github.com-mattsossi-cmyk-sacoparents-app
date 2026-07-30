"""Unit tests for the neutral SNC pair-comparison logic."""
from __future__ import annotations

from snc_comparison import compare_reports, SAFETY_NOTICE


def _report(cat_rows, questions=None, coordination=None):
    return {
        "category_summary": cat_rows,
        "questions_for_other_parent": questions or [],
        "at_a_glance": {"coordination_areas": coordination or []},
    }


def _row(cid, name, score, classification):
    return {"id": cid, "category": name, "score": score, "classification": classification, "primary_finding": ""}


def test_agreement_when_scores_are_close_and_same_classification():
    a = _report([_row("s2", "Understanding", 4.2, "Established strength")])
    b = _report([_row("s2", "Understanding", 4.5, "Established strength")])
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=a, report_b=b)
    assert out["buckets"]["agreement"] == ["s2"]
    assert out["buckets"]["different_observations"] == []
    assert out["counts"]["agreement"] == 1


def test_different_when_scores_diverge():
    a = _report([_row("s5", "Transitions", 4.5, "Established strength")])
    b = _report([_row("s5", "Transitions", 2.1, "Significant inconsistency")])
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=a, report_b=b)
    assert out["buckets"]["different_observations"] == ["s5"]
    assert out["counts"]["different_observations"] == 1
    row = next(c for c in out["categories"] if c["id"] == "s5")
    assert "differently" in row["note"].lower()


def test_missing_when_one_side_has_no_data():
    a = _report([_row("s3", "Medical", 3.0, "Coordination opportunity")])
    b = _report([_row("s3", "Medical", None, "Not enough data")])
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=a, report_b=b)
    assert out["buckets"]["missing_information"] == ["s3"]


def test_never_includes_section_11():
    a = _report([
        _row("s2", "Understanding", 4.2, "Established strength"),
        _row("s11", "Safety considerations", "Not scored", "Separate review"),
    ])
    b = _report([
        _row("s2", "Understanding", 4.3, "Established strength"),
        _row("s11", "Safety considerations", "Not scored", "Separate review"),
    ])
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=a, report_b=b)
    all_ids = [c["id"] for c in out["categories"]]
    assert "s11" not in all_ids
    for bucket_key in ("agreement", "different_observations", "missing_information"):
        assert "s11" not in out["buckets"][bucket_key]
    assert out["safety_notice"] == SAFETY_NOTICE


def test_no_verbatim_narrative_leakage():
    """Comparison output must not contain any free-text field values from either report."""
    a = _report(
        [_row("s2", "Understanding", 3.0, "Coordination opportunity")],
        questions=[],
        coordination=[],
    )
    a["narratives"] = {"s1_strengths": "SECRET_PARENT_A_NARRATIVE"}
    b = _report(
        [_row("s2", "Understanding", 3.2, "Coordination opportunity")],
        questions=[],
        coordination=[],
    )
    b["narratives"] = {"s1_strengths": "SECRET_PARENT_B_NARRATIVE"}
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=a, report_b=b)
    blob = str(out)
    assert "SECRET_PARENT_A_NARRATIVE" not in blob
    assert "SECRET_PARENT_B_NARRATIVE" not in blob


def test_professional_questions_are_deduped_across_parents():
    a = _report(
        [_row("s2", "Understanding", 3.0, "Coordination opportunity")],
        questions=["What does IEP timing look like?", "How often does OT happen?"],
    )
    b = _report(
        [_row("s2", "Understanding", 3.0, "Coordination opportunity")],
        questions=["What does IEP timing look like?", "Is medication being consistent?"],
    )
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=a, report_b=b)
    pqs = out["buckets"]["professional_questions"]
    assert len(pqs) == len(set(q.lower() for q in pqs))
    assert "How often does OT happen?" in pqs
    assert "Is medication being consistent?" in pqs


def test_output_never_labels_a_parent_correct_or_wrong():
    a = _report([_row("s5", "Transitions", 4.5, "Established strength")])
    b = _report([_row("s5", "Transitions", 2.0, "Priority concern")])
    out = compare_reports(parent_a_name="Alice", parent_b_name="Bob", report_a=a, report_b=b)
    blob = str(out).lower()
    for bad in ("correct parent", "wrong parent", "winner", "incorrect", "right parent"):
        assert bad not in blob


def test_disclaimer_and_safety_notice_present():
    out = compare_reports(parent_a_name="A", parent_b_name="B", report_a=_report([]), report_b=_report([]))
    assert "educational" in out["disclaimer"].lower()
    assert "safety" in out["safety_notice"].lower()
