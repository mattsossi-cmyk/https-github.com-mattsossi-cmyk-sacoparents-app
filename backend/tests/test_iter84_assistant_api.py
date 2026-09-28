"""Iter 84 — Align Assistant HTTP API integration tests (case-brief, triggers, chat SSE, history)."""
import json
import os
import time
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "mattsossi@bsossi.com"
KNOWN_CASE_ID = "62cf2f6d-2df3-4c55-9d8f-746423455b98"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    for pw in ("AlignTemp2026!", "CoParents2026!"):
        r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": pw}, timeout=15)
        if r.status_code == 200:
            return s
    pytest.skip(f"admin login failed: {r.status_code} {r.text[:200]}")


# --- triggers ---
def test_triggers_requires_auth():
    r = requests.get(f"{BASE}/api/assistant/triggers", timeout=10)
    assert r.status_code == 401, r.text[:200]


def test_triggers_admin_has_4_keys(admin_session):
    r = admin_session.get(f"{BASE}/api/assistant/triggers", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"invite", "review", "pathway", "report"}
    for v in data.values():
        assert isinstance(v, str) and len(v) > 10


# --- case-brief ---
def test_case_brief_admin_case(admin_session):
    r = admin_session.get(f"{BASE}/api/assistant/case-brief/{KNOWN_CASE_ID}", timeout=15)
    assert r.status_code == 200, r.text[:200]
    b = r.json()
    assert b["case_id"] == KNOWN_CASE_ID
    assert "case_code" in b and "case_status" in b
    assert set(b["participants"].keys()) == {"a", "b"}
    assert set(b["buckets"].keys()) == {"Agreed", "Minor Gap", "High Discrepancy"}
    assert isinstance(b["steps"], list) and len(b["steps"]) == 5
    for s in b["steps"]:
        assert set(s.keys()) >= {"key", "label", "state", "detail"}
        assert s["state"] in ("done", "active", "todo")


def test_case_brief_404_random_id(admin_session):
    r = admin_session.get(f"{BASE}/api/assistant/case-brief/{uuid.uuid4()}", timeout=10)
    assert r.status_code == 404


# --- chat SSE + history ---
def _stream_chat(session, payload):
    r = session.post(f"{BASE}/api/assistant/chat", json=payload, stream=True, timeout=60)
    assert r.status_code == 200, r.text[:200]
    assert "text/event-stream" in r.headers.get("content-type", "")
    deltas, done = [], False
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data: "):
            continue
        obj = json.loads(raw[6:])
        if "delta" in obj:
            deltas.append(obj["delta"])
        if obj.get("done"):
            done = True
            break
    return "".join(deltas), done


def test_chat_empty_message_400(admin_session):
    r = admin_session.post(f"{BASE}/api/assistant/chat", json={"session_id": "x", "message": ""}, timeout=10)
    assert r.status_code == 400


def test_chat_streams_and_history_multiturn(admin_session):
    sid = f"pytest-{uuid.uuid4()}"
    reply1, done1 = _stream_chat(admin_session, {"session_id": sid, "message": "In one short sentence, what is the case status?", "case_id": KNOWN_CASE_ID})
    assert done1 and len(reply1) > 5, f"reply1={reply1!r}"
    time.sleep(1)
    reply2, done2 = _stream_chat(admin_session, {"session_id": sid, "message": "Thanks. Now name one next step.", "case_id": KNOWN_CASE_ID})
    assert done2 and len(reply2) > 5, f"reply2={reply2!r}"

    h = admin_session.get(f"{BASE}/api/assistant/history", params={"session_id": sid}, timeout=10)
    assert h.status_code == 200
    msgs = h.json()
    roles = [m["role"] for m in msgs]
    assert roles.count("user") >= 2 and roles.count("assistant") >= 2, roles
