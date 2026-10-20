"""Iter v3 Self-Assessment regression:
- score bands rendered in PDF (overall + per-section)
- goal check-ins (POST /goal/checkin) idempotency, auth, 404, 422
- /history returns goal_practice for latest entry only
- unsubscribe HTML endpoint (valid + invalid token)
- cron endpoint auth + 200 shape
- crons.yml has sa-reassess-reminder entry and <=5 crons
"""
from __future__ import annotations

import io
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path("/app/frontend/.env"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from self_assessment_routes import QUESTION_KEYS  # noqa: E402
from self_assessment_reminders import make_unsubscribe_token  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
CREDS1 = {"email": "parent1@test.com", "password": "TestPass123!"}
CREDS2 = {"email": "parent2@test.com", "password": "TestPass123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def s1():
    return _login(CREDS1)


@pytest.fixture(scope="module")
def s2():
    return _login(CREDS2)


# ---------- PDF band rendering ----------
try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None


def _pdf_text(entry_val: int) -> str:
    body = {
        "entry": {
            "completed_at": "2026-01-15T10:00:00+00:00",
            "parent_name": "Sam Parent",
            "answers": {k: entry_val for k in QUESTION_KEYS},
            "reflections": {},
            "goal": "pause before replying",
        },
        "history": [],
    }
    r = requests.post(f"{API}/self-assessment/pdf", json=body, timeout=60)
    assert r.status_code == 200
    if PdfReader is None:
        pytest.skip("pypdf not installed")
    reader = PdfReader(io.BytesIO(r.content))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


class TestPdfBands:
    def test_band_label_growing_strength_for_all_fours_80(self):
        text = _pdf_text(4)
        assert "Growing Strength" in text, text[:1000]

    def test_band_label_consistent_strength_for_all_fives_100(self):
        text = _pdf_text(5)
        assert "Consistent Strength" in text, text[:1000]

    def test_band_label_starting_point_for_all_ones_20(self):
        text = _pdf_text(1)
        assert "Starting Point" in text, text[:1000]


# ---------- Check-ins ----------
def _get_latest_entry_id(session):
    h = session.get(f"{API}/self-assessment/history", timeout=20).json()
    assert h["entries"], "need at least one history entry"
    return h["entries"][-1]["id"]


class TestCheckins:
    def test_unauth_401(self):
        r = requests.post(
            f"{API}/self-assessment/goal/checkin",
            json={"entry_id": "x", "date": date.today().isoformat()},
            timeout=20,
        )
        assert r.status_code == 401

    def test_unknown_entry_404(self, s2):
        r = s2.post(
            f"{API}/self-assessment/goal/checkin",
            json={"entry_id": "no-such-entry", "date": date.today().isoformat()},
            timeout=20,
        )
        assert r.status_code == 404

    def test_other_user_entry_404(self, s1, s2):
        # try to check in parent2 under parent1's session
        eid = _get_latest_entry_id(s2)
        r = s1.post(
            f"{API}/self-assessment/goal/checkin",
            json={"entry_id": eid, "date": date.today().isoformat()},
            timeout=20,
        )
        assert r.status_code == 404

    def test_date_out_of_window_422(self, s2):
        eid = _get_latest_entry_id(s2)
        far = (date.today() - timedelta(days=10)).isoformat()
        r = s2.post(
            f"{API}/self-assessment/goal/checkin",
            json={"entry_id": eid, "date": far},
            timeout=20,
        )
        assert r.status_code == 422

    def test_bad_date_format_422(self, s2):
        eid = _get_latest_entry_id(s2)
        r = s2.post(
            f"{API}/self-assessment/goal/checkin",
            json={"entry_id": eid, "date": "not-a-date"},
            timeout=20,
        )
        assert r.status_code == 422

    def test_idempotent_same_day(self, s2):
        eid = _get_latest_entry_id(s2)
        today = date.today().isoformat()
        r1 = s2.post(f"{API}/self-assessment/goal/checkin",
                     json={"entry_id": eid, "date": today}, timeout=20)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        r2 = s2.post(f"{API}/self-assessment/goal/checkin",
                     json={"entry_id": eid, "date": today}, timeout=20)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d1["count"] == d2["count"]
        assert d1["entry_id"] == d2["entry_id"] == eid
        assert d2["last_date"] == today

    def test_history_returns_goal_practice_for_latest_only(self, s2):
        eid = _get_latest_entry_id(s2)
        h = s2.get(f"{API}/self-assessment/history", timeout=20).json()
        gp = h.get("goal_practice")
        assert gp is not None
        assert gp["entry_id"] == eid
        assert gp["count"] >= 1


# ---------- Unsubscribe ----------
class TestUnsubscribe:
    def test_invalid_token_400(self):
        r = requests.get(
            f"{API}/self-assessment/reminders/unsubscribe",
            params={"token": "garbage"},
            timeout=20,
        )
        assert r.status_code == 400
        assert "text/html" in r.headers.get("content-type", "")
        assert "not valid" in r.text.lower()

    def test_valid_token_200_and_upserts(self, s1):
        # need user_id of parent1
        me = s1.get(f"{API}/auth/me", timeout=20).json()
        uid = me.get("user_id") or me.get("id")
        assert uid
        tok = make_unsubscribe_token(uid)
        r = requests.get(
            f"{API}/self-assessment/reminders/unsubscribe",
            params={"token": tok}, timeout=20,
        )
        assert r.status_code == 200
        assert "unsubscribed" in r.text.lower()


# ---------- Cron auth ----------
class TestCron:
    URL = f"{API}/cron/self-assessment-reminders"

    def test_missing_bearer_401(self):
        r = requests.post(self.URL, timeout=20)
        assert r.status_code == 401

    def test_wrong_bearer_401(self):
        r = requests.post(self.URL, headers={"Authorization": "Bearer wrong-token"}, timeout=20)
        assert r.status_code == 401

    def test_valid_bearer_200(self):
        secret = os.environ.get("WEBHOOK_CRON_SECRET")
        assert secret, "WEBHOOK_CRON_SECRET missing in backend/.env"
        r = requests.post(
            self.URL,
            headers={"Authorization": f"Bearer {secret}", "X-Webhook-Id": "test-run"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert d.get("enqueued") == "self-assessment-reminders"
        assert d.get("run_id")


# ---------- crons.yml ----------
class TestCronsYaml:
    def test_sa_reassess_reminder_entry_valid(self):
        p = Path("/app/.emergent/crons.yml")
        assert p.exists()
        data = yaml.safe_load(p.read_text())
        crons = data.get("crons") or []
        assert len(crons) <= 5
        match = next((c for c in crons if c.get("name") == "sa-reassess-reminder"), None)
        assert match is not None
        assert match["cron"] == "0 9 * * *"  # 9am Central since the Oct 11 schedule change
        assert match["method"] == "POST"
        assert "/api/cron/self-assessment-reminders" in match["endpoint"]
