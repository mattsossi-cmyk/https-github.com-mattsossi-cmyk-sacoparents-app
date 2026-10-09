"""Alignment reflection prompts — Iter191.

Six free-text prompts modelled on sacoparentsalign.com's Co-Parenting
Agreement. Each parent answers these privately; the analysis engine
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
SUBJECT_COMMUNICATION = "communication"
SUBJECT_MEDICAL       = "medical"
SUBJECT_EDUCATIONAL   = "educational"
SUBJECT_SAFETY        = "safety"


def _prompts(subject_label: str, subject_focus: str, placeholders: List[str]) -> List[Dict[str, Any]]:
    """Build the 6-prompt list for a subject with subject-scoped
    labels + placeholders but the same 6 prompt IDs and shape. Keeps
    the analysis engine subject-agnostic — every subject uses the
    same overlap detection code."""
    labels = [
        ("Your child's primary need",
         f"What is your child's primary need right now, specifically around {subject_focus}?"),
        ("What's already working",
         f"What is currently working well for your child around {subject_focus}?"),
        ("Your concerns",
         f"What concerns do you have about {subject_focus} for your child?"),
        ("Desired improvements",
         f"What improvements would you most like to see around {subject_focus}?"),
        ("Options you would consider",
         f"What options or approaches would you consider around {subject_focus}?"),
        ("The other parent's likely concerns",
         f"What do you think the other parent's likely concerns are about {subject_focus} — in their own words, not yours?"),
    ]
    help_text = [
        "Focus on what your child needs — not what you or the other parent needs from each other.",
        "Naming what's working reminds both parents you're already aligned on more than you think.",
        "Say it plainly — the mediator or professional never sees whose concern it was, only the shared themes.",
        f"Improvements you name here shape the {subject_label} conversation options in Section 7 of the report.",
        "Neutral options only — no ultimatums. The report presents these as candidates, not demands.",
        "This is empathy practice, not concession. Naming their perspective in your own words builds surprising alignment.",
    ]
    prompt_ids = [
        PROMPT_PRIMARY_NEED, PROMPT_WHATS_WORKING, PROMPT_CONCERNS,
        PROMPT_DESIRED_IMPROVEMENTS, PROMPT_OPTIONS, PROMPT_OTHER_PARENT_CONCERNS,
    ]
    return [
        {
            "id":          prompt_ids[i],
            "label":       labels[i][0],
            "prompt":      labels[i][1],
            "placeholder": placeholders[i],
            "help":        help_text[i],
            "max_length":  600,
        }
        for i in range(6)
    ]


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


COMMUNICATION_PROMPTS = _prompts(
    subject_label="communication",
    subject_focus="how the two of you communicate about your child",
    placeholders=[
        "Clear, calm updates about school, health, and routines...",
        "Weekly handoff text, shared photo album, birthday coordination...",
        "Text tone escalating, updates going missing, last-minute changes...",
        "A predictable weekly update ritual, no venting through the child...",
        "Shared parenting app, weekly Sunday check-in, written summaries...",
        "They probably worry about being cut out of school or medical updates...",
    ],
)


MEDICAL_PROMPTS = _prompts(
    subject_label="medical",
    subject_focus="your child's medical needs and healthcare decisions",
    placeholders=[
        "Timely medication, aligned care plans across homes, shared symptom log...",
        "Both homes stock the inhaler, doctor updates go to both parents...",
        "Missing follow-ups, conflicting med schedules, appointments not shared...",
        "A shared medical folder, aligned dosage timing, both parents in the loop...",
        "Shared patient portal access, quarterly care review with the pediatrician...",
        "They probably worry about being cut out of urgent-care decisions...",
    ],
)


EDUCATIONAL_PROMPTS = _prompts(
    subject_label="educational",
    subject_focus="your child's education, school, and learning support",
    placeholders=[
        "Consistent homework routine, teacher access, IEP or 504 support...",
        "Both parents attend parent-teacher conferences, homework kit at each home...",
        "Homework routine drift, missed school forms, unequal school involvement...",
        "Both parents on the school portal, aligned bedtime on school nights...",
        "Shared school calendar, joint teacher meetings, tutor coordination...",
        "They probably worry about missing school events or being left off the emergency list...",
    ],
)


SAFETY_PROMPTS = _prompts(
    subject_label="safety",
    subject_focus="your child's physical and emotional safety",
    placeholders=[
        "Feeling safe expressing feelings, physical safety, no exposure to adult conflict...",
        "Both homes calm during handoffs, no adult conflict in front of the child...",
        "Specific incidents or patterns you'd like a professional to weigh in on...",
        "Handoffs feel calmer, adult conflict stays away from the child...",
        "Neutral handoff location, involving a family therapist, professional consult...",
        "They probably worry about the other home's environment during transitions...",
    ],
)


SUBJECTS: Dict[str, Dict[str, Any]] = {
    SUBJECT_CO_PARENTING: {
        "id":      SUBJECT_CO_PARENTING,
        "label":   "General Co-Parenting",
        "blurb":   (
            "Routines, rules, and day-to-day decisions across both homes."
        ),
        "prompts":  CO_PARENTING_PROMPTS,
        "sensitive": False,
    },
    SUBJECT_COMMUNICATION: {
        "id":      SUBJECT_COMMUNICATION,
        "label":   "Communication",
        "blurb":   (
            "How the two of you exchange updates, decisions, and "
            "day-to-day information about your child."
        ),
        "prompts":  COMMUNICATION_PROMPTS,
        "sensitive": False,
    },
    SUBJECT_MEDICAL: {
        "id":      SUBJECT_MEDICAL,
        "label":   "Medical",
        "blurb":   (
            "Coordinating your child's medical care, medications, and "
            "healthcare decisions across both homes."
        ),
        "prompts":  MEDICAL_PROMPTS,
        "sensitive": False,
    },
    SUBJECT_EDUCATIONAL: {
        "id":      SUBJECT_EDUCATIONAL,
        "label":   "Educational",
        "blurb":   (
            "School, learning support, homework routines, and school "
            "communication."
        ),
        "prompts":  EDUCATIONAL_PROMPTS,
        "sensitive": False,
    },
    SUBJECT_SAFETY: {
        "id":      SUBJECT_SAFETY,
        "label":   "Safety",
        "blurb":   (
            "Your child's physical and emotional safety. Handled with "
            "extra care — Safety answers are never shared with your "
            "co-parent unless BOTH of you explicitly opt in."
        ),
        "prompts":   SAFETY_PROMPTS,
        # Safety-sensitive subjects require an EXPLICIT dual-consent flag
        # on `/compare` (see `alignment_reflection_routes.py`), and are
        # NEVER auto-merged into `build_joint_agreement`. This mirrors
        # sacoparentsalign's "IPV and Family-Violence Safety" carve-out.
        "sensitive": True,
    },
}


def is_sensitive_subject(subject: str) -> bool:
    """True for subjects that require explicit dual-consent before any
    cross-parent comparison. Safety is the only sensitive subject in
    Phase 2; kept as a function so future high-conflict / IPV subjects
    can opt in with a single flag."""
    return bool(SUBJECTS.get(subject, {}).get("sensitive"))


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
