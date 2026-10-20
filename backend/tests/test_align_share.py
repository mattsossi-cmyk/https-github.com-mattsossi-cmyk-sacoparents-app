"""Align export: Communication Style answers only with the parent's yes; reflection answers never.

In-process (TestClient) like test_iter137_sibling_integration.py, so no webhook secret is needed.
"""
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

SECRET = "test-align-share-" + uuid.uuid4().hex
KEY = {"X-Integration-Key": SECRET}
SHARE = "/api/integrations/align-share/communication-readiness"
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_users: list[str] = []

COMM = {"answers": {"q1": "balanced", "q2": "escalator", "q3": "passive"}, "free_text_sample": "MARKER-SAMPLE please confirm pickup at 5."}
FOUR = [
    {"question": "When my co-parent texts me about a conflict, my first instinct is to…", "answer": "Pause, then reply briefly and factually."},
    {"question": "When disagreements arise about our child, I most often…", "answer": "Make my point loudly so it lands."},
    {"question": "If I had to be honest, the pattern I'd most like to change is…", "answer": "Going passive when I'm hurt."},
    {"question": "A recent message I sent", "answer": "MARKER-SAMPLE please confirm pickup at 5."},
]
REFLECTION_KEYS = {"reflection", "foundation_statement", "child_lens", "own_part", "best_outcome", "coparent_feedback",
                   "my_part", "best_case", "coparent_lens", "canonical", "release"}


@pytest.fixture(scope="module")
def client():
    os.environ["INTEGRATION_SHARED_SECRET"] = SECRET
    app.state.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    with TestClient(app) as c:
        yield c
    for uid in _users:
        for coll in ("users", "prep_data", "align_links", "align_access_log", "align_share_choices", "link_codes", "portal_state"):
            _db[coll].delete_many({"user_id": uid})


def _parent(client, linked=True):
    email = f"test_alignshare_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "Share Test",
                                                "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    _users.append(r.json()["user"]["user_id"])
    if linked:
        code = client.post("/api/link-codes", headers=h, json={}).json()["code"]
        assert client.post("/api/integrations/verify-link-code", headers=KEY, json={"code": code}).status_code == 200
    return email, h, r.json()["user"]["user_id"]


def _export(client, email):
    r = client.get(f"/api/integrations/export-assessments?email={email}", headers=KEY)
    assert r.status_code == 200, r.text
    return r.json()


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_choice_needs_sign_in(client):
    assert client.get(SHARE).status_code == 401
    assert client.put(SHARE, json={"share": True}).status_code == 401


def test_skipped_sends_no_field(client):
    email, h, _ = _parent(client)
    assert client.put("/api/mediation/comm-style", headers=h, json=COMM).status_code == 200
    assert client.get(SHARE, headers=h).json() == {"choice": None, "decided_at": None}
    body = _export(client, email)
    assert "communication_readiness" not in body
    assert "MARKER-SAMPLE" not in json.dumps(body)


def test_yes_sends_the_four_answers_in_plain_words(client):
    email, h, _ = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    r = client.put(SHARE, headers=h, json={"share": True})
    assert r.status_code == 200 and r.json()["choice"] == "yes" and r.json()["decided_at"]
    assert "no-store" in r.headers.get("cache-control", "")
    cr = _export(client, email)["communication_readiness"]
    assert cr["answers"] == FOUR
    assert cr["answered_at"] and cr["answered_at"][:4].isdigit()
    reads = client.get("/api/integrations/align-link", headers=h).json()["recent_reads"]
    assert reads[0]["what"] == "Your Situation Snapshot, Special Needs summaries and Communication Style answers"


def test_no_sends_nothing_and_the_parent_can_change_it_later(client):
    email, h, _ = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    assert client.put(SHARE, headers=h, json={"share": False}).json()["choice"] == "no"
    body = _export(client, email)
    assert "communication_readiness" not in body and "MARKER-SAMPLE" not in json.dumps(body)
    assert client.get("/api/integrations/align-link", headers=h).json()["recent_reads"][0]["what"] == \
        "Your Situation Snapshot and Special Needs summaries"
    client.put(SHARE, headers=h, json={"share": True})
    assert _export(client, email)["communication_readiness"]["answers"] == FOUR
    client.put(SHARE, headers=h, json={"share": False})
    assert "communication_readiness" not in _export(client, email)


def test_yes_without_answers_sends_no_field(client):
    email, h, _ = _parent(client)
    client.put(SHARE, headers=h, json={"share": True})
    assert "communication_readiness" not in _export(client, email)


def test_no_reflection_field_is_ever_sent(client):
    email, h, _ = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    client.put(SHARE, headers=h, json={"share": True})
    marks = {k: f"MARKER-REFLECT-{k}" for k in ("child_lens", "own_part", "best_outcome", "coparent_feedback", "release")}
    assert client.put("/api/mediation/reflection", headers=h, json=marks).status_code == 200
    assert client.put("/api/mediation/readiness", headers=h, json={"answers": {"listen": 5, "calm": 1}}).status_code == 200
    body = _export(client, email)
    text = json.dumps(body)
    assert not REFLECTION_KEYS & set(_keys(body)), REFLECTION_KEYS & set(_keys(body))
    assert "MARKER-REFLECT" not in text
    assert body["situation_snapshot"]["readiness"] is None and '"listen"' not in text
    pdf = client.get(f"/api/integrations/foundation-statement.pdf?email={email}", headers=KEY)
    assert pdf.status_code == 409 and b"MARKER-REFLECT" not in pdf.content


def test_parent_with_old_safety_result_never_gets_the_field(client):
    email, h, uid = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    client.put(SHARE, headers=h, json={"share": True})
    _db.portal_state.update_one({"user_id": uid}, {"$set": {"user_id": uid, "safety_ack": {"flagged": True}}}, upsert=True)
    body = _export(client, email)
    assert "communication_readiness" not in body and "MARKER-SAMPLE" not in json.dumps(body)
