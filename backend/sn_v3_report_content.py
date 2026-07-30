"""Deterministic Special Needs report content builder (2026 framework)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sn_v3_questions import DOMAINS
from sn_v3_scoring import (
    CAT_STRENGTH, CAT_DEVELOP, CAT_PRIORITY, CAT_PROFESSIONAL, CAT_SAFETY,
    OVERALL_STRENGTH, OVERALL_DEVELOPING, OVERALL_PRIORITY, OVERALL_SAFETY,
)


# Domain-level guidance library keyed by (domain_id, category).
_DOMAIN_GUIDANCE: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "d1": {
        CAT_STRENGTH: {"findings": ["You understand your child's needs and what helps them recover from stress."], "recommendations": ["Keep updating your understanding as new professional information arrives."]},
        CAT_DEVELOP:  {"findings": ["You know a lot; a few areas of your child's world are still coming into focus."], "recommendations": ["Ask one of your child's professionals for a plain-language summary of current recommendations."]},
        CAT_PRIORITY: {"findings": ["Gaps in shared knowledge of your child's needs are affecting decisions and consistency."], "recommendations": ["Book a 30-minute consult with the diagnosing / treating professional to align on today's picture."]},
    },
    "d2": {
        CAT_STRENGTH: {"findings": ["Your school participation is strong and information flows both ways."], "recommendations": ["Keep both parents on the school's official contact list."]},
        CAT_DEVELOP:  {"findings": ["School coordination mostly works with occasional gaps."], "recommendations": ["Ask the school to send communications to both parents; keep a shared school folder for the child."]},
        CAT_PRIORITY: {"findings": ["Classroom coordination is inconsistent and may affect academic support."], "recommendations": ["Request a joint parent-teacher meeting; if an IEP/504 is in place, request both parents receive full documentation."]},
    },
    "d3": {
        CAT_STRENGTH: {"findings": ["Medical, mental-health, and therapy coordination is solid."], "recommendations": ["Keep a shared medication + appointment log accessible to both parents."]},
        CAT_DEVELOP:  {"findings": ["Healthcare coordination usually works, with some gaps."], "recommendations": ["Confirm both parents are on file with the pediatrician and specialists; align on a refill responsibility."]},
        CAT_PRIORITY: {"findings": ["Medical information doesn't always reach both homes on time."], "recommendations": ["Ask providers to send appointment summaries to both parents; keep an emergency-info sheet in the child's bag."]},
    },
    "d4": {
        CAT_STRENGTH: {"findings": ["Your home offers stable, predictable routines that support your child."], "recommendations": ["Continue anchoring bedtime, mealtimes, and screen limits."]},
        CAT_DEVELOP:  {"findings": ["Most routines in your home are consistent, some drift."], "recommendations": ["Pick one anchor routine (bedtime) and keep it identical for 30 days."]},
        CAT_PRIORITY: {"findings": ["Daily-care consistency is currently low; transitions and behaviour may be affected."], "recommendations": ["Post a visible daily rhythm; ask your child's therapist for a home-carryover plan."]},
    },
    "d5": {
        CAT_STRENGTH: {"findings": ["Transitions are calm and predictable."], "recommendations": ["Keep exchange location and timing consistent to protect that stability."]},
        CAT_DEVELOP:  {"findings": ["Exchanges usually go smoothly with occasional friction."], "recommendations": ["Standardise what travels between homes (laminated checklist on the bag)."]},
        CAT_PRIORITY: {"findings": ["Transitions are a recurring source of stress."], "recommendations": ["Move exchanges to a neutral or school-based location; add visual warnings 24 hours before each exchange."]},
    },
    "d6": {
        CAT_STRENGTH: {"findings": ["Communication is timely, accurate, and child-focused."], "recommendations": ["Keep documenting agreements after each conversation."]},
        CAT_DEVELOP:  {"findings": ["Communication is largely reliable with occasional gaps."], "recommendations": ["Add a weekly 10-minute child-focused check-in with a fixed agenda."]},
        CAT_PRIORITY: {"findings": ["Communication frequently escalates or breaks down before important information is shared."], "recommendations": ["Move all non-emergency communication to a written, timestamped channel; adopt BIFF phrasing."]},
    },
    "d7": {
        CAT_STRENGTH: {"findings": ["Decisions get made cleanly using the plan and professionals."], "recommendations": ["Keep exchanging relevant records before major decisions."]},
        CAT_DEVELOP:  {"findings": ["Most decisions get made but the process is sometimes ad-hoc."], "recommendations": ["Adopt a written decision-resolution ladder (share records → professional input → mediation)."]},
        CAT_PRIORITY: {"findings": ["Decision-making is a recurring blocker for the child's care."], "recommendations": ["Follow the parenting-plan procedure; consider a Parenting Facilitator for implementation disputes."]},
    },
    "d8": {
        CAT_STRENGTH: {"findings": ["Events are handled child-first, without conflict."], "recommendations": ["Keep the child out of any adult negotiation about attendance."]},
        CAT_DEVELOP:  {"findings": ["Events mostly go smoothly."], "recommendations": ["Keep a shared events calendar so surprises don't create friction."]},
        CAT_PRIORITY: {"findings": ["Events are a recurring source of tension or missed information."], "recommendations": ["Share a written calendar; agree on separate attendance where useful; never ask the child to choose."]},
    },
    "d9": {
        CAT_STRENGTH: {"findings": ["Resource coordination flows smoothly."], "recommendations": ["Keep a shared expense record so nothing surprises either home."]},
        CAT_DEVELOP:  {"findings": ["Resource coordination works but has some sticky points."], "recommendations": ["Adopt a clear reimbursement + prior-consent procedure for shared expenses."]},
        CAT_PRIORITY: {"findings": ["Financial disagreements are delaying services or evaluations."], "recommendations": ["Separate the money question from the child-need question; consider mediating a written expense agreement."]},
    },
    "d10": {  # Safety
        CAT_STRENGTH: {"findings": ["No safety-sensitive concerns were flagged in your responses."], "recommendations": ["Continue to protect a stable, child-focused communication channel."]},
        CAT_SAFETY:   {"findings": ["Your responses indicate safety-sensitive concerns. Ordinary co-parenting recommendations may not be appropriate."], "recommendations": [
            "Consider written-only communication through a parenting app.",
            "Explore school-based or third-party exchanges to minimise direct contact.",
            "Speak confidentially with an attorney or a domestic-violence advocate about protective options.",
            "Do not enter joint sessions or shared decision meetings until safety has been assessed by a qualified professional.",
        ]},
    },
}

_PROFESSIONAL_ADDENDUM = "You explicitly asked for professional guidance on multiple items in this domain — please consider that request an important signal."

COMMUNICATION_TOOLKIT = [
    {"title": "Use BIFF messages", "detail": "Brief, Informative, Friendly, Firm — keep messages to 4 sentences or fewer."},
    {"title": "Move to a written channel", "detail": "Timestamped app or dedicated email thread for therapy, medication, and school updates."},
    {"title": "Weekly child-focused check-in", "detail": "10 minutes, same day/time, with a fixed child-focused agenda."},
    {"title": "Delay before responding", "detail": "Wait 4 hours before replying to charged messages. Draft, save, revise, then send."},
    {"title": "Facts, not feelings, in writing", "detail": "Move emotional processing to a therapist or trusted friend."},
]

DISCLAIMER = (
    "This report is an educational reflection tool from SA CoParents. It is not a diagnostic evaluation, custody evaluation, or legal advice. "
    "Findings are based on your self-assessment answers across the 10 special-needs co-parenting domains."
)


def _domain_meta(did: str) -> Dict[str, Any]:
    for d in DOMAINS:
        if d["id"] == did:
            return d
    return {}


def _overall_paragraph(overall: str, safety_triggered: bool) -> str:
    if safety_triggered:
        return (
            "Your responses flagged one or more safety-sensitive items. Because of this, the "
            "recommendations in this report intentionally do not include joint meetings or "
            "direct communication until a qualified professional has assessed the situation "
            "with you. Please prioritise your safety and your child's safety."
        )
    if overall == OVERALL_STRENGTH:
        return "Your responses show strong, child-focused co-parenting across most domains. Keep protecting what works; use this report to sharpen the areas that could still improve."
    if overall == OVERALL_PRIORITY:
        return "Several domains need focused attention. Completing this assessment is itself a strong first step. Focus on the priority domains one at a time; small, consistent wins compound."
    if overall == OVERALL_DEVELOPING:
        return "You have real strengths to build on alongside a handful of domains that would benefit from focused attention. This report highlights the highest-leverage next steps."
    return "Complete more of the assessment to unlock a full narrative — for now, here is what your answers already show."


def build_report(
    *, scores: Dict[str, Any], answers: Dict[str, int] | None = None,
    meta: Dict[str, Dict[str, bool]] | None = None,
    intake: Dict[str, Any] | None = None,
    parent_name: Optional[str] = None,
) -> Dict[str, Any]:
    _ = answers  # currently unused but kept for parity with cp_report
    _ = meta
    domain_scores: List[Dict[str, Any]] = scores.get("domains") or []
    overall = scores.get("overall_rating") or "Not enough data"
    safety_triggered = bool(scores.get("safety_triggered"))

    domains_out: List[Dict[str, Any]] = []
    for d in domain_scores:
        did = d["id"]
        category = d.get("category")
        band = _DOMAIN_GUIDANCE.get(did, {}).get(category or "", {}) if category else {}
        findings = list(band.get("findings") or [])
        recs = list(band.get("recommendations") or [])
        if category == CAT_PROFESSIONAL:
            findings.append(_PROFESSIONAL_ADDENDUM)
        domains_out.append({
            "id": did,
            "number": d["number"],
            "name": d["name"],
            "goal": _domain_meta(did).get("goal"),
            "framework_ref": _domain_meta(did).get("framework_ref"),
            "category": category,
            # `rating` is a legacy alias kept for the shared PDF renderer +
            # Family Report + shared viewers which still key off `sec.rating`.
            "rating": category,
            "avg": d.get("avg"),
            "answered": d.get("answered", 0),
            "total": d.get("total", 0),
            "want_help_hits": d.get("want_help_hits", 0),
            "safety_flagged": bool(d.get("safety_hits")),
            "findings": findings,
            "recommendations": recs,
        })

    strengths: List[Dict[str, Any]] = []
    for did in scores.get("strongest_domain_ids", []):
        d = next((x for x in domains_out if x["id"] == did), None)
        if d:
            strengths.append({"section_id": did, "title": d["name"], "detail": d.get("goal") or ""})

    growth_areas: List[Dict[str, Any]] = []
    for did in scores.get("priority_focus_ids", []):
        d = next((x for x in domains_out if x["id"] == did), None)
        if d:
            growth_areas.append({
                "section_id": did,
                "title": d["name"],
                "rating": d.get("category"),
                "why_it_matters": (d.get("findings") or [""])[0],
                "first_step": (d.get("recommendations") or [""])[0],
            })

    next_steps: List[str] = []
    for g in growth_areas:
        step = g.get("first_step") or ""
        if step and step not in next_steps:
            next_steps.append(step)
        if len(next_steps) >= 5:
            break
    if safety_triggered:
        next_steps.insert(0, "Prioritise safety planning — see the Safety block below before adopting any joint-meeting recommendations.")
        next_steps = next_steps[:5]

    toolkit = COMMUNICATION_TOOLKIT if scores.get("show_communication_toolkit") else []

    return {
        "prepared_by": (parent_name or "").strip() or None,
        "framework": "SA CoParents Special Needs Co-Parenting Assessment (2026)",
        "intake": intake or {},
        "overall_rating": overall,
        "overall_summary": _overall_paragraph(overall, safety_triggered),
        "safety_triggered": safety_triggered,
        "strengths": strengths,
        "growth_areas": growth_areas,
        "domains": domains_out,
        # Legacy alias used by cross-report machinery (Family Report) — kept
        # so existing PDF/JSON consumers keep working.
        "sections": domains_out,
        "show_communication_toolkit": bool(scores.get("show_communication_toolkit")),
        "communication_toolkit": toolkit,
        "next_steps": next_steps,
        "disclaimer": DISCLAIMER,
    }
