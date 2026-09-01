"""iter134 - NewCommentToaster contract.

Frontend toaster relies on:
  * GET /api/pathway-report/comments/mine responding with
    { "total": N, "comments": [ ... ] }
  * Each comment carrying `comment_id`, `reviewer_name`, `created_at`
    (ISO-8601 string), `comment` (text).
  * Sorted newest-first so `comments[0].created_at` is the freshest
    timestamp (baseline seed + lexical comparison against the
    localStorage sentinel).

This test pins the shape so the toaster can't silently break on a
backend refactor.
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


class _FakeCommentsColl:
    def __init__(self, rows):
        self.rows = rows

    def find(self, filt, proj=None):  # noqa: ARG002
        matched = [
            dict(r) for r in self.rows
            if all(r.get(k) == v for k, v in filt.items())
        ]

        class _Cursor:
            def __init__(self, rows):
                self._rows = rows

            def sort(self, key, direction):
                self._rows.sort(key=lambda r: r.get(key) or "",
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
    rows = [
        {"parent_user_id": "uA",
         "comment_id": "c-fresh",
         "sig_id": "sig-1",
         "audience": "mediator",
         "reviewer_name": "Sam Neutral",
         "reviewer_role": "Mediator",
         "comment_text": "Looks good — reply within 24h works for us.",
         "created_at": (now - timedelta(minutes=5)).isoformat()},
        {"parent_user_id": "uA",
         "comment_id": "c-older",
         "sig_id": "sig-1",
         "audience": "attorney",
         "reviewer_name": "Rae Attorney",
         "reviewer_role": "Attorney",
         "comment_text": "One question about the medication clause.",
         "created_at": (now - timedelta(days=2)).isoformat()},
        # Different parent - must not surface.
        {"parent_user_id": "uB",
         "comment_id": "c-other",
         "sig_id": "sig-9",
         "reviewer_name": "Mo Other",
         "reviewer_role": "Mediator",
         "comment_text": "irrelevant",
         "created_at": now.isoformat()},
    ]

    class _FakeDB:
        def __init__(self):
            self.pathway_report_comments = _FakeCommentsColl(rows)

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


def test_comments_mine_returns_total_and_comments_keys(client):
    res = client.get("/api/pathway-report/comments/mine")
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) >= {"total", "comments"}
    assert body["total"] == 2, "must filter to caller's parent_user_id"


def test_comments_mine_row_shape(client):
    body = client.get("/api/pathway-report/comments/mine").json()
    row = body["comments"][0]
    for key in ("comment_id", "reviewer_name", "created_at", "comment_text"):
        assert key in row, f"missing {key} — toaster relies on it"
    # ISO-8601 string so the toaster can lex-compare against
    # localStorage.
    assert isinstance(row["created_at"], str)
    assert "T" in row["created_at"]


def test_comments_mine_newest_first(client):
    body = client.get("/api/pathway-report/comments/mine").json()
    # First row is the "5 minutes ago" comment, second is the "2 days ago" one.
    assert body["comments"][0]["comment_id"] == "c-fresh"
    assert body["comments"][1]["comment_id"] == "c-older"
