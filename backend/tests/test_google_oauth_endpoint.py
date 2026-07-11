"""Tests for POST /api/auth/google/session endpoint contract.

Verifies the endpoint is wired and gracefully rejects invalid input
(no 500 crashes) as required by the review request.
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fall back to reading the frontend .env (protected variable, must exist)
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except OSError:
        pass

assert BASE_URL, "REACT_APP_BACKEND_URL is required for these tests."

ENDPOINT = f"{BASE_URL}/api/auth/google/session"


@pytest.fixture
def api_client():
    s = requests.Session()
    return s


# ----- 1. Endpoint is wired and rejects missing session_id -----
def test_google_session_missing_header_returns_400(api_client):
    """No X-Session-ID header at all -> 400 Missing X-Session-ID."""
    r = api_client.post(ENDPOINT, timeout=30)
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
    body = r.json()
    detail = body.get("detail") or body.get("message") or ""
    assert "session" in detail.lower(), f"unexpected detail: {detail}"


def test_google_session_empty_header_returns_400(api_client):
    """Empty X-Session-ID header -> treated as missing -> 400."""
    r = api_client.post(
        ENDPOINT,
        headers={"X-Session-ID": ""},
        timeout=30,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"


# ----- 2. Made-up session_id: upstream Emergent call fails gracefully with 4xx (401), not 500 -----
def test_google_session_bogus_session_id_returns_4xx_not_500(api_client):
    """A random session_id can't be exchanged upstream; endpoint must
    return a 4xx (401 per code path) — not crash with a 500."""
    bogus = f"bogus_{uuid.uuid4().hex}"
    r = api_client.post(
        ENDPOINT,
        headers={"X-Session-ID": bogus},
        timeout=30,
    )
    # Must NOT be a server crash.
    assert r.status_code < 500, f"5xx from bogus session id (should be 4xx): {r.status_code} {r.text[:400]}"
    # Contract says: 401 Invalid session on upstream non-200.
    assert r.status_code in (400, 401, 403), f"unexpected status: {r.status_code} {r.text[:400]}"
    body = r.json()
    detail = (body.get("detail") or body.get("message") or "").lower()
    assert "invalid" in detail or "session" in detail, f"unexpected detail: {detail}"


def test_google_session_bogus_session_id_no_cookie_set(api_client):
    """A failed exchange must NOT set a session_token cookie."""
    bogus = f"bogus_{uuid.uuid4().hex}"
    r = api_client.post(
        ENDPOINT,
        headers={"X-Session-ID": bogus},
        timeout=30,
    )
    # None of the auth cookies should be set on failure
    assert "session_token" not in r.cookies
    assert "auth_token" not in r.cookies


# ----- 3. /api/auth/me is reachable and returns 401 for unauth (endpoints wired) -----
def test_auth_me_returns_401_when_not_signed_in(api_client):
    r = api_client.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 401
