import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

import email_service  # noqa: E402
from court_checklist import progress_rows  # noqa: E402
from requested_reminders import make_unsubscribe_token, read_unsubscribe_token, send_requested_reminders  # noqa: E402

NOW = datetime(2026, 6, 8, 14, tzinfo=timezone.utc)  # a Monday, 9am Central


async def _seed(db):
    await db.users.insert_many([{"user_id": u, "email": f"{u}@example.com", "name": f"{u.title()} Parent"}
                                for u in ("wait2", "done", "flagged", "unsub", "casepar", "codepar")])
    await db.court_requested.insert_many([
        {"user_id": "wait2", "keys": ["coparent", "self"]},
        {"user_id": "done", "keys": ["self"]},
        {"user_id": "flagged", "keys": ["self"]},
        {"user_id": "unsub", "keys": ["self"], "reminders_off": True},
    ])
    await db.self_assessment_history.insert_one({"user_id": "done", "completed_at": "2026-06-01T10:00:00+00:00", "answers": {"q1": 5}})
    await db.portal_state.insert_many([
        {"user_id": "flagged", "safety_ack": {"flagged": True}},
        {"user_id": "codepar", "court_key": "CC-TEST01"},
    ])
    await db.joint_alignment_cases.insert_one({
        "case_id": "SA-TEST01", "status": "in_progress", "assessment_type": "co-parenting",
        "assigned_steps": [{"assessment_type": "medical", "required": True}],
        "parents": [{"user_id": "casepar", "email": "casepar@example.com"}],
    })
    await db.portal_court_keys.insert_one({"case_id": "CC-TEST01", "requested": ["parallel"], "revoked_at": None, "created_by": "pro"})


def test_weekly_requested_reminder_sweep(monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "send_requested_reminder", lambda **kw: sent.append(kw))

    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_req_reminders"
        await client.drop_database(name)
        db = client[name]
        try:
            await _seed(db)
            first = await send_requested_reminders(db, now=NOW)
            second = await send_requested_reminders(db, now=NOW)
            rows = await progress_rows(db, "done", ["self", "medical"])
            return first, second, rows
        finally:
            await client.drop_database(name)

    first, second, rows = asyncio.run(run())
    by_email = {kw["to_email"]: kw["waiting"] for kw in sent}
    # Parent ticks, joint-case requests and court-code requests all count; finished / flagged / unsubscribed skipped.
    assert by_email == {"wait2@example.com": 2, "casepar@example.com": 1, "codepar@example.com": 1}
    assert first["all_done"] == 1 and first["skipped_safety"] == 1 and first["skipped_unsubscribed"] == 1
    assert all("/api/court-path/reminders/unsubscribe?token=" in kw["unsubscribe_url"] for kw in sent)
    assert second["sent"] == 0 and second["already_sent"] == 3  # once per week
    # Professional view is status-only.
    assert rows == [{"key": "self", "title": "Self-Assessment", "status": "done", "finished_at": "2026-06-01T10:00:00+00:00"},
                    {"key": "medical", "title": "Medical Assessment", "status": "todo", "finished_at": None}]


def test_reminder_email_is_neutral(monkeypatch):
    out = {}
    monkeypatch.setattr(email_service, "_send", lambda **kw: out.update(kw))
    email_service.send_requested_reminder(to_email="a@example.com", waiting=2, cta_url="https://x/login",
                                          unsubscribe_url="https://x/unsub", first_name="Avery")
    body = out["html"] + out["text"] + out["subject"]
    assert "You have 2 assessments waiting for you" in body and "https://x/unsub" in body and "Sign in" in body
    for word in ("Co-Parenting", "Self-Assessment", "Medical", "Educational", "Psychological", "Foundation", "Parallel"):
        assert word not in body


def test_unsubscribe_token_roundtrip():
    assert read_unsubscribe_token(make_unsubscribe_token("u1")) == "u1"
    assert read_unsubscribe_token("garbage") is None
