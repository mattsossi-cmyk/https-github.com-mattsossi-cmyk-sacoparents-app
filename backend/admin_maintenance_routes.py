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


@router.get("/admin/consent-digest/preview.html")
async def admin_preview_consent_digest_html(
    request: Request,
    _admin: UserPublic = Depends(require_admin),
):
    """Render the digest HTML in the browser so admins can eyeball
    the layout against CURRENT live consent stats — without touching
    the mailer, without writing a dedupe row, without waiting for
    Monday. Pure preview.

    Same body an admin would receive on Monday morning; the top
    "PREVIEW" banner tells them nothing was actually sent."""
    from datetime import timedelta
    from consent_adoption_digest import (
        _admin_console_url,
        _compute_consent_stats,
        _load_all_cases,
        _now_utc,
        _week_start,
    )
    from email_service import build_admin_consent_adoption_digest_html
    from fastapi.responses import HTMLResponse

    now = _now_utc()
    cases = await _load_all_cases(request.app.state.db)
    stats = _compute_consent_stats(cases, now - timedelta(days=7))
    week_start = _week_start(now)
    _, html, _ = build_admin_consent_adoption_digest_html(
        stats=stats,
        week_start=week_start,
        console_url=_admin_console_url(),
    )

    # Prepend a big yellow "PREVIEW" banner so a screenshot of this
    # page can never be confused with a real digest.
    banner = (
        '<div style="background:#FFF3D6;border-bottom:2px solid #E5B84E;'
        'color:#7A4D0C;padding:14px 20px;font-family:sans-serif;font-size:14px;">'
        '<strong>PREVIEW · not sent.</strong> '
        f'This is the exact HTML the Monday digest for {week_start} '
        'would render right now. Hit '
        '<code style="background:#FFE7A5;padding:1px 6px;border-radius:4px;">'
        'POST /api/admin/consent-digest/run-now?dry_run=false</code> to send it real.'
        '</div>'
    )
    return HTMLResponse(banner + html, headers={"Cache-Control": "no-store"})


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
    import re
    from datetime import timedelta

    from consent_adoption_digest import (
        _admin_console_url,
        _compute_consent_stats,
        _load_all_cases,
        _now_utc,
        _week_start,
    )
    from email_service import (
        EmailNotConfigured,
        EmailSendError,
        _branded_html,
        _send,
        build_admin_consent_adoption_digest_html,
    )

    email = (to_email or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(
            status_code=422, detail="Recipient email is not a valid address.",
        )

    now = _now_utc()
    cases = await _load_all_cases(request.app.state.db)
    stats = _compute_consent_stats(cases, now - timedelta(days=7))
    week_start = _week_start(now)
    real_subject, real_html, real_plain = build_admin_consent_adoption_digest_html(
        stats=stats,
        week_start=week_start,
        console_url=_admin_console_url(),
    )
    # Prepend a bright TEST banner to the HTML body inside the branded
    # shell. We rebuild the branded HTML via `_branded_html` so the
    # banner lives INSIDE the outer layout (not outside), and screenshots
    # can't crop it away.
    test_banner_html = (
        '<div style="background:#FFF3D6;border:2px solid #E5B84E;'
        'color:#7A4D0C;padding:14px 18px;border-radius:12px;'
        'font-size:13px;line-height:1.5;margin:0 0 20px 0;">'
        '<strong>[TEST]</strong> This is a preview of the SA CoParents '
        'consent-adoption Monday digest sent by the app owner. It contains '
        'aggregate telemetry only — no parent names or verbatim answers. '
        'You can safely delete this email.'
        '</div>'
    )
    # Extract the body_html section from build_admin_...html by rebuilding
    # it via the same helper. To keep this simple, we prepend the banner
    # to the final `html` string. `_branded_html`'s output already wraps
    # everything in a table cell — the banner ends up first-child of the
    # body which is visually correct on every mail client we care about.
    html = real_html.replace("<body", "<body", 1)  # noop, keep as-is
    # Insert banner right after the first `<body>` tag so it lands at the
    # top of the visible email content. Fall back to a plain prefix if
    # the `<body>` marker isn't found (shouldn't happen but defensive).
    body_marker = "<body"
    idx = html.lower().find(body_marker)
    if idx != -1:
        # Find the end of the `<body ...>` tag.
        close = html.find(">", idx)
        if close != -1:
            html = html[: close + 1] + test_banner_html + html[close + 1 :]
        else:
            html = test_banner_html + html
    else:
        html = test_banner_html + html

    plain = (
        "[TEST] SA CoParents · Consent-adoption Monday digest preview.\n"
        "Aggregate telemetry only — no parent names or verbatim answers.\n"
        "You can safely delete this email.\n\n"
        f"{real_plain}"
    )
    subject = f"[TEST] {real_subject}"

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
