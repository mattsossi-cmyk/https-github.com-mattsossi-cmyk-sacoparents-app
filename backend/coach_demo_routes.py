"""Public Coach demo — a bounded, unauthenticated slice of the real AI Coach.

Iter205. Used to power a live sample of the SA CoParents Communication
Assistant on the marketing Landing page. Real Claude output (via the
same `generate_coach_reply` function the signed-in Coach uses), no auth
required, but hard-limited so we don't hand an open LLM microphone to
the internet.

Guardrails:
  * Rate limits: per-IP (hourly) and global (hourly) — enforced with a
    simple in-memory sliding window. Nothing is persisted.
  * Transcript length capped (max 6 turns total = 3 back-and-forths).
    Beyond that the endpoint responds 429 with a friendly nudge to
    sign up for a full conversation.
  * User message length capped at 600 chars.
  * Payload never touches Mongo. Everything is stateless.
  * The exact same safety-flag detection that runs for signed-in
    users flows through this endpoint too — surfaces to the frontend
    so the demo can show its safety banner.

Endpoints (mounted under /api/coach/demo):
  GET  /starters   — curated demo prompts (subset + rebranded copy)
  POST /reply      — send { history, user_message } → get { reply, ... }
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import ai_service
from ai_notice_routes import require_ai_notice
from models import UserPublic


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coach/demo", tags=["coach-demo"])


# --------------------------------------------------------------------- #
# Rate limits.
#
# The demo runs on the marketing surface, so we want everyone to be
# able to try it — but not for someone to loop-scrape Claude through us.
# Two sliding windows: one keyed by IP, one global. Both reset after 1h.
# --------------------------------------------------------------------- #
_PER_IP_WINDOW_SECONDS = 3600
_PER_IP_LIMIT = 10          # 10 messages per IP per hour
_GLOBAL_WINDOW_SECONDS = 3600
_GLOBAL_LIMIT = 400         # 400 messages platform-wide per hour
_MAX_TURNS = 6              # user + assistant rounds combined
_MAX_USER_MESSAGE_LEN = 600

_ip_hits: Dict[str, Deque[float]] = {}
_global_hits: Deque[float] = deque()
_rate_lock = asyncio.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _rate_guard(ip: str) -> None:
    """Raise 429 if this IP or the platform is over the demo quota.

    Sweeps expired buckets on every call — otherwise `_ip_hits` grew
    unbounded as unique visitor IPs kept a live entry forever even
    after their window emptied. The sweep runs under the rate lock
    so a concurrent reader never sees a partially-deleted key.
    """
    now = time.monotonic()
    async with _rate_lock:
        # Trim global window.
        while _global_hits and now - _global_hits[0] > _GLOBAL_WINDOW_SECONDS:
            _global_hits.popleft()
        # Trim the caller's per-IP window and reap any other IP whose
        # window has fully aged out — bounded work per call because
        # the number of live IPs is bounded by the global limit.
        stale_ips: list[str] = []
        for other_ip, other_bucket in _ip_hits.items():
            while other_bucket and now - other_bucket[0] > _PER_IP_WINDOW_SECONDS:
                other_bucket.popleft()
            if not other_bucket:
                stale_ips.append(other_ip)
        for stale in stale_ips:
            _ip_hits.pop(stale, None)
        bucket = _ip_hits.get(ip)
        if len(_global_hits) >= _GLOBAL_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    "The public demo is busy right now — please try again in "
                    "a bit, or create a free account to use the full Coach."
                ),
            )
        if bucket is not None and len(bucket) >= _PER_IP_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    "You've hit the demo's hourly limit — create a free "
                    "account to keep chatting with the Coach."
                ),
            )
        # Record the hit.
        if bucket is None:
            bucket = deque()
            _ip_hits[ip] = bucket
        bucket.append(now)
        _global_hits.append(now)


# --------------------------------------------------------------------- #
# Starter prompts. Curated for the marketing surface — shorter, more
# concrete than the in-app STARTER_PROMPTS. Each prompt is designed to
# produce a Coach reply that showcases BIFF-style, child-centered, non-
# adjudicative tone in ONE turn without needing follow-ups.
# --------------------------------------------------------------------- #
_DEMO_STARTERS: List[Dict[str, str]] = [
    {
        "id": "cancelled_visit_last_minute",
        "label": "Co-parent cancelled the visit an hour before pickup",
        "prompt": (
            "My co-parent just texted me an hour before pickup that they "
            "can't take our daughter this weekend. She was already packed "
            "and excited. I'm furious and about to send a message I'll "
            "regret. Help me get grounded and draft something that keeps "
            "the focus on her."
        ),
    },
    {
        "id": "new_partner_no_heads_up",
        "label": "New partner introduced without a heads-up",
        "prompt": (
            "Our son came home saying he met dad's new girlfriend this "
            "weekend. Nobody told me she'd be there. I'm hurt and I don't "
            "know how to bring it up without starting a fight. What do I say?"
        ),
    },
    {
        "id": "pickup_pattern_chronic_late",
        "label": "Chronic lateness at pickup",
        "prompt": (
            "For the third week in a row my co-parent has been more than "
            "30 minutes late at pickup. Our kid ends up sitting at school "
            "wondering if she's forgotten. How do I raise this so it "
            "actually lands?"
        ),
    },
    {
        "id": "pre_mediation_anxious",
        "label": "I have mediation next week and I'm anxious",
        "prompt": (
            "We have a mediation session next Tuesday and I'm losing "
            "sleep over it. Help me center on what actually matters for "
            "my kids so I don't walk in reactive."
        ),
    },
]


# --------------------------------------------------------------------- #
# Request / response models.
# --------------------------------------------------------------------- #
class DemoTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=6000)


class DemoReplyBody(BaseModel):
    user_message: str = Field(min_length=1, max_length=_MAX_USER_MESSAGE_LEN)
    history: List[DemoTurn] = Field(default_factory=list)


# --------------------------------------------------------------------- #
# Endpoints.
# --------------------------------------------------------------------- #
@router.get("/starters")
async def list_demo_starters() -> Dict[str, Any]:
    return {"starters": _DEMO_STARTERS}


@router.post("/reply")
async def demo_reply(
    body: DemoReplyBody, request: Request, _user: UserPublic = Depends(require_ai_notice)
) -> Dict[str, Any]:
    """Return the Coach's reply to a demo turn. Rate-limited; needs a (demo) session with the AI notice acknowledged."""
    ip = _client_ip(request)
    await _rate_guard(ip)

    # Turn cap — the demo intentionally short-circuits long conversations
    # so we don't keep an open LLM microphone to the internet forever.
    if len(body.history) >= _MAX_TURNS:
        raise HTTPException(
            status_code=409,
            detail=(
                "You've reached the demo's message cap — create a free "
                "account to keep the conversation going with your own "
                "private Coach."
            ),
        )

    history_payload: List[Dict[str, str]] = [
        {"role": t.role, "content": t.content} for t in body.history
    ]
    try:
        result = await ai_service.generate_coach_reply(
            user_message=body.user_message,
            history=history_payload,
            prep_context=None,
            model_preference=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("coach demo LLM call failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=(
                "The Coach couldn't respond right now — please try again "
                "in a moment."
            ),
        )

    return {
        "reply": result.get("reply", ""),
        "suggested_followups": result.get("suggested_followups") or [],
        "safety_flag": bool(result.get("safety_flag", False)),
    }
