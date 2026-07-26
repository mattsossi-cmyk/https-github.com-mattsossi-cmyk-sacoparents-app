"""Phase D e2e — verifies /api endpoints for safeguards & disagreement pathway.

Uses live BASE_URL. Registers/logs in parent1@test.com, seeds various answer
sets via /api/neurodivergent/answers/bulk, then asserts:

 - GET /schema exposes safeguards section, scale, groups
 - POST /answers/bulk accepts safeguard ids
 - GET /scores returns pathway with tier + safeguards + disagreement + actions
 - Tier mapping across the 6 required scenarios
 - Determinism (same input → same output)
 - POST /report/generate persists pathway + report.safeguards_pathway (or skipped if LLM unavailable)
 - GET /report/pdf renders and ?excluded=safeguards_pathway produces smaller PDF
 - GET /mediation/reports/sections/sn_report includes safeguards_pathway
 - PATCH /report/visibility accepts safeguards_pathway
"""
from __future__ import annotations
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Also try reading /app/frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def token():
    assert BASE_URL, "REACT_APP_BACKEND_URL not set"
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        # Try register
        rr = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "name": "Sam Parent"},
            timeout=15,
        )
        if rr.status_code not in (200, 201):
            pytest.skip(f"Cannot auth: login={r.status_code} register={rr.status_code} body={rr.text[:200]}")
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=15,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    tok = body.get("access_token") or body.get("token")
    assert tok, body
    return tok


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


def _bulk_save(client, answers):
    r = client.post(
        f"{BASE_URL}/api/neurodivergent/answers/bulk",
        json={"answers": answers},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _clear_answers(client):
    """Overwrite existing answers with neutral values by replacing db-side
    doc via bulk-save with cleared values. Since backend uses $set with
    dotted paths, we must clear known ids to specific 'na' etc. We just
    write neutral 'na' or blank string to known ids we touch in tests."""
    # We overwrite by sending explicit neutral values for keys we set.
    pass


# --- Schema ------------------------------------------------------------------
def test_schema_exposes_safeguards(client):
    r = client.get(f"{BASE_URL}/api/neurodivergent/schema", timeout=15)
    assert r.status_code == 200, r.text
    schema = r.json()
    assert "safeguard_scale" in schema
    values = [row["value"] for row in schema["safeguard_scale"]]
    assert set(values) == {"in_place", "partial", "not_yet", "not_needed"}
    assert "safeguard_groups" in schema
    group_ids = [g["id"] for g in schema["safeguard_groups"]]
    assert set(group_ids) == {"care_team", "documents", "neutrals"}
    # safeguards section with 13 items
    section = next((s for s in schema["sections"] if s["id"] == "safeguards"), None)
    assert section is not None
    assert len(section["items"]) == 13


# --- Bulk save accepts safeguard ids ----------------------------------------
def test_bulk_save_accepts_safeguard_ids(client):
    r = client.post(
        f"{BASE_URL}/api/neurodivergent/answers/bulk",
        json={"answers": {
            "sg_pediatrician": "in_place",
            "sg_therapist": "partial",
            "sg_iep": "not_yet",
            "sg_care_plan": "not_needed",
        }},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["saved"] == 4


# --- Scores includes pathway ------------------------------------------------
def _reset_and_seed(client, answers):
    """Reset all known keys we touch to neutral, then apply answers."""
    neutral = {
        "concern_response": "review",
        # domain items to reset (from tests)
        "med_info_shared": "na",
        "med_follow_through": "na",
        "edu_records_shared": "na",
        "dev_progress_shared": "na",
        "comm_style_understood": "na",
        "reg_triggers_understood": "na",
        # safeguards
        "sg_pediatrician": "not_needed",
        "sg_therapist": "not_needed",
        "sg_iep": "not_needed",
        "sg_care_plan": "not_needed",
        "sg_mediator_pc": "not_needed",
        "sg_specialists": "not_needed",
        "sg_school_liaison": "not_needed",
        "sg_iep_coordinator": "not_needed",
        "sg_sick_day": "not_needed",
        "sg_shared_calendar": "not_needed",
        "sg_med_log": "not_needed",
        "sg_family_therapist": "not_needed",
        "sg_neutral_other": "not_needed",
    }
    _bulk_save(client, neutral)
    if answers:
        _bulk_save(client, answers)


def _get_scores(client):
    r = client.get(f"{BASE_URL}/api/neurodivergent/scores", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def test_scores_returns_pathway(client):
    _reset_and_seed(client, {})
    scores = _get_scores(client)
    assert "pathway" in scores
    p = scores["pathway"]
    for key in ("tier", "safeguards", "disagreement", "actions"):
        assert key in p, f"missing {key}"
    assert p["tier"]["id"] in ("T1", "T2", "T3", "T4")


# --- Tier mapping ----------------------------------------------------------
def test_tier_a_empty_answers_T1(client):
    _reset_and_seed(client, {})
    p = _get_scores(client)["pathway"]
    assert p["tier"]["id"] == "T1"


def test_tier_b_3_missing_safeguards_T2(client):
    _reset_and_seed(client, {
        "sg_pediatrician": "not_yet",
        "sg_therapist": "not_yet",
        "sg_iep": "not_yet",
    })
    p = _get_scores(client)["pathway"]
    assert p["tier"]["id"] == "T2", p


def test_tier_c_risky_plus_1_disagree_T3(client):
    _reset_and_seed(client, {
        "concern_response": "dismiss",
        "med_info_shared": "disagree",
    })
    p = _get_scores(client)["pathway"]
    assert p["disagreement"]["index"] == 3
    assert p["disagreement"]["risky_concern_response"] is True
    assert p["tier"]["id"] == "T3", p


def test_tier_d_5_disagrees_alone_T3(client):
    _reset_and_seed(client, {
        "med_info_shared": "disagree",
        "med_follow_through": "disagree",
        "edu_records_shared": "disagree",
        "dev_progress_shared": "disagree",
        "comm_style_understood": "disagree",
    })
    p = _get_scores(client)["pathway"]
    assert p["disagreement"]["index"] == 5
    assert p["tier"]["id"] == "T3"


def test_tier_e_6_disagrees_plus_risky_T4(client):
    _reset_and_seed(client, {
        "med_info_shared": "disagree",
        "med_follow_through": "disagree",
        "edu_records_shared": "disagree",
        "dev_progress_shared": "disagree",
        "comm_style_understood": "disagree",
        "reg_triggers_understood": "disagree",
        "concern_response": "conflict",
    })
    p = _get_scores(client)["pathway"]
    assert p["disagreement"]["index"] == 8
    assert p["tier"]["id"] == "T4"


def test_tier_f_idx5_and_missing_in_2_groups_T4(client):
    _reset_and_seed(client, {
        "med_info_shared": "disagree",
        "med_follow_through": "disagree",
        "edu_records_shared": "disagree",
        "dev_progress_shared": "disagree",
        "comm_style_understood": "disagree",
        "sg_pediatrician": "not_yet",  # care_team
        "sg_mediator_pc": "not_yet",   # neutrals
    })
    p = _get_scores(client)["pathway"]
    assert p["disagreement"]["index"] == 5
    assert p["tier"]["id"] == "T4"


# --- Determinism ----------------------------------------------------------
def test_pathway_determinism(client):
    seed = {
        "concern_response": "dismiss",
        "med_info_shared": "disagree",
        "sg_pediatrician": "in_place",
        "sg_iep": "not_yet",
    }
    _reset_and_seed(client, seed)
    p1 = _get_scores(client)["pathway"]
    p2 = _get_scores(client)["pathway"]
    assert p1["tier"]["id"] == p2["tier"]["id"]
    assert p1["disagreement"]["index"] == p2["disagreement"]["index"]
    assert p1["safeguards"]["overall_score"] == p2["safeguards"]["overall_score"]
    assert [a["title"] for a in p1["actions"]] == [a["title"] for a in p2["actions"]]


# --- Safeguards math live -------------------------------------------------
def test_safeguards_math_via_scores(client):
    _reset_and_seed(client, {
        "sg_pediatrician": "in_place",     # 100
        "sg_therapist":    "partial",      # 55
        "sg_iep":          "not_yet",      # 0
        "sg_care_plan":    "not_needed",   # excluded
    })
    sg = _get_scores(client)["pathway"]["safeguards"]
    assert sg["items_scored"] == 3
    assert sg["overall_score"] == 52  # mean(100,55,0) → 51.67 → 52


# --- Mediation sections endpoint ------------------------------------------
def test_mediation_sections_includes_safeguards_pathway(client):
    r = client.get(f"{BASE_URL}/api/mediation/reports/sections/sn_report", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    # Expect a list of section rows under some key; support both shapes.
    sections = body.get("sections") if isinstance(body, dict) else body
    keys = [s.get("key") for s in sections]
    assert "safeguards_pathway" in keys
    # Total 7 keys
    assert len(keys) >= 7


# --- Visibility PATCH accepts safeguards_pathway --------------------------
def test_visibility_accepts_safeguards_pathway(client):
    # Generate the report first (skip if AI call fails)
    r = client.post(f"{BASE_URL}/api/neurodivergent/report/generate", timeout=90)
    if r.status_code != 200:
        pytest.skip(f"report/generate failed: {r.status_code} {r.text[:200]}")
    rr = client.patch(
        f"{BASE_URL}/api/neurodivergent/report/visibility",
        json={"excluded": ["safeguards_pathway"]},
        timeout=15,
    )
    assert rr.status_code == 200, rr.text
    assert "safeguards_pathway" in rr.json().get("excluded", [])


# --- Report generate persists pathway ------------------------------------
def test_report_generate_persists_pathway(client):
    _reset_and_seed(client, {
        "concern_response": "dismiss",
        "med_info_shared": "disagree",
        "child_name": "Nina",
    })
    r = client.post(f"{BASE_URL}/api/neurodivergent/report/generate", timeout=90)
    if r.status_code != 200:
        pytest.skip(f"report/generate failed: {r.status_code} {r.text[:300]}")
    body = r.json()
    assert "pathway" in body, list(body.keys())
    assert body["pathway"]["tier"]["id"] in ("T1", "T2", "T3", "T4")
    report = body.get("report") or {}
    assert "safeguards_pathway" in report
    # Body identical? Compare tier + index at least.
    assert report["safeguards_pathway"]["tier"]["id"] == body["pathway"]["tier"]["id"]
    assert report["safeguards_pathway"]["disagreement"]["index"] == body["pathway"]["disagreement"]["index"]


# --- PDF size diff -------------------------------------------------------
def test_pdf_size_diff_with_excluded_safeguards_pathway(client):
    # Ensure a report exists.
    r = client.post(f"{BASE_URL}/api/neurodivergent/report/generate", timeout=90)
    if r.status_code != 200:
        pytest.skip(f"report/generate failed: {r.status_code} {r.text[:200]}")
    pdf_default = client.get(f"{BASE_URL}/api/neurodivergent/report/pdf", timeout=30)
    pdf_excl = client.get(
        f"{BASE_URL}/api/neurodivergent/report/pdf?excluded=safeguards_pathway",
        timeout=30,
    )
    assert pdf_default.status_code == 200, pdf_default.text[:200]
    assert pdf_excl.status_code == 200, pdf_excl.text[:200]
    assert pdf_default.content.startswith(b"%PDF-")
    assert pdf_excl.content.startswith(b"%PDF-")
    assert len(pdf_excl.content) < len(pdf_default.content), (
        f"Excluded PDF ({len(pdf_excl.content)} bytes) should be smaller than default ({len(pdf_default.content)} bytes)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
