"""Admin-only "Insights" weekly report.

Pulls the past 7 days of:
  - Post-event survey responses (open-text fields)
  - Journal entries
  - Legal acknowledgments
  - Sign-ups + summaries generated + invites sent

…and asks Claude (via Emergent LLM Key) to produce a 5-minute Monday-morning
narrative that surfaces themes, concerns, and recommended actions.

Cached per ISO week so we don't burn tokens on every page load.

Endpoints:
  - GET  /api/insights/admin/weekly             (admin only — read cached/build)
  - POST /api/insights/admin/weekly/regenerate  (admin only — force a fresh build)
"""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException, Request

from analytics_routes import require_admin
from ai_service import CLAUDE_MODEL, PROVIDER, SAFETY_GUARDRAIL
from models import UserPublic


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _week_iso(dt: datetime) -> str:
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


async def _gather_signals(db) -> Dict[str, Any]:
    """Pull a structured snapshot of the past week's activity for Claude."""
    since_iso = _iso(_now() - timedelta(days=7))

    # Survey open responses
    survey_cursor = db.post_event_surveys.find(
        {"status": "responded", "responded_at": {"$gte": since_iso}},
        {"_id": 0, "responses": 1, "responded_at": 1},
    ).sort("responded_at", -1)
    survey_docs = await survey_cursor.to_list(200)
    most_valuable: List[str] = []
    improvements: List[str] = []
    nps_values: List[int] = []
    for d in survey_docs:
        r = d.get("responses") or {}
        if isinstance(r.get("most_valuable"), str) and r["most_valuable"].strip():
            most_valuable.append(r["most_valuable"].strip())
        if isinstance(r.get("improvements"), str) and r["improvements"].strip():
            improvements.append(r["improvements"].strip())
        if isinstance(r.get("nps"), (int, float)):
            nps_values.append(int(r["nps"]))

    # Journal entries — pull content only, no identifying info
    journal_cursor = db.journal_entries.find(
        {"created_at": {"$gte": since_iso}},
        {"_id": 0, "content": 1, "kind": 1, "created_at": 1},
    ).sort("created_at", -1).limit(150)
    journal_entries = await journal_cursor.to_list(150)
    journal_snippets = [
        (e.get("content") or "").strip()[:600]
        for e in journal_entries
        if e.get("content")
    ]

    # Counts
    legal_count = await db.legal_acknowledgments.count_documents(
        {"acknowledged_at": {"$gte": since_iso}}
    )
    new_users = await db.users.count_documents(
        {"created_at": {"$gte": since_iso}, "is_guest": {"$ne": True}}
    )
    new_guests = await db.users.count_documents(
        {"created_at": {"$gte": since_iso}, "is_guest": True}
    )
    summaries_count = await db.summaries.count_documents(
        {"generated_at": {"$gte": since_iso}}
    )
    invites_sent = await db.coparent_invites.count_documents(
        {"created_at": {"$gte": since_iso}}
    )
    invites_accepted = await db.coparent_invites.count_documents(
        {"signed_up_at": {"$gte": since_iso}}
    )

    avg_nps = round(sum(nps_values) / len(nps_values), 1) if nps_values else None

    return {
        "window_days": 7,
        "counts": {
            "new_users": new_users,
            "new_guests": new_guests,
            "summaries_generated": summaries_count,
            "legal_acks": legal_count,
            "survey_responses": len(survey_docs),
            "invites_sent": invites_sent,
            "invites_accepted": invites_accepted,
            "journal_entries": len(journal_entries),
        },
        "nps": {"count": len(nps_values), "avg": avg_nps},
        "most_valuable_text": most_valuable,
        "improvements_text": improvements,
        "journal_snippets": journal_snippets,
    }


def _make_insights_chat() -> LlmChat:
    system = (
        "You are an admin-only insights analyst for SA CoParents — a co-parenting "
        "prep platform. You read aggregated, anonymous user data from the past 7 days "
        "and produce a concise weekly briefing for the platform owner (a former "
        "mediator).\n\n"
        "Your tone: calm, professional, honest. No sycophancy. No marketing fluff.\n"
        "Output strict JSON only — no markdown, no apologies, no preamble."
    )
    return LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"insights-{uuid.uuid4().hex[:10]}",
        system_message=SAFETY_GUARDRAIL + system,
    ).with_model(PROVIDER, CLAUDE_MODEL)


def _extract_json(text: str) -> Dict[str, Any]:
    # Tolerant JSON parsing — strips code fences if Claude wraps the output.
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # drop the first fence line + any closing fence
        cleaned = "\n".join(
            ln for ln in lines if not ln.strip().startswith("```")
        )
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Find the first { and last } and try again — handles trailing prose.
        i, j = cleaned.find("{"), cleaned.rfind("}")
        if i != -1 and j != -1 and j > i:
            return json.loads(cleaned[i:j + 1])
        raise


async def _generate_briefing(signals: Dict[str, Any]) -> Dict[str, Any]:
    if not os.environ.get("EMERGENT_LLM_KEY"):
        raise HTTPException(
            status_code=503,
            detail="AI key not configured — insights need EMERGENT_LLM_KEY set.",
        )
    chat = _make_insights_chat()
    payload = json.dumps(signals, ensure_ascii=False)
    prompt = f"""Below is anonymized activity from SA CoParents for the past 7 days.

Produce a JSON briefing with EXACTLY these keys:

{{
  "headline": "one-sentence read on the week (e.g. 'Steady engagement; users mostly value the agreement draft.')",
  "highlights": ["3-5 short bullets — what worked, what's resonating"],
  "user_voice_themes": ["3-6 themes drawn from the open-text survey + journal data, each a short noun phrase"],
  "concerning_patterns": ["any patterns suggesting child welfare, safety, or platform abuse risk — empty array if none"],
  "recommended_actions": ["3-5 concrete, owner-actionable next steps for the week ahead"],
  "closing_note": "one calm sentence to close the briefing"
}}

Rules:
- Be honest. If the data is too sparse for a real insight, say so in the headline.
- Quote user voice ONLY when it's representative (anonymized).
- "concerning_patterns" should err on the side of inclusion — if anything in the journal snippets hints at DV, suicidal ideation, or threats to children, surface it.
- Never identify a user. Always speak in aggregate ("several parents…", "one journal entry mentioned…").
- Output strict JSON only — no markdown.

Data:
{payload}
"""
    response = await chat.send_message(UserMessage(text=prompt))
    return _extract_json(response)


async def _build_and_cache(db) -> Dict[str, Any]:
    week = _week_iso(_now())
    signals = await _gather_signals(db)
    briefing = await _generate_briefing(signals)
    doc = {
        "week_iso": week,
        "generated_at": _iso(_now()),
        "signals": signals,
        "briefing": briefing,
    }
    await db.weekly_insights.update_one(
        {"week_iso": week}, {"$set": doc}, upsert=True
    )
    return doc


@router.get("/admin/weekly")
async def get_weekly_insights(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Return the cached briefing for the current ISO week, or build one
    on first request of the week."""
    db = request.app.state.db
    week = _week_iso(_now())
    cached = await db.weekly_insights.find_one({"week_iso": week}, {"_id": 0})
    if cached:
        return cached
    return await _build_and_cache(db)


@router.post("/admin/weekly/regenerate")
async def regenerate_weekly_insights(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Force a fresh build for the current ISO week (overwrites the cache)."""
    return await _build_and_cache(request.app.state.db)
