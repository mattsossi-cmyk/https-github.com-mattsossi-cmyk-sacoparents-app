"""Scoring engine for the redesigned Special Needs Co-Parenting Assessment.

Result categories (from framework Section 17):
    - Existing strength
    - Developing area
    - Priority for planning
    - Professional guidance recommended
    - Safety-sensitive concern

Rules:
  * Each domain (except Safety) is averaged over answered non-N/A items on
    the 0-4 scale, then mapped to a category:
        avg >= 3.25  → Existing strength
        avg >= 2.25  → Developing area
        avg <  2.25  → Priority for planning
  * A domain is elevated to "Professional guidance recommended" if the parent
    flagged `want_help` on 2+ questions in that domain (regardless of avg).
  * Domain 10 (Safety) is NEVER averaged into strength ratings. If ANY
    reverse-scored safety item is Agree/Strongly agree (raw >= 3) OR any
    `safety` meta-flag is set, the Safety domain is marked
    "Safety-sensitive concern" and surfaces as a top-priority review.
  * Overall assessment rating:
        - "Safety-sensitive concern" if Safety triggered.
        - Otherwise a summary of strengths vs. priorities.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sn_v3_questions import DOMAINS, total_question_count


# Category constants (used in reports + frontend chips)
CAT_STRENGTH  = "Existing strength"
CAT_DEVELOP   = "Developing area"
CAT_PRIORITY  = "Priority for planning"
CAT_PROFESSIONAL = "Professional guidance recommended"
CAT_SAFETY    = "Safety-sensitive concern"

RESULT_CATEGORIES = [CAT_STRENGTH, CAT_DEVELOP, CAT_PRIORITY, CAT_PROFESSIONAL, CAT_SAFETY]


OVERALL_STRENGTH   = "Existing Strength Overall"
OVERALL_DEVELOPING = "Developing Overall"
OVERALL_PRIORITY   = "Priority Focus Overall"
OVERALL_SAFETY     = "Safety-Sensitive Review Recommended"


def _effective(raw: int, reverse: bool) -> int:
    return (4 - raw) if reverse else raw


def _category_from_avg(avg: float) -> str:
    if avg >= 3.25:
        return CAT_STRENGTH
    if avg >= 2.25:
        return CAT_DEVELOP
    return CAT_PRIORITY


def compute_scores(
    answers: Dict[str, int] | None,
    *,
    meta: Dict[str, Dict[str, bool]] | None = None,
) -> Dict[str, Any]:
    """Return the scored payload for an assessment.

    Args:
      answers: {question_id -> int(0-4)}. Missing = unanswered.
      meta:    {question_id -> {"na": bool, "need_info": bool, "want_help": bool, "safety": bool}}
    """
    answers = answers or {}
    meta = meta or {}

    domains_out: List[Dict[str, Any]] = []
    safety_hit = False
    safety_questions: List[str] = []

    for d in DOMAINS:
        did = d["id"]
        is_safety_domain = bool(d.get("safety_sensitive"))
        answered = 0
        na_count = 0
        want_help_hits = 0
        raw_scores: List[int] = []
        eff_scores: List[int] = []
        d_safety_hits: List[str] = []

        for q in d["questions"]:
            qid = q["id"]
            m = meta.get(qid) or {}
            if m.get("na"):
                na_count += 1
                # N/A items don't count toward avg and don't trigger flags.
                continue
            if m.get("want_help"):
                want_help_hits += 1
            # Safety meta flag can be set on ANY domain question.
            if m.get("safety"):
                safety_hit = True
                d_safety_hits.append(qid)
            if qid in answers:
                answered += 1
                raw = int(answers[qid])
                raw_scores.append(raw)
                eff = _effective(raw, bool(q.get("reverse")))
                eff_scores.append(eff)
                # Safety-domain reverse item — high raw = concern
                if is_safety_domain and q.get("safety_flag") and raw >= 3:
                    safety_hit = True
                    d_safety_hits.append(qid)

        avg = round(sum(eff_scores) / len(eff_scores), 2) if eff_scores else None
        # Category selection
        if is_safety_domain:
            category = CAT_SAFETY if d_safety_hits else CAT_STRENGTH
        elif avg is None:
            category = None
        else:
            category = _category_from_avg(avg)
            if want_help_hits >= 2:
                # Parent explicitly asked for help in this area
                category = CAT_PROFESSIONAL

        domains_out.append({
            "id": did,
            "number": d["number"],
            "name": d["name"],
            "goal": d.get("goal"),
            "framework_ref": d.get("framework_ref"),
            "avg": avg,
            "answered": answered,
            "total": len(d["questions"]),
            "na_count": na_count,
            "want_help_hits": want_help_hits,
            "safety_hits": d_safety_hits,
            "category": category,
        })
        if d_safety_hits:
            safety_questions.extend(d_safety_hits)

    # Rankings for report composition (exclude safety domain from strength/priority lists)
    non_safety = [d for d in domains_out if d["id"] != "d10" and d["avg"] is not None]
    strongest = [d["id"] for d in sorted(non_safety, key=lambda x: -x["avg"])[:2] if d["avg"] >= 3.0]
    priority = [
        d["id"] for d in sorted(non_safety, key=lambda x: (x["avg"], x["number"]))
        if d["category"] in (CAT_PRIORITY, CAT_PROFESSIONAL, CAT_DEVELOP)
    ][:4]

    # Communication toolkit trigger: Domain 6 (Communication) is Priority/Professional
    d6 = next((d for d in domains_out if d["id"] == "d6"), None)
    show_toolkit = bool(d6 and d6.get("category") in (CAT_PRIORITY, CAT_PROFESSIONAL))

    # Overall rating
    if safety_hit:
        overall = OVERALL_SAFETY
    elif not non_safety:
        overall = "Not enough data"
    else:
        strengths_count = sum(1 for d in non_safety if d["category"] == CAT_STRENGTH)
        priorities_count = sum(1 for d in non_safety if d["category"] in (CAT_PRIORITY, CAT_PROFESSIONAL))
        if strengths_count >= 6 and priorities_count <= 1:
            overall = OVERALL_STRENGTH
        elif priorities_count >= 4:
            overall = OVERALL_PRIORITY
        else:
            overall = OVERALL_DEVELOPING

    return {
        "domains": domains_out,
        "overall_rating": overall,
        "safety_triggered": safety_hit,
        "safety_questions": safety_questions,
        "strongest_domain_ids": strongest,
        "priority_focus_ids": priority,
        "show_communication_toolkit": show_toolkit,
        "answered_count": sum(d["answered"] for d in domains_out),
        "total_count": total_question_count(),
    }


def validate_answers(answers: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(answers, dict):
        return False, "answers must be an object"
    for qid, v in answers.items():
        if not isinstance(v, int) or v < 0 or v > 4:
            return False, f"Value for {qid} must be an int 0-4"
    return True, ""
