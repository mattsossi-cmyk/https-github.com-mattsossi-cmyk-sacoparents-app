"""iter144 — Family-violence safety gate on parent-to-co-parent invitations.

Founder directive (2026-03-04): every parent-driven invitation targeting the
other parent must be gated on the family-violence / IPV safety screen. If
the parent has not completed the screen, or their latest result is Level 1
or Level 2, the invite MUST be blocked with a compassionate 403.

Endpoints locked here:
  * POST /api/invites/coparent         — direct email invite
  * POST /api/link-codes               — sacoparentsalign.com join code
  * GET  /api/invites/coparent/gate    — non-raising status probe for the UI

Non-gated paths verified to STILL work:
  * POST /api/professionals/{id}/send-alignment-code (professional-directed)
"""
import pytest
pytest.skip("In-app safety screen turned off (2026-10); screening now happens on SACOparentsAlign.", allow_module_level=True)

import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient as SyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, str, str]:
    email = f"iter144_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Iter144 Parent"},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    return email, body["access_token"], body["user"]["user_id"]


def _seed_safety_level(user_id: str, email: str, level: int) -> None:
    sync = SyncClient(MONGO_URL)
    try:
        sync[DB_NAME]["safety_assessments"].delete_many({"user_id": user_id})
        sync[DB_NAME]["safety_assessments"].insert_one({
            "assessment_id": f"sa_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "email": email,
            "section_1": {},
            "section_2": {},
            "result": {"level": level, "pathway_title": f"Level {level}"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        sync.close()


# ------------------------- gate probe ------------------------- #

def test_gate_probe_no_screen(client: TestClient) -> None:
    _, token, _ = _register(client)
    r = client.get(
        "/api/invites/coparent/gate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["clear"] is False
    assert body["level"] is None
    assert body["code"] == "safety_screen_required"


def test_gate_probe_level_2_blocked(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 2)
    r = client.get(
        "/api/invites/coparent/gate",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["clear"] is False
    assert body["level"] == 2
    assert body["code"] == "safety_screen_blocked"


def test_gate_probe_level_3_clear(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 3)
    r = client.get(
        "/api/invites/coparent/gate",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["clear"] is True
    assert body["level"] == 3
    assert body["code"] == "ok"


# ------------------------- POST /invites/coparent ------------------------- #

def test_coparent_invite_blocked_when_no_screen(client: TestClient) -> None:
    _, token, _ = _register(client)
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code == 403, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "safety_screen_required"
    assert "safety" in detail["message"].lower()
    assert detail["hotline"] == "1-800-799-7233"


def test_coparent_invite_blocked_at_level_1(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 1)
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["code"] == "safety_screen_blocked"
    assert detail["level"] == 1


def test_coparent_invite_blocked_at_level_2(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 2)
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "safety_screen_blocked"


def test_coparent_invite_allowed_at_level_3(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 3)
    # We don't care whether Resend delivers — only that the gate lets us
    # through. A 503 (email not configured) also proves the gate passed.
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    # gate passed => NOT 403 with a gate code
    assert r.status_code != 403 or r.json().get("detail", {}).get("code") not in (
        "safety_screen_required",
        "safety_screen_blocked",
    ), r.text


def test_coparent_invite_allowed_at_level_4(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    r = client.post(
        "/api/invites/coparent",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"other_{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert r.status_code != 403 or r.json().get("detail", {}).get("code") not in (
        "safety_screen_required",
        "safety_screen_blocked",
    ), r.text


# ------------------------- POST /link-codes ------------------------- #

def test_link_code_mint_blocked_when_no_screen(client: TestClient) -> None:
    _, token, _ = _register(client)
    r = client.post(
        "/api/link-codes",
        headers={"Authorization": f"Bearer {token}"},
        json={"context": "coparenting"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "safety_screen_required"


def test_link_code_mint_blocked_at_level_2(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 2)
    r = client.post(
        "/api/link-codes",
        headers={"Authorization": f"Bearer {token}"},
        json={"context": "coparenting"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "safety_screen_blocked"


def test_link_code_mint_allowed_at_level_4(client: TestClient) -> None:
    email, token, uid = _register(client)
    _seed_safety_level(uid, email, 4)
    r = client.post(
        "/api/link-codes",
        headers={"Authorization": f"Bearer {token}"},
        json={"context": "coparenting"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["code"].startswith("SA-")


# ------------------------- professional path is NOT gated ------------------------- #

def test_send_to_professional_not_gated_by_safety(client: TestClient) -> None:
    """Sending a code to a *professional* is deliberately not gated by the
    IPV screen — a professional is not the safety risk and blocking this
    surface would harm the parent's ability to seek help."""
    _, token, _ = _register(client)
    # No safety assessment seeded — should still be allowed.
    r = client.post(
        "/api/professionals/matt-sossi/send-alignment-code",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_type": "educational"},
    )
    # Either 200 (allowed) or 404 (professional not seeded yet); NEVER a
    # gate 403. The 404 branch only happens if the professionals seed
    # didn't run; either way it's not a gate rejection.
    assert r.status_code in (200, 404), r.text
    if r.status_code == 403:
        # Should not be a gate rejection
        detail = r.json().get("detail")
        if isinstance(detail, dict):
            assert detail.get("code") not in (
                "safety_screen_required",
                "safety_screen_blocked",
            )
