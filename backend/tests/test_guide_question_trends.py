# Question Trends: weekly (last 8 weeks) list on admin guide-questions stats. Read-only (no taps written).
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
IDS = ["safety", "coparenting", "parallel", "choose", "pages", "switch", "report", "help"]
URL = f"{BASE_URL}/api/admin/guide-questions/stats"


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code}")
    d = r.json()
    return d.get("access_token") or d.get("token")


@pytest.fixture(scope="module")
def stats():
    h = {"Authorization": f"Bearer {_login('mattsossi@bsossi.com', 'AdminPass123!')}"}
    r = requests.get(URL, headers=h)
    assert r.status_code == 200, r.text
    return {q["question_id"]: q for q in r.json()["questions"]}


def test_non_admin_403():
    h = {"Authorization": f"Bearer {_login('parent1@test.com', 'TestPass123!')}"}
    assert requests.get(URL, headers=h).status_code == 403


def test_no_token_401():
    assert requests.get(URL).status_code in (401, 403)


def test_weekly_shape(stats):
    assert set(stats) == set(IDS)
    for q in stats.values():
        assert isinstance(q["weekly"], list) and len(q["weekly"]) == 8
        assert all(isinstance(v, int) and v >= 0 for v in q["weekly"])
        assert sum(q["weekly"]) <= q["all_time"]


@pytest.mark.parametrize("qid,expected", [
    ("parallel", [0, 0, 0, 0, 0, 5, 2, 3]),
    ("safety", [1, 0, 0, 0, 0, 0, 0, 4]),
    ("choose", [0, 0, 0, 0, 0, 0, 2, 0]),
    ("help", [0] * 8),
])
def test_seeded_weekly(stats, qid, expected):
    assert stats[qid]["weekly"] == expected


def test_help_all_time_7(stats):
    assert stats["help"]["all_time"] == 7


def test_weekly_matches_db_independent(stats):
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    today = datetime.now(timezone.utc).date()
    exp = {q: [0] * 8 for q in IDS}
    for d in db.guide_question_tap_counts.find({}, {"_id": 0}):
        if d.get("question_id") not in exp:
            continue
        age = (today - datetime.strptime(d["day"], "%Y-%m-%d").date()).days
        if 0 <= age < 56:
            exp[d["question_id"]][7 - age // 7] += int(d.get("count") or 0)
    for q in IDS:
        assert stats[q]["weekly"] == exp[q], q
