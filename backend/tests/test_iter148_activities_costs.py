"""iter148 — Activity Cost Splitter backend.

Locks the API for `activities_costs_routes.py`. Covers:
  * GET  /api/activities-costs/categories — public category chip list
  * POST /api/activities-costs           — create + basic validation
  * GET  /api/activities-costs/mine       — list + total
  * DELETE /api/activities-costs/{id}     — parent can only delete own
  * GET  /api/activities-costs/compare    — you-vs-coparent totals,
    per-category pair breakdown, note-redaction on co-parent rows.
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
    email = f"iter148_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter148 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def test_categories_public(client: TestClient) -> None:
    r = client.get("/api/activities-costs/categories")
    assert r.status_code == 200
    body = r.json()
    keys = {c["key"] for c in body["categories"]}
    assert {"sports", "arts", "gear", "other"}.issubset(keys)


def test_create_read_and_total(client: TestClient) -> None:
    _, token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    for label, amount, cat in [
        ("Soccer registration", 12500, "sports"),
        ("Piano lessons", 8000, "arts"),
        ("Cleats", 5500, "gear"),
    ]:
        r = client.post(
            "/api/activities-costs",
            headers=headers,
            json={
                "activity_label": label,
                "amount_cents": amount,
                "category": cat,
            },
        )
        assert r.status_code == 200, r.text

    mine = client.get("/api/activities-costs/mine", headers=headers)
    assert mine.status_code == 200
    body = mine.json()
    assert body["count"] == 3
    assert body["total_cents"] == 12500 + 8000 + 5500


def test_unknown_category_downgrades_to_other(client: TestClient) -> None:
    _, token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/activities-costs",
        headers=headers,
        json={"activity_label": "Rocket cost", "amount_cents": 100, "category": "spacetravel"},
    )
    assert r.status_code == 200
    assert r.json()["cost"]["category"] == "other"


def test_invalid_amount_rejected(client: TestClient) -> None:
    _, token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/activities-costs",
        headers=headers,
        json={"activity_label": "Empty amount", "amount_cents": 0},
    )
    assert r.status_code == 422


def test_delete_only_own_entry(client: TestClient) -> None:
    _, token_a = _register(client)
    _, token_b = _register(client)

    r = client.post(
        "/api/activities-costs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"activity_label": "Camp", "amount_cents": 15000, "category": "camps"},
    )
    assert r.status_code == 200
    cost_id = r.json()["cost"]["cost_id"]

    # Parent B cannot delete parent A's entry.
    r_del = client.delete(
        f"/api/activities-costs/{cost_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r_del.status_code == 404

    # Parent A can.
    r_del = client.delete(
        f"/api/activities-costs/{cost_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r_del.status_code == 200


def test_compare_totals_and_note_redaction(client: TestClient) -> None:
    _, token_a = _register(client)
    email_b, token_b = _register(client)

    # A logs two entries with a private note
    client.post(
        "/api/activities-costs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "activity_label": "Baseball registration",
            "amount_cents": 20000,
            "category": "sports",
            "note": "Reference AB-127 — invoice attached in Drive",
        },
    )
    client.post(
        "/api/activities-costs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"activity_label": "Piano lesson", "amount_cents": 6000, "category": "arts"},
    )
    # B logs one entry with a private note
    client.post(
        "/api/activities-costs",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "activity_label": "Uniform",
            "amount_cents": 4000,
            "category": "gear",
            "note": "secret coupon code XYZ",
        },
    )

    r = client.get(
        f"/api/activities-costs/compare?coparent_email={email_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["self"]["total_cents"] == 26000
    assert body["coparent"]["total_cents"] == 4000
    assert body["combined_total_cents"] == 30000
    # Your own note is visible.
    self_notes = [row["note"] for row in body["self"]["rows"]]
    assert any("AB-127" in (n or "") for n in self_notes)
    # Co-parent's notes are always redacted.
    for row in body["coparent"]["rows"]:
        assert row["note"] is None
    # per-category breakdown pairs the two parents
    cat_map = {c["key"]: c for c in body["per_category_pair"]}
    assert cat_map["sports"]["self_cents"] == 20000
    assert cat_map["sports"]["coparent_cents"] == 0
    assert cat_map["gear"]["self_cents"] == 0
    assert cat_map["gear"]["coparent_cents"] == 4000


def test_compare_unknown_coparent_returns_404(client: TestClient) -> None:
    _, token = _register(client)
    # Consent gate demands the caller has at least one entry before we
    # even resolve the co-parent email — log one so we exercise the
    # 404 branch rather than the 403 gate.
    client.post(
        "/api/activities-costs",
        headers={"Authorization": f"Bearer {token}"},
        json={"activity_label": "Cleats", "amount_cents": 5500, "category": "gear"},
    )
    r = client.get(
        "/api/activities-costs/compare?coparent_email=nobody-here@example.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_compare_without_own_entries_is_forbidden(client: TestClient) -> None:
    """
    Consent gate: a caller with no logged entries of their own cannot
    pull a stranger's itemized ledger by email. Regression guard for
    the 2026-03-06 code-review enumeration finding.
    """
    _, token_a = _register(client)
    email_b, token_b = _register(client)
    # Parent B logs an entry so the account exists and has data.
    client.post(
        "/api/activities-costs",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"activity_label": "Camp", "amount_cents": 15000, "category": "camps"},
    )
    # Parent A has nothing of their own → must be blocked.
    r = client.get(
        f"/api/activities-costs/compare?coparent_email={email_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403
    # And parent A cannot get parent B's rows via the PDF path either.
    r_pdf = client.get(
        f"/api/activities-costs/compare.pdf?coparent_email={email_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r_pdf.status_code == 403
