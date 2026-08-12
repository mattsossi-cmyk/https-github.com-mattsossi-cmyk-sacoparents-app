"""Trauma-Informed Safety and Functioning Lens — Phase 2:
Coparenting Feasibility Spectrum.

Wires Finding 3 (Parenting-Plan Implications) to a six-tier arrangement
recommender with explicit thresholds derived from Section-1 gap items
and the Phase-3 pattern typology.

Tier ladder (highest structure -> lowest):

    T1 suspended_contact
       No direct contact between children and the offending parent while
       immediate safety issues are addressed. Any contact is filtered
       through a third party.

    T2 supervised_contact
       Parent-child contact happens only in the presence of a qualified
       supervisor (professional supervised-visitation service).

    T3 supervised_exchanges
       Parent has independent parenting time, but handoffs happen at a
       supervised exchange centre or through a neutral third party so
       the parents never come into direct contact.

    T4 parallel_parenting
       No direct communication between parents. Written-only, on a
       neutral platform, business tone, child-focused. Each parent
       makes day-to-day decisions in their own home without needing
       consensus.

    T5 structured_coparenting
       Direct communication is possible with clear guardrails: written
       agreements, defined exchange logistics, escalation pathway,
       scheduled review points.

    T6 cooperative_coparenting
       Flexible day-to-day communication, joint decisions, direct
       hand-offs. Appropriate when no coercive pattern is present.

Threshold logic reads from what the parent has already reported:

    * Section-1 gap items (s1_q19..s1_q28) — strangulation, firearms,
      sexual coercion, digital surveillance, financial abuse,
      substance-during-incidents, distinct homicide/suicide threats,
      current protective order.
    * pattern_typology from Phase 3 — coercive_controlling,
      violent_resistance, situational, separation_instigated, unclear.
    * child_experience (Phase 5) — direct victimisation of the child
      (ce_q1) is treated as an immediate escalation trigger.

Special handling for the *violent_resistance* typology: the tier is
shaped by the underlying coercive pattern reported by the OTHER
parent, not by the defensive/self-protective conduct of the answering
parent. So a violent_resistance typology defaults to at least
parallel_parenting — never lower — because the person the answering
parent is being protected FROM is the one who drives the structure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set


# ---------- Tier metadata ----------

TIER_META: Dict[str, Dict[str, Any]] = {
    "cooperative_coparenting": {
        "order": 6,
        "label": "Cooperative coparenting",
        "short": "cooperative",
        "structure_words": "flexible day-to-day communication, direct handoffs",
        "narrative": (
            "Ordinary cooperative coparenting appears feasible based on this "
            "snapshot. Both parents can be trusted to communicate directly "
            "and make joint decisions in real time. Revisit if circumstances "
            "change."
        ),
    },
    "structured_coparenting": {
        "order": 5,
        "label": "Highly structured coparenting",
        "short": "structured",
        "structure_words": "direct communication with written guardrails",
        "narrative": (
            "Direct coparenting is workable if it happens inside clear "
            "guardrails: written agreements, defined exchange logistics, "
            "and a scheduled review point in the plan. The structure is "
            "what makes the trust-building possible, not the other way around."
        ),
    },
    "parallel_parenting": {
        "order": 4,
        "label": "Parallel parenting with written-only communication",
        "short": "parallel",
        "structure_words": "written-only communication via a neutral platform",
        "narrative": (
            "Cooperative coparenting is not indicated while the reported "
            "pattern of control or intimidation is present. Parallel "
            "parenting — each parent making day-to-day decisions in their "
            "own home with written-only, business-tone communication on a "
            "neutral platform (e.g. OurFamilyWizard) — is the appropriate "
            "structure. The parents do not need consensus for routine "
            "in-home decisions."
        ),
    },
    "supervised_exchanges": {
        "order": 3,
        "label": "Supervised exchanges",
        "short": "supervised-exchanges",
        "structure_words": "handoffs at a supervised exchange centre or neutral third party",
        "narrative": (
            "Parenting time can continue but the parents must not come into "
            "direct contact. Handoffs happen at a supervised exchange "
            "centre or through a neutral third party. Parenting time itself "
            "is independent — supervision is limited to the transitions."
        ),
    },
    "supervised_contact": {
        "order": 2,
        "label": "Supervised contact",
        "short": "supervised-contact",
        "structure_words": "contact only in the presence of a qualified supervisor",
        "narrative": (
            "Parent-child contact should occur only in the presence of a "
            "qualified supervisor — typically a professional supervised "
            "visitation service. This protects the child while preserving "
            "the relationship. Review points should be short (30 to 90 days) "
            "with clear criteria for stepping down to a less-restrictive tier."
        ),
    },
    "suspended_contact": {
        "order": 1,
        "label": "Temporarily suspended contact",
        "short": "suspended",
        "structure_words": "no direct contact while immediate safety issues are addressed",
        "narrative": (
            "The reported items describe an immediate-danger picture. "
            "Direct contact between the offending parent and the child(ren) "
            "should be temporarily suspended while a qualified family-violence "
            "practitioner, DV service, or the court assesses next steps. "
            "This is a protective pause, not a permanent finding — the aim "
            "is to preserve the parent-child relationship inside a "
            "structure that keeps everyone safe first."
        ),
    },
}


TIER_ORDER = [
    "suspended_contact",
    "supervised_contact",
    "supervised_exchanges",
    "parallel_parenting",
    "structured_coparenting",
    "cooperative_coparenting",
]


def _tier_index(name: str) -> int:
    try:
        return TIER_ORDER.index(name)
    except ValueError:
        return len(TIER_ORDER) - 1  # default to least-restrictive


def _more_structured(a: str, b: str) -> str:
    """Return whichever of the two tiers is MORE structured (lower index)."""
    return a if _tier_index(a) < _tier_index(b) else b


# ---------- Threshold rules ----------

# Items that on a single "yes" push straight to suspended_contact.
_SUSPEND_TRIGGERS = {
    "ce_q1",     # child directly harmed by the other parent
    "s1_q25",    # distinct homicide threat
    "s1_q13",    # ever choked/strangled you (single strangulation is a
                 # strong DA predictor of severe/fatal outcome)
}

# Items that on a single "yes" push at LEAST to supervised_contact.
_SUPERVISED_CONTACT_TRIGGERS = {
    "s1_q19",    # strangulation pattern (more than once)
    "s1_q14",    # forced sexual activity
    "s1_q2",     # physically hurt / restrained
    "ce_q2",     # children exposed to physical violence / threats
}

# Items that on a single "yes" push at LEAST to supervised_exchanges.
_SUPERVISED_EXCHANGE_TRIGGERS = {
    "s1_q4",     # stalking / showing up unexpectedly
    "s1_q22",    # digital surveillance / spyware / GPS
    "s1_q20",    # firearms access
    "s1_q26",    # distinct suicide threat (esp. in context of leaving)
    "s1_q11",    # violence increasing in frequency/severity
}


def _norm(v: Any) -> str:
    return str(v or "").strip().lower()


def _yes(section: Dict[str, Any] | None, qid: str) -> bool:
    if not section:
        return False
    return _norm(section.get(qid)) == "yes"


def _any_yes(section: Dict[str, Any] | None, ids: Set[str] | List[str]) -> Set[str]:
    hits: Set[str] = set()
    if not section:
        return hits
    for qid in ids:
        if _yes(section, qid):
            hits.add(qid)
    return hits


def _level_baseline(level: int) -> str:
    """Baseline tier from the base level (before gap items or typology)."""
    if level <= 1:
        return "supervised_contact"
    if level == 2:
        return "parallel_parenting"
    if level == 3:
        return "structured_coparenting"
    return "cooperative_coparenting"


def _typology_floor(typology: str | None) -> str:
    """Minimum-structure floor implied by the pattern typology."""
    if typology == "coercive_controlling":
        return "parallel_parenting"
    if typology == "violent_resistance":
        # Shape structure by the UNDERLYING coercive pattern the answering
        # parent is being protected from — not by the defensive conduct
        # they reported. So we treat this as at least parallel too.
        return "parallel_parenting"
    if typology == "separation_instigated":
        return "structured_coparenting"
    if typology == "situational":
        return "structured_coparenting"
    return "cooperative_coparenting"


def recommend_tier(
    *,
    level: int,
    section_1: Dict[str, Any] | None = None,
    child_experience: Dict[str, Any] | None = None,
    pattern_typology: str | None = None,
) -> Dict[str, Any]:
    """Score a single feasibility tier from the available inputs.

    Returns a dict shaped as:

        {
          "tier": "parallel_parenting",
          "label": "...",
          "narrative": "...",
          "structure_words": "...",
          "order": 4,                     # 1 = most restrictive
          "triggers": ["s1_q19", ...],    # items that pushed the tier up
          "typology_floor": "parallel_parenting",
          "baseline_from_level": "structured_coparenting",
          "review_point_days": 90,
          "caveats": [...],
        }
    """
    tier = _level_baseline(int(level or 4))
    triggers: List[str] = []

    # Typology floor.
    floor = _typology_floor(pattern_typology)
    if _tier_index(floor) < _tier_index(tier):
        tier = floor

    # Section-1 gap items — bump the tier up when their triggers fire.
    exch_hits = _any_yes(section_1, _SUPERVISED_EXCHANGE_TRIGGERS)
    if exch_hits:
        tier = _more_structured(tier, "supervised_exchanges")
        triggers.extend(sorted(exch_hits))
    contact_hits = _any_yes(section_1, _SUPERVISED_CONTACT_TRIGGERS)
    if contact_hits:
        tier = _more_structured(tier, "supervised_contact")
        triggers.extend(sorted(contact_hits))
    suspend_hits_s1 = _any_yes(section_1, _SUSPEND_TRIGGERS - {"ce_q1"})
    if suspend_hits_s1:
        tier = _more_structured(tier, "suspended_contact")
        triggers.extend(sorted(suspend_hits_s1))

    # Child-experience triggers.
    if _yes(child_experience, "ce_q1"):
        tier = _more_structured(tier, "suspended_contact")
        triggers.append("ce_q1")
    if _yes(child_experience, "ce_q2"):
        tier = _more_structured(tier, "supervised_contact")
        triggers.append("ce_q2")

    meta = TIER_META[tier]

    # Review-point cadence — tighter tiers = shorter review windows.
    review_days = {
        "suspended_contact": 30,
        "supervised_contact": 60,
        "supervised_exchanges": 90,
        "parallel_parenting": 180,
        "structured_coparenting": 180,
        "cooperative_coparenting": 365,
    }[tier]

    caveats: List[str] = []
    if pattern_typology == "violent_resistance":
        caveats.append(
            "The typology on Finding 1 is violent-resistance / "
            "self-protective. The tier here is shaped by the underlying "
            "coercive pattern the answering parent reports being subject "
            "to — NOT by the defensive conduct they described. It is not "
            "a finding against the answering parent."
        )
    if triggers:
        caveats.append(
            "Structure was escalated by explicit safety items: "
            + ", ".join(sorted(set(triggers)))
            + ". A qualified family-violence practitioner should corroborate before implementation."
        )

    return {
        "tier": tier,
        "label": meta["label"],
        "short": meta["short"],
        "narrative": meta["narrative"],
        "structure_words": meta["structure_words"],
        "order": meta["order"],
        "triggers": sorted(set(triggers)),
        "typology_floor": floor,
        "baseline_from_level": _level_baseline(int(level or 4)),
        "review_point_days": review_days,
        "caveats": caveats,
    }
