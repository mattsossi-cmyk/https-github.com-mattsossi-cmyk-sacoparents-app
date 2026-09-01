"""iter131 - Marketing Consent Toggle contract.

The /account (Data & Retention) page now surfaces a one-click
marketing opt-in toggle. Contract tests to lock down:

  1. `GET  /api/me/hb300/status` returns `marketing_opt_in` boolean.
  2. `POST /api/me/hb300/marketing` with `{opt_in: true}` flips the
     user's flag ON and returns `{ok, opt_in, updated_at}`.
  3. `POST /api/me/hb300/marketing` with `{opt_in: false}` flips it
     OFF.
  4. Every change lands in `phi_access_log` with the right action
     name (`marketing_opt_in` / `marketing_opt_out`) so the auditor
     can reconstruct the exact moment.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class _FakeUsersColl:
    def __init__(self, seed=None):
        self.rows = list(seed or [])

    async def find_one(self, filt, proj=None):  # noqa: ARG002
        for r in self.rows:
            if all(r.get(k) == v for k, v in filt.items()):
                return dict(r)
        return None

    async def update_one(self, filt, update):
        for r in self.rows:
            if all(r.get(k) == v for k, v in filt.items()):
                r.update(update.get("$set") or {})
                return None
        # Upsert-like fallback so tests don't have to pre-seed a doc
        # for every user_id.
        row = {**{k: v for k, v in filt.items()},
               **(update.get("$set") or {})}
        self.rows.append(row)
        return None


class _FakePhi:
    def __init__(self):
        self.rows: list[dict] = []

    async def insert_one(self, doc):
        self.rows.append(dict(doc))


class _FakeHb300Ack:
    async def find_one(self, filt, proj=None, sort=None):  # noqa: ARG002
        return None


class _FakeHb300Req:
    async def count_documents(self, filt):  # noqa: ARG002
        return 0


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient
    from auth import UserPublic, get_current_user, get_db
    from server import app

    class _FakeDB:
        def __init__(self):
            self.users = _FakeUsersColl([
                {"user_id": "uA", "email": "a@x.com", "name": "Alex",
                 "marketing_opt_in": False},
            ])
            self.phi_access_log = _FakePhi()
            self.hb300_acknowledgements = _FakeHb300Ack()
            self.hb300_access_requests = _FakeHb300Req()

        def __getitem__(self, name):
            return getattr(self, name)

    fake_db = _FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.state.db = fake_db  # some endpoints read from app.state directly

    fake_user = UserPublic(
        user_id="uA", email="a@x.com", name="Alex",
        is_guest=False, is_admin=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    tc = TestClient(app)
    try:
        yield tc, fake_db
    finally:
        app.dependency_overrides.clear()


def test_status_reports_marketing_opt_in_flag(client):
    tc, _ = client
    res = tc.get("/api/me/hb300/status")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["marketing_opt_in"] is False


def test_opt_in_flips_flag_and_audits(client):
    tc, db = client
    res = tc.post("/api/me/hb300/marketing", json={"opt_in": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["opt_in"] is True
    assert body["updated_at"]

    # User row updated.
    assert db.users.rows[0]["marketing_opt_in"] is True
    # PHI log carries the opt-in event.
    actions = [r["action"] for r in db.phi_access_log.rows]
    assert "marketing_opt_in" in actions

    # Status endpoint now reflects the flip.
    status = tc.get("/api/me/hb300/status").json()
    assert status["marketing_opt_in"] is True


def test_opt_out_flips_flag_and_audits(client):
    tc, db = client
    # Bootstrap: opt in first.
    tc.post("/api/me/hb300/marketing", json={"opt_in": True})
    res = tc.post("/api/me/hb300/marketing", json={"opt_in": False})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["opt_in"] is False
    assert db.users.rows[0]["marketing_opt_in"] is False
    actions = [r["action"] for r in db.phi_access_log.rows]
    assert "marketing_opt_out" in actions
