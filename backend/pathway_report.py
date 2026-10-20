"""Dispute Resolution Pathway Report — deterministic scoring engine.

Design goals (from user brief):
  * NEVER prescribe ("you should mediate"). ALWAYS describe ("the combined
    assessment data indicates").
  * NEVER mutualise abuse — if the safety screen shows coercive control,
    physical safety concern, or a critical pathway, Litigation / Court
    Intervention becomes the primary AND only recommended pathway, and
    mediation is explicitly shown as "Low suitability — not recommended
    at this time".
  * ALWAYS show the reasoning — factors, considerations, and goals for
    each candidate pathway.
  * Every pathway comes with a suitability rating so a professional can
    see at a glance which options warrant consideration.

Public surface:
  * `SinglePartyContext` — bag of one parent's inputs (safety, ND risk,
    companion tiers, compliance streak).
  * `DualPartyContext` — bag of both parents' inputs plus compare
    alignment %.
  * `score_pathway_single(SinglePartyContext) -> PathwayResult`
  * `score_pathway_dual(DualPartyContext) -> PathwayResult`
  * `PathwayResult` — { primary_key, suitability, factors, considerations,
    goals, hard_locked_by, generated_at }

The scoring is deliberately conservative: when data is missing OR the
safety picture is uncertain, the algorithm prefers more structured
processes over less structured ones. It never nudges a family toward
litigation without a concrete safety trigger, but it also never nudges
a family toward mediation over a signal that could indicate risk.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


PATHWAYS = {
    "direct_negotiation": {
        "key":   "direct_negotiation",
        "label": "Direct negotiation",
        "one_liner": (
            "Parents work out parenting decisions between themselves, "
            "without a mediator or lawyer in the room. This is the least "
            "structured option and depends entirely on both parents being "
            "able to communicate calmly and reach child-focused agreements "
            "on their own."
        ),
    },
    "mediation": {
        "key":   "mediation",
        "label": "Mediation",
        "one_liner": (
            "Conflict is manageable, both parents can negotiate directly, "
            "and no safety or power-imbalance concerns are apparent from the "
            "assessment data."
        ),
    },
    "child_centered_mediation": {
        "key":   "child_centered_mediation",
        "label": "Child-Centered Relational Mediation",
        "one_liner": (
            "Both parents can participate, but conflict, communication, "
            "emotional reactivity, or child-impact concerns suggest a more "
            "structured, child-focused process."
        ),
    },
    "collaborative_law": {
        "key":   "collaborative_law",
        "label": "Collaborative Family Law",
        "one_liner": (
            "The family has more complex legal, financial, parenting, or "
            "emotional issues but both parents remain committed to avoiding "
            "court and working with an interdisciplinary professional team."
        ),
    },
    "litigation": {
        "key":   "litigation",
        "label": "Litigation / Court Intervention",
        "one_liner": (
            "The assessment data indicates substantial safety concerns, "
            "coercive control, severe power imbalance, persistent "
            "non-participation, or disputes requiring judicial findings or "
            "enforceable orders."
        ),
    },
}

# Ordered from least-to-most-adversarial. Used for stable rendering.
# Direct negotiation is included as a professional-facing baseline
# option — it is intentionally never the primary recommendation the
# algorithm nudges toward (see `_pick_primary` which excludes it from
# the primary tie-break: the least adversarial option we recommend is
# Mediation with a mediator in the room).
PATHWAY_ORDER = [
    "direct_negotiation",
    "mediation",
    "child_centered_mediation",
    "collaborative_law",
    "litigation",
]

SuitabilityLevel = str   # "high" | "moderate" | "low" | "not_indicated"


@dataclass
class SinglePartyContext:
    """One parent's slice of the input."""
    # Safety Screen result (as stored on `safety_assessments.result`)
    safety_level:              Optional[int]     = None          # 1..5 (1 = most restrictive)
    safety_pathway_title:      Optional[str]     = None
    safety_coercive_trigger:   bool              = False
    safety_physical_trigger:   bool              = False

    # Dimension Companion tiers — each is "aligned"|"stretch"|"strained" or None
    dim2_communication_tier:   Optional[str]     = None
    dim3_emotional_reg_tier:   Optional[str]     = None
    dim4_executive_fn_tier:    Optional[str]     = None

    # ND Risk assessment
    nd_risk_tier:              Optional[str]     = None          # "low"|"medium"|"high"|"critical"
    nd_risk_score:             Optional[int]     = None          # 1..16

    # Follow-through evidence
    compliance_streak_weeks:   int               = 0
    compliance_current_pct:    Optional[float]   = None

    # Optional identity for headings — never used for logic.
    display_name:              Optional[str]     = None


@dataclass
class DualPartyContext:
    """Both parents' inputs plus optional Compare alignment."""
    parent_a: SinglePartyContext
    parent_b: SinglePartyContext
    compare_alignment_pct:    Optional[float] = None    # 0..100
    child_centered_alignment: Optional[float] = None    # subset — child-focused items only, 0..100


@dataclass
class PathwayResult:
    primary_key:      str
    primary_label:    str
    suitability:      Dict[str, SuitabilityLevel]      # per-pathway
    factors:          List[str]
    considerations:   List[str]
    goals:            List[str]
    hard_locked_by:   List[str] = field(default_factory=list)
    generated_at:     str        = ""
    is_dual_party:    bool       = False

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "primary_pathway_key":   self.primary_key,
            "primary_pathway_label": self.primary_label,
            "primary_pathway_summary": PATHWAYS[self.primary_key]["one_liner"],
            "suitability_profile": [
                {
                    "key":         k,
                    "label":       PATHWAYS[k]["label"],
                    "suitability": self.suitability.get(k, "not_indicated"),
                }
                for k in PATHWAY_ORDER
            ],
            "factors_supporting_primary": self.factors,
            "considerations":             self.considerations,
            "goals_before_or_during":     self.goals,
            "hard_locked_by":             self.hard_locked_by,
            "generated_at":               self.generated_at,
            "is_dual_party":              self.is_dual_party,
        }


# ---------------------------------------------------------------------------
# Safety hard-lock check.
# ---------------------------------------------------------------------------

# Safety levels that force litigation as the sole primary (per product
# spec: level 1 = most restrictive / "court-required pathway"). Levels
# 2..5 do NOT auto-lock — they factor into scoring like any other input.
_HARD_LOCK_SAFETY_LEVELS = {1}


def _party_hard_lock_reasons(p: SinglePartyContext) -> List[str]:
    reasons: List[str] = []
    if p.safety_level in _HARD_LOCK_SAFETY_LEVELS:
        reasons.append(
            "Safety Screen resolved to a limited-contact / court-only pathway."
        )
    if p.safety_coercive_trigger:
        reasons.append(
            "A coercive-control indicator was flagged in the Safety Screen."
        )
    if p.safety_physical_trigger:
        reasons.append(
            "A physical-safety indicator was flagged in the Safety Screen."
        )
    return reasons


def _hard_locked_result(
    reasons: List[str], *, is_dual: bool, now_iso: str,
) -> PathwayResult:
    """Return a fully-formed result where litigation is the ONLY primary
    and mediation is explicitly disrecommended."""
    return PathwayResult(
        primary_key="litigation",
        primary_label=PATHWAYS["litigation"]["label"],
        suitability={
            "direct_negotiation":       "not_indicated",
            "mediation":                "not_indicated",
            "child_centered_mediation": "low",
            "collaborative_law":        "low",
            "litigation":               "high",
        },
        factors=list(reasons),
        considerations=[
            "This app never recommends mediation or a consensual process "
            "when the assessment data shows a safety trigger. Coercive "
            "control and physical-safety concerns require protections that "
            "voluntary processes may not provide.",
            "A qualified family-violence advocate, forensic psychologist, "
            "or family-law attorney should be consulted before any further "
            "step is taken.",
        ],
        goals=[
            "Prioritise safety planning with a qualified professional.",
            "Preserve documentation of concerning incidents and dates.",
            "Consult a family-law attorney about protective options in your "
            "jurisdiction.",
            "Where children are involved, seek a child-focused advocate.",
        ],
        hard_locked_by=list(reasons),
        generated_at=now_iso,
        is_dual_party=is_dual,
    )


# ---------------------------------------------------------------------------
# Signal helpers.
# ---------------------------------------------------------------------------

_TIER_STRAINED  = "strained"
_TIER_STRETCHED = "stretched"
_TIER_STEADY    = "steady"
_TIER_STRONG    = "strong"


def _tier_score(tier: Optional[str]) -> int:
    """Ordinal for Dimension Companion tiers (4-tier scale from
    `dimension_companion_routes.py`):

        strong    → 3   (best — aligned enough for direct negotiation)
        steady    → 2   (workable)
        stretched → 1   (mild strain — needs scaffolding)
        strained  → 0   (severe strain — voluntary process likely fragile)
        None      → 1   (unknown → conservative default = mild strain)

    Comparisons downstream use `>= 2` to mean "steady or better" and
    `<= 1` to mean "some strain present".
    """
    if tier == _TIER_STRONG:    return 3
    if tier == _TIER_STEADY:    return 2
    if tier == _TIER_STRETCHED: return 1
    if tier == _TIER_STRAINED:  return 0
    return 1


def _party_signals(p: SinglePartyContext) -> Dict[str, Any]:
    """Extract normalised signals from one parent's slice."""
    return {
        "communication":  _tier_score(p.dim2_communication_tier),
        "emotional_reg":  _tier_score(p.dim3_emotional_reg_tier),
        "executive_fn":   _tier_score(p.dim4_executive_fn_tier),
        "safety_level":   p.safety_level,
        "nd_tier":        p.nd_risk_tier,
        "compliance":     p.compliance_streak_weeks or 0,
    }


# ---------------------------------------------------------------------------
# Suitability computation.
# ---------------------------------------------------------------------------

def _classify_suitability(
    signals: List[Dict[str, Any]],
    *,
    compare_alignment: Optional[float],
    is_dual: bool,
) -> Dict[str, SuitabilityLevel]:
    """Return a {pathway_key: level} map.

    Rules (deliberately transparent — every branch has a comment
    explaining WHY):
      * MEDIATION requires low-friction indicators on both sides:
        communication + emotional-reg mostly aligned, no nd_tier ≥ high,
        no safety level ≤ 2, decent compare alignment (if dual).
      * CHILD-CENTERED MEDIATION is the sweet spot for parents who CAN
        participate but need scaffolding — either side has emotional-reg
        or communication strain, but neither has severe safety or nd risk.
      * COLLABORATIVE LAW upgrades from CCRM when both sides are showing
        elevated complexity (high nd_tier, safety level 3+ but not
        locked, low compare alignment, executive-function strain).
      * LITIGATION upgrades from Collaborative when the picture crosses
        into "critical" nd_tier, safety level 2, or clear persistent
        non-participation.
    """
    # Aggregate the worst signal from either party — the algorithm is
    # bounded by the more-strained side (a mediation only works as well
    # as the weaker link).
    worst_comm  = min(s["communication"] for s in signals)
    worst_er    = min(s["emotional_reg"] for s in signals)
    worst_ef    = min(s["executive_fn"] for s in signals)
    worst_safety = min(
        (s["safety_level"] for s in signals if s["safety_level"] is not None),
        default=5,
    )
    any_nd_high = any(
        (s["nd_tier"] or "").lower() in {"high", "critical"} for s in signals
    )
    any_nd_critical = any(
        (s["nd_tier"] or "").lower() == "critical" for s in signals
    )

    # Compare alignment — only relevant for dual-party analysis. For
    # single-party previews we pass through `None` (unknown), which
    # we treat as neutral by leaving `align_missing=True` so downstream
    # branches only fire on alignment for dual-party data.
    align_missing = compare_alignment is None
    align = compare_alignment if compare_alignment is not None else 60.0

    # ---- Mediation: needs BOTH sides mostly aligned + safe.
    # `>= 3` = "strong" only. `>= 2` = "steady or better".
    if (
        worst_comm >= 3
        and worst_er >= 3
        and worst_safety >= 4
        and not any_nd_high
        and (align_missing or align >= 75.0)
    ):
        mediation = "high"
    elif (
        worst_comm >= 2
        and worst_er >= 2
        and worst_safety >= 3
        and not any_nd_high
        and (align_missing or align >= 60.0)
    ):
        mediation = "moderate"
    elif worst_safety >= 3 and not any_nd_critical:
        mediation = "low"
    else:
        mediation = "not_indicated"

    # ---- Child-Centered Mediation: strain but participatory.
    # `<= 1` = "stretched or worse". Align-based boost only counts for
    # dual-party analyses — a missing single-parent value must not
    # elevate CCRM.
    if worst_safety >= 3 and not any_nd_critical and (
        worst_er <= 1
        or worst_comm <= 1
        or ((not align_missing) and align < 65.0)
    ):
        ccrm = "high"
    elif worst_safety >= 3 and not any_nd_critical:
        ccrm = "moderate"
    elif worst_safety >= 2 and not any_nd_critical:
        ccrm = "low"
    else:
        ccrm = "not_indicated"

    # ---- Collaborative Law: complex but committed.
    if (
        worst_safety >= 3
        and (any_nd_high or worst_ef <= 1)
        and not any_nd_critical
    ):
        collab = "high"
    elif worst_safety >= 2 and not any_nd_critical:
        collab = "moderate"
    elif worst_safety >= 2:
        collab = "low"
    else:
        collab = "not_indicated"

    # ---- Litigation: soft signal (not hard-locked; hard-lock is handled
    # earlier). Elevated when nd_tier is critical, safety level ≤ 2, or
    # complexity signals converge.
    if any_nd_critical or worst_safety <= 2:
        litigation = "high"
    elif worst_safety <= 3 and any_nd_high:
        litigation = "moderate"
    elif align < 40.0 and (worst_er == 0 or worst_comm == 0):
        litigation = "moderate"
    else:
        litigation = "low"

    # ---- Direct negotiation: strictly one notch below Mediation.
    # Direct negotiation asks parents to reach agreements with NO
    # mediator in the room, so it is always a more fragile option than
    # supported Mediation. We derive it by demoting the Mediation rating
    # by one level, floored at "not_indicated".
    _DEMOTE = {
        "high":          "moderate",
        "moderate":      "low",
        "low":           "not_indicated",
        "not_indicated": "not_indicated",
    }
    direct_negotiation = _DEMOTE[mediation]

    return {
        "direct_negotiation":       direct_negotiation,
        "mediation":                mediation,
        "child_centered_mediation": ccrm,
        "collaborative_law":        collab,
        "litigation":               litigation,
    }


_LEVEL_RANK = {"high": 3, "moderate": 2, "low": 1, "not_indicated": 0}


# Primary-pathway candidates. `direct_negotiation` is deliberately
# EXCLUDED: it is shown in the professional suitability profile for
# comparison but the app never nudges a family toward negotiating with
# no professional present — the recommended-primary space starts at
# Mediation.
_PRIMARY_CANDIDATES = [
    "mediation",
    "child_centered_mediation",
    "collaborative_law",
    "litigation",
]


def _pick_primary(suitability: Dict[str, SuitabilityLevel]) -> str:
    """Highest-rated pathway wins. Ties break toward the LEAST adversarial
    option — a policy choice the product committed to: never nudge a
    family toward more-adversarial than the data supports.

    `direct_negotiation` is not eligible as the primary recommendation
    (see `_PRIMARY_CANDIDATES` above).
    """
    best_key = "mediation"
    best_rank = -1
    for k in _PRIMARY_CANDIDATES:
        r = _LEVEL_RANK[suitability[k]]
        if r > best_rank:
            best_rank, best_key = r, k
    return best_key


# ---------------------------------------------------------------------------
# Rationale generators.
# ---------------------------------------------------------------------------

def _factors_for(
    primary: str,
    signals: List[Dict[str, Any]],
    compare_alignment: Optional[float],
    is_dual: bool,
) -> List[str]:
    """Assemble the "Factors supporting this pathway" bullet list.

    Language is intentionally clinical and observational — never
    prescriptive. Each bullet is derived from a specific signal in the
    assessment data so a mediator or family-law attorney reading the
    report can trace each claim back to its origin.
    """
    out: List[str] = []
    if is_dual:
        out.append(
            "Both parents have completed the underlying assessments and "
            "consented to share their combined data through the Compare flow."
        )
    else:
        out.append(
            "This preview reflects one parent's data only — the full "
            "professional report requires the co-parent's assessment data "
            "to be added."
        )

    # Signal helpers reused across pathway branches.
    worst_comm = min(s["communication"]  for s in signals)
    worst_er   = min(s["emotional_reg"]  for s in signals)
    worst_ef   = min(s["executive_fn"]   for s in signals)
    any_nd_high     = any((s["nd_tier"] or "").lower() in {"high", "critical"} for s in signals)
    any_nd_critical = any((s["nd_tier"] or "").lower() == "critical" for s in signals)

    def _comm_line() -> Optional[str]:
        if worst_comm <= 0:
            return "Significant communication breakdown is present between the parents."
        if worst_comm <= 1:
            return "Communication between the parents is strained and unlikely to hold under conflict without support."
        return None

    def _er_line() -> Optional[str]:
        if worst_er <= 0:
            return "Emotional reactivity appears severe enough to interfere with any real-time negotiation."
        if worst_er <= 1:
            return "Emotional reactivity appears to interfere with negotiation."
        return None

    def _ef_line() -> Optional[str]:
        if worst_ef <= 1:
            return "Executive-function strain is likely to affect follow-through on complex parenting logistics."
        return None

    def _align_line() -> Optional[str]:
        if compare_alignment is None:
            return None
        if compare_alignment < 40.0:
            return (
                f"Compare alignment on child-focused items is low "
                f"({compare_alignment:.0f}%) — the parents disagree substantially "
                f"about the child's needs."
            )
        if compare_alignment < 65.0:
            return (
                f"Compare alignment on child-focused items is moderate "
                f"({compare_alignment:.0f}%) — there is meaningful disagreement "
                f"about the child's needs."
            )
        return (
            f"Compare alignment on child-focused items sits at "
            f"{compare_alignment:.0f}%."
        )

    if primary == "mediation":
        out.append("Communication and emotional-regulation dimensions are in a workable range on both sides.")
        line = _align_line()
        if line:
            out.append(line)
        out.append("Both parents demonstrate willingness to remain involved in the child's life.")

    elif primary == "child_centered_mediation":
        for line in (_comm_line(), _er_line(), _align_line()):
            if line:
                out.append(line)
        if any_nd_high:
            out.append(
                "A neurodivergent-coparenting risk signal is present — a "
                "child-focused, structured process better accommodates the "
                "cognitive load involved."
            )
        out.append("Both parents demonstrate willingness to remain involved in the child's life.")
        out.append(
            "Neither parent's assessment presently indicates a barrier "
            "requiring immediate court-only intervention."
        )

    elif primary == "collaborative_law":
        for line in (_comm_line(), _er_line(), _ef_line(), _align_line()):
            if line:
                out.append(line)
        if any_nd_high and not any_nd_critical:
            out.append(
                "An elevated ND-risk tier is present — a collaborative team "
                "including a mental-health coach and a child specialist is "
                "well-suited to the cognitive and emotional complexity."
            )
        out.append("Both parents remain committed to avoiding court where possible.")
        out.append(
            "The complexity of legal, financial, and parenting issues warrants "
            "an interdisciplinary team rather than a single mediator."
        )

    elif primary == "litigation":
        # Note: hard-lock reasons are surfaced separately (`hard_locked_by`);
        # this branch handles the soft-signal path where litigation wins
        # without a Safety Screen trigger firing.
        if any_nd_critical:
            out.append(
                "A critical ND-risk tier is present in the assessment data — "
                "consensual processes are unlikely to provide the structural "
                "protections the situation appears to require."
            )
        er_line = _er_line()
        if er_line:
            out.append(er_line)
        comm_line = _comm_line()
        if comm_line:
            out.append(comm_line)
        out.append(
            "Voluntary processes may not provide the enforceability or "
            "third-party oversight the situation warrants."
        )

    return out


def _considerations_for(primary: str, is_dual: bool) -> List[str]:
    out: List[str] = []
    if not is_dual:
        out.append(
            "This is a single-parent preview. A full pathway analysis "
            "requires both parents to complete the assessments and consent "
            "to share their results."
        )
    out.append(
        "This is not legal advice, a psychological determination, or a "
        "mediator's opinion. A qualified professional should review this "
        "data alongside their own assessment before any process is "
        "selected."
    )
    if primary in {"mediation", "child_centered_mediation", "collaborative_law"}:
        out.append(
            "If either parent's circumstances change — a safety incident, "
            "a change in mental-health status, a new family violence "
            "concern — this recommendation should be re-evaluated."
        )
    return out


def _goals_for(primary: str) -> List[str]:
    if primary == "mediation":
        return [
            "Confirm both parents can identify and articulate the child's needs.",
            "Establish written ground rules for negotiation sessions.",
            "Agree an initial scope of decisions to work through together.",
        ]
    if primary == "child_centered_mediation":
        return [
            "Establish child-focused communication rules.",
            "Identify the child's developmental and emotional needs.",
            "Separate unresolved relationship conflict from parenting decisions.",
            "Develop a structured parenting decision-making process.",
            "Create measurable agreements regarding communication and consistency between homes.",
        ]
    if primary == "collaborative_law":
        return [
            "Engage a collaborative attorney for each parent.",
            "Add specialists as needed — child specialist, mental-health coach, financial neutral.",
            "Commit in writing to keeping the process out of court.",
            "Map the full set of legal, parenting, and financial issues before negotiating.",
        ]
    # litigation
    return [
        "Prioritise safety planning with a qualified professional.",
        "Preserve documentation of concerning incidents and dates.",
        "Consult a family-law attorney about protective options in your jurisdiction.",
        "Where children are involved, seek a child-focused advocate.",
    ]


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_pathway_single(p: SinglePartyContext) -> PathwayResult:
    """One-parent preview — SAFETY-CROSS-CHECKED against the caller's own
    Safety Screen (hard-locks apply)."""
    now = _now_iso()
    reasons = _party_hard_lock_reasons(p)
    if reasons:
        return _hard_locked_result(reasons, is_dual=False, now_iso=now)

    signals = [_party_signals(p)]
    suitability = _classify_suitability(
        signals, compare_alignment=None, is_dual=False,
    )
    primary = _pick_primary(suitability)
    return PathwayResult(
        primary_key=primary,
        primary_label=PATHWAYS[primary]["label"],
        suitability=suitability,
        factors=_factors_for(primary, signals, None, False),
        considerations=_considerations_for(primary, False),
        goals=_goals_for(primary),
        hard_locked_by=[],
        generated_at=now,
        is_dual_party=False,
    )


def score_pathway_dual(ctx: DualPartyContext) -> PathwayResult:
    """Full 2-parent report — hard-lock if EITHER parent's Safety Screen
    trips a lock condition."""
    now = _now_iso()
    reasons = (
        _party_hard_lock_reasons(ctx.parent_a)
        + _party_hard_lock_reasons(ctx.parent_b)
    )
    if reasons:
        return _hard_locked_result(reasons, is_dual=True, now_iso=now)

    signals = [_party_signals(ctx.parent_a), _party_signals(ctx.parent_b)]
    align = ctx.child_centered_alignment
    if align is None:
        align = ctx.compare_alignment_pct
    suitability = _classify_suitability(
        signals, compare_alignment=align, is_dual=True,
    )
    primary = _pick_primary(suitability)
    return PathwayResult(
        primary_key=primary,
        primary_label=PATHWAYS[primary]["label"],
        suitability=suitability,
        factors=_factors_for(primary, signals, align, True),
        considerations=_considerations_for(primary, True),
        goals=_goals_for(primary),
        hard_locked_by=[],
        generated_at=now,
        is_dual_party=True,
    )
