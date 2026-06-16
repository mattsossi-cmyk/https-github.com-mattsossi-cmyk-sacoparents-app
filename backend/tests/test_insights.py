"""Tests for the admin weekly insights endpoint."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
import insights_routes  # noqa: E402


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _purge(week_iso: str):
    async def run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            await client[DB_NAME].weekly_insights.delete_many({"week_iso": week_iso})
        finally:
            client.close()

    asyncio.run(run())


@pytest.fixture
def cleanup_week():
    week = insights_routes._week_iso(datetime.now(timezone.utc))
    yield week
    _purge(week)


def test_admin_endpoints_require_auth(base_url, api_client):
    r = api_client.get(f"{base_url}/api/insights/admin/weekly")
    assert r.status_code == 401


def _make_user(api_client, base_url):
    email = f"ins_{uuid.uuid4().hex[:10]}@example.com"
    r = api_client.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "name": "Insights Test", "password": "TestPass123!"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def test_admin_endpoints_reject_non_admin(base_url, api_client):
    _, token = _make_user(api_client, base_url)
    r = api_client.get(
        f"{base_url}/api/insights/admin/weekly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_gather_signals_returns_structured_payload(cleanup_week):
    """End-to-end signal gathering against the real DB — never raises even when
    the collections are empty, returns sensible defaults."""

    async def run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            sig = await insights_routes._gather_signals(client[DB_NAME])
        finally:
            client.close()
        assert sig["window_days"] == 7
        for k in (
            "new_users",
            "new_guests",
            "summaries_generated",
            "legal_acks",
            "survey_responses",
            "invites_sent",
            "invites_accepted",
            "journal_entries",
        ):
            assert k in sig["counts"]
            assert isinstance(sig["counts"][k], int)
        assert isinstance(sig["most_valuable_text"], list)
        assert isinstance(sig["improvements_text"], list)
        assert isinstance(sig["journal_snippets"], list)

    asyncio.run(run())


def test_build_and_cache_writes_to_mongo(cleanup_week):
    """If we mock the LLM, _build_and_cache writes a doc keyed by ISO week."""
    week = cleanup_week
    fake_briefing = {
        "headline": "Sparse week — too little data to call.",
        "highlights": [],
        "user_voice_themes": [],
        "concerning_patterns": [],
        "recommended_actions": ["Add a real test user"],
        "closing_note": "More data next week.",
    }

    async def run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            db = client[DB_NAME]
            with patch.object(
                insights_routes,
                "_generate_briefing",
                new=AsyncMock(return_value=fake_briefing),
            ):
                doc = await insights_routes._build_and_cache(db)
            assert doc["week_iso"] == week
            assert doc["briefing"] == fake_briefing
            stored = await db.weekly_insights.find_one(
                {"week_iso": week}, {"_id": 0}
            )
            assert stored is not None
            assert stored["briefing"]["headline"] == fake_briefing["headline"]
        finally:
            client.close()

    asyncio.run(run())
