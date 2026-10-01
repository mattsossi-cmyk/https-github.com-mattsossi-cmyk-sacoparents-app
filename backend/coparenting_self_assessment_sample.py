"""Iter234 · Public sample of the thorough Self Co-Parenting Assessment PDF.

Mounted at `/api/insights/samples/coparenting-self-assessment.pdf` so
a parent, mediator, or attorney can see what the full 10-section
individual report looks like before taking the assessment themselves
or inviting a client to.

The fixture gives a *plausible* mid-range parent — some sections
score Excellent, some Good, some Fair, one Needs Improvement — so
the output exercises every rendered block (strengths, growth areas,
section detail, communication toolkit, next steps). No PII.

Rendered through the SAME `compute_scores` → `build_report` →
`build_coparenting_pdf` code path a real submission uses, so any
tweak to the live assessment flows automatically to the sample.
"""
from __future__ import annotations

from typing import Dict

from coparenting_questions import SECTIONS


SAMPLE_PARENT_NAME = "Jamie R."


# Per-section target raw-answer values. Picked so the computed
# section ratings land across the Excellent / Good / Fair / Needs
# Improvement bands and so reverse-scored items still read as
# plausible.
#
# Scoring recap (coparenting_scoring.compute_scores):
#   raw answer = 0..4, reverse items use (4 - raw)
#   section avg = mean of effective values, scaled to a rating band
#     >= 3.3 → Excellent, >= 2.6 → Good, >= 1.8 → Fair, else Needs
#     Improvement
#
# Each row below gives (positive_value, reverse_value) so that
# reverse-scored prompts stay realistic (e.g. "conversations tip
# into conflict" = Rarely for a healthy section).
_SECTION_PROFILES: Dict[str, Dict[str, int]] = {
    # Strong — Excellent band
    "s5": {"pos": 4, "rev": 0},   # Daily routines in own home
    "s8": {"pos": 4, "rev": 0},   # Safety & supervision
    "s10": {"pos": 4, "rev": 0},  # Long-term child success

    # Good band
    "s3": {"pos": 3, "rev": 1},   # Educational needs
    "s6": {"pos": 3, "rev": 1},   # Emotional / behavioural support
    "s9": {"pos": 3, "rev": 1},   # Social & community

    # Fair band — some texture
    "s2": {"pos": 2, "rev": 2},   # Pick-up / drop-off
    "s4": {"pos": 2, "rev": 2},   # Medical / healthcare
    "s7": {"pos": 2, "rev": 2},   # Therapy / skill reinforcement

    # Needs Improvement — Communication (triggers_toolkit=True so
    # the sample demonstrates the Communication Toolkit block too)
    "s1": {"pos": 1, "rev": 3},
}


def build_sample_answers() -> Dict[str, int]:
    """Materialise {question_id: 0..4} using _SECTION_PROFILES."""
    answers: Dict[str, int] = {}
    for section in SECTIONS:
        profile = _SECTION_PROFILES.get(section["id"]) or {"pos": 3, "rev": 1}
        for q in section["questions"]:
            if q.get("reverse"):
                answers[q["id"]] = profile["rev"]
            else:
                answers[q["id"]] = profile["pos"]
    return answers


def build_sample_report_dict() -> Dict:
    """Return the full report dict (same shape live submissions store)."""
    from coparenting_scoring import compute_scores
    from cp_report_content import build_report

    answers = build_sample_answers()
    scores = compute_scores(answers)
    return build_report(
        scores=scores,
        answers=answers,
        parent_name=SAMPLE_PARENT_NAME,
    )


def build_sample_pdf_bytes() -> bytes:
    """Fully-rendered PDF bytes — public, cacheable, no PII."""
    from cp_report_pdf import build_coparenting_pdf

    report = build_sample_report_dict()
    return build_coparenting_pdf(
        user_name=SAMPLE_PARENT_NAME,
        report=report,
        excluded_sections=None,
    )
