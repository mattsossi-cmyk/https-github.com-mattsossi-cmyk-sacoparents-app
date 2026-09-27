"""Iteration 82: report walk-through (editor guide + PDF page), invite open tracking, undelivered-invite digest."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pymongo
import pymupdf
import requests

from casekit import new_user
from test_judicial_portal import API, _flow

DB = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_walkthrough_endpoint_and_pdf_reader_page() -> None:
    judge, pro, ref, case = _flow()
    g = pro.get(f"{API}/cases/{case['id']}/professional-report/walkthrough")
    assert g.status_code == 200 and len(g.json()) == 11 and g.json()[0]["title"] == "Case & Assessment Overview" and g.json()[10]["title"] == "Concise Court Summary"
    assert all({"n", "title", "what", "how", "guardrail"} <= set(x) for x in g.json())
    assert judge.get(f"{API}/cases/{case['id']}/professional-report/walkthrough").status_code in (403, 404)
    pdf = requests.get(f"{API}/joint/sample-legal-lens/pdf")
    text = "".join(p.get_text() for p in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "How to Read This Report" in text and "Reader's guardrail" in text and "Reading the 1–10 scale" in text


def _temp_admin():
    s = new_user(API, "professional", "Temp Admin")
    uid = s.get(f"{API}/auth/me").json()["id"]
    DB.users.update_one({"_id": uid}, {"$set": {"role": "admin"}})
    return s, uid


def test_invite_open_tracking_and_digest() -> None:
    admin, uid = _temp_admin()
    email = f"t_open_{uuid.uuid4().hex[:8]}@example.com"
    inv = admin.post(f"{API}/admin/pro-invites", json={"name": "Open Tracker", "email": email, "zip": "78201"}).json()
    row = next(x for x in admin.get(f"{API}/admin/pro-invites").json() if x["id"] == inv["id"])
    assert row["first_opened_at"] is None and row["open_count"] == 0
    token = DB.pro_invites.find_one({"id": inv["id"]})["token"]
    assert requests.get(f"{API}/auth/pro-invite/{token}").status_code == 200
    requests.get(f"{API}/auth/pro-invite/{token}")
    row = next(x for x in admin.get(f"{API}/admin/pro-invites").json() if x["id"] == inv["id"])
    assert row["first_opened_at"] and row["open_count"] == 2 and row["email_sent"] is True

    # digest picks only failed + unopened + older than 24h
    stale = f"t_stale_{uuid.uuid4().hex[:8]}@example.com"
    DB.pro_invites.insert_one({"id": str(uuid.uuid4()), "token": uuid.uuid4().hex, "name": "Stale Invite", "email": stale, "zip": "78201", "status": "invited", "email_sent": False, "email_error": "simulated",
                               "first_opened_at": None, "created_at": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()})
    sys.path.insert(0, "/app/backend")
    import cron_jobs
    sent = []

    async def fake_send(**kw):
        sent.append(kw)
    cron_jobs.send_email = fake_send
    asyncio.run(cron_jobs.run_undelivered_invite_digest())
    assert sent, "digest should email admins"
    assert "Stale Invite" in sent[0]["html"] and "Open Tracker" not in sent[0]["html"] and "undelivered" in sent[0]["subject"]
    DB.pro_invites.delete_many({"email": {"$in": [email, stale]}})
    DB.users.delete_one({"_id": uid})
