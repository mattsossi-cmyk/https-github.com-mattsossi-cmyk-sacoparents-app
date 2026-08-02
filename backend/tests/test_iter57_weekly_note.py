"""Iteration 57 tests — Preview Custom Message (handwritten weekly note).

Backend contract:
* GET  /api/dashboard/weekly-email/note        → current week's note.
* POST /api/dashboard/weekly-email/note {note} → save/clear.
* GET  /api/dashboard/weekly-email/preview     → surfaces `personal_note`.
* POST /api/dashboard/weekly-email/send        → email carries the note
  AND the note auto-clears for the current ISO week.

Notes are ISO-week scoped so next week starts fresh (matches user's
"auto-clear after Sunday send, fresh each week" preference).
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from motor.motor_asyncio import AsyncIOMotorClient

from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1,
    _client, _ensure_account, _run,
    MONGO_URL, DB_NAME,
)


NOTE_MAX = 280


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


def _reset_notes_and_log():
    async def _r():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            await db["weekly_progress_email_notes"].delete_many({})
            await db["weekly_progress_email_log"].delete_many({})
        finally:
            c.close()
    _run(_r())


@pytest.fixture(autouse=True)
def _cleanup():
    _reset_notes_and_log()
    yield
    _reset_notes_and_log()


class TestWeeklyNoteCrud:
    def test_empty_by_default(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/dashboard/weekly-email/note", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["note"] == ""
        assert body["updated_at"] is None
        assert body["max_chars"] == NOTE_MAX
        assert body["week_key"].startswith(("20", "19"))  # sane ISO-ish

    def test_save_then_read_round_trip(self, p1_client):
        text = "Proud of us for showing up this week."
        r = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/note",
            json={"note": text}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["note"] == text
        assert r.json()["cleared"] is False

        got = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/note", timeout=15,
        ).json()
        assert got["note"] == text
        assert got["updated_at"] is not None

    def test_empty_or_whitespace_clears(self, p1_client):
        p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/note",
            json={"note": "something"}, timeout=15,
        )
        r = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/note",
            json={"note": "   "}, timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["note"] == ""
        assert r.json()["cleared"] is True
        got = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/note", timeout=15,
        ).json()
        assert got["note"] == ""
        assert got["updated_at"] is None

    def test_oversize_note_truncates_to_max(self, p1_client):
        r = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/note",
            json={"note": "x" * (NOTE_MAX + 120)}, timeout=15,
        )
        assert r.status_code == 200
        assert len(r.json()["note"]) == NOTE_MAX


class TestWeeklyNoteInPreviewAndSend:
    def test_preview_surfaces_saved_note(self, p1_client):
        text = "Small steady steps. Keep going."
        p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/note",
            json={"note": text}, timeout=15,
        )
        preview = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/preview", timeout=20,
        ).json()["preview"]
        assert "personal_note" in preview
        assert preview["personal_note"] == text
        assert "personal_note_updated_at" in preview

    def test_send_includes_note_then_clears_it(self, p1_client):
        text = "One last push before mediation."
        p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/note",
            json={"note": text}, timeout=15,
        )
        sent = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={"force": True}, timeout=60,
        )
        assert sent.status_code == 200, sent.text
        body = sent.json()
        assert body["already_sent"] is False
        assert body["personal_note_included"] is True

        # Note must be auto-cleared for this ISO week so next preview
        # starts blank ("fresh each week" per user preference).
        got = p1_client.get(
            f"{BASE_URL}/api/dashboard/weekly-email/note", timeout=15,
        ).json()
        assert got["note"] == ""
        assert got["updated_at"] is None

    def test_send_without_note_reports_not_included(self, p1_client):
        # No note saved.
        sent = p1_client.post(
            f"{BASE_URL}/api/dashboard/weekly-email/send",
            json={"force": True}, timeout=60,
        ).json()
        assert sent["personal_note_included"] is False
