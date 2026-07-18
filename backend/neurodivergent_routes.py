"""Special Needs Assessment — 6-pillar, evidence-informed pathway.

This assessment supports co-parents whose child has ANY of the following
(alone or in combination) — never diagnostic, always parent-led:

  * Neurodivergence (autism, ADHD, dyslexia, sensory, executive function,
    twice-exceptional / gifted)
  * Developmental disabilities (Down Syndrome, intellectual disability,
    cerebral palsy, global delay, genetic conditions)
  * Chronic medical conditions (diabetes, epilepsy, heart conditions,
    feeding disorders, cancer survivorship, etc.)
  * Mental health (anxiety, depression, OCD, PTSD, bipolar, eating disorders)
  * Behavioural challenges (aggression, elopement, self-injury, school refusal)
  * Trauma history (foster care, abuse, DV exposure, community violence, grief)
  * Attachment / regulation needs (any age)

Organised as six practical pillars, drawing on:
  Neurodiversity · Developmental Disability · Chronic Medical · Mental Health ·
  Behavioural Support · Trauma-Informed Care · Attachment · Executive Function ·
  Family Systems · Collaborative & Proactive Solutions (Ross Greene) ·
  Positive Behaviour Support · WHO Quality-of-Life Framework.

Endpoints unchanged from the previous version — this file just replaces the
QUESTIONS catalogue and the report prompt language.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import get_current_user
import ai_service


router = APIRouter(prefix="/neurodivergent", tags=["special-needs"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
#  Question catalogue — six pillars
# ============================================================================

QUESTIONS: List[Dict[str, Any]] = [
    # ---- Pillar 1: Understanding My Child ---------------------------------
    {
        "id": "child_name",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "What name (or nickname) should we use for your child in this space?",
        "help": "This stays private to your account.",
        "type": "short_text",
        "required": True,
    },
    {
        "id": "child_age",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "How old is your child?",
        "type": "short_text",
    },
    {
        "id": "child_words",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "In your own words, how would you describe your child's needs?",
        "help": "Use the language your family uses. Diagnoses are optional — 'autism', 'ADHD', 'anxiety', 'chronic illness', 'sensitive kid', 'strong feelings' are all fine.",
        "type": "long_text",
    },
    {
        "id": "categories",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "Which of these areas apply to your child? (Select all that fit — we build the report around your selections.)",
        "help": "This is a guide, not a label. You can add specifics in the next question.",
        "type": "multi_select",
        "options": [
            "Neurodivergence (autism, ADHD, dyslexia, sensory, executive function)",
            "Developmental disability (Down Syndrome, intellectual disability, CP, genetic condition, global delay)",
            "Chronic medical condition (diabetes, epilepsy, heart, feeding, cancer survivorship, other)",
            "Mental health (anxiety, depression, OCD, PTSD, bipolar, eating disorder)",
            "Behavioural challenges (aggression, elopement, self-injury, school refusal, big-feelings meltdowns)",
            "Trauma history (foster care, abuse, DV exposure, grief, community violence)",
            "Speech / language / hearing / vision",
            "Gifted with intense needs (twice-exceptional / 2e)",
            "Something else — I'll describe it below",
        ],
    },
    {
        "id": "child_strengths",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "What are three things you love or admire about your child?",
        "help": "We start with strengths on purpose. This becomes the opening of your report.",
        "type": "long_text",
    },
    {
        "id": "communication_style",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "How does your child communicate best?",
        "type": "multi_select",
        "options": [
            "Speaking (verbal)",
            "Writing or texting",
            "Gestures, signs, or pointing",
            "AAC device or app",
            "Drawing / visual",
            "Mix — depends on the day",
        ],
    },
    {
        "id": "learning_profile",
        "section": "Pillar 1 · Understanding my child",
        "prompt": "What kind of learner is your child? What environments help them thrive?",
        "help": "Hands-on, visual, one-to-one, quiet spaces, movement breaks, small groups…",
        "type": "long_text",
    },

    # ---- Pillar 2: Daily Care & Routines ----------------------------------
    {
        "id": "medication_schedule",
        "section": "Pillar 2 · Daily care & routines",
        "prompt": "Are there medications, treatments, or therapy schedules that must stay consistent between homes?",
        "help": "This information is sensitive. It stays private to your account unless you explicitly share it.",
        "type": "long_text",
    },
    {
        "id": "medical_coordination",
        "section": "Pillar 2 · Daily care & routines",
        "prompt": "How is medical / therapy coordination handled between the two homes today?",
        "help": "Who books appointments, who takes them, who talks to insurers.",
        "type": "long_text",
    },
    {
        "id": "sleep_routine",
        "section": "Pillar 2 · Daily care & routines",
        "prompt": "What does a healthy sleep routine look like for your child?",
        "type": "long_text",
    },
    {
        "id": "meal_routine",
        "section": "Pillar 2 · Daily care & routines",
        "prompt": "Meals, food sensitivities, feeding equipment or safety needs — anything the other home should know?",
        "type": "long_text",
    },
    {
        "id": "consistent_routines",
        "section": "Pillar 2 · Daily care & routines",
        "prompt": "Which routines matter most to keep consistent between homes?",
        "type": "multi_select",
        "options": [
            "Bedtime routine",
            "Morning routine",
            "Homework expectations",
            "Screen time rules",
            "Meals & snacks",
            "Medication administration",
            "Therapy attendance",
            "Visual schedule / calendar",
            "Wind-down before sleep",
            "Weekend/holiday rhythms",
        ],
    },
    {
        "id": "school_transportation",
        "section": "Pillar 2 · Daily care & routines",
        "prompt": "How is school, therapy, and appointment transportation handled between the two homes?",
        "type": "long_text",
    },

    # ---- Pillar 3: Emotional & Behavioural Supports -----------------------
    {
        "id": "early_signs",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "What are the earliest signs your child is becoming overwhelmed?",
        "help": "Before a meltdown — what do you notice first?",
        "type": "long_text",
    },
    {
        "id": "known_triggers",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "What situations reliably trigger dysregulation, anxiety, or big behaviours?",
        "type": "long_text",
    },
    {
        "id": "what_helps_regulate",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "What actually helps your child regulate when they're struggling?",
        "help": "Weighted blanket, quiet space, snack, movement, silence, familiar person…",
        "type": "long_text",
    },
    {
        "id": "what_makes_worse",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "What responses tend to make things WORSE — even when well-intentioned?",
        "help": "Naming these together protects your child from unhelpful patterns.",
        "type": "long_text",
    },
    {
        "id": "lagging_skills",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "If we ask 'what skill is missing?' rather than 'why won't they behave?' — what would you say?",
        "help": "Inspired by Ross Greene's Collaborative & Proactive Solutions: 'kids do well if they can.'",
        "type": "long_text",
    },
    {
        "id": "safety_plan",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "Does your child have any safety concerns that both homes need to plan for?",
        "help": "Elopement, self-injury, medical emergencies, mental-health crisis triggers, allergen exposure…",
        "type": "long_text",
    },
    {
        "id": "trauma_context",
        "section": "Pillar 3 · Emotional & behavioural supports",
        "prompt": "Are there past experiences that shape how your child feels about safety, predictability, or separation?",
        "help": "You do NOT need to disclose details — a short note is fine. Trauma-informed care is about predictability and calm, not re-telling.",
        "type": "long_text",
    },

    # ---- Pillar 4: Parent Alignment ---------------------------------------
    {
        "id": "shared_goals",
        "section": "Pillar 4 · Parent alignment",
        "prompt": "What shared goals do you and your co-parent already have for your child?",
        "type": "long_text",
    },
    {
        "id": "areas_of_disagreement",
        "section": "Pillar 4 · Parent alignment",
        "prompt": "Where do you and your co-parent see things differently right now?",
        "help": "Neutral is fine. This becomes 'areas needing discussion' — never blame.",
        "type": "long_text",
    },
    {
        "id": "decision_making",
        "section": "Pillar 4 · Parent alignment",
        "prompt": "How are big decisions made today (school, medical, therapy)?",
        "type": "long_text",
    },
    {
        "id": "communication_between_homes",
        "section": "Pillar 4 · Parent alignment",
        "prompt": "How do the two homes communicate about your child right now?",
        "help": "Text, email, hand-off notebook, shared app, mediator…",
        "type": "long_text",
    },
    {
        "id": "transition_advance_notice",
        "section": "Pillar 4 · Parent alignment",
        "prompt": "How much advance notice does your child need before a change or transition?",
        "type": "single_select",
        "options": [
            "A few hours is fine",
            "Same day",
            "24 hours",
            "Several days",
            "A week or more",
            "Depends on the change",
        ],
    },

    # ---- Pillar 5: Advocacy & Community -----------------------------------
    {
        "id": "school_supports",
        "section": "Pillar 5 · Advocacy & community",
        "prompt": "Does your child have an IEP, 504, or other school accommodations? What are they?",
        "help": "It's fine to write 'no formal plan yet' — just describe what supports currently exist.",
        "type": "long_text",
    },
    {
        "id": "providers",
        "section": "Pillar 5 · Advocacy & community",
        "prompt": "Which therapists, doctors, or specialists are involved?",
        "help": "First names or roles are fine — you don't need to list contact details here.",
        "type": "long_text",
    },
    {
        "id": "insurance_and_finance",
        "section": "Pillar 5 · Advocacy & community",
        "prompt": "How are insurance and medical costs handled between the two homes?",
        "type": "long_text",
    },
    {
        "id": "community_supports",
        "section": "Pillar 5 · Advocacy & community",
        "prompt": "Who are the trusted people in your child's community (family, teachers, coaches, faith community, therapists)?",
        "type": "long_text",
    },

    # ---- Pillar 6: Long-term Wellbeing & Vision ---------------------------
    {
        "id": "quality_of_life",
        "section": "Pillar 6 · Long-term wellbeing & vision",
        "prompt": "When you picture your child thriving in one year, what does it look like?",
        "help": "Based on the WHO Quality of Life framework: physical wellbeing, emotional wellbeing, social connection, learning, recreation, independence, family belonging.",
        "type": "long_text",
    },
    {
        "id": "long_term_hopes",
        "section": "Pillar 6 · Long-term wellbeing & vision",
        "prompt": "What are your long-term hopes for your child's independence, education, and quality of life?",
        "type": "long_text",
    },
    {
        "id": "wish_coparent_knew",
        "section": "Pillar 6 · Long-term wellbeing & vision",
        "prompt": "What is one thing you wish your co-parent truly understood about your child?",
        "help": "This becomes the heart of your Mediation Statement.",
        "type": "long_text",
    },
]

REPORT_TYPES = ["needs_summary", "two_home_plan", "mediation_statement"]

REPORT_TITLES = {
    "needs_summary": "Child Needs & Strengths Summary",
    "two_home_plan": "Two-Home Support & Transition Plan",
    "mediation_statement": "Special Needs Mediation Statement",
}


# ============================================================================
#  API models
# ============================================================================

class AnswerPayload(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=100)
    value: Any = None


# ============================================================================
#  Endpoints
# ============================================================================

@router.get("/questions")
async def list_questions(current=Depends(get_current_user)):
    return {"questions": QUESTIONS}


@router.get("/prep")
async def get_prep(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc:
        return {"user_id": current.user_id, "answers": {}, "completed": False}
    return doc


@router.post("/answer")
async def save_answer(
    payload: AnswerPayload,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    valid_ids = {q["id"] for q in QUESTIONS}
    if payload.question_id not in valid_ids:
        raise HTTPException(status_code=400, detail="Unknown question id")
    await db.nd_prep.update_one(
        {"user_id": current.user_id},
        {
            "$set": {
                f"answers.{payload.question_id}": payload.value,
                "updated_at": _now_iso(),
            },
            "$setOnInsert": {"user_id": current.user_id, "created_at": _now_iso()},
        },
        upsert=True,
    )
    return {"ok": True}


@router.post("/complete")
async def mark_complete(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.nd_prep.update_one(
        {"user_id": current.user_id},
        {"$set": {"completed": True, "completed_at": _now_iso()}},
    )
    return {"ok": True}


@router.post("/reports/generate")
async def generate_reports(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc or not doc.get("answers"):
        raise HTTPException(
            status_code=400,
            detail="Please answer some questions before generating reports.",
        )

    answers = doc.get("answers") or {}
    import asyncio

    async def _one(report_type: str):
        result = await ai_service.generate_nd_report(
            report_type=report_type,
            answers=answers,
            parent_name=current.name,
            questions=QUESTIONS,
        )
        return report_type, result

    try:
        results = await asyncio.gather(
            *(_one(rt) for rt in REPORT_TYPES),
            return_exceptions=True,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Coach could not generate reports: {e}") from e

    generated: List[Dict[str, Any]] = []
    errors: List[str] = []
    for res in results:
        if isinstance(res, Exception):
            errors.append(str(res))
            continue
        report_type, result = res
        report_doc = {
            "user_id": current.user_id,
            "report_type": report_type,
            "title": REPORT_TITLES[report_type],
            "content": result.get("content", ""),
            "highlights": result.get("highlights", []),
            "generated_at": _now_iso(),
        }
        await db.nd_reports.replace_one(
            {"user_id": current.user_id, "report_type": report_type},
            report_doc,
            upsert=True,
        )
        generated.append({k: v for k, v in report_doc.items() if k != "user_id"})

    if not generated:
        raise HTTPException(
            status_code=502,
            detail=f"Coach could not generate any reports: {'; '.join(errors) or 'unknown error'}",
        )
    return {"reports": generated, "errors": errors}


@router.get("/reports")
async def list_reports(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.nd_reports.find({"user_id": current.user_id}, {"_id": 0, "user_id": 0})
    reports = await cursor.to_list(length=10)
    order = {t: i for i, t in enumerate(REPORT_TYPES)}
    reports.sort(key=lambda r: order.get(r.get("report_type"), 99))
    return {"reports": reports}
