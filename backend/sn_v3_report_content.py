"""Deterministic Special Needs v3 report content builder.

Mirrors cp_report_content.py so the two dynamic reports produce the exact same
JSON shape and feel like part of the same product. Guidance library is keyed
by principle id + rating band, tailored to special-needs co-parenting.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sn_v3_questions import SECTIONS as SN_SECTIONS


_PRINCIPLE_GUIDANCE: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "p1": {  # Build an Individualized Parenting Plan
        "Excellent": {
            "findings": ["Your parenting plan is truly individualized to your child's transition and sensory needs."],
            "recommendations": ["Revisit the plan every 6 months as your child grows and needs shift."],
        },
        "Good": {
            "findings": ["The plan reflects your child's needs, with a few gaps around exchanges or updates."],
            "recommendations": ["Add an explicit review cadence (calendar reminder every 6 months)."],
        },
        "Fair": {
            "findings": ["The plan feels like a generic template in places — it doesn't fully reflect your child's regulation patterns."],
            "recommendations": [
                "Rewrite one section to name the specific supports your child needs (sensory, transition, medication).",
                "Ask your child's therapist to help translate clinical needs into schedule language.",
            ],
        },
        "Needs Improvement": {
            "findings": ["The current plan doesn't yet reflect how your child actually functions day-to-day."],
            "recommendations": [
                "Draft a special-needs addendum listing sensory, medical, and therapy accommodations.",
                "Work with a mediator experienced in special-needs plans to formalize it.",
            ],
        },
    },
    "p2": {  # Prioritize Consistent Routines & Predictability
        "Excellent": {"findings": ["Your home offers strong, predictable routines that support your child."], "recommendations": ["Share your successful routines with the other parent when helpful."]},
        "Good": {"findings": ["Most core routines in your home are consistent."], "recommendations": ["Pick one routine (bedtime, mealtime) to align with the other home."]},
        "Fair": {"findings": ["Routines vary enough in your home that transitions become harder for your child."], "recommendations": ["Anchor bedtime — it's the highest-impact routine — and keep it identical for two weeks.", "Post the daily rhythm somewhere visible."]},
        "Needs Improvement": {"findings": ["Lack of predictable routines is likely adding stress and dysregulation."], "recommendations": ["Start with ONE anchor routine and hold it for 30 days.", "Ask your child's therapist for a visual schedule template."]},
    },
    "p3": {  # Maintain Open, Child-Focused Communication
        "Excellent": {"findings": ["Child-focused communication with the other parent is working well."], "recommendations": ["Keep documenting agreements in writing after each conversation."]},
        "Good": {"findings": ["Communication is largely reliable, with occasional gaps."], "recommendations": ["Add a weekly 10-minute child-focused check-in for continuity of care."]},
        "Fair": {"findings": ["Timeliness and tone of updates are inconsistent — therapy/medication/school info sometimes reaches the other home late."], "recommendations": ["Move to a shared parenting app for a single source of truth.", "Use the BIFF framework (Brief, Informative, Friendly, Firm) in writing."]},
        "Needs Improvement": {"findings": ["Conversations escalate before important information is shared, which can put continuity of care at risk."], "recommendations": ["Move all non-emergency communication to a written, timestamped channel.", "Consider a Parenting Facilitator experienced with special-needs coordination."]},
    },
    "p4": {  # Align on Core Expectations
        "Excellent": {"findings": ["Medication, therapy, screen-time, and discipline expectations are well aligned."], "recommendations": ["Continue joint parent-training sessions when new challenges arise."]},
        "Good": {"findings": ["Most core expectations are aligned between homes."], "recommendations": ["Identify one area (screen-time or bedtime) to fully align."]},
        "Fair": {"findings": ["Medication schedules or behavioral expectations differ enough to confuse your child."], "recommendations": ["Ask the prescribing provider to give both parents the same written protocol.", "Agree on a shared discipline approach for meltdowns — even a one-page document helps."]},
        "Needs Improvement": {"findings": ["Cross-home inconsistency in core expectations is likely undermining your child's progress."], "recommendations": ["Book a joint parent-training session with your child's therapist.", "Consider formalizing medical decision-making language with your mediator or attorney."]},
    },
    "p5": {  # Understand & Share Your Child's Diagnosis and Needs
        "Excellent": {"findings": ["You have a strong working knowledge of your child's diagnosis and support needs."], "recommendations": ["Share updated diagnostic reports with all providers and the other parent."]},
        "Good": {"findings": ["Your understanding of the diagnosis is solid, with some information still to build."], "recommendations": ["Attend one professional-development session or workshop per year."]},
        "Fair": {"findings": ["There are gaps in shared knowledge between homes about what the diagnosis means day-to-day."], "recommendations": ["Ask the diagnosing provider for a plain-language summary both parents can read.", "Request that IEP/504 and therapy reports go to both parents."]},
        "Needs Improvement": {"findings": ["Limited shared understanding of the diagnosis is a coordination risk."], "recommendations": ["Request a joint consultation with the diagnosing provider.", "Both parents attend the next IEP/504 meeting."]},
    },
    "p6": {  # Coordinate Education & Therapy
        "Excellent": {"findings": ["Both parents are actively engaged in education and therapy carryover."], "recommendations": ["Keep a shared therapy-carryover log accessible to both parents."]},
        "Good": {"findings": ["Coordination on education and therapy usually works."], "recommendations": ["Ask the school to add both parents to all official communications."]},
        "Fair": {"findings": ["Classroom accommodations and therapy homework aren't consistently reinforced across both homes."], "recommendations": ["Ask the therapist for a written home-carryover plan.", "Schedule 10 minutes of therapy practice into the daily rhythm."]},
        "Needs Improvement": {"findings": ["Educational and therapy coordination is a significant gap — therapeutic gains may be limited."], "recommendations": ["Request a joint parent-training session with the therapist.", "If IEP/504 is in place, request full documentation goes to both parents."]},
    },
    "p7": {  # Manage Transitions Smoothly
        "Excellent": {"findings": ["Exchanges are calm, sensory-friendly, and predictable."], "recommendations": ["Keep exchange location and timing consistent to protect that stability."]},
        "Good": {"findings": ["Exchanges usually go smoothly."], "recommendations": ["Add a 5-minute buffer for transition time on either side."]},
        "Fair": {"findings": ["Your child shows anxiety around exchanges more often than you'd like."], "recommendations": ["Move exchanges to a neutral, low-stimulation location.", "Use transition warnings and a visual schedule 24 hours before each exchange."]},
        "Needs Improvement": {"findings": ["Transitions are a significant source of dysregulation."], "recommendations": ["Consider curbside exchanges to minimize direct contact.", "Ask your child's therapist for a transition-support protocol."]},
    },
    "p8": {  # Be Flexible and Adaptable
        "Excellent": {"findings": ["You adapt well as your child's needs, abilities, and preferences evolve."], "recommendations": ["Keep welcoming input from teachers, therapists, and specialists."]},
        "Good": {"findings": ["You're generally open to adjusting the plan when things change."], "recommendations": ["Set a formal 6-month plan review to catch drift proactively."]},
        "Fair": {"findings": ["The plan hasn't been updated recently, even though needs may have shifted."], "recommendations": ["Book a 30-minute plan-review conversation with the other parent.", "Ask one professional (teacher, therapist) for their perspective on what should change."]},
        "Needs Improvement": {"findings": ["The plan is out of step with where your child is now."], "recommendations": ["Schedule a formal re-review of the plan with a mediator.", "Ask your child's therapist to attend the review to advocate for accommodations."]},
    },
    "p9": {  # Build a Support Network
        "Excellent": {"findings": ["You've built a strong network of therapists, educators, and community support."], "recommendations": ["Keep leaning on your network — you don't have to do this alone."]},
        "Good": {"findings": ["You have professionals to consult when you're stuck."], "recommendations": ["Consider joining one parent-support group for continuity between visits."]},
        "Fair": {"findings": ["Support-network engagement is inconsistent."], "recommendations": ["Identify one gap (mediator, respite care, support group) and address it this month.", "Add a 'who to call' list to your phone for after-hours crises."]},
        "Needs Improvement": {"findings": ["You may be doing too much alone."], "recommendations": ["Book one intake with a special-needs-experienced mediator, attorney, or coach.", "Ask your child's therapist for local community-resource recommendations."]},
    },
    "p10": {  # Practice Compassion and Patience
        "Excellent": {"findings": ["You approach disagreements with empathy and keep your child at the center."], "recommendations": ["Continue modeling self-regulation for your child."]},
        "Good": {"findings": ["You're generally patient and solution-focused."], "recommendations": ["Add a brief daily reflection: what worked today?"]},
        "Fair": {"findings": ["Frustration is starting to show up in conversations or self-care is slipping."], "recommendations": ["Add one weekly self-care practice you don't skip.", "Speak with a therapist or coach about co-parenting stress."]},
        "Needs Improvement": {"findings": ["Ongoing stress is affecting your capacity to co-parent from a compassionate place."], "recommendations": ["Prioritize your own therapy or coaching this quarter.", "Consider a Parenting Facilitator to hold the child-focused frame during hard conversations."]},
    },
}


COMMUNICATION_TOOLKIT: List[Dict[str, str]] = [
    {"title": "Use BIFF messages", "detail": "Brief, Informative, Friendly, Firm. Keep each message to 4 sentences or fewer."},
    {"title": "Move to a written channel", "detail": "Use a shared parenting app or dedicated email thread so therapy, medication, and school updates are timestamped."},
    {"title": "Weekly child-focused check-in", "detail": "10 minutes, same day/time, fixed agenda: therapy progress, medication, school, one 'what's working'."},
    {"title": "Delay before responding", "detail": "Wait 4 hours before replying to a charged message. Draft, save, revise, then send."},
    {"title": "Facts, not feelings, in writing", "detail": "Move emotional processing to a therapist or trusted friend. Keep co-parent communication practical."},
]


DEFAULT_DISCLAIMER = (
    "This report is an educational reflection tool from SA CoParents. It is not "
    "a diagnostic evaluation, custody evaluation, or legal advice. Findings are "
    "based on your own self-assessment answers on a 5-point scale across the "
    "10-principle special-needs co-parenting framework."
)


def _sec_meta(sid: str) -> Dict[str, Any]:
    for s in SN_SECTIONS:
        if s["id"] == sid:
            return s
    return {}


def _overall_paragraph(overall: str) -> str:
    if overall == "Excellent Progress":
        return (
            "Your responses reflect strong, child-focused special-needs co-parenting "
            "across most of the 10 principles. Keep protecting the systems that are "
            "working, and use this report to sharpen the one or two areas that could "
            "still improve."
        )
    if overall == "Building Progress":
        return (
            "You have real strengths to build on, alongside a handful of principles "
            "that would benefit from focused attention. This report highlights the "
            "highest-leverage next steps for supporting your child across two homes."
        )
    if overall == "Early Progress":
        return (
            "Several principles need attention. That's a normal starting point — and "
            "completing this assessment is itself a strong first step. Focus on the "
            "priority principles one at a time; small, consistent wins compound."
        )
    return (
        "Complete more of the assessment to unlock a full narrative — for now, "
        "here is what your partial answers already show."
    )


def _pick_answered_prompts(section_id: str, answers: Dict[str, int], *, wanted_low: bool, limit: int = 2) -> List[str]:
    """Return prompts from a principle, filtered by effective score."""
    out: List[str] = []
    for q in _sec_meta(section_id).get("questions", []):
        qid = q["id"]
        if qid not in answers:
            continue
        raw = answers[qid]
        effective = (4 - raw) if q.get("reverse") else raw
        if wanted_low and effective <= 1:
            out.append(q["prompt"])
        elif (not wanted_low) and effective >= 3:
            out.append(q["prompt"])
        if len(out) >= limit:
            break
    return out


def build_report(
    *,
    scores: Dict[str, Any],
    answers: Dict[str, int],
    parent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Compose the full deterministic Special Needs v3 report from scoring output.

    Returns the same top-level shape as cp_report_content.build_report so the
    frontend and PDF renderers can be near-identical.
    """
    section_scores: List[Dict[str, Any]] = scores.get("sections") or []
    overall = scores.get("overall_rating") or "Not enough data"
    strongest_ids = set(scores.get("strongest_section_ids") or [])
    weakest_ids = set(scores.get("weakest_section_ids") or [])
    priority_ids = list(scores.get("priority_focus") or [])
    show_toolkit = bool(scores.get("show_communication_toolkit"))

    sections_out: List[Dict[str, Any]] = []
    for sec in section_scores:
        sid = sec["id"]
        rating = sec.get("rating") or "Needs Improvement"
        band = _PRINCIPLE_GUIDANCE.get(sid, {}).get(rating) or {}
        meta = _sec_meta(sid)
        sections_out.append({
            "id": sid,
            "number": sec.get("number"),
            "name": sec.get("name"),
            "goal": meta.get("goal"),
            "rating": sec.get("rating"),
            "avg": sec.get("avg"),
            "answered": sec.get("answered", 0),
            "total": sec.get("total", 0),
            "findings": list(band.get("findings") or []),
            "recommendations": list(band.get("recommendations") or []),
            "example_prompts": _pick_answered_prompts(sid, answers, wanted_low=(rating in ("Fair", "Needs Improvement"))),
        })

    # Strengths — up to 3 Good/Excellent principles
    strengths: List[Dict[str, str]] = []
    ranked = sorted(
        [s for s in section_scores if s.get("avg") is not None and s.get("rating") in ("Excellent", "Good")],
        key=lambda s: (-(s["avg"] or 0), s["number"]),
    )
    for s in ranked[:3]:
        meta = _sec_meta(s["id"])
        strengths.append({
            "section_id": s["id"],
            "title": s["name"],
            "detail": (meta.get("goal") or "").strip() or f"Rated {s.get('rating')}.",
        })
    if not strengths and section_scores:
        best = max(
            (s for s in section_scores if s.get("avg") is not None),
            key=lambda s: s["avg"],
            default=None,
        )
        if best:
            meta = _sec_meta(best["id"])
            strengths.append({
                "section_id": best["id"],
                "title": best["name"],
                "detail": f"Your strongest area so far ({best.get('rating')}).",
            })

    # Growth areas — priority_focus first, then any Fair principles not already listed
    growth_ids: List[str] = list(priority_ids)
    for s in section_scores:
        if s.get("rating") == "Fair" and s["id"] not in growth_ids:
            growth_ids.append(s["id"])
    growth_areas: List[Dict[str, Any]] = []
    for sid in growth_ids[:4]:
        sec = next((s for s in section_scores if s["id"] == sid), None)
        if not sec:
            continue
        band = _PRINCIPLE_GUIDANCE.get(sid, {}).get(sec.get("rating") or "Needs Improvement", {})
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
        next_steps.append("Keep protecting the routines and systems that are already working.")

    return {
        "prepared_by": (parent_name or "").strip() or None,
        "framework": "10-principle special-needs co-parenting",
        "overall_rating": overall,
        "overall_summary": _overall_paragraph(overall),
        "strengths": strengths,
        "growth_areas": growth_areas,
        "sections": sections_out,
        "communication_toolkit": COMMUNICATION_TOOLKIT if show_toolkit else [],
        "show_communication_toolkit": show_toolkit,
        "next_steps": next_steps,
        "strongest_section_ids": sorted(strongest_ids),
        "weakest_section_ids": sorted(weakest_ids),
        "disclaimer": DEFAULT_DISCLAIMER,
    }
