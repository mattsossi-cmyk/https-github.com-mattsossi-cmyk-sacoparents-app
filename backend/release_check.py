"""Post-release smoke check: the live app checks its own key pages and PDFs and emails admins on failure."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

RUNS = "release_checks"
STATE = "release_check_state"
BOOT_DELAY_S = 90
BOOT_RETRY_S = 90
BOOT_THROTTLE = timedelta(minutes=10)
ALERT_COOLDOWN = timedelta(hours=12)
PREVIEW_HOST = "preview.emergentagent.com"

Result = Tuple[bool, str]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def origin_from_request(request) -> str:
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    return f"{proto}://{host}"


async def remember_origin(db: AsyncIOMotorDatabase, origin: str) -> None:
    host = origin.split("://", 1)[-1]
    if not host or host.startswith(("localhost", "127.", "0.0.0.0")):
        return
    await db[STATE].update_one({"_id": "origin"}, {"$set": {"url": origin, "at": _now().isoformat()}}, upsert=True)


def _sa_sample() -> Dict[str, Any]:
    from self_assessment_routes import CONTENT
    answers = {f"{s['key']}_{i + 1}": 3 for s in CONTENT["sections"] for i in range(len(s["questions"]))}
    return {"entry": {"parent_name": "Release Check", "answers": answers}}


CN_SAMPLE = {"parent_name": "Release Check", "answers": {"medical": {"med_provider": "Sample clinic"}}}
FB_SAMPLE = {"fields": {"parent_names": "Release Check", "core_goals": "Sample statement used by the automatic release check."}}


async def _page(client: httpx.AsyncClient, url: str) -> Result:
    r = await client.get(url)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    ok = 'id="root"' in r.text
    return ok, "OK" if ok else "Page loaded but the app shell was missing"


async def _bundle(client: httpx.AsyncClient, base: str) -> Result:
    html = (await client.get(base + "/")).text
    srcs = re.findall(r'<script[^>]+src="([^"]+\.js)"', html)
    if not srcs:
        return False, "No app script found on the home page"
    for src in srcs:
        r = await client.get(src if src.startswith("http") else base + src)
        if r.status_code != 200 or len(r.content) < 1000:
            return False, f"{src} returned HTTP {r.status_code}"
    return True, f"{len(srcs)} script file(s) loaded"


async def _api(client: httpx.AsyncClient, base: str) -> Result:
    r = await client.get(base + "/api/health")
    return r.status_code == 200, "OK" if r.status_code == 200 else f"HTTP {r.status_code}"


async def _pdf(client: httpx.AsyncClient, url: str, payload: Dict[str, Any]) -> Result:
    r = await client.post(url, json=payload)
    ok = r.status_code == 200 and r.content[:4] == b"%PDF"
    return ok, f"{len(r.content) // 1024} KB PDF" if ok else f"HTTP {r.status_code}"


async def _mediator_pdf() -> Result:
    import cp_progress_pdf
    progress = {
        "snapshots": [{}, {}],
        "recent": {"overall_rating": "Good", "section_avgs": []},
        "overall_series": [
            {"submitted_at": "2026-01-05T10:00:00+00:00", "value": 2.4, "rating": "Fair"},
            {"submitted_at": "2026-03-05T10:00:00+00:00", "value": 3.1, "rating": "Good"},
        ],
    }
    out = await asyncio.to_thread(cp_progress_pdf.build_progress_pdf, parent_name="Release Check", progress=progress)
    return out[:4] == b"%PDF", f"{len(out) // 1024} KB PDF"


def _checks(client: httpx.AsyncClient, base: str) -> List[Tuple[str, Callable[[], Awaitable[Result]]]]:
    return [
        ("Home page", lambda: _page(client, base + "/")),
        ("Login page", lambda: _page(client, base + "/login")),
        ("Dashboard page", lambda: _page(client, base + "/dashboard")),
        ("App code", lambda: _bundle(client, base)),
        ("Backend API", lambda: _api(client, base)),
        ("Card 1 Self-Assessment PDF", lambda: _pdf(client, base + "/api/self-assessment/pdf", _sa_sample())),
        ("Card 3 Child's Specific Needs PDF", lambda: _pdf(client, base + "/api/child-needs/pdf", CN_SAMPLE)),
        ("Card 4 Foundation Statement PDF", lambda: _pdf(client, base + "/api/foundation-builder/pdf", FB_SAMPLE)),
        ("Mediator Progress PDF", _mediator_pdf),
    ]


async def _timed(name: str, fn: Callable[[], Awaitable[Result]]) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        ok, detail = await fn()
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc}"[:200]
    return {"name": name, "ok": bool(ok), "detail": detail, "ms": int((time.monotonic() - t0) * 1000)}


async def run_release_check(
    db: AsyncIOMotorDatabase, *, base_url: str, trigger: str, alert: bool = True,
) -> Dict[str, Any]:
    base = base_url.rstrip("/")
    started = _now()
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        results = [await _timed(name, fn) for name, fn in _checks(client, base)]
    doc = {
        "id": str(uuid.uuid4()),
        "trigger": trigger,
        "base_url": base,
        "started_at": started.isoformat(),
        "finished_at": _now().isoformat(),
        "ok": all(r["ok"] for r in results),
        "results": results,
        "alerted": False,
    }
    if not doc["ok"] and alert:
        doc["alerted"] = await _maybe_alert(db, doc)
    await db[RUNS].insert_one(dict(doc))
    logger.info("release-check trigger=%s base=%s ok=%s", trigger, base, doc["ok"])
    return doc


async def _maybe_alert(db: AsyncIOMotorDatabase, doc: Dict[str, Any]) -> bool:
    prev = await db[RUNS].find_one({}, {"_id": 0, "ok": 1}, sort=[("started_at", -1)])
    state = await db[STATE].find_one({"_id": "alert"}) or {}
    last = state.get("at")
    if prev and not prev.get("ok") and last and datetime.fromisoformat(last) > _now() - ALERT_COOLDOWN:
        return False
    from analytics_routes import ADMIN_EMAILS
    from email_service import send_release_check_alert
    failures = [r for r in doc["results"] if not r["ok"]]
    sent = False
    for to in sorted(ADMIN_EMAILS):
        try:
            await asyncio.to_thread(
                send_release_check_alert, to_email=to, base_url=doc["base_url"],
                trigger=doc["trigger"], failures=failures, total=len(doc["results"]),
            )
            sent = True
        except Exception:  # noqa: BLE001
            logger.exception("release-check alert to %s failed", to)
    if sent:
        await db[STATE].update_one({"_id": "alert"}, {"$set": {"at": _now().isoformat()}}, upsert=True)
    return sent


async def _claim_boot_slot(db: AsyncIOMotorDatabase) -> bool:
    now = _now()
    try:
        await db[STATE].update_one(
            {"_id": "boot", "at": {"$lt": (now - BOOT_THROTTLE).isoformat()}},
            {"$set": {"at": now.isoformat()}},
            upsert=True,
        )
        return True
    except DuplicateKeyError:
        return False


async def post_boot_release_check(app) -> None:
    """Runs once shortly after each backend start (i.e. after every release)."""
    await asyncio.sleep(BOOT_DELAY_S)
    try:
        db = app.state.db
        state = await db[STATE].find_one({"_id": "origin"}) or {}
        base: Optional[str] = state.get("url") or (os.environ.get("PUBLIC_APP_URL") or "").strip()
        if not base or PREVIEW_HOST in base or not await _claim_boot_slot(db):
            return
        doc = await run_release_check(db, base_url=base, trigger="release", alert=False)
        if not doc["ok"]:
            await asyncio.sleep(BOOT_RETRY_S)
            await run_release_check(db, base_url=base, trigger="release", alert=True)
    except Exception:  # noqa: BLE001
        logger.exception("post-boot release check failed")
