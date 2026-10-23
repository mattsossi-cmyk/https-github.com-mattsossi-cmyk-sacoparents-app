"""Deterministic Co-Parenting report content builder.

Converts (answers, scores) from the 10-section Co-Parenting Assessment into a
structured report dict ready for JSON API responses AND PDF rendering.

Kept fully deterministic (no LLM) so the same inputs always yield the same
report — matches the design of coparenting_scoring.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from coparenting_questions import SECTIONS as CP_SECTIONS, find_question


# ------------------------------------------------------------------
# Section-level guidance library. Keyed by section id + rating band.
# Copy is intentionally practical and single-parent framed ("your home").
# ------------------------------------------------------------------
_SECTION_GUIDANCE: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "s1": {  # Communication & Information Sharing
        "Excellent": {
            "findings": [
                "Information flows both ways and stays focused on the child.",
                "Escalation is rare and de-escalation tools are already working.",
            ],
            "recommendations": [
                "Keep using a shared calendar/app for schedule and updates.",
                "Continue documenting agreements in writing after each conversation.",
            ],
        },
        "Good": {
            "findings": [
                "Information sharing is largely reliable, with occasional gaps.",
            ],
            "recommendations": [
                "Set a weekly 10-minute child-focused check-in.",
                "Confirm major updates in writing to reduce misunderstandings.",
            ],
        },
        "Fair": {
            "findings": [
                "Timeliness and tone of updates are inconsistent — critical information sometimes reaches the other home late.",
            ],
            "recommendations": [
                "Introduce a shared parenting app (e.g. OurFamilyWizard, TalkingParents) for a single source of truth.",
                "Use the BIFF framework (Brief, Informative, Friendly, Firm) for written messages.",
            ],
        },
        "Needs Improvement": {
            "findings": [
                "Communication frequently escalates or breaks down before important information is shared.",
            ],
            "recommendations": [
                "Move all non-emergency communication to a written, timestamped channel.",
                "Consider working with a Parenting Facilitator or mediator to establish communication ground rules.",
            ],
        },
    },
    "s2": {  # Transitions
        "Excellent": {"findings": ["Exchanges are calm, punctual, and predictable."], "recommendations": ["Keep the exchange location and timing consistent to protect that stability."]},
        "Good": {"findings": ["Exchanges usually go smoothly with occasional friction."], "recommendations": ["Standardize what travels between homes (a laminated checklist on the bag)."]},
        "Fair": {"findings": ["Exchanges are frequently a source of stress for you or your child."], "recommendations": ["Move exchanges to a neutral, low-stimulation location and add a 5-minute buffer for transition time."]},
        "Needs Improvement": {"findings": ["Exchanges are conflict-prone and may be affecting your child's wellbeing."], "recommendations": ["Consider curbside exchanges, exchange logs, and a professional Parenting Facilitator's help to reduce direct contact during exchanges."]},
    },
    "s3": {  # Education
        "Excellent": {"findings": ["Both homes actively support academic success."], "recommendations": ["Continue attending school events together when possible."]},
        "Good": {"findings": ["Academic support is generally consistent between homes."], "recommendations": ["Add both parents' emails to the school's official contact list to ensure equal information flow."]},
        "Fair": {"findings": ["Homework routines and school communication are inconsistent."], "recommendations": ["Create a shared 'school folder' (physical or digital) that travels with the child.", "Request the school send communications to both parents."]},
        "Needs Improvement": {"findings": ["Educational coordination is a significant gap that may be affecting your child's academic outcomes."], "recommendations": ["Schedule a joint parent-teacher meeting.", "If an IEP/504 is in place, request both parents receive full documentation."]},
    },
    "s4": {  # Medical
        "Excellent": {"findings": ["Medical care is well-coordinated across both homes."], "recommendations": ["Keep a shared medication + appointment log accessible to both parents."]},
        "Good": {"findings": ["Healthcare coordination works most of the time."], "recommendations": ["Confirm both parents are on file with the pediatrician and specialists."]},
        "Fair": {"findings": ["Medical information doesn't always reach both homes on time."], "recommendations": ["Ask providers to send appointment summaries to both parents.", "Keep an emergency-info sheet in the child's bag."]},
        "Needs Improvement": {"findings": ["Medical coordination gaps could put the child's safety or treatment continuity at risk."], "recommendations": ["Establish an urgent-medical-notification protocol.", "If disputes about care are frequent, consider a medical decision-making clause with your mediator or attorney."]},
    },
    "s5": {  # Home consistency
        "Excellent": {"findings": ["Your home offers predictable routines that support your child's wellbeing."], "recommendations": ["Share your successful routines with the other parent when helpful."]},
        "Good": {"findings": ["Most routines in your home are consistent."], "recommendations": ["Identify one routine (bedtime, mealtime) to align across both homes."]},
        "Fair": {"findings": ["Daily routines in your home vary enough that transitions become harder for your child."], "recommendations": ["Establish a written daily rhythm — meals, homework, screen-time, bedtime.", "Discuss with the other parent which routines could be aligned."]},
        "Needs Improvement": {"findings": ["Lack of predictable routines is likely adding stress to your child's daily life."], "recommendations": ["Start with one anchor routine (bedtime is highest-impact) and keep it identical for two weeks.", "A parent-coach or family therapist can help build stronger routines."]},
    },
    "s6": {  # Emotional support
        "Excellent": {"findings": ["Your child feels safe expressing emotions to you."], "recommendations": ["Continue naming feelings and using positive reinforcement."]},
        "Good": {"findings": ["Emotional support is generally strong."], "recommendations": ["Add a brief daily emotional check-in (2 highs / 1 low)."]},
        "Fair": {"findings": ["Your child may be masking feelings or struggling to regulate."], "recommendations": ["Learn 2-3 co-regulation techniques (deep breathing, 5-4-3-2-1 grounding).", "Consider a short course of child-focused counseling."]},
        "Needs Improvement": {"findings": ["Your child may need additional emotional-support scaffolding."], "recommendations": ["Consult a child psychologist or licensed therapist.", "Educational family therapy can strengthen both parent-child bonds."]},
    },
    "s7": {  # Therapy reinforcement
        "Excellent": {"findings": ["Therapy carryover in your home is strong."], "recommendations": ["Keep sharing progress with the therapist and other parent."]},
        "Good": {"findings": ["You follow through on most therapy recommendations."], "recommendations": ["Ask the therapist for a written home-carryover plan."]},
        "Fair": {"findings": ["Therapy homework isn't consistently reinforced at home."], "recommendations": ["Schedule 10 minutes of therapy practice into the daily rhythm.", "Ask the therapist to include both parents in periodic parent-training sessions."]},
        "Needs Improvement": {"findings": ["Therapy carryover is limited, reducing therapeutic gains."], "recommendations": ["Request the therapist coach you on 1-2 specific home strategies.", "If cross-home consistency is an issue, ask about a joint parent-training session."]},
    },
    "s8": {  # Safety
        "Excellent": {"findings": ["Physical, medical, and digital safety practices are solid."], "recommendations": ["Do a periodic safety walkthrough as the child grows."]},
        "Good": {"findings": ["Most safety practices are in place."], "recommendations": ["Review medication storage, car-seat/booster fit, and emergency contacts annually."]},
        "Fair": {"findings": ["A few safety gaps could put the child at avoidable risk."], "recommendations": ["Write down emergency contacts and post them somewhere visible.", "Confirm supervision arrangements are age-appropriate."]},
        "Needs Improvement": {"findings": ["Safety gaps warrant immediate attention."], "recommendations": ["Address supervision, transportation, medication, or environmental hazards this week.", "If there are safety concerns about the other home, discuss with your attorney or a domestic-violence advocate before informal action."]},
    },
    "s9": {  # Social
        "Excellent": {"findings": ["Your child is thriving socially."], "recommendations": ["Keep encouraging peer relationships and extracurriculars."]},
        "Good": {"findings": ["Social participation is generally healthy."], "recommendations": ["Coordinate with the other parent so activities aren't lost in transitions."]},
        "Fair": {"findings": ["Social participation is inconsistent between homes."], "recommendations": ["Agree on a shared list of activities/friends the child continues across both homes.", "Confirm invitations reach both parents."]},
        "Needs Improvement": {"findings": ["Your child may benefit from more social connection and structured participation."], "recommendations": ["Enroll in one predictable weekly activity.", "If social difficulties persist, consider a social-skills group or child therapist."]},
    },
    "s10": {  # Long-term success
        "Excellent": {"findings": ["You're intentionally building your child's future skills."], "recommendations": ["Continue teaching problem-solving, self-advocacy, and celebrating growth."]},
        "Good": {"findings": ["You're thinking ahead about your child's growth."], "recommendations": ["Add age-appropriate responsibilities to build independence."]},
        "Fair": {"findings": ["Long-term skill-building is inconsistent."], "recommendations": ["Pick one skill (decision-making, time management) and reinforce it weekly.", "Celebrate small wins to build self-esteem."]},
        "Needs Improvement": {"findings": ["Focus on long-term growth is currently limited by day-to-day stress."], "recommendations": ["Set one small growth goal per month.", "Consider working with a parent coach on long-term child development strategies."]},
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
    "This report is an educational reflection tool from SA CoParents. It is not "
    "a diagnosis, custody evaluation, or legal advice. Findings are based on "
    "your own self-assessment answers on a 5-point scale."
)


def _sec_meta(sid: str) -> Dict[str, Any]:
    for s in CP_SECTIONS:
        if s["id"] == sid:
            return s
    return {}


def _overall_paragraph(overall: str) -> str:
    if overall == "Excellent Progress":
        return (
            "Your responses reflect strong, child-focused co-parenting habits across "
            "most areas. Keep protecting the systems that are working, and use this "
            "report to sharpen the one or two areas that could still improve."
        )
    if overall == "Building Progress":
        return (
            "You have real strengths to build on, alongside a handful of areas that "
            "would benefit from focused attention. This report highlights the highest-"
            "leverage next steps."
        )
    if overall == "Early Progress":
        return (
            "Several important areas need attention. That's a normal starting point — "
            "and completing this assessment is itself a strong first step. Focus on "
            "the priority areas one at a time; small, consistent wins compound."
        )
    return (
        "Complete more of the assessment to unlock a full narrative — for now, "
        "here is what your partial answers already show."
    )


def _pick_answered_prompts(section_id: str, answers: Dict[str, int], *, wanted_low: bool, limit: int = 2) -> List[str]:
    """Return prompts from a section, filtered by whether the effective score
    is low (wanted_low=True) or high (wanted_low=False). Used to surface
    concrete examples inside findings/strengths."""
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
    """Compose the full deterministic Co-Parenting report from scoring output.

    Returns a dict with these top-level keys (all string / list of dicts):
        overall_rating, overall_summary, strengths, growth_areas, sections,
        communication_toolkit, next_steps, disclaimer, prepared_by.
    """
    section_scores: List[Dict[str, Any]] = scores.get("sections") or []
    overall = scores.get("overall_rating") or "Not enough data"
    strongest_ids = set(scores.get("strongest_section_ids") or [])
    weakest_ids = set(scores.get("weakest_section_ids") or [])
    priority_ids = list(scores.get("priority_focus") or [])
    show_toolkit = bool(scores.get("show_communication_toolkit"))

    # Per-section detail
    sections_out: List[Dict[str, Any]] = []
    for sec in section_scores:
        sid = sec["id"]
        rating = sec.get("rating") or "Needs Improvement"
        band = _SECTION_GUIDANCE.get(sid, {}).get(rating) or {}
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

    # Strengths — up to 3 strongest sections with an "Excellent" or "Good" rating
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
    # Fallback — if nothing strong yet, use the highest-avg section available
    if not strengths and ranked == [] and section_scores:
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

    # Next steps — take the first recommendation from each of the top growth
    # sections, deduped; cap at 5.
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


# Safer report tips: when the parent shared safety concerns (their Self Journey pick, or the app's existing safety
# flag), suggestions that need direct contact are swapped for separate-meeting / professional-routed versions.
SAFER_SWAPS: Dict[str, str] = {
    "Continue attending school events together when possible.":
        "Ask the school about attending events at separate times or sitting apart, so each parent can be there safely.",
    "Schedule a joint parent-teacher meeting.": "Ask the school for separate parent-teacher conferences.",
    "Ask the therapist to include both parents in periodic parent-training sessions.":
        "Ask the therapist about separate parent-training sessions for each parent.",
    "If cross-home consistency is an issue, ask about a joint parent-training session.":
        "If cross-home consistency is an issue, ask the therapist about separate sessions for each parent.",
    "Share your successful routines with the other parent when helpful.":
        "Write down the routines that work in your home so a professional can share them if helpful.",
    "Identify one routine (bedtime, mealtime) to align across both homes.":
        "Pick one routine (bedtime, mealtime) to keep steady in your home.",
    "Discuss with the other parent which routines could be aligned.":
        "If routines need to line up, ask your mediator or parenting facilitator to help instead of discussing it directly.",
    "Keep sharing progress with the therapist and other parent.":
        "Keep sharing progress with the therapist, who can update the other parent if appropriate.",
    "Coordinate with the other parent so activities aren't lost in transitions.":
        "Use a written schedule or parenting app so activities aren't lost in transitions.",
    "Agree on a shared list of activities/friends the child continues across both homes.":
        "Keep a written list of the child's activities and friends that travels with the child between homes.",
}


def safer_report(value: Any) -> Any:
    """Copy of a stored report with every joint suggestion swapped (exact matches only)."""
    if isinstance(value, str):
        return SAFER_SWAPS.get(value, value)
    if isinstance(value, list):
        return [safer_report(v) for v in value]
    if isinstance(value, dict):
        return {k: safer_report(v) for k, v in value.items()}
    return value
