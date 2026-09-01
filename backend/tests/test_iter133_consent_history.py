"""iter133 - Consent History endpoint.

`GET /api/me/hb300/consent-history` returns the caller's HB 300
consent events (marketing opt-in/out + notice acknowledgements),
newest first, no PHI beyond what the caller already generated
about themselves.

Covers:
  1. Endpoint returns only rows for the current user.
  2. Rows are marketing_opt_in / marketing_opt_out / hb300_ack —
     other phi_access_log actions are filtered out.
  3. Newest-first ordering.
  4. Empty history → `{"events": [], "total": 0}`.
  5. Row shape carries action + at + ip + user_agent + resource_id.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class _FakePhi:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def find(self, filt, proj=None):  # noqa: ARG002
        def _match(row):
            if row.get("user_id") != filt.get("user_id"):
                return False
            allowed = (filt.get("action") or {}).get("$in") or []
            return row.get("action") in allowed

        matched = [dict(r) for r in self.rows if _match(r)]

        class _Cursor:
            def __init__(self, rows):
                self._rows = rows

            def sort(self, key, direction):  # noqa: ARG002
                self._rows.sort(key=lambda r: r.get(key) or datetime.min,
                                reverse=direction < 0)
                return self

            def limit(self, n):
                self._rows = self._rows[:n]
                return self

            def __aiter__(self):
                self._it = iter(self._rows)
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        return _Cursor(matched)


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient
    from auth import UserPublic, get_current_user, get_db
    from server import app

    now = datetime.now(timezone.utc)
    phi_rows = [
        # Owner's rows (all should show up).
        {"user_id": "uA", "action": "marketing_opt_in",
         "at": now - timedelta(days=1),  "ip": "1.1.1.1",
         "user_agent": "Mozilla/5.0"},
        {"user_id": "uA", "action": "marketing_opt_out",
         "at": now - timedelta(days=3),  "ip": "1.1.1.2",
         "user_agent": "Mozilla/5.0"},
        {"user_id": "uA", "action": "hb300_ack",
         "at": now - timedelta(days=5),  "ip": "1.1.1.3",
         "user_agent": "Mozilla/5.0", "resource_id": "v2.1"},
        # Unrelated action on same user - must be filtered out.
        {"user_id": "uA", "action": "read",
         "at": now,                     "ip": "1.1.1.4"},
        # Other user - must never appear.
        {"user_id": "uB", "action": "marketing_opt_in",
         "at": now,                     "ip": "9.9.9.9"},
    ]

    class _FakeDB:
        def __init__(self):
            self.phi_access_log = _FakePhi(phi_rows)

        def __getitem__(self, name):
            return getattr(self, name)

    fake_db = _FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.state.db = fake_db

    fake_user = UserPublic(
        user_id="uA", email="a@x.com", name="Alex",
        is_guest=False, is_admin=False,
        created_at=now.isoformat(),
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_consent_history_returns_only_consent_actions(client):
    res = client.get("/api/me/hb300/consent-history")
    assert res.status_code == 200, res.text
    body = res.json()
    actions = [e["action"] for e in body["events"]]
    # 3 owner-consent rows expected; 'read' filtered, uB filtered.
    assert set(actions) == {"marketing_opt_in", "marketing_opt_out", "hb300_ack"}
    assert body["total"] == 3


def test_consent_history_newest_first(client):
    res = client.get("/api/me/hb300/consent-history")
    events = res.json()["events"]
    # opt_in (day -1) → opt_out (day -3) → hb300_ack (day -5)
    assert events[0]["action"] == "marketing_opt_in"
    assert events[-1]["action"] == "hb300_ack"


def test_consent_history_row_shape(client):
    res = client.get("/api/me/hb300/consent-history")
    ev = res.json()["events"][0]
    for key in ("action", "at", "ip", "user_agent"):
        assert key in ev, f"missing {key} in row shape"
    # hb300_ack row carries the notice version.
    ack = next(e for e in res.json()["events"] if e["action"] == "hb300_ack")
    assert ack["resource_id"] == "v2.1"


def test_consent_history_empty_for_new_user(client, monkeypatch):
    from server import app
    from auth import UserPublic, get_current_user

    fresh_user = UserPublic(
        user_id="uC", email="c@x.com", name="Casey",
        is_guest=False, is_admin=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    app.dependency_overrides[get_current_user] = lambda: fresh_user

    res = client.get("/api/me/hb300/consent-history")
    body = res.json()
    assert body == {"events": [], "total": 0}
