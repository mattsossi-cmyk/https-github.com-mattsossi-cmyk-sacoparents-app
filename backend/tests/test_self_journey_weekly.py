"""Tests for the Weekly Self Journey Note feature (self_journey_weekly module + routes)."""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

import sys
sys.path.insert(0, "/app/backend")

import email_service  # noqa: E402
from self_journey_weekly import (  # noqa: E402
    PREFS,
    NOTES,
    build_highlights,
    collect_activity,
    make_unsubscribe_token,
    read_unsubscribe_token,
    send_weekly_notes,
)
from self_assessment_reminders import make_unsubscribe_token as reassess_unsub_token  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
WEBHOOK_CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET", "")


@pytest.fixture
def db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


# ---------- build_highlights pure unit tests ----------
class TestBuildHighlights:
    def test_full_example(self):
        today = datetime.now(timezone.utc).date()
        days = {str(today - timedelta(days=i)) for i in range(3)}
        a = {"sa": 2, "days": days, "streak": 3, "cp": 1, "cn": ["Medical", "Educational"], "fb": True}
        out = build_highlights(a)
        assert out == [
            "Completed 2 Self-Assessments",
            "Practised your personal goal on 3 days, with a 3-day streak",
            "Completed the Co-Parenting Relationship assessment",
            "Completed the Medical and Educational needs assessments",
            "Worked on your Foundation Statement",
        ]

    def test_singular_sa_and_single_day_no_streak(self):
        a = {"sa": 1, "days": {"2026-01-04"}, "streak": 1, "cp": 0, "cn": [], "fb": False}
        out = build_highlights(a)
        assert out == [
            "Completed a Self-Assessment",
            "Practised your personal goal on 1 day",
        ]

    def test_singular_cn(self):
        a = {"sa": 0, "days": set(), "streak": 0, "cp": 0, "cn": ["Medical"], "fb": False}
        assert build_highlights(a) == ["Completed the Medical needs assessment"]

    def test_empty_returns_empty(self):
        a = {"sa": 0, "days": set(), "streak": 0, "cp": 0, "cn": [], "fb": False}
        assert build_highlights(a) == []


# ---------- Token tests ----------
class TestTokens:
    def test_round_trip(self):
        uid = f"TEST_u_{uuid.uuid4().hex[:8]}"
        tok = make_unsubscribe_token(uid)
        assert read_unsubscribe_token(tok) == uid

    def test_bad_token(self):
        assert read_unsubscribe_token("not.a.token") is None

    def test_wrong_kind_rejected(self):
        """A token minted for the reassess-reminders flow must NOT work for weekly-note unsub."""
        uid = f"TEST_u_{uuid.uuid4().hex[:8]}"
        other = reassess_unsub_token(uid)
        assert read_unsubscribe_token(other) is None


# ---------- send_weekly_notes integration-ish (monkeypatched email) ----------
async def _seed_user(db, *, flagged=False, unsubscribed=False, is_guest=False, bounced=False,
                     activity=True, activity_days_ago=0):
    uid = f"TEST_u_{uuid.uuid4().hex[:8]}"
    await db.users.insert_one({
        "user_id": uid,
        "email": f"{uid}@example.com",
        "name": "Test User",
        "is_guest": is_guest,
        "email_bounced": bounced,
    })
    if flagged:
        await db.portal_state.insert_one({"user_id": uid, "safety_ack": {"flagged": True}})
    if unsubscribed:
        await db[PREFS].insert_one({"user_id": uid, "unsubscribed": True})
    if activity:
        when = datetime.now(timezone.utc) - timedelta(days=activity_days_ago)
        iso = when.isoformat()
        await db.foundation_builder.insert_one({"user_id": uid, "updated_at": iso})
        # 3 checkin days ending today
        today = datetime.now(timezone.utc).date()
        for i in range(3):
            await db.self_assessment_checkins.insert_one({
                "user_id": uid, "date": str(today - timedelta(days=i)),
            })
    return uid


async def _cleanup(db, uids):
    for coll in ("users", "portal_state", PREFS, NOTES, "foundation_builder",
                 "self_assessment_checkins", "self_assessment_history",
                 "cp_report_history", "child_needs_assessments"):
        await db[coll].delete_many({"$or": [{"user_id": {"$in": uids}}, {"_id": {"$in": uids}}]})


class TestSendWeeklyNotes:
    def test_sends_once_per_week_and_respects_filters(self, db, monkeypatch):
        calls = []

        def fake_send(**kwargs):
            calls.append(kwargs)
        monkeypatch.setattr(email_service, "send_self_journey_weekly_note", fake_send)

        async def run():
            active = await _seed_user(db)
            flagged = await _seed_user(db, flagged=True)
            unsub = await _seed_user(db, unsubscribed=True)
            guest = await _seed_user(db, is_guest=True)
            bounced = await _seed_user(db, bounced=True)
            stale_uid = await _seed_user(db, activity=False)
            # stale: foundation_builder updated 10 days ago -> should NOT count
            old_iso = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            await db.foundation_builder.insert_one({"user_id": stale_uid, "updated_at": old_iso})

            uids = [active, flagged, unsub, guest, bounced, stale_uid]

            now = datetime.now(timezone.utc)
            # Only match our seeded users via collect_activity scope (fine since they have activity)
            stats = await send_weekly_notes(db, app_url="https://app.example.com",
                                            api_url="https://api.example.com", now=now)

            # Our active test user got exactly one call
            matching = [c for c in calls if c["to_email"] == f"{active}@example.com"]
            assert len(matching) == 1, f"expected 1 call for active, got {len(matching)}: {calls}"
            c = matching[0]
            assert c["cta_url"] == "https://app.example.com/dashboard"
            assert c["unsubscribe_url"].startswith(
                "https://api.example.com/api/self-journey/weekly-note/unsubscribe?token=")
            # Highlights include foundation + practised days (fb True, days=3)
            assert "Worked on your Foundation Statement" in c["highlights"]
            assert any("Practised your personal goal on 3 days" in h for h in c["highlights"])

            # Flagged / unsub / guest / bounced should NOT be in calls
            for skip_uid in (flagged, unsub, guest, bounced):
                assert not any(k["to_email"].startswith(skip_uid) for k in calls), \
                    f"should have skipped {skip_uid}"

            # Stale (>7d) user should not be in calls either
            assert not any(k["to_email"].startswith(stale_uid) for k in calls)

            # Stats sanity (there may be other prod users; check our increments relatively)
            assert stats["sent"] >= 1
            assert stats["skipped_safety"] >= 1
            assert stats["skipped_unsubscribed"] >= 1
            assert stats["skipped_no_email"] >= 2  # guest + bounced

            # Second run same week: should NOT send to our active user again
            before = len(calls)
            stats2 = await send_weekly_notes(db, app_url="https://app.example.com",
                                             api_url="https://api.example.com", now=now)
            matching2 = [c for c in calls[before:] if c["to_email"] == f"{active}@example.com"]
            assert matching2 == []
            assert stats2["already_sent"] >= 1

            await _cleanup(db, uids)

        asyncio.get_event_loop().run_until_complete(run())


# ---------- Email template subject/content ----------
class TestEmailTemplate:
    def test_subject_html_text(self, monkeypatch):
        captured = {}

        def fake_send(*, to_email, subject, html, text, failure_message):
            captured.update(to_email=to_email, subject=subject, html=html, text=text)

        monkeypatch.setattr(email_service, "_send", fake_send)
        email_service.send_self_journey_weekly_note(
            to_email="x@example.com",
            first_name="Sam",
            highlights=["Completed a Self-Assessment", "Worked on your <Foundation> Statement"],
            cta_url="https://app.example.com/dashboard",
            unsubscribe_url="https://api.example.com/api/self-journey/weekly-note/unsubscribe?token=abc",
        )
        assert captured["subject"] == "Your weekly note"
        # HTML-escaped highlight
        assert "Worked on your &lt;Foundation&gt; Statement" in captured["html"]
        assert "Open my Self Journey" in captured["html"]
        assert "Unsubscribe" in captured["html"]
        assert "https://api.example.com/api/self-journey/weekly-note/unsubscribe?token=abc" in captured["text"]


# ---------- HTTP unsubscribe + cron auth ----------
class TestHTTP:
    def test_unsubscribe_valid(self, db):
        uid = f"TEST_u_{uuid.uuid4().hex[:8]}"
        tok = make_unsubscribe_token(uid)
        r = requests.get(f"{BASE_URL}/api/self-journey/weekly-note/unsubscribe",
                         params={"token": tok}, timeout=30)
        assert r.status_code == 200
        assert "You&#x27;re unsubscribed" in r.text or "You're unsubscribed" in r.text

        async def check():
            doc = await db[PREFS].find_one({"user_id": uid})
            assert doc and doc.get("unsubscribed") is True
            await db[PREFS].delete_many({"user_id": uid})

        asyncio.get_event_loop().run_until_complete(check())

    def test_unsubscribe_bad_token(self):
        r = requests.get(f"{BASE_URL}/api/self-journey/weekly-note/unsubscribe",
                         params={"token": "garbage"}, timeout=30)
        assert r.status_code == 400
        assert "Link not valid" in r.text

    def test_unsubscribe_wrong_kind_token(self):
        tok = reassess_unsub_token("some-uid")
        r = requests.get(f"{BASE_URL}/api/self-journey/weekly-note/unsubscribe",
                         params={"token": tok}, timeout=30)
        assert r.status_code == 400
        assert "Link not valid" in r.text

    def test_cron_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/cron/self-journey-weekly-note", timeout=30)
        assert r.status_code == 401
        r = requests.post(f"{BASE_URL}/api/cron/self-journey-weekly-note",
                          headers={"Authorization": "Bearer wrong"}, timeout=30)
        assert r.status_code == 401


# ---------- Artwork image availability ----------
class TestArtwork:
    def test_image_1024(self):
        r = requests.get(f"{BASE_URL}/images/sa-welcome.webp?v=2", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")

    def test_image_768(self):
        r = requests.get(f"{BASE_URL}/images/sa-welcome-768.webp?v=2", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")


# ---------- Crons YAML regression ----------
class TestCronsYaml:
    def test_crons_yaml(self):
        import yaml
        with open("/app/.emergent/crons.yml") as f:
            data = yaml.safe_load(f)
        crons = data["crons"]
        assert len(crons) == 5
        sj = next(c for c in crons if c["name"] == "sj-weekly-note")
        assert sj["cron"] == "0 17 * * 0"
        assert sj["timezone"] == "America/Chicago"
        assert sj["endpoint"].endswith("/api/cron/self-journey-weekly-note")
