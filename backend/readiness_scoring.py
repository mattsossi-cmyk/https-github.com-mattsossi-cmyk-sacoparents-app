"""Readiness scoring engine — rule-based, deterministic.

Turns a parent's raw preparation data into four dimension scores (0-100)
plus an overall Readiness Score. Same input → same output, always.
The AI layer then interprets these numbers into a narrative, but the numbers
themselves are always transparent, reproducible, and defensible.

Dimensions:
  * Communication   — how healthy the parent's communication self-assessment is
  * Trust           — how much co-parenting trust has been built (approach, safety)
  * Child Alignment — how child-centred the parent's stated goals and priorities are
  * Conflict        — inverse of how much unresolved conflict remains (higher = better)

Overall Readiness Score = weighted average of the four dimensions.
"""
from typing import Any, Dict, List, Tuple


# ---- Weights ---------------------------------------------------------------
# Communication self-assessment carries the most weight because it drives
# almost every mediation interaction. Child alignment is a close second — this
# is a child-centred app. Trust and conflict follow.
_WEIGHTS = {
    "communication": 0.30,
    "child_alignment": 0.30,
    "trust": 0.20,
    "conflict": 0.20,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_communication(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 based on the Communication Style self-assessment.

    The Communication Style module scores the parent 1-5 across ~5 sub-facets
    (tone, listening, escalation, boundaries, repair). Higher = healthier.
    We convert the average to a 0-100 scale.
    """
    reasons: List[str] = []
    comm = prep.get("comm_style") or {}
    scores = comm.get("scores") or {}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    if not numeric:
        # No self-assessment yet — neutral placeholder, flagged.
        reasons.append("Communication self-assessment not completed")
        return 50.0, reasons

    avg = sum(numeric) / len(numeric)  # 1-5 scale
    score = _clamp((avg - 1) / 4 * 100)  # 1→0, 5→100

    if avg < 2.5:
        reasons.append("Communication self-ratings are low — room to grow")
    elif avg < 3.5:
        reasons.append("Communication self-ratings are mixed")
    else:
        reasons.append("Communication self-ratings are strong")
    return score, reasons


def _score_child_alignment(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 based on how completely the parent has articulated child-centred
    goals and priorities."""
    reasons: List[str] = []
    goals = prep.get("child_goals") or {}
    priorities = prep.get("priority") or []

    goal_answers = 0
    for k in ("emotional_wellbeing", "stability", "relationships", "development"):
        v = goals.get(k)
        if v and str(v).strip():
            goal_answers += 1

    priorities_count = len(priorities) if isinstance(priorities, list) else 0

    # Base 40 for engaging at all, up to 60 more for completeness.
    if goal_answers == 0 and priorities_count == 0:
        reasons.append("Child-centred goals & priorities not yet defined")
        return 20.0, reasons

    goal_score = (goal_answers / 4) * 40  # up to 40
    prio_score = min(priorities_count / 5, 1.0) * 60  # up to 60
    score = _clamp(goal_score + prio_score)

    if goal_answers >= 3:
        reasons.append("Clear articulation of child-centred goals")
    if priorities_count >= 3:
        reasons.append(f"{priorities_count} priorities ranked with intention")
    if score < 60:
        reasons.append("More child-focused specifics would strengthen the report")
    return score, reasons


def _score_trust(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 from readiness sub-scores around cooperation and co-parenting posture (no safety results)."""
    reasons: List[str] = []
    readiness = prep.get("readiness") or {}

    # Readiness sub-scores relevant to trust: cooperation, hope, patience.
    readiness_scores = readiness.get("scores") or {}
    trust_keys = ("cooperation", "hope_for_agreement", "trust_in_process", "patience")
    trust_vals = [
        float(readiness_scores[k])
        for k in trust_keys
        if isinstance(readiness_scores.get(k), (int, float))
    ]
    if trust_vals:
        avg = sum(trust_vals) / len(trust_vals)  # 1-5
        base = _clamp((avg - 1) / 4 * 100)
    else:
        base = 55.0  # gentle neutral if not yet answered
        reasons.append("Readiness self-ratings incomplete")

    score = _clamp(base)
    if score >= 75 and not reasons:
        reasons.append("Strong foundation of co-parenting trust")
    return score, reasons


def _score_conflict(prep: Dict[str, Any]) -> Tuple[float, List[str]]:
    """0-100 where HIGHER = LESS unresolved conflict.

    Formula: 100 minus penalties for (a) many unresolved issues, (b) heavy
    'urgent' priorities, (c) low readiness-emotional-preparation self-rating."""
    reasons: List[str] = []
    issues = prep.get("issues") or {}
    priorities = prep.get("priority") or []
    readiness_scores = (prep.get("readiness") or {}).get("scores") or {}

    # Count how many issue categories have content.
    issue_categories_with_content = 0
    for key in ("schedule", "communication", "finances", "other"):
        v = issues.get(key)
        if v and str(v).strip():
            issue_categories_with_content += 1

    # More issue categories logged → more perceived conflict.
    issue_penalty = min(issue_categories_with_content, 5) * 8  # up to 40

    # 'Urgent' priorities weigh heavier than 'compromise' ones.
    urgent = sum(
        1
        for p in (priorities if isinstance(priorities, list) else [])
        if isinstance(p, dict) and (p.get("category") == "urgent" or p.get("weight") == "urgent")
    )
    urgent_penalty = min(urgent, 5) * 4  # up to 20

    # Emotional preparation lifts the conflict score (parent is calmer → less conflict).
    emo_prep = readiness_scores.get("emotional_preparation")
    if isinstance(emo_prep, (int, float)):
        emo_bonus = (float(emo_prep) - 3) * 5  # -10..+10
    else:
        emo_bonus = 0

    score = _clamp(100 - issue_penalty - urgent_penalty + emo_bonus)

    if issue_categories_with_content >= 4:
        reasons.append("Multiple areas of active concern")
    if urgent >= 2:
        reasons.append(f"{urgent} priorities flagged as urgent")
    if score >= 70:
        reasons.append("Conflict feels manageable in the current picture")
    return score, reasons


def compute_readiness(prep: Dict[str, Any]) -> Dict[str, Any]:
    """Public entry point. Returns a **profile-first** readiness view.

    Historically this returned a single overall number. That risks
    confusing *completeness* with *readiness* — a parent with polished
    answers may score highly while lacking emotional regulation, or
    while participating in a coercive relationship. The new shape leads
    with a per-domain descriptive profile + concrete preparation
    recommendations. The numerical score is preserved for backwards
    compatibility but presented as a secondary indicator.

    Shape:
      {
        # Legacy fields (unchanged for backwards compatibility) --------
        "overall": 72,
        "label": "Prepared for Mediation" | "Moderately Ready" | "Needs Support",
        "dimensions": {
          "communication":   {"score": 68, "reasons": [...]},
          "trust":           {"score": 74, "reasons": [...]},
          "child_alignment": {"score": 82, "reasons": [...]},
          "conflict":        {"score": 60, "reasons": [...]}
        },
        "weights": {...},

        # New profile-first fields ------------------------------------
        "profile": {
          "communication":   {level, headline, narrative,
                              strengths[], growth_areas[],
                              preparation_recommendations[]},
          "trust":           { ... },
          "child_alignment": { ... },
          "conflict":        { ... }
        },
        "caveats": [str, ...],
        "readiness_disclaimer": str,
        "secondary_score": {
          "overall": 72,
          "label": "...",
          "note": "The numerical score reflects completeness of "
                  "your preparation. It is NOT a measure of emotional "
                  "readiness or of whether mediation is safe."
        }
      }
    """
    dims: Dict[str, Dict[str, Any]] = {}
    for name, scorer in (
        ("communication", _score_communication),
        ("trust", _score_trust),
        ("child_alignment", _score_child_alignment),
        ("conflict", _score_conflict),
    ):
        score, reasons = scorer(prep)
        dims[name] = {"score": round(score, 1), "reasons": reasons}

    overall = sum(dims[k]["score"] * _WEIGHTS[k] for k in _WEIGHTS)
    overall_rounded = round(overall)

    if overall >= 75:
        label = "Prepared for Mediation"
    elif overall >= 55:
        label = "Moderately Ready"
    else:
        label = "Needs Support"

    # Build the profile-first payload.
    profile = _build_profile(prep, dims)
    caveats = _build_caveats(prep, dims)

    return {
        # Legacy fields for existing UI consumers.
        "overall": overall_rounded,
        "label": label,
        "dimensions": dims,
        "weights": _WEIGHTS,
        # Profile-first fields — new consumers should read these.
        "profile": profile,
        "caveats": caveats,
        "readiness_disclaimer": (
            "This assessment is a guided self-reflection and preparation "
            "resource. It is not a clinical, forensic, legal, or "
            "professional evaluation. Its results are intended to help "
            "you identify concerns, organize your thinking, and prepare "
            "questions for an appropriate professional. In particular: "
            "this score reflects the completeness of your preparation, "
            "not your emotional readiness for mediation and not whether "
            "mediation is safe for you. If a coercive "
            "pattern is present, highly structured or parallel "
            "arrangements — not mediation — are typically indicated "
            "regardless of how high this score is."
        ),
        "secondary_score": {
            "overall": overall_rounded,
            "label": label,
            "note": (
                "Numerical scores in this tool reflect completeness of "
                "preparation, not readiness. Use them as a secondary "
                "indicator only — the per-domain profile is the primary output."
            ),
        },
    }


# ---------- Profile-first builders ----------

def _level_from_score(score: float) -> str:
    if score >= 75:
        return "solid"
    if score >= 55:
        return "developing"
    return "emerging"


_DOMAIN_METADATA: Dict[str, Dict[str, Any]] = {
    "communication": {
        "label": "Communication",
        "core_question": "How healthy and regulated is your communication self-assessment?",
        "solid": {
            "headline": "Your communication self-assessment is strong",
            "narrative": (
                "You've rated yourself well across tone, listening, boundaries, and "
                "repair. That doesn't mean every conversation with the other parent "
                "will feel easy — it means you have language and habits to lean on."
            ),
            "recs": [
                "Bring one specific 'repair' phrase you already use into the mediation itself.",
                "Rehearse a difficult moment out loud once before the session — even the best communication needs pacing under stress.",
            ],
        },
        "developing": {
            "headline": "Communication is mixed — solid in places, thinner in others",
            "narrative": (
                "Some communication habits are working; others feel harder. That's "
                "typical mid-conflict. The goal isn't perfect communication — it's "
                "predictable communication the other parent can rely on."
            ),
            "recs": [
                "Pick the ONE facet you rated lowest and rehearse a script for it (e.g. saying 'no' without over-explaining).",
                "Draft your messages before sending — a 20-minute pause reduces reactive replies.",
                "Consider a 3-session communication coach before mediation if the pattern is entrenched.",
            ],
        },
        "emerging": {
            "headline": "Communication capacity is emerging — go slowly",
            "narrative": (
                "Your self-assessment shows communication is under real strain. This "
                "is not a character verdict — it's information. Mediation asks a lot "
                "of communication capacity in a short window, so extra scaffolding "
                "before the session will help far more than a polished write-up."
            ),
            "recs": [
                "Complete the Communication Style self-assessment if you haven't yet — that gives us your baseline.",
                "Work with a communication coach or therapist for 4-6 weeks before mediation, if resources allow.",
                "Ask the mediator for written pre-session prompts so you can prepare responses instead of improvising.",
                "Bring a support person to help you regulate between rounds.",
            ],
        },
    },
    "trust": {
        "label": "Trust in the co-parenting process",
        "core_question": "How much of a foundation exists to build a plan on?",
        "solid": {
            "headline": "There is enough foundational trust to build a plan on",
            "narrative": (
                "Your ratings around cooperation and hope for agreement are solid. "
                "That means the conversation can be about the plan itself."
            ),
            "recs": [
                "Bring one small win from the last month into the session — recent, concrete evidence anchors the conversation.",
                "Draft the two or three plan elements you'd offer as a first move.",
            ],
        },
        "developing": {
            "headline": "Trust is uneven — build guardrails, not shortcuts",
            "narrative": (
                "Trust is partial. That's workable, but the plan should be "
                "written, specific, and short-cycle — the kind that doesn't "
                "require good will to survive a bad week."
            ),
            "recs": [
                "Propose written-only communication for a set trial period (e.g. 60 days).",
                "Ask the mediator for a formal review point in the plan.",
                "Come prepared with the boundaries you need in writing, not the ones you'd accept verbally.",
            ],
        },
        "emerging": {
            "headline": "Foundational trust is not yet there",
            "narrative": (
                "The picture around trust is thin. Mediation without a clear structure is "
                "unlikely to hold. This does not close the door — it just means "
                "the structure has to do the work trust isn't yet doing."
            ),
            "recs": [
                "If mediation is still appropriate, insist on shuttle mediation (separate rooms) or written-only exchanges.",
                "Bring a lawyer, DV advocate, or support person; do not do this alone.",
            ],
        },
    },
    "child_alignment": {
        "label": "Child alignment",
        "core_question": "How child-centred are your stated goals and priorities?",
        "solid": {
            "headline": "Your framing is clearly child-centred",
            "narrative": (
                "Your goals and ranked priorities put the children's experience "
                "at the middle of the picture. That's the single strongest "
                "predictor of a durable parenting plan."
            ),
            "recs": [
                "In the session, use the children's names — moving from abstract to specific makes shared decisions easier.",
                "Keep one of your priorities as a 'compromise' item — you'll need one to trade for something you need.",
            ],
        },
        "developing": {
            "headline": "Child-centred framing is partially there",
            "narrative": (
                "Some goals are child-centred; others are still about the "
                "grown-ups. That's normal. Sharpening this before the session "
                "gives you a stronger anchor when the conversation drifts."
            ),
            "recs": [
                "For each priority, add a sentence naming how it affects each child specifically.",
                "Add at least one goal for a child in each developmental area — school, friendships, sleep, feelings.",
            ],
        },
        "emerging": {
            "headline": "The children's specific experience isn't yet at the centre",
            "narrative": (
                "Your goals and priorities are mostly about you, the other "
                "parent, or the arrangement itself. That's a common starting "
                "point but it makes agreement harder because everything is "
                "read as a win/lose between the adults."
            ),
            "recs": [
                "Complete the Priority Ranking module and add at least 3 child-focused goals.",
                "Ask each child (age-appropriately) what would help — then bring their words into your notes.",
                "Reread your notes and cross out any priority that doesn't name a child benefit.",
            ],
        },
    },
    "conflict": {
        "label": "Conflict load",
        "core_question": "How much unresolved conflict is loaded into the room?",
        "solid": {
            "headline": "Conflict load feels manageable in the current picture",
            "narrative": (
                "The number of active issues and urgent priorities is contained, "
                "and your emotional-preparation self-rating is steady."
            ),
            "recs": [
                "Batch the smallest 2-3 issues into a single agenda item — quick wins early lower the temperature.",
            ],
        },
        "developing": {
            "headline": "Multiple issues are live at once",
            "narrative": (
                "You have several categories of active concern. That doesn't "
                "mean mediation won't work — it means the agenda needs pacing."
            ),
            "recs": [
                "Rank issues into 'now', 'next session', and 'later'.",
                "Ask the mediator for a two-session structure rather than trying to resolve everything in one meeting.",
                "Do one grounding technique the morning of the session (breathwork, walk, prayer, whatever works for you).",
            ],
        },
        "emerging": {
            "headline": "The conflict load in the room will be heavy",
            "narrative": (
                "Many categories of concern are live, and urgent priorities "
                "outnumber the emotional-preparation resources you've reported. "
                "This is not a moral judgement — it's a bandwidth read."
            ),
            "recs": [
                "Consider whether now is the right timing at all — a 30-day delay to consolidate the picture is often a net gain.",
                "Bring only ONE agenda item to the first session. Save the rest for structured follow-ups.",
                "Line up emotional support for the day OF and the day AFTER the session, not just before.",
                "If you have safety concerns, talk with a family-violence advocate or attorney about whether mediation is the right forum.",
            ],
        },
    },
}


def _build_profile(prep: Dict[str, Any], dims: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    profile: Dict[str, Any] = {}
    for key, meta in _DOMAIN_METADATA.items():
        score = float(dims[key]["score"])
        reasons = list(dims[key]["reasons"])
        level = _level_from_score(score)
        band = meta[level]
        profile[key] = {
            "label": meta["label"],
            "core_question": meta["core_question"],
            "level": level,
            "headline": band["headline"],
            "narrative": band["narrative"],
            # Strengths / growth-areas are lifted directly from the
            # deterministic reasons so the profile stays evidence-linked.
            "strengths": [r for r in reasons if _looks_positive(r)],
            "growth_areas": [r for r in reasons if not _looks_positive(r)],
            "preparation_recommendations": list(band["recs"]),
            # The number is intentionally deprioritised — present but
            # after the descriptive content.
            "secondary_score": score,
        }
    return profile


_POSITIVE_MARKERS = ("strong", "clear", "solid", "steady", "manageable", "foundation")


def _looks_positive(reason: str) -> bool:
    s = (reason or "").lower()
    return any(m in s for m in _POSITIVE_MARKERS)


def _build_caveats(prep: Dict[str, Any], dims: Dict[str, Dict[str, Any]]) -> List[str]:
    caveats: List[str] = []
    if dims["conflict"]["score"] < 40 and dims["communication"]["score"] >= 70:
        caveats.append(
            "Your communication score is strong but the conflict load is "
            "high. Polished communication can mask emotional flooding under "
            "pressure — build in pacing and support even though the numbers "
            "look positive."
        )
    if all(d["score"] >= 70 for d in dims.values()) and not (prep.get("comm_style") or {}).get("scores"):
        caveats.append(
            "Every dimension scored highly, but the Communication Style "
            "self-assessment has not been completed. Consider finishing "
            "that module before relying on the overall number."
        )
    return caveats
