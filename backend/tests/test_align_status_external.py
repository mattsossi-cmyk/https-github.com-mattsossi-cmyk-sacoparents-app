# Align Status Check (iteration 143): align-status endpoint + refusal recording, via public URL
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
SECRET = os.environ.get("ALIGN_WEBHOOK_SECRET")

if not SECRET:
    pytest.skip("ALIGN_WEBHOOK_SECRET is not set: the webhook is off", allow_module_level=True)
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
STATUS = f"{BASE}/admin/safety-audit-log/align-status"
COUNTS = f"{BASE}/admin/safety-audit-log/daily-counts"
_cases = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    db.case_safety.delete_many({"case_id": {"$in": _cases}})
    db.safety_audit_log.delete_many({"case_id": {"$in": _cases}})


def _login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin():
    return _login("mattsossi@bsossi.com", "AdminPass123!")


def _body(case_id, version, ts=None, **extra):
    return json.dumps({"case_id": case_id, "safety_mode": "standard", "set_by": "professional",
                       "professional_name": "Dr X", "referral": "none", "screening_offered": True,
                       "version": version, "timestamp": int(time.time()) if ts is None else ts, **extra}).encode()


def _send(raw, sig="auto"):
    h = {"Content-Type": "application/json"}
    if sig == "auto":
        sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if sig is not None:
        h["X-Align-Signature"] = sig
    return requests.post(f"{BASE}/internal/safety-status", data=raw, headers=h, timeout=20)


def _status(admin):
    r = requests.get(STATUS, headers=admin, timeout=20)
    assert r.status_code == 200, r.text
    return r


def _today_rejected(admin):
    return requests.get(COUNTS, headers=admin, timeout=20).json()["days"][0]["rejected"]


# auth gating
def test_unauthenticated_401():
    assert requests.get(STATUS, timeout=20).status_code == 401


def test_parent_403():
    h = _login("parent1@test.com", "TestPass123!")
    assert requests.get(STATUS, headers=h, timeout=20).status_code == 403


def test_admin_shape_and_no_store(admin):
    r = _status(admin)
    assert "no-store" in r.headers.get("cache-control", "")
    b = r.json()
    assert set(b) == {"last_update", "last_applied_at", "last_rejected", "rejected_30d", "silence", "last_test"}
    assert set(b["rejected_30d"]) == {"bad_signature", "old_timestamp", "invalid_body", "replay"}
    if b["last_update"]:
        assert set(b["last_update"]) == {"at", "result"} and b["last_update"]["result"] in ("applied", "ignored")
    if b["last_rejected"]:
        assert set(b["last_rejected"]) == {"at", "reason"}


# each refusal reason increments its own counter and today's rejected column
@pytest.mark.parametrize("reason", ["bad_signature_wrong", "bad_signature_missing", "old_timestamp", "invalid_body", "replay"])
def test_refusal_recorded(admin, reason):
    before = _status(admin).json()["rejected_30d"]
    before_day = _today_rejected(admin)
    cid = f"SA-X{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    key = reason
    if reason == "bad_signature_wrong":
        assert _send(_body(cid, 1), sig="deadbeef").status_code == 401
        key = "bad_signature"
    elif reason == "bad_signature_missing":
        assert _send(_body(cid, 1), sig=None).status_code == 401
        key = "bad_signature"
    elif reason == "old_timestamp":
        assert _send(_body(cid, 1, ts=int(time.time()) - 600)).status_code == 401
    elif reason == "invalid_body":
        assert _send(b'{"case_id": "x", "not": "valid"').status_code == 422
    elif reason == "replay":
        raw = _body(cid, 1)
        assert _send(raw).status_code == 200
        assert _send(raw).status_code == 409
    after = _status(admin)
    b = after.json()
    assert b["rejected_30d"][key] == before[key] + 1
    for k in before:
        if k != key:
            assert b["rejected_30d"][k] >= before[k]
    assert b["last_rejected"]["reason"] == key
    assert cid not in after.text
    assert _today_rejected(admin) == before_day + 1
    doc = db.safety_webhook_rejects.find_one({}, sort=[("at", -1)])
    assert set(doc) == {"_id", "at", "reason", "created"} and doc["reason"] == key


# applied → stale ignored
def test_applied_then_ignored(admin):
    cid = f"SA-X{uuid.uuid4().hex[:6].upper()}"
    _cases.append(cid)
    assert _send(_body(cid, 5)).status_code == 200
    b = _status(admin).json()
    assert b["last_update"]["result"] == "applied"
    assert b["last_applied_at"] == b["last_update"]["at"]
    applied_at = b["last_applied_at"]
    time.sleep(1.1)
    assert _send(_body(cid, 5, note_review=True)).status_code == 200
    b2 = _status(admin).json()
    assert b2["last_update"]["result"] == "ignored"
    assert b2["last_applied_at"] == applied_at
    assert b2["last_update"]["at"] > applied_at
    # all reject docs only have the 4 allowed keys
    bad = db.safety_webhook_rejects.find_one({"$where": "Object.keys(this).length != 4"})
    assert bad is None
