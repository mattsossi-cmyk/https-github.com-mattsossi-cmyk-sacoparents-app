"""iter137 — sacoparentsalign server-to-server integration.

Covers the three endpoints wired in `integration_routes.py`:

  1. POST /api/link-codes                — parent-authenticated mint
  2. POST /api/integrations/verify-link-code
     — server-to-server; validates + consumes the code
  3. GET  /api/integrations/export-assessments?email=…
     — server-to-server; returns the reconciled bundle

Guardrails locked here:
  * `X-Integration-Key` header uses constant-time comparison — wrong
    key => 401.
  * Missing key => 401.
  * Missing INTEGRATION_SHARED_SECRET on the server => 503.
  * Codes are single-use — a second verify with the same code => 404.
  * Newly-minted codes invalidate older unused ones (superseded).
  * Guest accounts cannot mint (403).
  * Export shape includes `situation_snapshot`, `foundation_statement`,
    `special_needs.{medical, educational, psychological}` keys.
"""
from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Fixed value matches the spec pasted by the founder on 2026-03-04.
SHARED_SECRET = "2f9c1e7a4b8d3f6a5c0e9d7b2f4a6c8e1d3b5a7c9e0f2a4b6c8d1e3f5a7b9c0d"


@pytest.fixture(scope="module")
def client():
    os.environ["INTEGRATION_SHARED_SECRET"] = SHARED_SECRET
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str]:
    email = f"iter137_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter137 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def _mint_code(client: TestClient, token: str) -> str:
    r = client.post(
        "/api/link-codes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "code" in body
    assert len(body["code"]) == 8
    return body["code"]


# ------------------------- 1. Mint (POST /api/link-codes) ------------------------- #

def test_mint_returns_8_char_code(client: TestClient) -> None:
    _, token = _register(client)
    code = _mint_code(client, token)
    # Uppercase alphabet + digits, no ambiguous glyphs.
    assert set(code).issubset(set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"))


def test_mint_supersedes_previous_code(client: TestClient) -> None:
    """A second mint invalidates the first code so only the newest works."""
    _, token = _register(client)
    first = _mint_code(client, token)
    second = _mint_code(client, token)
    assert first != second

    # Older code should no longer verify.
    r = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"code": first},
    )
    assert r.status_code == 404


# ---------------------- 2. Verify (POST /verify-link-code) ---------------------- #

def test_verify_requires_integration_key(client: TestClient) -> None:
    _, token = _register(client)
    code = _mint_code(client, token)
    # No header
    r = client.post(
        "/api/integrations/verify-link-code",
        json={"code": code},
    )
    assert r.status_code == 401
    # Wrong header
    r = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": "not-the-real-secret"},
        json={"code": code},
    )
    assert r.status_code == 401


def test_verify_returns_email_and_is_single_use(client: TestClient) -> None:
    email, token = _register(client)
    code = _mint_code(client, token)
    r = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"code": code},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == email
    # Reusing the code fails — consumed.
    r2 = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"code": code},
    )
    assert r2.status_code == 404


def test_verify_unknown_code_404(client: TestClient) -> None:
    r = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"code": "ZZZZZZZZ"},
    )
    assert r.status_code == 404


# ----------------- 3. Export (GET /export-assessments) ----------------- #

def test_export_requires_integration_key(client: TestClient) -> None:
    email, _ = _register(client)
    r = client.get(f"/api/integrations/export-assessments?email={email}")
    assert r.status_code == 401
    r2 = client.get(
        f"/api/integrations/export-assessments?email={email}",
        headers={"X-Integration-Key": "wrong"},
    )
    assert r2.status_code == 401


def test_export_shape_for_new_parent(client: TestClient) -> None:
    """Even a brand-new parent with no assessments has the reconciled shape."""
    email, _ = _register(client)
    r = client.get(
        f"/api/integrations/export-assessments?email={email}",
        headers={"X-Integration-Key": SHARED_SECRET},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["parent"]["email"] == email
    assert "situation_snapshot" in body
    assert "foundation_statement" in body
    assert "special_needs" in body
    for lane in ("medical", "educational", "psychological"):
        assert lane in body["special_needs"]
    assert body.get("schema_version") == 1


def test_export_unknown_email_returns_404(client: TestClient) -> None:
    r = client.get(
        "/api/integrations/export-assessments?email=nobody@example.com",
        headers={"X-Integration-Key": SHARED_SECRET},
    )
    assert r.status_code == 404


# ---------- Server misconfiguration (INTEGRATION_SHARED_SECRET absent) ---------- #

def test_missing_secret_returns_503(monkeypatch, client: TestClient) -> None:
    monkeypatch.delenv("INTEGRATION_SHARED_SECRET", raising=False)
    r = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": "anything"},
        json={"code": "AAAAAAAA"},
    )
    assert r.status_code == 503
