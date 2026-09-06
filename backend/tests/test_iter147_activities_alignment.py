"""iter147 — Activities Alignment backend.

Locks the parent-facing surface + compare contract shipped in
`activities_alignment_routes.py` + `activities_reflection_questions.py`.
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
from ai_summary_activities import generate_activities_summary  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str]:
    email = f"iter147_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter147 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"]


def test_schema_shape(client: TestClient) -> None:
    r = client.get("/api/activities-reflection/schema")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == 1
    assert len(body["likert_labels"]) == 5
    assert set(body["dimensions"].keys()) == {"awareness", "support", "logistics"}
    assert len(body["questions"]) >= 10


def test_save_and_read_reflection(client: TestClient) -> None:
    _, token = _register(client)
    r = client.put(
        "/api/activities-reflection",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": {"a1": 5, "a2": 4, "a5": 5, "a9": 4, "a10": 5},
            "notes": {"a1": "kids are into soccer and piano"},
        },
    )
    assert r.status_code == 200, r.text
    scored = r.json()["score"]
    assert scored["answered_count"] == 5
    assert 0 <= scored["overall"] <= 100
    for dim in ("awareness", "support", "logistics"):
        assert dim in scored["dimensions"]

    r2 = client.get(
        "/api/activities-reflection/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["answers"]["a1"] == 5


def test_out_of_range_answers_are_dropped(client: TestClient) -> None:
    _, token = _register(client)
    r = client.put(
        "/api/activities-reflection",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"a1": 5, "a2": 99, "junk": 3, "a4": "x"}},
    )
    assert r.status_code == 200
    scored = r.json()["score"]
    assert scored["answered_count"] == 1


def test_compare_waiting_state(client: TestClient) -> None:
    _, token_a = _register(client)
    email_b, _ = _register(client)
    client.put(
        "/api/activities-reflection",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"answers": {"a1": 5, "a5": 4}},
    )
    r = client.post(
        "/api/activities-alignment/compare",
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
    # A: high awareness + support, high logistics
    client.put(
        "/api/activities-reflection",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "answers": {
                "a1": 5, "a2": 5, "a3": 5, "a4": 5,   # awareness high
                "a5": 5, "a6": 5, "a7": 5, "a8": 5,   # support high
                "a9": 5, "a10": 5, "a11": 5, "a12": 5, # logistics high
            },
        },
    )
    # B: matching awareness + support, low logistics — with a private
    # note that must never cross the parent boundary.
    client.put(
        "/api/activities-reflection",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "answers": {
                "a1": 5, "a2": 5, "a3": 5, "a4": 5,   # awareness high (shared)
                "a5": 5, "a6": 5, "a7": 5, "a8": 5,   # support high (shared)
                "a9": 1, "a10": 1, "a11": 1, "a12": 1, # logistics low (gap)
            },
            "notes": {"a9": "PRIVATE — must not reach parent A"},
        },
    )
    r = client.post(
        "/api/activities-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"
    gap_dims = {row["dimension"] for row in body["gaps"]}
    shared_dims = {row["dimension"] for row in body["shared"]}
    assert "logistics" in gap_dims
    assert "awareness" in shared_dims
    assert "support" in shared_dims
    # Privacy regression guard (2026-03-06 code review).
    assert "notes" not in body["coparent"], body["coparent"]
    assert "answers" not in body["coparent"], body["coparent"]
    assert "notes" in body["self"]


def test_compare_requires_self_reflection_first(client: TestClient) -> None:
    _, token_a = _register(client)
    email_b, _ = _register(client)
    r = client.post(
        "/api/activities-alignment/compare",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"coparent_email": email_b},
    )
    assert r.status_code == 409


def test_summary_returns_safety_sentence_on_unsafe_intake() -> None:
    payload = {
        "self": {"intake_choice": "unsafe", "score": {"overall": 40, "dimensions": {}}},
        "coparent": {"intake_choice": "productive", "score": {"overall": 60, "dimensions": {}}},
        "shared": [{"label": "Awareness", "self_score": 60, "coparent_score": 60}],
        "gaps": [],
    }
    result = asyncio.get_event_loop().run_until_complete(
        generate_activities_summary(payload)
    )
    assert result is not None
    assert "Safety pathway" in result
