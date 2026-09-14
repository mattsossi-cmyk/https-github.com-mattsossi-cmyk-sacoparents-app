"""Iter192 · Public co-parenting Joint Alignment Report sample.

Fictional but realistic data — Alex R. and Sam R. co-parenting Maya
(age 9). Used by the public `/api/insights/samples/co-parenting-alignment-report.pdf`
route so mediators, attorneys, and therapists can preview the format
before creating a real case.

Sample rules:
  * No PII, no real names, no real emails.
  * The two parents' reflection answers OVERLAP on 3-4 prompts so
    every "Both parents mentioned 'X'" bullet on the PDF is a
    genuine, non-trivial demonstration of the analysis engine.
  * Agreement clauses are populated for every merged section so the
    5-bucket Parent View and the colour-coded Alignment Map each
    surface a realistic mix of Strong / Moderate / Needs discussion.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple


SAMPLE_PARENT_A_NAME = "Alex R."
SAMPLE_PARENT_B_NAME = "Sam R."
SAMPLE_CHILD_NAME    = "Maya"
SAMPLE_SHARE_ID      = "SA-SAMPLE-COPARENTING"


def _sample_agreement_a() -> Dict[str, Any]:
    """Parent A's individual Co-Parenting Agreement Draft."""
    return {
        "agreement_id": "agr_sample_a",
        "generated_at": "2026-09-01T09:00:00Z",
        "shared_goals": [
            "Both homes prioritise consistent bedtime routines.",
            "Both parents support Maya's homework routine.",
        ],
        "communication": [
            {
                "area":      "Weekly check-ins",
                "agreement": "We hold a Sunday 8pm check-in call to align on the coming week.",
            },
            {
                "area":      "Handoff notes",
                "agreement": "Every exchange includes a two-line note about Maya's meals and mood.",
            },
        ],
        "child_needs": [
            {
                "area":      "Emotional support",
                "agreement": "Both parents actively listen when Maya expresses big feelings.",
            },
            {
                "area":      "Social calendar",
                "agreement": "Playdates with Emily and Josh continue at both homes.",
            },
        ],
        "household_rules": [
            {
                "area":      "Screen time",
                "agreement": "Screen time is capped at 90 minutes on weeknights.",
            },
            {
                "area":      "Bedtime",
                "agreement": "Lights out by 9pm on school nights.",
            },
        ],
        "priority_items": [
            {
                "area":      "School transitions",
                "agreement": "Prioritise smooth Monday morning drop-offs.",
            },
            {
                "area":      "Homework consistency",
                "agreement": "Keep the homework routine identical between both homes.",
            },
        ],
        "open_for_discussion": [
            "Weekend flexibility around family events",
            "Extended family visits in December",
        ],
    }


def _sample_agreement_b() -> Dict[str, Any]:
    """Parent B's individual Co-Parenting Agreement Draft — deliberate
    partial overlap with A so the merger surfaces realistic
    Strong/Moderate/Needs-discussion signal."""
    return {
        "agreement_id": "agr_sample_b",
        "generated_at": "2026-09-02T14:30:00Z",
        "shared_goals": [
            "Both homes prioritise consistent bedtime routines.",
        ],
        "communication": [
            {
                "area":      "Handoff notes",
                "agreement": "Share a two-line handoff note at each exchange about mood and meals.",
            },
            {
                "area":      "Emergency contact",
                "agreement": "Both parents are the emergency contact on Maya's school forms.",
            },
        ],
        "child_needs": [
            {
                "area":      "Emotional support",
                "agreement": "Both parents actively listen when Maya expresses big feelings.",
            },
            {
                "area":      "Consistent structure",
                "agreement": "Predictable weekday routines in both homes.",
            },
        ],
        "household_rules": [
            {
                "area":      "Homework routine",
                "agreement": "Homework is done before dinner in both homes.",
            },
            {
                "area":      "Bedtime",
                "agreement": "Lights out by 9pm on school nights.",
            },
        ],
        "priority_items": [
            {
                "area":      "Homework consistency",
                "agreement": "Keep homework routine identical in both homes.",
            },
            {
                "area":      "Communication rhythm",
                "agreement": "Prioritise the Sunday check-in call before the school week.",
            },
        ],
        "open_for_discussion": [
            "Weekend flexibility around family events",
            "Holiday transport arrangements",
        ],
    }


def _sample_reflections_a() -> Dict[str, str]:
    return {
        "primary_need": (
            "Maya needs consistent expectations across both homes so she "
            "isn't spending mental energy translating between two sets of rules."
        ),
        "whats_working": (
            "The bedtime routine is finally solid in both places. Sunday "
            "check-ins are a game-changer."
        ),
        "concerns": (
            "Screen-time rules quietly drift and homework routines change "
            "without me hearing about it until Maya is upset on a Monday."
        ),
        "desired_improvements": (
            "More consistent bedtimes on school nights and a shared "
            "written protocol so we're not re-negotiating the same "
            "things every month."
        ),
        "options": (
            "A shared calendar, monthly check-ins, and a written "
            "co-parenting protocol we both signed."
        ),
        "other_parent_concerns": (
            "They probably worry about Maya being tired at school after "
            "a busy weekend."
        ),
    }


def _sample_reflections_b() -> Dict[str, str]:
    return {
        "primary_need": (
            "Consistent expectations between both homes so Maya feels "
            "secure and doesn't have to pick a side."
        ),
        "whats_working": (
            "The bedtime routine works well with Maya — she anticipates "
            "the wind-down and settles quickly."
        ),
        "concerns": (
            "The rigid schedule is hard when family events come up on "
            "weekends. I feel like I'm always the flexible one."
        ),
        "desired_improvements": (
            "Consistent bedtimes and more predictable transitions on "
            "handoff days. A tiny bit more weekend flexibility."
        ),
        "options": (
            "Shared calendar with a monthly check-in call. Maybe a family "
            "therapist for tricky months."
        ),
        "other_parent_concerns": (
            "Probably worried about Maya feeling shuffled and the "
            "communication going quiet between exchanges."
        ),
    }


def sample_fixture() -> Tuple[
    str, str, str, str, Dict[str, Any], Dict[str, Any], Dict[str, str], Dict[str, str]
]:
    """Returns (share_id, parent_a_name, parent_b_name, child_name,
    agreement_a, agreement_b, reflections_a, reflections_b) for the
    public co-parenting sample."""
    return (
        SAMPLE_SHARE_ID,
        SAMPLE_PARENT_A_NAME,
        SAMPLE_PARENT_B_NAME,
        SAMPLE_CHILD_NAME,
        _sample_agreement_a(),
        _sample_agreement_b(),
        _sample_reflections_a(),
        _sample_reflections_b(),
    )


def build_sample_payload() -> Dict[str, Any]:
    """Assemble the full alignment-report payload the PDF renderer
    consumes. Wraps `joint_agreement.build_joint_agreement` so the
    sample uses EXACTLY the same code path a real merger uses — any
    future PDF change is guaranteed to flow through here."""
    from joint_agreement import build_joint_agreement
    share_id, a_name, b_name, child, agr_a, agr_b, refl_a, refl_b = sample_fixture()
    return build_joint_agreement(
        share_id=share_id,
        parent_a_name=a_name,
        parent_b_name=b_name,
        agreement_a=agr_a,
        agreement_b=agr_b,
        reflections_a=refl_a,
        reflections_b=refl_b,
        child_name=child,
    )


def build_sample_pdf_bytes() -> bytes:
    """One-call helper for the route: build the payload and render
    the PDF. Kept side-effect free so it's safe to warm up at import
    time if needed."""
    from joint_agreement_pdf import build_joint_agreement_pdf
    return build_joint_agreement_pdf(build_sample_payload())
