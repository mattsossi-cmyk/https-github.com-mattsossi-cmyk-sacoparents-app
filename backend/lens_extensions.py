"""Trauma-Informed Safety and Functioning Lens — Phase 3/4/5 extensions.

Adds three optional data-collection sections that enrich the lens
findings *without* replacing the base level (1-4) scoring:

  * Pattern & Context      -> reshapes Finding 1 (Family-Violence Pattern)
  * Trauma Impact          -> reshapes Finding 2 (Trauma Impact)
  * Child Experience       -> produces a NEW Finding 4 (Child Experience)

All three sections are OPTIONAL. Skipping is a first-class action —
this matters for trauma pacing.

Question numbering convention:
  p_q1..p_q8      pattern_context      (Phase 3)
  ti_q1..ti_q10   trauma_impact        (Phase 4)
  ce_q1..ce_q10   child_experience     (Phase 5)

Every question answer is Yes / No / Unsure (case-insensitive), or the
special value "skipped" when the parent elects not to complete that
section. `analyse_*` functions treat missing / unknown values the same
way they treat "unsure" — as low-confidence signal — so the classifier
never punishes a parent for pacing themselves.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ---------- Phase 3: Pattern & Context screen ----------
#
# Distinguishes four family-violence patterns per the Kelly & Johnson
# typology often referenced by AFCC:
#
#   (a) coercive_controlling   ongoing, cross-domain power & control
#   (b) violent_resistance     defensive/self-protective in response to (a)
#   (c) situational            mutual, incident-based, no power motive
#   (d) separation_instigated  emerged around separation, may be transient
#
# The questions are phrased in the parent's own voice and are
# behavioural, not diagnostic. We never ask the parent to label
# themselves — the classifier does that from behavioural markers.

PATTERN_CONTEXT_QUESTIONS: List[Dict[str, Any]] = [
    # Coercive control markers.
    {
        "id": "p_q1",
        "text": "Does the other parent monitor your movements, communications, finances, or friendships in a way that limits your independence?",
        "domain": "control",
        "weight": {"coercive_controlling": 2},
    },
    {
        "id": "p_q2",
        "text": "Do you change what you say or do because you fear how the other parent will react?",
        "domain": "fear",
        "weight": {"coercive_controlling": 2},
    },
    {
        "id": "p_q3",
        "text": "Are the incidents part of an ongoing pattern where the other parent seeks to control or intimidate you across many areas of life?",
        "domain": "pattern",
        "weight": {"coercive_controlling": 3},
    },
    # Violent resistance markers.
    {
        "id": "p_q4",
        "text": "When force was used by you, was it defensive — protecting yourself or a child from harm in that moment?",
        "domain": "self_protection",
        "weight": {"violent_resistance": 3},
    },
    {
        "id": "p_q5",
        "text": "Is there an ongoing pattern of the other parent controlling or intimidating you, separate from any incident you may have been involved in?",
        "domain": "context",
        "weight": {"violent_resistance": 2, "coercive_controlling": 1},
    },
    # Situational conflict markers.
    {
        "id": "p_q6",
        "text": "Were the incidents largely tied to a specific argument or stressor at the time, without an ongoing power dynamic between you?",
        "domain": "incident_based",
        "weight": {"situational": 3},
    },
    # Separation-instigated markers.
    {
        "id": "p_q7",
        "text": "Did the concerning behaviour begin, or noticeably escalate, only around the time of separation?",
        "domain": "timing",
        "weight": {"separation_instigated": 3},
    },
    {
        "id": "p_q8",
        "text": "Was there a history of coercive or controlling behaviour in your relationship before separation?",
        "domain": "pre_separation",
        "weight": {"coercive_controlling": 2, "separation_instigated": -2},
    },
]


PATTERN_TYPES: Dict[str, Dict[str, str]] = {
    "coercive_controlling": {
        "label": "Coercive-controlling pattern",
        "framing": (
            "Answers describe an ongoing pattern of power and control across "
            "multiple domains. This is a distinct pattern from isolated "
            "conflict. Ordinary or cooperative coparenting is not indicated "
            "while this pattern is present."
        ),
    },
    "violent_resistance": {
        "label": "Violent-resistance / self-protective response",
        "framing": (
            "Answers describe defensive or self-protective conduct in the "
            "context of the other parent's ongoing control or intimidation. "
            "This is not the same as being the aggressor and should not be "
            "read as such. Parenting-plan structure should be shaped by the "
            "underlying coercive pattern, not by the defensive conduct."
        ),
    },
    "situational": {
        "label": "Situational conflict pattern",
        "framing": (
            "Answers describe incident-based conflict tied to specific "
            "stressors, without an ongoing power dynamic. Highly structured "
            "coparenting with clear guardrails is often workable. Revisit "
            "if incidents escalate or a pattern of control emerges."
        ),
    },
    "separation_instigated": {
        "label": "Separation-instigated pattern",
        "framing": (
            "Answers describe concerning behaviour that emerged around the "
            "time of separation, without a pre-separation history of control. "
            "This pattern is often transient. Structured communication and "
            "a review point in 6 months are typically appropriate."
        ),
    },
    "unclear": {
        "label": "Pattern not yet clear",
        "framing": (
            "The data does not yet distinguish between patterns. A qualified "
            "family-violence practitioner may need more information before "
            "the pattern can be characterised."
        ),
    },
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def classify_pattern(answers: Dict[str, Any] | None) -> Dict[str, Any]:
    """Score the pattern-context answers into one of five typology
    buckets. Never rules out a pattern from a single item — the
    classifier requires a plurality of weighted signal."""
    answers = answers or {}
    scores = {k: 0 for k in ("coercive_controlling", "violent_resistance", "situational", "separation_instigated")}
    answered = 0
    for q in PATTERN_CONTEXT_QUESTIONS:
        val = _norm(answers.get(q["id"]))
        if val not in ("yes", "no", "unsure"):
            continue
        answered += 1
        if val != "yes":
            continue
        for k, w in (q.get("weight") or {}).items():
            scores[k] = scores.get(k, 0) + int(w)
    if answered < 3:
        return {
            "type": "unclear",
            "label": PATTERN_TYPES["unclear"]["label"],
            "framing": PATTERN_TYPES["unclear"]["framing"],
            "scores": scores,
            "answered": answered,
        }
    best_type = max(scores, key=lambda k: scores[k])
    if scores[best_type] <= 0:
        best_type = "unclear"
    return {
        "type": best_type,
        "label": PATTERN_TYPES[best_type]["label"],
        "framing": PATTERN_TYPES[best_type]["framing"],
        "scores": scores,
        "answered": answered,
    }


# ---------- Phase 4: Trauma Impact screen ----------
#
# NON-DIAGNOSTIC. Ten items across five behavioural domains. Each
# domain aggregates to low / moderate / high signal.

TRAUMA_IMPACT_QUESTIONS: List[Dict[str, Any]] = [
    # Hypervigilance
    {"id": "ti_q1", "text": "Do you find yourself constantly scanning for danger, or on edge in ways you didn't used to be?", "domain": "hypervigilance"},
    {"id": "ti_q2", "text": "Do you startle easily — for example at doors closing, phone notifications, or footsteps?", "domain": "hypervigilance"},
    # Avoidance
    {"id": "ti_q3", "text": "Do you avoid places, people, or conversations that remind you of what happened?", "domain": "avoidance"},
    {"id": "ti_q4", "text": "Do you avoid opening messages, emails, or notifications from the other parent?", "domain": "avoidance"},
    # Dissociation / memory
    {"id": "ti_q5", "text": "Do you have gaps in your memory of events, or times when you feel disconnected from your surroundings?", "domain": "dissociation"},
    {"id": "ti_q6", "text": "Do you sometimes struggle to recall details of incidents even when you know they happened?", "domain": "dissociation"},
    # Sleep
    {"id": "ti_q7", "text": "Is your sleep disturbed — trouble falling asleep, staying asleep, nightmares, or waking exhausted?", "domain": "sleep"},
    {"id": "ti_q8", "text": "Do you avoid sleep, or fear it, because of the other parent or intrusive thoughts?", "domain": "sleep"},
    # Fear-based communication
    {"id": "ti_q9", "text": "Do you rehearse or delay messages to the other parent because you are afraid of their reaction?", "domain": "fear_communication"},
    {"id": "ti_q10", "text": "Have you deleted messages, hidden accounts, or been unable to speak freely because of fear of the other parent?", "domain": "fear_communication"},
]

TRAUMA_DOMAINS = ("hypervigilance", "avoidance", "dissociation", "sleep", "fear_communication")
TRAUMA_DOMAIN_LABELS = {
    "hypervigilance": "Hypervigilance",
    "avoidance": "Avoidance",
    "dissociation": "Dissociation / memory",
    "sleep": "Sleep disruption",
    "fear_communication": "Fear-based communication",
}


def analyse_trauma_impact(answers: Dict[str, Any] | None) -> Dict[str, Any]:
    """Aggregate trauma-impact answers into per-domain intensity:
    'low' / 'moderate' / 'high'. Two items per domain — 0 yes = low,
    1 yes = moderate, 2 yes = high."""
    answers = answers or {}
    by_domain: Dict[str, int] = {d: 0 for d in TRAUMA_DOMAINS}
    answered = 0
    for q in TRAUMA_IMPACT_QUESTIONS:
        val = _norm(answers.get(q["id"]))
        if val not in ("yes", "no", "unsure"):
            continue
        answered += 1
        if val == "yes":
            by_domain[q["domain"]] += 1
    def _intensity(count: int) -> str:
        if count >= 2:
            return "high"
        if count == 1:
            return "moderate"
        return "low"
    domains = {
        d: {
            "label": TRAUMA_DOMAIN_LABELS[d],
            "count": by_domain[d],
            "intensity": _intensity(by_domain[d]),
        }
        for d in TRAUMA_DOMAINS
    }
    highs = [d for d, v in domains.items() if v["intensity"] == "high"]
    mods = [d for d, v in domains.items() if v["intensity"] == "moderate"]
    if len(highs) >= 2:
        overall = "high"
    elif highs or len(mods) >= 3:
        overall = "moderate"
    else:
        overall = "low"
    return {
        "overall_intensity": overall,
        "domains": domains,
        "answered": answered,
        "high_domains": [TRAUMA_DOMAIN_LABELS[d] for d in highs],
    }


# ---------- Phase 5: Child Experience section ----------
#
# The parent's account of the child(ren)'s experience — this tool never
# administers questions to the child directly. Items cover direct
# victimisation, exposure, fear, parentification, divided loyalties,
# and protective relationships.

CHILD_EXPERIENCE_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "ce_q1", "text": "Has any child been directly hit, threatened, or harmed by the other parent?", "domain": "direct_harm", "high_concern": True},
    {"id": "ce_q2", "text": "Have any of the children witnessed physical violence, threats, or intimidation between you and the other parent?", "domain": "exposure"},
    {"id": "ce_q3", "text": "Do any of the children seem afraid of the other parent — for example, tense, quiet, or overly compliant around them?", "domain": "fear"},
    {"id": "ce_q4", "text": "Do the children take on adult-like caregiving or peacekeeping roles for you or for younger siblings?", "domain": "parentification"},
    {"id": "ce_q5", "text": "Do the children feel they have to choose sides, or hide their feelings about one parent from the other?", "domain": "loyalty_conflict"},
    {"id": "ce_q6", "text": "Have the children shown new behavioural changes — sleep disturbances, withdrawal, tantrums, regression, school difficulties — since these events?", "domain": "behavioural_signals"},
    {"id": "ce_q7", "text": "Do the children have at least one safe, consistent adult they can turn to (family member, teacher, coach, counsellor)?", "domain": "protective_relationships", "protective": True},
    {"id": "ce_q8", "text": "Have any of the children spontaneously described being frightened, hurt, or unsafe with the other parent?", "domain": "child_account"},
    {"id": "ce_q9", "text": "Do the children resist or refuse contact with the other parent in ways that go beyond ordinary reluctance?", "domain": "resistance"},
    {"id": "ce_q10", "text": "Are the children involved in — or being asked to relay information for — the coparenting conflict?", "domain": "triangulation"},
]

CHILD_DOMAIN_LABELS = {
    "direct_harm": "Direct victimisation",
    "exposure": "Exposure to violence",
    "fear": "Fear of the other parent",
    "parentification": "Parentification",
    "loyalty_conflict": "Divided loyalties",
    "behavioural_signals": "Behavioural changes",
    "protective_relationships": "Protective relationships",
    "child_account": "Child's own account",
    "resistance": "Resistance to contact",
    "triangulation": "Triangulation into conflict",
}


def analyse_child_experience(answers: Dict[str, Any] | None) -> Dict[str, Any]:
    """Summarise the child-experience answers. Direct victimisation is
    always surfaced (never soft-pedalled). Protective-relationships is
    surfaced *positively* — a "yes" is a resilience factor.
    """
    answers = answers or {}
    hits: Dict[str, bool] = {}
    high_concern_hits: List[str] = []
    protective_present = False
    answered = 0
    for q in CHILD_EXPERIENCE_QUESTIONS:
        val = _norm(answers.get(q["id"]))
        if val not in ("yes", "no", "unsure"):
            continue
        answered += 1
        if val == "yes":
            hits[q["id"]] = True
            if q.get("high_concern"):
                high_concern_hits.append(q["id"])
            if q.get("protective"):
                protective_present = True
    concern_domains = sorted({
        q["domain"]
        for q in CHILD_EXPERIENCE_QUESTIONS
        if hits.get(q["id"]) and not q.get("protective")
    })
    if high_concern_hits:
        overall = "high"
        headline = "Serious child-safety concerns reported"
    elif len(concern_domains) >= 3:
        overall = "moderate"
        headline = "Significant impact on the children reported"
    elif concern_domains:
        overall = "low"
        headline = "Some impact on the children reported"
    else:
        overall = "none"
        headline = "No specific child-experience concerns reported at this time"
    return {
        "overall": overall,
        "headline": headline,
        "high_concern_ids": high_concern_hits,
        "concern_domains": [CHILD_DOMAIN_LABELS[d] for d in concern_domains],
        "protective_relationship_present": protective_present,
        "answered": answered,
    }


# ---------- Front-facing shape helpers ----------

def all_extension_sections() -> Dict[str, List[Dict[str, Any]]]:
    """Payload used by the /questions endpoint to expose the three
    optional sections to the frontend."""
    def _strip(qs):
        return [
            {"id": q["id"], "text": q["text"], "domain": q.get("domain")}
            for q in qs
        ]
    return {
        "pattern_context": _strip(PATTERN_CONTEXT_QUESTIONS),
        "trauma_impact": _strip(TRAUMA_IMPACT_QUESTIONS),
        "child_experience": _strip(CHILD_EXPERIENCE_QUESTIONS),
    }
