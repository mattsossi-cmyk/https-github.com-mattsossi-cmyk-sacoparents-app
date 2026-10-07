"""Platform cron webhook endpoints — iter223.

Handlers for the schedules declared in ``.emergent/crons.yml``. Each
endpoint:

* reads ``WEBHOOK_CRON_SECRET`` from backend env
* verifies ``Authorization: Bearer <secret>`` in constant time
* enqueues the real work as a background task
* returns 2xx immediately (< 5 s bound enforced by the dispatcher)
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request

from auth import get_db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cron", tags=["cron"])


def _cron_secret() -> str:
    return (os.environ.get("WEBHOOK_CRON_SECRET") or "").strip()


def _verify_cron_auth(authorization: Optional[str]) -> None:
    secret = _cron_secret()
    if not secret:
        # If the platform secret isn't configured, refuse every call
        # rather than leak an accidentally-open cron endpoint.
        raise HTTPException(status_code=401, detail="cron secret not configured")
    provided = ""
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization.split(None, 1)[1].strip()
    if not provided or not hmac.compare_digest(provided, secret):
        raise HTTPException(status_code=401, detail="invalid cron auth")


@router.post("/guided-draft-nudge")
async def guided_draft_nudge_cron(
    background: BackgroundTasks,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Weekly nudge to parents with stale Guided Journey drafts.

    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    """
    _verify_cron_auth(authorization)

    # Idempotency key — dispatcher provides X-Webhook-Id. We don't
    # need to hard-block dupes here because the underlying sweep uses
    # a per-parent-per-week dedupe collection.
    run_id = request.headers.get("X-Webhook-Id") or "manual"

    from guided_draft_nudge import send_guided_draft_nudges

    portal_url = os.environ.get("PORTAL_PUBLIC_URL") or None

    async def _run() -> None:
        try:
            stats = await send_guided_draft_nudges(db, portal_url=portal_url)
            logger.info(
                "guided-draft-nudge cron run_id=%s stats=%s", run_id, stats
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "guided-draft-nudge cron run_id=%s failed: %s", run_id, exc
            )

    background.add_task(_run)
    return {"ok": True, "run_id": run_id, "enqueued": "guided-draft-nudge"}


@router.post("/nudge-digest")
async def nudge_digest_cron(
    background: BackgroundTasks,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Weekly admin digest of last week's Guided Journey nudge batch.

    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    """
    _verify_cron_auth(authorization)
    run_id = request.headers.get("X-Webhook-Id") or "manual"

    from guided_draft_digest import send_nudge_digest

    async def _run() -> None:
        try:
            stats = await send_nudge_digest(db)
            logger.info(
                "nudge-digest cron run_id=%s stats=%s", run_id, stats
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "nudge-digest cron run_id=%s failed: %s", run_id, exc
            )

    background.add_task(_run)
    return {"ok": True, "run_id": run_id, "enqueued": "nudge-digest"}


@router.post("/self-assessment-reminders")
async def self_assessment_reminders_cron(
    background: BackgroundTasks,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Daily sweep: 6-week reassess email + 8-week follow-up (safety-flagged skipped).

    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    """
    _verify_cron_auth(authorization)
    # Dedupe lives in `self_assessment_reminders` (one sent row per entry + kind).
    run_id = request.headers.get("X-Webhook-Id") or "manual"

    from self_assessment_reminders import send_reassess_reminders

    async def _run() -> None:
        try:
            stats = await send_reassess_reminders(db)
            logger.info("self-assessment-reminders cron run_id=%s stats=%s", run_id, stats)
        except Exception as exc:  # noqa: BLE001
            logger.exception("self-assessment-reminders cron run_id=%s failed: %s", run_id, exc)

    background.add_task(_run)
    return {"ok": True, "run_id": run_id, "enqueued": "self-assessment-reminders"}


@router.post("/release-check")
async def release_check_cron(
    background: BackgroundTasks,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Daily smoke check of key pages + PDFs on the live app; emails admins on failure.

    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    """
    _verify_cron_auth(authorization)
    run_id = request.headers.get("X-Webhook-Id") or "manual"

    from release_check import origin_from_request, remember_origin, run_release_check

    origin = origin_from_request(request)
    await remember_origin(db, origin)

    async def _run() -> None:
        try:
            await run_release_check(db, base_url=origin, trigger="daily")
        except Exception as exc:  # noqa: BLE001
            logger.exception("release-check cron run_id=%s failed: %s", run_id, exc)

    background.add_task(_run)
    return {"ok": True, "run_id": run_id, "enqueued": "release-check"}
