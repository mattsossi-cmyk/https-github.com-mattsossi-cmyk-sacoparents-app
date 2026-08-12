"""Iter 109 — Universal self-reflection disclaimer surfaced everywhere.

The user explicitly asked for the following language to appear on every
assessment surface:

    This assessment is a guided self-reflection and preparation
    resource. It is not a clinical, forensic, legal, or professional
    evaluation. Its results are intended to help you identify concerns,
    organize your thinking, and prepare questions for an appropriate
    professional.

This test locks that language into:
    * the shared constant in trauma_lens.SELF_REFLECTION_DISCLAIMER
    * the readiness_scoring output (readiness_disclaimer field)
    * the safety_assessment_pdf output
    * the safety_court_report_pdf output (via COURT_REPORT_LIMITS_STATEMENT)
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/app/backend")

CORE_PHRASE = "guided self-reflection and preparation resource"
CORE_PHRASE_2 = "not a clinical, forensic, legal, or professional evaluation"


def test_constant_holds_the_agreed_language():
    from trauma_lens import SELF_REFLECTION_DISCLAIMER
    assert CORE_PHRASE in SELF_REFLECTION_DISCLAIMER
    assert CORE_PHRASE_2 in SELF_REFLECTION_DISCLAIMER
    assert "appropriate professional" in SELF_REFLECTION_DISCLAIMER


def test_readiness_disclaimer_includes_the_agreed_language():
    from readiness_scoring import compute_readiness
    r = compute_readiness({
        "comm_style": {"scores": {"tone": 3.0}},
        "child_goals": {"emotional_wellbeing": "ok"},
        "priority": [{"category": "compromise"}],
        "issues": {"schedule": "s"},
        "readiness": {"scores": {"cooperation": 3.0}},
        "safety_assessment": {},
    })
    disc = r["readiness_disclaimer"]
    assert CORE_PHRASE in disc
    assert CORE_PHRASE_2 in disc


def test_court_report_limits_statement_leads_with_the_agreed_language():
    from trauma_lens import COURT_REPORT_LIMITS_STATEMENT
    # The universal disclaimer must appear at the very START — a court
    # reviewer should see the framing before any other qualifier.
    assert COURT_REPORT_LIMITS_STATEMENT.startswith(
        "This assessment is a guided self-reflection and preparation resource."
    )


def test_safety_assessment_pdf_disclaimer_uses_the_shared_constant():
    """Direct source check — the PDF disclaimer renderer must reference
    the shared constant rather than a hard-coded string. This prevents
    the two from drifting apart."""
    with open("/app/backend/safety_assessment_pdf.py", encoding="utf-8") as fh:
        source = fh.read()
    assert "SELF_REFLECTION_DISCLAIMER" in source, (
        "safety_assessment_pdf._render_disclaimer must import and render "
        "trauma_lens.SELF_REFLECTION_DISCLAIMER so the language stays "
        "in sync across the app."
    )


def test_safety_assessment_intake_page_carries_the_agreed_language():
    with open("/app/frontend/src/pages/SafetyAssessment.jsx", encoding="utf-8") as fh:
        src = fh.read()
    assert "guided self-reflection and preparation" in src
    assert "not a clinical, forensic, legal, or professional" in src


def test_results_card_leads_with_the_agreed_language():
    """The results card must show the disclaimer prominently — a parent
    who lands here after scoring must see the framing before results."""
    with open("/app/frontend/src/pages/SafetyAssessment.jsx", encoding="utf-8") as fh:
        src = fh.read()
    assert 'data-testid="results-self-reflection-disclaimer"' in src
