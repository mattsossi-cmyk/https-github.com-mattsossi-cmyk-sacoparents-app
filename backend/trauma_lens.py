"""Trauma-Informed Safety and Functioning Lens (TISFL).

This module holds the interpretive framework for the SA CoParents Family
Violence & Communication Safety Assessment. The lens keeps three
findings *separate* rather than collapsing them into a single
"coparenting score":

    1. Family-Violence Pattern
       What conduct occurred, in what context, and with what pattern of
       power and control? (Sourced from Section 1 + coercive-control /
       high-concern hits.)

    2. Trauma Impact
       How has the conduct affected each parent and child? Uses
       communication-readiness signals as a *proxy* for functional
       impact, deliberately avoiding diagnostic language.

    3. Parenting-Plan Implications
       What structure and protections are presently necessary? This is
       the ONLY finding shared with the co-parent in the Compare view —
       Findings 1 and 2 stay private to protect survivors.

The two interpretation rules below must be surfaced anywhere the
lens's output is rendered (PDF, results page, email, court report):

    (a) Trauma symptoms are not evidence that a parent is unreliable,
        unfit, or responsible for the violence.
    (b) A history of trauma does not excuse coercion, intimidation,
        child maltreatment, or other harmful parenting behavior.

Design notes:
    * Non-diagnostic. Never labels PTSD, personality disorders, etc.
    * Never mutualises abuse — the pattern finding names the coercive
      party's conduct, not "conflict between the parents".
    * Language is calibrated to the four existing levels 1..4 from
      `score_assessment()` in `safety_assessment_routes.py`.
"""
from __future__ import annotations

from typing import Any, Dict, List


LENS_NAME = "Trauma-Informed Safety and Functioning Lens"
LENS_SHORT = "TISFL"

INTERPRETATION_RULES: List[str] = [
    "Trauma symptoms are not evidence that a parent is unreliable, unfit, or responsible for the violence.",
    "A history of trauma does not excuse coercion, intimidation, child maltreatment, or other harmful parenting behavior.",
]

PROCEDURAL_SAFEGUARDS: List[str] = [
    "Each parent completes this assessment separately. Answers are private and are never shared with the other parent unless you choose to.",
    "You can pause at any time. If a question raises a strong reaction, step away, breathe, and return when you're ready.",
    "This tool does not diagnose. It does not label either parent. It reflects behaviour and safety signals — not personality or worth.",
    "Safety information is walled off from the Compare view. Your co-parent will only see the parenting-plan implications, never your pattern or trauma details.",
    "If you're in immediate danger, this tool is not a substitute for calling 000 (AU) or a domestic-violence service.",
]


# ---------- Finding 1: Family-Violence Pattern ----------

_PATTERN_BY_LEVEL: Dict[int, Dict[str, str]] = {
    1: {
        "headline": "Serious safety concerns present",
        "summary": (
            "One or more items flagged that indicate serious risk to physical or "
            "psychological safety — for example strangulation, weapons, threats "
            "to kill, or child-directed harm. This assessment does not itself "
            "constitute a forensic finding, but the pattern reported meets the "
            "threshold that most family-violence frameworks treat as high-danger."
        ),
    },
    2: {
        "headline": "Coercive-control pattern indicated",
        "summary": (
            "Items reported point to a pattern of controlling behaviour — for "
            "example monitoring, isolation, financial control, intimidation, or "
            "post-separation escalation. Coercive control is a distinct pattern "
            "from isolated conflict and typically requires structured, written "
            "communication only."
        ),
    },
    3: {
        "headline": "Significant communication-safety friction",
        "summary": (
            "No high-severity or coercive items were reported, but multiple "
            "communication-readiness signals are strained. This may reflect "
            "high-conflict dynamics, situational conflict, or the aftermath of "
            "separation-instigated incidents rather than an ongoing pattern of "
            "power and control."
        ),
    },
    4: {
        "headline": "No family-violence pattern indicated at this time",
        "summary": (
            "No high-severity, coercive-control, or significant communication "
            "concerns were reported. This is a snapshot in time — the pattern "
            "finding should be revisited if circumstances change."
        ),
    },
}


# ---------- Finding 2: Trauma Impact ----------

_TRAUMA_BY_LEVEL: Dict[int, Dict[str, str]] = {
    1: {
        "headline": "Functional impact consistent with a high-danger environment",
        "summary": (
            "The pattern reported is the kind that produces hypervigilance, "
            "avoidance, sleep disruption, emotional flooding, and fear-based "
            "communication in adults and children. These responses are protective "
            "adaptations to danger, not evidence of unfitness. They are not "
            "diagnosed here — they are noted so the parenting plan can build "
            "in pacing, predictability, and safety."
        ),
    },
    2: {
        "headline": "Functional impact consistent with ongoing coercive stress",
        "summary": (
            "Living inside a controlling dynamic — even without physical assault "
            "— commonly produces chronic stress responses that look like "
            "hostility, memory fragmentation, or avoidance from the outside. "
            "This is context, not a character flaw. It informs how communication "
            "and exchanges should be structured."
        ),
    },
    3: {
        "headline": "Elevated stress signals in the communication space",
        "summary": (
            "The signals reported are more consistent with high-conflict or "
            "post-separation stress than with a coercive pattern. Structured "
            "communication tools, pacing, and clearer written agreements often "
            "reduce these signals over time."
        ),
    },
    4: {
        "headline": "No trauma-impact signals reported at this time",
        "summary": (
            "No significant fear-based or stress-response signals were reported "
            "in the communication readiness items. This should be revisited if "
            "circumstances change."
        ),
    },
}


# ---------- Finding 3: Parenting-Plan Implications (safe to share) ----------

_PLAN_BY_LEVEL: Dict[int, Dict[str, Any]] = {
    1: {
        "headline": "Structured, safety-first arrangements are indicated",
        "summary": (
            "Ordinary or cooperative coparenting is not indicated at this time. "
            "The parenting arrangement should assume safety planning as a first "
            "principle."
        ),
        "arrangement_spectrum": "supervised-exchange to supervised-contact",
    },
    2: {
        "headline": "Parallel parenting with written-only communication is indicated",
        "summary": (
            "Cooperative coparenting is not indicated. Parallel parenting — "
            "each parent making day-to-day decisions in their own home with "
            "written-only, business-tone communication — is the appropriate "
            "structure while the coercive-control pattern remains."
        ),
        "arrangement_spectrum": "parallel parenting with structured written communication",
    },
    3: {
        "headline": "Highly structured coparenting with clear guardrails",
        "summary": (
            "Ordinary coparenting can be attempted with strong structure: "
            "written agreements, defined exchange logistics, and a clear "
            "escalation pathway. Revisit if friction escalates or new safety "
            "signals emerge."
        ),
        "arrangement_spectrum": "highly structured coparenting",
    },
    4: {
        "headline": "Ordinary coparenting appears feasible at this time",
        "summary": (
            "Ordinary cooperative coparenting appears feasible based on this "
            "snapshot. Revisit if circumstances change."
        ),
        "arrangement_spectrum": "cooperative coparenting",
    },
}


def build_findings(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach the three-findings structure to a scoring result.

    Non-destructive — always returns a fresh dict with the extra
    `findings` key so callers can render the lens without changing the
    underlying score.
    """
    level = int(result.get("level") or 4)
    level = max(1, min(4, level))
    pattern = _PATTERN_BY_LEVEL[level]
    trauma = _TRAUMA_BY_LEVEL[level]
    plan = _PLAN_BY_LEVEL[level]
    return {
        "lens_name": LENS_NAME,
        "lens_short": LENS_SHORT,
        "interpretation_rules": list(INTERPRETATION_RULES),
        "findings": {
            "family_violence_pattern": {
                "title": "Finding 1 — Family-Violence Pattern",
                "core_question": "What conduct occurred, in what context, and with what pattern of power and control?",
                "headline": pattern["headline"],
                "summary": pattern["summary"],
                "confidential": True,
            },
            "trauma_impact": {
                "title": "Finding 2 — Trauma Impact",
                "core_question": "How has the conduct affected each parent and child?",
                "headline": trauma["headline"],
                "summary": trauma["summary"],
                "confidential": True,
                "non_diagnostic_note": (
                    "This finding does not diagnose PTSD or any other condition. "
                    "It reflects behavioural and functional signals only."
                ),
            },
            "parenting_plan_implications": {
                "title": "Finding 3 — Parenting-Plan Implications",
                "core_question": "What structure and protections are presently necessary?",
                "headline": plan["headline"],
                "summary": plan["summary"],
                "arrangement_spectrum": plan["arrangement_spectrum"],
                "confidential": False,  # This is the one the co-parent may see.
            },
        },
    }


# ---------- Court-report helpers ----------

COURT_REPORT_LIMITS_STATEMENT = (
    "Limits of use. This report is generated from a structured self-report screen "
    "completed by one parent. It is not a forensic family-violence evaluation, a "
    "psychological assessment, or a substitute for expert testimony. It is "
    "intended to help the court and practitioners frame safety and parenting-plan "
    "structure using the Trauma-Informed Safety and Functioning Lens (TISFL). "
    "Findings should be corroborated with other evidence before being relied on."
)

COURT_REPORT_METHODOLOGY = (
    "The lens keeps three findings separate rather than collapsing them into a "
    "single coparenting score. Finding 1 (Family-Violence Pattern) is derived "
    "from the presence of high-concern behaviours and coercive-control items "
    "reported in Section 1. Finding 2 (Trauma Impact) is derived from "
    "communication-readiness signals in Section 2 and is presented as "
    "behavioural context, not a diagnosis. Finding 3 (Parenting-Plan "
    "Implications) is the recommended parenting-plan structure spectrum given "
    "Findings 1 and 2 combined."
)


def redact_for_compare(findings_block: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the lens block that only includes Finding 3.

    Used when rendering the SNC2 Compare view for the other parent —
    the pattern and trauma findings must never leak to the co-parent
    per the existing survivor-protection rule.
    """
    if not findings_block or not isinstance(findings_block, dict):
        return {}
    findings = findings_block.get("findings") or {}
    plan = findings.get("parenting_plan_implications")
    if not plan:
        return {}
    return {
        "lens_name": findings_block.get("lens_name", LENS_NAME),
        "lens_short": findings_block.get("lens_short", LENS_SHORT),
        "interpretation_rules": list(findings_block.get("interpretation_rules") or INTERPRETATION_RULES),
        "findings": {"parenting_plan_implications": dict(plan)},
        "redacted": True,
        "redaction_note": (
            "The Family-Violence Pattern and Trauma Impact findings are private "
            "to the parent who completed the assessment and are not shown here."
        ),
    }
