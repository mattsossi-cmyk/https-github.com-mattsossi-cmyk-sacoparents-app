"""iter146 — Parenting Schedule Alignment backend.

Locks the parent-facing surface + compare contract shipped in
`parenting_schedule_alignment_routes.py` + `parenting_schedule_questions.py`.

Covers:
  * GET  /api/parenting-schedule-reflection/schema
  * PUT  /api/parenting-schedule-reflection (save + score)
  * GET  /api/parenting-schedule-reflection/mine
  * POST /api/parenting-schedule-alignment/compare (waiting / ready)
  * Unsafe intake short-circuit on the summary module.
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
from ai_summary_parenting_schedule import generate_parenting_schedule_summary  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str]:
    email = f"iter146_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter146 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def test_schema_shape(client: TestClient) -> None:
    r = client.get("/api/parenting-schedule-reflection/schema")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == 1
    assert len(body["likert_labels"]) == 5
    assert set(body["dimensions"].keys()) == {"predictability", "flexibility", "transitions"}
    assert len(body["questions"]) >= 10
    q0 = body["questions"][0]
    assert set(q0.keys()) >= {"id", "dimension", "stem", "reverse"}


def test_save_and_read_reflection(client: TestClient) -> None:
    _, token = _register(client)
    r = client.put(
        "/api/parenting-schedule-reflection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": {"s1": 5, "s2": 4, "s3": 5, "s5": 4, "s9": 5, "s11": 4},
            "notes": {"s1": "keeps the rhythm steady"},
        },
    )
    assert r.status_code == 200, r.text
    scored = r.json()["score"]
    assert scored["answered_count"] == 6
    assert 0 <= scored["overall"] <= 100
    for dim in ("predictability", "flexibility", "transitions"):
        assert dim in scored["dimensions"]

    r2 = client.get(
        "/api/parenting-schedule-reflection/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["answers"]["s1"] == 5


def test_out_of_range_answers_are_dropped(client: TestClient) -> None:
    _, token = _register(client)
    r = client.put(
        "/api/parenting-schedule-reflection",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"s1": 5, "s2": 99, "not_a_real_id": 3, "s4": "bad"}},
    )
    assert r.status_code == 200
    scored = r.json()["score"]
    assert scored["answered_count"] == 1


def test_compare_waiting_state(client: TestClient) -> None:
    _, token_a = _register(client)
    email_b, _ = _register(client)
    client.put(
        "/api/parenting-schedule-reflection",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"answers": {"s1": 5, "s9": 4}},
    )
    r = client.post(
        "/api/parenting-schedule-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "waiting_on_coparent"
    assert body["coparent"]["email"] == email_b


def test_compare_ready_state_returns_shared_and_gaps(client: TestClient) -> None:
    _, token_a = _register(client)
    email_b, token_b = _register(client)
    # A: high predictability, low transitions
    client.put(
        "/api/parenting-schedule-reflection",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "answers": {
                "s1": 5, "s2": 5, "s3": 5, "s4": 5,   # predictability high
                "s5": 5, "s6": 5, "s7": 5, "s8": 5,    # flexibility high
                "s9": 5, "s10": 5, "s11": 5, "s12": 5, # transitions high
            },
        },
    )
    # B: matching predictability + flexibility, low transitions
    client.put(
        "/api/parenting-schedule-reflection",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "answers": {
                "s1": 5, "s2": 5, "s3": 5, "s4": 5,   # predictability high (shared)
                "s5": 5, "s6": 5, "s7": 5, "s8": 5,    # flexibility high (shared)
                "s9": 1, "s10": 1, "s11": 1, "s12": 1, # transitions low (gap)
            },
            "notes": {"s9": "PRIVATE — should never reach the co-parent"},
        },
    )
    r = client.post(
        "/api/parenting-schedule-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"
    gap_dims = {row["dimension"] for row in body["gaps"]}
    shared_dims = {row["dimension"] for row in body["shared"]}
    assert "transitions" in gap_dims
    assert "predictability" in shared_dims
    assert "flexibility" in shared_dims
    # Privacy: co-parent branch must NOT leak free-text notes or raw
    # answers to the caller. Regression guard for the 2026-03-06 code
    # review finding.
    assert "notes" not in body["coparent"], body["coparent"]
    assert "answers" not in body["coparent"], body["coparent"]
    # The caller's own branch should still carry their notes.
    assert "notes" in body["self"]


def test_compare_requires_self_reflection_first(client: TestClient) -> None:
    _, token_a = _register(client)
    email_b, _ = _register(client)
    r = client.post(
        "/api/parenting-schedule-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 409


def test_summary_returns_safety_sentence_on_unsafe_intake() -> None:
    payload = {
        "self": {"intake_choice": "unsafe", "score": {"overall": 40, "dimensions": {}}},
        "coparent": {"intake_choice": "productive", "score": {"overall": 60, "dimensions": {}}},
        "shared": [{"label": "Predictability", "self_score": 60, "coparent_score": 60}],
        "gaps": [],
    }
    result = asyncio.get_event_loop().run_until_complete(
        generate_parenting_schedule_summary(payload)
    )
    assert result is not None
    assert "Safety pathway" in result
