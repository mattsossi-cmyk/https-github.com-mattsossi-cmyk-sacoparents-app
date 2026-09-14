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
  * GET /admin/consent-digest/preview.html
        Renders the digest HTML (exactly what would land in the
        Monday inbox) against CURRENT live consent stats. Does NOT
        touch the mailer or write a dedupe row — pure preview.
  * POST /admin/consent-digest/send-test?to_email=you@example.com
        Actually SENDS the digest to an arbitrary recipient with a
        `[TEST]` subject prefix + banner. Bypasses the Monday dedupe
        row so it doesn't affect the real send. Use for eyeballing
        the mobile inbox render before Monday.

Gating uses the existing `require_admin` dependency from
`analytics_routes` so we don't introduce a second admin taxonomy.
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from analytics_routes import require_admin
from auth import UserPublic


router = APIRouter(tags=["admin-maintenance"])
logger = logging.getLogger(__name__)

# Reusable HTML fragment builders — kept module-level so `preview.html`
# and `send-test` share the same visual language without duplication.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_recipient(to_email: str) -> str:
    """Trim + regex-check a recipient email. Raises HTTP 422 on any
    malformed input so the mailer never sees garbage."""
    email = (to_email or "").strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=422, detail="Recipient email is not a valid address.",
        )
    return email


async def _current_digest_stats(
    db: AsyncIOMotorDatabase,
) -> Tuple[dict, str]:
    """Load the joint-alignment cases and compute consent stats for
    the current week. Shared by `preview.html` and `send-test` so
    both routes render numbers from the exact same aggregation."""
    from consent_adoption_digest import (
        _compute_consent_stats,
        _load_all_cases,
        _now_utc,
        _week_start,
    )
    now = _now_utc()
    cases = await _load_all_cases(db)
    stats = _compute_consent_stats(cases, now - timedelta(days=7))
    return stats, _week_start(now)


_PREVIEW_BANNER = (
    '<div style="background:#FFF3D6;border-bottom:2px solid #E5B84E;'
    'color:#7A4D0C;padding:14px 20px;font-family:sans-serif;font-size:14px;">'
    '<strong>PREVIEW · not sent.</strong> '
    'This is the exact HTML the Monday digest for {week_start} '
    'would render right now. Hit '
    '<code style="background:#FFE7A5;padding:1px 6px;border-radius:4px;">'
    'POST /api/admin/consent-digest/run-now?dry_run=false</code> to send it real.'
    '</div>'
)

_TEST_BANNER_HTML = (
    '<div style="background:#FFF3D6;border:2px solid #E5B84E;'
    'color:#7A4D0C;padding:14px 18px;border-radius:12px;'
    'font-size:13px;line-height:1.5;margin:0 0 20px 0;">'
    '<strong>[TEST]</strong> This is a preview of the SA CoParents '
    'consent-adoption Monday digest sent by the app owner. It contains '
    'aggregate telemetry only — no parent names or verbatim answers. '
    'You can safely delete this email.'
    '</div>'
)

_TEST_PLAIN_BANNER = (
    "[TEST] SA CoParents · Consent-adoption Monday digest preview.\n"
    "Aggregate telemetry only — no parent names or verbatim answers.\n"
    "You can safely delete this email.\n\n"
)


def _inject_test_banner(html: str, banner: str) -> str:
    """Insert a `<div>` right after the first `<body ...>` tag so the
    banner is the first visible element in every mail client. Falls
    back to a raw prefix if the marker is missing (defensive — the
    branded HTML template always emits a `<body>`)."""
    idx = html.lower().find("<body")
    if idx == -1:
        return banner + html
    close = html.find(">", idx)
    if close == -1:
        return banner + html
    return html[: close + 1] + banner + html[close + 1 :]


def _wrap_as_test_digest(
    subject: str, html: str, plain: str,
) -> Tuple[str, str, str]:
    """Take the real Monday digest triple and return the TEST variant
    with `[TEST]` prefixes + banners. Pure fn — easy to unit-test."""
    return (
        f"[TEST] {subject}",
        _inject_test_banner(html, _TEST_BANNER_HTML),
        _TEST_PLAIN_BANNER + plain,
    )


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


@router.get("/admin/consent-digest/preview.html")
async def admin_preview_consent_digest_html(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Render the digest HTML in the browser so admins can eyeball
    the layout against CURRENT live consent stats — without touching
    the mailer, without writing a dedupe row, without waiting for
    Monday. Pure preview."""
    from consent_adoption_digest import _admin_console_url
    from email_service import build_admin_consent_adoption_digest_html
    from fastapi.responses import HTMLResponse

    stats, week_start = await _current_digest_stats(request.app.state.db)
    _, html, _ = build_admin_consent_adoption_digest_html(
        stats=stats,
        week_start=week_start,
        console_url=_admin_console_url(),
    )
    # Inject the banner INSIDE `<body>` (same pattern as `send-test`)
    # rather than before the doctype, so it lives inside the rendered
    # page shell not above it.
    banner = _PREVIEW_BANNER.format(week_start=week_start)
    return HTMLResponse(
        _inject_test_banner(html, banner),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/admin/consent-digest/send-test")
async def admin_send_test_consent_digest(
    request: Request,
    to_email: str,
    _admin: UserPublic = Depends(require_admin),
):
    """Send the Monday digest to an arbitrary email address (typically
    the admin's personal inbox on their phone) so they can eyeball
    the mobile render before Monday.

    Never touches the Monday dedupe row — this is a one-off
    send-and-forget. Subject prefixed with `[TEST]` and body carries
    a big banner so it can't be mistaken for a real digest.

    Admin gated. Recipient email must look like a real address —
    same guard we use for real digest recipients.
    """
    from consent_adoption_digest import _admin_console_url
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        _send,
        build_admin_consent_adoption_digest_html,
    )

    email = _validate_recipient(to_email)
    stats, week_start = await _current_digest_stats(request.app.state.db)
    real_subject, real_html, real_plain = build_admin_consent_adoption_digest_html(
        stats=stats,
        week_start=week_start,
        console_url=_admin_console_url(),
    )
    subject, html, plain = _wrap_as_test_digest(real_subject, real_html, real_plain)

    try:
        _send(
            to_email=email,
            subject=subject,
            html=html,
            text=plain,
            failure_message="Could not send the test digest right now.",
        )
    except EmailNotConfigured as exc:
        raise HTTPException(
            status_code=503, detail="Email service is not configured.",
        ) from exc
    except EmailSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True, "to_email": email, "week_start": week_start}



@router.post("/admin/alignment-reflections/send-reminders")
async def admin_send_reflection_reminders(
    request: Request,
    dry_run: bool = True,
    stale_days: int = 3,
    _admin: UserPublic = Depends(require_admin),
):
    """Trigger the reflection reminder sweep (Iter193). Defaults to
    `dry_run=True` — admins should always preview the candidate list
    before firing emails. Pass `?dry_run=false` to actually send.

    Guardrails baked into the sweep itself: safety-sensitive subjects
    are excluded, one reminder per (target_user, coparent_user,
    subject), reflections with no completed answers are skipped.
    """
    from alignment_reflection_reminder import send_reflection_reminders

    result = await send_reflection_reminders(
        request.app.state.db,
        stale_days=max(0, int(stale_days)),
        dry_run=bool(dry_run),
    )
    return result


@router.get("/admin/alignment-reflections/analytics")
async def admin_alignment_reflection_analytics(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Iter194 · aggregate open / click rates on the reminder emails
    so we can prove the sweep lifts the `waiting_on_coparent` →
    `ready` conversion. Per-subject rows + a total summary."""
    from alignment_reflection_analytics import compute_reminder_analytics
    return await compute_reminder_analytics(request.app.state.db)

