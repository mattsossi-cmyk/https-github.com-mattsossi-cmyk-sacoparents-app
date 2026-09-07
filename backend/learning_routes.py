"""Learning Center — read-tracking + optional AI depth expansion.

Endpoints:
  * GET  /api/learning/hubs                      → static hub + article index
  * GET  /api/learning/hub/{hub}/article/{slug}  → article body + user read state
  * POST /api/learning/hub/{hub}/article/{slug}/read           → mark read
  * DELETE /api/learning/hub/{hub}/article/{slug}/read         → unmark (undo)
  * POST /api/learning/hub/{hub}/article/{slug}/coach          → AI depth
      (short 3-paragraph expansion via Claude; cached per article per user)
  * GET  /api/learning/progress                  → user's read summary

Progress is stored per-user in `learning_reads`; AI expansions in
`learning_ai_expansions` (cached forever unless force=true, since the
seed content doesn't change).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from auth import UserPublic, get_current_user, get_db
from learning_content import (
    HUBS, find_article, get_article, get_hub, hubs_summary,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])

_READS_COLLECTION = "learning_reads"
_AI_COLLECTION = "learning_ai_expansions"


class CoachIn(BaseModel):
    force: Optional[bool] = False


async def _read_set(db: AsyncIOMotorDatabase, user_id: str) -> Dict[str, str]:
    """Return `{article_slug: read_at_iso}` for every article the user has read."""
    cursor = db[_READS_COLLECTION].find(
        {"user_id": user_id}, {"_id": 0, "article_slug": 1, "read_at": 1},
    )
    return {row["article_slug"]: row.get("read_at") async for row in cursor}


def _hub_progress(hub: Dict[str, Any], read_map: Dict[str, str]) -> Dict[str, Any]:
    read_count = sum(1 for a in hub["articles"] if a["slug"] in read_map)
    return {
        "read": read_count,
        "total": len(hub["articles"]),
        "complete": read_count == len(hub["articles"]) and hub["articles"],
    }


@router.get("/hubs")
async def list_hubs(user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Return every hub (with lightweight article stubs) alongside the
    current user's per-hub read progress."""
    read_map = await _read_set(db, user.user_id)
    hubs = []
    for hub_stub in hubs_summary():
        hub_full = get_hub(hub_stub["slug"])
        progress = _hub_progress(hub_full, read_map)
        stub_articles = []
        for a in hub_stub["articles"]:
            stub_articles.append({
                **a,
                "read": a["slug"] in read_map,
                "read_at": read_map.get(a["slug"]),
            })
        hubs.append({**hub_stub, "articles": stub_articles, "progress": progress})
    total_articles = sum(len(h["articles"]) for h in HUBS)
    return {
        "hubs": hubs,
        "total_articles": total_articles,
        "read_count": len(read_map),
    }


@router.get("/hub/{hub_slug}/article/{article_slug}")
async def get_article_endpoint(hub_slug: str, article_slug: str,
                               user: UserPublic = Depends(get_current_user),
                               db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Return an article's full body plus this user's read + AI-expansion state."""
    article = get_article(hub_slug, article_slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    read_row = await db[_READS_COLLECTION].find_one(
        {"user_id": user.user_id, "article_slug": article_slug}, {"_id": 0, "read_at": 1},
    )
    ai_row = await db[_AI_COLLECTION].find_one(
        {"user_id": user.user_id, "article_slug": article_slug}, {"_id": 0},
    )
    return {
        "article": article,
        "read": bool(read_row),
        "read_at": (read_row or {}).get("read_at"),
        "ai_expansion": (ai_row or {}).get("expansion"),
        "ai_generated_at": (ai_row or {}).get("generated_at"),
    }


@router.post("/hub/{hub_slug}/article/{article_slug}/read")
async def mark_read(hub_slug: str, article_slug: str,
                    user: UserPublic = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    article = get_article(hub_slug, article_slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    now = datetime.now(timezone.utc).isoformat()
    await db[_READS_COLLECTION].update_one(
        {"user_id": user.user_id, "article_slug": article_slug},
        {"$set": {
            "user_id": user.user_id,
            "article_slug": article_slug,
            "hub_slug": hub_slug,
            "read_at": now,
        }},
        upsert=True,
    )
    read_map = await _read_set(db, user.user_id)
    return {
        "ok": True,
        "read": True,
        "read_at": now,
        "hub_progress": _hub_progress(get_hub(hub_slug), read_map),
    }


@router.delete("/hub/{hub_slug}/article/{article_slug}/read")
async def unmark_read(hub_slug: str, article_slug: str,
                      user: UserPublic = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Undo a read — useful when the user marked it by accident."""
    article = get_article(hub_slug, article_slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    await db[_READS_COLLECTION].delete_one(
        {"user_id": user.user_id, "article_slug": article_slug},
    )
    read_map = await _read_set(db, user.user_id)
    return {
        "ok": True,
        "read": False,
        "hub_progress": _hub_progress(get_hub(hub_slug), read_map),
    }


@router.get("/progress")
async def learning_progress(user: UserPublic = Depends(get_current_user),
                            db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Compact progress payload for the dashboard entry card."""
    read_map = await _read_set(db, user.user_id)
    per_hub = []
    for hub in HUBS:
        p = _hub_progress(hub, read_map)
        per_hub.append({
            "slug": hub["slug"],
            "name": hub["name"],
            "accent": hub["accent"],
            "read": p["read"],
            "total": p["total"],
        })
    total = sum(len(h["articles"]) for h in HUBS)
    return {
        "read_count": len(read_map),
        "total_articles": total,
        "per_hub": per_hub,
        "started": bool(read_map),
    }


# ---------------------------------------------------------------------------
# "Ask the coach for more depth" — Claude expansion per article.
# ---------------------------------------------------------------------------
_COACH_SYSTEM = (
    "You are a neutral co-parenting coach. A parent has just read a short "
    "article and asked you for a little more depth. Write EXACTLY three "
    "short paragraphs (roughly 50-90 words each) that:\n"
    "  Paragraph 1: expand the article's core idea with one concrete example.\n"
    "  Paragraph 2: gently name a common pitfall parents hit when trying it.\n"
    "  Paragraph 3: offer one small, specific practice for THIS week.\n\n"
    "Rules you MUST follow:\n"
    "  1. Neutral, parent-attributed tone. Never take sides in any dispute.\n"
    "  2. Non-diagnostic. Never suggest diagnoses or treatment.\n"
    "  3. Non-adjudicative. Never suggest one parent is right or wrong.\n"
    "  4. No legal, medical, or psychological advice.\n"
    "  5. Plain, warm language — no jargon, no bullet points, no headers.\n"
    "  6. Child-first framing throughout.\n"
    "  7. Return STRICT JSON only, no prose before or after, of the shape: "
    '{"paragraphs": ["...", "...", "..."]}. Exactly three strings.'
)


def _sanitize_expansion(raw: Any) -> Optional[List[str]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            stripped = raw.strip().lstrip("`json").rstrip("`").strip()
            try:
                raw = json.loads(stripped)
            except Exception:  # noqa: BLE001
                return None
    if not isinstance(raw, dict):
        return None
    paras = raw.get("paragraphs")
    if not isinstance(paras, list):
        return None
    out: List[str] = []
    for p in paras:
        if not isinstance(p, (str, int, float)):
            continue
        s = str(p).strip()
        if s:
            out.append(s)
    if len(out) < 2:
        return None
    return out[:3]


@router.post("/hub/{hub_slug}/article/{article_slug}/coach")
async def ai_expansion(hub_slug: str, article_slug: str,
                       body: CoachIn = CoachIn(),
                       user: UserPublic = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:
    """Generate (or return cached) 3-paragraph Claude expansion for the
    given article. Cached forever per user unless `force=true` since the
    underlying seed content is static."""
    article = get_article(hub_slug, article_slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    cache_key = {"user_id": user.user_id, "article_slug": article_slug}
    if not body.force:
        cached = await db[_AI_COLLECTION].find_one(cache_key, {"_id": 0})
        if cached and cached.get("expansion"):
            return {
                "ok": True,
                "expansion": cached["expansion"],
                "cached": True,
                "generated_at": cached.get("generated_at"),
            }

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503,
                            detail="AI coach is not configured. Please try again later.")

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    prompt = (
        f"Article title: {article['title']}\n"
        f"Article summary: {article['summary']}\n\n"
        "Article body:\n"
        f"{article['body']}\n\n"
        'Now write the 3-paragraph expansion. Return STRICT JSON only: '
        '{"paragraphs": ["...", "...", "..."]}'
    )
    try:
        from ai_models import resolve_model
        provider, model_name = resolve_model(None)
        chat = LlmChat(
            api_key=api_key,
            session_id=f"learning-coach-{uuid.uuid4().hex[:10]}",
            system_message=_COACH_SYSTEM,
        ).with_model(provider, model_name)
        text = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:  # noqa: BLE001
        logger.warning("learning coach LLM call failed for %s: %s", article_slug, e)
        raise HTTPException(status_code=503,
                            detail="Coach is briefly unavailable. Try again in a moment.") from e

    paragraphs = _sanitize_expansion(text)
    if not paragraphs:
        logger.warning("learning coach returned unparseable output for %s", article_slug)
        raise HTTPException(status_code=502,
                            detail="Couldn't compose a good expansion this time. Try once more?")

    generated_at = datetime.now(timezone.utc).isoformat()
    await db[_AI_COLLECTION].update_one(
        cache_key,
        {"$set": {
            **cache_key,
            "hub_slug": hub_slug,
            "expansion": {"paragraphs": paragraphs},
            "generated_at": generated_at,
        }},
        upsert=True,
    )
    return {
        "ok": True,
        "expansion": {"paragraphs": paragraphs},
        "cached": False,
        "generated_at": generated_at,
    }


@router.get("/search")
async def search(q: str = "",
                 user: UserPublic = Depends(get_current_user),  # noqa: ARG001
                 db: AsyncIOMotorDatabase = Depends(get_db)) -> Dict[str, Any]:  # noqa: ARG001
    """Simple case-insensitive keyword search across titles + summaries."""
    q = (q or "").strip().lower()
    if not q:
        return {"query": "", "results": []}
    results: List[Dict[str, Any]] = []
    for hub in HUBS:
        for a in hub["articles"]:
            hay = f"{a['title']} {a['summary']} {a['body']}".lower()
            if q in hay:
                results.append({
                    "hub_slug": hub["slug"],
                    "hub_name": hub["name"],
                    "slug": a["slug"],
                    "title": a["title"],
                    "summary": a["summary"],
                    "read_minutes": a["read_minutes"],
                })
    return {"query": q, "results": results}
