"""Scheduled notification endpoints (platform cron) and their runners."""





import secrets
import asyncio
from datetime import datetime, timezone, timedelta

from html import escape




from fastapi import APIRouter, HTTPException, Request







from court_workflow import run_hearing_reminders
from judge_digest import run_judge_digests




from email_utils import send_email, EMAIL_FROM_NAME
from core import db, logger, app_url, _parse_iso, WEBHOOK_CRON_SECRET, INVITE_EXPIRY_DAYS, INVITE_EXPIRING_SOON_DAYS



router = APIRouter()


# ---------- Scheduled completion notifications ----------

async def _cron_accept(request: Request, job: str) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or not secrets.compare_digest(token, WEBHOOK_CRON_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        envelope = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    run_id = (envelope or {}).get("run_id") or request.headers.get("x-webhook-id")
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id, "job": job}):
            return {"ok": True, "duplicate": True}
        await db.cron_runs.insert_one({"run_id": run_id, "job": job, "at": datetime.now(timezone.utc).isoformat()})
    return {"ok": True}


@router.post("/cron/completion-nudge")
async def cron_completion_nudge(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "completion-nudge")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_completion_nudges())
    return ack


@router.post("/cron/expiry-digest")
async def cron_expiry_digest(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "expiry-digest")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_expiry_digests())
    asyncio.create_task(run_undelivered_invite_digest())
    return ack


def _digest_row(report: dict, inv: dict, now: datetime) -> str:
    expires = _parse_iso(inv["created_at"]) + timedelta(days=INVITE_EXPIRY_DAYS)
    days = (expires - now).days
    when = "has expired" if expires <= now else ("expires today" if days == 0 else f"expires in {days} day{'s' if days != 1 else ''}")
    child = (report.get("child_name") or "").strip()
    child_ref = f"{child[0].upper()}." if child else "child"
    parent = "Parent 1" if inv["role"] == "a" else "Parent 2"
    return f"<li><strong>{escape(report.get('case_code') or report['id'])}</strong> ({escape(report.get('subject_label', ''))}, matter for {escape(child_ref)}) &mdash; invitation to {parent} {when}</li>"


@router.post("/cron/weekly-summary")
async def cron_weekly_summary(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "weekly-summary")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_weekly_summaries())
    asyncio.create_task(run_judge_digests(db, send_email, app_url, EMAIL_FROM_NAME, logger))
    from research import run_provider_freshness
    asyncio.create_task(run_provider_freshness(db, send_email, app_url, EMAIL_FROM_NAME, logger))
    return ack


@router.post("/cron/judge-digest")
async def cron_judge_digest(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "judge-digest")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_judge_digests(db, send_email, app_url, EMAIL_FROM_NAME, logger))
    return ack


@router.post("/cron/follow-up-reminder")
async def cron_follow_up_reminder(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "follow-up-reminder")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_follow_up_reminders())
    from legal_lens import run_reassessment_reminders
    from safety_screening import run_screening_reminders
    asyncio.create_task(run_reassessment_reminders(db, send_email, app_url, EMAIL_FROM_NAME, logger))
    asyncio.create_task(run_screening_reminders(db, send_email, app_url, EMAIL_FROM_NAME, logger))
    # Retention Engine (retention.run_retention) is built but intentionally NOT scheduled — owner has it PAUSED pending report sign-off.
    return ack


@router.post("/cron/hearing-reminder")
async def cron_hearing_reminder(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    ack = await _cron_accept(request, "hearing-reminder")
    if ack.get("duplicate"):
        return ack
    asyncio.create_task(run_hearing_reminders(db, send_email, app_url, EMAIL_FROM_NAME, logger))
    return ack


def _follow_up_html(name: str, report: dict, outcome: dict, link: str) -> str:
    steps = "".join(f"<li>{escape(s)}</li>" for s in outcome.get("chosen_steps") or [])
    child = (report.get("child_name") or "").strip()
    child_ref = f"{child[0].upper()}." if child else "the child"
    summary = f"<p><em>{escape(outcome['summary'])}</em></p>" if outcome.get("summary") else ""
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(name)},</p>"
        f"<p>Today is the follow-up date you set for case <strong>{escape(report.get('case_code') or report['id'])}</strong> "
        f"({escape(report.get('subject_label', ''))}, matter for {escape(child_ref)}).</p>"
        f"<p>Next steps the parents chose:</p><ul>{steps or '<li>None recorded</li>'}</ul>{summary}"
        f'<p><a href="{link}" style="color:#5B2A86">Open the case</a></p>'
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
        "</td></tr></table>"
    )


async def run_follow_up_reminders() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    docs = await db.joint_reports.find(
        {"session_outcome.follow_up_date": {"$lte": today, "$ne": ""}, "follow_up_reminder_sent": {"$in": [None]}, "closed_at": {"$exists": False}},
        {"_id": 0},
    ).to_list(500)
    for report in docs:
        pro = await db.users.find_one({"_id": report.get("created_by")}, {"name": 1, "email": 1})
        if not pro or not pro.get("email"):
            continue
        outcome = report["session_outcome"]
        try:
            await send_email(
                to=pro["email"],
                subject=f"Follow-up today: case {report.get('case_code') or report['id'][:8]}",
                html=_follow_up_html(pro.get("name", ""), report, outcome, f"{app_url()}/joint/{report['id']}"),
                case_id=report["id"], kind="follow_up_reminder", to_role="Professional",
            )
        except Exception as exc:
            logger.warning("follow-up reminder failed for %s: %s", report["id"], exc)
            continue
        now = datetime.now(timezone.utc).isoformat()
        await db.joint_reports.update_one({"id": report["id"]}, {"$set": {"follow_up_reminder_sent": now}})
        await db.access_events.insert_one({
            "report_id": report["id"], "kind": "lifecycle", "action": f"Follow-up reminder emailed (due {outcome['follow_up_date']})",
            "at": now, "by": "system", "by_name": "SA CoParents Align", "by_role": "System",
        })


def _matter_state(report: dict, pending: list, now: datetime) -> tuple[str, str]:
    if report.get("status") == "ready":
        return "ready", "Report ready"
    a = bool(report.get("responses", {}).get("a"))
    b = bool(report.get("responses", {}).get("b"))
    states = {(True, False): ("awaiting_b", "Awaiting Parent 2"), (False, True): ("awaiting_a", "Awaiting Parent 1")}
    key, label = states.get((a, b), ("awaiting_both", "Awaiting both parents"))
    expiring = [i for i in pending if _parse_iso(i["created_at"]) + timedelta(days=INVITE_EXPIRY_DAYS - INVITE_EXPIRING_SOON_DAYS) <= now]
    if expiring:
        label += f" &middot; {len(expiring)} invitation{'s' if len(expiring) != 1 else ''} expiring/expired"
    return key, label


def _summary_row(report: dict, label: str) -> str:
    child = (report.get("child_name") or "").strip()
    child_ref = f"{child[0].upper()}." if child else "child"
    return (
        f"<tr><td style=\"padding:6px 8px;border-bottom:1px solid #eee\"><strong>{escape(report.get('case_code') or report['id'][:8])}</strong><br>"
        f"<span style=\"color:#666;font-size:12px\">{escape(report.get('subject_label', ''))} &middot; matter for {escape(child_ref)}</span></td>"
        f"<td style=\"padding:6px 8px;border-bottom:1px solid #eee\">{label}</td></tr>"
    )


async def _weekly_summary_html(pro: dict, reports: list, now: datetime) -> str:
    rids = [r["id"] for r in reports]
    pending: dict[str, list] = {}
    async for i in db.invitations.find({"report_id": {"$in": rids}, "status": "pending"}, {"_id": 0}):
        pending.setdefault(i["report_id"], []).append(i)
    week_ago = (now - timedelta(days=7)).isoformat()
    new_notes = await db.professional_notes.count_documents({"author_id": pro["_id"], "created_at": {"$gte": week_ago}})
    counts = {"ready": 0, "awaiting_a": 0, "awaiting_b": 0, "awaiting_both": 0}
    rows = []
    for r in sorted(reports, key=lambda x: x.get("created_at", "")):
        key, label = _matter_state(r, pending.get(r["id"], []), now)
        counts[key] += 1
        rows.append(_summary_row(r, label))
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
        f"<p>Here is your Monday overview of <strong>{len(reports)} active family matter{'s' if len(reports) != 1 else ''}</strong>.</p>"
        f"<p style=\"font-size:14px\"><strong>{counts['ready']}</strong> report{'s' if counts['ready'] != 1 else ''} ready &middot; "
        f"<strong>{counts['awaiting_a'] + counts['awaiting_b']}</strong> awaiting one parent &middot; "
        f"<strong>{counts['awaiting_both']}</strong> awaiting both parents &middot; "
        f"<strong>{new_notes}</strong> private note{'s' if new_notes != 1 else ''} added this week</p>"
        f"<table style=\"border-collapse:collapse;width:100%;font-size:14px\">{''.join(rows)}</table>"
        f'<p><a href="{app_url()}/matters" style="display:inline-block;background:#5B2A86;color:#ffffff;'
        'padding:12px 24px;text-decoration:none;border-radius:6px;margin-top:12px">Open Family Matters</a></p>'
        f'<p style="font-size:12px;color:#888">Weekly caseload summary sent by {escape(EMAIL_FROM_NAME)}. '
        f'Turn this off at {app_url()}/matters. Children are shown by initial only; parent responses are never included in email.</p>'
        "</td></tr></table>"
    )


async def run_weekly_summaries() -> None:
    now = datetime.now(timezone.utc)
    week = now.strftime("%G-W%V")
    by_pro: dict[str, list] = {}
    async for r in db.joint_reports.find({"archived": {"$ne": True}, "created_by": {"$ne": None}}, {"_id": 0}):
        by_pro.setdefault(r["created_by"], []).append(r)
    for pro_id, reports in by_pro.items():
        if await db.cron_runs.find_one({"job": "weekly-summary-sent", "pro_id": pro_id, "week": week}):
            continue
        pro = await db.users.find_one({"_id": pro_id, "role": "professional", "approved": True})
        if not pro or not pro.get("weekly_summary", True) or pro["email"].endswith("@example.com"):
            continue
        try:
            await send_email(
                to=pro["email"],
                subject=f"Weekly caseload summary: {len(reports)} active matter{'s' if len(reports) != 1 else ''} - {EMAIL_FROM_NAME}",
                html=await _weekly_summary_html(pro, reports, now),
            )
            await db.cron_runs.insert_one({"job": "weekly-summary-sent", "pro_id": pro_id, "week": week, "count": len(reports), "at": now.isoformat()})
        except Exception:
            logger.warning(f"Weekly summary not sent to {pro['email']}")


def _digest_html(pro: dict, rows: list[str], freq: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(pro.get('name') or 'there')},</p>"
        f"<p>The following parent invitations expire within {INVITE_EXPIRING_SOON_DAYS} days or have already expired. "
        "You can send a reminder or reissue a fresh invitation from your Family Matters page.</p>"
        f"<ul>{''.join(rows)}</ul>"
        f'<p><a href="{app_url()}/matters?filter=expiring" style="display:inline-block;background:#5B2A86;color:#ffffff;'
        'padding:12px 24px;text-decoration:none;border-radius:6px">Open Family Matters</a></p>'
        f'<p style="font-size:12px;color:#888">{"Weekly" if freq == "weekly" else "Daily"} digest sent by {escape(EMAIL_FROM_NAME)}. '
        f'Change how often you receive this at {app_url()}/matters. Parent responses are never included in email.</p>'
        "</td></tr></table>"
    )


async def _expiring_rows_by_pro(now: datetime) -> dict[str, list[str]]:
    cutoff = (now - timedelta(days=INVITE_EXPIRY_DAYS - INVITE_EXPIRING_SOON_DAYS)).isoformat()
    invs = await db.invitations.find({"status": "pending", "created_at": {"$lte": cutoff}}, {"_id": 0}).to_list(2000)
    if not invs:
        return {}
    rids = list({i["report_id"] for i in invs})
    reports = {r["id"]: r async for r in db.joint_reports.find({"id": {"$in": rids}, "archived": {"$ne": True}}, {"_id": 0})}
    by_pro: dict[str, list[str]] = {}
    for inv in invs:
        report = reports.get(inv["report_id"])
        if report and report.get("created_by"):
            by_pro.setdefault(report["created_by"], []).append(_digest_row(report, inv, now))
    return by_pro


def _digest_due(pro: dict, now: datetime) -> str | None:
    freq = pro.get("digest_frequency") or "daily"
    if freq == "off" or (freq == "weekly" and now.weekday() != 0):
        return None
    return freq


async def _send_digest(pro_id: str, rows: list[str], now: datetime) -> None:
    today = now.date().isoformat()
    if await db.cron_runs.find_one({"job": "expiry-digest-sent", "pro_id": pro_id, "day": today}):
        return
    pro = await db.users.find_one({"_id": pro_id, "role": "professional"})
    freq = _digest_due(pro, now) if pro else None
    if not freq:
        return
    try:
        await send_email(
            to=pro["email"],
            subject=f"{len(rows)} parent invitation{'s' if len(rows) != 1 else ''} expiring soon - {EMAIL_FROM_NAME}",
            html=_digest_html(pro, rows, freq),
        )
        await db.cron_runs.insert_one({"job": "expiry-digest-sent", "pro_id": pro_id, "day": today, "count": len(rows), "at": now.isoformat()})
    except Exception:
        logger.warning(f"Expiry digest not sent to {pro['email']}")


async def run_undelivered_invite_digest() -> None:
    """Daily admin digest: professional invitations whose email failed and have stayed undelivered > 24h (and never opened)."""
    from email_utils import EMAIL_FROM_NAME as _from
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = await db.pro_invites.find({"status": "invited", "email_sent": False, "first_opened_at": None, "created_at": {"$lt": cutoff}},
                                     {"_id": 0, "name": 1, "email": 1, "zip": 1, "created_at": 1, "email_error": 1, "invited_by_name": 1}).sort("created_at", 1).to_list(200)
    if not rows:
        return
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "email": 1, "name": 1}).to_list(20)
    items = "".join(f"<li><strong>{escape(r['name'])}</strong> &lt;{escape(r['email'])}&gt; · ZIP {escape(r.get('zip') or '')} · invited {escape(str(r['created_at'])[:10])}"
                    f"{' by ' + escape(r['invited_by_name']) if r.get('invited_by_name') else ''}{(' — ' + escape(r['email_error'][:120])) if r.get('email_error') else ''}</li>" for r in rows)
    html = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
            f"<p>{len(rows)} professional invitation{'s' if len(rows) > 1 else ''} could not be emailed and {'have' if len(rows) > 1 else 'has'} stayed undelivered for more than 24 hours:</p><ul>{items}</ul>"
            f'<p>Open the admin dashboard → Invite Professional, run the <strong>email health check</strong>, fix the sender settings if needed, then tap <strong>Retry send</strong> on each invitation.</p>'
            f'<p><a href="{app_url()}/dashboard">Go to the admin dashboard</a></p><p style="font-size:12px;color:#888">Sent by {escape(_from)}. We never ask for your password by email.</p></td></tr></table>')
    for a in admins:
        try:
            await send_email(to=a["email"], subject=f"[Action needed] {len(rows)} undelivered professional invitation{'s' if len(rows) > 1 else ''}", html=html, kind="admin_alert", to_role="Admin")
        except Exception as exc:
            logger.warning("undelivered-invite digest to %s failed: %s", a["email"], exc)


async def run_expiry_digests() -> None:
    now = datetime.now(timezone.utc)
    for pro_id, rows in (await _expiring_rows_by_pro(now)).items():
        await _send_digest(pro_id, rows, now)


def _ready_email_html(name: str, child: str, label: str, link: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(name)},</p>"
        f"<p>Both parents have completed their assessments for <strong>{escape(child)}</strong> ({escape(label)}). "
        "Your Joint Report is ready to view.</p>"
        f'<p><a href="{link}" style="color:#5B2A86">Open your Joint Report</a></p>'
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
        "</td></tr></table>"
    )


def _ready_window_open(doc: dict, now: datetime) -> bool:
    ra, rb = doc["responses"]["a"], doc["responses"]["b"]
    done_a, done_b = _parse_iso(ra.get("completed_at")), _parse_iso(rb.get("completed_at"))
    return bool(done_a and done_b) and (now - max(done_a, done_b)) <= timedelta(hours=48)


async def _send_ready_notifications(doc: dict, now: datetime) -> None:
    if not _ready_window_open(doc, now):
        return
    sent = doc.get("ready_notified")
    if not isinstance(sent, dict):
        sent = {}
    label = doc.get("subject_label", "Joint Report")
    child = doc.get("child_name") or "your child"
    link = f"{app_url()}/joint/{doc['id']}"
    updates = {}
    for side, p in (("a", doc["participants"]["a"]), ("b", doc["participants"]["b"])):
        if sent.get(side) or not p.get("email"):
            continue
        try:
            await send_email(
                to=p["email"],
                subject=f"Your Joint Report is ready - {EMAIL_FROM_NAME}",
                html=_ready_email_html(p.get("name") or "there", child, label, link),
                case_id=doc["id"], kind="report_ready", to_role=f"Parent {side.upper()}",
            )
            updates[side] = now.isoformat()
        except Exception:
            logger.warning(f"Ready notification not sent to {p['email']}")
    if updates:
        await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {"ready_notified": {**sent, **updates}}})


def _nudge_target(doc: dict, now: datetime) -> tuple[dict, dict, str] | None:
    """Returns (done_participant, other_participant, side_to_nudge) when a nudge is due."""
    ra = doc.get("responses", {}).get("a")
    rb = doc.get("responses", {}).get("b")
    if bool(ra) == bool(rb):
        return None
    pa, pb = doc["participants"]["a"], doc["participants"]["b"]
    done, other, side = (pa, pb, "b") if ra else (pb, pa, "a")
    if doc.get("nudges", {}).get(side) or not other.get("email"):
        return None
    done_at = _parse_iso((ra or rb).get("completed_at"))
    if not done_at or not (timedelta(minutes=15) <= (now - done_at) <= timedelta(hours=48)):
        return None
    return done, other, side


def _nudge_email_html(done_name: str, other_name: str, child: str, label: str, link: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f"<p>Hi {escape(other_name)},</p>"
        f"<p><strong>{escape(done_name)}</strong> has completed their half of the "
        f"{escape(label)} for <strong>{escape(child)}</strong>. Once you complete yours, the Joint Report "
        "will be generated for both of you.</p>"
        f'<p><a href="{link}" style="color:#5B2A86">Complete your half</a></p>'
        f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password by email.</p>'
        "</td></tr></table>"
    )


async def _send_completion_nudge(doc: dict, now: datetime) -> None:
    target = _nudge_target(doc, now)
    if target is None:
        return
    done, other, side = target
    label = doc.get("subject_label", "Joint Report")
    child = doc.get("child_name") or "your child"
    link = f"{app_url()}/joint/{doc['id']}"
    try:
        await send_email(
            to=other["email"],
            subject=f"Your co-parent has completed their half - {EMAIL_FROM_NAME}",
            html=_nudge_email_html(done.get("name") or "Your co-parent", other.get("name") or "there", child, label, link),
            case_id=doc["id"], kind="completion_nudge", to_role=f"Parent {side.upper()}",
        )
        await db.joint_reports.update_one({"id": doc["id"]}, {"$set": {f"nudges.{side}": now.isoformat()}})
    except Exception:
        logger.warning(f"Completion nudge not sent to {other['email']}")


async def run_completion_nudges():
    now = datetime.now(timezone.utc)
    docs = await db.joint_reports.find({"status": {"$in": ["in_progress", "ready"]}}, {"_id": 0}).to_list(500)
    for doc in docs:
        try:
            if doc.get("responses", {}).get("a") and doc.get("responses", {}).get("b"):
                await _send_ready_notifications(doc, now)
            else:
                await _send_completion_nudge(doc, now)
        except Exception as e:
            logger.error(f"Nudge processing error for {doc.get('id')}: {e}")
