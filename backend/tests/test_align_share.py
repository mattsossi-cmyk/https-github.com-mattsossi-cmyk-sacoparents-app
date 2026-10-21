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
    assert client.get(SHARE, headers=h).json() == {"choice": None, "decided_at": None, "reask": False}
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


def test_only_linked_parents_can_set_a_choice(client):
    _, h, _ = _parent(client, linked=False)
    r = client.put(SHARE, headers=h, json={"share": True})
    assert r.status_code == 409, r.text
    assert client.get(SHARE, headers=h).json()["choice"] is None


def test_unlinking_resets_the_choice_and_relinking_does_not_restart_sharing(client):
    email, h, _ = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    client.put(SHARE, headers=h, json={"share": True})
    assert "communication_readiness" in _export(client, email)
    assert client.delete("/api/integrations/align-link", headers=h).json()["linked"] is False
    assert client.get(SHARE, headers=h).json() == {"choice": None, "decided_at": None, "reask": False}
    code = client.post("/api/link-codes", headers=h, json={}).json()["code"]
    assert client.post("/api/integrations/verify-link-code", headers=KEY, json={"code": code}).status_code == 200
    assert "communication_readiness" not in _export(client, email)


def test_privacy_notice_describes_the_sharing():
    from pathlib import Path
    page = " ".join((Path(__file__).resolve().parents[2] / "frontend/src/pages/privacyNotice/PrivacyNoticeContent.jsx").read_text().split())
    for s in ("Sharing with SACOparentsAlign.",
              "If you link your account to SACOparentsAlign with a link code, SACOparentsAlign can read your Situation Snapshot and Special Needs summaries.",
              "Your four Communication Style answers (your three choices and the message you pasted, with the date you answered) are sent to "
              "SACOparentsAlign only if you say yes.",
              "There they are seen only by the professionals assigned to your case and, when needed, SA CoParents administrators.",
              "They never go to your co-parent, the court, or any report.",
              "You can change your answer at any time on your Account page.",
              "Your reflection and Foundation Statement answers are never sent to SACOparentsAlign."):
        assert s in page, s


def test_yes_also_carries_aligns_five_field_names(client):
    email, h, _ = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    client.put(SHARE, headers=h, json={"share": True})
    cr = _export(client, email)["communication_readiness"]
    assert cr["cr_conflict"] == FOUR[0]["answer"] and cr["cr_child"] == FOUR[1]["answer"]
    assert cr["cr_direct"] == FOUR[2]["answer"] and cr["cr_channel"] == FOUR[3]["answer"]
    assert cr["completed_at"] == cr["answered_at"]


def test_a_yes_under_older_wording_is_asked_again_and_shares_nothing(client):
    email, h, uid = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    client.put(SHARE, headers=h, json={"share": True})
    _db.align_share_choices.update_one({"user_id": uid}, {"$unset": {"wording_version": ""}})
    assert client.get(SHARE, headers=h).json() == {"choice": None, "decided_at": None, "reask": True}
    body = _export(client, email)
    assert "communication_readiness" not in body and "MARKER-SAMPLE" not in json.dumps(body)
    # Skip for now -> plain "not chosen", no more asking.
    assert client.delete(SHARE, headers=h).json() == {"choice": None, "decided_at": None, "reask": False}
    assert client.put(SHARE, headers=h, json={"share": True}).json()["reask"] is False
    assert _export(client, email)["communication_readiness"]["answers"] == FOUR


def test_an_earlier_no_stays_no(client):
    _, h, uid = _parent(client)
    client.put(SHARE, headers=h, json={"share": False})
    _db.align_share_choices.update_one({"user_id": uid}, {"$unset": {"wording_version": ""}})
    assert client.get(SHARE, headers=h).json()["choice"] == "no"


class _FakeAsyncClient:
    sent: list = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeAsyncClient.sent.append({"url": url, "json": json, "headers": headers})

        class R:
            status_code = 200
        return R()


def test_import_push_is_off_until_both_settings_exist(client, monkeypatch):
    import align_share
    _FakeAsyncClient.sent = []
    monkeypatch.setattr(align_share.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.delenv("ALIGN_IMPORT_URL", raising=False)
    monkeypatch.setenv("ALIGN_IMPORT_KEY", "k")
    _, h, _ = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    client.put(SHARE, headers=h, json={"share": True})
    assert _FakeAsyncClient.sent == []


def test_import_push_sends_only_the_five_fields_after_a_yes(client, monkeypatch):
    import align_share
    _FakeAsyncClient.sent = []
    monkeypatch.setattr(align_share.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setenv("ALIGN_IMPORT_URL", "https://align.example/api/integrations/import")
    monkeypatch.setenv("ALIGN_IMPORT_KEY", "test-import-key")
    email, h, uid = _parent(client)
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    assert _FakeAsyncClient.sent == []  # saved but not shared yet
    client.put(SHARE, headers=h, json={"share": True})
    assert len(_FakeAsyncClient.sent) == 1
    sent = _FakeAsyncClient.sent[0]
    assert sent["url"] == "https://align.example/api/integrations/import"
    assert sent["headers"] == {"X-Integration-Key": "test-import-key"}
    assert set(sent["json"]) == {"case_id", "email", "cr_conflict", "cr_direct", "cr_channel", "cr_child", "completed_at"}
    assert sent["json"]["email"] == email and sent["json"]["cr_conflict"] == FOUR[0]["answer"]
    client.put(SHARE, headers=h, json={"share": False})
    client.put("/api/mediation/comm-style", headers=h, json=COMM)
    assert len(_FakeAsyncClient.sent) == 1  # "no" -> nothing more is sent
    _db.portal_state.update_one({"user_id": uid}, {"$set": {"user_id": uid, "safety_ack": {"flagged": True}}}, upsert=True)
    client.put(SHARE, headers=h, json={"share": True})
    assert len(_FakeAsyncClient.sent) == 1  # older concerning result -> never sent
