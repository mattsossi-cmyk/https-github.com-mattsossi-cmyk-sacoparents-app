"""Tests for the post-event ("How was mediation?") survey flow."""
import os
import sys
import uuid

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
import survey_routes  # noqa: E402


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest_asyncio.fixture
async def cleanup(db):
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    yield user_id
    await db.post_event_surveys.delete_many({"user_id": user_id})


@pytest.mark.asyncio
async def test_schedule_post_event_survey_is_idempotent(db, cleanup):
    user_id = cleanup
    summary_id = f"sum_{uuid.uuid4().hex[:8]}"
    await survey_routes.schedule_post_event_survey(
        db, user_id=user_id, email="t@example.com", name="Test", summary_id=summary_id,
    )
    await survey_routes.schedule_post_event_survey(
        db, user_id=user_id, email="t@example.com", name="Test", summary_id=summary_id,
    )
    count = await db.post_event_surveys.count_documents({"user_id": user_id})
    assert count == 1


@pytest.mark.asyncio
async def test_schedule_skips_guest_without_email(db, cleanup):
    user_id = cleanup
    await survey_routes.schedule_post_event_survey(
        db, user_id=user_id, email=None, name="Guest", summary_id="sum_x",
    )
    count = await db.post_event_surveys.count_documents({"user_id": user_id})
    assert count == 0


@pytest.mark.asyncio
async def test_survey_token_and_submit_flow(base_url, api_client, db, cleanup):
    """Public token endpoints: fetch survey, submit, idempotency on re-submit."""
    user_id = cleanup
    summary_id = f"sum_{uuid.uuid4().hex[:8]}"
    await survey_routes.schedule_post_event_survey(
        db, user_id=user_id, email="t@example.com", name="Test Parent", summary_id=summary_id,
    )
    doc = await db.post_event_surveys.find_one({"user_id": user_id})
    token = doc["token"]

    # GET by token
    r = api_client.get(f"{base_url}/api/surveys/post-event/by-token/{token}")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["user_name"] == "Test Parent"
    assert isinstance(payload["questions"], list) and len(payload["questions"]) > 5

    # POST submit — happy path, only known question ids retained.
    responses = {
        "ease_of_use": "Easy",
        "nps": 9,
        "primary_reason": "Preparing for mediation",
        "most_valuable": "The summary report",
        "improvements": "More videos",
        "assessment_helpfulness": "Very Helpful",
        "agreement_helpfulness": "Very Helpful",
        "needs_statement_helpfulness": "Very Helpful",
        "preparedness_change": "More Prepared",
        "child_focus_agreement": "Strongly Agree",
        "bogus_field": "should be dropped",
    }
    r = api_client.post(
        f"{base_url}/api/surveys/post-event/submit/{token}", json={"responses": responses}
    )
    assert r.status_code == 200, r.text

    stored = await db.post_event_surveys.find_one({"user_id": user_id})
    assert stored["status"] == "responded"
    assert "bogus_field" not in stored["responses"]
    assert stored["responses"]["nps"] == 9

    # Re-submit should now 409.
    r = api_client.post(
        f"{base_url}/api/surveys/post-event/submit/{token}", json={"responses": {"nps": 10}}
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_invalid_token_returns_404(base_url, api_client):
    r = api_client.get(f"{base_url}/api/surveys/post-event/by-token/this-is-not-real")
    assert r.status_code == 404
