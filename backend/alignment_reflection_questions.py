"""Alignment reflection prompts — Iter191.

Six free-text prompts modelled on sacoparentsalign.com's Joint Alignment
Report. Each parent answers these privately; the analysis engine
(`alignment_reflection_analysis.py`) then produces the "Both parents
mentioned 'consistent' when describing desired improvements..." style
verbatim quotes that populate SS2 (What Both Agree) and SS3 (Where
Perspectives Differ) of the report.

Phase 1 scope: General Co-Parenting subject only. Multi-subject rollout
(Communication / Medical / Educational / Safety) lands in a follow-up
iteration and reuses the same 6-prompt shape.

Product principles baked in:
  * Every prompt is CHILD-FOCUSED, not parent-focused (never "what
    frustrates you" — always "what does the child need").
  * Neutral wording — never assumes conflict, never implies one parent
    is more responsible than the other.
  * Optional in every field — a blank answer is a valid answer and the
    analysis engine handles missing/empty answers gracefully.
"""
from __future__ import annotations

from typing import Any, Dict, List


# Prompt IDs are stable strings that the DB, analysis engine, and PDF
# all key off. Never rename an ID without a data migration — parents
# who saved partial answers key their responses by prompt_id.
PROMPT_PRIMARY_NEED           = "primary_need"
PROMPT_WHATS_WORKING          = "whats_working"
PROMPT_CONCERNS               = "concerns"
PROMPT_DESIRED_IMPROVEMENTS   = "desired_improvements"
PROMPT_OPTIONS                = "options"
PROMPT_OTHER_PARENT_CONCERNS  = "other_parent_concerns"


SUBJECT_CO_PARENTING = "co_parenting"


# Ordered prompt list for the "General Co-Parenting" subject. Order is
# UX-critical — the form renders them in this exact order and the PDF
# analysis section references them in the same sequence.
CO_PARENTING_PROMPTS: List[Dict[str, str]] = [
    {
        "id":          PROMPT_PRIMARY_NEED,
        "label":       "Your child's primary need",
        "prompt":      "What is your child's primary need right now, in your own words?",
        "placeholder": "Predictability, consistency, feeling safe in both homes...",
        "help":        (
            "Focus on what your child needs — not what you or the other "
            "parent needs from each other."
        ),
        "max_length":  600,
    },
    {
        "id":          PROMPT_WHATS_WORKING,
        "label":       "What's already working",
        "prompt":      "What is currently working well for your child across both homes?",
        "placeholder": "Bedtime routines, shared homework tracker, weekend calls...",
        "help":        (
            "Naming what's working reminds both parents you're already "
            "aligned on more than you think."
        ),
        "max_length":  600,
    },
    {
        "id":          PROMPT_CONCERNS,
        "label":       "Your concerns",
        "prompt":      "What concerns do you have about co-parenting arrangements for your child?",
        "placeholder": "Screen-time rules changing without notice, homework routine drift...",
        "help":        (
            "Say it plainly — the mediator or professional never sees "
            "whose concern it was, only the shared themes."
        ),
        "max_length":  600,
    },
    {
        "id":          PROMPT_DESIRED_IMPROVEMENTS,
        "label":       "Desired improvements",
        "prompt":      "What improvements would you most like to see for your child?",
        "placeholder": "More consistent expectations between homes, calmer transitions...",
        "help":        (
            "Improvements you name here become the shared vocabulary "
            "for options in Section 7 of the report."
        ),
        "max_length":  600,
    },
    {
        "id":          PROMPT_OPTIONS,
        "label":       "Options you would consider",
        "prompt":      "What options or approaches would you consider to move forward?",
        "placeholder": "Shared calendar, monthly check-ins, written co-parenting protocol...",
        "help":        (
            "Neutral options only — no ultimatums. The report presents "
            "these as candidates, not demands."
        ),
        "max_length":  600,
    },
    {
        "id":          PROMPT_OTHER_PARENT_CONCERNS,
        "label":       "The other parent's likely concerns",
        "prompt":      (
            "What do you think the other parent's likely concerns are — "
            "in their own words, not yours?"
        ),
        "placeholder": "They probably worry about the weekend schedule flexibility...",
        "help":        (
            "This is empathy practice, not concession. Naming their "
            "perspective in your own words builds surprising alignment."
        ),
        "max_length":  600,
    },
]


SUBJECTS: Dict[str, Dict[str, Any]] = {
    SUBJECT_CO_PARENTING: {
        "id":      SUBJECT_CO_PARENTING,
        "label":   "General Co-Parenting",
        "blurb":   (
            "Routines, rules, and day-to-day decisions across both homes."
        ),
        "prompts": CO_PARENTING_PROMPTS,
    },
}


def prompts_for(subject: str) -> List[Dict[str, str]]:
    """Return the ordered prompt list for a subject. Unknown subjects
    return an empty list — callers should validate before calling."""
    return list(SUBJECTS.get(subject, {}).get("prompts") or [])


def prompt_ids_for(subject: str) -> List[str]:
    return [p["id"] for p in prompts_for(subject)]


def is_known_subject(subject: str) -> bool:
    return subject in SUBJECTS


def find_prompt(subject: str, prompt_id: str) -> Dict[str, Any] | None:
    for p in prompts_for(subject):
        if p["id"] == prompt_id:
            return p
    return None
