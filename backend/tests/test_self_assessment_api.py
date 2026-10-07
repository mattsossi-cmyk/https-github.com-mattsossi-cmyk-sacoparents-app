"""Backend API tests for Self Journey Card 1 Self-Assessment feature.

Covers:
 - GET /api/self-assessment/me (auth + empty defaults)
 - PUT /api/self-assessment/me (upsert, invalid-key/value drop, per-user isolation, GET persistence)
 - POST /api/self-assessment/pdf (public, filename, empty/partial/full+unicode, scoring guardrail)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path("/app/frontend/.env"))

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CREDS1 = {"email": "parent1@test.com", "password": "TestPass123!"}
CREDS2 = {"email": "parent2@test.com", "password": "TestPass123!"}

CONTENT = json.loads(
    (Path(__file__).parent.parent / "self_assessment_content.json").read_text(encoding="utf-8")
)
QUESTION_KEYS = [
    f"{s['key']}{i + 1}" for s in CONTENT["sections"] for i in range(len(s["questions"]))
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

    def test_get_me_authenticated(self, session1):
        r = session1.get(f"{API}/self-assessment/me", timeout=20)
        assert r.status_code == 200
        data = r.json()
        for k in ("meta", "answers", "foundation", "updated_at"):
            assert k in data


# ---------- PUT /me upsert + validation ----------
class TestPutMe:
    def test_put_valid_and_invalid_keys_dropped(self, session1):
        payload = {
            "meta": {"parent_name": "Sam Parent", "date": "2026-01-15", "child": "Kid", "case_ref": "REF-1"},
            "answers": {"A1": 4, "A2": 3, "B1": 3, "Z1": 2, "A1x": 1, "B1_bad": 1},
            "foundation": {"going_well": ["one", "", ""], "improve": ["", "", ""], "shared_goals": "goals"},
        }
        r = session1.put(f"{API}/self-assessment/me", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["updated_at"], "updated_at ISO should be set"
        assert set(saved["answers"].keys()) == {"A1", "A2", "B1"}
        assert saved["meta"]["parent_name"] == "Sam Parent"

    def test_put_out_of_scale_values_dropped(self, session1):
        payload = {"meta": {}, "answers": {"B1": 9, "B2": 0, "B3": 2, "B4": -1}, "foundation": {}}
        r = session1.put(f"{API}/self-assessment/me", json=payload, timeout=30)
        assert r.status_code == 200
        assert set(r.json()["answers"].keys()) == {"B3"}

    def test_get_returns_saved_data(self, session1):
        # Save then GET
        payload = {
            "meta": {"parent_name": "Sam Parent", "date": "2026-01-16", "child": "", "case_ref": ""},
            "answers": {"A1": 4, "A2": 3, "C1": 2},
            "foundation": {"going_well": ["", "", ""], "improve": ["", "", ""], "shared_goals": ""},
        }
        p = session1.put(f"{API}/self-assessment/me", json=payload, timeout=30)
        assert p.status_code == 200
        g = session1.get(f"{API}/self-assessment/me", timeout=20)
        assert g.status_code == 200
        d = g.json()
        assert d["answers"] == {"A1": 4, "A2": 3, "C1": 2}
        assert d["meta"]["parent_name"] == "Sam Parent"
        assert d["updated_at"]

    def test_per_user_isolation(self, session1, session2):
        session1.put(f"{API}/self-assessment/me", json={
            "meta": {"parent_name": "Sam Parent"}, "answers": {"A1": 4}, "foundation": {}
        }, timeout=30)
        session2.put(f"{API}/self-assessment/me", json={
            "meta": {"parent_name": "Riley Parent"}, "answers": {"F1": 2}, "foundation": {}
        }, timeout=30)
        d1 = session1.get(f"{API}/self-assessment/me", timeout=20).json()
        d2 = session2.get(f"{API}/self-assessment/me", timeout=20).json()
        assert d1["meta"]["parent_name"] == "Sam Parent"
        assert d2["meta"]["parent_name"] == "Riley Parent"
        assert "A1" in d1["answers"] and "A1" not in d2["answers"]
        assert "F1" in d2["answers"] and "F1" not in d1["answers"]


# ---------- POST /pdf ----------
class TestPdf:
    def _assert_pdf(self, resp, name_token):
        assert resp.status_code == 200, resp.text[:300]
        assert resp.headers.get("content-type", "").startswith("application/pdf")
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd and "SA_CoParents_Self_Assessment_" in cd
        assert name_token in cd
        assert resp.content.startswith(b"%PDF"), "body should be a PDF"
        assert len(resp.content) > 1000

    def test_pdf_public_no_auth_empty(self):
        r = requests.post(f"{API}/self-assessment/pdf", json={}, timeout=60)
        self._assert_pdf(r, "me")  # safe filename fallback

    def test_pdf_partial_answers(self):
        body = {
            "meta": {"parent_name": "Sam Parent"},
            "answers": {"A1": 4, "A2": 3, "B1": 3},
            "foundation": {},
        }
        r = requests.post(f"{API}/self-assessment/pdf", json=body, timeout=60)
        self._assert_pdf(r, "Sam_Parent")

    def test_pdf_full_answers_with_unicode(self):
        answers = {k: 4 for k in QUESTION_KEYS}
        body = {
            "meta": {
                "parent_name": "Sam \u2014 Parent",  # em dash
                "date": "2026\u201301\u201315",
                "child": "\u201cKid\u201d",  # smart quotes
                "case_ref": "ref \u2013 1",
            },
            "answers": answers,
            "foundation": {
                "going_well": ["It\u2019s going well", "", ""],
                "improve": ["", "", ""],
                "shared_goals": "Shared \u2014 goals",
            },
        }
        r = requests.post(f"{API}/self-assessment/pdf", json=body, timeout=60)
        self._assert_pdf(r, "Sam")
        # 30 answers * 4 = 120 → tier[0] "Strong"


# ---------- scoring guardrail (via local import) ----------
class TestScoringGuardrail:
    def test_partial_no_tier(self):
        from self_assessment_routes import compute_scores
        s = compute_scores({"A1": 4, "A2": 3})
        assert s["tier"] is None
        assert s["answered"] == 2
        assert s["question_count"] == 30

    def test_all_answered_shows_tier(self):
        from self_assessment_routes import compute_scores
        s = compute_scores({k: 4 for k in QUESTION_KEYS})
        assert s["tier"] is not None
        assert s["total"] == 120
        assert s["tier"]["min"] == 96  # Strong tier
