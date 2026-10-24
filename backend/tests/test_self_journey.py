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


def test_pdf_has_seven_sections_without_private_notes(client):
    from pypdf import PdfReader
    import io

    assert client.get("/api/self-journey/pdf").status_code == 401
    _, h, _ = _parent(client)
    secret = "PRIVATE-NOTE-XYZ"
    body = {
        "maxStepReached": 7, "safety": {"status": "concern"},
        "situation": {"currentSituation": secret}, "mediation": {"issues": secret},
        "coparenting": {"approach": "parallel", "agree": secret, "disagree": secret},
        "childNeeds": {"opened": ["medical"]},
        "foundation": {"draft": "We put our child first.", "approved": True, "approvedAt": "2026-10-23T10:00:00+00:00"},
    }
    assert client.put(ME, headers=h, json=body).status_code == 200
    r = client.get("/api/self-journey/pdf", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    for title in ("Parenting Situation Overview", "Self Assessment Reflections", "Co-Parenting Relationship",
                  "Child's Identified Needs", "Foundation Statement", "Mediation Preparation & Options",
                  "Next Steps & Available Resources"):
        assert title in text, title
    assert secret not in text
    assert "concern" not in text.lower()
    assert "We put our child first." in text and "Parallel parenting" in text and "Medical needs" in text
    assert "210-733-8810" in text


def test_unapproved_foundation_is_left_out(client):
    from pypdf import PdfReader
    import io

    _, h, _ = _parent(client)
    client.put(ME, headers=h, json={"foundation": {"draft": "DRAFT-ONLY-TEXT", "approved": False}})
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(client.get("/api/self-journey/pdf", headers=h).content)).pages)
    assert "DRAFT-ONLY-TEXT" not in text and "Not approved yet" in text


def test_guide_chat_rejects_unknown_safety_status(client):
    from datetime import datetime, timezone
    from ai_notice import AI_NOTICE_VERSION

    _, h, _ = _parent(client)
    client.post("/api/ai-notice/ack", headers=h, json={"ai_notice_version": AI_NOTICE_VERSION,
                                                        "ai_notice_ack_at": datetime.now(timezone.utc).isoformat()})
    r = client.post("/api/journey-guide/self-journey/chat", headers=h, json={"message": "hi", "safety_status": "safe"})
    assert r.status_code == 422


def _pdf_text(content):
    from pypdf import PdfReader
    import io

    return "".join(p.extract_text() for p in PdfReader(io.BytesIO(content)).pages)


def test_check_ins_saved_loaded_and_kept_out_of_pdf(client):
    _, h, uid = _parent(client)
    ci = {"date": "2026-10-23T10:00:00+00:00", "hardest": "CHECKIN-SECRET", "wentWell": "", "helpNext": "x", "planFits": "no"}
    assert client.put(ME, headers=h, json={"checkIns": [ci]}).status_code == 200
    got = client.get(ME, headers=h).json()["progress"]["checkIns"]
    assert got[0]["hardest"] == "CHECKIN-SECRET" and got[0]["planFits"] == "no"
    assert client.put(ME, headers=h, json={"checkIns": [{**ci, "planFits": "maybe"}]}).status_code == 422
    assert "CHECKIN-SECRET" not in _pdf_text(client.get("/api/self-journey/pdf", headers=h).content)


def test_old_journey_without_check_ins_or_awards_still_loads(client):
    _, h, uid = _parent(client)
    _db.self_journey_progress.update_one({"user_id": uid}, {"$set": {"user_id": uid, "progress": {"maxStepReached": 2}}}, upsert=True)
    p = client.get(ME, headers=h).json()["progress"]
    assert p["maxStepReached"] == 2 and p["checkIns"] == [] and p["awards"]["journey"] is None


def test_awards_need_the_real_milestone_and_unlock_the_certificate(client):
    _, h, uid = _parent(client)
    now = "2026-10-23T10:00:00+00:00"
    claim = {"selfAssessment": now, "coparenting": now, "foundation": now, "journey": now}
    a = client.put(ME, headers=h, json={"awards": claim}).json()["progress"]["awards"]
    assert a == {"selfAssessment": None, "coparenting": None, "foundation": None, "journey": None}
    assert client.get("/api/self-journey/certificate", headers=h).status_code == 409
    body = {"maxStepReached": 7, "foundation": {"draft": "d", "approved": True}, "awards": {"foundation": now, "journey": now}}
    a = client.put(ME, headers=h, json=body).json()["progress"]["awards"]
    assert a["foundation"] == now and a["journey"] == now and a["selfAssessment"] is None
    # once earned an award stays, even if a later save leaves it out
    assert client.put(ME, headers=h, json={"maxStepReached": 7}).json()["progress"]["awards"]["journey"] == now
    r = client.get("/api/self-journey/certificate", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    text = _pdf_text(r.content)
    assert "Certificate of Completion" in text and "SJ" in text and "Foundation Award" in text
    assert client.get("/api/self-journey/certificate").status_code == 401


def test_stage_saved_and_old_journeys_load_with_null_stage(client):
    _, h, uid = _parent(client)
    _db.self_journey_progress.update_one({"user_id": uid}, {"$set": {"user_id": uid, "progress": {"maxStepReached": 1}}}, upsert=True)
    assert client.get(ME, headers=h).json()["progress"]["stage"] is None
    assert client.put(ME, headers=h, json={"stage": "communication"}).status_code == 200
    assert client.get(ME, headers=h).json()["progress"]["stage"] == "communication"
    assert client.put(ME, headers=h, json={"stage": "other"}).status_code == 422


def test_pdf_prints_the_path_but_never_the_safety_path(client):
    _, h, _ = _parent(client)
    client.put(ME, headers=h, json={"stage": "communication"})
    text = _pdf_text(client.get("/api/self-journey/pdf", headers=h).content)
    assert "Your path: Communication is difficult" in text and "BIFF tool" in text
    # "Communication is difficult" + a safety-concern pick: the safety path wins and nothing about it prints
    client.put(ME, headers=h, json={"stage": "communication", "safety": {"status": "concern"}})
    text = _pdf_text(client.get("/api/self-journey/pdf", headers=h).content)
    assert "Your path" not in text and "BIFF tool" not in text and "Safety first" not in text
    assert "concern" not in text.lower()


def test_guide_chat_accepts_path_and_rejects_unknown_level(client):
    from datetime import datetime, timezone
    from ai_notice import AI_NOTICE_VERSION

    _, h, _ = _parent(client)
    client.post("/api/ai-notice/ack", headers=h, json={"ai_notice_version": AI_NOTICE_VERSION,
                                                        "ai_notice_ack_at": datetime.now(timezone.utc).isoformat()})
    bad = client.post("/api/journey-guide/self-journey/chat", headers=h, json={"message": "hi", "level": "calm"})
    assert bad.status_code == 422
