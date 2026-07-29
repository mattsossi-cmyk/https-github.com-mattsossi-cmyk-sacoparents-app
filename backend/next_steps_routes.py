"""Personalised "Your Next Three Steps" — end-of-assessment routing.

After every assessment (Readiness Check · Communication Style · Family
Violence & Safety · Special Needs Coordination), the parent sees three
personalised, actionable next steps auto-generated from their answers.
The steps are rule-based (deterministic) so the same answers always
produce the same recommendations — the AI never authors these.

Endpoints (mounted under /api/next-steps):
  GET  /{assessment}                    → three steps (auto-generates when missing)
  POST /{assessment}/generate           → force a recompute
  POST /{assessment}/{step_id}/action   → done | dismiss | undo
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import get_current_user

router = APIRouter(prefix="/next-steps", tags=["next-steps"])

ASSESSMENTS = ("readiness", "comm_style", "safety", "special_needs", "coparenting")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _step(step_id: str, *, what: str, why: str, how_long: str, cta_label: str,
          cta_path: str, category: str = "preparation") -> dict:
    """Shape one step. Kept flat so the frontend can render without a mapper."""
    return {
        "step_id": step_id,
        "what": what,
        "why": why,
        "how_long": how_long,
        "cta_label": cta_label,
        "cta_path": cta_path,
        "category": category,
        "done": False,
        "dismissed": False,
    }


# ---------------------------------------------------------------------------
# Per-assessment rule engines
# ---------------------------------------------------------------------------
def _readiness_steps(prep: dict) -> List[dict]:
    """Uses readiness_scoring to route based on lowest dimension."""
    from readiness_scoring import compute_readiness  # local import to avoid cycles
    scores = compute_readiness(prep)
    overall = scores.get("overall") or 0
    dims = scores.get("dimensions") or {}

    steps: List[dict] = []

    # 1. Always: reinforce Foundation Statement if not written.
    if not (prep.get("reflection") or {}).get("text"):
        steps.append(_step(
            "readiness_write_foundation",
            what="Write your Foundation Statement",
            why="A short, child-centered statement gives your future self "
                "something to lean on when the exchange gets hard.",
            how_long="10 minutes",
            cta_label="Open the reflection space",
            cta_path="/prep/reflection",
            category="reflection",
        ))

    # 2. Pick the weakest dimension → offer a matching next surface.
    weakest = None
    for key, d in dims.items():
        if not d or d.get("score") is None:
            continue
        if weakest is None or d["score"] < weakest[1]:
            weakest = (key, d["score"])

    weak_map = {
        "communication": _step(
            "readiness_biff_practice",
            what="Practice a BIFF-style reply with the AI Coach",
            why="Your Communication score is the lowest dimension right now. "
                "Even one drafted reply changes the pattern.",
            how_long="5 minutes",
            cta_label="Open the AI Coach",
            cta_path="/coach",
            category="preparation",
        ),
        "trust": _step(
            "readiness_alignment",
            what="Draft a short Alignment Statement",
            why="Trust dips when parents can't name what they've already agreed on. "
                "Naming it — even one line — resets the frame.",
            how_long="8 minutes",
            cta_label="Open the Alignment tab",
            cta_path="/summary?tab=agreement",
            category="preparation",
        ),
        "child_alignment": _step(
            "readiness_child_goals",
            what="Revisit your child-centered goals",
            why="Coming back to what your child actually needs — separate from "
                "the conflict — brings this score back up.",
            how_long="8 minutes",
            cta_label="Open Child Goals",
            cta_path="/prep/child-goals",
            category="reflection",
        ),
        "conflict": _step(
            "readiness_safety_review",
            what="Review the Family Violence & Communication Safety pathway",
            why="A low Conflict-Managed score doesn't mean you're doing anything "
                "wrong — it means the pattern is worth surfacing with a coach.",
            how_long="6 minutes",
            cta_label="Open the Safety pathway",
            cta_path="/safety",
            category="safety",
        ),
    }
    if weakest and weakest[0] in weak_map:
        steps.append(weak_map[weakest[0]])

    # 3. Course by overall score.
    if overall >= 75:
        steps.append(_step(
            "readiness_generate_summary",
            what="Generate your Mediation Summary",
            why="You're in the Prepared band. Turn that momentum into a "
                "court-quality document for your mediator.",
            how_long="4 minutes",
            cta_label="Open the Summary",
            cta_path="/summary",
            category="preparation",
        ))
    elif overall >= 55:
        steps.append(_step(
            "readiness_growth_check",
            what="Compare this session against your last one",
            why="You're in the Moderately Ready band — growth tracking will "
                "show which dimensions are moving.",
            how_long="3 minutes",
            cta_label="Open My Plan",
            cta_path="/my-plan#growth",
            category="review",
        ))
    else:
        steps.append(_step(
            "readiness_coach_check_in",
            what="Book a 5-minute check-in with the AI Coach",
            why="A low Readiness score doesn't mean you shouldn't mediate — it "
                "means one more prep step matters before you do.",
            how_long="5 minutes",
            cta_label="Open the AI Coach",
            cta_path="/coach",
            category="preparation",
        ))
    return steps[:3]


def _comm_steps(prep: dict) -> List[dict]:
    comm = prep.get("comm_style") or {}
    steps: List[dict] = []
    steps.append(_step(
        "comm_biff_reply",
        what="Draft a BIFF reply for a real exchange",
        why="You just named the pattern. The next step is trying it in a "
            "message that actually matters this week.",
        how_long="5 minutes",
        cta_label="Open the AI Coach",
        cta_path="/coach",
        category="preparation",
    ))
    if not comm.get("triggers"):
        steps.append(_step(
            "comm_triggers",
            what="Name your top three triggers",
            why="Naming them here gives your coach the specifics needed to "
                "help you catch the pattern before it fires.",
            how_long="6 minutes",
            cta_label="Return to Communication",
            cta_path="/prep/communication",
            category="reflection",
        ))
    steps.append(_step(
        "comm_gmail_reply",
        what="Draft your next co-parenting email with AI",
        why="The Gmail integration turns 'I don't know how to respond' into "
            "a Brief-Informative-Friendly-Firm reply.",
        how_long="4 minutes",
        cta_label="Open Gmail",
        cta_path="/gmail",
        category="preparation",
    ))
    return steps[:3]


def _safety_steps(prep: dict) -> List[dict]:
    """Safety pathway — routed by the safety assessment level (L1–L4)."""
    sa = prep.get("safety_assessment") or {}
    level = (sa.get("level") or sa.get("risk_level") or "L1").upper()
    steps: List[dict] = []

    if level in ("L3", "L4"):
        steps.append(_step(
            "safety_hotline",
            what="Call the National DV Hotline (1-800-799-7233)",
            why="Your responses indicate coercive control or fear-of-harm "
                "signals. An advocate can help you plan the next step safely.",
            how_long="15 minutes",
            cta_label="Open Safety resources",
            cta_path="/safety",
            category="safety",
        ))
        steps.append(_step(
            "safety_parallel",
            what="Move to Parallel Parenting communication",
            why="Direct exchanges are unlikely to be safe right now. A "
                "structured, third-party channel protects your child from "
                "the conflict.",
            how_long="10 minutes",
            cta_label="Open the Parallel Parenting toolkit",
            cta_path="/safety#parallel",
            category="safety",
        ))
        steps.append(_step(
            "safety_share_report",
            what="Share your Safety Assessment with an advocate or attorney",
            why="A written record helps if you need to make a legal decision "
                "about mediation itself.",
            how_long="3 minutes",
            cta_label="Download / share the report",
            cta_path="/safety-assessment/report",
            category="safety",
        ))
    else:
        steps.append(_step(
            "safety_biff_practice",
            what="Practice a BIFF reply for the next hard message",
            why="Your Safety level is currently low-concern. Skill-building on "
                "communication is the highest-value next step.",
            how_long="5 minutes",
            cta_label="Open the AI Coach",
            cta_path="/coach",
            category="preparation",
        ))
        steps.append(_step(
            "safety_review_plan",
            what="Review your personal safety plan",
            why="Even a low-concern score benefits from an explicit written "
                "plan — 'what would I do if this changed?'",
            how_long="8 minutes",
            cta_label="Open Safety resources",
            cta_path="/safety",
            category="safety",
        ))
        steps.append(_step(
            "safety_retake_reminder",
            what="Retake this assessment before your next mediation",
            why="Dynamics can shift. A pre-mediation re-check gives your "
                "mediator the current safety picture.",
            how_long="10 minutes",
            cta_label="Retake later",
            cta_path="/safety-assessment",
            category="safety",
        ))
    return steps[:3]


def _sn_steps(db_scores: dict) -> List[dict]:
    """Special Needs — routed by the weakest coordination dimension."""
    dims = db_scores.get("dimensions") or {}
    structure = db_scores.get("structure") or {}
    steps: List[dict] = []

    # 1. Always encourage generating/refreshing the care plan.
    steps.append(_step(
        "sn_generate_plan",
        what="Generate the 6-part care plan for your child",
        why="Your seven coordination scores are ready. The next step is a "
            "single downloadable document you can hand to your pediatrician "
            "or mediator.",
        how_long="2 minutes",
        cta_label="Open Reports",
        cta_path="/neurodivergent/reports",
        category="review",
    ))

    # 2. Weakest coordination dimension → matching next surface.
    weakest = None
    for key, d in dims.items():
        if not d or d.get("no_signal") or d.get("score") is None:
            continue
        if weakest is None or d["score"] < weakest[1]:
            weakest = (key, d["score"])

    dim_map = {
        "information_sharing": ("Open shared records channel with the other parent",
            "Info-sharing was your lowest coordination score. A single shared "
            "email thread (or app) resolves most of these gaps."),
        "consistency": ("Align three consistency items with the other parent",
            "Pick the three items from your Consistency module that BOTH "
            "parents flagged as 'child needs consistent' and align on the "
            "specific routine this week."),
        "follow_through": ("Assign follow-through owners in your Action Plan",
            "Follow-through dips when nobody explicitly owns the task. Assign "
            "one responsible parent per row in the Action Plan worksheet."),
        "understanding": ("Revisit the Child Profile section with the other parent",
            "The lowest score is on understanding your child. The Child "
            "Profile section is short — share it and align on it."),
        "professional_collaboration": ("Update professional contact info in one place",
            "Doctors, therapists, and schools need to reach both parents. "
            "A single shared contact card removes this gap."),
        "decision_making": ("Set a decision-making rhythm with a deadline",
            "Decisions stall when neither parent has a channel and a deadline. "
            "Agree on one now."),
        "transition_stability": ("Write a handover checklist for your child",
            "A one-page checklist (meds, comfort item, recovery-time note) "
            "removes 80% of transition friction."),
    }
    if weakest:
        key = weakest[0]
        # DIMENSION_LABELS uses snake_case matching keys → map keys align.
        if key in dim_map:
            label, why = dim_map[key]
            steps.append(_step(
                f"sn_dim_{key}",
                what=label,
                why=why,
                how_long="15 minutes",
                cta_label="Open the care plan",
                cta_path="/neurodivergent/reports",
                category="preparation",
            ))

    # 3. Structure-specific step.
    sid = structure.get("id")
    if sid == "parallel":
        steps.append(_step(
            "sn_structure_parallel",
            what="Move day-to-day coordination to a structured channel",
            why="Your coordination pattern points to Parallel Coordination — "
                "a low-contact, structured channel with clear owners protects "
                "your child from the coordination gap.",
            how_long="20 minutes",
            cta_label="Open Safety & Parallel toolkit",
            cta_path="/safety",
            category="safety",
        ))
    elif sid == "structured":
        steps.append(_step(
            "sn_structure_structured",
            what="Turn one action row into a written 30-day agreement",
            why="Structured Coordination works when the plan is written down. "
                "Start with the highest-priority row.",
            how_long="10 minutes",
            cta_label="Open the Alignment Statement",
            cta_path="/summary?tab=agreement",
            category="preparation",
        ))
    else:
        steps.append(_step(
            "sn_structure_cooperative",
            what="Schedule a monthly coordination check-in",
            why="Cooperative Coordination stays cooperative when there's a "
                "predictable rhythm. Even 15 minutes monthly holds it.",
            how_long="5 minutes",
            cta_label="Open your calendar",
            cta_path="/my-plan",
            category="review",
        ))
    return steps[:3]


# ---------------------------------------------------------------------------
# Deterministic step-builders for the new 10-principle Special Needs (v3)
# assessment and the new 10-section Co-Parenting assessment.
#
# Both accept the shared scoring shape from cp_scoring / sn_v3_scoring:
#   { sections: [{id, number, name, rating, avg, ...}],
#     overall_rating, priority_focus: [section_id, ...],
#     show_communication_toolkit: bool }
# ---------------------------------------------------------------------------
def _priority_step_from(scores: dict, section_lookup: dict, *, cta_label: str, cta_path: str) -> Optional[dict]:
    """Convert the top priority-focus id into a 'first step here' recommendation."""
    priority_ids = scores.get("priority_focus") or []
    if not priority_ids:
        return None
    sid = priority_ids[0]
    sec = section_lookup.get(sid)
    if not sec:
        return None
    return _step(
        f"pf_{sid}",
        what=f"Start with {sec['name']}",
        why=f"This scored lowest in your assessment ({sec.get('rating') or 'Fair'}). "
            "Even a single change here will move the needle further than working on stronger areas.",
        how_long="15 minutes",
        cta_label=cta_label,
        cta_path=cta_path,
        category="preparation",
    )


def _sn_v3_steps(scores: dict) -> List[dict]:
    """Special Needs v3 (10-principle) — 3 deterministic steps."""
    from sn_v3_questions import SECTIONS as SN_SECTIONS
    lookup = {s["id"]: s for s in SN_SECTIONS}

    steps: List[dict] = []
    steps.append(_step(
        "snv3_open_report",
        what="Open your personalised Special Needs report",
        why="You just finished a 10-principle self-assessment. Your report has "
            "strengths, priority focus areas, and next steps ready to share with "
            "your co-parent, mediator, or Parenting Facilitator.",
        how_long="3 minutes",
        cta_label="Open my report",
        cta_path="/special-needs-v3",
        category="review",
    ))

    pf = _priority_step_from(scores, lookup, cta_label="Open my report", cta_path="/special-needs-v3")
    if pf:
        steps.append(pf)

    if scores.get("show_communication_toolkit"):
        steps.append(_step(
            "snv3_toolkit",
            what="Use the Communication Toolkit for the next 2 weeks",
            why="Principle 3 (Maintain Open, Child-Focused Communication) needs "
                "attention. BIFF messages + a shared parenting app will remove most "
                "of the friction before your next mediation session.",
            how_long="10 minutes",
            cta_label="Open my plan",
            cta_path="/my-plan",
            category="preparation",
        ))
    else:
        steps.append(_step(
            "snv3_share",
            what="Share the report with your co-parent or Parenting Facilitator",
            why="A shared link keeps everyone aligned on the same 10-principle "
                "framework — no diagnostic language, just practical coordination.",
            how_long="2 minutes",
            cta_label="Open my report",
            cta_path="/special-needs-v3",
            category="preparation",
        ))
    return steps[:3]


def _cp_steps(scores: dict) -> List[dict]:
    """Co-Parenting (10-section) — 3 deterministic steps."""
    from coparenting_questions import SECTIONS as CP_SECTIONS
    lookup = {s["id"]: s for s in CP_SECTIONS}

    steps: List[dict] = []
    steps.append(_step(
        "cp_open_report",
        what="Open your personalised Co-Parenting report",
        why="You just finished the 10-section self-assessment. Your report is "
            "ready with strengths, priority focus areas, and next steps.",
        how_long="3 minutes",
        cta_label="Open my report",
        cta_path="/dashboard",
        category="review",
    ))

    pf = _priority_step_from(scores, lookup, cta_label="Open my report", cta_path="/dashboard")
    if pf:
        steps.append(pf)

    if scores.get("show_communication_toolkit"):
        steps.append(_step(
            "cp_toolkit",
            what="Adopt the Communication Toolkit for the next 2 weeks",
            why="Communication & Information Sharing (Section 1) is currently "
                "your priority area. BIFF messages + a shared parenting app "
                "resolve most communication gaps.",
            how_long="10 minutes",
            cta_label="Open my plan",
            cta_path="/my-plan",
            category="preparation",
        ))
    else:
        steps.append(_step(
            "cp_share",
            what="Share the report with your co-parent or mediator",
            why="A signed share link keeps everyone aligned on the same "
                "practical framework before your next mediation session.",
            how_long="2 minutes",
            cta_label="Open my dashboard",
            cta_path="/dashboard",
            category="preparation",
        ))
    return steps[:3]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
async def _load_prep(db, user_id: str) -> dict:
    return await db.prep_data.find_one({"user_id": user_id}, {"_id": 0}) or {}


async def _generate(db, assessment: str, current) -> List[dict]:
    if assessment == "readiness":
        prep = await _load_prep(db, current.user_id)
        return _readiness_steps(prep)
    if assessment == "comm_style":
        prep = await _load_prep(db, current.user_id)
        return _comm_steps(prep)
    if assessment == "safety":
        prep = await _load_prep(db, current.user_id)
        sa = await db.safety_assessments.find_one(
            {"user_id": current.user_id}, {"_id": 0}, sort=[("created_at", -1)]
        )
        if sa:
            prep = {**prep, "safety_assessment": sa}
        return _safety_steps(prep)
    if assessment == "special_needs":
        # Prefer new SN v3 (10-principle); fallback to legacy nd_prep so existing
        # users' next-steps keep working.
        v3 = await db.sn_v3_assessments.find_one(
            {"user_id": current.user_id}, {"_id": 0}, sort=[("updated_at", -1)]
        )
        if v3 and (v3.get("scores") or v3.get("answers")):
            from sn_v3_scoring import compute_scores as sn_v3_compute
            scores = v3.get("scores") or sn_v3_compute(v3.get("answers") or {})
            return _sn_v3_steps(scores)
        import special_needs_scoring as sn_scoring
        nd = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0}) or {}
        answers = nd.get("answers_v2") or {}
        scores = sn_scoring.compute_scores(answers)
        return _sn_steps(scores)
    if assessment == "coparenting":
        cp = await db.cp_assessments.find_one(
            {"user_id": current.user_id}, {"_id": 0}, sort=[("updated_at", -1)]
        )
        if not cp or not (cp.get("answers") or {}):
            raise HTTPException(status_code=404, detail="No Co-Parenting assessment on file yet.")
        from coparenting_scoring import compute_scores as cp_compute
        scores = cp.get("scores") or cp_compute(cp.get("answers") or {})
        return _cp_steps(scores)
    raise HTTPException(status_code=400, detail=f"Unknown assessment: {assessment}")


class ActionBody(BaseModel):
    action: str = Field(..., pattern="^(done|dismiss|undo)$")


@router.get("/{assessment}")
async def get_next_steps(
    assessment: str,
    request: Request,
    current=Depends(get_current_user),
):
    if assessment not in ASSESSMENTS:
        raise HTTPException(status_code=404, detail="Unknown assessment")
    db = request.app.state.db
    doc = await db.next_steps.find_one(
        {"user_id": current.user_id, "assessment": assessment}, {"_id": 0}
    )
    if not doc:
        steps = await _generate(db, assessment, current)
        doc = {
            "user_id": current.user_id,
            "assessment": assessment,
            "steps": steps,
            "generated_at": _now_iso(),
        }
        await db.next_steps.replace_one(
            {"user_id": current.user_id, "assessment": assessment}, doc, upsert=True
        )
        doc.pop("_id", None)
    return doc


@router.post("/{assessment}/generate")
async def regenerate_next_steps(
    assessment: str,
    request: Request,
    current=Depends(get_current_user),
):
    if assessment not in ASSESSMENTS:
        raise HTTPException(status_code=404, detail="Unknown assessment")
    db = request.app.state.db
    steps = await _generate(db, assessment, current)
    doc = {
        "user_id": current.user_id,
        "assessment": assessment,
        "steps": steps,
        "generated_at": _now_iso(),
    }
    await db.next_steps.replace_one(
        {"user_id": current.user_id, "assessment": assessment}, doc, upsert=True
    )
    doc.pop("_id", None)
    return doc


@router.post("/{assessment}/{step_id}/action")
async def act_on_step(
    assessment: str,
    step_id: str,
    request: Request,
    body: ActionBody = Body(...),
    current=Depends(get_current_user),
):
    if assessment not in ASSESSMENTS:
        raise HTTPException(status_code=404, detail="Unknown assessment")
    db = request.app.state.db
    doc = await db.next_steps.find_one(
        {"user_id": current.user_id, "assessment": assessment}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="No steps to act on — generate first.")

    steps = doc.get("steps") or []
    hit = False
    for s in steps:
        if s.get("step_id") == step_id:
            hit = True
            if body.action == "done":
                s["done"] = True
                s["dismissed"] = False
            elif body.action == "dismiss":
                s["dismissed"] = True
                s["done"] = False
            else:  # undo
                s["done"] = False
                s["dismissed"] = False
    if not hit:
        raise HTTPException(status_code=404, detail="Step not found")
    doc["steps"] = steps
    doc["updated_at"] = _now_iso()
    await db.next_steps.replace_one(
        {"user_id": current.user_id, "assessment": assessment}, doc, upsert=True
    )
    doc.pop("_id", None)
    return doc
