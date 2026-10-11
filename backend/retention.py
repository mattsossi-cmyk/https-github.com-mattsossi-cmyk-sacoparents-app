"""Retention engine — owner-approved design (2026-10-11).

- Raw safety screening answers AND computed flags: purged RAW_SCREENING_RETENTION_DAYS after the case closes.
  Kept: tier, receipt (received/completed_at), version letter, pathway decision. Account deletion already removes the slot immediately.
- Frozen court submissions: deleted entirely (PDF bytes, metadata, hash, submission entry) COURT_SUBMISSION_RETENTION_MONTHS after submission.
- Judge reminder: JUDGE_REMINDER_LEAD_DAYS before deletion, one email to the judge if the packet has never been opened.
Runs once a day from the follow-up-reminder cron (see cron_jobs.py). Nothing runs on import.
"""
from datetime import datetime, timedelta, timezone
from html import escape

RAW_SCREENING_RETENTION_DAYS = 90
COURT_SUBMISSION_RETENTION_MONTHS = 6
JUDGE_REMINDER_LEAD_DAYS = 30
PURGED_SCREENING_FIELDS = ("responses", "flags", "pathway_suggested", "skipped", "answered_count", "skipped_count")


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(s: str) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def court_purge_at(created_at: str) -> datetime | None:
    d = _parse(created_at)
    if not d:
        return None
    m = d.month - 1 + COURT_SUBMISSION_RETENTION_MONTHS
    y, m = d.year + m // 12, m % 12 + 1
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    day = min(d.day, [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return d.replace(year=y, month=m, day=day)


async def purge_screening_answers(db, now: datetime) -> int:
    cutoff = _iso(now - timedelta(days=RAW_SCREENING_RETENTION_DAYS))
    n = 0
    async for doc in db.joint_reports.find({"closed_at": {"$gt": "", "$lte": cutoff}, "safety_screenings": {"$exists": True}}, {"id": 1, "safety_screenings": 1}):
        unset, mark = {}, {}
        for role, scr in (doc.get("safety_screenings") or {}).items():
            if scr and any(f in scr for f in PURGED_SCREENING_FIELDS):
                unset.update({f"safety_screenings.{role}.{f}": "" for f in PURGED_SCREENING_FIELDS})
                mark[f"safety_screenings.{role}.purged_at"] = _iso(now)
        if unset:
            await db.joint_reports.update_one({"id": doc["id"]}, {"$unset": unset, "$set": mark})
            n += len(mark)
    return n


async def purge_court_submissions(db, now: datetime) -> int:
    n = 0
    async for p in db.court_packets.find({"frozen": True}, {"id": 1, "created_at": 1, "report_id": 1, "court_referral_id": 1}):
        pa = court_purge_at(p.get("created_at") or "")
        if not pa or pa > now:
            continue
        await db.court_frozen_pdfs.delete_many({"packet_id": p["id"]})
        await db.court_packets.delete_one({"id": p["id"]})
        if p.get("report_id"):
            await db.joint_reports.update_one({"id": p["report_id"]}, {"$pull": {"court_submissions": {"packet_id": p["id"]}}, "$push": {"retention_log": {"packet_id": p["id"], "deleted_at": _iso(now), "rule": f"{COURT_SUBMISSION_RETENTION_MONTHS}-month court submission retention"}}})
        if p.get("court_referral_id"):
            await db.court_referrals.update_one({"id": p["court_referral_id"], "status": "submitted"}, {"$set": {"status": "expired", "expired_at": _iso(now)}})
        n += 1
    return n


async def remind_judges(db, send_email, app_url, from_name: str, now: datetime, logger) -> int:
    sent = 0
    q = {"frozen": True, "purge_reminder_sent_at": {"$exists": False}, "judge_email": {"$nin": [None, ""]}, "$or": [{"opened_count": {"$exists": False}}, {"opened_count": 0}]}
    async for p in db.court_packets.find(q, {"id": 1, "created_at": 1, "judge_email": 1, "judge_name": 1, "cause_number": 1, "court_name": 1, "professional_name": 1, "report_id": 1}):
        pa = court_purge_at(p.get("created_at") or "")
        if not pa or pa <= now or pa - now > timedelta(days=JUDGE_REMINDER_LEAD_DAYS):
            continue
        ref = p.get("cause_number") or p.get("court_name") or "your matter"
        html = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f"<p>Dear {escape(p.get('judge_name') or 'Judge')},</p>"
                f"<p>A court submission from {escape(p.get('professional_name') or 'the assigned professional')} for <strong>{escape(ref)}</strong> has not yet been opened. "
                f"Under the SA CoParents Align retention schedule it will be permanently deleted on <strong>{pa.date().isoformat()}</strong> "
                f"({COURT_SUBMISSION_RETENTION_MONTHS} months after submission).</p>"
                f'<p><a href="{app_url()}/court" style="display:inline-block;background:#5B2A86;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Open the Judicial Portal</a></p>'
                f'<p style="font-size:12px;color:#888">Sent by {escape(from_name)}. This notice contains no case content.</p></td></tr></table>')
        try:
            await send_email(to=p["judge_email"], subject=f"Court submission will be deleted on {pa.date().isoformat()} — {ref} - {from_name}", html=html, case_id=p.get("report_id"), kind="court_retention_reminder", to_role="Judge")
        except Exception as exc:
            logger.warning("retention judge reminder failed for packet %s: %s", p["id"], exc)
            continue
        await db.court_packets.update_one({"id": p["id"]}, {"$set": {"purge_reminder_sent_at": _iso(now)}})
        sent += 1
    return sent


async def run_retention(db, send_email, app_url, from_name: str, logger) -> dict:
    now = datetime.now(timezone.utc)
    out = {"screening_slots_purged": await purge_screening_answers(db, now), "court_submissions_deleted": await purge_court_submissions(db, now),
           "judge_reminders_sent": await remind_judges(db, send_email, app_url, from_name, now, logger), "at": _iso(now)}
    await db.retention_runs.insert_one(dict(out))
    logger.info("retention run: %s", out)
    return out


async def preview(db) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = _iso(now - timedelta(days=RAW_SCREENING_RETENTION_DAYS))
    due_scr = 0
    async for doc in db.joint_reports.find({"closed_at": {"$gt": "", "$lte": cutoff}, "safety_screenings": {"$exists": True}}, {"safety_screenings": 1}):
        due_scr += sum(1 for s in (doc.get("safety_screenings") or {}).values() if s and "responses" in s)
    due_pdf = rem = 0
    async for p in db.court_packets.find({"frozen": True}, {"created_at": 1, "opened_count": 1, "purge_reminder_sent_at": 1}):
        pa = court_purge_at(p.get("created_at") or "")
        if not pa:
            continue
        due_pdf += pa <= now
        rem += (now < pa <= now + timedelta(days=JUDGE_REMINDER_LEAD_DAYS)) and not (p.get("opened_count") or 0) and not p.get("purge_reminder_sent_at")
    last = await db.retention_runs.find_one({}, {"_id": 0}, sort=[("at", -1)])
    return {"rules": {"raw_screening_retention_days": RAW_SCREENING_RETENTION_DAYS, "court_submission_retention_months": COURT_SUBMISSION_RETENTION_MONTHS, "judge_reminder_lead_days": JUDGE_REMINDER_LEAD_DAYS,
                      "screening_fields_purged": list(PURGED_SCREENING_FIELDS), "screening_fields_kept": ["tier", "version", "completed_at", "received"]},
            "due_now": {"screening_slots": due_scr, "court_submissions": due_pdf, "judge_reminders": rem}, "last_run": last}
