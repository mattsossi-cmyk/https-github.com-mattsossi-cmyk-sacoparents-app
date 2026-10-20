"""Iter 195 — Admin reminder-analytics tile.

Locks the CONTRACT the new `ReminderAnalyticsTile` component on
`/admin` relies on:

  * `GET /api/admin/alignment-reflections/analytics`
      - Requires an authenticated admin (403 otherwise).
      - Response shape MUST include `total` + `subjects`.
      - Each row exposes the four numbers the tile prints:
          sent · open_rate · click_rate · click_through_open.
      - Empty DB → totals are zero, subjects list is empty, and
        the endpoint STILL returns 200 (the tile's empty-state
        depends on that).

The tile hides itself when the endpoint fails, but a silently
broken contract (missing keys, 500 on empty DB) is a regression
we want to catch here — not in Sentry after ops squints at a
missing tile.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe_reminders():
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            await c[DB_NAME].alignment_reflection_reminders.delete_many(
                {"target_email": {"$regex": "iter195"}},
            )
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_run())
    yield
    loop.run_until_complete(_run())
    loop.close()


def _admin_client(client):
    """Fake an authed admin using the require_admin dependency
    override — same pattern as the other analytics tests."""
    from server import app as _app
    from analytics_routes import require_admin
    from models import UserPublic

    admin = UserPublic(
        user_id="iter195-admin",
        email="mattsossi@bsossi.com",
        name="Admin",
        created_at=datetime.now(timezone.utc).isoformat(),
        is_guest=False,
    )
    _app.dependency_overrides[require_admin] = lambda: admin
    yield client
    _app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def as_admin(client):
    yield from _admin_client(client)


# ---------------------------------------------------------------------------
# Auth gating.
# ---------------------------------------------------------------------------

def test_analytics_endpoint_requires_admin(client):
    """Unauthed callers MUST NOT see reminder analytics — the sweep
    can carry sensitive routing (subject names, timing) that we
    don't expose outside the admin taxonomy."""
    r = client.get("/api/admin/alignment-reflections/analytics")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Empty-DB contract — tile depends on this for the empty-state render.
# ---------------------------------------------------------------------------

def test_analytics_endpoint_returns_zeroed_shape_when_empty(as_admin):
    """The tile's empty-state renders based on `total.sent === 0`.
    That means the endpoint MUST return 200 with a well-formed
    envelope even when the collection is empty."""
    async def _wipe_all():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            await c[DB_NAME].alignment_reflection_reminders.delete_many({})
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_wipe_all())
    loop.close()

    r = as_admin.get("/api/admin/alignment-reflections/analytics")
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and "subjects" in body
    assert body["subjects"] == []
    total = body["total"]
    for key in (
        "sent", "opened", "clicked",
        "open_rate", "click_rate", "click_through_open",
    ):
        assert key in total, f"totals missing key: {key}"
    assert total["sent"] == 0
    assert total["open_rate"] == 0.0
    assert total["click_rate"] == 0.0


# ---------------------------------------------------------------------------
# Populated-DB contract — per-subject rows expose the four numbers
# the frontend table prints.
# ---------------------------------------------------------------------------

def _seed_reminder_rows():
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            base = "iter195_analytics_tile@test.local"
            now = datetime.now(timezone.utc)
            docs = [
                # 3 co_parenting: 2 open, 1 click
                {"target_email": base, "subject": "co_parenting",
                 "sent_at": now,
                 "opened_at": now, "clicked_at": now},
                {"target_email": base, "subject": "co_parenting",
                 "sent_at": now, "opened_at": now},
                {"target_email": base, "subject": "co_parenting",
                 "sent_at": now},
                # 1 communication: 0 open
                {"target_email": base, "subject": "communication",
                 "sent_at": now},
            ]
            await db.alignment_reflection_reminders.insert_many(docs)
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_run())
    loop.close()


def test_analytics_endpoint_per_subject_shape_matches_tile_expectations(as_admin):
    _seed_reminder_rows()
    r = as_admin.get("/api/admin/alignment-reflections/analytics")
    assert r.status_code == 200
    body = r.json()
    assert body["total"]["sent"] >= 4

    by = {s["subject"]: s for s in body["subjects"]}
    # Both subjects seeded appear in the response.
    assert "co_parenting" in by
    assert "communication" in by

    cp = by["co_parenting"]
    # These are exactly the keys the JSX in AdminDashboard reads.
    for key in (
        "subject", "sent", "opened", "clicked",
        "open_rate", "click_rate", "click_through_open",
    ):
        assert key in cp, f"per-subject row missing key: {key}"
    assert cp["sent"] == 3
    assert cp["opened"] == 2
    assert cp["clicked"] == 1
    # 2/3 opens → 66.7 · 1/3 clicks → 33.3 · 1/2 CTR-of-opens → 50.0
    assert cp["open_rate"] == 66.7
    assert cp["click_rate"] == 33.3
    assert cp["click_through_open"] == 50.0
