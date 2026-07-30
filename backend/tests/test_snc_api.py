"""End-to-end API tests for the SNC (Special Needs Co-Parenting) routes at /api/snc.

Covers Phase B/C wiring: schema, assessment save/resume, scoring, cached report
lifecycle, PDF download, reset, and Family Report removal regression.
"""
from __future__ import annotations

import pytest
import requests


# ---------------------------------------------------------------------------
# Schema (public - no auth)
# ---------------------------------------------------------------------------
class TestSchema:
    def test_schema_shape(self, base_url, api_client):
        r = api_client.get(f"{base_url}/api/snc/schema")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["assessment_version"] == "snc-2026-1"
        assert data["total_scored_items"] == 92
        assert "response_scale" in data
        assert "consistency_scale" in data
        sections = data["sections"]
        assert len(sections) == 13
        ids = [s["id"] for s in sections]
        assert ids == [f"s{i}" for i in range(1, 14)]


# ---------------------------------------------------------------------------
# Assessment lifecycle (save, resume, delete)
# ---------------------------------------------------------------------------
class TestAssessmentLifecycle:
    def test_reset_first_to_ensure_clean_state(self, base_url, auth_client):
        r = auth_client.delete(f"{base_url}/api/snc/me")
        assert r.status_code == 200, r.text

    def test_get_me_returns_exists_false_before_answers(self, base_url, auth_client):
        r = auth_client.get(f"{base_url}/api/snc/me")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["exists"] is False

    def test_post_single_answer_persists(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/answer",
                             json={"question_id": "s2_q1", "value": 5})
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        # verify persistence
        me = auth_client.get(f"{base_url}/api/snc/me").json()
        assert me["exists"] is True
        assert me["answers"]["s2_q1"] == 5

    def test_unknown_question_id_rejected(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/answer",
                             json={"question_id": "s99_qbogus", "value": 3})
        assert r.status_code == 400

    def test_invalid_likert_rejected(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/answer",
                             json={"question_id": "s2_q2", "value": 7})
        assert r.status_code == 400

    def test_bulk_save_mixed_types_with_coercion(self, base_url, auth_client):
        payload = {
            "answers": {
                "s2_q2": "4",                # numeric string -> 4
                "s3_q1": 3,                  # int likert
                "s6_medication": 5,          # consistency scale
                "s7_preferred": ["Email", "Text message"],  # multi-select
                "s1_diagnosis_status": "Diagnosis or eligibility determination received",  # single
                "s13_goals": "Consistent bedtime and shared homework routine.",  # text
            }
        }
        r = auth_client.post(f"{base_url}/api/snc/answers/bulk", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        me = auth_client.get(f"{base_url}/api/snc/me").json()
        assert me["answers"]["s2_q2"] == 4  # coerced
        assert me["answers"]["s7_preferred"] == ["Email", "Text message"]
        assert me["answers"]["s13_goals"].startswith("Consistent")

    def test_bulk_rejects_bad_likert(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/answers/bulk",
                             json={"answers": {"s2_q3": 7}})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Full-coverage save so we can generate a real report/PDF
# ---------------------------------------------------------------------------
def _full_answers():
    """Build a realistic full answer set covering all 10 scored categories."""
    a = {}
    # Likert sections (default 4)
    likert_sections = {
        "s2": 8, "s3": 9, "s4": 10, "s5": 10,
        "s7": 8, "s8": 8, "s9": 10, "s10": 7, "s12": 10,
    }
    for sid, n in likert_sections.items():
        for i in range(1, n + 1):
            a[f"{sid}_q{i}"] = 4
    # s6 uses consistency scale (2..5 valid) — pick 5
    from snc_questions import scored_items  # noqa: WPS433
    for it in scored_items("s6"):
        a[it["id"]] = 5
    # Context / intake
    a["s1_age"] = "8 years / 3rd grade"
    a["s1_strengths"] = "Curious. Kind. Loves dinosaurs."
    a["s1_joy"] = "Drawing, biking."
    a["s1_diagnosis_status"] = "Diagnosis or eligibility determination received"
    a["s1_needs"] = ["ADHD or executive functioning"]
    a["s1_needs_narrative"] = "ADHD-Combined."
    a["s11_flags"] = ["None of these apply."]
    a["s13_goals"] = "Predictable bedtime; shared homework."
    a["s13_concerns"] = "Homework meltdowns."
    a["s13_info_needed"] = "Medication dose review."
    a["s13_thirty_day"] = "Try shared parenting app."
    return a


@pytest.fixture(scope="module")
def full_saved(request):
    """Save a full answer set once for the report tests."""
    return None


# ---------------------------------------------------------------------------
# Scores endpoint
# ---------------------------------------------------------------------------
class TestScores:
    def test_scores_full_answers(self, base_url, auth_client):
        # Save a complete set first
        r = auth_client.post(f"{base_url}/api/snc/answers/bulk",
                             json={"answers": _full_answers()})
        assert r.status_code == 200, r.text
        r = auth_client.get(f"{base_url}/api/snc/scores")
        assert r.status_code == 200, r.text
        data = r.json()
        cat_ids = [c["id"] for c in data["categories"]]
        assert cat_ids == ["s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s12"]
        assert data["safety"]["level"] in {"unanswered", "clear", "declined", "concerns"}
        assert data["safety"]["level"] == "clear"
        # answered_scored_count should be 92 with full likert+consistency coverage
        assert data["answered_scored_count"] == 92


# ---------------------------------------------------------------------------
# Report lifecycle (cache, stale, regenerate)
# ---------------------------------------------------------------------------
class TestReportLifecycle:
    def test_generate_first_call_not_cached(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/report/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cached"] is False
        assert "report" in data
        assert data["report"]["cover"]["parent_name"]

    def test_generate_second_call_cached(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/report/generate")
        assert r.status_code == 200, r.text
        assert r.json()["cached"] is True

    def test_status_reports_fresh(self, base_url, auth_client):
        r = auth_client.get(f"{base_url}/api/snc/report/status")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["has_report"] is True
        assert data["stale"] is False
        assert data["generated_at"]

    def test_new_answer_marks_stale(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/answer",
                             json={"question_id": "s2_q1", "value": 3})
        assert r.status_code == 200, r.text
        status = auth_client.get(f"{base_url}/api/snc/report/status").json()
        assert status["stale"] is True

    def test_regenerate_returns_cached_false_and_clears_stale(self, base_url, auth_client):
        r = auth_client.post(f"{base_url}/api/snc/report/regenerate")
        assert r.status_code == 200, r.text
        assert r.json()["cached"] is False
        status = auth_client.get(f"{base_url}/api/snc/report/status").json()
        assert status["stale"] is False


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------
class TestReportPdf:
    def test_pdf_download(self, base_url, auth_client):
        r = auth_client.get(f"{base_url}/api/snc/report/pdf")
        assert r.status_code == 200, r.text
        ctype = r.headers.get("Content-Type", "")
        assert "application/pdf" in ctype
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 50_000, f"PDF too small: {len(r.content)} bytes"

    def test_pdf_404_after_reset(self, base_url, test_user):
        # Use a fresh user so we don't disrupt cached report for other tests
        import uuid
        suffix = uuid.uuid4().hex[:8]
        email = f"TEST_snc_pdf_{suffix}@test.com"
        reg = requests.post(f"{base_url}/api/auth/register", json={
            "email": email, "password": "TestPass123!", "name": "Fresh User",
        }, timeout=30)
        assert reg.status_code == 200, reg.text
        token = reg.json()["access_token"]
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json",
                          "Authorization": f"Bearer {token}"})
        r = s.get(f"{base_url}/api/snc/report/pdf")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /me removes assessment + report
# ---------------------------------------------------------------------------
class TestReset:
    def test_reset_deletes_everything(self, base_url, auth_client):
        r = auth_client.delete(f"{base_url}/api/snc/me")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["assessments_deleted"] >= 1
        # a cached report was built earlier, so it should also be deleted
        assert data["reports_deleted"] >= 1
        # Verify subsequent state
        me = auth_client.get(f"{base_url}/api/snc/me").json()
        assert me["exists"] is False
        status = auth_client.get(f"{base_url}/api/snc/report/status").json()
        assert status["has_assessment"] is False
        assert status["has_report"] is False


# ---------------------------------------------------------------------------
# Family Report removal regression
# ---------------------------------------------------------------------------
class TestFamilyReportRemoved:
    def test_family_report_status_404(self, base_url, auth_client):
        r = auth_client.get(f"{base_url}/api/family-report/status")
        assert r.status_code == 404

    def test_family_report_sample_pdf_404(self, base_url, api_client):
        r = api_client.get(f"{base_url}/api/insights/family-report-dynamic-sample.pdf")
        assert r.status_code == 404
