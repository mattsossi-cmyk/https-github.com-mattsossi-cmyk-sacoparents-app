"""Special Needs Assessment — v2, child-centered coordination rebuild.

The v2 assessment moves from a single "co-parent quality" number to
seven coordination scores plus a per-domain rollup. See
`special_needs_questions.py` for the question catalogue and
`special_needs_scoring.py` for the deterministic scorer.

Legacy `nd_prep` documents (v1 question ids) are still readable but
never mixed with v2 answers — v2 uses `answers_v2` on the same doc so
we don't fragment collections while migrating in-flight parents.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import get_current_user
import ai_service
import special_needs_questions as sn_q
import special_needs_scoring as sn_scoring
import sn_pathway
import report_visibility


router = APIRouter(prefix="/neurodivergent", tags=["special-needs"])


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# The v1 catalogue is retained below for any lingering v1 report generator
# call sites — it will be removed once the frontend fully cuts over.


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


class BulkAnswerPayload(BaseModel):
    # Used by the wizard to save multiple items in one call (e.g. when the
    # user completes an 8-domain section and moves on).
    answers: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
#  v2 endpoints (child-centered coordination assessment)
# ============================================================================

@router.get("/schema")
async def get_schema(current=Depends(get_current_user)):
    """Full v2 assessment structure (sections, items, scales, domains)."""
    return sn_q.get_schema()


@router.get("/questions")
async def list_questions(current=Depends(get_current_user)):
    """Legacy v1 shape kept only to avoid a hard 404 on stale clients."""
    return {"questions": []}


@router.get("/prep")
async def get_prep(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc:
        return {"user_id": current.user_id, "answers": {}, "completed": False, "version": 2}
    # The wizard writes to `answers_v2`. Return that as `answers` so the
    # frontend has one place to look; legacy `answers` (v1) is left alone
    # in-place for archival.
    doc.setdefault("answers", doc.get("answers_v2") or {})
    doc["version"] = 2 if doc.get("answers_v2") is not None else 1
    return doc


@router.post("/answer")
async def save_answer(
    payload: AnswerPayload,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    valid_ids = set(sn_q.all_question_ids())
    if payload.question_id not in valid_ids:
        raise HTTPException(status_code=400, detail="Unknown question id")
    await db.nd_prep.update_one(
        {"user_id": current.user_id},
        {
            "$set": {
                f"answers_v2.{payload.question_id}": payload.value,
                "updated_at": _now_iso(),
            },
            "$setOnInsert": {"user_id": current.user_id, "created_at": _now_iso()},
        },
        upsert=True,
    )
    return {"ok": True}


@router.post("/answers/bulk")
async def save_answers_bulk(
    payload: BulkAnswerPayload,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    valid_ids = set(sn_q.all_question_ids())
    unknown = [k for k in payload.answers if k not in valid_ids]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown question ids: {unknown[:5]}")
    update: Dict[str, Any] = {"updated_at": _now_iso()}
    for k, v in payload.answers.items():
        update[f"answers_v2.{k}"] = v
    await db.nd_prep.update_one(
        {"user_id": current.user_id},
        {"$set": update, "$setOnInsert": {"user_id": current.user_id, "created_at": _now_iso()}},
        upsert=True,
    )
    return {"ok": True, "saved": len(payload.answers)}


@router.get("/scores")
async def get_scores(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0}) or {}
    answers = doc.get("answers_v2") or {}
    scores = sn_scoring.compute_scores(answers)
    scores["pathway"] = sn_pathway.build_pathway(answers, dimensions=scores.get("dimensions"))
    return scores


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


# ============================================================================
#  v2 report — generate / read / PDF / share
# ============================================================================
import uuid  # noqa: E402
from io import BytesIO  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from auth import create_share_token, decode_share_token  # noqa: E402
import sn_report_pdf  # noqa: E402


def _extract_profile(answers: Dict[str, Any]) -> Dict[str, Any]:
    keys = [q["id"] for q in sn_q.CHILD_PROFILE]
    return {k: answers.get(k) for k in keys if answers.get(k) is not None}


def _extract_concerns(answers: Dict[str, Any]) -> Dict[str, Any]:
    keys = [q["id"] for q in sn_q.CONCERNS_ITEMS]
    return {k: answers.get(k) for k in keys if answers.get(k) is not None}


@router.post("/report/generate")
async def generate_v2_report(
    request: Request,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate (or regenerate) the 6-part care plan from saved v2 answers."""
    doc = await db.nd_prep.find_one({"user_id": current.user_id}, {"_id": 0}) or {}
    answers = doc.get("answers_v2") or {}
    if not answers:
        raise HTTPException(status_code=400, detail="Please answer some questions before generating the report.")

    scores = sn_scoring.compute_scores(answers)
    pathway = sn_pathway.build_pathway(answers, dimensions=scores.get("dimensions"))
    try:
        report = await ai_service.generate_special_needs_report_v2(
            profile=_extract_profile(answers),
            concerns=_extract_concerns(answers),
            scores=scores,
            disagreement=answers.get("concern_response"),
            parent_name=current.name,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Report generation failed: {e}")

    # Merge Phase D pathway output into the report payload so PDF/HTML/share
    # renderers can access it without re-running the engine.
    if isinstance(report, dict):
        report["safeguards_pathway"] = pathway

    report_id = f"sn_{uuid.uuid4().hex[:12]}"
    child_name = (answers.get("child_name") or "").strip() or "your child"
    doc_out = {
        "report_id": report_id,
        "user_id": current.user_id,
        "child_name": child_name,
        "generated_at": _now_iso(),
        "scores": scores,
        "pathway": pathway,
        "report": report,
    }
    # Store as the parent's current v2 report — replace-on-insert keeps
    # exactly one live report per user.
    await db.sn_v2_reports.replace_one(
        {"user_id": current.user_id}, doc_out, upsert=True
    )
    doc_out.pop("_id", None)
    return doc_out


@router.get("/report")
async def get_v2_report(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.sn_v2_reports.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc:
        return {"report": None}
    return doc


@router.get("/report/pdf")
async def download_v2_report_pdf(
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    excluded: Optional[str] = None,
):
    doc = await db.sn_v2_reports.find_one({"user_id": current.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Generate the report first.")
    # Resolve visibility: per-request query wins, else stored preference on doc.
    if excluded is not None:
        raw = [x for x in excluded.split(",") if x]
    else:
        raw = list(((doc.get("visibility") or {}).get("excluded") or []))
    ex_list = report_visibility.clean_excluded("sn_report", raw)
    pdf_bytes = sn_report_pdf.build_special_needs_pdf(
        user_name=current.name or "",
        child_name=doc.get("child_name") or "",
        report=doc.get("report") or {},
        excluded_sections=ex_list,
    )
    safe_child = "".join(c if c.isalnum() else "_" for c in (doc.get("child_name") or "child")).strip("_")
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="SN_Care_Plan_{safe_child}.pdf"'},
    )


class SNVisibilityBody(BaseModel):
    excluded: List[str] = Field(default_factory=list)


@router.patch("/report/visibility")
async def update_sn_visibility(
    body: SNVisibilityBody,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Persist the parent's section-visibility preference for their current
    Special Needs report. Used to prefill the visibility panel next time and
    to seed subsequent PDF/share generations that don't override explicitly."""
    ex = report_visibility.clean_excluded("sn_report", body.excluded)
    result = await db.sn_v2_reports.update_one(
        {"user_id": current.user_id},
        {"$set": {"visibility": {"excluded": ex, "updated_at": _now_iso()}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No report to update. Generate one first.")
    return {"excluded": ex}


class SNShareBody(BaseModel):
    excluded: Optional[List[str]] = None


@router.post("/report/{report_id}/share-link")
async def create_v2_report_share_link(
    report_id: str,
    current=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    body: Optional[SNShareBody] = None,
):
    doc = await db.sn_v2_reports.find_one(
        {"report_id": report_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    incoming = (body.excluded if body else None)
    if incoming is None:
        incoming = (doc.get("visibility") or {}).get("excluded") or []
    ex = report_visibility.clean_excluded("sn_report", incoming)
    token = create_share_token("sn_report", report_id, current.user_id, excluded_sections=ex)
    return {"token": token, "path": f"/api/neurodivergent/report/shared/{token}", "excluded": ex}


@router.get("/report/shared/{token}")
async def shared_v2_report(
    token: str,
    request: Request,
    format: str = "pdf",
):
    """Public read-only route. `?format=json` returns the report JSON so a
    frontend page can render the HTML view; default is a PDF download."""
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "sn_report":
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db = request.app.state.db
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="This link is no longer valid.")
    doc = await db.sn_v2_reports.find_one(
        {"report_id": payload["doc_id"], "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    ex_list = report_visibility.clean_excluded("sn_report", payload.get("ex") or [])

    if format == "json":
        filtered = report_visibility.filter_sn_report(doc.get("report") or {}, ex_list)
        return {
            "report_id": doc.get("report_id"),
            "child_name": doc.get("child_name"),
            "generated_at": doc.get("generated_at"),
            "scores": doc.get("scores"),
            "report": filtered,
            "excluded_sections": ex_list,
            "shared_by": user.get("name") or "A co-parent",
        }

    pdf_bytes = sn_report_pdf.build_special_needs_pdf(
        user_name=user.get("name") or "",
        child_name=doc.get("child_name") or "",
        report=doc.get("report") or {},
        excluded_sections=ex_list,
    )
    safe = "".join(c if c.isalnum() else "_" for c in (doc.get("child_name") or "child")).strip("_")
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="SN_Care_Plan_{safe}.pdf"'},
    )
