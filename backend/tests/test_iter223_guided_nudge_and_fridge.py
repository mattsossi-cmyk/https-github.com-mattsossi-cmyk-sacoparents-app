"""iter223 — Guided Draft Nudge cron + Fridge-size Recap PDF variant."""
from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
import yaml

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

# Load cron secret from backend/.env directly (do not depend on process env)
CRON_SECRET = ""
with open("/app/backend/.env") as f:
    for line in f:
        if line.startswith("WEBHOOK_CRON_SECRET="):
            CRON_SECRET = line.split("=", 1)[1].strip().strip('"')

sys.path.insert(0, "/app/backend")


# ---------------------------------------------------------------------
# Cron endpoint auth
# ---------------------------------------------------------------------
class TestCronAuth:
    URL = None

    @classmethod
    def setup_class(cls):
        cls.URL = f"{BASE_URL}/api/cron/guided-draft-nudge"

    def test_no_auth_header_returns_401(self):
        r = requests.post(self.URL, timeout=15)
        assert r.status_code == 401
        assert "invalid cron auth" in r.text.lower() or "cron" in r.text.lower()

    def test_wrong_bearer_returns_401(self):
        r = requests.post(self.URL, headers={"Authorization": "Bearer wrong-secret"}, timeout=15)
        assert r.status_code == 401
        assert "invalid cron auth" in r.text.lower()

    def test_correct_bearer_returns_200_manual_run_id(self):
        assert CRON_SECRET, "WEBHOOK_CRON_SECRET missing"
        r = requests.post(
            self.URL,
            headers={"Authorization": f"Bearer {CRON_SECRET}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("enqueued") == "guided-draft-nudge"
        assert data.get("run_id") == "manual"

    def test_x_webhook_id_echoed_as_run_id(self):
        assert CRON_SECRET
        r = requests.post(
            self.URL,
            headers={
                "Authorization": f"Bearer {CRON_SECRET}",
                "X-Webhook-Id": "test-run-abc123",
            },
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json().get("run_id") == "test-run-abc123"


# ---------------------------------------------------------------------
# Worker: send_guided_draft_nudges — direct DB seed + call
# ---------------------------------------------------------------------
@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db_and_user():
    """A throwaway parent (no old safety result) with a portal_state row. Removed after."""
    import uuid
    from motor.motor_asyncio import AsyncIOMotorClient

    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    user_id = f"test-nudge-{uuid.uuid4().hex[:10]}"
    email = f"{user_id}@example.com"

    loop = asyncio.new_event_loop()

    async def _add_user():
        await db.users.insert_one({"user_id": user_id, "email": email, "name": "Nudge Test", "align_ref": str(uuid.uuid4())})

    try:
        loop.run_until_complete(_add_user())
        yield db, user_id, email, loop
    finally:
        async def _cleanup():
            await db.portal_state.delete_many({"user_id": user_id})
            await db.guided_draft_nudges.delete_many({"user_id": user_id})
            await db.users.delete_many({"user_id": user_id})
        loop.run_until_complete(_cleanup())
        client.close()
        loop.close()


def _now_ms_days_ago(days: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)


class TestNudgeWorker:
    def _seed_draft(self, db, user_id, days_ago, loop):
        # "foundation" / "safety" drafts are hidden topics and never get a nudge; use a visible one.
        snap = {
            "topic": "coparenting",
            "answers": [{"q": "Q1", "a": "A1"}],
            "progress": {"step": 3, "total": 5},
            "updated_at": _now_ms_days_ago(days_ago),
        }
        async def _seed():
            await db.portal_state.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "guided_drafts": {"coparenting": snap}}},
                upsert=True,
            )
            # Clear any prior nudge for this user (fresh week key)
            await db.guided_draft_nudges.delete_many({"user_id": user_id})

        loop.run_until_complete(_seed())

    def test_old_safety_result_holds_the_nudge(self, db_and_user, monkeypatch):
        db, user_id, _email, loop = db_and_user
        from guided_draft_nudge import send_guided_draft_nudges
        import email_service
        sent_to = []
        monkeypatch.setattr(email_service, "send_guided_draft_nudge", lambda **kw: sent_to.append(kw["to_email"]))

        self._seed_draft(db, user_id, days_ago=7, loop=loop)

        async def _flag_and_run():
            await db.portal_state.update_one({"user_id": user_id}, {"$set": {"safety_ack": {"flagged": True}}})
            await send_guided_draft_nudges(db)
            return await db.guided_draft_nudges.find_one({"user_id": user_id})

        row = loop.run_until_complete(_flag_and_run())
        assert _email not in sent_to
        assert row is None

    def test_7_day_old_draft_is_eligible_and_sent(self, db_and_user, monkeypatch):
        db, user_id, _email, loop = db_and_user
        from guided_draft_nudge import send_guided_draft_nudges
        import email_service
        # Resend in the preview refuses test addresses; the sweep logic is what's under test.
        monkeypatch.setattr(email_service, "send_guided_draft_nudge", lambda **kw: None)

        self._seed_draft(db, user_id, days_ago=7, loop=loop)

        stats = loop.run_until_complete(send_guided_draft_nudges(db))
        assert stats["eligible"] >= 1
        assert stats["sent"] >= 1
        # Dedupe row written
        row = loop.run_until_complete(
            db.guided_draft_nudges.find_one({"user_id": user_id, "topic": "coparenting"})
        )
        assert row is not None
        assert "week_key" in row
        assert "sent_at" in row
        assert "days_since_update" in row
        assert "days_left" in row
        assert 5 <= row["days_since_update"] <= 9
        assert 5 <= row["days_left"] <= 9

    def test_second_run_dedupes(self, db_and_user, monkeypatch):
        db, user_id, _email, loop = db_and_user
        from guided_draft_nudge import send_guided_draft_nudges
        import email_service
        # Resend in the preview refuses test addresses; the sweep logic is what's under test.
        monkeypatch.setattr(email_service, "send_guided_draft_nudge", lambda **kw: None)

        self._seed_draft(db, user_id, days_ago=7, loop=loop)
        stats1 = loop.run_until_complete(send_guided_draft_nudges(db))
        assert stats1["sent"] >= 1
        stats2 = loop.run_until_complete(send_guided_draft_nudges(db))
        assert stats2["sent"] == 0
        assert stats2["skipped_dupes"] >= 1

    def test_2_day_old_draft_not_eligible(self, db_and_user):
        db, user_id, _email, loop = db_and_user
        from guided_draft_nudge import send_guided_draft_nudges

        self._seed_draft(db, user_id, days_ago=2, loop=loop)
        stats = loop.run_until_complete(send_guided_draft_nudges(db))
        # Might still have OTHER stale drafts from other users — check row NOT written for this user
        row = loop.run_until_complete(
            db.guided_draft_nudges.find_one({"user_id": user_id, "topic": "coparenting"})
        )
        assert row is None

    def test_20_day_old_draft_beyond_ttl_not_eligible(self, db_and_user):
        db, user_id, _email, loop = db_and_user
        from guided_draft_nudge import send_guided_draft_nudges

        self._seed_draft(db, user_id, days_ago=20, loop=loop)
        loop.run_until_complete(send_guided_draft_nudges(db))
        row = loop.run_until_complete(
            db.guided_draft_nudges.find_one({"user_id": user_id, "topic": "coparenting"})
        )
        assert row is None, "20-day-old draft should NOT get a nudge (past TTL)"


# ---------------------------------------------------------------------
# Fridge PDF variant
# ---------------------------------------------------------------------
class TestFridgePdf:
    URL = None

    @classmethod
    def setup_class(cls):
        cls.URL = f"{BASE_URL}/api/portal/guided-snapshot-pdf"

    def _payload(self, **kw):
        base = {
            "topic": "foundation",
            "answers": [
                {"q": f"Question {i}", "a": f"Answer {i} text here."} for i in range(5)
            ],
            "parent_name": "Sam",
        }
        base.update(kw)
        return base

    def test_fridge_variant_returns_a6_postcard_pdf(self):
        r = requests.post(self.URL, json=self._payload(variant="fridge"), timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert "coparent-snapshot-foundation-fridge.pdf" in r.headers.get("content-disposition", "")
        assert r.content.startswith(b"%PDF")
        # postcard-sized — expect small
        assert 800 <= len(r.content) <= 4000, f"unexpected fridge size {len(r.content)}"

    def test_medical_fridge_empty_answers_still_ok(self):
        r = requests.post(
            self.URL,
            json={"topic": "medical", "variant": "fridge", "answers": []},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.content.startswith(b"%PDF")

    def test_bogus_variant_rejected(self):
        r = requests.post(self.URL, json=self._payload(variant="bogus"), timeout=15)
        assert r.status_code == 422

    def test_default_variant_larger_than_fridge(self):
        r_std = requests.post(self.URL, json=self._payload(), timeout=30)
        r_frd = requests.post(self.URL, json=self._payload(variant="fridge"), timeout=30)
        assert r_std.status_code == 200 and r_frd.status_code == 200
        assert "coparent-snapshot-foundation.pdf" in r_std.headers["content-disposition"]
        assert "-fridge" not in r_std.headers["content-disposition"]
        assert len(r_std.content) > len(r_frd.content)

    def test_safety_flagged_fridge_contains_marker(self):
        r = requests.post(
            self.URL,
            json=self._payload(variant="fridge", safety_flagged=True),
            timeout=30,
        )
        assert r.status_code == 200
        # Text may be encoded as PDF stream — extract via pypdf
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(r.content))
        text = "".join((p.extract_text() or "") for p in reader.pages)
        assert "Grey-rock voice" in text, f"marker missing; text={text[:400]}"


# ---------------------------------------------------------------------
# Backend regression — standard variant for all six topics
# ---------------------------------------------------------------------
class TestRegression:
    def test_all_six_topics_standard_variant(self):
        url = f"{BASE_URL}/api/portal/guided-snapshot-pdf"
        for topic in ["foundation", "safety", "coparenting", "medical", "educational", "psychological"]:
            r = requests.post(url, json={"topic": topic, "answers": [{"q": "Q", "a": "A"}]}, timeout=30)
            assert r.status_code == 200, f"{topic}: {r.status_code} {r.text}"
            assert r.content.startswith(b"%PDF")


# ---------------------------------------------------------------------
# crons.yml validity
# ---------------------------------------------------------------------
class TestCronsYaml:
    def test_crons_yaml_valid(self):
        path = Path("/app/.emergent/crons.yml")
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        crons = data.get("crons") or []
        entry = next((c for c in crons if c.get("name") == "guided-draft-nudge"), None)
        assert entry is not None
        assert entry["cron"] == "0 15 * * 1"
        assert entry["method"] == "POST"
        assert entry["enabled"] is True
        assert "/api/cron/guided-draft-nudge" in entry["endpoint"]
