"""Iter 196 — Front Door restructure · multi-assessment case model +
`/case/:caseId` scoped parent view.

Locks:
  * Legacy cases without `assigned_steps` on the doc still return a
    normalised one-item list via `_case_public_shape`.
  * Professional-created cases accept optional `assigned_steps` with
    per-step `required: bool`. The primary lane is always first.
  * Duplicate rows are deduped (primary lane can't be added again
    via `assigned_steps`; second identical row is silently dropped).
  * Unknown assessment_type in `assigned_steps` raises 400.
  * `GET /api/joint-alignment/case/{case_id}`:
      - requires auth
      - 403 when the caller is neither parent on the case
      - 404 when the code is malformed / missing
      - returns caller-scoped `me.steps` array with each step's
        required flag, label, and status
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env BEFORE `joint_alignment_routes` (which pulls in `auth`
# which reads JWT_SECRET at import time). Without this the pure-
# function tests that skip the `client` fixture fail on collection.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe_cases():
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            await c[DB_NAME].joint_alignment_cases.delete_many(
                {"case_id": {"$regex": "^SA-1196"}},
            )
        finally:
            c.close()
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_run())
    loop.close()
    yield


def _mock_admin(app, *, user_id: str, email: str):
    """Override get_current_user with an in-memory admin/parent
    identity so we can drive the endpoint without JWT scaffolding."""
    from auth import get_current_user
    from models import UserPublic
    u = UserPublic(
        user_id=user_id,
        email=email,
        name="Test Parent",
        created_at=datetime.now(timezone.utc).isoformat(),
        is_guest=False,
    )
    app.dependency_overrides[get_current_user] = lambda: u
    return u


# ---------------------------------------------------------------------------
# _normalise_assigned_steps — legacy compat.
# ---------------------------------------------------------------------------

def test_legacy_case_synthesises_single_step_list():
    """A case document persisted BEFORE iter196 has no `assigned_steps`
    field. The public shape MUST still expose a one-item list derived
    from the top-level `assessment_type` so downstream consumers see
    a consistent shape."""
    from joint_alignment_routes import _normalise_assigned_steps
    legacy = {"case_id": "SA-119601", "assessment_type": "educational"}
    steps = _normalise_assigned_steps(legacy)
    assert len(steps) == 1
    assert steps[0]["assessment_type"] == "educational"
    assert steps[0]["required"] is True


def test_case_public_shape_exposes_assigned_steps_with_labels():
    from joint_alignment_routes import _case_public_shape
    case = {
        "case_id": "SA-119602",
        "assessment_type": "co-parenting",
        "assigned_steps": [
            {"assessment_type": "co-parenting", "required": True},
            {"assessment_type": "educational", "required": False},
        ],
        "parents": [
            {"email": "p1@t.local", "accepted_at": datetime.now(timezone.utc)},
            {"email": "p2@t.local"},
        ],
    }
    shape = _case_public_shape(case)
    steps = shape["assigned_steps"]
    assert [s["assessment_type"] for s in steps] == ["co-parenting", "educational"]
    assert [s["required"] for s in steps] == [True, False]
    # Human-readable labels drive the parent-facing UI.
    assert steps[0]["label"] == "Co-Parenting Assessment"
    assert steps[1]["label"] == "Educational Needs Assessment"
    # Per-parent status: p1 accepted (in_progress on step 1), p2 invited.
    assert steps[0]["parent_statuses"] == ["in_progress", "invited"]


# ---------------------------------------------------------------------------
# _build_case_assigned_steps — dedupes primary + validates types.
# ---------------------------------------------------------------------------

def test_build_case_assigned_steps_primary_always_first_and_required():
    from joint_alignment_routes import _build_case_assigned_steps, AssignedStep
    out = _build_case_assigned_steps(
        primary="co-parenting",
        extra=[
            AssignedStep(assessment_type="educational", required=False),
            AssignedStep(assessment_type="medical", required=True),
        ],
    )
    assert out[0] == {"assessment_type": "co-parenting", "required": True}
    assert {r["assessment_type"] for r in out} == {"co-parenting", "educational", "medical"}
    # Required flag is preserved on non-primary rows.
    edu = next(r for r in out if r["assessment_type"] == "educational")
    assert edu["required"] is False


def test_build_case_assigned_steps_dedupes_primary():
    """A professional who accidentally lists the primary lane again
    in `assigned_steps` must NOT get it twice on the case doc."""
    from joint_alignment_routes import _build_case_assigned_steps, AssignedStep
    out = _build_case_assigned_steps(
        primary="co-parenting",
        extra=[
            AssignedStep(assessment_type="co-parenting", required=False),
            AssignedStep(assessment_type="educational", required=True),
        ],
    )
    # Primary appears once, and stays required despite the dupe's
    # required=False (the primary is inviolate).
    cp_rows = [r for r in out if r["assessment_type"] == "co-parenting"]
    assert len(cp_rows) == 1
    assert cp_rows[0]["required"] is True
    assert any(r["assessment_type"] == "educational" for r in out)


def test_build_case_assigned_steps_rejects_unknown_type():
    from joint_alignment_routes import _build_case_assigned_steps, AssignedStep
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _build_case_assigned_steps(
            primary="co-parenting",
            extra=[AssignedStep(assessment_type="not-a-real-lane", required=True)],
        )
    assert exc.value.status_code == 400


def test_create_case_response_echoes_assigned_steps(client):
    """POST /professional/joint-alignment/cases MUST echo the
    persisted `assigned_steps` array in its response so clients
    don't need to round-trip to see what was stored. Contract parity
    with GET /joint-alignment/case/{id}."""
    from server import app
    _mock_admin(app, user_id="u-prof-196", email="prof-196@t.local")
    body = {
        "assessment_type": "co-parenting",
        "parents": [
            {"email": f"iter196-a-{os.getpid()}@example.com", "name": "P A"},
            {"email": f"iter196-b-{os.getpid()}@example.com", "name": "P B"},
        ],
        "assigned_steps": [
            {"assessment_type": "educational", "required": False},
            {"assessment_type": "medical", "required": True},
        ],
    }
    r = client.post("/api/professional/joint-alignment/cases", json=body)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "assigned_steps" in payload
    at_list = [s["assessment_type"] for s in payload["assigned_steps"]]
    assert at_list == ["co-parenting", "educational", "medical"]
    required = {s["assessment_type"]: s["required"] for s in payload["assigned_steps"]}
    assert required == {"co-parenting": True, "educational": False, "medical": True}
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /joint-alignment/case/{case_id} — caller-scoped view.
# ---------------------------------------------------------------------------

async def _seed_case(*, case_id: str, parents: list, assigned_steps=None,
                     primary: str = "co-parenting"):
    c = AsyncIOMotorClient(MONGO_URL)
    try:
        doc = {
            "case_id": case_id,
            "assessment_type": primary,
            "professional": {"id": "prof-1", "name": "Test Prof",
                             "email": "prof@t.local"},
            "parents": parents,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        }
        if assigned_steps is not None:
            doc["assigned_steps"] = assigned_steps
        await c[DB_NAME].joint_alignment_cases.insert_one(doc)
    finally:
        c.close()


def test_case_endpoint_404_when_case_missing(client):
    from server import app
    _mock_admin(app, user_id="u-missing", email="missing@t.local")
    r = client.get("/api/joint-alignment/case/SA-999999")
    # Missing case → 404
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_case_endpoint_403_when_caller_not_on_case(client):
    from server import app
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_seed_case(
        case_id="SA-119610",
        parents=[
            {"email": "known1@t.local"},
            {"email": "known2@t.local"},
        ],
    ))
    loop.close()

    _mock_admin(app, user_id="u-stranger", email="stranger@t.local")
    r = client.get("/api/joint-alignment/case/SA-119610")
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_case_endpoint_returns_caller_scoped_steps(client):
    from server import app
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_seed_case(
        case_id="SA-119611",
        primary="co-parenting",
        assigned_steps=[
            {"assessment_type": "co-parenting", "required": True},
            {"assessment_type": "educational", "required": False},
        ],
        parents=[
            {
                "email": "on-case@t.local",
                "accepted_at": datetime.now(timezone.utc),
            },
            {"email": "coparent@t.local"},
        ],
    ))
    loop.close()

    _mock_admin(app, user_id="u-on-case", email="on-case@t.local")
    r = client.get("/api/joint-alignment/case/SA-119611")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "SA-119611"
    # Public assigned_steps carries the case-wide labels.
    at_list = [s["assessment_type"] for s in body["assigned_steps"]]
    assert at_list == ["co-parenting", "educational"]
    # Caller-scoped `me.steps` mirrors the assigned_steps but adds
    # personal status. The caller has accepted → in_progress on both.
    assert "me" in body
    me = body["me"]
    assert [s["assessment_type"] for s in me["steps"]] == ["co-parenting", "educational"]
    assert [s["required"] for s in me["steps"]] == [True, False]
    assert [s["status"] for s in me["steps"]] == ["in_progress", "in_progress"]
    # Human-friendly labels are surfaced so the frontend doesn't need
    # its own label registry.
    assert me["steps"][0]["label"] == "Co-Parenting Assessment"
    assert me["steps"][1]["label"] == "Educational Needs Assessment"
    app.dependency_overrides.clear()


def test_case_endpoint_normalises_legacy_case_shape(client):
    """A pre-iter196 case with no `assigned_steps` field must still
    return a 1-item `me.steps` list so the /case/:caseId page has
    something to render."""
    from server import app
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_seed_case(
        case_id="SA-119612",
        primary="medical",
        # NO assigned_steps field.
        parents=[
            {"email": "legacy@t.local"},
            {"email": "co-legacy@t.local"},
        ],
    ))
    loop.close()

    _mock_admin(app, user_id="u-legacy", email="legacy@t.local")
    r = client.get("/api/joint-alignment/case/SA-119612")
    assert r.status_code == 200
    body = r.json()
    assert len(body["assigned_steps"]) == 1
    assert body["assigned_steps"][0]["assessment_type"] == "medical"
    assert body["me"]["steps"][0]["required"] is True
    assert body["me"]["steps"][0]["status"] == "invited"
    app.dependency_overrides.clear()
