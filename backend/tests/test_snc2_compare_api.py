"""Integration tests for SNC v2 Co-Parent Comparison API.

Covers /api/snc2/compare/* endpoints:
  - link creation (happy path, own-email, unknown partner, dedup)
  - consent -> active
  - safety guardrails at link / consent / view stages
  - comparison payload structure + category filter
  - PDF endpoint
  - revoke + consent withdrawal -> 409

Note: uses parent1@test.com + parent2@test.com from /app/memory/test_credentials.md
for stable happy-path flow (their assessments may already exist). Uses freshly-
registered users to exercise error/guardrail paths so we don't corrupt shared state.
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


def _register(email: str, name: str, password: str = "TestPass123!") -> requests.Session:
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=30,
    )
    if r.status_code == 400:
        # Already exists -> login
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
    assert r.status_code == 200, f"auth failed for {email}: {r.status_code} {r.text}"
    tok = r.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    return s


def _seed_assessment(sess: requests.Session, pathways=("medical",)):
    sess.delete(f"{BASE_URL}/api/snc2/me")
    r = sess.post(f"{BASE_URL}/api/snc2/select",
                  json={"pathways": list(pathways), "child_name": "Kiddo"})
    assert r.status_code == 200, r.text
    r = sess.post(f"{BASE_URL}/api/snc2/answers/bulk",
                  json={"answers": SEED_ANSWERS_MEDICAL})
    assert r.status_code == 200, r.text
    r = sess.post(f"{BASE_URL}/api/snc2/complete")
    assert r.status_code == 200, r.text


def _submit_safety_level_1(sess: requests.Session) -> str:
    """Submit a Safety Assessment that scores level 1 for the session user."""
    payload = {
        "section_1": {
            "s1_q1": "yes", "s1_q2": "no", "s1_q3": "no", "s1_q4": "no",
            "s1_q5": "no", "s1_q6": "no", "s1_q7": "no", "s1_q8": "no",
            "s1_q9": "no", "s1_q10": "no",
        },
        "section_2": {},
    }
    r = sess.post(f"{BASE_URL}/api/safety-assessment", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["level"] == 1
    return body["assessment_id"]


def _delete_safety(sess: requests.Session, aid: str):
    """Direct-mongo cleanup — there is no DELETE endpoint for safety_assessments."""
    try:
        from pymongo import MongoClient
        import os as _os
        with open("/app/backend/.env") as _f:
            for _l in _f:
                _l = _l.strip()
                if _l.startswith("MONGO_URL="):
                    _os.environ["MONGO_URL"] = _l.split("=", 1)[1].strip().strip('"').strip("'")
                if _l.startswith("DB_NAME="):
                    _os.environ["DB_NAME"] = _l.split("=", 1)[1].strip().strip('"').strip("'")
        cli = MongoClient(_os.environ["MONGO_URL"])
        cli[_os.environ["DB_NAME"]].safety_assessments.delete_one({"assessment_id": aid})
        cli.close()
    except Exception as e:  # pragma: no cover
        print(f"safety cleanup failed for {aid}: {e}")


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def base_url():
    assert BASE_URL, "REACT_APP_BACKEND_URL not set"
    return BASE_URL


@pytest.fixture(scope="module")
def parent1():
    """Canonical parent1@test.com — happy-path user."""
    return _register("parent1@test.com", "Sam Parent")


@pytest.fixture(scope="module")
def parent2():
    """Canonical parent2@test.com — happy-path partner."""
    return _register("parent2@test.com", "Riley Parent")


@pytest.fixture(scope="module")
def happy_share(parent1, parent2):
    """Fresh happy-path share: both consent, both complete medical assessment."""
    # Ensure any prior share is revoked so we start clean
    r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
    if r.status_code == 200:
        for s in r.json().get("shares", []):
            if s.get("partner_email") == "parent2@test.com" and s.get("status") != "revoked":
                parent1.post(f"{BASE_URL}/api/snc2/compare/{s['share_id']}/revoke")

    _seed_assessment(parent1)
    _seed_assessment(parent2)

    r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                     json={"email": "parent2@test.com"})
    assert r.status_code == 200, r.text
    share_id = r.json()["share"]["share_id"]

    # parent2 consents
    r = parent2.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                     json={"consent": True})
    assert r.status_code == 200, r.text
    assert r.json()["share"]["my_consent"] is True
    assert r.json()["share"]["partner_consent"] is True
    return share_id


# ============ Link creation ============
class TestLinkCreation:
    def test_link_own_email_400(self, parent1):
        r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                         json={"email": "parent1@test.com"})
        assert r.status_code == 400
        assert "own email" in r.json()["detail"].lower()

    def test_link_unknown_partner_404(self, parent1):
        ghost = f"TEST_ghost_{uuid.uuid4().hex[:8]}@test.com"
        r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                         json={"email": ghost})
        assert r.status_code == 404
        assert "no sa coparents account" in r.json()["detail"].lower()

    def test_link_dedup_returns_existing(self, happy_share, parent1):
        # Second /link for same pair should return already_existed=True
        r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                         json={"email": "parent2@test.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["already_existed"] is True
        assert body["share"]["share_id"] == happy_share


# ============ /me listing ============
class TestListMyShares:
    def test_creator_sees_share(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
        assert r.status_code == 200
        ids = [s["share_id"] for s in r.json()["shares"]]
        assert happy_share in ids

    def test_partner_sees_share(self, happy_share, parent2):
        r = parent2.get(f"{BASE_URL}/api/snc2/compare/me")
        assert r.status_code == 200
        ids = [s["share_id"] for s in r.json()["shares"]]
        assert happy_share in ids
        me_share = next(s for s in r.json()["shares"] if s["share_id"] == happy_share)
        assert me_share["role"] == "partner"


# ============ Comparison payload ============
class TestComparisonPayload:
    def test_active_returns_payload_with_expected_fields(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}")
        assert r.status_code == 200, r.text
        cmp = r.json()["comparison"]
        for key in ("shared_pathways", "only_parent_a_pathways",
                    "only_parent_b_pathways", "steps", "summary",
                    "alignment_labels"):
            assert key in cmp
        assert "medical" in cmp["shared_pathways"]
        # Summary fields
        s = cmp["summary"]
        for k in ("total_items", "aligned_pct", "divergent_pct", "counts"):
            assert k in s
        # Every item should carry an alignment
        items = [it for step in cmp["steps"] for p in step["pathways"] for it in p["items"]]
        assert len(items) > 0
        for it in items:
            assert "alignment" in it
            assert "prompt" in it
            assert "parent_a" in it and "parent_b" in it
            assert "type" in it

    def test_alignment_labels_present(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}")
        labels = r.json()["comparison"]["alignment_labels"]
        assert set(labels.keys()) >= {"aligned", "close", "divergent",
                                     "both_responded", "one_only", "insufficient"}


# ============ Category filter ============
class TestCategoryFilter:
    def test_medical_filter_restricts_pathways(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}",
                        params={"category": "medical"})
        assert r.status_code == 200
        cmp = r.json()["comparison"]
        for step in cmp["steps"]:
            for p in step["pathways"]:
                assert p["id"] == "medical"

    def test_educational_filter_400_when_neither_selected(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}",
                        params={"category": "educational"})
        assert r.status_code == 400
        assert "educational" in r.json()["detail"].lower()


# ============ PDF ============
class TestPdfEndpoint:
    def test_pdf_download(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")
        assert len(r.content) > 5000

    def test_pdf_with_category_filter(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}/pdf",
                        params={"category": "medical"})
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")


# ============ Safety guardrails ============
class TestSafetyGuardrailAtCreation:
    def test_creator_with_level1_safety_gets_403(self):
        # Fresh user so we don't corrupt happy_share for others
        email_a = f"TEST_safe_a_{uuid.uuid4().hex[:6]}@test.com"
        email_b = f"TEST_safe_b_{uuid.uuid4().hex[:6]}@test.com"
        sess_a = _register(email_a, "Safety A")
        _register(email_b, "Safety B")  # partner must exist

        aid = _submit_safety_level_1(sess_a)
        try:
            r = sess_a.post(f"{BASE_URL}/api/snc2/compare/link",
                            json={"email": email_b})
            assert r.status_code == 403, r.text
            assert "safety" in r.json()["detail"].lower()
        finally:
            _delete_safety(sess_a, aid)


class TestSafetyGuardrailAtConsent:
    def test_partner_with_level1_safety_gets_403_on_consent(self):
        email_a = f"TEST_scc_a_{uuid.uuid4().hex[:6]}@test.com"
        email_b = f"TEST_scc_b_{uuid.uuid4().hex[:6]}@test.com"
        sess_a = _register(email_a, "Consent A")
        sess_b = _register(email_b, "Consent B")

        r = sess_a.post(f"{BASE_URL}/api/snc2/compare/link", json={"email": email_b})
        assert r.status_code == 200, r.text
        share_id = r.json()["share"]["share_id"]

        aid = _submit_safety_level_1(sess_b)
        try:
            r = sess_b.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                            json={"consent": True})
            assert r.status_code == 403, r.text
            assert "safety" in r.json()["detail"].lower()
        finally:
            _delete_safety(sess_b, aid)


class TestSafetyGuardrailAtView:
    def test_viewer_with_level1_safety_gets_403_on_get(self, happy_share, parent1):
        # parent1 has active share. Trigger level 1 for parent1, then GET.
        aid = _submit_safety_level_1(parent1)
        try:
            r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}")
            assert r.status_code == 403, r.text
            assert "safety" in r.json()["detail"].lower()
            # And PDF should also be blocked.
            r2 = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}/pdf")
            assert r2.status_code == 403
        finally:
            _delete_safety(parent1, aid)

    def test_after_safety_clear_view_works_again(self, happy_share, parent1):
        r = parent1.get(f"{BASE_URL}/api/snc2/compare/{happy_share}")
        assert r.status_code == 200


# ============ Consent withdrawal + revoke ============
class TestConsentWithdrawalAndRevoke:
    def test_withdraw_consent_returns_409_on_get(self, parent1, parent2):
        # Fresh share dedicated to withdrawal test.
        email_a = f"TEST_wd_a_{uuid.uuid4().hex[:6]}@test.com"
        email_b = f"TEST_wd_b_{uuid.uuid4().hex[:6]}@test.com"
        sess_a = _register(email_a, "Wd A")
        sess_b = _register(email_b, "Wd B")
        _seed_assessment(sess_a)
        _seed_assessment(sess_b)
        r = sess_a.post(f"{BASE_URL}/api/snc2/compare/link", json={"email": email_b})
        share_id = r.json()["share"]["share_id"]
        r = sess_b.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                        json={"consent": True})
        assert r.status_code == 200
        # Verify active
        r = sess_a.get(f"{BASE_URL}/api/snc2/compare/{share_id}")
        assert r.status_code == 200
        # Withdraw partner consent
        r = sess_b.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                        json={"consent": False})
        assert r.status_code == 200
        assert r.json()["share"]["my_consent"] is False
        # Now GET should be 409
        r = sess_a.get(f"{BASE_URL}/api/snc2/compare/{share_id}")
        assert r.status_code == 409

    def test_revoke_returns_409_on_get_and_pdf(self, parent1, parent2):
        email_a = f"TEST_rv_a_{uuid.uuid4().hex[:6]}@test.com"
        email_b = f"TEST_rv_b_{uuid.uuid4().hex[:6]}@test.com"
        sess_a = _register(email_a, "Rv A")
        sess_b = _register(email_b, "Rv B")
        _seed_assessment(sess_a)
        _seed_assessment(sess_b)
        r = sess_a.post(f"{BASE_URL}/api/snc2/compare/link", json={"email": email_b})
        share_id = r.json()["share"]["share_id"]
        sess_b.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                    json={"consent": True})
        r = sess_a.post(f"{BASE_URL}/api/snc2/compare/{share_id}/revoke")
        assert r.status_code == 200
        assert r.json()["share"]["status"] == "revoked"
        r = sess_a.get(f"{BASE_URL}/api/snc2/compare/{share_id}")
        assert r.status_code == 409
        r = sess_a.get(f"{BASE_URL}/api/snc2/compare/{share_id}/pdf")
        assert r.status_code == 409


# ============ 409 when partner incomplete ============
class TestIncompleteAssessment409:
    def test_get_returns_409_when_partner_hasnt_finished(self):
        email_a = f"TEST_inc_a_{uuid.uuid4().hex[:6]}@test.com"
        email_b = f"TEST_inc_b_{uuid.uuid4().hex[:6]}@test.com"
        sess_a = _register(email_a, "Inc A")
        sess_b = _register(email_b, "Inc B")
        _seed_assessment(sess_a)
        # sess_b does NOT complete
        r = sess_a.post(f"{BASE_URL}/api/snc2/compare/link", json={"email": email_b})
        share_id = r.json()["share"]["share_id"]
        sess_b.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                    json={"consent": True})
        r = sess_a.get(f"{BASE_URL}/api/snc2/compare/{share_id}")
        assert r.status_code == 409
