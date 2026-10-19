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
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from auth import UserPublic, get_current_user, get_db, create_share_token, decode_share_token
from email_service import EmailNotConfigured, EmailSendError, send_mediator_safety_assessment, send_safety_assessment_report
from safety_assessment_pdf import build_safety_assessment_pdf
from safety_court_report_pdf import build_court_report_pdf
from safety_one_pager_pdf import build_one_pager_pdf
from trauma_lens import PROCEDURAL_SAFEGUARDS
from share_routes import record_share_token, is_share_token_revoked
from analytics_routes import ADMIN_EMAILS
from ai_notice_routes import user_has_ai_notice
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
    # ---- Structured gap-closure items (added iter 106) ----
    # These items address gaps identified in the safety screen:
    # strangulation pattern, firearms access (specific), sexual coercion
    # (non-force), digital surveillance, financial abuse, substance use
    # during incidents, distinct homicide/suicide threats, and
    # protective-order status. Wording is clinical, structured, and
    # designed to be filed with a court where relevant.
    {
        "id": "s1_q19",
        "text": (
            "Has the other parent choked, strangled, or restricted your "
            "breathing on more than one occasion — even briefly? "
            "(Any strangulation is a well-established predictor of severe harm.)"
        ),
        "high_concern": True,
        "da_domain": True,
        "gap_domain": "strangulation",
    },
    {
        "id": "s1_q20",
        "text": (
            "Does the other parent own, keep at home, or have easy access "
            "to firearms — regardless of whether they have threatened you with one?"
        ),
        "high_concern": True,
        "da_domain": True,
        "gap_domain": "firearms",
    },
    {
        "id": "s1_q21",
        "text": (
            "Have you been pressured, manipulated, or coerced into sexual "
            "activity you did not want, without physical force being used?"
        ),
        "high_concern": True,
        "da_domain": True,
        "gap_domain": "sexual_coercion",
    },
    {
        "id": "s1_q22",
        "text": (
            "Have you found (or reasonably suspect) tracking apps, spyware, "
            "hidden cameras, GPS trackers, or account impersonation used to "
            "monitor your movements or communications?"
        ),
        "high_concern": True,
        "gap_domain": "digital_surveillance",
    },
    {
        "id": "s1_q23",
        "text": (
            "Has the other parent deliberately sabotaged your income, run up "
            "debt in your name, hidden marital assets, or interfered with your "
            "employment, education, or benefits access?"
        ),
        "high_concern": True,
        "gap_domain": "financial_abuse",
    },
    {
        "id": "s1_q24",
        "text": (
            "Has the other parent been under the influence of alcohol or drugs "
            "during any of the violent, threatening, or coercive incidents "
            "you have experienced?"
        ),
        "high_concern": True,
        "da_domain": True,
        "gap_domain": "substance_during_incidents",
    },
    {
        "id": "s1_q25",
        "text": (
            "Has the other parent specifically threatened to kill you, the "
            "children, or someone else — separate from any other threats they may have made?"
        ),
        "high_concern": True,
        "da_domain": True,
        "gap_domain": "homicide_threat",
    },
    {
        "id": "s1_q26",
        "text": (
            "Has the other parent specifically threatened to kill themselves "
            "— particularly in connection with you leaving, ending the "
            "relationship, or the children being separated from them?"
        ),
        "high_concern": True,
        "da_domain": True,
        "gap_domain": "suicide_threat",
    },
    {
        "id": "s1_q27",
        "text": (
            "Is there currently a protective order, restraining order, or "
            "intervention order in force involving you and the other parent?"
        ),
        "high_concern": False,
        "gap_domain": "protective_order_current",
    },
    {
        "id": "s1_q28",
        "text": (
            "Have you ever been advised by police, a domestic-violence service, "
            "a lawyer, or a court to seek a protective order — whether or not "
            "you followed through?"
        ),
        "high_concern": False,
        "gap_domain": "protective_order_advised",
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
AnswerYNU = str  # "yes" | "no" | "unsure" | "prefer_not" — validated in scoring


class AssessmentSubmit(BaseModel):
    section_1: Dict[str, AnswerYNU] = Field(default_factory=dict)
    section_2: Dict[str, AnswerYNU] = Field(default_factory=dict)
    # Phase 3/4/5 optional sections. All three may be omitted or
    # partially filled — the classifier treats missing as low-signal
    # rather than reporting.
    pattern_context: Dict[str, str] = Field(default_factory=dict)
    trauma_impact: Dict[str, str] = Field(default_factory=dict)
    child_experience: Dict[str, str] = Field(default_factory=dict)


class MediatorEmailBody(BaseModel):
    mediator_email: str = Field(min_length=3, max_length=254)
    mediator_name: str = ""
    parent_message: str = ""
    include_answers: bool = False  # Section 1 + 2 answers stay out unless the parent ticks the box


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


# Skipping one of these ("I'd rather not answer") makes the result at least Amber (Level 2):
# immediate danger, physical or sexual harm, or harm to children.
SKIP_FLOOR_S1_IDS = frozenset({
    "s1_q1", "s1_q11", "s1_q12", "s1_q15", "s1_q20", "s1_q25", "s1_q26",  # immediate danger
    "s1_q2", "s1_q13", "s1_q19",  # physical harm
    "s1_q14", "s1_q21",  # sexual harm
})
SKIP_FLOOR_CHILD_IDS = frozenset({"ce_q1", "ce_q8"})  # harm to children
SKIP_FLOOR_LEVEL = 2


def _is_declined(v: Any) -> bool:
    return isinstance(v, str) and v.strip().lower() == "prefer_not"


def _answer_text(v: Any) -> str:
    """Answer as shown in PDFs and summaries; 'I'd rather not answer' reads as a plain label."""
    return "Prefer not to answer" if _is_declined(v) else (v or "—")


def score_assessment(payload: AssessmentSubmit) -> Dict[str, Any]:
    """Return level (1-4), flags, counts. Pure function — easy to unit-test."""
    s1 = payload.section_1 or {}
    s2 = payload.section_2 or {}

    high_concern_hits = sorted([qid for qid in HIGH_CONCERN_IDS if _is_yes(s1.get(qid))])
    coercive_hits = sorted([qid for qid in COERCIVE_IDS if _is_yes(s1.get(qid))])
    section_1_yes = sum(1 for q in SECTION_1_QUESTIONS if _is_yes(s1.get(q["id"])))
    # "I'd rather not answer" is a skip: it never counts toward a concern, except the floor below.
    section_1_declined = sum(1 for q in SECTION_1_QUESTIONS if _is_declined(s1.get(q["id"])))
    declined = section_1_declined + sum(1 for q in SECTION_2_QUESTIONS if _is_declined(s2.get(q["id"])))
    child = getattr(payload, "child_experience", None) or {}
    floor_skips = sorted(
        [qid for qid in SKIP_FLOOR_S1_IDS if _is_declined(s1.get(qid))]
        + [qid for qid in SKIP_FLOOR_CHILD_IDS if _is_declined(child.get(qid))]
    )
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
    if floor_skips:
        level = min(level, SKIP_FLOOR_LEVEL)

    pathway = PATHWAYS[level]
    result = {
        "level": level,
        "pathway_title": pathway["title"],
        "pathway_headline": pathway["headline"],
        "pathway_tone": pathway["tone"],
        "pathway_summary": pathway["summary"],
        "recommendations": pathway["recommendations"],
        "high_concern_hits": high_concern_hits,
        "coercive_hits": coercive_hits,
        "section_1_yes_count": section_1_yes,
        "section_1_declined_count": section_1_declined,
        "declined_count": declined,
        "skip_floor_ids": floor_skips,
        "section_2_concern_count": section_2_concerns,
    }
    # Trauma-Informed Safety and Functioning Lens (TISFL) — attach the
    # three-findings interpretive layer to every score. Kept in a
    # separate `lens` field so legacy callers reading `level`/`pathway_*`
    # continue to work unchanged.
    try:
        from trauma_lens import build_findings
        from lens_extensions import (
            classify_pattern,
            analyse_trauma_impact,
            analyse_child_experience,
        )
        pattern_ctx = getattr(payload, "pattern_context", None) or {}
        trauma_imp = getattr(payload, "trauma_impact", None) or {}
        child_exp = getattr(payload, "child_experience", None) or {}
        extensions = {
            "pattern_context": classify_pattern(pattern_ctx),
            "trauma_impact": analyse_trauma_impact(trauma_imp),
            "child_experience": analyse_child_experience(child_exp),
            # Raw answers threaded through so the feasibility tier can
            # inspect specific items (e.g. ce_q1 direct victimisation).
            "child_experience_raw": child_exp,
        }
        result["extension_analysis"] = extensions
        result["lens"] = build_findings(
            result,
            extensions=extensions,
            section_1_answers=payload.section_1 or {},
        )
    except Exception:  # noqa: BLE001 - defensive: never fail scoring on lens issues
        pass
    return result


def _question_lookup(question_id: str) -> str:
    for q in SECTION_1_QUESTIONS:
        if q["id"] == question_id:
            return q["text"]
    for q in SECTION_2_QUESTIONS:
        if q["id"] == question_id:
            return q["text"]
    return question_id


# Accepted answer values for every question in both sections. Kept lower-cased
# so callers submitting "Yes"/"YES"/"yes" all pass. The frontend Yes/No/Unsure
# radios emit lowercase already.
_VALID_ANSWERS = {"yes", "no", "unsure", "prefer_not"}


def _validate_all_answered(body: "AssessmentSubmit") -> None:
    """Reject the submission when the parent hasn't answered every
    question in both sections. Mirrors the frontend's Continue gate so
    a scripted client can't slip an incomplete assessment past.

    Raises 400 with a machine-readable `missing` payload the UI can
    highlight ({"section_1": ["s1_q7"], "section_2": []}).
    """
    s1 = {k: (str(v or "").strip().lower()) for k, v in (body.section_1 or {}).items()}
    s2 = {k: (str(v or "").strip().lower()) for k, v in (body.section_2 or {}).items()}
    missing_s1 = [q["id"] for q in SECTION_1_QUESTIONS if s1.get(q["id"]) not in _VALID_ANSWERS]
    missing_s2 = [q["id"] for q in SECTION_2_QUESTIONS if s2.get(q["id"]) not in _VALID_ANSWERS]
    if missing_s1 or missing_s2:
        total_missing = len(missing_s1) + len(missing_s2)
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"Please answer every question before submitting "
                    f"({total_missing} left to answer)."
                ),
                "missing": {"section_1": missing_s1, "section_2": missing_s2},
            },
        )


# ============================================================
# Routes
# ============================================================
@router.get("/questions")
async def get_questions():
    """Public — used by the frontend to render the wizard."""
    from lens_extensions import all_extension_sections
    ext = all_extension_sections()
    return {
        "section_1": SECTION_1_QUESTIONS,
        "section_2": SECTION_2_QUESTIONS,
        "high_concern_ids": sorted(HIGH_CONCERN_IDS),
        "texas_resource_block": TEXAS_RESOURCE_BLOCK,
        "pathways": PATHWAYS,
        # Phase 3/4/5 optional sections.
        "pattern_context": ext["pattern_context"],
        "trauma_impact": ext["trauma_impact"],
        "child_experience": ext["child_experience"],
    }


@router.post("")
async def submit_assessment(
    body: AssessmentSubmit,
    request: Request,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _validate_all_answered(body)
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
        "pattern_context": body.pattern_context or {},
        "trauma_impact": body.trauma_impact or {},
        "child_experience": body.child_experience or {},
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


def _build_pdf_bytes(
    doc: Dict[str, Any],
    excluded_sections: list | None = None,
    ai_summaries: Dict[str, Any] | None = None,
) -> bytes:
    section_1_rows = [
        {"text": _question_lookup(q["id"]), "answer": _answer_text(doc.get("section_1", {}).get(q["id"], ""))}
        for q in SECTION_1_QUESTIONS
    ]
    section_2_rows = [
        {"text": _question_lookup(q["id"]), "answer": _answer_text(doc.get("section_2", {}).get(q["id"], ""))}
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
        ai_summaries=ai_summaries or {},
    )


async def _fetch_or_generate_ai_summaries(
    db: AsyncIOMotorDatabase, doc: Dict[str, Any],
) -> Dict[str, Any]:
    """Return the four AI narratives (overall / pathway / section_1 /
    section_2) for this Safety Assessment. Cached on the assessment doc
    itself under ``ai_summaries`` after the first successful generation
    so subsequent PDF downloads are instant.

    Never raises — a failure returns ``{}`` and the PDF renders without
    the AI blocks (the layout has graceful empty-state handling).
    """
    cached = doc.get("ai_summaries")
    if isinstance(cached, dict) and any(cached.get(k) for k in ("overall", "pathway", "section_1", "section_2")):
        return cached
    if not await user_has_ai_notice(db, doc.get("user_id")):
        return {}
    try:
        from safety_ai_summary import generate_safety_summaries
        section_1_rows = [
            {"text": _question_lookup(q["id"]),
             "answer": _answer_text(doc.get("section_1", {}).get(q["id"], ""))}
            for q in SECTION_1_QUESTIONS
        ]
        section_2_rows = [
            {"text": _question_lookup(q["id"]),
             "answer": _answer_text(doc.get("section_2", {}).get(q["id"], ""))}
            for q in SECTION_2_QUESTIONS
        ]
        summaries = await generate_safety_summaries(
            doc=doc,
            section_1_rows=section_1_rows,
            section_2_rows=section_2_rows,
        )
    except Exception:  # noqa: BLE001
        return {}
    # Only cache when at least one field was populated — a completely
    # empty result usually means the LLM key was missing at request
    # time; we want to retry next download rather than lock the empty
    # state in perpetuity.
    if any((summaries or {}).get(k) for k in ("overall", "pathway", "section_1", "section_2")):
        try:
            await db.safety_assessments.update_one(
                {"assessment_id": doc.get("assessment_id"), "user_id": doc.get("user_id")},
                {"$set": {
                    "ai_summaries":              summaries,
                    "ai_summaries_generated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
        except Exception:  # noqa: BLE001
            pass
    return summaries or {}


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
    ai = await _fetch_or_generate_ai_summaries(db, doc)
    pdf_bytes = _build_pdf_bytes(doc, excluded_sections=ex_list, ai_summaries=ai)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="sacoparents-safety-assessment-{assessment_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{assessment_id}/court-report")
async def download_court_report(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    reviewer_name: str = "",
):
    """Court-facing PDF using the Trauma-Informed Safety and Functioning
    Lens. Excludes raw Section-1 behavioural answers by default, puts
    the two interpretation rules on page 1, one finding per page, adds
    a limits-of-use statement, procedural safeguards, and a signature
    block for the parent + optional qualified reviewer co-signature.
    """
    doc = await _load_for_user(db, assessment_id, current.user_id)
    if doc.get("is_guest"):
        raise HTTPException(
            status_code=400,
            detail="Save your work before downloading the court report.",
        )
    result = doc.get("result") or {}
    # If the doc was created before the lens layer existed, attach it
    # now so old assessments still produce a valid court report.
    if not result.get("lens"):
        try:
            from trauma_lens import build_findings
            result = dict(result)
            result["lens"] = build_findings(result)
        except Exception:  # noqa: BLE001
            pass
    pdf_bytes = build_court_report_pdf(
        user_name=doc.get("name") or current.name or "",
        generated_at=doc.get("created_at") or datetime.now(timezone.utc).isoformat(),
        assessment_id=assessment_id,
        result=result,
        safeguards=PROCEDURAL_SAFEGUARDS,
        reviewer_name=(reviewer_name or "").strip(),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="tisfl-court-report-{assessment_id}.pdf"'
            ),
            "Cache-Control": "no-store",
        },
    )


@router.post("/{assessment_id}/prepare-cosign")
async def prepare_cosign(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Owner prepares a Reviewer Co-Sign QR for their Court Report.
    Returns ``{sig_id, verify_url, qr_png_data_url}`` — the frontend
    renders the QR in a modal so a mediator or DV practitioner can
    scan and land on the public verify page."""
    doc = await _load_for_user(db, assessment_id, current.user_id)
    if doc.get("is_guest"):
        raise HTTPException(
            status_code=400,
            detail="Save your work before creating a co-sign QR.",
        )
    from court_report_verify_routes import create_court_report_signature
    return await create_court_report_signature(
        db,
        assessment_id=assessment_id,
        user_id=current.user_id,
        parent_name=doc.get("name") or current.name or "",
    )


@router.get("/{assessment_id}/one-pager")
async def download_one_pager(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """"For your professional" one-page handoff PDF. Very short — names
    what this tool is/is-not, summarises the findings at a glance
    (headlines only, no raw behavioural language), and lists targeted
    questions the professional should now explore with the parent."""
    doc = await _load_for_user(db, assessment_id, current.user_id)
    if doc.get("is_guest"):
        raise HTTPException(
            status_code=400,
            detail="Save your work before downloading the one-pager.",
        )
    result = doc.get("result") or {}
    if not result.get("lens"):
        try:
            from trauma_lens import build_findings
            result = dict(result)
            result["lens"] = build_findings(result)
        except Exception:  # noqa: BLE001
            pass
    pdf_bytes = build_one_pager_pdf(
        user_name=doc.get("name") or current.name or "",
        generated_at=doc.get("created_at") or datetime.now(timezone.utc).isoformat(),
        assessment_id=assessment_id,
        result=result,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="sacoparents-for-your-professional-{assessment_id}.pdf"'
            ),
            "Cache-Control": "no-store",
        },
    )


# Minimum seconds between AI-summary regenerations per assessment. Keeps
# Claude cost + latency bounded when parents (or admins) hammer the
# regenerate button. Override via env for tests / operator debugging.
REGENERATE_SUMMARIES_COOLDOWN_SEC = int(
    os.environ.get("SAFETY_SUMMARY_REGEN_COOLDOWN_SEC", "600")
)


@router.post("/{assessment_id}/regenerate-summaries")
async def regenerate_safety_summaries(
    assessment_id: str,
    current: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Force-regenerate the four Claude Sonnet 4.5 AI summaries for a
    Family Violence & Communication Safety Assessment.

    Access: the assessment **owner** OR an ADMIN_EMAILS operator.

    Cooldown: one regeneration per ``REGENERATE_SUMMARIES_COOLDOWN_SEC``
    (default 10 minutes) per assessment, enforced from the doc's
    ``ai_summaries_generated_at`` timestamp. Admins bypass the cooldown
    so ops can force-refresh support cases.
    """
    if current.is_guest:
        raise HTTPException(status_code=403, detail="Sign in to regenerate summaries.")
    is_admin = current.email.lower() in ADMIN_EMAILS
    # Load doc — owner path first, else admin fallback.
    doc = await db.safety_assessments.find_one(
        {"assessment_id": assessment_id, "user_id": current.user_id}, {"_id": 0}
    )
    if not doc:
        if not is_admin:
            raise HTTPException(status_code=404, detail="Assessment not found")
        doc = await db.safety_assessments.find_one(
            {"assessment_id": assessment_id}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")

    # Cooldown enforcement — admin bypass so operators can force-refresh.
    if not is_admin:
        last_iso = doc.get("ai_summaries_generated_at")
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(str(last_iso).replace("Z", "+00:00"))
                delta = (datetime.now(timezone.utc) - last_dt).total_seconds()
                if delta < REGENERATE_SUMMARIES_COOLDOWN_SEC:
                    retry_in = int(REGENERATE_SUMMARIES_COOLDOWN_SEC - delta)
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            f"Please wait {retry_in // 60}m {retry_in % 60}s "
                            "before regenerating the AI summaries again."
                        ),
                    )
            except HTTPException:
                raise
            except Exception:  # noqa: BLE001
                # Bad timestamp shouldn't wedge the button forever.
                pass

    # Clear cache then regenerate.
    await db.safety_assessments.update_one(
        {"assessment_id": assessment_id, "user_id": doc.get("user_id")},
        {"$unset": {"ai_summaries": "", "ai_summaries_generated_at": ""}},
    )
    fresh_doc = {**doc}
    fresh_doc.pop("ai_summaries", None)
    fresh_doc.pop("ai_summaries_generated_at", None)
    summaries = await _fetch_or_generate_ai_summaries(db, fresh_doc)
    if not any(summaries.get(k) for k in ("overall", "pathway", "section_1", "section_2")):
        raise HTTPException(
            status_code=503,
            detail="AI summary service is temporarily unavailable. Please try again shortly.",
        )
    return {
        "assessment_id": assessment_id,
        "ai_summaries": summaries,
        "ai_summaries_generated_at": datetime.now(timezone.utc).isoformat(),
        "forced_by_admin": bool(is_admin and doc.get("user_id") != current.user_id),
    }


class SafetyVisibilityBody(BaseModel):
    excluded: List[str] = Field(default_factory=list)


class SafetyShareBody(BaseModel):
    excluded: Optional[List[str]] = None
    expire_days: Optional[int] = 7
    label: Optional[str] = None


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
    expire_days = body.expire_days if body else 7
    token = create_share_token("safety", assessment_id, current.user_id,
                               excluded_sections=ex, expire_days=expire_days)
    payload = decode_share_token(token) or {}
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) if payload.get("exp") else None
    await record_share_token(db, jti=payload.get("jti"), user_id=current.user_id,
                             doc_type="safety", doc_id=assessment_id,
                             expires_at=expires_at,
                             label=(body.label if body else None))
    return {
        "token": token,
        "jti": payload.get("jti"),
        "path": f"/api/safety-assessment/shared/{token}",
        "excluded": ex,
        "expires_at": expires_at.isoformat() if expires_at else None,
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
    if await is_share_token_revoked(db, payload.get("jti")):
        raise HTTPException(status_code=404, detail="This link has been revoked by the sender.")
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

    pdf_bytes = _build_pdf_bytes(doc, excluded_sections=[] if body.include_answers else ["section_1", "section_2"])
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
            "included_answers": body.include_answers,
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

