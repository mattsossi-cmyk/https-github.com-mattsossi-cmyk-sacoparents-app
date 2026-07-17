"""Neurodivergent Child Pathway — assessment + AI-generated reports.

This is an optional pathway that co-parents can enter from the Dashboard when
their child has additional needs (autism, ADHD, dyslexia, sensory-processing
differences, executive function challenges, etc.). It is:

  * NOT diagnostic — parents describe their child in their own words.
  * NOT medical or legal advice — a preparation tool only.
  * Neurodivergent-friendly by design — one question per screen, plain
    language, save & resume, no forced audio.

Produces three AI-synthesised reports:
  1. Child Needs & Strengths Summary
  2. Two-Home Support & Transition Plan
  3. Neurodivergent Child Mediation Statement

Data model:
  Collection `nd_prep` — one document per user with the raw answers.
  Collection `nd_reports` — one document per (user, report_type, generation).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import get_current_user
import ai_service


router = APIRouter(prefix="/neurodivergent", tags=["neurodivergent"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Question catalogue ----------------------------------------------------

# Each question has: id, section, prompt, help (optional), type, and — for
# multi-select questions — an options list. The frontend renders one at a
# time. Adding/removing questions here is enough; the frontend consumes this
# catalogue via /api/neurodivergent/questions.
QUESTIONS: List[Dict[str, Any]] = [
    # About your child
    {
        "id": "child_name",
        "section": "About your child",
        "prompt": "What name (or nickname) should we use for your child in this space?",
        "help": "This stays private to your account.",
        "type": "short_text",
        "required": True,
    },
    {
        "id": "child_age",
        "section": "About your child",
        "prompt": "How old is your child?",
        "type": "short_text",
    },
    {
        "id": "child_words",
        "section": "About your child",
        "prompt": "In your own words, how would you describe your child's needs?",
        "help": "Use the language your family uses. You do NOT need a diagnosis to fill this out — 'autism', 'ADHD', 'sensory-sensitive', 'anxious learner', 'sensitive kid' are all fine.",
        "type": "long_text",
    },
    {
        "id": "child_strengths",
        "section": "About your child",
        "prompt": "What are three things you love or admire about your child?",
        "help": "We start with strengths on purpose.",
        "type": "long_text",
    },

    # Communication
    {
        "id": "communication_style",
        "section": "How your child communicates",
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
        "id": "helps_feel_heard",
        "section": "How your child communicates",
        "prompt": "What helps your child feel heard when they're upset?",
        "type": "long_text",
    },
    {
        "id": "escalating_words",
        "section": "How your child communicates",
        "prompt": "Which words or tones tend to escalate things?",
        "help": "Naming these gently helps you and your co-parent avoid them.",
        "type": "long_text",
    },

    # Sensory
    {
        "id": "sensory_sensitivities",
        "section": "Sensory profile",
        "prompt": "What sensory things overwhelm your child most?",
        "help": "Sounds, lights, textures, foods, smells, crowds…",
        "type": "long_text",
    },
    {
        "id": "sensory_seeking",
        "section": "Sensory profile",
        "prompt": "What sensory input does your child seek out or find calming?",
        "help": "Weighted blanket, tight hugs, spinning, running, humming, chewy foods…",
        "type": "long_text",
    },
    {
        "id": "comfort_objects",
        "section": "Sensory profile",
        "prompt": "Are there comfort objects that should travel with your child between homes?",
        "type": "long_text",
    },

    # Regulation
    {
        "id": "early_signs",
        "section": "Regulation & triggers",
        "prompt": "What are the earliest signs your child is becoming overwhelmed?",
        "help": "Before a meltdown, what do you notice?",
        "type": "long_text",
    },
    {
        "id": "known_triggers",
        "section": "Regulation & triggers",
        "prompt": "What situations reliably trigger dysregulation?",
        "type": "long_text",
    },
    {
        "id": "what_helps_regulate",
        "section": "Regulation & triggers",
        "prompt": "What actually helps your child regulate when they're overwhelmed?",
        "type": "long_text",
    },
    {
        "id": "what_makes_worse",
        "section": "Regulation & triggers",
        "prompt": "What responses tend to make things WORSE (even if well-intentioned)?",
        "help": "Naming these together protects your child from unhelpful patterns.",
        "type": "long_text",
    },

    # Routines & transitions
    {
        "id": "consistent_routines",
        "section": "Routines & two-home consistency",
        "prompt": "Which routines matter most to keep consistent between homes?",
        "type": "multi_select",
        "options": [
            "Bedtime routine",
            "Morning routine",
            "Homework expectations",
            "Screen time rules",
            "Meals & snacks",
            "Medication administration",
            "Visual schedule / calendar",
            "Wind-down before sleep",
            "Weekend/holiday rhythms",
        ],
    },
    {
        "id": "transition_style",
        "section": "Routines & two-home consistency",
        "prompt": "How does your child respond to transitions between homes today?",
        "type": "long_text",
    },
    {
        "id": "transition_advance_notice",
        "section": "Routines & two-home consistency",
        "prompt": "How much advance notice does your child need before a change?",
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

    # School & providers
    {
        "id": "school_supports",
        "section": "School, providers & medication",
        "prompt": "Does your child have an IEP, 504, or other school accommodations? What are they?",
        "help": "It's fine to write 'no formal plan yet' — just tell us what supports currently exist.",
        "type": "long_text",
    },
    {
        "id": "providers",
        "section": "School, providers & medication",
        "prompt": "Which therapists, doctors, or specialists are involved?",
        "help": "First names or roles are fine — you don't need to list contact details here.",
        "type": "long_text",
    },
    {
        "id": "medication_schedule",
        "section": "School, providers & medication",
        "prompt": "Are there medications or treatment schedules that must stay consistent between homes?",
        "help": "This information is sensitive. It stays private to your account unless you explicitly share it.",
        "type": "long_text",
    },

    # Wrap up
    {
        "id": "wish_coparent_knew",
        "section": "One thing to say",
        "prompt": "What is one thing you wish your co-parent truly understood about your child?",
        "help": "This becomes the heart of your Mediation Statement.",
        "type": "long_text",
    },
]

REPORT_TYPES = ["needs_summary", "two_home_plan", "mediation_statement"]

REPORT_TITLES = {
    "needs_summary": "Child Needs & Strengths Summary",
    "two_home_plan": "Two-Home Support & Transition Plan",
    "mediation_statement": "Neurodivergent Child Mediation Statement",
}


# ---- Pydantic models -------------------------------------------------------

class AnswerPayload(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=100)
    value: Any = None


class BulkAnswersPayload(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)


# ---- Endpoints -------------------------------------------------------------

@router.get("/questions")
async def list_questions(current=Depends(get_current_user)):
    """Return the ordered question catalogue for the frontend wizard."""
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
    """Autosave a single answer as the parent moves through the wizard."""
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
    """Flag the assessment as complete once the user submits."""
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
    """Generate all three reports from the current answers. Overwrites previous."""
    doc = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc or not doc.get("answers"):
        raise HTTPException(
            status_code=400,
            detail="Please answer some questions before generating reports.",
        )

    answers = doc.get("answers") or {}

    # Generate all three reports in parallel — sequential runs ~14s each and
    # trip the ingress 502 timeout at ~40s. Parallel cuts wall time to ~14s.
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
    # Return in canonical order
    order = {t: i for i, t in enumerate(REPORT_TYPES)}
    reports.sort(key=lambda r: order.get(r.get("report_type"), 99))
    return {"reports": reports}
