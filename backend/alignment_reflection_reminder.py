"""Alignment Reflection Reminder Sweep — Iter193.

Nudges the co-parent of any parent who has completed reflection
answers on a subject but whose co-parent has not started that same
subject in 3+ days.

Design:
  * The sweep is a pure Python function `send_reflection_reminders()`.
    Any cron / scheduler / admin trigger can invoke it. This module
    NEVER schedules itself — deployment ops owns cadence.
  * We identify co-parents through the same `snc2_shares` /
    `compare_shares` collections the joint-agreement flow already
    uses (see `joint_professional_report_routes::_find_active_share`).
    A parent's "co-parent" for a subject is the other participant of
    any ACTIVE share they belong to.
  * Every (parent_user_id, coparent_user_id, subject) reminder is
    sent at most ONCE, tracked in `alignment_reflection_reminders`.
  * Safety-sensitive subjects are excluded from the sweep — Safety
    reflections require an explicit dual-consent ceremony and must
    never be surfaced through automated nudges.

Return payload (per invocation):
  {
    "sent":      [ {to, subject, coparent_id, ...}, ... ],
    "skipped":   [ {reason, ...}, ... ],
    "candidate_count": N,
    "sent_count": M,
  }

Kept dry-run-friendly via the `dry_run=True` param so admins can
inspect what WOULD be sent before flipping it live.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from alignment_reflection_questions import (
    SUBJECTS,
    is_sensitive_subject,
    prompts_for,
)


logger = logging.getLogger(__name__)

REMINDER_COLL = "alignment_reflection_reminders"
REFLECTION_COLL = "alignment_reflections"

# 3-day grace period matches the user's spec: give parents time to
# breathe after a partner completes a subject before nudging.
DEFAULT_STALE_DAYS = 3

# Share collections in the same priority order used by the joint
# report / joint agreement flow so the reminder pipeline behaves
# consistently with what parents already see on the dashboard.
_SHARE_COLLECTIONS = ("snc2_shares", "compare_shares")


def _reflection_reminder_email_html(
    *,
    coparent_display: str,
    subject_label: str,
    click_url: str,
    open_pixel_url: Optional[str] = None,
) -> str:
    """Neutral reminder body — never names WHO completed the
    reflection (removes the emotional 'they beat me to it' pressure).
    Focuses on the child + the format ("Ten neutral sections. Your
    voice.").

    Optional `open_pixel_url` embeds a transparent 1x1 tracker so
    analytics can compute open rate. `click_url` wraps the CTA in a
    tracked redirect."""
    pixel_tag = (
        f'<img src="{open_pixel_url}" alt="" width="1" height="1" '
        f'style="display:block;border:0" />'
        if open_pixel_url else ""
    )
    return f"""
    <p>Hi,</p>
    <p>
      A short heads-up from SA CoParents: your co-parent finished the
      <strong>{subject_label}</strong> reflection a few days ago. The
      Joint Alignment Report is waiting on your answers to the same
      six child-focused prompts before it can be generated.
    </p>
    <p>
      There's no rush — take it at your own pace. The prompts take
      about ten minutes to complete. Nothing is shared with
      {coparent_display} until you save your answers.
    </p>
    <p>
      <a href="{click_url}" style="display:inline-block;background:#3D1A78;color:#fff;padding:10px 18px;border-radius:9999px;text-decoration:none;font-weight:600">
        Finish the {subject_label} reflection
      </a>
    </p>
    <p style="color:#4B4567;font-size:13px">
      Ten neutral sections. Your voice. Your child. Alignment before
      agreement.
    </p>
    {pixel_tag}
    """


def _reflection_reminder_email_text(
    *,
    coparent_display: str,
    subject_label: str,
    click_url: str,
) -> str:
    return (
        f"Hi,\n\n"
        f"A short heads-up from SA CoParents: your co-parent finished the "
        f"{subject_label} reflection a few days ago. The Joint Alignment "
        f"Report is waiting on your answers to the same six child-focused "
        f"prompts before it can be generated.\n\n"
        f"There's no rush — take it at your own pace. The prompts take "
        f"about ten minutes to complete. Nothing is shared with "
        f"{coparent_display} until you save your answers.\n\n"
        f"Finish here: {click_url}\n\n"
        f"Ten neutral sections. Your voice. Your child. "
        f"Alignment before agreement.\n"
    )


def _reflect_url(subject: str) -> str:
    """Build the deep link into the reflection form. Falls back to
    the sacoparents.com root when the frontend base isn't set."""
    base = (
        os.environ.get("PUBLIC_APP_URL")
        or os.environ.get("FRONTEND_URL")
        or "https://sacoparents.com"
    ).rstrip("/")
    return f"{base}/alignment/reflect/{subject}"


async def _load_active_shares(
    db: AsyncIOMotorDatabase, user_id: str,
) -> List[Dict[str, Any]]:
    """Return every ACTIVE share the parent is a participant in,
    across all supported share collections. Mirrors
    `_find_active_share`'s two-shape handling so the reminder
    pipeline never misses a valid co-parent link."""
    out: List[Dict[str, Any]] = []
    for coll in _SHARE_COLLECTIONS:
        try:
            cursor = db[coll].find({
                "$or": [
                    {"user_pair": user_id},
                    {"creator_user_id": user_id},
                    {"partner_user_id": user_id},
                ],
            })
            rows = await cursor.to_list(length=None)
        except Exception:  # noqa: BLE001
            continue
        for row in rows:
            pair = list(row.get("user_pair") or [])
            if not pair:
                creator = row.get("creator_user_id")
                partner = row.get("partner_user_id")
                pair = [x for x in (creator, partner) if x]
            if user_id not in pair or len(pair) != 2:
                continue
            is_active = (row.get("status") == "active") or (
                bool(row.get("creator_consent"))
                and bool(row.get("partner_consent"))
                and row.get("status") != "revoked"
            )
            if not is_active:
                continue
            row["_user_pair"] = pair
            out.append(row)
    return out


async def _has_started_subject(
    db: AsyncIOMotorDatabase, user_id: str, subject: str,
) -> bool:
    """True when the parent has at least one non-empty answer for
    the subject. Used to determine whether the co-parent has "not
    yet started" — a submitted-but-blank doc still counts as not
    started (they saved by accident or wiped their answers)."""
    doc = await db[REFLECTION_COLL].find_one(
        {"user_id": user_id, "subject": subject}, {"answers": 1},
    )
    if not doc:
        return False
    for v in (doc.get("answers") or {}).values():
        if (v or "").strip():
            return True
    return False


async def _reminder_already_sent(
    db: AsyncIOMotorDatabase, coparent_id: str, target_id: str, subject: str,
) -> bool:
    doc = await db[REMINDER_COLL].find_one({
        "target_user_id":  target_id,
        "coparent_user_id": coparent_id,
        "subject":         subject,
    })
    return bool(doc)


async def _record_reminder(
    db: AsyncIOMotorDatabase,
    *, target_id: str, target_email: str, coparent_id: str, subject: str,
) -> Any:
    """Iter194 · returns the inserted ObjectId so the caller can
    embed it in the tracking pixel + click wrapper URLs."""
    doc = {
        "target_user_id":   target_id,
        "target_email":     target_email,
        "coparent_user_id": coparent_id,
        "subject":          subject,
        "sent_at":          datetime.now(timezone.utc),
    }
    res = await db[REMINDER_COLL].insert_one(doc)
    return res.inserted_id


def _api_base_url() -> str:
    """Public API base for the tracking pixel / click wrapper. The
    reminder email lives OUTSIDE the SPA — needs a fully-qualified
    URL, not a relative path."""
    api = (
        os.environ.get("PUBLIC_API_URL")
        or os.environ.get("REACT_APP_BACKEND_URL")
        or os.environ.get("PUBLIC_APP_URL")
        or "https://sacoparents.com"
    )
    return api.rstrip("/")


async def send_reflection_reminders(
    db: AsyncIOMotorDatabase,
    *,
    stale_days: int = DEFAULT_STALE_DAYS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Sweep every recently-updated reflection and nudge the
    co-parent when they haven't started that subject.

    Args:
        stale_days: minimum age (days) of the completed reflection
            before the reminder fires. Prevents piling on parents
            hours after their partner saves.
        dry_run: when True, no emails are sent and no reminders are
            recorded — the return payload lists the candidates only.

    Returns a dict with `sent` / `skipped` / counts.
    """
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(days=stale_days)

    # Load every reflection last touched at least `stale_days` ago.
    # We compare `updated_at` not `created_at` — a parent who tweaks
    # their answers is still an active participant.
    cursor = db[REFLECTION_COLL].find(
        {"updated_at": {"$lte": stale_before}},
    )
    completed = await cursor.to_list(length=None)

    sent: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for doc in completed:
        subject = doc.get("subject")
        if not subject or not SUBJECTS.get(subject):
            skipped.append({"reason": "unknown_subject", "subject": subject})
            continue
        # Never nudge on safety-sensitive subjects.
        if is_sensitive_subject(subject):
            skipped.append({
                "reason": "safety_sensitive_subject", "subject": subject,
            })
            continue
        # Doc must contain at least one non-empty answer to count as
        # "completed enough to nudge on" — never nudge on a blank
        # save.
        answers = doc.get("answers") or {}
        if not any((v or "").strip() for v in answers.values()):
            skipped.append({
                "reason": "no_completed_answers", "subject": subject,
                "user_id": doc.get("user_id"),
            })
            continue

        parent_id = doc.get("user_id")
        if not parent_id:
            skipped.append({"reason": "orphan_reflection", "subject": subject})
            continue

        shares = await _load_active_shares(db, parent_id)
        if not shares:
            skipped.append({
                "reason": "no_active_share", "subject": subject,
                "user_id": parent_id,
            })
            continue

        for share in shares:
            pair = share["_user_pair"]
            coparent_id = next((u for u in pair if u != parent_id), None)
            if not coparent_id:
                continue
            # Already reminded for this triple?
            if await _reminder_already_sent(db, parent_id, coparent_id, subject):
                skipped.append({
                    "reason": "already_sent", "subject": subject,
                    "target_user_id": coparent_id,
                })
                continue
            # Co-parent already has answers?
            if await _has_started_subject(db, coparent_id, subject):
                skipped.append({
                    "reason": "coparent_already_started", "subject": subject,
                    "target_user_id": coparent_id,
                })
                continue

            # Resolve co-parent's email + display name.
            coparent_user = await db.users.find_one(
                {"user_id": coparent_id},
                {"email": 1, "name": 1, "_id": 0},
            )
            if not coparent_user or not coparent_user.get("email"):
                skipped.append({
                    "reason": "coparent_email_unknown",
                    "target_user_id": coparent_id,
                })
                continue

            parent_user = await db.users.find_one(
                {"user_id": parent_id},
                {"name": 1, "email": 1, "_id": 0},
            )
            parent_display = (parent_user or {}).get("name") or "your co-parent"

            subject_label = SUBJECTS[subject]["label"]
            reflect_url = _reflect_url(subject)

            if dry_run:
                sent.append({
                    "dry_run":         True,
                    "to":              coparent_user["email"],
                    "subject":         subject,
                    "coparent_id":     coparent_id,
                    "triggered_by":    parent_id,
                })
                continue

            # Iter194 · record the reminder FIRST so we have the
            # `_id` to embed in the pixel + click-wrapper URLs. If the
            # subsequent send fails we clean up the placeholder row so
            # a future sweep can retry.
            reminder_id = await _record_reminder(
                db,
                target_id=coparent_id,
                target_email=coparent_user["email"],
                coparent_id=parent_id,
                subject=subject,
            )

            api_base = _api_base_url()
            from alignment_reflection_analytics import build_reminder_url
            click_url = build_reminder_url(
                api_base=api_base, rid=str(reminder_id), kind="click",
            )
            open_pixel_url = build_reminder_url(
                api_base=api_base, rid=str(reminder_id), kind="open",
            )

            html = _reflection_reminder_email_html(
                coparent_display=parent_display,
                subject_label=subject_label,
                click_url=click_url,
                open_pixel_url=open_pixel_url,
            )
            text = _reflection_reminder_email_text(
                coparent_display=parent_display,
                subject_label=subject_label,
                click_url=reflect_url,  # plain-text falls back to direct URL
            )

            # Send via the shared email service. Late import keeps this
            # module importable in worker / CI environments that don't
            # need the mailer.
            try:
                from email_service import _send  # noqa: WPS437 — deliberate internal use
                _send(
                    to_email=coparent_user["email"],
                    subject=(
                        f"Your co-parent finished the {subject_label} "
                        f"reflection — your turn?"
                    ),
                    html=html,
                    text=text,
                    failure_message=(
                        "Could not deliver the alignment-reflection reminder."
                    ),
                )
                sent.append({
                    "to":            coparent_user["email"],
                    "subject":       subject,
                    "coparent_id":   coparent_id,
                    "triggered_by":  parent_id,
                    "reminder_id":   str(reminder_id),
                })
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "reflection reminder send failed for %s / %s: %s",
                    coparent_user.get("email"), subject, e,
                )
                # Roll back the placeholder row so the next sweep can
                # retry this triple — otherwise the "already_sent"
                # guard would freeze a failed reminder forever.
                await db[REMINDER_COLL].delete_one({"_id": reminder_id})
                skipped.append({
                    "reason":         "send_failed",
                    "target_user_id": coparent_id,
                    "subject":        subject,
                    "error":          str(e),
                })

    return {
        "sent":            sent,
        "skipped":         skipped,
        "candidate_count": len(completed),
        "sent_count":      len(sent),
        "dry_run":         dry_run,
    }


# ---------------------------------------------------------------------------
# Scheduler loop — Iter194 · long-running background sweep that
# `server.py::startup_log` registers as an `asyncio.create_task`.
# Gated behind `ALIGNMENT_REFLECTION_REMINDER_ENABLED=1` — idle
# no-op otherwise so a rollback is a single env-flag flip.
# ---------------------------------------------------------------------------

_SWEEP_INTERVAL_S = int(
    os.environ.get("ALIGNMENT_REFLECTION_REMINDER_SWEEP_SECONDS", "86400")
)  # daily by default


def _enabled() -> bool:
    return os.environ.get("ALIGNMENT_REFLECTION_REMINDER_ENABLED", "").lower() in (
        "1", "true", "yes", "on",
    )


async def alignment_reflection_reminder_loop(app) -> None:
    """Daily sweep. Idle no-op until
    `ALIGNMENT_REFLECTION_REMINDER_ENABLED=1` is set — safe to
    register unconditionally at startup."""
    import asyncio  # local import so the module is import-safe in test envs.
    if not _enabled():
        logger.info(
            "alignment_reflection_reminder_loop: "
            "ALIGNMENT_REFLECTION_REMINDER_ENABLED not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    # Offset from the other Monday sweeps so we don't all fire at once.
    await asyncio.sleep(600)
    while True:
        try:
            result = await send_reflection_reminders(app.state.db, dry_run=False)
            logger.info(
                "alignment reflection reminder sweep: sent=%d skipped=%d",
                result.get("sent_count", 0),
                len(result.get("skipped", [])),
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "alignment reflection reminder sweep failed; will retry."
            )
        await asyncio.sleep(_SWEEP_INTERVAL_S)
