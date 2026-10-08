"""Backend tests for the new Court-Ordered Journey (iter after 101).

Covers: /court-path/summary, /court-path/ai/chat (GET/POST + /new memory + reuse-empty),
/parallel-parenting/ai/chat/new, PUT /portal/state partial court_legal_name,
POST /court-path/checklist legal_name/parent_name, 401 unauth.
"""
import os
import time
import requests

def _read_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.strip().startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].strip('"').strip("'")
    except Exception:
        pass
    return None

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env() or "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL missing"
API = f"{BASE}/api"
EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


def _login():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_unauth_returns_401():
    for path in ("/court-path/summary", "/court-path/ai/chat"):
        r = requests.get(f"{API}{path}", timeout=15)
        assert r.status_code in (401, 403), f"{path} -> {r.status_code}"


def test_summary_shape():
    tok = _login()
    r = requests.get(f"{API}/court-path/summary", headers=_h(tok), timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("alignment", "difference", "child", "has_cp", "has_sa", "has_child"):
        assert k in data
    assert isinstance(data["alignment"], list)
    assert isinstance(data["child"], list)
    # parent1 has CN medical seed per credentials file
    assert len(data["child"]) == 3  # medical/educational/psychological


def test_portal_state_partial_court_legal_name():
    tok = _login()
    # Partial PUT only this field
    val = "  Samuel   Q.  Parent  "
    r = requests.put(f"{API}/portal/state", headers=_h(tok), json={"court_legal_name": val}, timeout=15)
    assert r.status_code == 200, r.text
    r2 = requests.get(f"{API}/portal/state", headers=_h(tok), timeout=15).json()
    state2 = r2.get("state") or r2
    assert state2.get("court_legal_name") == "Samuel Q. Parent"  # collapsed

    # Max 120 chars
    long_name = "A" * 500
    requests.put(f"{API}/portal/state", headers=_h(tok), json={"court_legal_name": long_name}, timeout=15)
    r3 = requests.get(f"{API}/portal/state", headers=_h(tok), timeout=15).json()
    state3 = r3.get("state") or r3
    assert len(state3.get("court_legal_name", "")) <= 120

    # Restore to a sensible value
    requests.put(f"{API}/portal/state", headers=_h(tok), json={"court_legal_name": "Samuel Q. Parent"}, timeout=15)


def test_checklist_legal_name_in_payload():
    tok = _login()
    # Set a legal name
    requests.put(f"{API}/portal/state", headers=_h(tok), json={"court_legal_name": "Samuel Q. Parent"}, timeout=15)
    r = requests.post(f"{API}/court-path/checklist", headers=_h(tok), json={}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("legal_name") == "Samuel Q. Parent"
    assert "parent_name" in data


def test_court_chat_new_returns_empty_and_reuses():
    tok = _login()
    r = requests.post(f"{API}/court-path/ai/chat/new", headers=_h(tok), timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "session_id" in d
    assert d.get("messages") == []
    sid1 = d["session_id"]
    # Call /new again without sending any message -> should reuse empty session
    r2 = requests.post(f"{API}/court-path/ai/chat/new", headers=_h(tok), timeout=20).json()
    assert r2["session_id"] == sid1, "empty session should be reused"


def test_court_chat_remembers_turn():
    tok = _login()
    sid = requests.post(f"{API}/court-path/ai/chat/new", headers=_h(tok), timeout=20).json()["session_id"]
    # Turn 1
    r1 = requests.post(
        f"{API}/court-path/ai/chat",
        headers=_h(tok),
        json={"session_id": sid, "message": "My child is Maya, age 6."},
        timeout=90,
    )
    assert r1.status_code == 200, r1.text
    time.sleep(1)
    # Turn 2
    r2 = requests.post(
        f"{API}/court-path/ai/chat",
        headers=_h(tok),
        json={"session_id": sid, "message": "What was my child's name?"},
        timeout=90,
    )
    assert r2.status_code == 200, r2.text
    reply = (r2.json().get("reply") or r2.json().get("message") or "").lower()
    assert "maya" in reply, f"expected memory, got: {reply[:200]}"

    # GET returns history with 4 msgs
    hist = requests.get(f"{API}/court-path/ai/chat", headers=_h(tok), timeout=20).json()
    msgs = hist.get("messages") or []
    assert len(msgs) >= 4


def test_parallel_parenting_chat_new():
    tok = _login()
    r = requests.post(f"{API}/parallel-parenting/ai/chat/new", headers=_h(tok), timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "session_id" in d
    assert d.get("messages") == []
