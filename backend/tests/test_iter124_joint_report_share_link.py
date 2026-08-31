"""iter124 · Joint Professional Report public share-link flow.

Mirrors iter123 (Joint Agreement) for the Joint Report endpoints:

  * POST /api/joint-professional-report/{share_id}/share-link
  * GET  /api/joint-professional-report/shared/{token}
  * GET  /api/joint-professional-report/shared/{token}/pdf
  * GET  /api/joint-professional-report/preview/{token}
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def app_and_state(monkeypatch):
    for mod in ("server", "joint_professional_report_routes", "share_routes"):
        sys.modules.pop(mod, None)

    from server import app
    import joint_professional_report_routes as jpr

    tokens_store: dict = {}
    phi_log: list = []

    async def _record_share_token(db, *, jti, user_id, doc_type, doc_id,
                                  expires_at=None, label=None, note=None):
        tokens_store[jti] = {
            "jti": jti, "user_id": user_id, "doc_type": doc_type,
            "doc_id": doc_id, "expires_at": expires_at,
            "label": label, "note": note, "revoked_at": None,
        }
        return tokens_store[jti]

    async def _is_revoked(db, jti):
        row = tokens_store.get(jti)
        return bool(row and row.get("revoked_at"))

    async def _record_phi(db, **kwargs):
        phi_log.append(kwargs)

    monkeypatch.setattr(jpr, "record_share_token", _record_share_token)
    monkeypatch.setattr(jpr, "is_share_token_revoked", _is_revoked)
    monkeypatch.setattr(
        "phi_access_routes.record_phi_access", _record_phi, raising=False,
    )

    # Stub share resolver + assemble.
    fake_share = {"share_id": "sh_test", "_user_pair": ["userA", "userB"], "status": "active"}

    async def _find_share(db, share_id, user_id):
        assert share_id == "sh_test"
        return dict(fake_share)

    async def _assemble(db, share, caller_id, share_id):
        return {
            "report_type": "joint_coparenting_summary_for_professional_review",
            "report_title": "Joint Co-Parenting Summary for Professional Review",
            "share_id": share_id,
            "parent_a_name": "Alex Parent",
            "parent_b_name": "Blake Parent",
            "disclaimer": "Preparation resource — not a custody evaluation.",
            "sections": {},
            "section_order": [{"key": "pathways", "title": "Pathways"}],
            "comparison_summary": {"total_items": 12, "aligned_pct": 75},
        }

    monkeypatch.setattr(jpr, "_find_active_share", _find_share)
    monkeypatch.setattr(jpr, "_assemble_report", _assemble)

    # Auth stubs.
    from auth import UserPublic, get_current_user, get_db

    def _fake_user():
        return UserPublic(
            user_id="userA", email="a@test.local", name="Alex Parent",
            is_guest=False, is_admin=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    app.dependency_overrides[get_current_user] = _fake_user

    class _FakeShareTokensColl:
        def __init__(self, store):
            self._store = store

        async def find_one(self, q, proj=None):  # noqa: ARG002
            row = self._store.get(q.get("jti"))
            return dict(row) if row else None

    class _FakeDB:
        pass

    _shared_db = _FakeDB()
    _shared_db.share_tokens = _FakeShareTokensColl(tokens_store)  # type: ignore[attr-defined]
    app.dependency_overrides[get_db] = lambda: _shared_db
    app.state.db = _shared_db

    # Stub the PDF builder so tests don't need real report data shapes.
    import joint_professional_report_pdf
    monkeypatch.setattr(
        joint_professional_report_pdf, "build_joint_report_pdf",
        lambda p: b"%PDF-1.4\n%stub\n",
    )

    yield app, tokens_store, phi_log
    app.dependency_overrides.clear()


def test_report_share_link_requires_consent(app_and_state):
    from fastapi.testclient import TestClient
    app, *_ = app_and_state
    client = TestClient(app)
    res = client.post(
        "/api/joint-professional-report/sh_test/share-link",
        json={"consent_acknowledged": False},
    )
    assert res.status_code == 400
    assert "consent" in res.json()["detail"].lower()


def test_report_share_link_full_roundtrip(app_and_state):
    from fastapi.testclient import TestClient
    app, tokens, phi = app_and_state
    client = TestClient(app)

    # Mint with a personal landing note.
    note = "Hi Sam — this is the SNC summary I mentioned. Happy to walk through."
    res = client.post(
        "/api/joint-professional-report/sh_test/share-link",
        json={"consent_acknowledged": True, "expire_days": 14, "note": note},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["path"].startswith("/joint-report/shared/")
    assert body["preview_path"].startswith("/api/joint-professional-report/preview/")
    assert body["api_path"].startswith("/api/joint-professional-report/shared/")
    token = body["token"]
    assert body["jti"] in tokens
    assert tokens[body["jti"]]["note"] == note

    # Public JSON read includes the sender_note.
    res2 = client.get(f"/api/joint-professional-report/shared/{token}")
    assert res2.status_code == 200, res2.text
    d = res2.json()
    assert d["report_type"] == "joint_coparenting_summary_for_professional_review"
    assert d["shared_by_name"] == "Alex Parent"
    assert d["sender_note"] == note

    # PDF works, is a PDF.
    res3 = client.get(f"/api/joint-professional-report/shared/{token}/pdf")
    assert res3.status_code == 200
    assert res3.headers["content-type"] == "application/pdf"
    assert res3.content[:4] == b"%PDF"

    # Revocation kills both.
    tokens[body["jti"]]["revoked_at"] = datetime.now(timezone.utc).isoformat()
    res4 = client.get(f"/api/joint-professional-report/shared/{token}")
    assert res4.status_code == 404
    res5 = client.get(f"/api/joint-professional-report/shared/{token}/pdf")
    assert res5.status_code == 404

    kinds = [entry["action"] for entry in phi]
    assert "share_link_created" in kinds
    assert "external_read_via_share_link" in kinds
    assert "external_download_via_share_link" in kinds


def test_report_preview_serves_og_html_to_bots(app_and_state):
    from fastapi.testclient import TestClient
    app, *_ = app_and_state
    client = TestClient(app)
    mint = client.post(
        "/api/joint-professional-report/sh_test/share-link",
        json={"consent_acknowledged": True, "expire_days": 7},
    ).json()
    token = mint["token"]
    res = client.get(
        f"/api/joint-professional-report/preview/{token}",
        headers={"User-Agent": "Slackbot-LinkExpanding 1.0"},
        follow_redirects=False,
    )
    assert res.status_code == 200
    html = res.text
    assert 'property="og:title"' in html
    assert 'property="og:image"' in html
    assert "Joint Co-Parenting Summary for Professional Review" in html
    assert "Alex Parent" in html
    assert "/joint-report/shared/" in html


def test_report_preview_redirects_real_browsers(app_and_state):
    from fastapi.testclient import TestClient
    app, *_ = app_and_state
    client = TestClient(app)
    mint = client.post(
        "/api/joint-professional-report/sh_test/share-link",
        json={"consent_acknowledged": True, "expire_days": 7},
    ).json()
    token = mint["token"]
    res = client.get(
        f"/api/joint-professional-report/preview/{token}",
        headers={"User-Agent": "Mozilla/5.0 Safari"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"].endswith(f"/joint-report/shared/{token}")


def test_report_preview_generic_card_for_invalid_token(app_and_state):
    from fastapi.testclient import TestClient
    app, *_ = app_and_state
    client = TestClient(app)
    res = client.get(
        "/api/joint-professional-report/preview/not-a-real-token",
        headers={"User-Agent": "facebookexternalhit/1.1"},
        follow_redirects=False,
    )
    assert res.status_code == 200
    html = res.text
    assert "SA CoParents" in html
    assert "shared by" not in html.lower()
