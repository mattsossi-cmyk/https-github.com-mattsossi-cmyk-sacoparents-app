"""Live E2E tests for edu-deep against the public REACT_APP_BACKEND_URL."""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": EMAIL, "password": PASSWORD, "name": "Sam Parent"}, timeout=30)
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


def test_schema(h):
    r = requests.get(f"{BASE_URL}/api/edu-deep/schema", headers=h, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    sections = data["sections"]
    assert len(sections) == 12
    ids = [s["id"] for s in sections]
    assert ids == [f"s{i}" for i in range(1, 13)]
    s3 = next(s for s in sections if s["id"] == "s3")
    assert s3.get("texas_only") is True
    gates = {s["id"]: s.get("gate") for s in sections}
    assert gates["s4"] and gates["s4"]["item"] == "has_iep" and gates["s4"]["value"] == "Yes"
    assert gates["s5"] and gates["s5"]["item"] == "has_504" and gates["s5"]["value"] == "Yes"
    assert gates["s6"] and gates["s6"]["item"] == "meets_counselor" and gates["s6"]["value"] == "Yes"
    valid_types = {"likert", "single", "multi", "textarea", "text"}
    for s in sections:
        for it in s["items"]:
            assert it["id"] and it["type"] in valid_types


def test_wipe_and_persistence(h):
    requests.delete(f"{BASE_URL}/api/edu-deep/me", headers=h, timeout=30)
    r = requests.post(f"{BASE_URL}/api/edu-deep/answer", headers=h,
                      json={"question_id": "s1_school_state", "value": "TX"}, timeout=30)
    assert r.status_code == 200, r.text
    r = requests.post(f"{BASE_URL}/api/edu-deep/answers/bulk", headers=h,
                      json={"answers": {
                          "s2_discuss_goals": 4,
                          "s2_communicate_after": 4,
                      }}, timeout=30)
    assert r.status_code == 200, r.text
    r = requests.get(f"{BASE_URL}/api/edu-deep/me", headers=h, timeout=30)
    assert r.status_code == 200
    assess = r.json().get("assessment") or {}
    responses = assess.get("responses") or {}
    assert responses.get("s1_school_state") == "TX"
    assert responses.get("s2_discuss_goals") == 4


def test_invalid_values_rejected(h):
    r = requests.post(f"{BASE_URL}/api/edu-deep/answer", headers=h,
                      json={"question_id": "s2_discuss_goals", "value": 9}, timeout=30)
    assert r.status_code == 400
    r = requests.post(f"{BASE_URL}/api/edu-deep/answer", headers=h,
                      json={"question_id": "s4_has_iep", "value": "Bogus"}, timeout=30)
    assert r.status_code == 400


def _fill(h, state="TX", has_iep="Yes"):
    requests.delete(f"{BASE_URL}/api/edu-deep/me", headers=h, timeout=30)
    # Get valid s1_concerns options from schema first
    concerns_pool = ["Reading", "Writing", "Math", "Attention",
                     "Executive Functioning", "Behaviour"]
    answers = {
        "s1_school_setting": "Public School",
        "s1_grade_level": "3rd",
        "s1_school_state": state,
        "s1_concerns": concerns_pool,
        # s2 low
        "s2_communicate_after": "Never",
        "s2_discuss_goals": 2,
        "s2_how_often_attend": "Rarely",
        "s2_both_can_attend": "Rarely",
        "s2_both_receive_updates": "No",
        # s3 ARD Texas — low likerts + conflict_interferes=4
        "s3_conflict_interferes": 4,
        "s3_review_plan_before": 2,
        "s3_comfort_participating": 2,
        "s3_prepare_questions": 2,
        "s3_decisions_focus_child": 2,
        # s4 IEP flagged
        "s4_has_iep": has_iep,
        "s4_familiar_with_goals": 2,
        "s4_both_homes_support": 2,
        "s4_monitor_progress": 2,
        "s4_accommodations_consistent": 2,
        # s8 strength
        "s8_homework_consistent": 5,
        "s8_quiet_study_spaces": 5,
        "s8_assignments_completed": 5,
        "s8_communicate_missing_work": 5,
        "s8_child_encouraged": 5,
        "s8_technology_available": 5,
        # s10 3+ Rarely/Never Agree topics
        "s10_school_choice": "Rarely Agree",
        "s10_special_ed_placement": "Never Agree",
        "s10_testing": "Rarely Agree",
        "s10_tutoring": "Sometimes Agree",
    }
    r = requests.post(f"{BASE_URL}/api/edu-deep/answers/bulk", headers=h,
                      json={"answers": answers}, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def test_scoring_tx_flags(h):
    resp = _fill(h)
    assert resp.get("rejected") == [], resp
    r = requests.get(f"{BASE_URL}/api/edu-deep/score", headers=h, timeout=30)
    assert r.status_code == 200, r.text
    score = r.json()["score"]
    by_id = {s["id"]: s for s in score["sections"]}
    for sid in ["s1", "s2", "s3", "s4", "s10"]:
        assert by_id[sid].get("is_flagged"), f"{sid} should be flagged: {by_id[sid]}"
    assert by_id["s8"].get("is_strength"), by_id["s8"]
    for sid in ["s5", "s6"]:
        assert by_id[sid].get("is_visible") is False, by_id[sid]
    # s7 has no gate: it stays visible but is unanswered
    assert by_id["s7"].get("answered") is False


def test_scoring_non_tx_hides_ard(h):
    _fill(h)
    r = requests.post(f"{BASE_URL}/api/edu-deep/answer", headers=h,
                      json={"question_id": "s1_school_state", "value": "CA"}, timeout=30)
    assert r.status_code == 200
    r = requests.get(f"{BASE_URL}/api/edu-deep/score", headers=h, timeout=30)
    by_id = {s["id"]: s for s in r.json()["score"]["sections"]}
    assert by_id["s3"].get("is_visible") is False
    assert by_id["s3"].get("is_flagged") is False


def test_gate_hides_iep(h):
    _fill(h, has_iep="No")
    r = requests.get(f"{BASE_URL}/api/edu-deep/score", headers=h, timeout=30)
    by_id = {s["id"]: s for s in r.json()["score"]["sections"]}
    assert by_id["s4"].get("is_visible") is False


def test_report_generate_and_pdf(h):
    _fill(h)
    r = requests.post(f"{BASE_URL}/api/edu-deep/report/generate", headers=h, timeout=60)
    assert r.status_code == 200, r.text
    rep = r.json()
    summary = rep["report"]["summary"]
    for k in ("flagged_sections", "strength_sections", "flagged_names", "strength_names"):
        assert k in summary, summary
    assert len(summary["flagged_names"]) >= 4, summary
    assert len(summary["strength_names"]) >= 1, summary
    sec_ids = [s["id"] for s in rep["report"]["sections"]]
    for gated in ("s5", "s6", "s7"):
        assert gated not in sec_ids, f"{gated} should not be in report (not visible/answered)"
    r = requests.get(f"{BASE_URL}/api/edu-deep/report/pdf", headers=h, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 5000


def test_guest_blocked():
    r = requests.post(f"{BASE_URL}/api/edu-deep/report/generate", timeout=30)
    # No auth token → 401 or 403 depending on auth setup; both are "blocked"
    assert r.status_code in (401, 403), r.status_code


def test_cleanup(h):
    r = requests.delete(f"{BASE_URL}/api/edu-deep/me", headers=h, timeout=30)
    assert r.status_code == 200
