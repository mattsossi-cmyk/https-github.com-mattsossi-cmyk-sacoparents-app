"""Silent-Reviewer Nudge — daily sweep that emails the sending parent
when a Joint Report or Joint Agreement share they emailed to a
professional hasn't been opened after N days.

Design choices worth recording:
  * We nudge the *parent*, not the professional. The parent chose the
    share, holds the audit relationship, and can decide whether to
    re-send from their dashboard. Auto-emailing the professional
    directly risks feeling like spam.
  * Idempotent: each `share_tokens` row is nudged at most once ever.
    A `nudged_at` timestamp is written on first send; subsequent
    sweeps skip rows already carrying it.
  * Only tokens created by the email flow are candidates — we key off
    the `label` prefix "Emailed to " (set in
    `joint_agreement_routes` / `joint_professional_report_routes`).
    Manually-minted share links from the "Get shareable link" dialog
    are excluded because parents opted-in to hand those out
    themselves.
  * A share counts as unread iff `phi_access_log` has zero rows with
    action=`external_read_via_share_link` for that jti.
  * The sweep never nudges a token that is revoked or already expired.

Env flags:
  * SILENT_REVIEWER_NUDGE_ENABLED (default off) — set to "1" to run.
  * SILENT_REVIEWER_NUDGE_AFTER_DAYS (default 3) — how quiet is quiet.
  * SILENT_REVIEWER_NUDGE_SWEEP_SECONDS (default 3600) — sweep cadence.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)


_SHARE_COLLECTION = "share_tokens"
_PHI_COLLECTION = "phi_access_log"
_JOINT_REPORT_EMAILS = "joint_report_emails"
_JOINT_AGREEMENT_EMAILS = "joint_agreement_emails"


_ARTEFACT_LABELS = {
    "joint_report":     "Joint Co-Parenting Summary for Professional Review",
    "joint_agreement":  "Co-Parenting Agreement",
}
_EMAIL_COLLECTIONS = {
    "joint_report":    _JOINT_REPORT_EMAILS,
    "joint_agreement": _JOINT_AGREEMENT_EMAILS,
}


def _enabled() -> bool:
    return (os.environ.get("SILENT_REVIEWER_NUDGE_ENABLED") or "").strip() in {
        "1", "true", "yes", "on",
    }


def _after_days() -> int:
    try:
        return max(1, int(os.environ.get("SILENT_REVIEWER_NUDGE_AFTER_DAYS", "3")))
    except (TypeError, ValueError):
        return 3


def _sweep_interval_s() -> int:
    try:
        return max(60, int(os.environ.get("SILENT_REVIEWER_NUDGE_SWEEP_SECONDS", "3600")))
    except (TypeError, ValueError):
        return 3600


def _app_url() -> str:
    return (os.environ.get("PUBLIC_APP_URL") or "https://sacoparentsapp.online").rstrip("/")


async def _has_been_opened(db: AsyncIOMotorDatabase, jti: str) -> bool:
    """Cheap existence check against the aggregate audit log."""
    doc = await db[_PHI_COLLECTION].find_one(
        {"jti": jti, "action": "external_read_via_share_link"},
        {"_id": 1},
    )
    return doc is not None


async def _recipient_for(
    db: AsyncIOMotorDatabase, doc_type: str, share_id: str, user_id: str, jti: str,
) -> Optional[Dict[str, Any]]:
    """Look up the email-send record matching a specific share token so
    we can personalise the nudge with the recipient's name/role."""
    coll = _EMAIL_COLLECTIONS.get(doc_type)
    if not coll:
        return None
    # Prefer an exact match on preview_jti (added iter126+); fall back to
    # newest send for the same share_id/user_id if the row was written
    # before that column existed.
    row = await db[coll].find_one(
        {"preview_jti": jti, "user_id": user_id, "share_id": share_id},
        {"_id": 0},
    )
    if row:
        return row
    return await db[coll].find_one(
        {"user_id": user_id, "share_id": share_id},
        {"_id": 0}, sort=[("sent_at", -1)],
    )


async def _load_user_email(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    return await db["users"].find_one(
        {"user_id": user_id}, {"_id": 0, "email": 1, "name": 1},
    )


def _recipient_display(row: Optional[Dict[str, Any]]) -> str:
    if not row:
        return "your recipient"
    name = (row.get("recipient_name") or "").strip()
    email = (row.get("to_email") or "").strip()
    if name and email:
        return f"{name} ({email})"
    return name or email or "your recipient"


async def _iter_candidates(
    db: AsyncIOMotorDatabase, now: datetime, after_days: int,
) -> List[Dict[str, Any]]:
    """Return share_tokens rows eligible for a nudge on this sweep."""
    cutoff = (now - timedelta(days=after_days)).isoformat()
    cursor = db[_SHARE_COLLECTION].find(
        {
            "doc_type": {"$in": list(_ARTEFACT_LABELS.keys())},
            "revoked_at": None,
            "nudged_at": {"$in": [None]},
            # Only tokens minted via the /email endpoint carry the
            # "Emailed to <address>" label. Manual /share-link tokens
            # never get nudged.
            "label": {"$regex": "^Emailed to "},
            "created_at": {"$lte": cutoff},
        },
        {"_id": 0},
    )
    return [row async for row in cursor]


async def _mark_nudged(db: AsyncIOMotorDatabase, jti: str, iso_ts: str) -> None:
    await db[_SHARE_COLLECTION].update_one(
        {"jti": jti}, {"$set": {"nudged_at": iso_ts}},
    )


async def send_silent_reviewer_nudges(
    db: AsyncIOMotorDatabase,
    *,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """One sweep pass. Returns per-token result dicts so an operator
    preview endpoint (future) or tests can inspect what would fire."""
    from email_service import send_silent_reviewer_nudge, EmailNotConfigured, EmailSendError

    now = now or datetime.now(timezone.utc)
    after_days = _after_days()
    results: List[Dict[str, Any]] = []
    candidates = await _iter_candidates(db, now, after_days)

    for row in candidates:
        jti = row.get("jti")
        doc_type = row.get("doc_type")
        share_id = row.get("doc_id")
        user_id = row.get("user_id")
        if not (jti and doc_type and share_id and user_id):
            continue
        # Expiry guard — if the token is already dead we skip so the
        # parent never gets a "your link is invalid" surprise after
        # tapping the CTA.
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                if datetime.fromisoformat(expires_at) < now:
                    results.append({"jti": jti, "status": "expired"})
                    continue
            except ValueError:
                pass

        if await _has_been_opened(db, jti):
            # Backfill nudged_at so we skip it forever without needing
            # to re-check the audit log every sweep.
            if not dry_run:
                await _mark_nudged(db, jti, now.isoformat())
            results.append({"jti": jti, "status": "already_opened"})
            continue

        user = await _load_user_email(db, user_id)
        if not user or not (user.get("email") or "").strip():
            results.append({"jti": jti, "status": "no_parent_email"})
            continue
        parent_email = user["email"].strip()
        if parent_email.endswith("@demo.local"):
            results.append({"jti": jti, "status": "demo_email_skipped"})
            continue

        recipient = await _recipient_for(db, doc_type, share_id, user_id, jti)
        artefact_label = _ARTEFACT_LABELS[doc_type]
        # Compute the age in days for the copy.
        try:
            created_at = datetime.fromisoformat(row.get("created_at") or "")
        except (ValueError, TypeError):
            created_at = now - timedelta(days=after_days)
        days_since = max(1, int((now - created_at).total_seconds() // 86400))

        share_page_url = f"{_app_url()}/dashboard"

        if dry_run:
            results.append({
                "jti": jti, "status": "would_send",
                "to": parent_email, "days_since": days_since,
                "recipient_display": _recipient_display(recipient),
                "artefact_label": artefact_label,
            })
            continue

        try:
            send_silent_reviewer_nudge(
                to_email=parent_email,
                parent_name=(user.get("name") or "").strip(),
                recipient_display=_recipient_display(recipient),
                artefact_label=artefact_label,
                share_page_url=share_page_url,
                days_since_sent=days_since,
            )
        except (EmailNotConfigured, EmailSendError) as e:
            log.warning("silent-reviewer nudge send failed for jti=%s: %s", jti, e)
            results.append({"jti": jti, "status": "send_failed"})
            continue

        await _mark_nudged(db, jti, now.isoformat())
        # Audit the nudge on the parent's PHI-access history — this is
        # a disclosure trigger they should be able to see later.
        try:
            from phi_access_routes import record_phi_access
            await record_phi_access(
                db, user_id=user_id, action="silent_reviewer_nudge",
                resource_type=doc_type, share_id=share_id, jti=jti,
            )
        except Exception:  # noqa: BLE001
            log.exception("phi audit for silent-reviewer nudge failed")

        results.append({"jti": jti, "status": "nudged", "to": parent_email})

    return results


async def silent_reviewer_nudge_loop(app) -> None:
    """Long-running sweep task started from server.py. No-ops when the
    feature is not enabled via env var so the loop stays safe to
    always register."""
    if not _enabled():
        log.info("silent_reviewer_nudge_loop: SILENT_REVIEWER_NUDGE_ENABLED not set; idle")
        while True:
            await asyncio.sleep(3600)
    await asyncio.sleep(180)  # small warmup so DB is ready
    while True:
        try:
            db = app.state.db
            results = await send_silent_reviewer_nudges(db)
            nudged = sum(1 for r in results if r["status"] == "nudged")
            if nudged:
                log.info("silent-reviewer nudge sweep: %d nudge(s) sent", nudged)
        except Exception:  # noqa: BLE001
            log.exception("silent-reviewer nudge sweep failed; will retry")
        await asyncio.sleep(_sweep_interval_s())
