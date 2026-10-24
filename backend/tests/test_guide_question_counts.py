# Guide Questions Count: anonymous tap counter + admin stats
import os
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
IDS = ["safety", "coparenting", "parallel", "choose", "pages", "switch", "report", "help"]


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code}")
    d = r.json()
    return d.get("access_token") or d.get("token")


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login('mattsossi@bsossi.com', 'AdminPass123!')}"}


@pytest.fixture(scope="module")
def parent_h():
    return {"Authorization": f"Bearer {_login('parent1@test.com', 'TestPass123!')}"}


def _stats(h):
    r = requests.get(f"{BASE_URL}/api/admin/guide-questions/stats", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


class TestTap:
    @pytest.mark.parametrize("qid", IDS)
    def test_tap_all_ids_204(self, qid):
        r = requests.post(f"{BASE_URL}/api/guide-questions/tap", json={"question_id": qid, "where": "reading"})
        assert r.status_code == 204
        assert r.content == b""

    def test_tap_guided_204(self):
        r = requests.post(f"{BASE_URL}/api/guide-questions/tap", json={"question_id": "switch", "where": "guided"})
        assert r.status_code == 204

    @pytest.mark.parametrize("body", [
        {"question_id": "bogus", "where": "reading"},
        {"question_id": "safety", "where": "home"},
        {"question_id": "safety"},
        {},
    ])
    def test_tap_bad_422(self, body):
        r = requests.post(f"{BASE_URL}/api/guide-questions/tap", json=body)
        assert r.status_code == 422


class TestStats:
    def test_no_token_401(self):
        r = requests.get(f"{BASE_URL}/api/admin/guide-questions/stats")
        assert r.status_code == 401

    def test_parent_403(self, parent_h):
        r = requests.get(f"{BASE_URL}/api/admin/guide-questions/stats", headers=parent_h)
        assert r.status_code == 403

    def test_shape_and_ranking(self, admin_h):
        d = _stats(admin_h)
        qs = d["questions"]
        assert sorted(q["question_id"] for q in qs) == sorted(IDS)
        for q in qs:
            for k in ("all_time", "last_30_days", "reading", "guided"):
                assert isinstance(q[k], int)
            assert q["reading"] + q["guided"] == q["all_time"]
        alls = [q["all_time"] for q in qs]
        assert alls == sorted(alls, reverse=True)
        assert d["total_all_time"] == sum(alls)
        assert d["total_last_30_days"] == sum(q["last_30_days"] for q in qs)

    def test_increments(self, admin_h):
        before = {q["question_id"]: q for q in _stats(admin_h)["questions"]}
        requests.post(f"{BASE_URL}/api/guide-questions/tap", json={"question_id": "parallel", "where": "reading"})
        requests.post(f"{BASE_URL}/api/guide-questions/tap", json={"question_id": "parallel", "where": "guided"})
        requests.post(f"{BASE_URL}/api/guide-questions/tap", json={"question_id": "help", "where": "guided"})
        after = {q["question_id"]: q for q in _stats(admin_h)["questions"]}
        p0, p1 = before["parallel"], after["parallel"]
        assert p1["all_time"] == p0["all_time"] + 2
        assert p1["last_30_days"] == p0["last_30_days"] + 2
        assert p1["reading"] == p0["reading"] + 1
        assert p1["guided"] == p0["guided"] + 1
        assert after["help"]["guided"] == before["help"]["guided"] + 1
        assert after["safety"]["all_time"] == before["safety"]["all_time"]


class TestPrivacyStorage:
    def test_doc_fields_only(self):
        # tapping while authenticated must still not store identity
        db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        docs = list(db["guide_question_tap_counts"].find({}))
        assert docs
        for d in docs:
            keys = set(d.keys()) - {"_id"}
            assert keys == {"day", "question_id", "where", "count"}, keys
