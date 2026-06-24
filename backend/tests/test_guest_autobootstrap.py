"""End-to-end backend tests for the P0 fix:
- POST /api/auth/guest creates a guest session and sets an httpOnly cookie
- Guest can PUT each mediation save endpoint (child-goals, issues, priority,
  comm-style, readiness) and GET /api/mediation/prep returns persisted data
- The same cookie continues to work across requests (the "refresh keeps session"
  regression the user reported)
- /api/auth/login still works for parent1@test.com (regression check)
"""
import os
import uuid

import pytest
import requests

# Load REACT_APP_BACKEND_URL from frontend/.env if it isn't already in the env
# (pytest doesn't auto-load the frontend dotenv).
if "REACT_APP_BACKEND_URL" not in os.environ:
    try:
        with open("/app/frontend/.env") as _f:
            for _line in _f:
                if _line.startswith("REACT_APP_BACKEND_URL="):
                    os.environ["REACT_APP_BACKEND_URL"] = _line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture
def guest_session():
    """Fresh requests.Session that holds whatever cookies the backend sets."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/guest", json={})
    assert r.status_code == 200, f"guest start failed: {r.status_code} {r.text}"
    data = r.json()
    assert "user" in data and data["user"]["is_guest"] is True
    assert data["user"]["user_id"].startswith("guest_")
    # FastAPI sets auth_token cookie (httpOnly). requests captures it.
    assert any(c.name == "auth_token" for c in s.cookies), (
        f"auth_token cookie not set; got {[c.name for c in s.cookies]}"
    )
    return s, data["user"]


class TestGuestBootstrap:
    def test_guest_endpoint_creates_session(self, guest_session):
        s, user = guest_session
        assert user["is_guest"] is True
        # /auth/me with just cookies (no bearer) must succeed
        r = s.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        me = r.json()
        assert me["user_id"] == user["user_id"]
        assert me["is_guest"] is True

    def test_guest_session_survives_new_request(self, guest_session):
        """Simulates 'refresh the page' — same cookie jar, new requests."""
        s, user = guest_session
        for _ in range(3):
            r = s.get(f"{BASE_URL}/api/auth/me")
            assert r.status_code == 200
            assert r.json()["user_id"] == user["user_id"]


class TestGuestCanSaveAllSections:
    """Each section: PUT then GET /prep and assert it was persisted."""

    def _put_and_verify(self, s, path, payload, section_key, assertions):
        put = s.put(f"{BASE_URL}/api/mediation/{path}", json=payload)
        assert put.status_code == 200, f"PUT /{path} -> {put.status_code} {put.text}"
        assert put.json() == {"ok": True}

        get_ = s.get(f"{BASE_URL}/api/mediation/prep")
        assert get_.status_code == 200
        prep = get_.json()
        assert section_key in prep, f"{section_key} missing from prep payload: {prep}"
        for k, expected in assertions.items():
            assert prep[section_key].get(k) == expected, (
                f"{section_key}.{k} != {expected}; got {prep[section_key].get(k)}"
            )
        assert prep.get("completed", {}).get(section_key) is True

    def test_save_child_goals(self, guest_session):
        s, _ = guest_session
        token = uuid.uuid4().hex[:6]
        payload = {
            "selected_goals": ["safety", "stability"],
            "consistency_text": f"TEST_{token}_calm handovers",
            "feel_text": f"TEST_{token}_safe and heard",
            "strength_text": f"TEST_{token}_consistent routines",
            "priority_order": ["safety", "stability"],
        }
        self._put_and_verify(
            s, "child-goals", payload, "child_goals",
            {
                "selected_goals": payload["selected_goals"],
                "consistency_text": payload["consistency_text"],
                "feel_text": payload["feel_text"],
                "priority_order": payload["priority_order"],
            },
        )

    def test_save_issues(self, guest_session):
        s, _ = guest_session
        payload = {
            "items": {"schedule": "TEST_handover times keep slipping",
                       "handovers": "TEST_too tense"},
            "other": "TEST_other_issue",
        }
        self._put_and_verify(
            s, "issues", payload, "issues",
            {"items": payload["items"], "other": payload["other"]},
        )

    def test_save_priority(self, guest_session):
        s, _ = guest_session
        payload = {
            "items": [
                {"id": "schedule", "label": "Schedule", "bucket": "urgent"},
                {"id": "handovers", "label": "Handovers", "bucket": "difficult"},
            ]
        }
        self._put_and_verify(
            s, "priority", payload, "priority",
            {"items": payload["items"]},
        )

    def test_save_comm_style(self, guest_session):
        s, _ = guest_session
        payload = {
            "answers": {"q1": "calm", "q2": "direct"},
            "free_text_sample": "TEST_I try to use I-statements",
        }
        self._put_and_verify(
            s, "comm-style", payload, "comm_style",
            {"answers": payload["answers"], "free_text_sample": payload["free_text_sample"]},
        )

    def test_save_readiness(self, guest_session):
        s, _ = guest_session
        payload = {"answers": {"emotional": 4, "logistical": 3}}
        self._put_and_verify(
            s, "readiness", payload, "readiness",
            {"answers": payload["answers"]},
        )

    def test_persistence_across_refresh(self, guest_session):
        """Save → simulate refresh (drop in-memory state, keep cookies only) → GET."""
        s, user = guest_session
        payload = {
            "selected_goals": ["safety"],
            "consistency_text": "TEST_persist_check",
            "feel_text": "",
            "strength_text": "",
            "priority_order": ["safety"],
        }
        assert s.put(f"{BASE_URL}/api/mediation/child-goals", json=payload).status_code == 200

        # New Session reusing only the cookies — closest analog to "browser refresh".
        cookies = {c.name: c.value for c in s.cookies}
        s2 = requests.Session()
        s2.headers.update({"Content-Type": "application/json"})
        for k, v in cookies.items():
            s2.cookies.set(k, v)

        me = s2.get(f"{BASE_URL}/api/auth/me")
        assert me.status_code == 200, f"cookie did not survive: {me.status_code} {me.text}"
        assert me.json()["user_id"] == user["user_id"]

        prep = s2.get(f"{BASE_URL}/api/mediation/prep")
        assert prep.status_code == 200
        cg = prep.json().get("child_goals") or {}
        assert cg.get("consistency_text") == "TEST_persist_check"
        assert cg.get("selected_goals") == ["safety"]


class TestLoginRegression:
    """Regression: /login must still work for the seeded test user."""

    def test_login_parent1(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "parent1@test.com", "password": "TestPass123!"},
            timeout=15,
        )
        assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["user"]["email"] == "parent1@test.com"
        assert data["user"].get("is_guest") in (False, None)
        assert isinstance(data.get("access_token"), str) and len(data["access_token"]) > 10
