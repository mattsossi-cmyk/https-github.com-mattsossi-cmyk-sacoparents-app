"""Backend API tests for Self Journey Card 1 Self-Assessment v2 (chat-style).

Covers:
- GET /api/self-assessment/me (auth required, defaults for empty)
- PUT /api/self-assessment/me (upsert, invalid keys/values dropped)
- POST /api/self-assessment/complete (422 on incomplete; appends to history; deletes draft)
- GET /api/self-assessment/history (sorted oldest->newest; per-user isolation; current_goal)
- POST /api/self-assessment/pdf (public, empty/with-history/unicode)
- scoring semantics (overall + per-section 0-100)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path("/app/frontend/.env"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from self_assessment_routes import QUESTION_KEYS, compute_scores  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CREDS1 = {"email": "parent1@test.com", "password": "TestPass123!"}
CREDS2 = {"email": "parent2@test.com", "password": "TestPass123!"}

REFLECTION_KEYS = [
    "going_better", "still_difficult", "done_differently",
    "habit_to_improve", "goal_before_next",
]


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def session1():
    return _login(CREDS1)


@pytest.fixture(scope="module")
def session2():
    return _login(CREDS2)


# ---------- Auth / GET /me ----------
class TestAuthAndGet:
    def test_get_me_unauthenticated_401(self):
        r = requests.get(f"{API}/self-assessment/me", timeout=20)
        assert r.status_code == 401

    def test_put_me_unauthenticated_401(self):
        r = requests.put(f"{API}/self-assessment/me", json={}, timeout=20)
        assert r.status_code == 401

    def test_get_me_authenticated_shape(self, session2):
        # parent2 is "brand-new" (per note) - draft should have defaults
        r = session2.get(f"{API}/self-assessment/me", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("started", "parent_name", "answers", "reflections", "goal", "updated_at"):
            assert k in d


# ---------- PUT /me validation ----------
class TestPutMe:
    def test_put_drops_invalid_keys_and_values(self, session1):
        payload = {
            "started": True,
            "parent_name": "Sam Parent",
            "answers": {
                "child_focus_1": 4,
                "self_awareness_2": 3,
                "communication_3": 9,   # out of range -> dropped
                "bogus_key": 2,         # unknown -> dropped
                "differences_1": 0,     # out of range -> dropped
            },
            "reflections": {
                "going_better": "ok",
                "not_a_key": "drop me",
            },
            "goal": "pause before replying",
        }
        r = session1.put(f"{API}/self-assessment/me", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["updated_at"]
        assert set(saved["answers"].keys()) == {"child_focus_1", "self_awareness_2"}
        assert set(saved["reflections"].keys()) == {"going_better"}
        assert saved["goal"] == "pause before replying"

    def test_get_returns_saved_draft(self, session1):
        g = session1.get(f"{API}/self-assessment/me", timeout=20)
        assert g.status_code == 200
        d = g.json()
        assert d["parent_name"] == "Sam Parent"
        assert d["answers"].get("child_focus_1") == 4


# ---------- POST /complete ----------
class TestComplete:
    def test_incomplete_returns_422(self, session2):
        r = session2.post(f"{API}/self-assessment/complete", json={
            "started": True,
            "parent_name": "Riley",
            "answers": {"child_focus_1": 3},
            "reflections": {},
            "goal": "",
        }, timeout=30)
        assert r.status_code == 422

    def test_complete_appends_and_clears_draft_and_scores(self, session2):
        # Baseline history for parent2 should be empty-ish before test
        hist0 = session2.get(f"{API}/self-assessment/history", timeout=20).json()
        before = len(hist0["entries"])

        # All 3s -> overall 60, each section 60
        answers = {k: 3 for k in QUESTION_KEYS}
        reflections = {k: f"ans-{k}" for k in REFLECTION_KEYS}
        payload = {
            "started": True,
            "parent_name": "Riley Parent",
            "answers": answers,
            "reflections": reflections,
            "goal": "TEST_goal_v2_all_threes",
        }
        # Save draft first
        session2.put(f"{API}/self-assessment/me", json=payload, timeout=30)

        r = session2.post(f"{API}/self-assessment/complete", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["scores"]["overall"] == 60
        assert entry["scores"]["sections"] == {
            "child_focus": 60, "self_awareness": 60,
            "communication": 60, "differences": 60,
        }
        assert entry["goal"] == "TEST_goal_v2_all_threes"
        assert entry["id"]
        assert entry["completed_at"]

        # Draft deleted
        d = session2.get(f"{API}/self-assessment/me", timeout=20).json()
        assert d["answers"] == {} and d["started"] is False

        # History appended
        hist = session2.get(f"{API}/self-assessment/history", timeout=20).json()
        assert len(hist["entries"]) == before + 1
        assert hist["current_goal"] == "TEST_goal_v2_all_threes"

    def test_second_complete_appends_not_replaces_all_fours(self, session2):
        before = len(session2.get(f"{API}/self-assessment/history", timeout=20).json()["entries"])
        answers = {k: 4 for k in QUESTION_KEYS}
        payload = {
            "started": True, "parent_name": "Riley Parent",
            "answers": answers, "reflections": {},
            "goal": "TEST_goal_v2_all_fours",
        }
        r = session2.post(f"{API}/self-assessment/complete", json=payload, timeout=30)
        assert r.status_code == 200
        assert r.json()["scores"]["overall"] == 80
        hist = session2.get(f"{API}/self-assessment/history", timeout=20).json()
        assert len(hist["entries"]) == before + 1
        assert hist["current_goal"] == "TEST_goal_v2_all_fours"


# ---------- GET /history ----------
class TestHistory:
    def test_unauth_401(self):
        r = requests.get(f"{API}/self-assessment/history", timeout=20)
        assert r.status_code == 401

    def test_sorted_oldest_to_newest(self, session2):
        h = session2.get(f"{API}/self-assessment/history", timeout=20).json()
        times = [e["completed_at"] for e in h["entries"]]
        assert times == sorted(times)

    def test_per_user_isolation(self, session1, session2):
        h1 = session1.get(f"{API}/self-assessment/history", timeout=20).json()
        h2 = session2.get(f"{API}/self-assessment/history", timeout=20).json()
        goals1 = {e["goal"] for e in h1["entries"]}
        goals2 = {e["goal"] for e in h2["entries"]}
        # parent2's test goals should not appear in parent1
        assert "TEST_goal_v2_all_threes" not in goals1
        assert "TEST_goal_v2_all_fours" not in goals1
        assert "TEST_goal_v2_all_threes" in goals2 or "TEST_goal_v2_all_fours" in goals2


# ---------- POST /pdf (public) ----------
class TestPdf:
    def _assert_pdf(self, resp):
        assert resp.status_code == 200, resp.text[:400]
        assert resp.headers.get("content-type", "").startswith("application/pdf")
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "SA_CoParents_Self_Assessment" in resp.headers.get("content-disposition", "")
        assert resp.content.startswith(b"%PDF")
        assert len(resp.content) > 1000

    def test_pdf_public_empty_history(self):
        body = {
            "entry": {
                "completed_at": "2026-01-15T10:00:00+00:00",
                "parent_name": "Sam Parent",
                "answers": {k: 4 for k in QUESTION_KEYS},
                "reflections": {"going_better": "pickups calmer"},
                "goal": "pause",
            },
            "history": [],
        }
        r = requests.post(f"{API}/self-assessment/pdf", json=body, timeout=60)
        self._assert_pdf(r)

    def test_pdf_with_history_and_unicode(self):
        def item(v, when):
            return {
                "completed_at": when,
                "parent_name": "Sam \u2014 Parent",
                "answers": {k: v for k in QUESTION_KEYS},
                "reflections": {"going_better": "It\u2019s going well"},
                "goal": "Shared \u2014 goals",
            }
        body = {
            "entry": item(5, "2026-07-02T10:00:00+00:00"),
            "history": [
                item(3, "2026-05-02T10:00:00+00:00"),
                item(4, "2026-06-02T10:00:00+00:00"),
                item(5, "2026-07-02T10:00:00+00:00"),
            ],
        }
        r = requests.post(f"{API}/self-assessment/pdf", json=body, timeout=60)
        self._assert_pdf(r)


# ---------- scoring semantics (local) ----------
class TestScoring:
    def test_all_threes(self):
        s = compute_scores({k: 3 for k in QUESTION_KEYS})
        assert s["overall"] == 60
        assert all(v == 60 for v in s["sections"].values())

    def test_all_fours(self):
        s = compute_scores({k: 4 for k in QUESTION_KEYS})
        assert s["overall"] == 80
        assert all(v == 80 for v in s["sections"].values())

    def test_section_isolation(self):
        answers = {k: 0 for k in QUESTION_KEYS}
        for i in range(1, 6):
            answers[f"child_focus_{i}"] = 5
        s = compute_scores({k: v for k, v in answers.items() if v})
        assert s["sections"]["child_focus"] == 100
        assert s["sections"]["self_awareness"] == 0
