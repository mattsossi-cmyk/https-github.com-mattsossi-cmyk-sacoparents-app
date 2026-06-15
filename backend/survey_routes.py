"""Post-event ("How was mediation?") survey routes.

Lifecycle:
  1. When a user generates a Mediation Summary, `schedule_post_event_survey()`
     (called from mediation_routes) inserts a `post_event_surveys` doc with
     `scheduled_send_at = now + 7d`.
  2. A background scheduler (started in server.py) periodically looks for
     surveys whose send time has arrived and emails them. A reminder is sent
     7 days later if the user hasn't responded.
  3. The email contains a public, token-based link to `/survey/<token>` which
     loads the survey, lets the user submit answers, then shows a thank-you.

Endpoints:
  - GET  /api/surveys/post-event/by-token/{token}   (public)
  - POST /api/surveys/post-event/submit/{token}     (public)
  - GET  /api/surveys/admin/post-event              (admin)
  - GET  /api/surveys/admin/post-event.csv          (admin CSV export)
"""
import asyncio
import csv
import io
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

import email_service
from analytics_routes import require_admin
from models import UserPublic


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/surveys", tags=["surveys"])

# How long after a user generates their first summary do we email them?
SURVEY_DELAY_DAYS = int(os.environ.get("POST_EVENT_SURVEY_DELAY_DAYS", "7"))
# How long after the first email do we send a reminder if no response?
REMINDER_DELAY_DAYS = int(os.environ.get("POST_EVENT_SURVEY_REMINDER_DAYS", "7"))
# Scheduler sweep interval.
SCHEDULER_INTERVAL_SECONDS = int(os.environ.get("POST_EVENT_SURVEY_SWEEP_SECONDS", "1800"))


# ============ Question schema (kept in code so admin reports stay aligned) ============
SURVEY_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "primary_reason",
        "type": "single",
        "label": "What was your primary reason for using the SA CoParenting App?",
        "options": [
            "Preparing for mediation",
            "Improving communication with my co-parent",
            "Creating a co-parenting agreement",
            "Focusing on my child's needs",
            "Court recommendation / referral",
            "Other",
        ],
        "allow_other": True,
    },
    {
        "id": "ease_of_use",
        "type": "single",
        "label": "How easy was it to navigate and complete the app?",
        "options": ["Very Easy", "Easy", "Neutral", "Difficult", "Very Difficult"],
    },
    {
        "id": "assessment_helpfulness",
        "type": "single",
        "label": (
            "How helpful was the Co-Parenting Assessment Report in helping you "
            "understand your co-parenting relationship?"
        ),
        "options": [
            "Extremely Helpful",
            "Very Helpful",
            "Somewhat Helpful",
            "Slightly Helpful",
            "Not Helpful",
        ],
    },
    {
        "id": "agreement_helpfulness",
        "type": "single",
        "label": (
            "How helpful was the Co-Parenting Agreement Draft in identifying "
            "goals, interests, and concerns for your child?"
        ),
        "options": [
            "Extremely Helpful",
            "Very Helpful",
            "Somewhat Helpful",
            "Slightly Helpful",
            "Not Helpful",
        ],
    },
    {
        "id": "needs_statement_helpfulness",
        "type": "single",
        "label": (
            "How helpful was the Child Needs Statement in clarifying your "
            "child's needs and priorities?"
        ),
        "options": [
            "Extremely Helpful",
            "Very Helpful",
            "Somewhat Helpful",
            "Slightly Helpful",
            "Not Helpful",
        ],
    },
    {
        "id": "preparedness_change",
        "type": "single",
        "label": (
            "As a result of using the app, how much more prepared do you feel "
            "for mediation or co-parenting discussions?"
        ),
        "options": [
            "Much More Prepared",
            "More Prepared",
            "About the Same",
            "Less Prepared",
            "Much Less Prepared",
        ],
    },
    {
        "id": "child_focus_agreement",
        "type": "single",
        "label": (
            "Did the app help you focus more on your child's needs rather than "
            "parent-to-parent conflict?"
        ),
        "options": [
            "Strongly Agree",
            "Agree",
            "Neutral",
            "Disagree",
            "Strongly Disagree",
        ],
    },
    {
        "id": "most_valuable",
        "type": "long_text",
        "label": "What was the most valuable feature or report provided by the app?",
    },
    {
        "id": "improvements",
        "type": "long_text",
        "label": "What improvements or additional features would make the app more useful for parents?",
    },
    {
        "id": "nps",
        "type": "scale_0_10",
        "label": (
            "How likely are you to recommend the SA CoParenting App to another "
            "parent, mediator, therapist, or attorney?"
        ),
        "low_label": "Not at all likely",
        "high_label": "Extremely likely",
    },
    {
        "id": "outcome_change",
        "type": "single",
        "label": (
            "Since using the SA CoParenting App, have you experienced any "
            "positive changes in your co-parenting relationship?"
        ),
        "options": [
            "Significant Improvement",
            "Some Improvement",
            "No Change",
            "Some Decline",
            "Significant Decline",
        ],
        "optional": True,
    },
    {
        "id": "outcome_explain",
        "type": "long_text",
        "label": "Please explain your answer:",
        "optional": True,
    },
]


# ============ Helpers ============
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _public_app_url() -> str:
    return (os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")


def _survey_link(token: str) -> str:
    base = _public_app_url()
    return f"{base}/survey/{token}" if base else f"/survey/{token}"


def _survey_doc_to_public(doc: dict) -> dict:
    """Strip a survey doc to fields safe to expose via the public token endpoint."""
    return {
        "survey_id": doc.get("survey_id"),
        "status": doc.get("status"),
        "responded_at": doc.get("responded_at"),
        "user_name": doc.get("name") or "",
        "questions": SURVEY_QUESTIONS,
    }


# ============ Called by mediation_routes after a summary is generated ============
async def schedule_post_event_survey(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    email: Optional[str],
    name: Optional[str],
    summary_id: str,
) -> None:
    """Insert a pending post-event survey for this user if they don't already
    have one tied to their most recent summary. Idempotent — running twice
    for the same (user_id, summary_id) is a no-op."""
    if not email:
        # Guest sessions without an email can't receive a survey link.
        return
    existing = await db.post_event_surveys.find_one(
        {"user_id": user_id, "summary_id": summary_id},
        {"_id": 0, "survey_id": 1},
    )
    if existing:
        return
    # Skip if the user has already responded to any survey within the past 30d
    # (we don't want to spam parents who've already given us feedback).
    recent_responded = await db.post_event_surveys.find_one(
        {
            "user_id": user_id,
            "responded_at": {"$gte": _iso(_now() - timedelta(days=30))},
        },
        {"_id": 0, "survey_id": 1},
    )
    if recent_responded:
        return
    token = secrets.token_urlsafe(32)
    survey_id = f"svy_{uuid.uuid4().hex[:12]}"
    await db.post_event_surveys.insert_one({
        "survey_id": survey_id,
        "token": token,
        "user_id": user_id,
        "summary_id": summary_id,
        "email": email,
        "name": name or "",
        "status": "pending",
        "created_at": _iso(_now()),
        "scheduled_send_at": _iso(_now() + timedelta(days=SURVEY_DELAY_DAYS)),
        "sent_at": None,
        "reminder_sent_at": None,
        "responded_at": None,
        "responses": {},
    })


# ============ Public endpoints (token-based) ============
@router.get("/post-event/by-token/{token}")
async def get_post_event_survey(token: str, request: Request):
    db = request.app.state.db
    doc = await db.post_event_surveys.find_one({"token": token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="This survey link is no longer valid.")
    return _survey_doc_to_public(doc)


class SurveySubmitBody(BaseModel):
    responses: Dict[str, Any] = Field(default_factory=dict)


@router.post("/post-event/submit/{token}")
async def submit_post_event_survey(
    token: str,
    request: Request,
    body: SurveySubmitBody = Body(default_factory=SurveySubmitBody),
):
    db = request.app.state.db
    doc = await db.post_event_surveys.find_one({"token": token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="This survey link is no longer valid.")
    if doc.get("status") == "responded":
        raise HTTPException(status_code=409, detail="You've already submitted this survey. Thank you!")

    # Only keep responses for known question ids — silently drop everything else
    # to avoid the DB filling with arbitrary client-sent keys.
    known_ids = {q["id"] for q in SURVEY_QUESTIONS}
    cleaned: Dict[str, Any] = {}
    for qid, val in (body.responses or {}).items():
        if qid in known_ids:
            cleaned[qid] = val

    await db.post_event_surveys.update_one(
        {"token": token},
        {
            "$set": {
                "responses": cleaned,
                "responded_at": _iso(_now()),
                "status": "responded",
            }
        },
    )
    return {"ok": True}


# ============ Admin endpoints ============
@router.get("/admin/post-event")
async def admin_list_post_event(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
    limit: int = 200,
):
    db = request.app.state.db
    limit = max(1, min(limit, 500))
    cursor = db.post_event_surveys.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    rows = await cursor.to_list(limit)

    # Aggregate stats from rows we already pulled (cheap, no extra query).
    sent = sum(1 for r in rows if r.get("sent_at"))
    pending = sum(1 for r in rows if r.get("status") == "pending")
    responded = sum(1 for r in rows if r.get("status") == "responded")
    nps_values = [
        int(r["responses"]["nps"])
        for r in rows
        if isinstance(r.get("responses"), dict)
        and isinstance(r["responses"].get("nps"), (int, float))
    ]
    avg_nps = round(sum(nps_values) / len(nps_values), 1) if nps_values else None

    return {
        "total": len(rows),
        "pending": pending,
        "sent": sent,
        "responded": responded,
        "response_rate_pct": (
            round((responded / sent) * 100) if sent else 0
        ),
        "avg_nps": avg_nps,
        "questions": SURVEY_QUESTIONS,
        "rows": rows,
    }


@router.get("/admin/post-event.csv")
async def admin_export_post_event_csv(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    db = request.app.state.db
    cursor = db.post_event_surveys.find(
        {"status": "responded"}, {"_id": 0}
    ).sort("responded_at", -1)
    rows = await cursor.to_list(2000)

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["responded_at", "email", "name", "user_id", "summary_id"]
    qids = [q["id"] for q in SURVEY_QUESTIONS]
    writer.writerow(header + qids)
    for r in rows:
        responses = r.get("responses") or {}
        writer.writerow(
            [
                r.get("responded_at") or "",
                r.get("email") or "",
                r.get("name") or "",
                r.get("user_id") or "",
                r.get("summary_id") or "",
            ]
            + [str(responses.get(qid, "")) for qid in qids]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="post-event-survey-responses.csv"'
        },
    )


# ============ Background scheduler ============
async def _send_due_surveys(db: AsyncIOMotorDatabase) -> None:
    """Send the initial survey email for any pending survey whose
    scheduled_send_at has elapsed."""
    now_iso = _iso(_now())
    cursor = db.post_event_surveys.find(
        {
            "status": "pending",
            "sent_at": None,
            "scheduled_send_at": {"$lte": now_iso},
        },
        {"_id": 0},
    ).limit(50)
    async for doc in cursor:
        try:
            email_service.send_post_event_survey(
                to_email=doc["email"],
                link_url=_survey_link(doc["token"]),
                user_name=doc.get("name") or "",
            )
            await db.post_event_surveys.update_one(
                {"token": doc["token"]},
                {"$set": {"sent_at": _iso(_now())}},
            )
            logger.info("Post-event survey sent → %s", doc["email"])
        except email_service.EmailNotConfigured:
            # No point hammering the loop if email is off — drop out.
            logger.warning("Resend not configured; skipping survey send.")
            return
        except Exception:  # noqa: BLE001
            logger.exception("Post-event survey send failed for %s", doc.get("email"))


async def _send_due_reminders(db: AsyncIOMotorDatabase) -> None:
    """Send a reminder N days after the first email if there's been no response."""
    cutoff = _iso(_now() - timedelta(days=REMINDER_DELAY_DAYS))
    cursor = db.post_event_surveys.find(
        {
            "status": "pending",  # responded -> "responded", so this stays pending
            "sent_at": {"$ne": None, "$lte": cutoff},
            "reminder_sent_at": None,
            "responded_at": None,
        },
        {"_id": 0},
    ).limit(50)
    async for doc in cursor:
        try:
            email_service.send_post_event_survey_reminder(
                to_email=doc["email"],
                link_url=_survey_link(doc["token"]),
                user_name=doc.get("name") or "",
            )
            await db.post_event_surveys.update_one(
                {"token": doc["token"]},
                {"$set": {"reminder_sent_at": _iso(_now())}},
            )
            logger.info("Post-event survey reminder sent → %s", doc["email"])
        except email_service.EmailNotConfigured:
            return
        except Exception:  # noqa: BLE001
            logger.exception("Post-event survey reminder failed for %s", doc.get("email"))


async def survey_scheduler_loop(app) -> None:
    """Long-lived task that periodically processes due survey emails."""
    # Small delay so we don't slam the loop on startup before the DB connection
    # has fully warmed up.
    await asyncio.sleep(60)
    while True:
        try:
            db = app.state.db
            await _send_due_surveys(db)
            await _send_due_reminders(db)
        except Exception:  # noqa: BLE001
            logger.exception("Survey scheduler sweep failed; will retry.")
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
