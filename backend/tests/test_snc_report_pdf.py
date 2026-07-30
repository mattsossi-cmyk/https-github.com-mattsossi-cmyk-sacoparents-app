"""Unit tests for the SNC PDF renderer (Phase C)."""
from __future__ import annotations

from snc_questions import SECTIONS, SCORED_CATEGORY_IDS, scored_items
from snc_scoring import compute_scores
from snc_report_content import build_individual_report
from snc_report_pdf import build_snc_pdf


def _answers(mix: bool = True) -> dict:
    """Realistic mixed profile so every classification appears."""
    a = {
        "s1_age": "8 years / 3rd grade",
        "s1_strengths": "Curious. Kind. Loves dinosaurs.",
        "s1_joy": "Drawing, biking, reading with mom.",
        "s1_diagnosis_status": "Diagnosis or eligibility determination received",
        "s1_needs": ["ADHD or executive functioning", "Sensory processing"],
        "s1_needs_narrative": "ADHD-Combined; ongoing OT.",
        "s3_providers": ["Pediatrician", "Occupational therapist"],
        "s3_open_coord": "Medication timing.",
        "s7_preferred": ["Co-parenting application"],
        "s11_flags": ["None of these apply."],
        "s13_goals": "Predictable bedtime; shared homework; regular OT.",
        "s13_concerns": "Homework meltdowns; medication timing; missed notices.",
        "s13_info_needed": "ADHD medication dose review.",
        "s13_thirty_day": "Try the shared parenting app for 30 days.",
    }
    if mix:
        for it in scored_items("s2"):  a[it["id"]] = 4
        for it in scored_items("s3"):  a[it["id"]] = 3
        for it in scored_items("s4"):  a[it["id"]] = 5
        for it in scored_items("s5"):  a[it["id"]] = 2
        for it in scored_items("s6"):  a[it["id"]] = 4
        for it in scored_items("s7"):  a[it["id"]] = 1
        for it in scored_items("s8"):  a[it["id"]] = 4
        for it in scored_items("s9"):  a[it["id"]] = 4
        for it in scored_items("s10"): a[it["id"]] = 3
        for it in scored_items("s12"): a[it["id"]] = 4
    return a


def test_pdf_bytes_signature_and_size():
    a = _answers()
    r = build_individual_report(parent_name="Sam Parent", child_name="A.",
                                assessment_date="2026-02-15", answers=a)
    pdf = build_snc_pdf(report=r)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 5000, "expected a multi-page report"


def test_pdf_renders_with_empty_answers():
    r = build_individual_report(parent_name="Sam", answers={})
    pdf = build_snc_pdf(report=r)
    assert pdf[:4] == b"%PDF"


def test_pdf_respects_safety_redaction():
    """When include_safety=False, the rendered PDF must not carry safety flag
    text. Compare byte size between the two views: the shared view should be
    smaller when there are flagged items to redact."""
    a = _answers()
    a["s11_flags"] = ["I am afraid of the other parent.",
                      "Communications include threats, harassment, intimidation, or degrading language."]
    a["s11_safeguards"] = ["BIFF communication", "Neutral or supervised exchange location"]

    own = build_individual_report(parent_name="Sam", answers=a, include_safety=True)
    shared = build_individual_report(parent_name="Sam", answers=a, include_safety=False)

    pdf_own = build_snc_pdf(report=own)
    pdf_shared = build_snc_pdf(report=shared)

    # The flag text must appear in the own-view PDF and not the shared-view PDF.
    assert b"I am afraid of the other parent" in pdf_own
    assert b"I am afraid of the other parent" not in pdf_shared
    assert b"BIFF communication" in pdf_own
    assert b"BIFF communication" not in pdf_shared


def test_pdf_uses_new_vocabulary_only():
    """PDF must not carry any of the old SN / CP rating vocabulary."""
    a = _answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    pdf = build_snc_pdf(report=r)
    for banned in (
        b"Excellent Progress", b"Building Progress", b"Early Progress",
        b"Existing strength", b"Developing area",
        b"Priority for planning", b"Professional guidance recommended",
        b"Safety-sensitive concern", b"10 Principles", b"10 Domains",
    ):
        assert banned not in pdf, f"legacy label {banned!r} should not appear"


def test_pdf_carries_all_seventeen_report_sections():
    """Spot-check that the section headers we expect are all rendered."""
    a = _answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    pdf = build_snc_pdf(report=r)
    for marker in [
        b"Report at a Glance",
        b"Category Summary",
        b"Child Profile",
        b"Understanding and Acceptance",
        b"Medical and Mental Healthcare",
        b"Kindergarten and Elementary School",
        b"Transitions, Pickup",
        b"Daily Routines Across Homes",
        b"Communication and Information Sharing",
        b"School Events",
        b"Extracurricular Activities",
        b"Decision-Making and Professional Guidance",
        b"Family Violence and Communication Safety",
        b"Parent Capacity and Support",
        b"Recommended Child-Focused Action Plan",
        b"Questions for the Other Parent",
        b"Closing Summary",
    ]:
        assert marker in pdf, f"missing PDF section marker: {marker!r}"


def test_pdf_never_labels_a_parent_correct_or_wrong():
    a = _answers()
    r = build_individual_report(parent_name="Sam", answers=a)
    pdf = build_snc_pdf(report=r)
    # Purpose paragraph legitimately quotes the spec's "…is correct…" line — that's fine.
    # Anywhere else we scan for judgemental phrases.
    for phrase in (b" is wrong", b"better parent", b"worse parent", b"at fault"):
        assert phrase not in pdf, f"PDF must never contain judgemental phrase {phrase!r}"
