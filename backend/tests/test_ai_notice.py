"""AI privacy notice: one server-side acknowledgment (current version) is required before any AI call."""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ai_notice import AI_NOTICE_LABELS, AI_NOTICE_VERSION  # noqa: E402

API = "http://localhost:8001/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}
PASSWORD = "Str0ng!Pass99"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails = []

# Every user-triggered AI endpoint: (method, path, json body). Each must answer 428 before the notice is accepted.
AI_ENDPOINTS = [
    ("post", "/portal/biff-refine", {"raw": "You are late again."}),
    ("post", "/portal/guided-journey/step", {"topic": "foundation", "step_index": -1}),
    ("post", "/coach/demo/reply", {"user_message": "Hi", "history": []}),
    ("post", "/coach/sessions/nope/message", {"content": "Hi"}),
    ("post", "/self-assessment/ai/tip", {"section": "overall", "answers": {}}),
    ("post", "/self-assessment/ai/framing", {"text": "Help me say this calmly"}),
    ("post", "/journey-guide/self-assessment/chat", {"message": "Hi"}),
    ("post", "/journey-guide/coparenting/chat", {"message": "Hi"}),
    ("post", "/journey-guide/child-needs/chat", {"message": "Hi"}),
    ("post", "/journey-guide/child-needs/suggest", {"category": "x", "field_id": "y"}),
    ("post", "/court-path/ai/chat", {"message": "Hi"}),
    ("post", "/court-path/ai/foundation-split", {"text": "x" * 30}),
    ("post", "/court-path/compare/talking-points", None),
    ("post", "/parallel-parenting/ai/chat", {"message": "Hi"}),
    ("post", "/parallel-parenting/ai/tip", {"step": "x"}),
    ("post", "/mediation/analyze-communication", {"text": "Hi"}),
    ("post", "/mediation/reframe", {"text": "Hi"}),
    ("post", "/mediation/section-coaching", {"section": "readiness", "data": {"a": 1}}),
    ("post", "/mediation/summary", None),
    ("post", "/mediation/agreement", None),
    ("post", "/mediation/improvement-plan", None),
    ("post", "/edu-deep/report/regen-summary", {}),
    ("post", "/med-deep/report/regen-summary", {}),
    ("post", "/psych-deep/report/regen-summary", {}),
    ("post", "/edu-deep/section/s1/coach", {}),
    ("post", "/med-deep/section/s1/coach", {}),
    ("post", "/psych-deep/section/s1/coach", {}),
    ("post", "/learning/hub/x/article/y/coach", {}),
]


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    ids = [u["user_id"] for u in db.users.find({"email": {"$in": _emails}}, {"user_id": 1})]
    db.users.delete_many({"email": {"$in": _emails}})
    for coll in ("privacy_consents", "legal_acknowledgments", "ai_send_anyway_log", "journal_entries", "journal_recaps"):
        db[coll].delete_many({"user_id": {"$in": ids}})


def _new_user():
    email = f"test_ainotice_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": PASSWORD, "name": "AI Notice Test", **CONSENT}, timeout=20)
    assert r.status_code == 200, r.text
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}


def _login(email):
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _call(method, path, body, headers):
    return httpx.request(method, f"{API}{path}", json=body, headers=headers, timeout=30)


@pytest.fixture(scope="module")
def fresh():
    return _new_user()


@pytest.mark.parametrize("method,path,body", AI_ENDPOINTS, ids=[p for _, p, _ in AI_ENDPOINTS])
def test_ai_endpoint_refused_without_ack(fresh, method, path, body):
    r = _call(method, path, body, fresh[1])
    assert r.status_code == 428, (path, r.status_code, r.text[:200])
    assert "AI privacy notice" in r.json()["detail"]


def test_voice_transcribe_refused_without_ack(fresh):
    r = httpx.post(f"{API}/portal/voice-transcribe", files={"audio": ("v.webm", b"\x00" * 5000, "audio/webm")}, headers=fresh[1], timeout=20)
    assert r.status_code == 428


def test_signed_out_ai_calls_refused():
    for path, body in (("/portal/biff-refine", {"raw": "Hi"}), ("/coach/demo/reply", {"user_message": "Hi"}), ("/portal/guided-journey/step", {"topic": "foundation", "step_index": -1})):
        assert httpx.post(f"{API}{path}", json=body, timeout=20).status_code == 401, path


def test_send_anyway_refused_without_ack(fresh):
    r = _call("post", "/ai-notice/send-anyway", {"feature": "biff", "labels": ["Phone number"]}, fresh[1])
    assert r.status_code == 428


def test_journal_recap_not_generated_without_ack(fresh):
    for text in ("Pickup went fine today.", "We agreed on the weekend plan."):
        assert _call("post", "/journal/entries", {"content": text}, fresh[1]).status_code == 201
    r = _call("get", "/journal/weekly-recap", None, fresh[1])
    assert r.status_code == 200 and r.json()["ai_notice_required"] is True and r.json()["recap_text"] is None
    uid = db.users.find_one({"email": fresh[0]})["user_id"]
    assert db.journal_recaps.count_documents({"user_id": uid}) == 0


def test_ack_is_server_side_and_shared_across_devices():
    email, h = _new_user()
    me = _call("get", "/auth/me", None, h).json()
    assert me["ai_notice_current"] is False
    before = datetime.now(timezone.utc)
    r = _call("post", "/ai-notice/ack", {"ai_notice_version": "fake", "ai_notice_ack_at": "2000-01-01"}, h)
    assert r.status_code == 200 and r.json()["version"] == AI_NOTICE_VERSION
    doc = db.users.find_one({"email": email})
    assert doc["ai_notice_version"] == AI_NOTICE_VERSION
    at = datetime.fromisoformat(doc["ai_notice_ack_at"])
    assert at.tzinfo is not None and before - timedelta(seconds=5) <= at <= datetime.now(timezone.utc) + timedelta(seconds=5)
    # A second sign-in (another device/browser) sees the same acknowledgment.
    other = _login(email)
    assert _call("get", "/auth/me", None, other).json()["ai_notice_current"] is True
    r = _call("post", "/portal/biff-refine", {"raw": "You are late again and never tell me."}, other)
    assert r.status_code == 200, r.text


def test_version_change_asks_again():
    email, h = _new_user()
    assert _call("post", "/ai-notice/ack", None, h).status_code == 200
    db.users.update_one({"email": email}, {"$set": {"ai_notice_version": "2000-01-01"}})
    assert _call("get", "/auth/me", None, h).json()["ai_notice_current"] is False
    assert _call("post", "/portal/biff-refine", {"raw": "Hi"}, h).status_code == 428
    assert _call("post", "/ai-notice/ack", None, h).status_code == 200
    assert _call("get", "/auth/me", None, h).json()["ai_notice_current"] is True


def test_ack_refused_until_privacy_consent_is_current():
    email, h = _new_user()
    db.users.update_one({"email": email}, {"$set": {"privacy_notice_version": "2000-01-01-v0"}})
    assert _call("get", "/auth/me", None, h).json()["consent_current"] is False
    r = _call("post", "/ai-notice/ack", None, h)
    assert r.status_code == 409, r.text
    assert "ai_notice_version" not in db.users.find_one({"email": email})
    assert _call("post", "/privacy-consent", CONSENT, h).status_code == 200
    assert _call("post", "/ai-notice/ack", None, h).status_code == 200



def test_send_anyway_records_labels_only():
    email, h = _new_user()
    assert _call("post", "/ai-notice/ack", None, h).status_code == 200
    secret = "Call me at 210-555-1234 about Jamie's ADHD"
    body = {"feature": "biff", "labels": ["Phone number", "Medical or psychological details"], "text": secret, "raw": secret}
    r = _call("post", "/ai-notice/send-anyway", body, h)
    assert r.status_code == 200
    uid = db.users.find_one({"email": email})["user_id"]
    rows = list(db.ai_send_anyway_log.find({"user_id": uid}))
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == {"_id", "user_id", "at", "notice_version", "feature", "labels"}
    assert row["notice_version"] == AI_NOTICE_VERSION and row["feature"] == "biff"
    assert row["labels"] == ["Phone number", "Medical or psychological details"]
    assert datetime.fromisoformat(row["at"]).tzinfo is not None
    assert "555" not in str(row) and "Jamie" not in str(row)


@pytest.mark.parametrize("body", [
    {"feature": "biff", "labels": ["210-555-1234"]},
    {"feature": "biff", "labels": []},
    {"feature": "not_a_feature", "labels": ["Phone number"]},
    {"feature": "biff", "labels": list(AI_NOTICE_LABELS) + ["extra"]},
])
def test_send_anyway_rejects_anything_but_known_labels(body):
    email, h = _new_user()
    assert _call("post", "/ai-notice/ack", None, h).status_code == 200
    assert _call("post", "/ai-notice/send-anyway", body, h).status_code == 422
    uid = db.users.find_one({"email": email})["user_id"]
    assert db.ai_send_anyway_log.count_documents({"user_id": uid}) == 0
