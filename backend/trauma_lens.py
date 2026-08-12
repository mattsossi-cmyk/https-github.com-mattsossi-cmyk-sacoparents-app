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

# Universal disclaimer that must appear prominently on every screen,
# PDF, and email that surfaces results from any assessment in this app.
# The wording deliberately positions this tool as a preparation aid, not
# an evaluation — so it is neither weaponised in litigation nor mistaken
# for a clinical or forensic finding.
SELF_REFLECTION_DISCLAIMER = (
    "This assessment is a guided self-reflection and preparation resource. "
    "It is not a clinical, forensic, legal, or professional evaluation. "
    "Its results are intended to help you identify concerns, organize your "
    "thinking, and prepare questions for an appropriate professional."
)

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


def build_findings(result: Dict[str, Any], extensions: Dict[str, Any] | None = None, section_1_answers: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Attach the three-findings structure to a scoring result.

    Non-destructive — always returns a fresh dict with the extra
    `findings` key so callers can render the lens without changing the
    underlying score.

    ``extensions`` is an optional dict produced from the Phase 3/4/5
    optional sections. When provided, it enriches the findings:

        * ``extensions["pattern_context"]``   -> reshapes Finding 1
          headline/summary with the typology label + framing produced
          by ``lens_extensions.classify_pattern``.
        * ``extensions["trauma_impact"]``     -> attaches per-domain
          intensity to Finding 2 (produced by
          ``lens_extensions.analyse_trauma_impact``).
        * ``extensions["child_experience"]``  -> produces a NEW
          Finding 4 (produced by ``lens_extensions.analyse_child_experience``).
    """
    level = int(result.get("level") or 4)
    level = max(1, min(4, level))
    pattern = _PATTERN_BY_LEVEL[level]
    trauma = _TRAUMA_BY_LEVEL[level]
    plan = _PLAN_BY_LEVEL[level]
    ext = extensions or {}
    findings: Dict[str, Any] = {
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
            "confidential": False,
        },
    }

    # ---- Phase 2: Coparenting Feasibility Spectrum on Finding 3 ----
    # Derive the tier from level + section-1 gap items + Phase-3
    # typology + Phase-5 child-experience. Attach to Finding 3 so the
    # co-parent's Compare view (which sees Finding 3) gets the tier
    # too — it's the ONE thing they need to know from this report.
    try:
        from feasibility_spectrum import recommend_tier
        pat_ctx = (ext.get("pattern_context") or {}) if ext else {}
        child_raw = (ext.get("child_experience_raw") or {}) if ext else {}
        tier = recommend_tier(
            level=level,
            section_1=section_1_answers or {},
            child_experience=child_raw,
            pattern_typology=pat_ctx.get("type"),
        )
        findings["parenting_plan_implications"]["feasibility_tier"] = tier
        # Override the arrangement_spectrum label with the tier's
        # richer descriptor so callers reading the legacy field still
        # get the improved language.
        findings["parenting_plan_implications"]["arrangement_spectrum"] = tier["label"]
    except Exception:  # noqa: BLE001
        pass

    # ---- Phase 3: Pattern & Context enrichment for Finding 1 ----
    pattern_ctx = ext.get("pattern_context") or {}
    if pattern_ctx.get("type") and pattern_ctx.get("answered", 0) >= 3:
        findings["family_violence_pattern"]["pattern_typology"] = {
            "type": pattern_ctx["type"],
            "label": pattern_ctx.get("label"),
            "framing": pattern_ctx.get("framing"),
        }

    # ---- Phase 4: Trauma Impact enrichment for Finding 2 ----
    trauma_impact = ext.get("trauma_impact") or {}
    if trauma_impact.get("answered", 0) >= 3:
        findings["trauma_impact"]["domain_signals"] = {
            "overall_intensity": trauma_impact.get("overall_intensity"),
            "domains": trauma_impact.get("domains") or {},
            "high_domains": trauma_impact.get("high_domains") or [],
        }

    # ---- Phase 5: Child Experience -> Finding 4 ----
    child_exp = ext.get("child_experience") or {}
    if child_exp.get("answered", 0) >= 3:
        findings["child_experience"] = {
            "title": "Finding 4 — Child Experience (parent's account)",
            "core_question": "What has the child(ren) experienced, and what protective resources exist?",
            "headline": child_exp.get("headline") or "",
            "summary": (
                "This finding reflects the parent's account of the children's "
                "experience — it is not an interview of the child. A qualified "
                "child specialist should conduct any direct assessment of the "
                "child using developmentally-appropriate methods."
            ),
            "overall": child_exp.get("overall"),
            "concern_domains": child_exp.get("concern_domains") or [],
            "protective_relationship_present": bool(child_exp.get("protective_relationship_present")),
            "high_concern": bool(child_exp.get("high_concern_ids")),
            "confidential": True,
        }

    return {
        "lens_name": LENS_NAME,
        "lens_short": LENS_SHORT,
        "interpretation_rules": list(INTERPRETATION_RULES),
        "findings": findings,
    }


# ---------- Court-report helpers ----------

COURT_REPORT_LIMITS_STATEMENT = (
    "This assessment is a guided self-reflection and preparation resource. "
    "It is not a clinical, forensic, legal, or professional evaluation. "
    "Its results are intended to help you identify concerns, organize your "
    "thinking, and prepare questions for an appropriate professional.\n\n"
    "This report is generated from a structured self-report screen "
    "completed by one parent. It is not a forensic family-violence evaluation, "
    "a psychological assessment, or a substitute for expert testimony. It is "
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
