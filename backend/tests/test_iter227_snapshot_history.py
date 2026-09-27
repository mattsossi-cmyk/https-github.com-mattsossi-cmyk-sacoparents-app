"""iter227 — Coparent Portal snapshot_history sanitizer + roundtrip.

Verifies the /api/portal/state PUT sanitizes `snapshot_history` per the
whitelist rules in portal_routes._sanitize_snapshot_history:
    - only known guided topics accepted (bogus dropped)
    - items with missing/empty answers dropped
    - list capped at _MAX_SNAPSHOT_HISTORY (=12), newest-first order preserved
    - question/answer strings truncated (400 / 2000 chars)
    - safety_flagged coerced to True only when truthy
    - unknown extra keys stripped
    - passing None clears field (but partial-update means other fields untouched)
    - authenticated read-back via GET /api/portal/state returns the cleaned list
"""
import pytest


def _put_state(auth_client, base_url, body):
    r = auth_client.put(f"{base_url}/api/portal/state", json=body, timeout=15)
    assert r.status_code == 200, f"PUT /portal/state failed: {r.status_code} {r.text}"
    return r.json()


def _get_state(auth_client, base_url):
    r = auth_client.get(f"{base_url}/api/portal/state", timeout=15)
    assert r.status_code == 200, f"GET /portal/state failed: {r.status_code} {r.text}"
    return r.json()


class TestSnapshotHistorySanitizer:
    """Behavioural correctness of _sanitize_snapshot_history."""

    def test_valid_snapshots_roundtrip(self, auth_client, base_url):
        payload = {
            "snapshot_history": [
                {
                    "id": 1001,
                    "topic": "foundation",
                    "answers": [
                        {"question": "What matters most?", "answer": "My kid's stability"},
                        {"question": "What's the risk?", "answer": "Escalation"},
                    ],
                    "saved_at": "2026-01-15T10:00:00.000Z",
                    "save_key": "foundation_text",
                    "category": None,
                    "safety_flagged": False,
                },
                {
                    "id": 1002,
                    "topic": "medical",
                    "answers": [{"question": "Q", "answer": "A"}],
                    "saved_at": "2026-01-14T09:00:00.000Z",
                    "save_key": "align_record",
                    "category": "Medical",
                    "safety_flagged": True,
                },
            ]
        }
        _put_state(auth_client, base_url, payload)
        state = _get_state(auth_client, base_url)["state"]
        hist = state.get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 2
        assert hist[0]["topic"] == "foundation"
        assert hist[0]["id"] == 1001
        assert hist[0]["save_key"] == "foundation_text"
        assert "safety_flagged" not in hist[0]  # False is dropped by sanitizer
        assert hist[1]["topic"] == "medical"
        assert hist[1]["category"] == "Medical"
        assert hist[1]["safety_flagged"] is True
        assert hist[1]["answers"][0] == {"question": "Q", "answer": "A"}

    def test_bogus_topic_dropped(self, auth_client, base_url):
        _put_state(auth_client, base_url, {
            "snapshot_history": [
                {"topic": "not-a-topic", "answers": [{"question": "Q", "answer": "A"}], "saved_at": "2026-01-01"},
                {"topic": "safety", "answers": [{"question": "Q", "answer": "A"}], "saved_at": "2026-01-01"},
            ]
        })
        hist = _get_state(auth_client, base_url)["state"].get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 1
        assert hist[0]["topic"] == "safety"

    def test_empty_answers_dropped(self, auth_client, base_url):
        _put_state(auth_client, base_url, {
            "snapshot_history": [
                {"topic": "foundation", "answers": [], "saved_at": "2026-01-01"},
                {"topic": "coparenting", "saved_at": "2026-01-01"},  # missing answers entirely
                {"topic": "psychological", "answers": "notalist", "saved_at": "2026-01-01"},
                {"topic": "educational", "answers": [{"question": "Q", "answer": "Answer"}], "saved_at": "2026-01-02"},
            ]
        })
        hist = _get_state(auth_client, base_url)["state"].get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 1
        assert hist[0]["topic"] == "educational"

    def test_cap_at_12_items(self, auth_client, base_url):
        # Push 15; sanitizer should keep first 12 (newest-first order preserved)
        items = [
            {
                "id": i,
                "topic": "foundation",
                "answers": [{"question": f"Q{i}", "answer": f"A{i}"}],
                "saved_at": f"2026-01-{(i%28)+1:02d}",
            }
            for i in range(15)
        ]
        _put_state(auth_client, base_url, {"snapshot_history": items})
        hist = _get_state(auth_client, base_url)["state"].get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 12
        assert hist[0]["id"] == 0  # first item preserved (order)
        assert hist[-1]["id"] == 11

    def test_long_strings_truncated(self, auth_client, base_url):
        long_q = "Q" * 800
        long_a = "A" * 5000
        _put_state(auth_client, base_url, {
            "snapshot_history": [{
                "topic": "safety",
                "answers": [{"question": long_q, "answer": long_a}],
                "saved_at": "2026-01-01",
            }]
        })
        hist = _get_state(auth_client, base_url)["state"].get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 1
        qa = hist[0]["answers"][0]
        assert len(qa["question"]) == 400
        assert len(qa["answer"]) == 2000

    def test_extra_keys_stripped(self, auth_client, base_url):
        _put_state(auth_client, base_url, {
            "snapshot_history": [{
                "topic": "medical",
                "answers": [{"question": "Q", "answer": "A", "sneaky": "x"}],
                "saved_at": "2026-01-01",
                "malicious": {"huge": "x" * 20000},
                "other_extra": [1, 2, 3],
            }]
        })
        hist = _get_state(auth_client, base_url)["state"].get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 1
        item = hist[0]
        assert "malicious" not in item
        assert "other_extra" not in item
        # sneaky sub-key on each QA is also dropped (whitelist to {question, answer})
        assert set(item["answers"][0].keys()) == {"question", "answer"}

    def test_non_list_returns_none_field(self, auth_client, base_url):
        # First set some history, then send a non-list, then verify it's cleared
        _put_state(auth_client, base_url, {
            "snapshot_history": [{
                "topic": "coparenting",
                "answers": [{"question": "Q", "answer": "A"}],
                "saved_at": "2026-01-01",
            }]
        })
        hist = _get_state(auth_client, base_url)["state"].get("snapshot_history")
        assert isinstance(hist, list) and len(hist) == 1
        # Non-list payload → pydantic 422 (defense-in-depth before sanitizer)
        r = auth_client.put(f"{base_url}/api/portal/state",
                            json={"snapshot_history": "notalist"}, timeout=10)
        assert r.status_code == 422
        # Prior state must be untouched
        state = _get_state(auth_client, base_url)["state"]
        assert isinstance(state.get("snapshot_history"), list)
        assert len(state["snapshot_history"]) == 1
        # Explicit null → sanitizer returns None (field intentionally cleared)
        _put_state(auth_client, base_url, {"snapshot_history": None})
        state2 = _get_state(auth_client, base_url)["state"]
        assert state2.get("snapshot_history") in (None, [])

    def test_partial_update_leaves_other_fields(self, auth_client, base_url):
        # Seed foundation_text separately, then a snapshot_history-only PUT
        _put_state(auth_client, base_url, {"foundation_text": "TEST_IT227_FOUNDATION"})
        _put_state(auth_client, base_url, {
            "snapshot_history": [{
                "topic": "foundation",
                "answers": [{"question": "Q", "answer": "A"}],
                "saved_at": "2026-01-01",
            }]
        })
        state = _get_state(auth_client, base_url)["state"]
        assert state.get("foundation_text") == "TEST_IT227_FOUNDATION"
        assert isinstance(state.get("snapshot_history"), list)
        assert len(state["snapshot_history"]) == 1


class TestSnapshotHistoryAuth:
    """/portal/state must remain auth-gated (iter227 does not change this)."""

    def test_unauthenticated_get_rejected(self, api_client, base_url):
        r = api_client.get(f"{base_url}/api/portal/state", timeout=10)
        assert r.status_code in (401, 403)

    def test_unauthenticated_put_rejected(self, api_client, base_url):
        r = api_client.put(f"{base_url}/api/portal/state",
                           json={"snapshot_history": []}, timeout=10)
        assert r.status_code in (401, 403)
