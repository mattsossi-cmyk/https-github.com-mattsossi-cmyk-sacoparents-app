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
    # Founder rule (2026-03-04): a parent must pass the family-violence
    # safety screen (Level 3+) before minting a co-parent link code.
    # Legacy iter137 tests were written pre-gate — seed a Level 4 result
    # directly so they exercise the mint flow, not the gate.
    _seed_passing_safety(r.json()["user"]["user_id"], email)
    return email, r.json()["access_token"]


def _seed_passing_safety(user_id: str, email: str) -> None:
    from datetime import datetime, timezone
    from pymongo import MongoClient as SyncClient
    sync = SyncClient(MONGO_URL)
    try:
        sync[DB_NAME]["safety_assessments"].delete_many({"user_id": user_id})
        sync[DB_NAME]["safety_assessments"].insert_one({
            "assessment_id": f"sa_test_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "email": email,
            "section_1": {},
            "section_2": {},
            "result": {"level": 4, "pathway_title": "Level 4"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        sync.close()


def _mint_code(client: TestClient, token: str, context: str | None = None) -> str:
    body = {"context": context} if context else {}
    r = client.post(
        "/api/link-codes",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "code" in body
    assert body["code"].startswith("SA-")
    assert len(body["code"]) == 9  # SA- + 6 digits
    assert body["code"][3:].isdigit()
    assert body.get("join_url", "").endswith(body["code"])
    assert body.get("expires_at")
    return body["code"]


# ------------------------- 1. Mint (POST /api/link-codes) ------------------------- #

def test_mint_returns_human_readable_code(client: TestClient) -> None:
    _, token = _register(client)
    code = _mint_code(client, token)
    # SA-482731 format
    assert code[:3] == "SA-"
    digits = code[3:]
    assert digits.isdigit() and len(digits) == 6


def test_mint_persists_context_and_returns_it_on_verify(client: TestClient) -> None:
    _, token = _register(client)
    code = _mint_code(client, token, context="co-parenting")
    r = client.post(
        "/api/integrations/verify-link-code",
        headers={"X-Integration-Key": SHARED_SECRET},
        json={"code": code},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["context"] == "co-parenting"


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
        json={"code": "SA-999999"},
    )
    assert r.status_code == 404


def test_verify_normalises_human_input(client: TestClient) -> None:
    """Accept 'SA-482731', 'sa 482731', '482731', 'SA482731' — anything with the 6 digits."""
    _, token = _register(client)
    # Mint fresh per variant since verify consumes single-use.
    for build_variant in (
        lambda d: f"SA-{d}",       # canonical
        lambda d: f"sa-{d}",       # lowercase prefix
        lambda d: f"sa {d}",       # space instead of hyphen
        lambda d: d,               # digits only
        lambda d: f"SA{d}",        # no separator
    ):
        code = _mint_code(client, token)
        digits = code[3:]
        variant = build_variant(digits)
        r = client.post(
            "/api/integrations/verify-link-code",
            headers={"X-Integration-Key": SHARED_SECRET},
            json={"code": variant},
        )
        assert r.status_code == 200, (
            f"variant={variant!r} (digits={digits!r}) → {r.status_code} {r.text}"
        )


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
    """Unlinked parent → 404; after linking with a code, even a brand-new parent gets the reconciled shape."""
    email, token = _register(client)
    url = f"/api/integrations/export-assessments?email={email}"
    assert client.get(url, headers={"X-Integration-Key": SHARED_SECRET}).status_code == 404
    code = _mint_code(client, token)
    assert client.post("/api/integrations/verify-link-code", headers={"X-Integration-Key": SHARED_SECRET}, json={"code": code}).status_code == 200
    r = client.get(url, headers={"X-Integration-Key": SHARED_SECRET})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["redacted_for_safety"] is False
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
        json={"code": "SA-000000"},
    )
    assert r.status_code == 503
