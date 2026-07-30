"""Unit tests for the Medical / Prescription Deep Dive."""
from __future__ import annotations

from med_deep_questions import (
    DEEP_DIVE_SECTIONS, DEEP_DIVE_VERSION, all_item_keys, item_by_key,
    public_schema, validate_answer,
)
from med_deep_report import build_deep_dive_pdf, build_deep_dive_report
from med_deep_scoring import score_deep_dive


def test_schema_has_ten_sections():
    assert len(DEEP_DIVE_SECTIONS) == 10
    numbers = [s["number"] for s in DEEP_DIVE_SECTIONS]
    assert numbers == list(range(1, 11))


def test_gates():
    gated = {s["id"]: s["gate"] for s in DEEP_DIVE_SECTIONS if s.get("gate")}
    assert gated["s8"] == {"item": "has_controlled", "value": "Yes"}
    assert gated["s9"] == {"item": "school_meds", "value": "Yes"}


def test_public_schema_json_safe():
    sch = public_schema()
    assert sch["version"] == DEEP_DIVE_VERSION
    for s in sch["sections"]:
        for it in s["items"]:
            assert it["type"] in ("likert", "single", "multi", "textarea")


def test_all_item_keys_unique():
    keys = all_item_keys()
    assert len(keys) == len(set(keys))


def test_validation():
    assert validate_answer("s2_who_picks_up", "Both")
    assert not validate_answer("s2_who_picks_up", "Sibling")
    assert validate_answer("s1_med_categories",
                           ["Daily maintenance medication", "Rescue / emergency medication (e.g., inhaler, EpiPen, glucagon)"])
    assert not validate_answer("s1_med_categories", ["Not a real category"])
    assert validate_answer("s3_supply_each_home", "Rarely")
    assert not validate_answer("bogus_key", "x")
    assert validate_answer("s1_notes", "Just some notes")
    assert item_by_key("s10_whether_to_use")["type"] == "single"


def _high_risk_answers():
    """Answers that should surface a wide set of flags and safety signals."""
    return {
        "s1_med_categories": ["Daily maintenance medication",
                              "Rescue / emergency medication (e.g., inhaler, EpiPen, glucagon)",
                              "Controlled substance (e.g., stimulant, benzodiazepine, opioid)"],
        "s1_prescriber_types": ["Paediatrician", "Psychiatrist"],
        "s1_shared_info": ["Medication name(s)"],  # only 1 of 8 -> flag
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
        "s5_new_prescriptions": "Rarely",
        "s5_dose_changes": "Rarely",
        "s5_missed_doses": "Rarely",
        "s5_side_effects": "Rarely",
        "s5_refill_needs": "Rarely",
        "s5_emergency_use": "Never",
        "s5_stopping_med": "Rarely",
        "s5_provider_visits": "Rarely",
        "s6_same_pharmacy": "No",
        "s6_both_authorized": "No",
        "s6_pharmacy_has_contacts": "No",
        "s6_pharmacist_alignment": "Rarely",
        "s6_delivery_pickup": "No",
        "s7_financial_issues": ["Insurance denied / requires prior auth",
                                "One parent refuses to pay their share"],
        "s7_cost_split_clear": "No",
        "s7_reimbursement": "Rarely",
        "s7_insurance_current": "No",
        "s7_affordability": "A major barrier",
        "s8_has_controlled": "Yes",
        "s8_controlled_type": "Stimulant (ADHD medication)",
        "s8_protections": ["Medication stored in a locked location"],  # only 1
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


def test_scoring_flags_all_10():
    scored = score_deep_dive(_high_risk_answers())
    by_id = {s["id"]: s for s in scored["sections"]}
    for sid in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"):
        assert by_id[sid]["is_flagged"], f"expected {sid} flagged"
    # Risk signals should appear on multiple sections
    risk_sections = [s for s in scored["sections"] if s["risk_signals"]]
    assert len(risk_sections) >= 4, [s["id"] for s in risk_sections]


def test_gates_hide_when_no():
    ans = _high_risk_answers()
    ans["s8_has_controlled"] = "No"
    ans["s9_school_meds"] = "No"
    scored = score_deep_dive(ans)
    by_id = {s["id"]: s for s in scored["sections"]}
    assert not by_id["s8"]["is_visible"]
    assert not by_id["s8"]["is_flagged"]
    assert not by_id["s9"]["is_visible"]
    assert not by_id["s9"]["is_flagged"]


def test_strengths_when_ideal():
    ideal = {
        "s1_med_categories": ["Daily maintenance medication"],
        "s1_prescriber_types": ["Paediatrician"],
        "s1_shared_info": ["Medication name(s)", "Dose / strength", "Purpose / condition treated",
                           "Administration schedule (times, with/without food)",
                           "Side effects to watch for", "Interactions & allergies",
                           "Prescriber name & contact", "Pharmacy name & contact"],
        "s1_written_med_list": "Yes",
        "s1_list_updated": "Always",
        "s1_both_receive_new_rx": "Always",
        "s2_who_picks_up": "Both",
        "s2_pickup_issues": ["No issues in the last 6 months"],
        "s2_pickup_delays": "Never",
        "s2_clear_assignment": "Always",
        "s2_confirmation": "Always",
        "s3_supply_each_home": "Always",
        "s3_backup_supply": "Yes",
        "s3_refill_coordination": "Always",
        "s3_runs_out_frequency": "Never",
        "s3_emergency_med_available": "Yes in both",
        "s3_expired_check": "Always",
        "s4_who_administers": "Both",
        "s4_same_schedule": "Always Consistent",
        "s4_missed_doses_freq": "Never",
        "s4_dose_log": "Yes",
        "s4_handoff_dose": "Always",
        "s4_child_involved": "Yes, appropriately",
        "s5_new_prescriptions": "Always", "s5_dose_changes": "Always",
        "s5_missed_doses": "Always", "s5_side_effects": "Always",
        "s5_refill_needs": "Always", "s5_emergency_use": "Always",
        "s5_stopping_med": "Always", "s5_provider_visits": "Always",
        "s6_same_pharmacy": "Yes always", "s6_both_authorized": "Yes",
        "s6_pharmacy_has_contacts": "Yes", "s6_pharmacist_alignment": "Always",
        "s6_delivery_pickup": "Yes",
        "s7_financial_issues": ["No financial barriers currently"],
        "s7_cost_split_clear": "Yes", "s7_reimbursement": "Always",
        "s7_insurance_current": "Yes", "s7_affordability": "Very affordable",
        "s8_has_controlled": "No", "s9_school_meds": "No",
        "s10_whether_to_use": "Always Agree", "s10_which_medication": "Always Agree",
        "s10_dosing": "Always Agree", "s10_side_effects": "Usually Agree",
        "s10_brand_vs_generic": "Always Agree", "s10_stopping_med": "Usually Agree",
        "s10_as_needed_use": "Always Agree", "s10_controlled_use": "Always Agree",
    }
    scored = score_deep_dive(ideal)
    by_id = {s["id"]: s for s in scored["sections"]}
    for sid in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s10"):
        assert by_id[sid]["is_strength"], f"{sid} not strength"


def test_no_answers_no_flags():
    scored = score_deep_dive({})
    assert scored["totals"] == {"answered": 0, "flagged": 0, "strengths": 0, "risk_sections": 0}


def test_report_only_surfaces_flagged_or_strength():
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_high_risk_answers())
    for entry in r["sections"]:
        assert entry.get("is_flagged") or entry.get("is_strength") or entry["answered"] is not None
        if entry["is_flagged"]:
            assert entry.get("challenge_text")
            assert entry.get("recommendations")
    assert (r["summary"]["risk_signals"] or [])


def test_pdf_letter_and_page_count():
    r = build_deep_dive_report(parent_name="Alex", child_name="Ari",
                               responses=_high_risk_answers())
    pdf = build_deep_dive_pdf(report=r)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 5000
    page_markers = pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ")
    assert page_markers <= 8, f"PDF has too many pages ({page_markers})"


def test_emergency_med_none_flags_risk():
    ans = {**_high_risk_answers()}
    ans["s3_emergency_med_available"] = "No"
    scored = score_deep_dive(ans)
    s3 = next(s for s in scored["sections"] if s["id"] == "s3")
    assert s3["is_flagged"]
    assert any("Rescue" in r for r in s3["risk_signals"])


def test_only_one_home_emergency_flags():
    ans = {**_high_risk_answers()}
    ans["s3_emergency_med_available"] = "Only one home"
    scored = score_deep_dive(ans)
    s3 = next(s for s in scored["sections"] if s["id"] == "s3")
    assert s3["is_flagged"]
    assert any("only one home" in r.lower() for r in s3["risk_signals"])


def test_school_authorization_missing_flags():
    ans = {**_high_risk_answers()}
    ans["s9_both_on_paperwork"] = "No"
    scored = score_deep_dive(ans)
    s9 = next(s for s in scored["sections"] if s["id"] == "s9")
    assert s9["is_flagged"]
    assert any("school medication paperwork" in r.lower() for r in s9["risk_signals"])
