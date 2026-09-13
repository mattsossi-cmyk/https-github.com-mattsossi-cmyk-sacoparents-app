"""Admin-gated maintenance endpoints — small, low-frequency
operational actions the platform owner may need to run from the
Emergent UI (no shell required).

Currently exposes:
  * POST /admin/seed-demo-case
        Runs `seed_joint_sample_case.run()` against the CURRENT
        environment's Mongo binding. Produces `SA-DEMO01` with both
        parents auto-accepted. Idempotent — safe to hit repeatedly.
        Requires the caller to be listed in `ADMIN_EMAILS`.
  * POST /admin/consent-digest/run-now
        Force-runs the Monday-morning Child-Needs consent adoption
        digest right now. Defaults to `dry_run=True` (computes stats
        + records dedupe row, no email sent). Pass `?dry_run=false`
        to actually email every `ADMIN_EMAILS` recipient.

Gating uses the existing `require_admin` dependency from
`analytics_routes` so we don't introduce a second admin taxonomy.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from analytics_routes import require_admin
from auth import UserPublic


router = APIRouter(tags=["admin-maintenance"])
logger = logging.getLogger(__name__)


@router.post("/admin/seed-demo-case")
async def admin_seed_demo_case(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Spin up (or refresh) the SA-DEMO01 sample joint case on the
    environment this server is currently bound to. Returns the
    case_id + both parents' user_ids so the caller can paste the
    login credentials into their test-credentials store.

    Safe to hit repeatedly — the seed script uses `$set` + `$setOnInsert`
    so re-running never duplicates rows and preserves the original
    seed timestamp. Never deletes anything.

    Cost warning: if a caller re-runs this after a real production
    parent has already been seeded with `parent1@test.com`, the seed
    will re-assert canonical Foundation prompts on that account. In
    practice `parent1@test.com` is a fixture email, not a real user,
    so this is safe. The dependency uses `require_admin` so only
    platform owners can trigger it.
    """
    try:
        from seed_joint_sample_case import run as run_seed
        result = await run_seed()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Admin seed_demo_case failed")
        raise HTTPException(status_code=500, detail=f"Seed failed: {exc}") from exc
    return {
        "ok": True,
        "case_id": result["case_id"],
        "parent_a": result["parent_a"],
        "parent_b": result["parent_b"],
        "note": (
            "Sign in as parent1@test.com or parent2@test.com "
            "(TestPass123!) to view the joint variant of the Complete "
            "Alignment Report at /complete-alignment-report/joint/SA-DEMO01."
        ),
    }


@router.post("/admin/consent-digest/run-now")
async def admin_run_consent_digest(
    request: Request,
    dry_run: bool = True,
    _admin: UserPublic = Depends(require_admin),
):
    """Force-run the Child-Needs consent adoption digest **right now**,
    bypassing the Monday-morning send window.

    Defaults to `dry_run=True` — the digest is computed and the send
    is dedupe-recorded, but no email is actually dispatched. Pass
    `?dry_run=false` to send the real digest to every `ADMIN_EMAILS`
    recipient.

    Idempotent per (admin_email, ISO week): a second call in the same
    week returns `already_sent_this_week` for each admin instead of
    double-emailing.
    """
    try:
        from consent_adoption_digest import send_consent_adoption_digest
        result = await send_consent_adoption_digest(
            request.app.state.db,
            dry_run=bool(dry_run),
            force_window=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Admin run consent digest failed")
        raise HTTPException(
            status_code=500, detail=f"Digest run failed: {exc}"
        ) from exc
    return result
