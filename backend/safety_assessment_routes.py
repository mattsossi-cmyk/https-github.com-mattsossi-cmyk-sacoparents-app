"""IPV Communication Safety Assessment routes.

Endpoints (mounted at /api/safety-assessment):
  POST   /                       Submit a completed assessment; returns level + recommendations
  GET    /me                     Return the current user's most recent assessment
  GET    /me/history             List up to 20 most recent assessments for this user
  GET    /:assessment_id/pdf     Download branded PDF of an assessment
  POST   /:assessment_id/email   Email the user a PDF + summary
  POST   /problem-solving        Save a Problem-Solving Worksheet entry
  GET    /problem-solving/me     List the user's saved worksheets

Scoring is fully server-side so the recommended pathway can never be tampered with.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db, create_share_token, decode_share_token
from email_service import EmailNotConfigured, EmailSendError, send_mediator_safety_assessment, send_safety_assessment_report
from safety_assessment_pdf import build_safety_assessment_pdf
import report_visibility


router = APIRouter(prefix="/safety-assessment", tags=["safety-assessment"])
logger = logging.getLogger(__name__)


# ============================================================
# Question metadata — kept here so scoring + PDF + UI all agree
# ============================================================
SECTION_1_QUESTIONS = [
    {
        "id": "s1_q1",
        "text": "Threatened to hurt or kill you, the children, themselves, or someone you love?",
        "high_concern": True,
    },
    {
        "id": "s1_q2",
        "text": "Physically hurt you, blocked you from leaving, restrained you, choked or strangled you, or damaged property?",
        "high_concern": True,
    },
    {
        "id": "s1_q3",
        "text": "Used parenting communication to intimidate, harass, monitor, or control you?",
        "high_concern": False,
    },
    {
        "id": "s1_q4",
        "text": "Shown up unexpectedly at your home, work, school, or exchanges — or stalked or followed you?",
        "high_concern": True,
    },
    {
        "id": "s1_q5",
        "text": "Threatened to take the children, withhold them, or use court to punish you?",
        "high_concern": True,
    },
    {
        "id": "s1_q6",
        "text": "Controlled money, transportation, phone access, accounts, passwords, or location tracking?",
        "high_concern": False,
    },
    {
        "id": "s1_q7",
        "text": "Used insults, humiliation, interrogation, or repeated messaging to wear you down?",
        "high_concern": False,
    },
    {
        "id": "s1_q8",
        "text": "Made you afraid to disagree, set boundaries, or say no?",
        "high_concern": False,
    },
    {
        "id": "s1_q9",
        "text": "Involved the children in threats, pressure, spying, or message-carrying?",
        "high_concern": False,
    },
    {
        "id": "s1_q10",
        "text": "Violated a protective order, court order, or agreed safety boundary?",
        "high_concern": True,
    },
    # ---- Lethality-domain items informed by the Danger Assessment (Campbell) ----
    # These are the domains most predictive of severe / fatal outcomes and any
    # single 'yes' should escalate the pathway to safety planning. Wording is
    # softened to reflection-prompt form; framing (not scoring) is ours.
    {
        "id": "s1_q11",
        "text": "Has the physical violence increased in frequency or severity over the last year?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q12",
        "text": "Owns or has access to a gun, or has threatened you with any weapon?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q13",
        "text": "Ever tried to choke or strangle you, or cut off your breathing?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q14",
        "text": "Ever forced you into sexual activity when you did not want to?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q15",
        "text": "Ever threatened or attempted suicide, or said \u201cif I can\u2019t have you no one will\u201d?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q16",
        "text": "Uses alcohol or drugs (including stimulants) daily or in a way that changes their behaviour?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q17",
        "text": "Is intensely jealous, or controls most of your daily activities?",
        "high_concern": True,
        "da_domain": True,
    },
    {
        "id": "s1_q18",
        "text": "Is currently unemployed or was recently fired, and appears despondent or hopeless?",
        "high_concern": True,
        "da_domain": True,
    },
]

SECTION_2_QUESTIONS = [
    {"id": "s2_q1", "text": "Can you respond without fear of retaliation?"},
    {"id": "s2_q2", "text": "Can you say \u201cno\u201d without escalation?"},
    {"id": "s2_q3", "text": "Can communication remain child-focused?"},
    {"id": "s2_q4", "text": "Can written communication occur without harassment?"},
    {"id": "s2_q5", "text": "Can exchanges occur without intimidation?"},
    {"id": "s2_q6", "text": "Can both parents follow limits on time, topic, and tone?"},
    {"id": "s2_q7", "text": "Can problems be discussed without threats?"},
    {"id": "s2_q8", "text": "Would a neutral third party reduce conflict?"},
]


HIGH_CONCERN_IDS = {q["id"] for q in SECTION_1_QUESTIONS if q["high_concern"]}
COERCIVE_IDS = {"s1_q3", "s1_q6", "s1_q7", "s1_q8", "s1_q9"}


PATHWAYS: Dict[int, Dict[str, Any]] = {
    1: {
        "title": "No Direct Communication Recommended",
        "headline": "A safety-focused communication plan is recommended.",
        "tone": "danger",
        "summary": (
            "Your responses suggest that direct co-parenting communication may not be "
            "appropriate at this time. A safety-focused communication plan is recommended. "
            "This may include limited or no direct contact, use of attorneys or court-"
            "approved channels, neutral exchange locations, and safety planning before any "
            "parenting exchange."
        ),
        "use_when": (
            "Use when there is fear, threats, coercive control, stalking, violence, "
            "repeated harassment, protective order violations, or immediate safety concerns."
        ),
        "recommendations": [
            "Communication only through attorneys, court-approved platforms, parenting facilitator, or supervised channel",
            "No phone calls or in-person discussions",
            "Neutral or supervised exchanges",
            "Emergency-only communication protocol",
            "Safety plan before any parenting exchange",
            "Review by attorney, advocate, court professional, or trained family violence provider",
        ],
    },
    2: {
        "title": "Structured Written Communication Only",
        "headline": "Communication should be structured and limited to written, child-focused topics.",
        "tone": "warning",
        "summary": (
            "Your responses suggest that communication should be structured and limited to "
            "written, child-focused topics. Direct calls, emotional discussions, or "
            "unstructured exchanges may increase conflict. A written communication plan can "
            "help reduce escalation and protect the child from being placed in the middle."
        ),
        "use_when": (
            "Use when there is high conflict, intimidation, repeated escalation, or "
            "emotional pressure, but no immediate danger has been identified."
        ),
        "recommendations": [
            "App-based written communication only",
            "BIFF format: brief, informative, focused, firm",
            "One issue per message",
            "Child-related topics only",
            "No emotional history, blame, insults, interrogation, or threats",
            "Response window of 24\u201348 hours unless urgent",
            "Written record maintained",
            "Clear boundaries around tone, timing, and topic",
        ],
    },
    3: {
        "title": "Assisted Problem-Solving",
        "headline": "Assisted communication may be appropriate.",
        "tone": "info",
        "summary": (
            "Your responses suggest that assisted communication may be appropriate. A "
            "structured process can help each parent focus on the child\u2019s needs, "
            "reduce blame, and create practical options for parenting decisions."
        ),
        "use_when": "Use when parents can communicate but need structure, support, or a neutral process.",
        "recommendations": [
            "Use a problem-solving worksheet",
            "Identify the child\u2019s need",
            "Each parent states concerns",
            "Each parent offers options",
            "Compare options by safety, stability, and child impact",
            "Create a written agreement",
            "Consider mediator, parenting facilitator, therapist, or neutral support",
        ],
    },
    4: {
        "title": "Cooperative Co-Parenting Communication",
        "headline": "Cooperative co-parenting communication may be appropriate.",
        "tone": "ok",
        "summary": (
            "Your responses suggest that cooperative co-parenting communication may be "
            "appropriate. Continued use of child-focused communication, shared goals, and "
            "written agreements can help maintain stability for the child."
        ),
        "use_when": "Use when there is low safety risk and both parents can communicate respectfully.",
        "recommendations": [
            "Direct app communication",
            "Shared child-focused goals",
            "Parenting agreements",
            "Mediation preparation",
            "Child-centered planning",
            "Respectful problem-solving",
        ],
    },
}


TEXAS_RESOURCE_BLOCK = (
    "For Texas users, family violence resources include the National Domestic Violence "
    "Hotline: call 800-799-7233, text START to 88788, or chat online through the Hotline "
    "website. Texas Health and Human Services states that trained advocates can provide "
    "crisis intervention, safety planning, education, advocacy, and referrals to shelters "
    "and local resources. If there is immediate danger, call 911."
)


# ============================================================
# Request / response models
# ============================================================
AnswerYNU = str  # "yes" | "no" | "unsure" — validated in scoring


class AssessmentSubmit(BaseModel):
    section_1: Dict[str, AnswerYNU] = Field(default_factory=dict)
    section_2: Dict[str, AnswerYNU] = Field(default_factory=dict)


class MediatorEmailBody(BaseModel):
    mediator_email: str = Field(min_length=3, max_length=254)
    mediator_name: str = ""
    parent_message: str = ""


class ProblemSolvingSubmit(BaseModel):
    parenting_issue: str = ""
    child_need: str = ""
    my_concern: str = ""
    other_parent_concern: str = ""
    safest_pathway: str = ""
    option_a: str = ""
    option_b: str = ""
    option_c: str = ""
    best_option: str = ""
    boundary: str = ""
    next_step: str = ""


# ============================================================
# Scoring
# ============================================================
def _is_yes(v: Any) -> bool:
    return isinstance(v, str) and v.strip().lower() == "yes"


def _is_no(v: Any) -> bool:
    return isinstance(v, str) and v.strip().lower() == "no"


def score_assessment(payload: AssessmentSubmit) -> Dict[str, Any]:
    """Return level (1-4), flags, counts. Pure function — easy to unit-test."""
    s1 = payload.section_1 or {}
    s2 = payload.section_2 or {}

    high_concern_hits = sorted([qid for qid in HIGH_CONCERN_IDS if _is_yes(s1.get(qid))])
    coercive_hits = sorted([qid for qid in COERCIVE_IDS if _is_yes(s1.get(qid))])
    section_1_yes = sum(1 for q in SECTION_1_QUESTIONS if _is_yes(s1.get(q["id"])))
    # Section 2: "no" answers indicate communication is NOT safe/ready.
    # Q8 is inverted in tone ("would a neutral 3rd party reduce conflict?") — a "yes" there
    # is actually a signal that direct communication is harder, so we count it as a concern.
    section_2_concerns = 0
    for q in SECTION_2_QUESTIONS:
        ans = s2.get(q["id"])
        if q["id"] == "s2_q8":
            if _is_yes(ans):
                section_2_concerns += 1
        else:
            if _is_no(ans):
                section_2_concerns += 1

    # ---- Level decision ----
    # Any single yes on a coercive-control question (s1_q3, s1_q6, s1_q7, s1_q8, s1_q9)
    # escalates to Level 2 — structured written communication only.
    if high_concern_hits:
        level = 1
    elif len(coercive_hits) >= 1 or section_1_yes >= 4:
        level = 2
    elif section_2_concerns >= 3:
        level = 3
    else:
        level = 4

    pathway = PATHWAYS[level]
    return {
        "level": level,
        "pathway_title": pathway["title"],
        "pathway_headline": pathway["headline"],
        "pathway_tone": pathway["tone"],
        "pathway_summary": pathway["summary"],
        "recommendations": pathway["recommendations"],
        "high_concern_hits": high_concern_hits,
        "coercive_hits": coercive_hits,
        "section_1_yes_count": section_1_yes,
        "section_2_concern_count": section_2_concerns,
    }


def _question_lookup(question_id: str) -> str:
    for q in SECTION_1_QUESTIONS:
        if q["id"] == question_id:
            return q["text"]
    for q in SECTION_2_QUESTIONS:
        if q["id"] == question_id:
            return q["text"]
    return question_id


# ============================================================
# Routes
# ============================================================
@router.get("/questions")
async def get_questions():
    """Public — used by the frontend to render the wizard."""
    return {
        "section_1": SECTION_1_QUESTIONS,
        "section_2": SECTION_2_QUESTIONS,
        "high_concern_ids": sorted(HIGH_CONCERN_IDS),
        "texas_resource_block": TEXAS_RESOURCE_BLOCK,
        "pathways": PATHWAYS,
    }


@router.post("")
async def submit_assessment(
    body: AssessmentSubmit,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = score_assessment(body)
    assessment_id = f"sa_{uuid.uuid4().hex[:12]}"
    doc = {
        "assessment_id": assessment_id,
        "user_id": current.user_id,
        "email": current.email,
        "name": current.name,
        "is_guest": bool(getattr(current, "is_guest", False)),
        "section_1": body.section_1 or {},
        "section_2": body.section_2 or {},
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.safety_assessments.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/me")
async def get_my_latest(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.safety_assessments.find_one(
        {"user_id": current.user_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    return doc or None


@router.get("/me/history")
async def get_my_history(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = (
        db.safety_assessments.find({"user_id": current.user_id}, {"_id": 0})
        .sort("created_at", -1)
        .limit(20)
    )
    return [d async for d in cursor]


async def _load_for_user(
    db: AsyncIOMotorDatabase, assessment_id: str, user_id: str
) -> Dict[str, Any]:
    doc = await db.safety_assessments.find_one(
        {"assessment_id": assessment_id, "user_id": user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return doc


def _build_pdf_bytes(doc: Dict[str, Any], excluded_sections: list | None = None) -> bytes:
    section_1_rows = [
        {"text": _question_lookup(q["id"]), "answer": doc.get("section_1", {}).get(q["id"], "") or "—"}
        for q in SECTION_1_QUESTIONS
    ]
    section_2_rows = [
        {"text": _question_lookup(q["id"]), "answer": doc.get("section_2", {}).get(q["id"], "") or "—"}
        for q in SECTION_2_QUESTIONS
    ]
    return build_safety_assessment_pdf(
        user_name=doc.get("name") or "Friend",
        generated_at=doc.get("created_at") or datetime.now(timezone.utc).isoformat(),
        result=doc.get("result") or {},
        section_1_rows=section_1_rows,
        section_2_rows=section_2_rows,
        texas_resource_block=TEXAS_RESOURCE_BLOCK,
        excluded_sections=excluded_sections or [],
    )


@router.get("/{assessment_id}/pdf")
async def download_pdf(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    excluded: Optional[str] = None,
):
    doc = await _load_for_user(db, assessment_id, current.user_id)
    if excluded is not None:
        raw = [x for x in excluded.split(",") if x]
    else:
        raw = list(((doc.get("visibility") or {}).get("excluded") or []))
    ex_list = report_visibility.clean_excluded("safety", raw)
    pdf_bytes = _build_pdf_bytes(doc, excluded_sections=ex_list)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="sacoparents-safety-assessment-{assessment_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


class SafetyVisibilityBody(BaseModel):
    excluded: List[str] = Field(default_factory=list)


class SafetyShareBody(BaseModel):
    excluded: Optional[List[str]] = None


@router.patch("/{assessment_id}/visibility")
async def update_safety_visibility(
    assessment_id: str,
    body: SafetyVisibilityBody,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ex = report_visibility.clean_excluded("safety", body.excluded)
    result = await db.safety_assessments.update_one(
        {"assessment_id": assessment_id, "user_id": current.user_id},
        {"$set": {"visibility": {"excluded": ex, "updated_at": datetime.now(timezone.utc).isoformat()}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"assessment_id": assessment_id, "excluded": ex}


@router.post("/{assessment_id}/share-link")
async def create_safety_share_link(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    body: Optional[SafetyShareBody] = None,
):
    doc = await _load_for_user(db, assessment_id, current.user_id)
    incoming = (body.excluded if body else None)
    if incoming is None:
        incoming = (doc.get("visibility") or {}).get("excluded") or []
    ex = report_visibility.clean_excluded("safety", incoming)
    token = create_share_token("safety", assessment_id, current.user_id, excluded_sections=ex)
    return {
        "token": token,
        "path": f"/api/safety-assessment/shared/{token}",
        "excluded": ex,
    }


@router.get("/shared/{token}")
async def shared_safety_assessment(
    token: str,
    request: Request,
):
    payload = decode_share_token(token)
    if not payload or payload.get("doc_type") != "safety":
        raise HTTPException(status_code=404, detail="This link has expired or is invalid.")
    db: AsyncIOMotorDatabase = request.app.state.db
    doc = await db.safety_assessments.find_one(
        {"assessment_id": payload["doc_id"], "user_id": payload["sub"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Assessment not found")
    ex_list = report_visibility.clean_excluded("safety", payload.get("ex") or [])
    pdf_bytes = _build_pdf_bytes(doc, excluded_sections=ex_list)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="sacoparents-safety-assessment.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{assessment_id}/email")
async def email_assessment(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await _load_for_user(db, assessment_id, current.user_id)
    if doc.get("is_guest"):
        raise HTTPException(
            status_code=400,
            detail="Save your work to email yourself a copy.",
        )
    to_email = current.email
    if not to_email or to_email.endswith("@demo.local"):
        raise HTTPException(
            status_code=400,
            detail="Add a real email to your account first.",
        )
    pdf_bytes = _build_pdf_bytes(doc)
    try:
        send_safety_assessment_report(
            to_email=to_email,
            user_name=current.name or "",
            level=int(doc.get("result", {}).get("level") or 0),
            pathway_title=doc.get("result", {}).get("pathway_title") or "",
            pathway_summary=doc.get("result", {}).get("pathway_summary") or "",
            pdf_bytes=pdf_bytes,
        )
    except EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Email isn\u2019t configured on this environment. Use the PDF download instead.",
        )
    except EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    await db.safety_assessments.update_one(
        {"assessment_id": assessment_id, "user_id": current.user_id},
        {"$set": {"emailed_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "emailed_to": to_email}


@router.post("/{assessment_id}/email-mediator")
async def email_assessment_to_mediator(
    assessment_id: str,
    body: MediatorEmailBody,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """One-tap CTA: forward this parent's IPV Safety Assessment pathway to their mediator."""
    mediator_email = (body.mediator_email or "").strip().lower()
    if "@" not in mediator_email or "." not in mediator_email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="That doesn’t look like a valid email address.")
    if mediator_email.endswith("@demo.local"):
        raise HTTPException(status_code=400, detail="Please use your mediator’s real email address.")

    doc = await _load_for_user(db, assessment_id, current.user_id)
    if doc.get("is_guest"):
        raise HTTPException(
            status_code=400,
            detail="Save your work first so we can email this to your mediator.",
        )

    parent_email = current.email or ""
    if not parent_email or parent_email.endswith("@demo.local"):
        raise HTTPException(
            status_code=400,
            detail="Add a real email to your account so your mediator can reply to you.",
        )

    pdf_bytes = _build_pdf_bytes(doc)
    result = doc.get("result") or {}
    level = int(result.get("level") or 0)
    pathway_title = result.get("pathway_title") or ""
    filename = f"sacoparents-safety-assessment-level-{level or 'x'}.pdf"

    try:
        send_mediator_safety_assessment(
            to_email=mediator_email,
            mediator_name=(body.mediator_name or "").strip(),
            parent_name=current.name or "",
            parent_email=parent_email,
            parent_message=(body.parent_message or "").strip(),
            level=level,
            pathway_title=pathway_title,
            pathway_summary=result.get("pathway_summary") or "",
            pdf_bytes=pdf_bytes,
            pdf_filename=filename,
        )
    except EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Email isn’t configured on this environment. Download the PDF and share it directly.",
        )
    except EmailSendError as e:
        # 503 keeps the error body as JSON through Cloudflare so the frontend
        # can show a friendly toast instead of the raw gateway HTML page.
        logger.warning("Mediator email send failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Couldn’t send to your mediator right now. Please try again in a moment.",
        )

    await db.safety_assessments.update_one(
        {"assessment_id": assessment_id, "user_id": current.user_id},
        {"$push": {"mediator_emails": {
            "to": mediator_email,
            "name": (body.mediator_name or "").strip(),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }}},
    )
    return {"ok": True, "emailed_to": mediator_email}


# ============================================================
# Problem-Solving Worksheet
# ============================================================
@router.post("/problem-solving")
async def save_worksheet(
    body: ProblemSolvingSubmit,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    worksheet_id = f"ps_{uuid.uuid4().hex[:12]}"
    doc = {
        "worksheet_id": worksheet_id,
        "user_id": current.user_id,
        **body.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.problem_solving_worksheets.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/problem-solving/me")
async def list_worksheets(
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = (
        db.problem_solving_worksheets.find({"user_id": current.user_id}, {"_id": 0})
        .sort("created_at", -1)
        .limit(20)
    )
    return [d async for d in cursor]
