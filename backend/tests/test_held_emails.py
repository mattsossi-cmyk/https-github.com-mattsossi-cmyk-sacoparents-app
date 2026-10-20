"""Admin count of reminder emails held back for safety: counts only, no ids, small numbers masked."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from held_emails import COLL, held_counts, record_held  # noqa: E402
from tests.conftest import BASE_URL  # noqa: E402

API = f"{BASE_URL}/api/admin/safety-audit-log/held-emails"


def _scratch(fn):
    async def run():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        name = f"{os.environ['DB_NAME']}_test_held_emails"
        await client.drop_database(name)
        try:
            return await fn(client[name])
        finally:
            await client.drop_database(name)
            client.close()
    return asyncio.run(run())


def test_same_email_counts_once_and_no_user_id_is_kept():
    async def body(db):
        await record_held(db, "reassess", "user-abc", "e1:6w")
        await record_held(db, "reassess", "user-abc", "e1:6w")
        await record_held(db, "reassess", "user-abc", "e1:8w")
        rows = await db[COLL].find().to_list(None)
        return rows
    rows = _scratch(body)
    assert len(rows) == 2
    assert all(set(r) == {"_id", "kind", "at"} for r in rows)
    assert "user-abc" not in str(rows)


def test_counts_by_type_mask_small_numbers_and_skip_old_rows():
    async def body(db):
        for i in range(3):
            await record_held(db, "reassess", f"u{i}", "p")
        for i in range(6):
            await record_held(db, "weekly_note", f"u{i}", "p")
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        await db[COLL].insert_one({"_id": "old", "kind": "weekly_note", "at": old})
        return await held_counts(db)
    out = _scratch(body)
    by = {k["kind"]: k for k in out["kinds"]}
    assert out["days"] == 30
    assert out["total"] == {"count": 9, "fewer_than_5": False}
    assert by["reassess"] == {"kind": "reassess", "label": "Self-Assessment reassess reminder", "count": None, "fewer_than_5": True}
    assert by["weekly_note"]["count"] == 6
    assert by["draft_nudge"]["count"] == 0 and by["draft_nudge"]["fewer_than_5"] is False
    assert set(by) == {"reassess", "weekly_note", "requested", "pro_nudge", "compare_alert", "draft_nudge"}


def test_draft_nudge_for_held_parent_is_counted_once_per_week(monkeypatch):
    import email_service
    from guided_draft_nudge import send_guided_draft_nudges
    sent = []
    monkeypatch.setattr(email_service, "send_guided_draft_nudge", lambda **kw: sent.append(kw))

    async def body(db):
        uid = f"test-held-{uuid.uuid4().hex[:8]}"
        stale = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
        await db.users.insert_one({"user_id": uid, "email": f"{uid}@example.com", "name": "Held"})
        await db.portal_state.insert_one({"user_id": uid, "safety_ack": {"flagged": True},
                                          "guided_drafts": {"coparenting": {"updated_at": stale, "progress": {"step": 2}}}})
        first = await send_guided_draft_nudges(db)
        second = await send_guided_draft_nudges(db)
        return first, second, await db[COLL].count_documents({"kind": "draft_nudge"})
    first, second, held = _scratch(body)
    assert first["sent"] == 0 and second["sent"] == 0 and not sent
    assert held == 1


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize("who,code", [(None, 401), (("parent1@test.com", "TestPass123!"), 403)])
def test_endpoint_is_admin_only(who, code):
    r = requests.get(API, headers=_login(*who) if who else {}, timeout=30)
    assert r.status_code == code, r.text


def test_admin_gets_counts_only():
    r = requests.get(API, headers=_login("mattsossi@bsossi.com", "AdminPass123!"), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "no-store" in r.headers.get("cache-control", "")
    assert set(body) == {"days", "total", "kinds"}
    for k in body["kinds"]:
        assert set(k) == {"kind", "label", "count", "fewer_than_5"}
        assert (k["count"] is None) == k["fewer_than_5"]
