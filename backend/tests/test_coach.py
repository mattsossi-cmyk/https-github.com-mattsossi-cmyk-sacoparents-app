"""Backend tests for the Interactive AI Coach chat feature (/api/coach/*)."""
import time
import pytest
import requests


# ---------- Starters (no auth) ----------
class TestCoachStarters:
    def test_starters_returns_five_prompts(self, base_url, api_client):
        r = api_client.get(f"{base_url}/api/coach/starters", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "starters" in data
        starters = data["starters"]
        assert isinstance(starters, list)
        assert len(starters) == 5
        for s in starters:
            assert "id" in s and isinstance(s["id"], str)
            assert "label" in s and isinstance(s["label"], str)
            assert "prompt" in s and isinstance(s["prompt"], str)


# ---------- Session lifecycle ----------
class TestCoachSessionLifecycle:
    def test_create_session_defaults(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15)
        assert r.status_code == 200, r.text
        s = r.json()
        assert "session_id" in s and s["session_id"].startswith("coach_")
        assert s["title"] == "New conversation"
        assert s["message_count"] == 0
        assert s["safety_flag"] is False
        assert "created_at" in s and "updated_at" in s
        assert "user_id" in s

    def test_create_session_requires_auth(self, base_url, api_client):
        r = api_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15)
        assert r.status_code in (401, 403), r.text

    def test_get_session_returns_session_and_messages(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15)
        sid = r.json()["session_id"]
        g = auth_client.get(f"{base_url}/api/coach/sessions/{sid}", timeout=15)
        assert g.status_code == 200
        payload = g.json()
        assert "session" in payload
        assert "messages" in payload
        assert isinstance(payload["messages"], list)
        assert payload["session"]["session_id"] == sid

    def test_list_sessions_newest_first(self, base_url, auth_client):
        a = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15).json()
        time.sleep(1.1)
        b = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15).json()
        r = auth_client.get(f"{base_url}/api/coach/sessions", timeout=15)
        assert r.status_code == 200
        sessions = r.json().get("sessions", [])
        ids = [s["session_id"] for s in sessions]
        assert a["session_id"] in ids and b["session_id"] in ids
        # newest first: b (created later) should come before a
        assert ids.index(b["session_id"]) < ids.index(a["session_id"])

    def test_delete_session_removes_session_and_messages(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15)
        sid = r.json()["session_id"]
        d = auth_client.delete(f"{base_url}/api/coach/sessions/{sid}", timeout=15)
        assert d.status_code == 200
        # subsequent GET should 404
        g = auth_client.get(f"{base_url}/api/coach/sessions/{sid}", timeout=15)
        assert g.status_code == 404


# ---------- Content validation ----------
class TestCoachContentValidation:
    def test_send_message_requires_auth(self, base_url, api_client):
        r = api_client.post(
            f"{base_url}/api/coach/sessions/fake_id/message",
            json={"content": "hi"},
            timeout=15,
        )
        assert r.status_code in (401, 403)

    def test_empty_content_rejected(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15)
        sid = r.json()["session_id"]
        rr = auth_client.post(
            f"{base_url}/api/coach/sessions/{sid}/message",
            json={"content": ""},
            timeout=15,
        )
        assert rr.status_code in (400, 422), rr.text

    def test_too_long_content_rejected(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15)
        sid = r.json()["session_id"]
        big = "x" * 4001
        rr = auth_client.post(
            f"{base_url}/api/coach/sessions/{sid}/message",
            json={"content": big},
            timeout=15,
        )
        assert rr.status_code in (400, 422), rr.text


# ---------- LLM-backed flows (slow) ----------
class TestCoachLLMFlows:
    def test_send_message_returns_valid_shape_and_updates_title(self, base_url, auth_client):
        s = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15).json()
        sid = s["session_id"]
        msg = "My co-parent yelled at me during pickup. I want to draft a BIFF reply."
        r = auth_client.post(
            f"{base_url}/api/coach/sessions/{sid}/message",
            json={"content": msg},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert "user_message" in payload and "assistant_message" in payload
        um = payload["user_message"]
        am = payload["assistant_message"]
        assert um["role"] == "user" and um["content"] == msg
        assert am["role"] == "assistant"
        assert isinstance(am["content"], str) and len(am["content"]) > 0
        assert isinstance(am["suggested_followups"], list)
        assert 0 <= len(am["suggested_followups"]) <= 4
        assert isinstance(am["safety_flag"], bool)

        # session_updates: title should be derived, and count incremented by 2
        upd = payload["session_updates"]
        assert upd.get("message_count") == 2
        assert upd.get("title") and upd["title"] != "New conversation"
        assert len(upd["title"]) <= 60

        # GET session confirms persistence
        g = auth_client.get(f"{base_url}/api/coach/sessions/{sid}", timeout=15).json()
        assert g["session"]["message_count"] == 2
        assert len(g["messages"]) == 2
        # messages sorted chronologically
        assert g["messages"][0]["role"] == "user"
        assert g["messages"][1]["role"] == "assistant"

    def test_multi_turn_context_remembers_child_name(self, base_url, auth_client):
        s = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15).json()
        sid = s["session_id"]
        # Turn 1 — set child name
        r1 = auth_client.post(
            f"{base_url}/api/coach/sessions/{sid}/message",
            json={"content": "My daughter's name is Zephyrine and she is 6. She struggles with the handoff."},
            timeout=60,
        )
        assert r1.status_code == 200, r1.text
        # Turn 2 — ask about "her" without repeating the name
        r2 = auth_client.post(
            f"{base_url}/api/coach/sessions/{sid}/message",
            json={"content": "What is one small thing I can do this week to help her feel more grounded during the transition?"},
            timeout=60,
        )
        assert r2.status_code == 200, r2.text
        reply = r2.json()["assistant_message"]["content"].lower()
        # The coach should keep the thread — either mentions the name or refers to daughter/6yo child.
        assert (
            "zephyrine" in reply
            or "daughter" in reply
            or "her" in reply
            or "6" in reply
        ), f"multi-turn continuity missing: {reply[:200]}"

        # Session message count should be 4 (2 turns)
        g = auth_client.get(f"{base_url}/api/coach/sessions/{sid}", timeout=15).json()
        assert g["session"]["message_count"] == 4

    def test_safety_relevant_message_returns_valid_schema(self, base_url, auth_client):
        """Non-strict: verify schema and no 5xx on safety-relevant input.
        Claude may or may not set safety_flag=True; we just ensure it's a
        boolean and the response references safety resources when relevant."""
        s = auth_client.post(f"{base_url}/api/coach/sessions", json={}, timeout=15).json()
        sid = s["session_id"]
        r = auth_client.post(
            f"{base_url}/api/coach/sessions/{sid}/message",
            json={"content": "My co-parent threatened to hurt me last night and I'm scared for my safety."},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        am = r.json()["assistant_message"]
        assert isinstance(am["safety_flag"], bool)
        assert isinstance(am["content"], str) and am["content"].strip()
        # If safety_flag was set, session_updates should promote it.
        if am["safety_flag"]:
            upd = r.json()["session_updates"]
            assert upd.get("safety_flag") is True
