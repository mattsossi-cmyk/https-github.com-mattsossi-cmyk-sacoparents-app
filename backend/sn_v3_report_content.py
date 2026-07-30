"""Deterministic Special Needs report content builder.

Mirrors cp_report_content.py so the two products' JSON payloads look identical
to the Family Report composer, the shared viewers, and the PDF renderers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sn_v3_questions import SECTIONS


# ---------------------------------------------------------------------------
# Section-level guidance library. Keyed by section id + rating band.
# ---------------------------------------------------------------------------
_SECTION_GUIDANCE: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "d1": {  # Understanding the Child
        "Excellent": {"findings": ["You understand your child's needs and what helps them recover from stress."], "recommendations": ["Keep updating your understanding as new professional information arrives."]},
        "Good":      {"findings": ["You know a lot; a few areas of your child's world are still coming into focus."], "recommendations": ["Ask one of your child's professionals for a plain-language summary of current recommendations."]},
        "Fair":      {"findings": ["Some parts of your child's picture are unclear enough that decisions and consistency are affected."], "recommendations": ["Book a 30-minute consult with the diagnosing or treating professional to align on today's picture."]},
        "Needs Improvement": {"findings": ["Gaps in shared knowledge of your child's needs are affecting decisions and consistency."], "recommendations": ["Ask the diagnosing / treating professional for a written child summary you can both use."]},
    },
    "d2": {  # Educational Coordination
        "Excellent": {"findings": ["School participation is strong and information flows both ways."], "recommendations": ["Keep both parents on the school's official contact list."]},
        "Good":      {"findings": ["School coordination mostly works with occasional gaps."], "recommendations": ["Ask the school to send communications to both parents; keep a shared school folder for the child."]},
        "Fair":      {"findings": ["Classroom coordination is inconsistent and may affect academic support."], "recommendations": ["Request a joint parent-teacher meeting; if an IEP/504 is in place, request both parents receive full documentation."]},
        "Needs Improvement": {"findings": ["Educational coordination is a significant gap that may be affecting your child's academic outcomes."], "recommendations": ["Contact the school counsellor to request equal information flow.", "Ask for a case-manager introduction if an IEP/504 is active."]},
    },
    "d3": {  # Healthcare Coordination
        "Excellent": {"findings": ["Medical, mental-health, and therapy coordination is solid."], "recommendations": ["Keep a shared medication + appointment log accessible to both parents."]},
        "Good":      {"findings": ["Healthcare coordination usually works, with some gaps."], "recommendations": ["Confirm both parents are on file with the paediatrician and specialists; align on a refill responsibility."]},
        "Fair":      {"findings": ["Medical information doesn't always reach both homes on time."], "recommendations": ["Ask providers to send appointment summaries to both parents; keep an emergency-info sheet in the child's bag."]},
        "Needs Improvement": {"findings": ["Healthcare coordination gaps could put treatment continuity at risk."], "recommendations": ["Establish an urgent-medical-notification protocol.", "If disputes about care are frequent, consider a medical decision-making clause with your mediator or attorney."]},
    },
    "d4": {  # Daily-Care Consistency
        "Excellent": {"findings": ["Your home offers stable, predictable routines that support your child."], "recommendations": ["Continue anchoring bedtime, mealtimes, and screen limits."]},
        "Good":      {"findings": ["Most routines in your home are consistent, with some drift."], "recommendations": ["Pick one anchor routine (bedtime) and keep it identical for 30 days."]},
        "Fair":      {"findings": ["Daily-care consistency is uneven; transitions and behaviour may be affected."], "recommendations": ["Post a visible daily rhythm; ask your child's therapist for a home-carryover plan."]},
        "Needs Improvement": {"findings": ["Lack of predictable routines is likely adding stress to your child's daily life."], "recommendations": ["Start with one anchor routine (bedtime is highest-impact) and keep it identical for two weeks.", "A parent-coach or family therapist can help build stronger routines."]},
    },
    "d5": {  # Transition Support
        "Excellent": {"findings": ["Transitions are calm and predictable."], "recommendations": ["Keep exchange location and timing consistent to protect that stability."]},
        "Good":      {"findings": ["Exchanges usually go smoothly with occasional friction."], "recommendations": ["Standardise what travels between homes (laminated checklist on the bag)."]},
        "Fair":      {"findings": ["Transitions are a recurring source of stress."], "recommendations": ["Move exchanges to a neutral or school-based location; add visual warnings 24 hours before each exchange."]},
        "Needs Improvement": {"findings": ["Exchanges are conflict-prone and may be affecting your child's wellbeing."], "recommendations": ["Consider curbside or school-based exchanges and a written exchange log.", "A Parenting Facilitator can help reduce direct contact during exchanges."]},
    },
    "d6": {  # Communication
        "Excellent": {"findings": ["Communication is timely, accurate, and child-focused."], "recommendations": ["Keep documenting agreements after each conversation."]},
        "Good":      {"findings": ["Communication is largely reliable with occasional gaps."], "recommendations": ["Add a weekly 10-minute child-focused check-in with a fixed agenda."]},
        "Fair":      {"findings": ["Timeliness and tone of updates are inconsistent — critical information sometimes reaches the other home late."], "recommendations": ["Introduce a shared parenting app for a single source of truth.", "Use the BIFF framework (Brief, Informative, Friendly, Firm) for written messages."]},
        "Needs Improvement": {"findings": ["Communication frequently escalates or breaks down before important information is shared."], "recommendations": ["Move all non-emergency communication to a written, timestamped channel.", "Consider working with a Parenting Facilitator or mediator to establish communication ground rules."]},
    },
    "d7": {  # Decision-Making
        "Excellent": {"findings": ["Decisions get made cleanly using the plan and professionals."], "recommendations": ["Keep exchanging relevant records before major decisions."]},
        "Good":      {"findings": ["Most decisions get made but the process is sometimes ad-hoc."], "recommendations": ["Adopt a written decision-resolution ladder (share records \u2192 professional input \u2192 mediation)."]},
        "Fair":      {"findings": ["Decision-making sometimes stalls before the child's care catches up."], "recommendations": ["Follow the parenting plan procedure and set a deadline for each open decision."]},
        "Needs Improvement": {"findings": ["Decision-making is a recurring blocker for the child's care."], "recommendations": ["Follow the parenting-plan procedure; consider a Parenting Facilitator for implementation disputes."]},
    },
    "d8": {  # Event Participation
        "Excellent": {"findings": ["Events are handled child-first, without conflict."], "recommendations": ["Keep the child out of any adult negotiation about attendance."]},
        "Good":      {"findings": ["Events mostly go smoothly."], "recommendations": ["Keep a shared events calendar so surprises don't create friction."]},
        "Fair":      {"findings": ["Events are a recurring source of tension or missed information."], "recommendations": ["Share a written calendar; agree on separate attendance where useful; never ask the child to choose."]},
        "Needs Improvement": {"findings": ["Event participation is producing conflict or leaving the child in the middle."], "recommendations": ["Move all event announcements to a shared calendar with reminders.", "Agree on separate attendance for now and revisit later."]},
    },
    "d9": {  # Resource Coordination
        "Excellent": {"findings": ["Resource coordination flows smoothly."], "recommendations": ["Keep a shared expense record so nothing surprises either home."]},
        "Good":      {"findings": ["Resource coordination works but has some sticky points."], "recommendations": ["Adopt a clear reimbursement + prior-consent procedure for shared expenses."]},
        "Fair":      {"findings": ["Financial coordination is causing occasional gaps in the child's services."], "recommendations": ["Separate the money question from the child-need question; agree on a written expense procedure."]},
        "Needs Improvement": {"findings": ["Financial disagreements are delaying services or evaluations."], "recommendations": ["Bring an accountant or mediator in to write a shared-expense agreement."]},
    },
}


COMMUNICATION_TOOLKIT: List[Dict[str, str]] = [
    {"title": "Use BIFF messages", "detail": "Brief, Informative, Friendly, Firm. Aim for 4 sentences or fewer per message."},
    {"title": "Move to a written channel", "detail": "Use a shared parenting app or dedicated email thread for all non-emergency communication so it's timestamped."},
    {"title": "Weekly child-focused check-in", "detail": "10 minutes, same day/time, with a fixed agenda: schedule, health, school, one 'what's working'."},
    {"title": "Delay before responding", "detail": "Wait 4 hours before replying to any charged message. Draft, save, revise, then send."},
    {"title": "Focus on facts, not feelings, in writing", "detail": "Move emotional processing to a therapist or trusted friend — keep co-parent communication practical."},
]


DEFAULT_DISCLAIMER = (
    "This report is an educational reflection tool from SA CoParents. It is not a diagnosis, "
    "custody evaluation, or legal advice. Findings are based on your own self-assessment answers "
    "on a 5-point scale across nine special-needs co-parenting sections."
)


def _sec_meta(sid: str) -> Dict[str, Any]:
    for s in SECTIONS:
        if s["id"] == sid:
            return s
    return {}


def _overall_paragraph(overall: str) -> str:
    if overall == "Excellent Progress":
        return (
            "Your responses reflect strong, child-focused special-needs co-parenting habits "
            "across most sections. Keep protecting the systems that are working, and use this "
            "report to sharpen the one or two areas that could still improve."
        )
    if overall == "Building Progress":
        return (
            "You have real strengths to build on, alongside a handful of sections that would "
            "benefit from focused attention. This report highlights the highest-leverage next steps."
        )
    if overall == "Early Progress":
        return (
            "Several important sections need attention. That's a normal starting point — and "
            "completing this assessment is itself a strong first step. Focus on the priority "
            "sections one at a time; small, consistent wins compound."
        )
    return "Complete more of the assessment to unlock a full narrative — for now, here is what your partial answers already show."


def build_report(
    *,
    scores: Dict[str, Any],
    answers: Dict[str, int] | None = None,
    meta: Dict[str, Dict[str, bool]] | None = None,
    intake: Dict[str, Any] | None = None,
    parent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Compose the full deterministic Special Needs report from scoring output."""
    _ = answers
    _ = meta
    section_scores: List[Dict[str, Any]] = scores.get("sections") or []
    overall = scores.get("overall_rating") or "Not enough data"
    priority_ids = list(scores.get("priority_focus") or [])
    show_toolkit = bool(scores.get("show_communication_toolkit"))

    # Per-section detail
    sections_out: List[Dict[str, Any]] = []
    for sec in section_scores:
        sid = sec["id"]
        rating = sec.get("rating") or "Needs Improvement"
        band = _SECTION_GUIDANCE.get(sid, {}).get(rating) or {}
        meta_row = _sec_meta(sid)
        sections_out.append({
            "id": sid,
            "number": sec.get("number"),
            "name": sec.get("name"),
            "goal": meta_row.get("goal"),
            "rating": sec.get("rating"),
            "avg": sec.get("avg"),
            "answered": sec.get("answered", 0),
            "total": sec.get("total", 0),
            "want_help_hits": sec.get("want_help_hits", 0),
            "need_info_hits": sec.get("need_info_hits", 0),
            "findings": list(band.get("findings") or []),
            "recommendations": list(band.get("recommendations") or []),
        })

    # Strengths — up to 3 strongest sections rated Excellent/Good.
    strengths: List[Dict[str, Any]] = []
    ranked = sorted(
        [s for s in section_scores if s.get("avg") is not None and s.get("rating") in ("Excellent", "Good")],
        key=lambda s: (-(s["avg"] or 0), s["number"]),
    )
    for s in ranked[:3]:
        strengths.append({
            "section_id": s["id"],
            "title": s["name"],
            "detail": (_sec_meta(s["id"]).get("goal") or "").strip() or f"Rated {s.get('rating')}.",
        })
    if not strengths and section_scores:
        best = max(
            (s for s in section_scores if s.get("avg") is not None),
            key=lambda s: s["avg"],
            default=None,
        )
        if best:
            strengths.append({
                "section_id": best["id"],
                "title": best["name"],
                "detail": f"Your strongest area so far ({best.get('rating')}).",
            })

    # Growth areas — priority_focus first, then any Fair sections not already listed
    growth_ids: List[str] = list(priority_ids)
    for s in section_scores:
        if s.get("rating") == "Fair" and s["id"] not in growth_ids:
            growth_ids.append(s["id"])
    growth_areas: List[Dict[str, Any]] = []
    for sid in growth_ids[:4]:
        sec = next((s for s in section_scores if s["id"] == sid), None)
        if not sec:
            continue
        band = _SECTION_GUIDANCE.get(sid, {}).get(sec.get("rating") or "Needs Improvement", {})
        growth_areas.append({
            "section_id": sid,
            "title": sec.get("name"),
            "rating": sec.get("rating"),
            "why_it_matters": (band.get("findings") or [""])[0],
            "first_step": (band.get("recommendations") or [""])[0],
        })

    # Next steps
    next_steps: List[str] = []
    for ga in growth_areas:
        rec = ga.get("first_step") or ""
        if rec and rec not in next_steps:
            next_steps.append(rec)
        if len(next_steps) >= 5:
            break
    if not next_steps and strengths:
        next_steps.append("Keep protecting the routines that are already working.")

    return {
        "prepared_by": (parent_name or "").strip() or None,
        "framework": "SA CoParents Special Needs Co-Parenting Assessment (9 sections)",
        "intake": intake or {},
        "overall_rating": overall,
        "overall_summary": _overall_paragraph(overall),
        "strengths": strengths,
        "growth_areas": growth_areas,
        "sections": sections_out,
        # Legacy alias so existing consumers that read `domains` keep working.
        "domains": sections_out,
        "communication_toolkit": COMMUNICATION_TOOLKIT if show_toolkit else [],
        "show_communication_toolkit": show_toolkit,
        "next_steps": next_steps,
        "strongest_section_ids": sorted(scores.get("strongest_section_ids") or []),
        "weakest_section_ids": sorted(scores.get("weakest_section_ids") or []),
        "disclaimer": DEFAULT_DISCLAIMER,
    }
