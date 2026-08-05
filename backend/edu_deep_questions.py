"""Educational Needs — Deep Dive schema.

Iteration 67 (2026-02-05) — the Educational Deep Dive is now the
**Co-Parenting Alignment Assessment: Special Education & ADHD Edition**:
25 items in 5 parts, each scored on a 0-4 alignment scale with an
optional N/A.

* Emotional Well-being & Child Support         (5 items)
* Communication & Conflict Management          (5 items)
* IEP & ARD Special-Education Management       (5 items)
* ADHD Routines, Structure, & Accommodations   (5 items)
* Logistics, Reliability, & Flexibility        (5 items)

Total 100 points possible; three interpretation bands (81-100 High,
51-80 Moderate, 0-50 Low). See ``edu_deep_scoring.score_deep_dive``.

The old 12-section 60-item schema (edu-deep-1.x) has been retired.
Answers saved against that schema are silently ignored at load time and
overwritten by the new schema.
"""
from __future__ import annotations

from typing import Any, Dict, List


DEEP_DIVE_VERSION = "edu-deep-2.0.0"

# ---------------------------------------------------------------------------
# The 0-4 alignment likert. Presented in the UI as a 5-button row.
# ---------------------------------------------------------------------------
ALIGNMENT_SCALE = [0, 1, 2, 3, 4]
ALIGNMENT_LABELS = {
    0: "Never / High Conflict",
    1: "Seldom / Rarely",
    2: "Sometimes / Inconsistent",
    3: "Often / Mostly Consistent",
    4: "Always / Very Consistent",
}

# Points possible per item (max score for a fully-answered assessment is 100).
POINTS_PER_ITEM_MAX = 4
TOTAL_ITEMS = 25


def _alignment_item(prompt: str) -> Dict[str, Any]:
    """Convenience factory for a 0-4 alignment likert question."""
    return {
        "type": "alignment",
        "scale": ALIGNMENT_SCALE,
        "labels": ALIGNMENT_LABELS,
        "prompt": prompt,
        "allow_na": True,
        "scored": True,
    }


# Section schema. Each section has: id, number, name, purpose, items.
DEEP_DIVE_SECTIONS: List[Dict[str, Any]] = [
    # 1 -----------------------------------------------------------------
    {"id": "p1", "number": 1, "name": "Emotional Well-being & Child Support",
     "purpose": "How consistently both parents protect the child from adult conflict "
                "and safeguard the child's bond with the other parent.",
     "items": {
        "q1": _alignment_item(
            "We explicitly give our children permission to love, bond with, "
            "and enjoy time with the other parent."),
        "q2": _alignment_item(
            "We speak respectfully about (or do not criticise) the other parent "
            "when the children are within earshot."),
        "q3": _alignment_item(
            "We shield the children from hearing or seeing any adult arguments, "
            "legal matters, or financial disputes."),
        "q4": _alignment_item(
            "We encourage our children to express their feelings about the "
            "separation without making them feel guilty."),
        "q5": _alignment_item(
            "We avoid using the children as messengers, informants, or spies to "
            "get information about the other household."),
     }},
    # 2 -----------------------------------------------------------------
    {"id": "p2", "number": 2, "name": "Communication & Conflict Management",
     "purpose": "How adults exchange information about the child and resolve "
                "disagreements.",
     "items": {
        "q6": _alignment_item(
            "We communicate directly with each other regarding the children, "
            "rather than making the children pass messages."),
        "q7": _alignment_item(
            "Our written and verbal communications remain brief, informative, "
            "friendly, and focused strictly on the kids."),
        "q8": _alignment_item(
            "We respond to non-emergency messages about the children within a "
            "reasonable, agreed-upon timeframe (e.g. 24 hours)."),
        "q9": _alignment_item(
            "When disagreements happen, we focus on finding solutions for the "
            "child rather than winning the argument."),
        "q10": _alignment_item(
            "We actively use a shared calendar or specialised co-parenting app "
            "to log schedules, appointments, and expenses."),
     }},
    # 3 -----------------------------------------------------------------
    {"id": "p3", "number": 3, "name": "IEP & ARD Special-Education Management",
     "purpose": "How the household coordinates the child's Individualised "
                "Education Program and ARD meetings.",
     "items": {
        "q11": _alignment_item(
            "We attend ARD/IEP meetings together cooperatively, or we coordinate "
            "ahead of time to present a unified front to the school."),
        "q12": _alignment_item(
            "We share all school diagnostic reports, IEP progress updates, and "
            "teacher communications immediately with each other."),
        "q13": _alignment_item(
            "We enforce the same classroom accommodations (extra time, sensory "
            "breaks) during homework time in both houses."),
        "q14": _alignment_item(
            "We collaborate on educational goals rather than using ARD meetings "
            "to argue or blame the other parent for school delays."),
        "q15": _alignment_item(
            "We maintain a single, shared digital folder for all legal IEP "
            "documentation, psychological evaluations, and school paperwork."),
     }},
    # 4 -----------------------------------------------------------------
    {"id": "p4", "number": 4, "name": "ADHD Routines, Structure, & Accommodations",
     "purpose": "How consistently both homes hold the routines, medication, "
                "and expectations that support ADHD.",
     "items": {
        "q16": _alignment_item(
            "We use matching visual schedules, checklists, or token systems in "
            "both homes to support our child's executive functioning."),
        "q17": _alignment_item(
            "We strictly coordinate ADHD medication doses, timings, and pharmacy "
            "refills so the child's routine never lapses between houses."),
        "q18": _alignment_item(
            "We report side effects, behavioural changes, or medication efficacy "
            "to each other before reporting them to the doctor."),
        "q19": _alignment_item(
            "Our two households maintain highly similar, predictable expectations "
            "for bedtimes, wake-up times, and electronics limits."),
        "q20": _alignment_item(
            "We handle transitions and drop-offs peacefully, knowing abrupt "
            "changes can trigger ADHD dysregulation or meltdowns."),
     }},
    # 5 -----------------------------------------------------------------
    {"id": "p5", "number": 5, "name": "Logistics, Reliability, & Flexibility",
     "purpose": "The day-to-day reliability that makes a special-needs plan "
                "actually work.",
     "items": {
        "q21": _alignment_item(
            "We consistently arrive on time for custody exchanges and pick-ups, "
            "respecting each other's time and the child's need for routine."),
        "q22": _alignment_item(
            "We provide ample advance notice (48 hours or more) if a schedule "
            "change or adjustment is needed."),
        "q23": _alignment_item(
            "We respect the other parent's designated custody time and do not "
            "interrupt it with unnecessary calls or texts to the child."),
        "q24": _alignment_item(
            "We ensure all specialised gear (fidgets, noise-cancelling "
            "headphones, school binders) travels smoothly between houses."),
        "q25": _alignment_item(
            "We accommodate reasonable, occasional schedule adjustments when "
            "special events, holidays, or unexpected conflicts arise."),
     }},
]


# Kept for downstream code that still imports it (e.g. the legacy narrative
# builder). The list is intentionally empty in v2 so nothing accidentally
# references an old key.
DECISION_TOPICS: List[tuple] = []


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def public_schema() -> Dict[str, Any]:
    """Serialisable schema used by the React assessment page."""
    return {
        "version": DEEP_DIVE_VERSION,
        "sections": [
            {
                "id": s["id"],
                "number": s["number"],
                "name": s["name"],
                "purpose": s.get("purpose"),
                # Sections in v2 never conditionally hide, but we retain
                # `texas_only` and `gate` in the payload as `None` for
                # frontend backwards-compat.
                "texas_only": False,
                "gate": None,
                "items": [
                    {"id": iid, **spec} for iid, spec in s["items"].items()
                ],
            }
            for s in DEEP_DIVE_SECTIONS
        ],
    }


def all_item_keys() -> List[str]:
    """`{section_id}_{item_id}` composite keys used as answer keys."""
    out = []
    for s in DEEP_DIVE_SECTIONS:
        for iid in s["items"].keys():
            out.append(f"{s['id']}_{iid}")
    return out


def item_by_key(key: str) -> Dict[str, Any] | None:
    for s in DEEP_DIVE_SECTIONS:
        for iid, spec in s["items"].items():
            if f"{s['id']}_{iid}" == key:
                return {**spec, "id": iid, "section": s["id"]}
    return None


def validate_answer(key: str, value: Any) -> bool:
    """A response is valid iff the value is either the string "na" (skip
    marker) or an int in 0..4."""
    if item_by_key(key) is None:
        return False
    if value == "na":
        return True
    if isinstance(value, bool):  # bool is a subclass of int — reject
        return False
    return isinstance(value, int) and 0 <= value <= 4


def is_v2_key(key: str) -> bool:
    """True iff `key` matches the new p*_q* pattern (used to filter out
    legacy answers persisted against the retired v1 schema)."""
    return key.startswith(("p1_", "p2_", "p3_", "p4_", "p5_"))
