"""Iter 199 — Individual → Joint bridge · variant copy + CTR tracking.

Locks:
  * Default variants are returned when no admin override exists.
  * Admin update accepts one or both variants and persists them.
  * CTA route validator rejects `//evil.com/...` and non-`/` paths.
  * Impression + click tracking rows land in `nudge_copy_events`.
  * Analytics roll-up computes per-variant CTR correctly.
  * Public endpoints require no auth; admin endpoints reject non-admins.
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

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe():
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            await c[DB_NAME].nudge_copy_config.delete_many(
                {"key": "individual_to_joint_bridge"},
            )
            await c[DB_NAME].nudge_copy_history.delete_many(
                {"key": "individual_to_joint_bridge"},
            )
            await c[DB_NAME].nudge_copy_events.delete_many(
                {"key": "individual_to_joint_bridge"},
            )
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_run())
    loop.close()
    yield


def _mock_admin(app):
    from analytics_routes import require_admin
    from models import UserPublic
    admin = UserPublic(
        user_id="iter199-admin",
        email="mattsossi@bsossi.com",
        name="Admin",
        created_at=datetime.now(timezone.utc).isoformat(),
        is_guest=False,
    )
    app.dependency_overrides[require_admin] = lambda: admin


# ---------------------------------------------------------------------------
# Public GET — defaults come through when no admin has customised.
# ---------------------------------------------------------------------------

def test_public_bridge_copy_returns_defaults_when_empty(client):
    r = client.get("/api/public/nudge-copy/individual-to-joint-bridge")
    assert r.status_code == 200
    body = r.json()
    assert body["is_default"] is True
    assert body["cleared"]["eyebrow"].startswith("When you're ready to go further")
    assert body["concerned"]["eyebrow"].startswith("When you're ready, on your own timeline")
    # Both variants ship every field the frontend renders.
    for key in ("eyebrow", "headline", "body", "cta_label", "cta_route"):
        assert key in body["cleared"]
        assert key in body["concerned"]


# ---------------------------------------------------------------------------
# Admin write — merges variants, persists, drops is_default flag.
# ---------------------------------------------------------------------------

def test_admin_update_only_cleared_leaves_concerned_default(client):
    from server import app
    _mock_admin(app)
    r = client.post("/api/admin/nudge-copy/individual-to-joint-bridge", json={
        "cleared": {
            "eyebrow": "Cleared eyebrow tweak",
            "headline": "Compare with your co-parent",
            "body": "Test body long enough to pass validators please.",
            "cta_label": "See sample",
            "cta_route": "/samples",
        },
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cleared"]["headline"] == "Compare with your co-parent"
    # Concerned variant still shows the default because we didn't touch it.
    assert body["concerned"]["eyebrow"].startswith("When you're ready, on your own timeline")
    assert body["is_default"] is False
    app.dependency_overrides.clear()


def test_admin_update_rejects_offsite_cta_route(client):
    from server import app
    _mock_admin(app)
    r = client.post("/api/admin/nudge-copy/individual-to-joint-bridge", json={
        "concerned": {
            "eyebrow": "Concerned eyebrow ok",
            "headline": "Safe paths only",
            "body": "Test body long enough to pass validators please.",
            "cta_label": "Off site",
            "cta_route": "//evil.example.com/steal",
        },
    })
    assert r.status_code == 422
    app.dependency_overrides.clear()


def test_admin_update_requires_at_least_one_variant(client):
    from server import app
    _mock_admin(app)
    r = client.post("/api/admin/nudge-copy/individual-to-joint-bridge", json={
        "note": "no variants supplied",
    })
    assert r.status_code == 400
    app.dependency_overrides.clear()


def test_admin_update_writes_history_row(client):
    from server import app
    _mock_admin(app)
    client.post("/api/admin/nudge-copy/individual-to-joint-bridge", json={
        "cleared": {
            "eyebrow": "Cleared eyebrow tweak v2",
            "headline": "Compare with your co-parent",
            "body": "Test body long enough to pass validators please.",
            "cta_label": "See sample",
            "cta_route": "/samples",
        },
    })

    async def _count():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            n = await c[DB_NAME].nudge_copy_history.count_documents({
                "key": "individual_to_joint_bridge",
                "variant": "cleared",
            })
        finally:
            c.close()
        return n
    loop = asyncio.get_event_loop_policy().new_event_loop()
    n = loop.run_until_complete(_count())
    loop.close()
    assert n == 1
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Public tracking — insert impression + click rows.
# ---------------------------------------------------------------------------

def test_track_event_persists_row_anonymously(client):
    r = client.post(
        "/api/public/nudge-copy/individual-to-joint-bridge/track",
        json={"variant": "cleared", "event": "impression"},
    )
    assert r.status_code == 204

    async def _last():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            doc = await c[DB_NAME].nudge_copy_events.find_one(
                {"key": "individual_to_joint_bridge"},
                sort=[("created_at", -1)],
            )
        finally:
            c.close()
        return doc
    loop = asyncio.get_event_loop_policy().new_event_loop()
    doc = loop.run_until_complete(_last())
    loop.close()
    assert doc is not None
    assert doc["variant"] == "cleared"
    assert doc["event"] == "impression"
    # No user_id association — public marketing surface.
    assert "user_id" not in doc


def test_track_event_rejects_unknown_variant(client):
    r = client.post(
        "/api/public/nudge-copy/individual-to-joint-bridge/track",
        json={"variant": "not-a-variant", "event": "impression"},
    )
    assert r.status_code == 422


def test_track_event_rejects_unknown_event(client):
    r = client.post(
        "/api/public/nudge-copy/individual-to-joint-bridge/track",
        json={"variant": "cleared", "event": "hover"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Analytics — per-variant CTR math.
# ---------------------------------------------------------------------------

def test_bridge_analytics_computes_per_variant_ctr(client):
    from server import app
    _mock_admin(app)
    # Seed 5 cleared impressions, 2 cleared clicks (CTR 40%)
    # + 3 concerned impressions, 0 concerned clicks (CTR 0%).
    for _ in range(5):
        client.post(
            "/api/public/nudge-copy/individual-to-joint-bridge/track",
            json={"variant": "cleared", "event": "impression"},
        )
    for _ in range(2):
        client.post(
            "/api/public/nudge-copy/individual-to-joint-bridge/track",
            json={"variant": "cleared", "event": "click",
                  "target": "sample-joint-preview"},
        )
    for _ in range(3):
        client.post(
            "/api/public/nudge-copy/individual-to-joint-bridge/track",
            json={"variant": "concerned", "event": "impression"},
        )

    r = client.get("/api/admin/nudge-copy/individual-to-joint-bridge/analytics")
    assert r.status_code == 200
    variants = r.json()["variants"]
    assert variants["cleared"]["impressions"] == 5
    assert variants["cleared"]["clicks"] == 2
    assert variants["cleared"]["ctr"] == 40.0
    assert variants["concerned"]["impressions"] == 3
    assert variants["concerned"]["clicks"] == 0
    assert variants["concerned"]["ctr"] == 0.0
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Admin analytics requires admin.
# ---------------------------------------------------------------------------

def test_analytics_requires_admin(client):
    r = client.get("/api/admin/nudge-copy/individual-to-joint-bridge/analytics")
    assert r.status_code in (401, 403)




def test_safety_assessment_page_shows_both_variants():
    p = os.path.join(
        os.path.dirname(__file__), "..", "..", "frontend", "src", "pages",
        "SafetyAssessment.jsx",
    )
    src = open(p).read()
    assert 'data-testid="safety-companion-cta-eyebrow"' in src
    assert 'data-testid="safety-concerned-cta"' in src
    # The concerned variant is gated on level < 3.
    assert "result.result.level < 3" in src
