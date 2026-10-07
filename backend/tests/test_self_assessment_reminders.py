import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

import email_service  # noqa: E402
from self_assessment_reminders import send_reassess_reminders  # noqa: E402

NOW = datetime(2026, 9, 1, 15, tzinfo=timezone.utc)


async def _seed(db):
    def user(uid, **kw):
        return {"user_id": uid, "email": f"{uid}@example.com", "name": f"{uid.title()} Parent", **kw}

    def entry(uid, days_ago, eid=None):
        return {"user_id": uid, "id": eid or f"e-{uid}", "completed_at": (NOW - timedelta(days=days_ago)).isoformat()}

    await db.users.insert_many([
        user("due"), user("recent"), user("flagged"), user("ipv"), user("unsub"), user("guest", is_guest=True),
        user("followup"), user("retook"),
    ])
    await db.self_assessment_history.insert_many([
        entry("due", 43), entry("recent", 10), entry("flagged", 60), entry("ipv", 60), entry("unsub", 60),
        entry("guest", 60), entry("followup", 57),
        entry("retook", 90, "old"), entry("retook", 5, "new"),
    ])
    await db.portal_state.insert_one({"user_id": "flagged", "safety_ack": {"flagged": True}})
    await db.safety_assessments.insert_one({"user_id": "ipv", "result": {"level": 2}, "created_at": NOW.isoformat()})
    await db.self_assessment_reminder_prefs.insert_one({"user_id": "unsub", "unsubscribed": True})
    await db.self_assessment_reminders.insert_one(
        {"user_id": "followup", "entry_id": "e-followup", "kind": "6w", "status": "sent",
         "sent_at": (NOW - timedelta(days=15)).isoformat()}
    )


def test_reminder_sweep_respects_safety_and_dedupe(monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "send_reassess_reminder", lambda **kw: sent.append(kw))

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_sa_reminders"
        await client.drop_database(name)
        db = client[name]
        try:
            await _seed(db)
            first = await send_reassess_reminders(db, now=NOW)
            second = await send_reassess_reminders(db, now=NOW)
            return first, second
        finally:
            await client.drop_database(name)

    first, second = asyncio.run(run())
    recipients = sorted(kw["to_email"] for kw in sent)
    assert recipients == ["due@example.com", "followup@example.com"]
    assert {kw["to_email"]: kw["follow_up"] for kw in sent} == {"due@example.com": False, "followup@example.com": True}
    assert all("unsubscribe?token=" in kw["unsubscribe_url"] for kw in sent)
    assert all(kw["cta_url"].endswith("/dashboard?open=self-assessment") for kw in sent)
    assert first["skipped_safety"] == 2 and first["skipped_unsubscribed"] == 1 and first["skipped_no_email"] == 1
    assert second["sent"] == 0  # idempotent: nothing re-sent on the next run
