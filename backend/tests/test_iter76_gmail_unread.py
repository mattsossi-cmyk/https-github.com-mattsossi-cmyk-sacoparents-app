"""Iteration 76 — Gmail Mini Inbox unread badge.

Only backend-observable behaviour is asserted here — the badge itself
is a small span rendered by the frontend when `unread_messages > 0`.

We verify:
- `GET /api/gmail/unread-count` requires auth.
- A signed-in user with NO Gmail tokens gets a well-formed
  `{ connected: false, unread_messages: 0, unread_threads: 0 }`.
- Ints are ints (not strings), so the frontend can safely `> 0`.
"""
import os
import pytest
import httpx


BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://prepared-parents.preview.emergentagent.com",
).rstrip("/")


@pytest.fixture(scope="module")
def token():
    with httpx.Client(timeout=15) as c:
        r = c.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "parent1@test.com", "password": "TestPass123!"},
        )
        r.raise_for_status()
        data = r.json()
        tok = data.get("access_token") or data.get("token")
        assert tok, f"login returned no token: {data}"
        return tok


def test_unread_count_requires_auth():
    r = httpx.get(f"{BASE_URL}/api/gmail/unread-count", timeout=15)
    assert r.status_code in (401, 403), r.status_code


def test_unread_count_shape_when_disconnected(token):
    r = httpx.get(
        f"{BASE_URL}/api/gmail/unread-count",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"connected", "unread_messages", "unread_threads"}
    assert body["connected"] is False
    assert isinstance(body["unread_messages"], int)
    assert isinstance(body["unread_threads"], int)
    assert body["unread_messages"] == 0
    assert body["unread_threads"] == 0
