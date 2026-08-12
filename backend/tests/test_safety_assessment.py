"""Backend tests for the SA CoParents IPV Communication Safety Assessment.

Covers:
- GET  /api/safety-assessment/questions metadata
- POST /api/safety-assessment scoring (all 4 levels) — both as a guest and
  cross-checked against the pure score_assessment() function
- GET  /api/safety-assessment/{id}/pdf returns a real PDF
- POST /api/safety-assessment/{id}/email rejects guest sessions with 400
- POST /api/safety-assessment/problem-solving + GET /problem-solving/me
"""
import os
import sys
import uuid

import pytest
import requests

# Make safety_assessment_routes importable so we can unit-test score_assessment()
sys.path.insert(0, "/app/backend")
# Load /app/backend/.env so JWT_SECRET / MONGO_URL are available at import time
try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

from safety_assessment_routes import (  # noqa: E402
    AssessmentSubmit,
    HIGH_CONCERN_IDS,
    SECTION_1_QUESTIONS,
    SECTION_2_QUESTIONS,
    score_assessment,
)

if "REACT_APP_BACKEND_URL" not in os.environ:
    try:
        with open("/app/frontend/.env") as _f:
            for _line in _f:
                if _line.startswith("REACT_APP_BACKEND_URL="):
                    os.environ["REACT_APP_BACKEND_URL"] = _line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


# A section_2 payload that answers every question with a "no-concern"
# value so the server-side "all questions answered" guard (iter 104)
# accepts the submission without shifting the scoring level. Used by
# submit / PDF / email tests where the test intent is about section_1
# behaviour, not section_2 counting.
_CLEAN_S2 = {q["id"]: ("no" if q["id"] == "s2_q8" else "yes") for q in SECTION_2_QUESTIONS}


# =======================================================
# Fixtures
# =======================================================
@pytest.fixture
def guest_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/guest", json={})
    assert r.status_code == 200, f"guest start failed: {r.status_code} {r.text}"
    return s, r.json()["user"]


@pytest.fixture(scope="session")
def real_user():
    """Register a real (non-guest) user for the email-rejection test."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_sa_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "SA Tester"},
        timeout=30,
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {data['access_token']}",
    })
    return s, data["user"], email


# =======================================================
# Pure scoring function tests
# =======================================================
class TestScoreAssessment:
    def test_all_no_is_level_4(self):
        s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
        s2 = {q["id"]: "yes" if q["id"] != "s2_q8" else "no"
              for q in SECTION_2_QUESTIONS}  # all "ready"
        result = score_assessment(AssessmentSubmit(section_1=s1, section_2=s2))
        assert result["level"] == 4
        assert result["high_concern_hits"] == []
        assert result["section_1_yes_count"] == 0

    def test_any_high_concern_yes_is_level_1(self):
        for qid in HIGH_CONCERN_IDS:
            s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
            s1[qid] = "yes"
            result = score_assessment(AssessmentSubmit(section_1=s1, section_2={}))
            assert result["level"] == 1, f"{qid}: expected level 1 got {result['level']}"
            assert qid in result["high_concern_hits"]

    def test_two_coercive_yes_is_level_2(self):
        s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
        s1["s1_q3"] = "yes"
        s1["s1_q6"] = "yes"
        result = score_assessment(AssessmentSubmit(section_1=s1, section_2={}))
        assert result["level"] == 2
        assert set(result["coercive_hits"]) == {"s1_q3", "s1_q6"}

    def test_single_coercive_yes_is_level_2(self):
        """New rule (2026-01): a single coercive-control yes escalates to Level 2."""
        for qid in ["s1_q3", "s1_q6", "s1_q7", "s1_q8", "s1_q9"]:
            s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
            s1[qid] = "yes"
            s2 = {
                "s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
                "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
                "s2_q7": "yes", "s2_q8": "no",
            }
            result = score_assessment(AssessmentSubmit(section_1=s1, section_2=s2))
            assert result["level"] == 2, f"{qid}: expected level 2 got {result['level']}"
            assert qid in result["coercive_hits"]

    def test_three_section2_concerns_is_level_3(self):
        s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
        s2 = {"s2_q1": "no", "s2_q2": "no", "s2_q3": "no"}
        result = score_assessment(AssessmentSubmit(section_1=s1, section_2=s2))
        assert result["level"] == 3
        assert result["section_2_concern_count"] == 3

    def test_high_concern_ids_metadata(self):
        assert HIGH_CONCERN_IDS == {"s1_q1", "s1_q2", "s1_q4", "s1_q5", "s1_q10"}


# =======================================================
# /questions endpoint
# =======================================================
class TestQuestionsEndpoint:
    def test_returns_correct_structure(self):
        r = requests.get(f"{BASE_URL}/api/safety-assessment/questions", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert len(body["section_1"]) == 10
        assert len(body["section_2"]) == 8
        assert sorted(body["high_concern_ids"]) == ["s1_q1", "s1_q10", "s1_q2", "s1_q4", "s1_q5"]
        assert "texas_resource_block" in body
        assert "800-799-7233" in body["texas_resource_block"]
        assert "pathways" in body and "1" in body["pathways"] and "4" in body["pathways"]


# =======================================================
# POST /api/safety-assessment scoring through HTTP as a guest
# =======================================================
class TestSubmitEndpoint:
    def test_submit_level_1(self, guest_session):
        s, _ = guest_session
        payload = {
            "section_1": {q["id"]: "no" for q in SECTION_1_QUESTIONS},
            "section_2": dict(_CLEAN_S2),
        }
        payload["section_1"]["s1_q1"] = "yes"
        r = s.post(f"{BASE_URL}/api/safety-assessment", json=payload)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["result"]["level"] == 1
        assert doc["is_guest"] is True
        assert doc["assessment_id"].startswith("sa_")
        assert "_id" not in doc  # mongo _id excluded

    def test_submit_level_2(self, guest_session):
        s, _ = guest_session
        s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
        s1.update({"s1_q3": "yes", "s1_q6": "yes", "s1_q7": "yes", "s1_q8": "yes"})
        r = s.post(f"{BASE_URL}/api/safety-assessment",
                   json={"section_1": s1, "section_2": dict(_CLEAN_S2)})
        assert r.status_code == 200
        assert r.json()["result"]["level"] == 2

    def test_submit_level_4(self, guest_session):
        s, _ = guest_session
        payload = {
            "section_1": {q["id"]: "no" for q in SECTION_1_QUESTIONS},
            "section_2": {"s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
                          "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
                          "s2_q7": "yes", "s2_q8": "no"},
        }
        r = s.post(f"{BASE_URL}/api/safety-assessment", json=payload)
        assert r.status_code == 200
        assert r.json()["result"]["level"] == 4

    def test_get_me_returns_latest(self, guest_session):
        s, _ = guest_session
        # one submit
        s1 = {q["id"]: "no" for q in SECTION_1_QUESTIONS}
        r = s.post(f"{BASE_URL}/api/safety-assessment",
                   json={"section_1": s1, "section_2": dict(_CLEAN_S2)})
        assert r.status_code == 200
        latest_id = r.json()["assessment_id"]
        me = s.get(f"{BASE_URL}/api/safety-assessment/me")
        assert me.status_code == 200
        assert me.json()["assessment_id"] == latest_id


# =======================================================
# PDF endpoint
# =======================================================
class TestPdfEndpoint:
    def test_pdf_download(self, guest_session):
        s, _ = guest_session
        payload = {
            "section_1": {q["id"]: "no" for q in SECTION_1_QUESTIONS},
            "section_2": dict(_CLEAN_S2),
        }
        payload["section_1"]["s1_q1"] = "yes"  # level 1
        sub = s.post(f"{BASE_URL}/api/safety-assessment", json=payload).json()
        aid = sub["assessment_id"]

        r = s.get(f"{BASE_URL}/api/safety-assessment/{aid}/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF"), "Response is not a PDF"
        assert len(r.content) > 1000  # not empty

    def test_pdf_404_for_unknown(self, guest_session):
        s, _ = guest_session
        r = s.get(f"{BASE_URL}/api/safety-assessment/sa_doesnotexist/pdf")
        assert r.status_code == 404


# =======================================================
# Email endpoint
# =======================================================
class TestEmailEndpoint:
    def test_email_rejected_for_guest(self, guest_session):
        s, _ = guest_session
        payload = {
            "section_1": {q["id"]: "no" for q in SECTION_1_QUESTIONS},
            "section_2": dict(_CLEAN_S2),
        }
        sub = s.post(f"{BASE_URL}/api/safety-assessment", json=payload).json()
        aid = sub["assessment_id"]
        r = s.post(f"{BASE_URL}/api/safety-assessment/{aid}/email", json={})
        assert r.status_code == 400, r.text
        assert "Save your work" in r.json().get("detail", "")

    def test_email_path_for_real_user(self, real_user):
        """The real-user path should NOT be the guest-rejection 400. It will
        either return 200 (Resend configured) or 503 (Email not configured in
        preview). Either is acceptable — what we're guarding against is a
        regression where the guest check leaks to real users."""
        s, _user, _email = real_user
        payload = {
            "section_1": {q["id"]: "no" for q in SECTION_1_QUESTIONS},
            "section_2": dict(_CLEAN_S2),
        }
        sub = s.post(f"{BASE_URL}/api/safety-assessment", json=payload).json()
        aid = sub["assessment_id"]
        r = s.post(f"{BASE_URL}/api/safety-assessment/{aid}/email", json={})
        assert r.status_code in (200, 502, 503), f"unexpected {r.status_code} {r.text}"
        if r.status_code == 200:
            assert r.json().get("ok") is True


# =======================================================
# Problem-Solving Worksheet
# =======================================================
class TestProblemSolvingWorksheet:
    def test_save_and_list(self, guest_session):
        s, _ = guest_session
        payload = {
            "parenting_issue": "TEST_handover times",
            "child_need": "TEST_consistency",
            "my_concern": "TEST_late drop-offs",
            "best_option": "TEST_neutral location",
        }
        r = s.post(f"{BASE_URL}/api/safety-assessment/problem-solving", json=payload)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["worksheet_id"].startswith("ps_")
        assert doc["parenting_issue"] == "TEST_handover times"
        assert "_id" not in doc

        listing = s.get(f"{BASE_URL}/api/safety-assessment/problem-solving/me")
        assert listing.status_code == 200
        rows = listing.json()
        assert any(r_["worksheet_id"] == doc["worksheet_id"] for r_ in rows)
        assert len(rows) <= 20
