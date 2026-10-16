"""Admin weekly Consent Trend: admin only, weekly totals only, weeks under 5 sign-ups carry no numbers."""
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from analytics_routes import TREND_WEEKS, _trend_rows, _trend_week_starts  # noqa: E402

API = "http://localhost:8001/api"
URL = f"{API}/analytics/admin/consent-trend"
ADMIN = {"email": "mattsossi@bsossi.com", "password": "AdminPass123!"}
NUMBERS = {"signups", "privacy_notice_accepted", "sensitive_info_consent", "needs_reconsent"}
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
_emails = []


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    ids = [u["user_id"] for u in db.users.find({"email": {"$in": _emails}}, {"user_id": 1})]
    db.users.delete_many({"email": {"$in": _emails}})
    db.portal_court_keys.delete_many({"created_by": {"$in": ids}})
    for coll in ("privacy_consents", "legal_acknowledgments"):
        db[coll].delete_many({"user_id": {"$in": ids}})


def _token(email, password):
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _new_user(tag):
    email = f"test_trend_{tag}_{uuid.uuid4().hex[:8]}@example.com"
    _emails.append(email)
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": f"Trend {tag}",
                                                "ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=20)
    assert r.status_code == 200, r.text
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


def test_signed_out_refused():
    assert httpx.get(URL, timeout=20).status_code == 401


def test_parent_refused():
    _, h, _ = _new_user("parent")
    r = httpx.get(URL, headers=h, timeout=20)
    assert r.status_code == 403 and "signups" not in r.text


def test_professional_refused():
    _, h, user = _new_user("pro")
    db.portal_court_keys.insert_one({"key": f"TEST-{uuid.uuid4().hex[:6]}", "created_by": user["user_id"], "test_fixture": True})
    r = httpx.get(URL, headers=h, timeout=20)
    assert r.status_code == 403 and "signups" not in r.text


def test_small_weeks_suppressed_unit():
    starts = _trend_week_starts(datetime(2026, 10, 15, 9, tzinfo=timezone.utc))
    assert len(starts) == TREND_WEEKS and all(s.weekday() == 0 and s.hour == 0 for s in starts)
    assert starts[-1].date().isoformat() == "2026-10-12"
    buckets = {
        starts[0].date(): {"signups": 4, "accepted": 4, "sensitive": 4, "current": 4},
        starts[1].date(): {"signups": 5, "accepted": 3, "sensitive": 2, "current": 2},
        starts[2].date(): {"signups": 1, "accepted": 0, "sensitive": 0, "current": 0},
    }
    rows = _trend_rows(starts, buckets)
    assert rows[0] == {"week_start": starts[0].date().isoformat(), "fewer_than_5": True}
    assert rows[2] == {"week_start": starts[2].date().isoformat(), "fewer_than_5": True}
    assert rows[3] == {"week_start": starts[3].date().isoformat(), "fewer_than_5": True}  # 0 sign-ups
    assert rows[1] == {"week_start": starts[1].date().isoformat(), "fewer_than_5": False, "signups": 5,
                       "privacy_notice_accepted": 3, "sensitive_info_consent": 2, "needs_reconsent": 3}


def test_admin_gets_weekly_totals_only():
    email, _, user = _new_user("shape")
    r = httpx.get(URL, headers=_token(**ADMIN), timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"current_version", "weeks"}
    weeks = body["weeks"]
    assert len(weeks) == TREND_WEEKS
    assert [w["week_start"] for w in weeks] == sorted(w["week_start"] for w in weeks)
    for w in weeks:
        assert datetime.fromisoformat(w["week_start"]).weekday() == 0
        if w["fewer_than_5"]:
            assert set(w) == {"week_start", "fewer_than_5"}
        else:
            assert set(w) == {"week_start", "fewer_than_5"} | NUMBERS
            assert w["signups"] >= 5 and all(isinstance(w[k], int) and 0 <= w[k] <= w["signups"] for k in NUMBERS)
    # No per-user data: the fresh account's email, name and id never appear.
    text = json.dumps(body)
    for needle in (email, user["user_id"], user["name"], "@", "user_id", "email", "name"):
        assert needle not in text, needle


def test_demo_sessions_not_counted():
    r = httpx.get(URL, headers=_token(**ADMIN), timeout=20).json()
    before = r["weeks"][-1]
    guests = []
    for _ in range(6):
        g = httpx.post(f"{API}/auth/guest", json={}, timeout=20)
        assert g.status_code == 200
        guests.append(g.json()["user"]["user_id"])
    try:
        after = httpx.get(URL, headers=_token(**ADMIN), timeout=20).json()["weeks"][-1]
        assert after == before
    finally:
        db.users.delete_many({"user_id": {"$in": guests}})


def _db_week(start, end):
    """The same totals, counted straight from the database for one week."""
    from privacy_consent import PRIVACY_NOTICE_VERSION as v
    q = {"is_guest": {"$ne": True}, "created_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}}
    cur = {"privacy_notice_version": v}
    n = db.users.count_documents(q)
    a = db.users.count_documents({**q, **cur, "ack_privacy_notice": True})
    s = db.users.count_documents({**q, **cur, "consent_sensitive_info": True})
    c = db.users.count_documents({**q, **cur, "ack_privacy_notice": True, "consent_sensitive_info": True})
    return n, a, s, c


def test_week_bucketing_end_to_end():
    """Six accounts added to the oldest week change its totals by exactly their own numbers."""
    from privacy_consent import PRIVACY_NOTICE_VERSION as v
    starts = _trend_week_starts(datetime.now(timezone.utc))
    wk, end = starts[0], starts[0] + timedelta(weeks=1)
    n0, a0, s0, c0 = _db_week(wk, end)
    tag = uuid.uuid4().hex[:8]
    for i in range(6):
        e = f"test_trend_bucket_{tag}_{i}@example.com"
        _emails.append(e)
        consent = {"ack_privacy_notice": True, "consent_sensitive_info": True, "privacy_notice_version": v} if i < 4 else {}
        db.users.insert_one({"user_id": f"test_trend_{tag}_{i}", "email": e, "name": "Bucket", "is_guest": False,
                             "created_at": (wk + timedelta(days=1, hours=i)).isoformat(), **consent})
    n, a, s, c = _db_week(wk, end)
    assert (n, a, s, c) == (n0 + 6, a0 + 4, s0 + 4, c0 + 4)
    row = httpx.get(URL, headers=_token(**ADMIN), timeout=20).json()["weeks"][0]
    assert row == {"week_start": wk.date().isoformat(), "fewer_than_5": False, "signups": n,
                   "privacy_notice_accepted": a, "sensitive_info_consent": s, "needs_reconsent": n - c}
