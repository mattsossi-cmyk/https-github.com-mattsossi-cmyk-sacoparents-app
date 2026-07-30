"""Unit tests for the SNC scoring engine (Phase A)."""
from __future__ import annotations

from snc_questions import SECTIONS, SCORED_CATEGORY_IDS, scored_items, total_scored_items
from snc_scoring import (
    compute_scores, classify_avg, validate_answers,
    CLS_ESTABLISHED, CLS_SUPPORTED, CLS_OPPORTUNITY, CLS_INCONSISTENT, CLS_PRIORITY,
)


# ---------------------------------------------------------------------------
# Framework-shape sanity checks
# ---------------------------------------------------------------------------

def test_thirteen_sections():
    numbers = [s["number"] for s in SECTIONS]
    assert numbers == list(range(1, 14))


def test_scored_categories_are_sections_2_10_and_12():
    assert SCORED_CATEGORY_IDS == ("s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s12")


def test_section_11_is_never_scored():
    s11 = next(s for s in SECTIONS if s["id"] == "s11")
    assert s11["scored"] is False
    assert not any(it.get("scored") for it in s11["items"])


def test_expected_scored_item_counts():
    counts = {sid: len(scored_items(sid)) for sid in SCORED_CATEGORY_IDS}
    assert counts == {
        "s2": 8, "s3": 9, "s4": 10, "s5": 10, "s6": 12,
        "s7": 8, "s8": 8, "s9": 10, "s10": 7, "s12": 10,
    }
    assert total_scored_items() == sum(counts.values())  # 92 scored items


# ---------------------------------------------------------------------------
# Classification map
# ---------------------------------------------------------------------------

def test_classification_thresholds():
    assert classify_avg(5.00) == CLS_ESTABLISHED
    assert classify_avg(4.25) == CLS_ESTABLISHED
    assert classify_avg(4.24) == CLS_SUPPORTED
    assert classify_avg(3.50) == CLS_SUPPORTED
    assert classify_avg(3.49) == CLS_OPPORTUNITY
    assert classify_avg(2.75) == CLS_OPPORTUNITY
    assert classify_avg(2.74) == CLS_INCONSISTENT
    assert classify_avg(2.00) == CLS_INCONSISTENT
    assert classify_avg(1.99) == CLS_PRIORITY
    assert classify_avg(1.00) == CLS_PRIORITY
    assert classify_avg(None) is None


# ---------------------------------------------------------------------------
# End-to-end scoring
# ---------------------------------------------------------------------------

def _uniform_answers(v):
    """Set every SCORED item to value v. Section 6 uses consistency-scale numerics."""
    a = {}
    for sid in SCORED_CATEGORY_IDS:
        for it in scored_items(sid):
            a[it["id"]] = v if v != 5 or it["type"] != "consistency" else 5
    return a


def test_all_strong_is_established():
    s = compute_scores(_uniform_answers(5))
    assert all(c["classification"] == CLS_ESTABLISHED for c in s["categories"])
    assert s["overall_hint"] == "established_overall"


def test_all_weak_maps_to_priority():
    # Likert 1 for Likert sections, consistency 2 for Section 6 (lowest scored value).
    a = {}
    for sid in SCORED_CATEGORY_IDS:
        for it in scored_items(sid):
            a[it["id"]] = 2 if it["type"] == "consistency" else 1
    s = compute_scores(a)
    for c in s["categories"]:
        # s6 hits Frequently inconsistent = 2 → CLS_INCONSISTENT
        expected = CLS_INCONSISTENT if c["id"] == "s6" else CLS_PRIORITY
        assert c["classification"] == expected, c
    assert s["overall_hint"] == "priority_focus"


def test_na_and_unknown_are_excluded_from_average():
    a = _uniform_answers(4)
    a["s3_q1"] = "na"
    a["s6_medication"] = "unknown"
    a["s6_sleep"] = "na"
    s = compute_scores(a)
    s3 = next(c for c in s["categories"] if c["id"] == "s3")
    s6 = next(c for c in s["categories"] if c["id"] == "s6")
    assert s3["na_count"] == 1
    assert s3["answered"] == 8  # 9 scored - 1 NA
    assert s6["na_count"] == 2  # unknown + na
    assert s6["answered"] == 10 # 12 - 2 excluded


def test_section_11_never_contributes_to_scoring():
    a = _uniform_answers(4)
    a["s11_flags"] = ["I am afraid of the other parent.",
                      "Communications include threats, harassment, intimidation, or degrading language."]
    a["s11_safeguards"] = ["BIFF communication"]
    s = compute_scores(a)
    # Categories are the exact 10 scored sections — no s11 row.
    assert [c["id"] for c in s["categories"]] == list(SCORED_CATEGORY_IDS)
    assert s["safety"]["flagged"] is True
    assert s["safety"]["level"] == "concerns"
    assert s["safety"]["recommend_full_assessment"] is True
    assert "I am afraid of the other parent." in s["safety"]["selected_flags"]


def test_safety_clear_and_declined_levels():
    clear = compute_scores({"s11_flags": ["None of these apply."]})
    assert clear["safety"]["level"] == "clear"
    assert clear["safety"]["flagged"] is False
    assert clear["safety"]["recommend_full_assessment"] is False

    declined = compute_scores({"s11_flags": ["Prefer not to answer."]})
    assert declined["safety"]["level"] == "declined"


def test_validate_answers_accepts_and_rejects_correctly():
    ok, err = validate_answers({"s2_q1": 4, "s3_q2": "na", "s6_medication": 3})
    assert ok, err
    ok, err = validate_answers({"s2_q1": 6})
    assert not ok
    ok, err = validate_answers({"s6_medication": 1})
    assert not ok  # 1 is invalid on the consistency scale (min = 2)
    ok, err = validate_answers({"s7_preferred": ["Email", "Text message"]})
    assert ok


def test_answered_count_matches_input():
    a = _uniform_answers(4)
    s = compute_scores(a)
    assert s["answered_scored_count"] == total_scored_items()


def test_strongest_and_weakest_ids_populated():
    a = _uniform_answers(4)
    a["s7_q1"] = 5
    a["s7_q2"] = 5
    a["s7_q3"] = 5
    a["s7_q4"] = 5
    a["s7_q5"] = 5
    a["s7_q6"] = 5
    a["s7_q7"] = 5
    a["s7_q8"] = 5
    a["s5_q1"] = 1
    a["s5_q2"] = 1
    a["s5_q3"] = 1
    a["s5_q4"] = 1
    a["s5_q5"] = 1
    a["s5_q6"] = 1
    a["s5_q7"] = 1
    a["s5_q8"] = 1
    a["s5_q9"] = 1
    a["s5_q10"] = 1
    s = compute_scores(a)
    assert "s7" in s["strongest_category_ids"]
    assert "s5" in s["weakest_category_ids"]
