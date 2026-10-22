"""Self Journey guide progress: private per parent, safety pick stays here, unknown keys dropped."""
from __future__ import annotations

import json
import os
import sys
import uuid

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from server import app  # noqa: E402

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ME = "/api/self-journey/me"


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    with TestClient(app) as c:
        yield c


def _parent(client):
    email = f"sj.{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "SJ Parent",
                                                 "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]["user_id"]


def test_needs_sign_in(client):
    assert client.get(ME).status_code == 401
    assert client.put(ME, json={}).status_code == 401


def test_starts_empty_then_saves_and_reloads(client):
    _, h, _ = _parent(client)
    assert client.get(ME, headers=h).json() == {"progress": None}
    body = {"maxStepReached": 3, "safety": {"status": "clear", "completedAt": "2026-10-22T10:00:00Z"},
            "situation": {"currentSituation": "We share weekends", "bogus": "x"},
            "coparenting": {"approach": "cooperative", "agree": "Bedtimes", "disagree": ""},
            "childNeeds": {"opened": ["medical"]},
            "foundation": {"answers": {"values": "Kindness", "nope": "y"}, "draft": "My child needs calm.", "approved": True},
            "mediation": {"issues": "Holidays", "zzz": "dropped"}}
    saved = client.put(ME, headers=h, json=body).json()["progress"]
    assert saved["updatedAt"]
    got = client.get(ME, headers=h).json()["progress"]
    assert got["maxStepReached"] == 3 and got["safety"]["status"] == "clear"
    assert got["situation"] == {"currentSituation": "We share weekends"}
    assert got["foundation"]["answers"] == {"values": "Kindness"}
    assert got["mediation"] == {"issues": "Holidays"}
    assert got["coparenting"]["approach"] == "cooperative"


def test_safety_concern_never_keeps_working_together(client):
    _, h, _ = _parent(client)
    body = {"safety": {"status": "concern"}, "coparenting": {"approach": "cooperative"}}
    assert client.put(ME, headers=h, json=body).json()["progress"]["coparenting"]["approach"] is None


def test_bad_values_are_rejected(client):
    _, h, _ = _parent(client)
    assert client.put(ME, headers=h, json={"maxStepReached": 9}).status_code == 422
    assert client.put(ME, headers=h, json={"safety": {"status": "maybe"}}).status_code == 422
    assert client.put(ME, headers=h, json={"childNeeds": {"opened": ["school"]}}).status_code == 422


def test_each_parent_sees_only_their_own(client):
    _, h1, _ = _parent(client)
    _, h2, _ = _parent(client)
    client.put(ME, headers=h1, json={"situation": {"currentSituation": "PARENT-ONE-MARKER"}})
    assert client.get(ME, headers=h2).json() == {"progress": None}


def test_safety_pick_never_reaches_the_align_export(client, monkeypatch):
    monkeypatch.setenv("INTEGRATION_SHARED_SECRET", "sj-test-secret")
    email, h, _ = _parent(client)
    client.put(ME, headers=h, json={"safety": {"status": "concern"}, "situation": {"currentSituation": "SJ-MARKER"}})
    body = client.get(f"/api/integrations/export-assessments?email={email}", headers={"X-Integration-Key": "sj-test-secret"})
    text = json.dumps(body.json())
    assert "SJ-MARKER" not in text and "concern" not in text.lower().replace("concerns", "")


def test_journey_guide_topic_exists_and_needs_the_ai_notice(client):
    _, h, _ = _parent(client)
    r = client.post("/api/journey-guide/self-journey/chat", headers=h, json={"message": "Why is this first?", "section": "Safety"})
    assert r.status_code == 428
    assert client.post("/api/journey-guide/not-a-guide/chat", headers=h, json={"message": "hi"}).status_code in (404, 428)
