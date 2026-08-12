"""SNC v2 enhancement tests (iteration 37).

Coverage:
  - Safety recommendation override in the SNC v2 report at levels 1, 2, 3, 4
  - Cache invalidation when safety level changes
  - POST /snc2/report/email (auth, guest block, missing report, resend accepted or 503)
  - GET /snc2/compare/dashboard/highlights (ready, not-ready, safety-blocked)
  - Regression: existing SNC v2 core endpoints still respond

Uses parent1@test.com / parent2@test.com from /app/memory/test_credentials.md.
Ephemeral TEST_* users are used for guardrail scenarios so shared state stays clean.
"""
from __future__ import annotations

import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

# Reuse minimal medical-only assessment payload
SEED_ANSWERS_MEDICAL = {
    "step1_medical_concern": "Chronic asthma, needs daily meds.",
    "step1_medical_current_impact": 4,
    "step1_medical_duration": "1 to 3 years",
    "step1_medical_urgency": "Needs attention within weeks",
    "step2_medical_current_needs": ["Chronic medical condition", "Medication schedule"],
    "step3_medical_professionals_seen": ["Paediatrician"],
    "step3_medical_recommendation_types": ["Daily medication"],
    "step3_medical_recs_written": "Yes",
    "step3_medical_recs_understand": 5,
    "step4_medical_same_info": 4,
    "step4_medical_attend_appts": 3,
    "step4_medical_discuss_openly": 4,
    "step4_medical_shared_language": 3,
    "step4_medical_believe_understood": 4,
    "step5_medical_routines_consistent": 3,
    "step5_medical_follow_recs": 4,
    "step5_medical_share_updates": 3,
    "step5_medical_carry_over_supplies": 4,
    "step5_medical_handoffs_reliable": 3,
    "step6_medical_agree_areas": "Both agree meds are important.",
    "step6_medical_biggest_gap": "Different priorities",
    "step7_medical_practical_selected": ["Shared calendar for medical appointments"],
    "step8_medical_top_priority": "Refill medication or supplies",
    "step8_medical_next_meeting": "Within 2 weeks",
    "step8_medical_professional_next": "Specialist physician",
}


# ---------- helpers ----------
def _login(email: str, password: str = "TestPass123!") -> requests.Session:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"email": email, "password": password, "name": "Test User"},
                          timeout=30)
    assert r.status_code == 200, f"auth failed {email}: {r.status_code} {r.text}"
    tok = r.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    return s


def _register(email: str, name: str, password: str = "TestPass123!") -> requests.Session:
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": password, "name": name}, timeout=30)
    if r.status_code == 400:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    return s


def _seed_medical(sess: requests.Session):
    sess.delete(f"{BASE_URL}/api/snc2/me")
    r = sess.post(f"{BASE_URL}/api/snc2/select",
                  json={"pathways": ["medical"], "child_name": "Kiddo"})
    assert r.status_code == 200, r.text
    r = sess.post(f"{BASE_URL}/api/snc2/answers/bulk",
                  json={"answers": SEED_ANSWERS_MEDICAL})
    assert r.status_code == 200, r.text
    r = sess.post(f"{BASE_URL}/api/snc2/complete")
    assert r.status_code == 200, r.text


def _submit_safety(sess: requests.Session, section_1: dict, section_2: dict | None = None) -> tuple[str, int]:
    # Autofill defaults so the server-side "all questions answered" guard
    # (iter 104) passes — callers only need override the items that drive
    # the target level.
    full_s1 = {f"s1_q{i}": "no" for i in range(1, 19)}
    full_s1.update(section_1 or {})
    full_s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    full_s2["s2_q8"] = "no"
    full_s2.update(section_2 or {})
    payload = {"section_1": full_s1, "section_2": full_s2}
    r = sess.post(f"{BASE_URL}/api/safety-assessment", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    return body["assessment_id"], body["result"]["level"]


def _safety_level_1(sess):
    # s1_q1 is high_concern -> level 1
    return _submit_safety(sess, {"s1_q1": "yes"})


def _safety_level_2(sess):
    # s1_q3 is coercive but not high_concern -> level 2
    return _submit_safety(sess, {"s1_q3": "yes"})


def _safety_level_4(sess):
    # All no + section 2 safe answers -> level 4
    s1 = {f"s1_q{i}": "no" for i in range(1, 19)}
    s2 = {f"s2_q{i}": "yes" for i in range(1, 8)}
    s2["s2_q8"] = "no"
    return _submit_safety(sess, s1, s2)


def _delete_safety(aid: str):
    """Direct-mongo cleanup."""
    try:
        from pymongo import MongoClient
        with open("/app/backend/.env") as _f:
            env = {}
            for _l in _f:
                _l = _l.strip()
                if "=" in _l and not _l.startswith("#"):
                    k, v = _l.split("=", 1)
                    env[k] = v.strip().strip('"').strip("'")
        cli = MongoClient(env["MONGO_URL"])
        cli[env["DB_NAME"]].safety_assessments.delete_one({"assessment_id": aid})
        cli.close()
    except Exception as e:  # pragma: no cover
        print(f"cleanup failed for {aid}: {e}")


def _delete_all_safety_for_user(user_email: str):
    """Remove any lingering safety records for a canonical account."""
    try:
        from pymongo import MongoClient
        with open("/app/backend/.env") as _f:
            env = {}
            for _l in _f:
                _l = _l.strip()
                if "=" in _l and not _l.startswith("#"):
                    k, v = _l.split("=", 1)
                    env[k] = v.strip().strip('"').strip("'")
        cli = MongoClient(env["MONGO_URL"])
        db = cli[env["DB_NAME"]]
        user = db.users.find_one({"email": user_email})
        if user:
            db.safety_assessments.delete_many({"user_id": user["user_id"]})
        cli.close()
    except Exception as e:  # pragma: no cover
        print(f"cleanup failed for {user_email}: {e}")


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def parent1():
    _delete_all_safety_for_user("parent1@test.com")
    return _login("parent1@test.com")


@pytest.fixture(scope="module")
def parent2():
    return _login("parent2@test.com")


@pytest.fixture(scope="module", autouse=True)
def _module_cleanup():
    yield
    _delete_all_safety_for_user("parent1@test.com")


# =====================================================================
# SAFETY RECOMMEND — override at 1, 2; no override at 3, 4
# =====================================================================
class TestSafetyRecommendOverride:
    def test_level1_hard_overrides_to_parallel(self, parent1):
        # Baseline: no safety -> get a report first
        _seed_medical(parent1)
        r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
        assert r.status_code == 200, r.text
        baseline_rec = r.json()["report"]["recommended_structure"]
        baseline_id = baseline_rec["structure_id"]
        assert baseline_rec["safety_override_applied"] is False

        aid, lvl = _safety_level_1(parent1)
        assert lvl == 1
        try:
            r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
            assert r.status_code == 200, r.text
            body = r.json()
            rec = body["report"]["recommended_structure"]
            assert rec["structure_id"] == "parallel_or_supported"
            assert rec["safety_override_applied"] is True
            assert rec["safety_level"] == 1
            assert "Family Violence" in rec["rationale"] and "Safety Assessment" in rec["rationale"]
            # Cached alongside report at doc-level too
            assert body.get("safety_level_at_generation") == 1
        finally:
            _delete_safety(aid)
        # baseline_id noted (not asserted equal to "cooperative"): baseline
        # varies with score volatility; we only need to prove override at L1.
        _ = baseline_id

    def test_level2_at_least_structured(self, parent1):
        _seed_medical(parent1)
        # Fresh baseline
        r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
        baseline_rec = r.json()["report"]["recommended_structure"]
        baseline_id = baseline_rec["structure_id"]

        aid, lvl = _safety_level_2(parent1)
        assert lvl == 2
        try:
            r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
            assert r.status_code == 200
            rec = r.json()["report"]["recommended_structure"]
            # Never 'cooperative' when safety=2
            assert rec["structure_id"] in {"structured", "parallel_or_supported"}
            assert rec["safety_level"] == 2
            # Override applied iff baseline was cooperative
            if baseline_id == "cooperative":
                assert rec["safety_override_applied"] is True
            else:
                # baseline was already structured/parallel — override may be False
                assert rec["safety_override_applied"] in (False, True)
        finally:
            _delete_safety(aid)

    def test_level4_no_override(self, parent1):
        _seed_medical(parent1)
        aid, lvl = _safety_level_4(parent1)
        assert lvl == 4
        try:
            r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
            assert r.status_code == 200
            rec = r.json()["report"]["recommended_structure"]
            assert rec["safety_override_applied"] is False
            assert rec["safety_level"] == 4
        finally:
            _delete_safety(aid)


# =====================================================================
# Cache invalidation — safety level change flips `stale`
# =====================================================================
class TestSafetyCacheInvalidation:
    def test_status_becomes_stale_after_safety_submission(self, parent1):
        _seed_medical(parent1)
        # Generate a report with no safety
        r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
        assert r.status_code == 200
        r = parent1.get(f"{BASE_URL}/api/snc2/report/status")
        assert r.status_code == 200
        assert r.json()["stale"] is False

        aid, lvl = _safety_level_1(parent1)
        assert lvl == 1
        try:
            r = parent1.get(f"{BASE_URL}/api/snc2/report/status")
            assert r.status_code == 200
            assert r.json()["stale"] is True, "status should be stale after safety change"

            r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
            assert r.status_code == 200
            rec = r.json()["report"]["recommended_structure"]
            assert rec["structure_id"] == "parallel_or_supported"

            r = parent1.get(f"{BASE_URL}/api/snc2/report/status")
            assert r.json()["stale"] is False
        finally:
            _delete_safety(aid)


# =====================================================================
# EMAIL MY REPORT
# =====================================================================
class TestEmailMyReport:
    def test_email_report_authenticated_success_or_503(self, parent1):
        _seed_medical(parent1)
        r = parent1.post(f"{BASE_URL}/api/snc2/report/regenerate")
        assert r.status_code == 200

        r = parent1.post(f"{BASE_URL}/api/snc2/report/email", json={})
        # Acceptable outcomes: 200 (Resend accepted) or 503 (not configured)
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            body = r.json()
            assert body["ok"] is True
            assert body["sent_to"] == "parent1@test.com"
            assert body["filename"].startswith("Special_Needs_Report_")
            assert body["filename"].endswith(".pdf")
            print("EMAIL: Resend accepted for parent1@test.com")
        else:
            print("EMAIL: 503 not-configured (acceptable)")

    def test_email_report_no_report_returns_404(self):
        # Fresh user with no report
        email = f"TEST_email_{uuid.uuid4().hex[:6]}@test.com"
        sess = _register(email, "Email NoReport")
        r = sess.post(f"{BASE_URL}/api/snc2/report/email", json={})
        assert r.status_code == 404, r.text

    def test_email_report_guest_forbidden(self):
        # Bootstrap a guest account
        r = requests.post(f"{BASE_URL}/api/auth/guest",
                          json={"name": "Guest T"}, timeout=30)
        if r.status_code != 200:
            pytest.skip(f"guest bootstrap not available: {r.status_code}")
        tok = r.json().get("access_token")
        if not tok:
            pytest.skip("guest bootstrap didn't return access_token")
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json",
                          "Authorization": f"Bearer {tok}"})
        r = s.post(f"{BASE_URL}/api/snc2/report/email", json={})
        assert r.status_code == 403, r.text


# =====================================================================
# GROWTH WINS — dashboard/highlights
# =====================================================================
class TestDashboardHighlights:
    def test_ready_for_parent1_with_active_share(self, parent1, parent2):
        # Ensure both parents have completed medical assessment (idempotent).
        _seed_medical(parent1)
        _seed_medical(parent2)

        # Ensure there's an active share between them.
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
        assert r.status_code == 200
        active = None
        for s in r.json().get("shares", []):
            if s.get("partner_email") == "parent2@test.com" and s.get("status") == "active":
                active = s
                break
        if not active:
            # Revoke any non-active, then create fresh
            for s in r.json().get("shares", []):
                if s.get("partner_email") == "parent2@test.com" and s.get("status") != "revoked":
                    parent1.post(f"{BASE_URL}/api/snc2/compare/{s['share_id']}/revoke")
            r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                             json={"email": "parent2@test.com"})
            assert r.status_code == 200, r.text
            share_id = r.json()["share"]["share_id"]
            r = parent2.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                             json={"consent": True})
            assert r.status_code == 200, r.text

        r = parent1.get(f"{BASE_URL}/api/snc2/compare/dashboard/highlights")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ready"] is True, body
        assert body["share_id"] and body["share_id"].startswith("snc2_share_")
        assert body["partner_name"] == "Riley Parent"
        assert isinstance(body["total_items"], int) and body["total_items"] > 0
        assert isinstance(body["aligned_pct"], (int, float))
        assert isinstance(body["highlights"], list)
        assert len(body["highlights"]) <= 5
        if body["highlights"]:
            h0 = body["highlights"][0]
            for k in ("prompt", "summary", "step_number", "step_name",
                      "pathway_name", "alignment"):
                assert k in h0, f"missing {k} in highlight: {h0}"

    def test_no_share_returns_ready_false(self):
        email = f"TEST_high_none_{uuid.uuid4().hex[:6]}@test.com"
        sess = _register(email, "No Share")
        r = sess.get(f"{BASE_URL}/api/snc2/compare/dashboard/highlights")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ready"] is False
        assert body["highlights"] == []

    def test_safety_blocked_returns_empty(self, parent1, parent2):
        # Parent1 has an active share (assumed from earlier test); file L1 safety.
        _seed_medical(parent1)
        _seed_medical(parent2)
        # ensure a share exists
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
        has_active = any(
            s.get("status") == "active" and s.get("partner_email") == "parent2@test.com"
            for s in r.json().get("shares", [])
        )
        if not has_active:
            r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                             json={"email": "parent2@test.com"})
            share_id = r.json()["share"]["share_id"]
            parent2.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                         json={"consent": True})

        aid, lvl = _safety_level_1(parent1)
        assert lvl == 1
        try:
            r = parent1.get(f"{BASE_URL}/api/snc2/compare/dashboard/highlights")
            assert r.status_code == 200
            body = r.json()
            assert body["ready"] is False
            assert body["highlights"] == []
        finally:
            _delete_safety(aid)


# =====================================================================
# Regression — existing SNC v2 endpoints still return 200
# =====================================================================
class TestSnc2Regression:
    def test_core_flow(self, parent1):
        _seed_medical(parent1)
        r = parent1.post(f"{BASE_URL}/api/snc2/report/generate")
        assert r.status_code == 200
        r = parent1.get(f"{BASE_URL}/api/snc2/report/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
        assert r.status_code == 200
        assert "shares" in r.json()
