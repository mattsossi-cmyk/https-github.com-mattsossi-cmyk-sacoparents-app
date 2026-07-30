"""End-to-end API tests for the Psychological Deep Dive routes."""
from __future__ import annotations
import os
import time
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CRED = {"email": "parent1@test.com", "password": "TestPass123!"}


def _register_or_login():
    r = requests.post(f"{API}/auth/login", json=CRED, timeout=30)
    if r.status_code == 200:
        return r.json()["access_token"]
    # try register
    requests.post(f"{API}/auth/register",
                  json={**CRED, "name": "Sam Parent"}, timeout=30)
    r = requests.post(f"{API}/auth/login", json=CRED, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


TOKEN = _register_or_login()
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _low_answers():
    return {
        "s1_diagnoses": ["ADHD", "Anxiety Disorder", "Emotional dysregulation"],
        "s2_provider_types": ["Child Psychologist"],
        "s2_both_know_provider": "Sometimes",
        "s2_attend_appointments": "Rarely",
        "s2_both_receive_updates": "Rarely",
        "s2_communicate_recs": "Sometimes",
        "s2_follow_recs_consistent": "Rarely",
        "s3_provider_understands": "Somewhat Confident",
        "s3_confidence_plan": "Neutral",
        "s3_trust_recommendations": "Somewhat Confident",
        "s3_both_confident": "Not Confident",
        "s3_discuss_respectfully": 2,
        "s4_has_medication": "Yes",
        "s4_prescriber": "Psychiatrist",
        "s4_understand_areas": ["Medication purpose"],
        "s4_administered_consistent": 2, "s4_communicate_changes": 2,
        "s4_refills_coordinated": 2, "s4_side_effects_discussed": 2,
        "s4_concerns_reported": 2,
        "s7_anxiety": "Rarely Consistent", "s7_meltdowns": "Rarely Consistent",
        "s7_transitions": "Sometimes Consistent",
        "s8_planned_areas": ["Severe anxiety"],
        "s8_know_emergency_contacts": "No", "s8_know_crisis_procedures": "No",
        "s8_plan_in_writing": "No",
        "s10_start_therapy": "Rarely Agree",
        "s10_medication": "Never Agree",
        "s10_change_therapist": "Never Agree",
        "s11_routines": "Always Consistent", "s11_emotional_support": "Always Consistent",
        "s11_calm_environment": "Always Consistent", "s11_positive_reinforcement": "Always Consistent",
        "s11_safe_expression": "Always Consistent", "s11_consistent_expectations": "Always Consistent",
        "s11_healthy_coping": "Always Consistent", "s11_stress_reduction": "Always Consistent",
    }


def test_schema():
    r = requests.get(f"{API}/psych-deep/schema", headers=H, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    secs = data["sections"]
    assert len(secs) == 11
    assert [s["number"] for s in secs] == list(range(1, 12))
    gate_map = {s["id"]: s.get("gate") for s in secs}
    assert gate_map["s4"] == {"item": "has_medication", "value": "Yes"}
    assert gate_map["s6"] == {"item": "attends_therapy", "value": "Yes"}
    for s in secs:
        for it in s["items"]:
            assert it["type"] in ("likert", "single", "multi", "textarea"), it


def test_clean_state_start():
    r = requests.delete(f"{API}/psych-deep/me", headers=H, timeout=30)
    assert r.status_code in (200, 204), r.text


def test_answer_single():
    r = requests.post(f"{API}/psych-deep/answer", headers=H,
                      json={"question_id": "s2_both_know_provider", "value": "Sometimes"}, timeout=30)
    assert r.status_code == 200, r.text


def test_bulk_and_invalid():
    ans = _low_answers()
    # inject one invalid to check rejected list
    payload = {"answers": {**ans, "s3_discuss_respectfully": "invalid_value"}}
    r = requests.post(f"{API}/psych-deep/answers/bulk", headers=H, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "s3_discuss_respectfully" in (body.get("rejected") or []), body
    # now bulk valid low answers
    r2 = requests.post(f"{API}/psych-deep/answers/bulk", headers=H,
                       json={"answers": ans}, timeout=30)
    assert r2.status_code == 200
    assert not (r2.json().get("rejected") or [])


def test_me_has_saved():
    r = requests.get(f"{API}/psych-deep/me", headers=H, timeout=30)
    assert r.status_code == 200
    data = r.json()
    a = data.get("assessment") or {}
    resp = a.get("responses") or {}
    assert "s1_diagnoses" in resp


def test_score_low_answers_flags():
    r = requests.get(f"{API}/psych-deep/score", headers=H, timeout=30)
    assert r.status_code == 200, r.text
    scored = r.json()["score"]
    by_id = {s["id"]: s for s in scored["sections"]}
    for sid in ("s1", "s2", "s3", "s4", "s8", "s10"):
        assert by_id[sid]["is_flagged"], f"{sid} not flagged"
    assert by_id["s11"]["is_strength"]
    assert not by_id["s6"]["is_visible"]


def test_report_generate():
    r = requests.post(f"{API}/psych-deep/report/generate", headers=H, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    summary = body.get("summary") or body.get("report", {}).get("summary") or {}
    report = body.get("report", body)
    flagged = summary.get("flagged_sections") or report.get("summary", {}).get("flagged_sections")
    strengths = summary.get("strength_sections") or report.get("summary", {}).get("strength_sections")
    assert (flagged or 0) >= 5, body
    assert (strengths or 0) >= 1, body


def test_report_pdf():
    r = requests.get(f"{API}/psych-deep/report/pdf", headers=H, timeout=60)
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 5000
    page_markers = r.content.count(b"/Type /Page\n") + r.content.count(b"/Type /Page ")
    assert page_markers <= 6, f"PDF too many pages: {page_markers}"


def test_gate_hides_when_none():
    # override has_medication to No & attends_therapy to No
    payload = {"answers": {**_low_answers(),
                           "s4_has_medication": "No",
                           "attends_therapy": "No"}}
    r = requests.post(f"{API}/psych-deep/answers/bulk", headers=H, json=payload, timeout=30)
    assert r.status_code == 200
    scored = requests.get(f"{API}/psych-deep/score", headers=H, timeout=30).json()["score"]
    by_id = {s["id"]: s for s in scored["sections"]}
    assert not by_id["s4"]["is_visible"]
    assert not by_id["s4"]["is_flagged"]


def test_guest_blocked_on_report_generate():
    gr = requests.post(f"{API}/auth/guest", timeout=30)
    if gr.status_code != 200:
        import pytest
        pytest.skip(f"No guest endpoint available: {gr.status_code}")
    gtoken = gr.json().get("access_token") or gr.json().get("token")
    if not gtoken:
        import pytest
        pytest.skip("No guest token returned")
    gh = {"Authorization": f"Bearer {gtoken}", "Content-Type": "application/json"}
    # Save some answers so we hit the guest-block check (not the empty-answers 400)
    requests.post(f"{API}/psych-deep/answers/bulk", headers=gh,
                  json={"answers": _low_answers()}, timeout=30)
    r = requests.post(f"{API}/psych-deep/report/generate", headers=gh, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
    # cleanup guest data
    requests.delete(f"{API}/psych-deep/me", headers=gh, timeout=30)


def test_delete_wipes_state():
    r = requests.delete(f"{API}/psych-deep/me", headers=H, timeout=30)
    assert r.status_code in (200, 204)
    r2 = requests.get(f"{API}/psych-deep/me", headers=H, timeout=30)
    assert r2.status_code == 200
    body = r2.json() or {}
    assert not body.get("has_assessment"), f"assessment not cleared: {body}"
