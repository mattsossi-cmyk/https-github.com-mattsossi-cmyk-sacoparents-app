"""Monday judicial digest: every referred case's stage, hearing date, and unanswered court messages, per judge."""
from datetime import date
from html import escape

from court_workflow import STAGES, court_stage, hearing_overdue


def _last_unanswered(msgs: list[dict]) -> dict | None:
    """The judge's latest message when the professional has not replied after it."""
    if not msgs:
        return None
    last = msgs[-1]
    return last if last["from_role"] == "court" else None


def _row_html(x: dict, case: dict | None, unanswered: dict | None, app_url: str) -> str:
    stage = court_stage(case)["label"] if case else ("Declined" if x["status"] == "declined" else STAGES[0])
    hd = x.get("hearing_date") or "—"
    flag = ' <span style="color:#b91c1c;font-weight:bold">OVERDUE</span>' if hearing_overdue(x) else ""
    unans = f"Unanswered since {unanswered['at'][:10]}" if unanswered else "—"
    return (f'<tr><td style="padding:6px 8px;border-bottom:1px solid #eee"><a href="{app_url}/court/case/{x["id"]}" style="color:#5B2A86;font-weight:bold">Cause No. {escape(x.get("cause_number", ""))}</a>'
            f'<br><span style="font-size:11px;color:#888">{escape(x.get("case_code") or "")}</span></td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">{escape(x.get("professional_name", ""))}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">{escape(stage)}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">{escape(hd)}{flag}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">{escape(unans)}</td></tr>')


def build_digest(judge: dict, refs: list[dict], cases: dict, threads: dict, app_url: str, from_name: str) -> dict:
    """Returns {"subject", "html", "counts"} for one judge."""
    rows, overdue, unanswered_n = [], 0, 0
    for x in refs:
        unans = _last_unanswered(threads.get(x["id"], []))
        unanswered_n += bool(unans)
        overdue += hearing_overdue(x)
        rows.append(_row_html(x, cases.get(x.get("case_id") or ""), unans, app_url))
    week = date.today().isoformat()
    headline = f"{len(refs)} referred case{'s' if len(refs) != 1 else ''} · {overdue} hearing{'s' if overdue != 1 else ''} within 7 days awaiting submission · {unanswered_n} court message{'s' if unanswered_n != 1 else ''} unanswered"
    html = ('<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#222">'
            f"<p>Your Honor,</p><p>Weekly Judicial Portal digest for {escape(judge.get('name', ''))} — week of {week}.</p>"
            f'<p style="font-weight:bold">{headline}</p>'
            '<table style="border-collapse:collapse;width:100%;font-size:13px"><thead><tr style="background:#f3eefa;text-align:left">'
            '<th style="padding:6px 8px">Case</th><th style="padding:6px 8px">Professional</th><th style="padding:6px 8px">Stage</th><th style="padding:6px 8px">Hearing</th><th style="padding:6px 8px">Court messages</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            f'<p><a href="{app_url}/court-dashboard" style="color:#5B2A86">Open the Judicial Portal</a></p>'
            '<p style="font-size:12px;color:#888">Procedural status only. SA CoParents Align makes no determination of credibility, parenting fitness, or legal conclusions.</p>'
            f'<p style="font-size:12px;color:#888">Sent by {escape(from_name)}.</p></td></tr></table>')
    return {"subject": f"Judicial Portal weekly digest - {len(refs)} referred case{'s' if len(refs) != 1 else ''}", "html": html,
            "counts": {"cases": len(refs), "overdue": overdue, "unanswered": unanswered_n}}


async def run_judge_digests(db, send_email, app_url, email_from_name, logger) -> int:
    """One email per approved judge who has at least one open (non-declined) referral."""
    judges = await db.users.find({"role": "judge", "approved": True}, {"_id": 1, "name": 1, "email": 1}).to_list(1000)
    sent = 0
    for j in judges:
        refs = await db.court_referrals.find({"judge_id": j["_id"], "status": {"$ne": "declined"}}, {"_id": 0}).sort("created_at", -1).to_list(300)
        if not refs or not j.get("email"):
            continue
        case_ids = [x["case_id"] for x in refs if x.get("case_id")]
        cases = {c["id"]: c async for c in db.joint_reports.find({"id": {"$in": case_ids}}, {"_id": 0})} if case_ids else {}
        threads: dict = {}
        async for m in db.court_messages.find({"referral_id": {"$in": [x["id"] for x in refs]}}, {"_id": 0}).sort("at", 1):
            threads.setdefault(m["referral_id"], []).append(m)
        d = build_digest(j, refs, cases, threads, app_url(), email_from_name)
        try:
            await send_email(to=j["email"], subject=d["subject"], html=d["html"], kind="judge_digest", to_role="Court")
            sent += 1
        except Exception as exc:
            logger.warning("judge digest failed for %s: %s", j["_id"], exc)
    return sent



