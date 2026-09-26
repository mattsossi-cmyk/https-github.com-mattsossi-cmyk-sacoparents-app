"""iter224 — Weekly Nudge Digest admin email + cron endpoint."""
from __future__ import annotations

import asyncio
import os
import sys
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

CRON_SECRET = ""
with open("/app/backend/.env") as f:
    for line in f:
        if line.startswith("WEBHOOK_CRON_SECRET="):
            CRON_SECRET = line.split("=", 1)[1].strip().strip('"')

sys.path.insert(0, "/app/backend")

CRON_URL = f"{BASE_URL}/api/cron/nudge-digest"


# ---------------------------------------------------------------------
# Cron auth
# ---------------------------------------------------------------------
class TestNudgeDigestCronAuth:
    def test_no_auth_401(self):
        r = requests.post(CRON_URL, timeout=15)
        assert r.status_code == 401
        assert "cron" in r.text.lower()

    def test_wrong_bearer_401(self):
        r = requests.post(CRON_URL, headers={"Authorization": "Bearer nope"}, timeout=15)
        assert r.status_code == 401
        assert "invalid cron auth" in r.text.lower()

    def test_correct_bearer_manual_run_id(self):
        assert CRON_SECRET
        r = requests.post(
            CRON_URL, headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=15
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("enqueued") == "nudge-digest"
        assert data.get("run_id") == "manual"

    def test_x_webhook_id_echoed(self):
        r = requests.post(
            CRON_URL,
            headers={
                "Authorization": f"Bearer {CRON_SECRET}",
                "X-Webhook-Id": "digest-run-xyz",
            },
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json().get("run_id") == "digest-run-xyz"


# ---------------------------------------------------------------------
# Worker fixtures
# ---------------------------------------------------------------------
@pytest.fixture(scope="module")
def db_users():
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv

    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    loop = asyncio.new_event_loop()

    async def _find(email):
        return await db.users.find_one({"email": email})

    u1 = loop.run_until_complete(_find("parent1@test.com"))
    u2 = loop.run_until_complete(_find("parent2@test.com"))
    assert u1 and u2, "seed users missing"
    uid1 = u1.get("user_id") or u1.get("id")
    uid2 = u2.get("user_id") or u2.get("id")
    assert uid1 and uid2

    async def _cleanup():
        await db.guided_draft_nudges.delete_many({"user_id": {"$in": [uid1, uid2]}})
        await db.portal_state.update_one(
            {"user_id": uid1}, {"$set": {"guided_drafts": None}}, upsert=True
        )
        await db.portal_state.update_one(
            {"user_id": uid2}, {"$set": {"guided_drafts": None}}, upsert=True
        )

    # Pre-clean
    loop.run_until_complete(_cleanup())

    yield db, uid1, uid2, loop

    # Post-clean
    loop.run_until_complete(_cleanup())
    client.close()
    loop.close()


def _ms_days_ago(days: float) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)


def _iso_days_ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def _seed_nudge(db, user_id, topic, days_ago):
    await db.guided_draft_nudges.insert_one({
        "user_id": user_id,
        "topic": topic,
        "sent_at": _iso_days_ago(days_ago),
        "week_key": f"seed-{topic}-{days_ago}",
        "days_since_update": 7,
        "days_left": 7,
    })


async def _set_draft(db, user_id, topic, updated_days_ago):
    """Set portal_state.guided_drafts[topic] with updated_at N days ago."""
    # Ensure guided_drafts is a dict, not null (Mongo can't set sub-field on null)
    doc = await db.portal_state.find_one({"user_id": user_id}, {"guided_drafts": 1})
    if not doc or not isinstance(doc.get("guided_drafts"), dict):
        await db.portal_state.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "guided_drafts": {}}},
            upsert=True,
        )
    await db.portal_state.update_one(
        {"user_id": user_id},
        {"$set": {f"guided_drafts.{topic}": {
            "topic": topic,
            "answers": [{"q": "Q", "a": "A"}],
            "updated_at": _ms_days_ago(updated_days_ago),
        }}},
    )


async def _clear_draft(db, user_id, topic=None):
    if topic:
        await db.portal_state.update_one(
            {"user_id": user_id}, {"$unset": {f"guided_drafts.{topic}": ""}}
        )
    else:
        await db.portal_state.update_one(
            {"user_id": user_id}, {"$set": {"guided_drafts": None}}, upsert=True
        )


async def _reset(db, uid1, uid2):
    await db.guided_draft_nudges.delete_many({"user_id": {"$in": [uid1, uid2]}})
    await db.portal_state.update_one({"user_id": uid1}, {"$set": {"guided_drafts": None}}, upsert=True)
    await db.portal_state.update_one({"user_id": uid2}, {"$set": {"guided_drafts": None}}, upsert=True)


# ---------------------------------------------------------------------
# compute_digest heuristic
# ---------------------------------------------------------------------
class TestComputeDigest:
    def test_three_nudge_heuristic(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users

        async def _seed():
            await _reset(db, uid1, uid2)
            # A) parent1 foundation nudge 10d ago, draft updated 8d ago (AFTER nudge) -> finished
            await _seed_nudge(db, uid1, "foundation", 10)
            await _set_draft(db, uid1, "foundation", 8)
            # B) parent1 medical nudge 10d ago, draft updated 12d ago (BEFORE nudge) -> NOT
            await _seed_nudge(db, uid1, "medical", 10)
            await _set_draft(db, uid1, "medical", 12)
            # C) parent2 educational nudge 10d ago, portal_state.guided_drafts null -> finished
            await _seed_nudge(db, uid2, "educational", 10)
            # (guided_drafts already null from reset)

        loop.run_until_complete(_seed())
        digest = loop.run_until_complete(compute_digest(db))

        assert digest["total_sent"] == 3, digest
        assert digest["total_finished"] == 2, digest
        assert digest["conversion_pct"] == 66.7, digest
        bt = digest["by_topic"]
        assert "Foundation Statement" in bt
        assert bt["Foundation Statement"] == {"sent": 1, "finished": 1}
        assert bt["Medical Needs Assessment"] == {"sent": 1, "finished": 0}
        assert bt["Educational Assessment"] == {"sent": 1, "finished": 1}
        # ensure no user_id keys in by_topic
        assert all(k in {"Foundation Statement", "Medical Needs Assessment", "Educational Assessment"} for k in bt)
        loop.run_until_complete(_reset(db, uid1, uid2))

    def test_window_boundaries(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users

        async def _seed():
            await _reset(db, uid1, uid2)
            await _seed_nudge(db, uid1, "foundation", 5)   # too fresh
            await _seed_nudge(db, uid1, "safety", 20)      # too old
            await _seed_nudge(db, uid1, "coparenting", 8)  # inside

        loop.run_until_complete(_seed())
        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 1, digest
        assert "Co-parenting Assessment" in digest["by_topic"]
        loop.run_until_complete(_reset(db, uid1, uid2))

    def test_empty_window(self, db_users):
        from guided_draft_digest import compute_digest, send_nudge_digest
        db, uid1, uid2, loop = db_users
        loop.run_until_complete(_reset(db, uid1, uid2))
        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 0
        assert digest["total_finished"] == 0
        assert digest["conversion_pct"] == 0.0
        assert digest["by_topic"] == {}

        # send_nudge_digest with empty window returns recipients_sent=0 and does NOT email
        import email_service
        calls = []
        orig = email_service.send_nudge_digest
        email_service.send_nudge_digest = lambda **kw: calls.append(kw)
        try:
            result = loop.run_until_complete(send_nudge_digest(db))
        finally:
            email_service.send_nudge_digest = orig
        assert result["recipients_sent"] == 0
        assert calls == []

    def test_unknown_topic_ignored(self, db_users):
        from guided_draft_digest import compute_digest
        db, uid1, uid2, loop = db_users

        async def _seed():
            await _reset(db, uid1, uid2)
            await _seed_nudge(db, uid1, "legacy_unknown_topic", 10)
            await _seed_nudge(db, uid1, "foundation", 10)

        loop.run_until_complete(_seed())
        digest = loop.run_until_complete(compute_digest(db))
        assert digest["total_sent"] == 1
        assert list(digest["by_topic"].keys()) == ["Foundation Statement"]
        loop.run_until_complete(_reset(db, uid1, uid2))


# ---------------------------------------------------------------------
# send_nudge_digest email dispatch
# ---------------------------------------------------------------------
class TestSendNudgeDigest:
    def test_emails_each_admin(self, db_users, monkeypatch):
        import guided_draft_digest
        db, uid1, uid2, loop = db_users

        async def _seed():
            await _reset(db, uid1, uid2)
            await _seed_nudge(db, uid1, "foundation", 10)

        loop.run_until_complete(_seed())

        monkeypatch.setenv("ADMIN_EMAILS", "a@x.com, b@x.com , c@x.com")

        calls = []

        def _spy(*, to_email, digest):
            calls.append((to_email, digest))

        # Patch inside email_service so guided_draft_digest's late import picks it up
        import email_service
        monkeypatch.setattr(email_service, "send_nudge_digest", _spy)

        result = loop.run_until_complete(guided_draft_digest.send_nudge_digest(db))
        assert result["recipients_sent"] == 3
        assert sorted([c[0] for c in calls]) == ["a@x.com", "b@x.com", "c@x.com"]
        # digest dict shape
        for _, d in calls:
            assert "total_sent" in d and "by_topic" in d and "conversion_pct" in d
        loop.run_until_complete(_reset(db, uid1, uid2))

    def test_admin_email_failure_does_not_abort_loop(self, db_users, monkeypatch):
        import guided_draft_digest
        db, uid1, uid2, loop = db_users

        async def _seed():
            await _reset(db, uid1, uid2)
            await _seed_nudge(db, uid1, "foundation", 10)

        loop.run_until_complete(_seed())
        monkeypatch.setenv("ADMIN_EMAILS", "fail@x.com,ok@x.com")

        def _spy(*, to_email, digest):
            if to_email == "fail@x.com":
                raise RuntimeError("resend down")

        import email_service
        monkeypatch.setattr(email_service, "send_nudge_digest", _spy)

        result = loop.run_until_complete(guided_draft_digest.send_nudge_digest(db))
        # Only 1 succeeded, but loop kept going
        assert result["recipients_sent"] == 1
        loop.run_until_complete(_reset(db, uid1, uid2))


# ---------------------------------------------------------------------
# Email body correctness
# ---------------------------------------------------------------------
class TestEmailBody:
    def test_html_and_subject_and_plain(self, monkeypatch):
        import email_service

        captured = {}

        def fake_send(*, to_email, subject, html, text, failure_message=None):
            captured["to"] = to_email
            captured["subject"] = subject
            captured["html"] = html
            captured["text"] = text

        monkeypatch.setattr(email_service, "_send", fake_send)

        digest = {
            "window_start": "2026-01-05T00:00:00+00:00",
            "window_end": "2026-01-12T00:00:00+00:00",
            "total_sent": 3,
            "total_finished": 2,
            "conversion_pct": 66.7,
            "by_topic": {
                "Foundation Statement": {"sent": 1, "finished": 1},
                "Medical Needs Assessment": {"sent": 1, "finished": 0},
                "Educational Assessment": {"sent": 1, "finished": 1},
            },
        }
        email_service.send_nudge_digest(to_email="admin@x.com", digest=digest)

        assert captured["to"] == "admin@x.com"
        assert captured["subject"] == "[SA CoParents] Nudge digest \u2014 2 of 3 finished last week"
        html = captured["html"]
        # 3 tile summary
        assert "Nudges sent" in html
        assert "Finished in 7d" in html
        assert "Conversion" in html
        assert ">3<" in html and ">2<" in html and "66.7%" in html
        # per-topic table rows
        assert "Foundation Statement" in html
        assert "Medical Needs Assessment" in html
        assert "Educational Assessment" in html
        assert "1 / 1" in html and "0 / 1" in html
        # window date range
        assert "2026-01-05" in html and "2026-01-12" in html
        # plain text
        text = captured["text"]
        assert "Foundation Statement" in text
        assert "\u2022" in text  # bullet
        assert "1/1" in text or "1 / 1" in text  # topic count
        assert "2026-01-05" in text and "2026-01-12" in text


# ---------------------------------------------------------------------
# crons.yml
# ---------------------------------------------------------------------
class TestCronsYaml:
    def test_two_entries(self):
        data = yaml.safe_load(Path("/app/.emergent/crons.yml").read_text())
        crons = data.get("crons") or []
        names = {c["name"]: c for c in crons}
        assert "guided-draft-nudge" in names
        assert "nudge-digest" in names
        nd = names["nudge-digest"]
        assert nd["cron"] == "0 16 * * 1"
        assert nd["enabled"] is True
        assert "{{BASE_URL}}" in nd["endpoint"]
        assert "/api/cron/nudge-digest" in nd["endpoint"]
        gdn = names["guided-draft-nudge"]
        assert gdn["cron"] == "0 15 * * 1"
        assert gdn["enabled"] is True


# ---------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------
class TestRegression:
    def test_guided_draft_nudge_cron_still_works(self):
        r = requests.post(
            f"{BASE_URL}/api/cron/guided-draft-nudge",
            headers={"Authorization": f"Bearer {CRON_SECRET}"},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json().get("enqueued") == "guided-draft-nudge"

    def test_fridge_pdf_still_works(self):
        r = requests.post(
            f"{BASE_URL}/api/portal/guided-snapshot-pdf",
            json={"topic": "foundation", "variant": "fridge",
                  "answers": [{"q": "Q", "a": "A"}], "parent_name": "Sam"},
            timeout=30,
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
        assert "-fridge" in r.headers.get("content-disposition", "")

    def test_standard_pdf_still_works(self):
        r = requests.post(
            f"{BASE_URL}/api/portal/guided-snapshot-pdf",
            json={"topic": "foundation", "answers": [{"q": "Q", "a": "A"}]},
            timeout=30,
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
