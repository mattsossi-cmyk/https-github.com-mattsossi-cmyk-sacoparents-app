"""End-to-end API tests for the Medical / Prescription Deep Dive routes."""
from __future__ import annotations
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CRED = {"email": "parent1@test.com", "password": "TestPass123!"}


def _register_or_login():
    r = requests.post(f"{API}/auth/login", json=CRED, timeout=30)
    if r.status_code == 200:
        return r.json()["access_token"]
    requests.post(f"{API}/auth/register",
                  json={**CRED, "name": "Sam Parent"}, timeout=30)
    r = requests.post(f"{API}/auth/login", json=CRED, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


TOKEN = _register_or_login()
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _high_risk_answers():
    return {
        "s1_med_categories": ["Daily maintenance medication",
                              "Rescue / emergency medication (e.g., inhaler, EpiPen, glucagon)",
                              "Controlled substance (e.g., stimulant, benzodiazepine, opioid)"],
        "s1_prescriber_types": ["Paediatrician", "Psychiatrist"],
        "s1_shared_info": ["Medication name(s)"],
        "s1_written_med_list": "No",
        "s1_list_updated": "Rarely",
        "s1_both_receive_new_rx": "Rarely",
        "s2_who_picks_up": "Mother",
        "s2_pickup_issues": ["Delay of one or more days after prescription written",
                             "Missed pick-up so a dose was skipped",
                             "Ran out before refill was picked up"],
        "s2_pickup_delays": "Usually",
        "s2_clear_assignment": "Rarely",
        "s2_confirmation": "Rarely",
        "s3_supply_each_home": "Rarely",
        "s3_backup_supply": "No",
        "s3_refill_coordination": "Rarely",
        "s3_runs_out_frequency": "More than 3 times",
        "s3_emergency_med_available": "Only one home",
        "s3_expired_check": "Rarely",
        "s4_who_administers": "Mother",
        "s4_same_schedule": "Rarely Consistent",
        "s4_missed_doses_freq": "Usually",
        "s4_dose_log": "No",
        "s4_handoff_dose": "Rarely",
        "s4_child_involved": "No",
        "s5_new_prescriptions": "Rarely", "s5_dose_changes": "Rarely",
        "s5_missed_doses": "Rarely", "s5_side_effects": "Rarely",
        "s5_refill_needs": "Rarely", "s5_emergency_use": "Never",
        "s5_stopping_med": "Rarely", "s5_provider_visits": "Rarely",
        "s6_same_pharmacy": "No", "s6_both_authorized": "No",
        "s6_pharmacy_has_contacts": "No", "s6_pharmacist_alignment": "Rarely",
        "s6_delivery_pickup": "No",
        "s7_financial_issues": ["Insurance denied / requires prior auth",
                                "One parent refuses to pay their share"],
        "s7_cost_split_clear": "No", "s7_reimbursement": "Rarely",
        "s7_insurance_current": "No", "s7_affordability": "A major barrier",
        "s8_has_controlled": "Yes",
        "s8_controlled_type": "Stimulant (ADHD medication)",
        "s8_protections": ["Medication stored in a locked location"],
        "s8_count_tracking": "No",
        "s8_diversion_concerns": "Moderate concerns",
        "s8_provider_agreement": "No",
        "s9_school_meds": "Yes",
        "s9_school_items": ["School nurse has the current prescription order"],
        "s9_both_on_paperwork": "No",
        "s9_school_updates": "Rarely",
        "s9_field_trip_ready": "No",
        "s10_whether_to_use": "Never Agree",
        "s10_which_medication": "Rarely Agree",
        "s10_dosing": "Never Agree",
        "s10_side_effects": "Rarely Agree",
        "s10_brand_vs_generic": "Sometimes Agree",
        "s10_stopping_med": "Never Agree",
        "s10_as_needed_use": "Rarely Agree",
        "s10_controlled_use": "Never Agree",
    }


def test_schema():
    r = requests.get(f"{API}/med-deep/schema", headers=H, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["version"] == "med-deep-1.0.0", data
    secs = data["sections"]
    assert len(secs) == 10
    assert [s["number"] for s in secs] == list(range(1, 11))
    gate_map = {s["id"]: s.get("gate") for s in secs}
    assert gate_map["s8"] == {"item": "has_controlled", "value": "Yes"}
    assert gate_map["s9"] == {"item": "school_meds", "value": "Yes"}
    for s in secs:
        for it in s["items"]:
            assert it["type"] in ("likert", "single", "multi", "textarea"), it


def test_clean_state_start():
    r = requests.delete(f"{API}/med-deep/me", headers=H, timeout=30)
    assert r.status_code in (200, 204), r.text
    g = requests.get(f"{API}/med-deep/me", headers=H, timeout=30)
    assert g.status_code == 200
    assert not (g.json() or {}).get("has_assessment"), g.json()


def test_answer_single_valid():
    r = requests.post(f"{API}/med-deep/answer", headers=H,
                      json={"question_id": "s2_who_picks_up", "value": "Both"}, timeout=30)
    assert r.status_code == 200, r.text


def test_answer_single_invalid():
    r = requests.post(f"{API}/med-deep/answer", headers=H,
                      json={"question_id": "s2_who_picks_up", "value": "Sibling"}, timeout=30)
    assert r.status_code == 400, r.text


def test_bulk_mixed():
    ans = _high_risk_answers()
    payload = {"answers": {**ans, "s2_who_picks_up": "Sibling"}}  # inject invalid
    r = requests.post(f"{API}/med-deep/answers/bulk", headers=H, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "s2_who_picks_up" in (body.get("rejected") or []), body
    # Now bulk valid
    r2 = requests.post(f"{API}/med-deep/answers/bulk", headers=H,
                       json={"answers": ans}, timeout=30)
    assert r2.status_code == 200
    assert not (r2.json().get("rejected") or [])


def test_me_has_saved():
    r = requests.get(f"{API}/med-deep/me", headers=H, timeout=30)
    assert r.status_code == 200
    data = r.json()
    a = data.get("assessment") or {}
    resp = a.get("responses") or {}
    assert "s1_med_categories" in resp
    assert resp.get("s8_has_controlled") == "Yes"


def test_score_flags_all_ten():
    r = requests.get(f"{API}/med-deep/score", headers=H, timeout=30)
    assert r.status_code == 200, r.text
    scored = r.json()["score"]
    by_id = {s["id"]: s for s in scored["sections"]}
    for sid in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"):
        assert by_id[sid]["is_flagged"], f"{sid} not flagged"


def test_report_generate():
    r = requests.post(f"{API}/med-deep/report/generate", headers=H, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    report = body.get("report", body)
    summary = report.get("summary", {}) or body.get("summary", {}) or {}
    flagged = summary.get("flagged_sections") or 0
    assert flagged >= 5, body
    risk_signals = summary.get("risk_signals") or []
    assert isinstance(risk_signals, list) and len(risk_signals) > 0, body


def test_report_pdf():
    r = requests.get(f"{API}/med-deep/report/pdf", headers=H, timeout=60)
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 5000
    page_markers = r.content.count(b"/Type /Page\n") + r.content.count(b"/Type /Page ")
    assert page_markers <= 8, f"PDF too many pages: {page_markers}"


def test_gates_hide_when_no():
    payload = {"answers": {**_high_risk_answers(),
                           "s8_has_controlled": "No",
                           "s9_school_meds": "No"}}
    r = requests.post(f"{API}/med-deep/answers/bulk", headers=H, json=payload, timeout=30)
    assert r.status_code == 200
    scored = requests.get(f"{API}/med-deep/score", headers=H, timeout=30).json()["score"]
    by_id = {s["id"]: s for s in scored["sections"]}
    assert not by_id["s8"]["is_visible"]
    assert not by_id["s8"]["is_flagged"]
    assert not by_id["s9"]["is_visible"]
    assert not by_id["s9"]["is_flagged"]


def test_guest_blocked_on_report_generate():
    gr = requests.post(f"{API}/auth/guest", timeout=30)
    if gr.status_code != 200:
        import pytest
        pytest.skip(f"No guest endpoint: {gr.status_code}")
    gtoken = gr.json().get("access_token") or gr.json().get("token")
    if not gtoken:
        import pytest
        pytest.skip("No guest token")
    gh = {"Authorization": f"Bearer {gtoken}", "Content-Type": "application/json"}
    requests.post(f"{API}/med-deep/answers/bulk", headers=gh,
                  json={"answers": _high_risk_answers()}, timeout=30)
    r = requests.post(f"{API}/med-deep/report/generate", headers=gh, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
    requests.delete(f"{API}/med-deep/me", headers=gh, timeout=30)


def test_regression_other_schema_endpoints_alive():
    for path in ("/psych-deep/schema", "/edu-deep/schema", "/snc2/schema"):
        r = requests.get(f"{API}{path}", headers=H, timeout=30)
        assert r.status_code == 200, f"{path} -> {r.status_code}"


def test_delete_wipes_state():
    r = requests.delete(f"{API}/med-deep/me", headers=H, timeout=30)
    assert r.status_code in (200, 204)
    r2 = requests.get(f"{API}/med-deep/me", headers=H, timeout=30)
    assert r2.status_code == 200
    assert not (r2.json() or {}).get("has_assessment")
