"""Tests for the 2-week post-summary check-in flow."""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
import checkin_routes  # noqa: E402


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest_asyncio.fixture
async def cleanup(db):
    uid = f"checkin_test_{uuid.uuid4().hex[:8]}"
    yield uid
    await db.post_summary_checkins.delete_many({"user_id": uid})


def _iso(dt):
    return dt.isoformat()


@pytest.mark.asyncio
async def test_schedule_is_idempotent(db, cleanup):
    uid = cleanup
    sid = f"sum_{uuid.uuid4().hex[:8]}"
    for _ in range(2):
        await checkin_routes.schedule_post_summary_checkin(
            db, user_id=uid, email="t@example.com", name="Test", summary_id=sid,
        )
    n = await db.post_summary_checkins.count_documents({"user_id": uid})
    assert n == 1


@pytest.mark.asyncio
async def test_schedule_skips_demo_emails(db, cleanup):
    uid = cleanup
    await checkin_routes.schedule_post_summary_checkin(
        db, user_id=uid, email="guest_x@demo.local", name="G", summary_id="sum_x",
    )
    await checkin_routes.schedule_post_summary_checkin(
        db, user_id=uid, email=None, name="G", summary_id="sum_y",
    )
    n = await db.post_summary_checkins.count_documents({"user_id": uid})
    assert n == 0


@pytest.mark.asyncio
async def test_scheduled_14_days_in_future(db, cleanup):
    uid = cleanup
    await checkin_routes.schedule_post_summary_checkin(
        db, user_id=uid, email="t@example.com", name="Test", summary_id="sum_z",
    )
    doc = await db.post_summary_checkins.find_one({"user_id": uid})
    sched = datetime.fromisoformat(doc["scheduled_send_at"])
    delta = sched - datetime.now(timezone.utc)
    # Allow a small window for clock skew between insert + read.
    assert timedelta(days=13, hours=23) < delta <= timedelta(days=14, minutes=1)
    assert doc["status"] == "pending"
    assert doc["sent_at"] is None


@pytest.mark.asyncio
async def test_send_due_sends_and_marks_sent(db, cleanup):
    uid = cleanup
    # Insert a doc that's already past its scheduled time.
    await db.post_summary_checkins.insert_one({
        "checkin_id": f"chk_{uuid.uuid4().hex[:8]}",
        "user_id": uid,
        "summary_id": "sum_a",
        "email": "t@example.com",
        "name": "Test",
        "status": "pending",
        "created_at": _iso(datetime.now(timezone.utc) - timedelta(days=15)),
        "scheduled_send_at": _iso(datetime.now(timezone.utc) - timedelta(minutes=5)),
        "sent_at": None,
    })

    with (
        patch.object(checkin_routes, "_build_recap_text", new=AsyncMock(return_value="Recap text")),
        patch.object(checkin_routes.email_service, "send_post_summary_checkin") as fake_send,
    ):
        await checkin_routes._send_due(db)

    fake_send.assert_called_once()
    kwargs = fake_send.call_args.kwargs
    assert kwargs["to_email"] == "t@example.com"
    assert kwargs["recap_text"] == "Recap text"

    doc = await db.post_summary_checkins.find_one({"user_id": uid})
    assert doc["status"] == "sent"
    assert doc["sent_at"] is not None


@pytest.mark.asyncio
async def test_send_due_skips_future_scheduled(db, cleanup):
    uid = cleanup
    # Insert a doc that's not yet due.
    await db.post_summary_checkins.insert_one({
        "checkin_id": f"chk_{uuid.uuid4().hex[:8]}",
        "user_id": uid,
        "summary_id": "sum_b",
        "email": "t@example.com",
        "name": "Test",
        "status": "pending",
        "created_at": _iso(datetime.now(timezone.utc)),
        "scheduled_send_at": _iso(datetime.now(timezone.utc) + timedelta(days=14)),
        "sent_at": None,
    })

    with patch.object(checkin_routes.email_service, "send_post_summary_checkin") as fake_send:
        await checkin_routes._send_due(db)

    fake_send.assert_not_called()
    doc = await db.post_summary_checkins.find_one({"user_id": uid})
    assert doc["status"] == "pending"
    assert doc["sent_at"] is None
