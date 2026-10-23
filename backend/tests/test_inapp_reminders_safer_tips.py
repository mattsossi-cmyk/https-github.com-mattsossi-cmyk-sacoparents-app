"""No check-in / progress emails (in-app only) and safer Co-Parenting report tips on shared safety concerns."""
from __future__ import annotations

import os
import sys
import uuid

import pytest
import yaml
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from server import app  # noqa: E402

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
JOINT = "Schedule a joint parent-teacher meeting."
SEPARATE = "Ask the school for separate parent-teacher conferences."


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    with TestClient(app) as c:
        yield c


def _parent(client):
    email = f"safer.{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "Safer Parent",
                                                 "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]["user_id"]


def _seed_report(uid: str) -> None:
    _db.cp_reports.replace_one({"user_id": uid}, {
        "report_id": f"cp_{uuid.uuid4().hex[:12]}", "user_id": uid, "generated_at": "2026-10-23T10:00:00+00:00",
        "scores": {}, "report": {"sections": [{"id": "education", "title": "Education", "findings": [],
                                               "recommendations": [JOINT, "Request the school send communications to both parents."]}]},
    }, upsert=True)


def _recs(client, h):
    return client.get("/api/coparenting/report", headers=h).json()["report"]["sections"][0]["recommendations"]


def test_joint_tips_swapped_only_when_the_parent_shared_concerns(client):
    h, uid = _parent(client)
    _seed_report(uid)
    assert _recs(client, h)[0] == JOINT
    client.put("/api/self-journey/me", headers=h, json={"safety": {"status": "concern"}})
    recs = _recs(client, h)
    assert recs[0] == SEPARATE and recs[1] == "Request the school send communications to both parents."
    stored = _db.cp_reports.find_one({"user_id": uid})["report"]["sections"][0]["recommendations"][0]
    assert stored == JOINT  # the saved report is untouched; a "clear" pick brings the original tips back
    client.put("/api/self-journey/me", headers=h, json={"safety": {"status": "clear"}})
    assert _recs(client, h)[0] == JOINT


def test_existing_safety_flag_also_swaps_tips(client):
    h, uid = _parent(client)
    _seed_report(uid)
    _db.portal_state.update_one({"user_id": uid}, {"$set": {"user_id": uid, "safety_ack": {"flagged": True}}}, upsert=True)
    assert _recs(client, h)[0] == SEPARATE


def test_report_pdf_uses_the_safer_tips(client):
    from pypdf import PdfReader
    import io

    h, uid = _parent(client)
    _seed_report(uid)
    client.put("/api/self-journey/me", headers=h, json={"safety": {"status": "concern"}})
    r = client.get("/api/coparenting/report/pdf", headers=h)
    assert r.status_code == 200
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages).replace("\n", " ")
    assert "joint parent-teacher" not in text and "separate parent-teacher" in text


def test_retake_and_weekly_emails_are_off():
    src = open(os.path.join(os.path.dirname(__file__), "..", "cron_routes.py")).read()
    assert "send_reassess_reminders" not in src and "send_weekly_notes" not in src
    crons = yaml.safe_load(open("/app/.emergent/crons.yml"))["crons"]
    assert next(c for c in crons if c["name"] == "sj-weekly-note")["enabled"] is False
    assert next(c for c in crons if c["name"] == "sa-reassess-reminder")["enabled"] is True


def test_weekly_note_cron_is_a_no_op(client):
    secret = os.environ["WEBHOOK_CRON_SECRET"]
    r = client.post("/api/cron/self-journey-weekly-note", headers={"Authorization": f"Bearer {secret}"})
    assert r.status_code == 200 and r.json()["stopped"] is True
    assert client.post("/api/cron/self-journey-weekly-note").status_code == 401
