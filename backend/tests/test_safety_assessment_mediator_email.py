"""Tests for the new POST /api/safety-assessment/{assessment_id}/email-mediator endpoint
and the new-rule coercive-threshold scoring (single yes -> Level 2)."""
import os
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

if "REACT_APP_BACKEND_URL" not in os.environ:
    with open("/app/frontend/.env") as _f:
        for _line in _f:
            if _line.startswith("REACT_APP_BACKEND_URL="):
                os.environ["REACT_APP_BACKEND_URL"] = _line.split("=", 1)[1].strip()
                break

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _register_or_login(email: str, password: str, name: str = "Test User"):
    """Register a fresh user; if already exists, fall back to login."""
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    # Fallback to login
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def known_test_user():
    """Use the well-known parent1@test.com fixture user."""
    data = _register_or_login("parent1@test.com", "TestPass123!", "Sam Parent")
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {data['access_token']}",
    })
    return s, data["user"]


@pytest.fixture()
def guest_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/guest", json={})
    assert r.status_code == 200
    return s, r.json()["user"]


def _submit_level4(session):
    """Submit a Level-4 assessment (all safe) and return the assessment_id."""
    payload = {
        "section_1": {f"s1_q{i}": "no" for i in range(1, 11)},
        "section_2": {
            "s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
            "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
            "s2_q7": "yes", "s2_q8": "no",
        },
    }
    r = session.post(f"{BASE_URL}/api/safety-assessment", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["level"] == 4
    return body["assessment_id"]


# =======================================================
# /questions still returns expected structure (regression)
# =======================================================
class TestQuestionsStillIntact:
    def test_metadata(self):
        r = requests.get(f"{BASE_URL}/api/safety-assessment/questions", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert len(body["section_1"]) == 10
        assert len(body["section_2"]) == 8
        assert set(body["high_concern_ids"]) == {"s1_q1", "s1_q2", "s1_q4", "s1_q5", "s1_q10"}
        assert "pathways" in body and set(body["pathways"].keys()) >= {"1", "2", "3", "4"}


# =======================================================
# Scoring regression coverage of new rule + old rules
# =======================================================
class TestScoringRegressions:
    """Exercise the HTTP endpoint (not just the pure fn) to guarantee the new rule
    reaches the wire."""
    def test_single_coercive_s1_q3_yes_is_level_2(self, guest_session):
        s, _ = guest_session
        s1 = {f"s1_q{i}": "no" for i in range(1, 11)}
        s1["s1_q3"] = "yes"
        s2 = {
            "s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
            "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
            "s2_q7": "yes", "s2_q8": "no",
        }
        r = s.post(f"{BASE_URL}/api/safety-assessment",
                   json={"section_1": s1, "section_2": s2})
        assert r.status_code == 200
        result = r.json()["result"]
        assert result["level"] == 2, f"expected 2 got {result['level']}"
        assert "s1_q3" in result["coercive_hits"]

    def test_single_coercive_s1_q7_yes_is_level_2(self, guest_session):
        s, _ = guest_session
        s1 = {f"s1_q{i}": "no" for i in range(1, 11)}
        s1["s1_q7"] = "yes"
        s2 = {
            "s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
            "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
            "s2_q7": "yes", "s2_q8": "no",
        }
        r = s.post(f"{BASE_URL}/api/safety-assessment",
                   json={"section_1": s1, "section_2": s2})
        assert r.status_code == 200
        result = r.json()["result"]
        assert result["level"] == 2
        assert "s1_q7" in result["coercive_hits"]

    def test_high_concern_still_level_1(self, guest_session):
        s, _ = guest_session
        s1 = {f"s1_q{i}": "no" for i in range(1, 11)}
        s1["s1_q1"] = "yes"
        s2 = {
            "s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
            "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
            "s2_q7": "yes", "s2_q8": "no",
        }
        r = s.post(f"{BASE_URL}/api/safety-assessment",
                   json={"section_1": s1, "section_2": s2})
        assert r.status_code == 200
        assert r.json()["result"]["level"] == 1

    def test_all_safe_is_level_4(self, guest_session):
        s, _ = guest_session
        r = s.post(f"{BASE_URL}/api/safety-assessment", json={
            "section_1": {f"s1_q{i}": "no" for i in range(1, 11)},
            "section_2": {
                "s2_q1": "yes", "s2_q2": "yes", "s2_q3": "yes",
                "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
                "s2_q7": "yes", "s2_q8": "no",
            },
        })
        assert r.status_code == 200
        assert r.json()["result"]["level"] == 4

    def test_section2_three_concerns_no_section1_is_level_3(self, guest_session):
        s, _ = guest_session
        # 3 concerns in section 2, all section 1 "no"
        s2 = {"s2_q1": "no", "s2_q2": "no", "s2_q3": "no",
              "s2_q4": "yes", "s2_q5": "yes", "s2_q6": "yes",
              "s2_q7": "yes", "s2_q8": "no"}
        r = s.post(f"{BASE_URL}/api/safety-assessment", json={
            "section_1": {f"s1_q{i}": "no" for i in range(1, 11)},
            "section_2": s2,
        })
        assert r.status_code == 200
        assert r.json()["result"]["level"] == 3


# =======================================================
# New /email-mediator endpoint validation
# =======================================================
class TestEmailMediatorValidation:
    def test_invalid_email_returns_400(self, known_test_user):
        s, _ = known_test_user
        aid = _submit_level4(s)
        r = s.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/email-mediator",
            json={"mediator_email": "not-an-email"},
            timeout=20,
        )
        assert r.status_code == 400, r.text
        assert "email" in r.json().get("detail", "").lower()

    def test_missing_tld_returns_400(self, known_test_user):
        s, _ = known_test_user
        aid = _submit_level4(s)
        r = s.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/email-mediator",
            json={"mediator_email": "someone@localhost"},
            timeout=20,
        )
        assert r.status_code == 400

    def test_demo_local_returns_400(self, known_test_user):
        s, _ = known_test_user
        aid = _submit_level4(s)
        r = s.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/email-mediator",
            json={"mediator_email": "mediator@demo.local"},
            timeout=20,
        )
        assert r.status_code == 400
        assert "real email" in r.json().get("detail", "").lower()

    def test_guest_rejected_with_save_message(self, guest_session):
        s, _ = guest_session
        aid = _submit_level4(s)
        r = s.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/email-mediator",
            json={"mediator_email": "mediator@example.com"},
            timeout=20,
        )
        assert r.status_code == 400, r.text
        assert "save your work" in r.json().get("detail", "").lower()

    def test_happy_path_returns_ok_or_503(self, known_test_user):
        """Real (non-guest, non-demo) parent submits — expect 200 or 503
        (503 acceptable in preview when Resend is not configured)."""
        s, _ = known_test_user
        aid = _submit_level4(s)
        r = s.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/email-mediator",
            json={
                "mediator_email": "mediator@example.com",
                "mediator_name": "Dr. Mediator",
                "parent_message": "Please review before our session.",
            },
            timeout=45,
        )
        assert r.status_code in (200, 502, 503), r.text
        if r.status_code == 200:
            body = r.json()
            assert body.get("ok") is True
            assert body.get("emailed_to") == "mediator@example.com"
        elif r.status_code == 503:
            assert "email" in r.json().get("detail", "").lower()


# =======================================================
# Existing self-email endpoint still works (regression)
# =======================================================
class TestSelfEmailNoRegression:
    def test_self_email_returns_200_or_503_for_real_user(self, known_test_user):
        s, _ = known_test_user
        aid = _submit_level4(s)
        r = s.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/email",
            json={},
            timeout=45,
        )
        assert r.status_code in (200, 502, 503), r.text
