"""iter123 · Joint Agreement public share-link flow.

Covers the three new endpoints added in this iteration:

  * POST /api/joint-agreement/{share_id}/share-link
  * GET  /api/joint-agreement/shared/{token}
  * GET  /api/joint-agreement/shared/{token}/pdf

Uses the FastAPI TestClient with monkey-patched auth + share fixtures so
the tests are hermetic and do not require a running MongoDB.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def app_and_state(monkeypatch):
    """Import the FastAPI app fresh with a stub DB + stub auth."""
    # Ensure fresh imports so our monkeypatches take effect.
    for mod in ("server", "joint_agreement_routes", "share_routes"):
        sys.modules.pop(mod, None)

    from server import app
    import joint_agreement_routes as jar

    # -- Stub DB collections we touch --------------------------------------
    tokens_store: dict = {}
    phi_log: list = []

    async def _record_share_token(db, *, jti, user_id, doc_type, doc_id,
                                  expires_at=None, label=None):
        tokens_store[jti] = {
            "jti": jti, "user_id": user_id, "doc_type": doc_type,
            "doc_id": doc_id, "expires_at": expires_at,
            "label": label, "revoked_at": None,
        }
        return tokens_store[jti]

    async def _is_revoked(db, jti):
        row = tokens_store.get(jti)
        return bool(row and row.get("revoked_at"))

    async def _record_phi(db, **kwargs):
        phi_log.append(kwargs)

    monkeypatch.setattr(jar, "record_share_token", _record_share_token)
    monkeypatch.setattr(jar, "is_share_token_revoked", _is_revoked)
    monkeypatch.setattr(
        "phi_access_routes.record_phi_access", _record_phi, raising=False,
    )

    # -- Stub share resolver ----------------------------------------------
    fake_share = {
        "share_id": "sh_test",
        "_user_pair": ["userA", "userB"],
        "status": "active",
    }

    async def _find_share(db, share_id, user_id):
        assert share_id == "sh_test"
        assert user_id in ("userA", "userB")
        return dict(fake_share)

    monkeypatch.setattr(jar, "_find_active_share", _find_share)

    # -- Stub name lookups + agreement loaders ----------------------------
    async def _display_name(db, uid, default):
        return {"userA": "Alex Parent", "userB": "Blake Parent"}.get(uid, default)

    async def _load_latest(db, uid):
        # Both parents have a drafted agreement.
        return {
            "agreement_id": f"agr_{uid}",
            "generated_at": "2026-02-22T00:00:00+00:00",
            "shared_goals": ["Child feels safe in both homes"],
            "communication": [
                {"area": "Texting", "agreement": "Reply within 24 hours."},
            ],
            "child_needs": [],
            "household_rules": [],
            "priority_items": [],
            "open_for_discussion": [],
            "closing_note": "",
        }

    monkeypatch.setattr(jar, "_load_user_display_name", _display_name)
    monkeypatch.setattr(jar, "_load_latest_agreement", _load_latest)

    # -- Stub auth dependency ---------------------------------------------
    from auth import UserPublic, get_current_user

    def _fake_user():
        return UserPublic(
            user_id="userA", email="a@test.local", name="Alex Parent",
            is_guest=False, is_admin=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    app.dependency_overrides[get_current_user] = _fake_user

    # -- Stub the DB dependency + app.state.db so route can access it -----
    class _FakeDB:
        pass

    from auth import get_db
    app.dependency_overrides[get_db] = lambda: _FakeDB()
    app.state.db = _FakeDB()

    yield app, tokens_store, phi_log

    app.dependency_overrides.clear()


def test_share_link_creation_requires_consent(app_and_state):
    from fastapi.testclient import TestClient
    app, _tokens, _phi = app_and_state
    client = TestClient(app)

    res = client.post(
        "/api/joint-agreement/sh_test/share-link",
        json={"consent_acknowledged": False},
    )
    assert res.status_code == 400
    assert "consent" in res.json()["detail"].lower()


def test_share_link_full_roundtrip(app_and_state):
    from fastapi.testclient import TestClient
    app, tokens, phi = app_and_state
    client = TestClient(app)

    # 1. Mint
    res = client.post(
        "/api/joint-agreement/sh_test/share-link",
        json={"consent_acknowledged": True, "expire_days": 7},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["path"].startswith("/joint-agreement/shared/")
    assert body["api_path"].startswith("/api/joint-agreement/shared/")
    assert body["expire_days"] == 7
    assert body["jti"] in tokens
    token = body["token"]

    # 2. Public read succeeds and returns the joint payload shape
    res2 = client.get(f"/api/joint-agreement/shared/{token}")
    assert res2.status_code == 200, res2.text
    joint = res2.json()
    assert joint["report_type"] == "joint_coparenting_agreement_draft"
    assert joint["parent_a_name"] == "Alex Parent"
    assert joint["parent_b_name"] == "Blake Parent"
    assert joint["shared_by_name"] == "Alex Parent"
    assert "disclaimer" in joint
    assert "sections" in joint and len(joint["sections"]) >= 1

    # 3. Public PDF works and is a PDF
    res3 = client.get(f"/api/joint-agreement/shared/{token}/pdf")
    assert res3.status_code == 200, res3.text
    assert res3.headers["content-type"] == "application/pdf"
    assert res3.content[:4] == b"%PDF"

    # 4. Revocation makes both endpoints 404
    tokens[body["jti"]]["revoked_at"] = datetime.now(timezone.utc).isoformat()
    res4 = client.get(f"/api/joint-agreement/shared/{token}")
    assert res4.status_code == 404
    assert "revoked" in res4.json()["detail"].lower()
    res5 = client.get(f"/api/joint-agreement/shared/{token}/pdf")
    assert res5.status_code == 404

    # 5. PHI access log captured both a create + external read entries
    kinds = [entry["action"] for entry in phi]
    assert "share_link_created" in kinds
    assert "external_read_via_share_link" in kinds
    assert "external_download_via_share_link" in kinds


def test_shared_endpoint_rejects_wrong_doc_type(app_and_state):
    from fastapi.testclient import TestClient
    from auth import create_share_token
    app, _tokens, _phi = app_and_state
    client = TestClient(app)

    # Mint a safety-typed token — the endpoint must reject it.
    other_token = create_share_token(
        doc_type="safety", doc_id="sh_test", user_id="userA",
    )
    res = client.get(f"/api/joint-agreement/shared/{other_token}")
    assert res.status_code == 404


def test_shared_endpoint_rejects_invalid_token(app_and_state):
    from fastapi.testclient import TestClient
    app, _t, _p = app_and_state
    client = TestClient(app)
    res = client.get("/api/joint-agreement/shared/not-a-real-jwt")
    assert res.status_code == 404
