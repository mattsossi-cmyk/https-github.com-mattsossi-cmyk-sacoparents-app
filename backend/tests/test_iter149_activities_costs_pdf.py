"""iter149 — Activity Cost Ledger PDF export.

Locks the `/api/activities-costs/compare.pdf` endpoint. Covers:
  * Auth required (401 for anonymous).
  * Solo mode (no coparent_email) returns a PDF with the caller's ledger.
  * Paired mode (valid coparent_email) returns a PDF combining both ledgers.
  * Bad coparent_email → 404.
  * Mode query params (`even` / `income` / `custom`) accepted.
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


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str]:
    email = f"iter149_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter149 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def _seed(client: TestClient, token: str, entries: list) -> None:
    for label, cents, cat in entries:
        r = client.post(
            "/api/activities-costs",
            headers={"Authorization": f"Bearer {token}"},
            json={"activity_label": label, "amount_cents": cents, "category": cat},
        )
        assert r.status_code == 200, r.text


def test_pdf_requires_auth(client: TestClient) -> None:
    r = client.get("/api/activities-costs/compare.pdf")
    assert r.status_code in (401, 403)


def test_pdf_solo_mode(client: TestClient) -> None:
    _, token = _register(client)
    _seed(client, token, [
        ("Soccer registration", 12500, "sports"),
        ("Piano", 8000, "arts"),
    ])
    r = client.get(
        "/api/activities-costs/compare.pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    body = r.content
    assert body.startswith(b"%PDF-")
    assert len(body) > 500


def test_pdf_paired_mode_all_split_modes(client: TestClient) -> None:
    email_a, token_a = _register(client)
    email_b, token_b = _register(client)
    _seed(client, token_a, [("Baseball", 20000, "sports"), ("Piano", 6000, "arts")])
    _seed(client, token_b, [("Uniform", 4000, "gear")])

    for mode, extra in [
        ("even", ""),
        ("income", "&self_income=450000&coparent_income=550000"),
        ("custom", "&custom_pct=60"),
    ]:
        r = client.get(
            f"/api/activities-costs/compare.pdf?coparent_email={email_b}&mode={mode}{extra}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 200, (mode, r.text[:200])
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF-")


def test_pdf_unknown_coparent_returns_404(client: TestClient) -> None:
    _, token = _register(client)
    # Log one entry so we bypass the consent-gate 403 and exercise
    # the 404 branch instead.
    _seed(client, token, [("Cleats", 5500, "gear")])
    r = client.get(
        "/api/activities-costs/compare.pdf?coparent_email=nobody-here@example.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_pdf_content_disposition_inline(client: TestClient) -> None:
    _, token = _register(client)
    _seed(client, token, [("Camp", 15000, "camps")])
    r = client.get(
        "/api/activities-costs/compare.pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    disp = r.headers.get("content-disposition", "")
    assert "activity-cost-ledger.pdf" in disp
