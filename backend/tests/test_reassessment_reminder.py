"""Reassessment reminder: due report -> one email -> idempotent per date. Cron endpoint auth check."""
import os
import requests
from datetime import date

from test_legal_report import API


def test_reassessment_reminder_runs_once_per_date() -> None:
    import asyncio, pymongo
    from motor.motor_asyncio import AsyncIOMotorClient
    import sys
    sys.path.insert(0, "/app/backend")
    from legal_lens import run_reassessment_reminders
    sync = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    pro = sync.users.find_one({"email": "approval.test.pro1@gmail.com"})
    cid = "reassess-test-case"
    sync.joint_reports.update_one({"id": cid}, {"$set": {"id": cid, "case_code": "SA-TEST-REASSESS", "professional_id": pro["_id"]}}, upsert=True)
    sync.professional_reports.update_one({"case_id": cid}, {"$set": {"case_id": cid, "professional_id": pro["_id"], "status": "final", "next_review_date": date.today().isoformat(),
                                                                       "parent_a_growth": "A goal one\nA goal two", "growth_status": {"a": {"A goal one": True}}}, "$unset": {"reassess_reminder_for": ""}}, upsert=True)
    sent_to = []

    async def fake_send(to, **kw):
        sent_to.append((to, kw["subject"], kw["html"]))

    class L:
        def warning(self, *a): pass

    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        first = await run_reassessment_reminders(db, fake_send, lambda: "https://x", "SA CoParents Align", L())
        second = await run_reassessment_reminders(db, fake_send, lambda: "https://x", "SA CoParents Align", L())
        return first, second

    first, second = asyncio.run(run())
    try:
        assert first >= 1 and second == 0
        mine = [s for s in sent_to if s[0] == pro["email"] and "SA-TEST-REASSESS" in s[1]]
        assert len(mine) == 1 and "1 Key Growth Area is not yet marked" in mine[0][2] and f"/cases/{cid}/professional-report" in mine[0][2]
        assert sync.professional_reports.find_one({"case_id": cid})["reassess_reminder_for"] == date.today().isoformat()
    finally:
        sync.joint_reports.delete_one({"id": cid})
        sync.professional_reports.delete_one({"case_id": cid})


def test_follow_up_cron_requires_secret() -> None:
    assert requests.post(f"{API}/cron/follow-up-reminder", json={"event": "schedule.triggered", "run_id": "x"}).status_code == 401
    ok = requests.post(f"{API}/cron/follow-up-reminder", json={"event": "schedule.triggered", "schedule_id": "follow-up-reminder", "run_id": "test-run-reassess-1"},
                       headers={"Authorization": f"Bearer {os.environ['WEBHOOK_CRON_SECRET']}", "X-Webhook-Id": "test-run-reassess-1"})
    assert ok.status_code in (200, 202)
