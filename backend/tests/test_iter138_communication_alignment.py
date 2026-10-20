"""iter138 — Communication Alignment backend (Phase 2a).

Locks the parent-facing surface and the compare contract shipped in
`communication_alignment_routes.py` + `communication_reflection_questions.py`.

Covers:
  * GET  /api/communication-reflection/schema — public bank shape
  * PUT  /api/communication-reflection        — save + score
  * GET  /api/communication-reflection/mine   — read back
  * POST /api/communication-alignment/compare — pair + diff
  * Unsafe intake short-circuit (compare summary returns safety
    sentence without calling the LLM)
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402
from ai_summary_communication import generate_communication_summary  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str]:
    email = f"iter138_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter138 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


# ---------- Schema ---------- #

def test_schema_shape(client: TestClient) -> None:
    r = client.get("/api/communication-reflection/schema")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == 1
    assert len(body["likert_labels"]) == 5
    assert set(body["dimensions"].keys()) == {"clarity", "regulation", "structure"}
    assert len(body["questions"]) >= 10
    q0 = body["questions"][0]
    assert set(q0.keys()) >= {"id", "dimension", "stem", "reverse"}


# ---------- Save + read + score ---------- #

def test_save_and_read_reflection(client: TestClient) -> None:
    _, token = _register(client)
    r = client.put(
        "/api/communication-reflection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": {"c1": 5, "c2": 4, "c3": 5, "c4": 3, "c5": 4, "c8": 4},
            "notes": {"c1": "trying really hard here"},
            "intake_choice": "difficult",
        },
    )
    assert r.status_code == 200, r.text
    scored = r.json()["score"]
    assert scored["answered_count"] == 6
    assert 0 <= scored["overall"] <= 100
    # per-dimension shape
    for dim in ("clarity", "regulation", "structure"):
        assert dim in scored["dimensions"]

    r2 = client.get(
        "/api/communication-reflection/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["intake_choice"] == "difficult"
    assert body["answers"]["c1"] == 5


def test_out_of_range_answers_are_dropped(client: TestClient) -> None:
    _, token = _register(client)
    r = client.put(
        "/api/communication-reflection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": {"c1": 5, "c2": 99, "not_a_real_id": 3, "c4": "bad"},
        },
    )
    assert r.status_code == 200
    scored = r.json()["score"]
    # Only c1 survived
    assert scored["answered_count"] == 1


# ---------- Compare ---------- #

def test_compare_waiting_state_when_coparent_hasnt_submitted(client: TestClient) -> None:
    email_a, token_a = _register(client)
    email_b, _ = _register(client)
    # Only parent A has submitted.
    client.put(
        "/api/communication-reflection",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"answers": {"c1": 5, "c8": 4}, "intake_choice": "productive"},
    )
    r = client.post(
        "/api/communication-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "waiting_on_coparent"
    assert body["coparent"]["email"] == email_b


def test_compare_ready_state_returns_shared_and_gaps(client: TestClient) -> None:
    email_a, token_a = _register(client)
    email_b, token_b = _register(client)
    # A: high clarity
    client.put(
        "/api/communication-reflection",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "answers": {
                "c1": 5, "c2": 5, "c3": 5, "c12": 5,  # clarity high
                "c4": 5, "c5": 5, "c7": 5,             # regulation high
                "c8": 5, "c9": 5, "c10": 5, "c11": 5,  # structure high
            },
            "intake_choice": "productive",
        },
    )
    # B: low regulation, matching clarity + structure — private note
    # must never cross the parent boundary.
    client.put(
        "/api/communication-reflection",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "answers": {
                "c1": 5, "c2": 5, "c3": 5, "c12": 5,   # clarity high (shared)
                "c4": 1, "c5": 1, "c7": 1,              # regulation low (gap)
                "c8": 5, "c9": 5, "c10": 5, "c11": 5,   # structure high (shared)
            },
            "notes": {"c4": "PRIVATE — must not reach parent A"},
            "intake_choice": "difficult",
        },
    )
    r = client.post(
        "/api/communication-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"
    # Regulation should land in gaps (delta > 15).
    gap_labels = {row["dimension"] for row in body["gaps"]}
    shared_labels = {row["dimension"] for row in body["shared"]}
    assert "regulation" in gap_labels
    assert "clarity" in shared_labels
    assert "structure" in shared_labels
    # Privacy regression guard (2026-03-06 code review): co-parent's
    # free-text notes and raw answers must not appear in the payload.
    assert "notes" not in body["coparent"], body["coparent"]
    assert "answers" not in body["coparent"], body["coparent"]
    assert "notes" in body["self"]


def test_compare_requires_self_reflection_first(client: TestClient) -> None:
    email_a, token_a = _register(client)
    email_b, _ = _register(client)
    r = client.post(
        "/api/communication-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 409


# ---------- Unsafe intake short-circuit ---------- #

def test_summary_returns_safety_sentence_on_unsafe_intake() -> None:
    payload = {
        "self": {"intake_choice": "unsafe", "score": {"overall": 40, "dimensions": {}}},
        "coparent": {"intake_choice": "productive", "score": {"overall": 60, "dimensions": {}}},
        "shared": [{"label": "Clarity", "self_score": 60, "coparent_score": 60}],
        "gaps": [],
    }
    result = asyncio.get_event_loop().run_until_complete(
        generate_communication_summary(payload)
    )
    assert result is not None
    assert "Safety pathway" in result
