"""Case Completion Nudge Sweep — Iter197.

Nudges a parent 5 days after they accepted an invitation to a Joint
Alignment Case if any REQUIRED step is still incomplete. The email
lists the specific assessments they still owe and deep-links straight
to their scoped `/case/:caseId` view.

Design (mirrors `alignment_reflection_reminder.py`):
  * Pure async function `send_case_completion_nudges()` — cron / admin
    / manual invocation, never self-schedules.
  * Env-gated loop `case_completion_nudge_loop(app)` — idle no-op
    until `CASE_COMPLETION_NUDGE_ENABLED=1`. Safe to register on
    every deploy.
  * Dedupe: one nudge per (case_id, parent_email) tracked in
    `case_completion_nudges` collection. First-touch wins.
  * Only touches parents who:
        - accepted_at is 5+ days old
        - at least one required step in `assigned_steps` has no
          `step_completions[assessment_type]` timestamp
        - `assessment_completed_at` is not set (legacy full-completion)
  * Never mentions the co-parent's status — the nudge is scoped to
    THIS parent's own progress. No cross-parent PHI leakage.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


logger = logging.getLogger(__name__)

CASES_COLL = "joint_alignment_cases"
NUDGES_COLL = "case_completion_nudges"

# 5-day grace period per founder spec — long enough to feel supportive,
# short enough to keep parents from ghosting their referral entirely.
DEFAULT_STALE_DAYS = 5

# Sweep runs once a day when enabled. Offset relative to the other
# reminder loops so we don't burst the mailer.
_SWEEP_INTERVAL_S = 24 * 3600

# Human-friendly labels — kept in lock-step with
# `joint_alignment_routes._ASSESSMENT_LABELS` so the email body prints
# the same phrase the parent sees on their `/case/:caseId` page.
_LABELS = {
    "co-parenting":  "Co-Parenting Assessment",
    "communication": "Communication Assessment",
    "educational":   "Educational Needs Assessment",
    "medical":       "Medical Needs Assessment",
    "psychological": "Psychological / Emotional Needs Assessment",
    "special-needs": "Special Needs Assessment",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt):
    """Coerce a Mongo-returned naive datetime to UTC-aware so
    comparisons don't blow up. Mongo drivers return `datetime`
    with `tzinfo=None` even when we wrote UTC-aware values."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _public_case_url(case_id: str) -> str:
    base = (
        os.environ.get("PUBLIC_APP_URL")
        or os.environ.get("FRONTEND_URL")
        or "https://sacoparents.com"
    ).rstrip("/")
    return f"{base}/case/{case_id}"


def _incomplete_required_steps_for(parent: Dict[str, Any],
                                   assigned_steps: List[Dict[str, Any]],
                                   primary: str) -> List[Dict[str, Any]]:
    """Return the subset of the case's assigned_steps that this parent
    still owes: required=True AND no matching completion timestamp.

    Legacy fallback: if a parent has a top-level
    `assessment_completed_at` set, treat the primary lane as done
    even when no `step_completions` map is stored — the older
    completion flow only stamped that single field.
    """
    step_completions = parent.get("step_completions") or {}
    top_done = parent.get("assessment_completed_at")
    out: List[Dict[str, Any]] = []
    for step in assigned_steps or []:
        at = step.get("assessment_type")
        if not at or not step.get("required", True):
            continue
        completed = step_completions.get(at) if isinstance(step_completions, dict) else None
        if completed:
            continue
        # Legacy: primary lane done via the old single-field flag.
        if at == primary and top_done:
            continue
        out.append({
            "assessment_type": at,
            "label": _LABELS.get(at, at.replace("-", " ").title()),
        })
    return out


def _normalise_case_assigned_steps(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Same shape helper as `_normalise_assigned_steps` in
    `joint_alignment_routes` — copy is DRY-broken on purpose so the
    nudge module can be imported without pulling the whole routes
    graph (avoids a circular import between routes and cron loops)."""
    steps = case.get("assigned_steps") or []
    if steps:
        out = []
        for s in steps:
            if isinstance(s, dict) and s.get("assessment_type"):
                out.append({
                    "assessment_type": s["assessment_type"],
                    "required": bool(s.get("required", True)),
                })
        if out:
            return out
    return [{
        "assessment_type": case.get("assessment_type") or "co-parenting",
        "required": True,
    }]


def _nudge_html(*, parent_name: Optional[str],
                professional_name: Optional[str],
                case_id: str,
                incomplete: List[Dict[str, Any]],
                case_url: str) -> str:
    hi = f"Hi {parent_name}," if parent_name else "Hi,"
    prof = professional_name or "your professional"
    steps_html = "".join(
        f"<li style=\"margin: 6px 0; color: #1A1330;\">"
        f"<strong>{s['label']}</strong></li>"
        for s in incomplete
    )
    return f"""\
<!doctype html>
<html><body style="font-family: 'Georgia', serif; color:#1A1330; padding: 24px; max-width: 560px; margin: 0 auto;">
  <p style="font-size: 15px;">{hi}</p>
  <p style="font-size: 15px; line-height: 1.55;">
    It&rsquo;s been a few days since you started your SA CoParents case
    <strong style="font-family: monospace; letter-spacing: 0.02em;">{case_id}</strong>
    referred by {prof}. A quiet reminder that the following required
    assessment{"s" if len(incomplete) != 1 else ""} {"are" if len(incomplete) != 1 else "is"} still open:
  </p>
  <ul style="padding-left: 20px; font-size: 15px; line-height: 1.6;">
    {steps_html}
  </ul>
  <p style="font-size: 15px; line-height: 1.55;">
    You can pick up right where you left off — your answers stay
    private until you explicitly share.
  </p>
  <p style="margin: 24px 0;">
    <a href="{case_url}"
       style="display: inline-block; background: #3D1A78; color: #fff;
              text-decoration: none; padding: 12px 22px; border-radius: 999px;
              font-family: sans-serif; font-size: 14px; font-weight: 600;">
      Open my case &rsquo;
    </a>
  </p>
  <p style="font-size: 12px; color: #857E9C;">
    You&rsquo;re receiving this because your referral professional
    invited you to complete assessments in SA CoParents. We only send
    one gentle nudge per case.
  </p>
</body></html>"""


def _nudge_text(*, parent_name: Optional[str],
                professional_name: Optional[str],
                case_id: str,
                incomplete: List[Dict[str, Any]],
                case_url: str) -> str:
    hi = f"Hi {parent_name}," if parent_name else "Hi,"
    prof = professional_name or "your professional"
    steps_lines = "\n".join(f"  - {s['label']}" for s in incomplete)
    return (
        f"{hi}\n\n"
        f"It's been a few days since you started your SA CoParents case "
        f"{case_id} referred by {prof}. A quiet reminder that the "
        f"following required assessment(s) are still open:\n\n"
        f"{steps_lines}\n\n"
        f"You can pick up right where you left off — your answers stay "
        f"private until you explicitly share.\n\n"
        f"Open your case: {case_url}\n\n"
        f"We only send one gentle nudge per case.\n"
    )


async def _already_nudged(db: AsyncIOMotorDatabase,
                          case_id: str, parent_email: str) -> bool:
    doc = await db[NUDGES_COLL].find_one({
        "case_id": case_id,
        "parent_email": parent_email.lower(),
    }, {"_id": 1})
    return bool(doc)


async def _record_nudge(db: AsyncIOMotorDatabase, *, case_id: str,
                        parent_email: str, steps: List[str]) -> None:
    await db[NUDGES_COLL].insert_one({
        "case_id": case_id,
        "parent_email": parent_email.lower(),
        "steps": steps,
        "sent_at": _now(),
    })


async def send_case_completion_nudges(
    db: AsyncIOMotorDatabase,
    *,
    stale_days: int = DEFAULT_STALE_DAYS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Iterate every live joint-alignment case; for each accepted
    parent whose required steps are stale, send exactly one nudge.

    Returns per-invocation stats + a `sent` list for admin logging.
    Never raises on individual send failures — logs and continues so
    one bad address can't block the sweep.
    """
    cutoff = _now() - timedelta(days=stale_days)
    sent: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    cursor = db[CASES_COLL].find({
        # Live cases only: not expired / cancelled / released.
        "status": {"$nin": ["expired", "cancelled"]},
        "released_at": {"$in": [None, False]} if False else {"$exists": False},
    })
    async for case in cursor:
        # `released_at` may exist as None in some legacy docs — skip
        # if truthy.
        if case.get("released_at"):
            continue
        assigned = _normalise_case_assigned_steps(case)
        primary = case.get("assessment_type")
        case_id = case.get("case_id")
        prof_name = ((case.get("professional") or {}).get("name") or "").strip() or None
        for parent in (case.get("parents") or []):
            accepted_at = _as_aware(parent.get("accepted_at"))
            if not accepted_at:
                skipped.append({"case_id": case_id, "reason": "never_accepted"})
                continue
            if accepted_at > cutoff:
                skipped.append({"case_id": case_id, "reason": "still_within_grace"})
                continue
            email = (parent.get("email") or "").lower()
            if not email:
                skipped.append({"case_id": case_id, "reason": "no_email"})
                continue
            incomplete = _incomplete_required_steps_for(parent, assigned, primary)
            if not incomplete:
                skipped.append({"case_id": case_id, "reason": "all_required_done"})
                continue
            if await _already_nudged(db, case_id, email):
                skipped.append({"case_id": case_id, "reason": "already_nudged"})
                continue

            if dry_run:
                sent.append({
                    "case_id": case_id, "to": email,
                    "steps": [s["assessment_type"] for s in incomplete],
                    "dry_run": True,
                })
                continue

            case_url = _public_case_url(case_id)
            html = _nudge_html(
                parent_name=parent.get("name"),
                professional_name=prof_name,
                case_id=case_id,
                incomplete=incomplete,
                case_url=case_url,
            )
            text = _nudge_text(
                parent_name=parent.get("name"),
                professional_name=prof_name,
                case_id=case_id,
                incomplete=incomplete,
                case_url=case_url,
            )
            try:
                from email_service import _send  # noqa: WPS437
                _send(
                    to_email=email,
                    subject=(
                        f"A gentle reminder — {len(incomplete)} required "
                        f"step{'s' if len(incomplete) != 1 else ''} left "
                        f"on your SA CoParents case {case_id}"
                    ),
                    html=html,
                    text=text,
                    failure_message="Could not deliver case completion nudge.",
                )
                await _record_nudge(
                    db,
                    case_id=case_id,
                    parent_email=email,
                    steps=[s["assessment_type"] for s in incomplete],
                )
                sent.append({
                    "case_id": case_id,
                    "to": email,
                    "steps": [s["assessment_type"] for s in incomplete],
                })
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "case completion nudge failed case=%s to=%s: %s",
                    case_id, email, e,
                )
                skipped.append({
                    "case_id": case_id, "reason": "send_failed",
                    "error": str(e),
                })

    return {
        "sent": sent,
        "skipped": skipped,
        "sent_count": len(sent),
        "candidate_count": len(sent) + len(skipped),
    }


def _enabled() -> bool:
    return os.environ.get("CASE_COMPLETION_NUDGE_ENABLED", "").lower() in (
        "1", "true", "yes", "on",
    )


async def case_completion_nudge_loop(app) -> None:
    """Daily sweep. Idle no-op until
    `CASE_COMPLETION_NUDGE_ENABLED=1` — safe to register on every
    deploy so we don't accidentally spam parents in dev."""
    import asyncio
    if not _enabled():
        logger.info(
            "case_completion_nudge_loop: "
            "CASE_COMPLETION_NUDGE_ENABLED not set; loop idle",
        )
        while True:
            await asyncio.sleep(3600)
    # Offset from the other sweeps.
    await asyncio.sleep(900)
    while True:
        try:
            result = await send_case_completion_nudges(app.state.db, dry_run=False)
            logger.info(
                "case completion nudge sweep: sent=%d skipped=%d",
                result.get("sent_count", 0),
                len(result.get("skipped", [])),
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "case completion nudge sweep failed; will retry.",
            )
        await asyncio.sleep(_SWEEP_INTERVAL_S)
