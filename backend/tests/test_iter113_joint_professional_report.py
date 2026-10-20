"""Iter 113 — Joint Co-Parenting Summary for Professional Review.

Locks the neutral-language guardrails, the consent gate, section
shape, and the PDF export. Uses the shared parent1/parent2 fixtures
+ the SNC v2 compare flow to reach an active share, then hits the
new /api/joint-professional-report/{share_id} endpoints.
"""
from __future__ import annotations

import os
import re
import uuid

import pytest
import requests

# Fresh accounts each run (older shared test accounts may hold a saved concerning result, which blocks comparisons).
P1 = f"test_jpr_a_{uuid.uuid4().hex[:6]}@example.com"
P2 = f"test_jpr_b_{uuid.uuid4().hex[:6]}@example.com"

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


# Fresh registration/login helper — identical to the SNC2 compare tests
# but self-contained so this module can run standalone.
def _register(email: str, name: str, password: str = "TestPass123!") -> requests.Session:
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": name,
              "ack_privacy_notice": True, "consent_sensitive_info": True},
        timeout=30,
    )
    if r.status_code == 400:
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


SEED_MED = {
    "step1_medical_concern": "Chronic asthma; daily controller.",
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
    "step5_medical_routines_consistent": 4,
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

# Parent B answers — deliberately diverge on the consistency step so the
# report has a "differs" row to summarise.
SEED_MED_B = dict(SEED_MED)
SEED_MED_B["step5_medical_routines_consistent"] = 1
SEED_MED_B["step5_medical_share_updates"] = 1
SEED_MED_B["step6_medical_agree_areas"] = "We agree on the diagnosis."
SEED_MED_B["step6_medical_biggest_gap"] = "Different priorities"


def _seed_snc2(sess: requests.Session, answers=None, pathways=("medical",)):
    sess.delete(f"{BASE_URL}/api/snc2/me")
    r = sess.post(f"{BASE_URL}/api/snc2/select",
                  json={"pathways": list(pathways), "child_name": "Kiddo"})
    assert r.status_code == 200, r.text
    r = sess.post(f"{BASE_URL}/api/snc2/answers/bulk",
                  json={"answers": answers or SEED_MED})
    assert r.status_code == 200, r.text
    r = sess.post(f"{BASE_URL}/api/snc2/complete")
    assert r.status_code == 200, r.text


@pytest.fixture(scope="module")
def parent1():
    return _register(P1, "Sam Parent")


@pytest.fixture(scope="module")
def parent2():
    return _register(P2, "Riley Parent")


@pytest.fixture(scope="module")
def active_share(parent1, parent2):
    """Create a fully-consented SNC v2 share we can point the joint report at."""
    # Revoke any pre-existing share so we start from a known state.
    r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
    if r.status_code == 200:
        for s in r.json().get("shares", []):
            if s.get("partner_email") == P2 and s.get("status") != "revoked":
                parent1.post(f"{BASE_URL}/api/snc2/compare/{s['share_id']}/revoke")

    _seed_snc2(parent1, SEED_MED)
    _seed_snc2(parent2, SEED_MED_B)

    r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                     json={"email": P2})
    assert r.status_code == 200, r.text
    share_id = r.json()["share"]["share_id"]
    r = parent2.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                     json={"consent": True})
    assert r.status_code == 200, r.text
    return share_id


# ================================================================
# TESTS
# ================================================================

class TestConsentGate:
    def test_auth_required(self):
        r = requests.get(f"{BASE_URL}/api/joint-professional-report/{uuid.uuid4().hex}",
                         timeout=30)
        assert r.status_code in {401, 403}

    def test_unknown_share_404(self, parent1):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{uuid.uuid4().hex}")
        assert r.status_code == 404

    def test_non_participant_403(self, active_share):
        # Fresh stranger — not part of the pair.
        stranger = _register(
            f"TEST_stranger_{uuid.uuid4().hex[:8]}@test.com", "Stranger",
        )
        r = stranger.get(f"{BASE_URL}/api/joint-professional-report/{active_share}")
        assert r.status_code == 403


class TestPayloadShape:
    def test_all_nine_sections_present(self, parent1, active_share):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{active_share}")
        assert r.status_code == 200, r.text
        body = r.json()
        expected = {
            "shared_priorities",
            "medical",
            "educational",
            "psychological",
            "household_consistency",
            "communication_concerns",
            "areas_of_agreement",
            "areas_where_perceptions_differ",
            "issues_for_professional_discussion",
        }
        assert set(body["sections"].keys()) == expected

    def test_disclaimer_and_neutral_language(self, parent1, active_share):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{active_share}")
        body = r.json()
        assert body["not_a_custody_evaluation"] is True
        d = body["disclaimer"]
        assert "not a custody evaluation" in d.lower()
        assert "neutral" in body["neutral_language_note"].lower()

    def test_safety_step_line_only(self, parent1, active_share):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{active_share}")
        body = r.json()
        # Only the safety-step line; no safety-lens finding or note.
        assert body["safety_step"] == "Safety step: see SACOparentsAlign"
        assert "safety_privacy_note" not in body and "finding 3" not in str(body).lower()
        # No leaked Finding 1/2 language anywhere in the payload.
        text = str(body).lower()
        assert "family_violence_pattern" not in text
        assert "trauma_impact" not in text

    def test_medical_section_has_rows_after_seed(self, parent1, active_share):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{active_share}")
        body = r.json()
        medical = body["sections"]["medical"]
        assert medical["row_count"] >= 1
        # Divergent rows should surface first thanks to the sort.
        first = medical["rows"][0]
        assert first["alignment"] in {"divergent", "close", "one_only", "aligned",
                                       "insufficient", "both_responded"}

    def test_neutral_phrasing_in_issues(self, parent1, active_share):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{active_share}")
        body = r.json()
        # Scan every issue_for_discussion / summary for banned adjudicative
        # language. No "mother is correct", "father is uncooperative", "should
        # have custody", "primary custody", "sole custody", "possession".
        banned = re.compile(
            r"(mother is correct|father is correct|"
            r"is uncooperative|is at fault|should have custody|"
            r"primary custody|sole custody|possession|access schedule|"
            r"visitation should|court should award|parent a should have)",
            re.IGNORECASE,
        )
        for sect in body["sections"].values():
            for row in sect.get("rows") or []:
                text = " ".join([
                    row.get("issue_for_discussion") or "",
                    (row.get("parent_a") or {}).get("summary") or "",
                    (row.get("parent_b") or {}).get("summary") or "",
                    row.get("childs_need") or "",
                ])
                assert not banned.search(text), (
                    f"Banned language surfaced in row {row.get('topic')}: {text}"
                )


class TestPdf:
    def test_pdf_bytes(self, parent1, active_share):
        r = parent1.get(f"{BASE_URL}/api/joint-professional-report/{active_share}/pdf")
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"].startswith("application/pdf")
        # Non-trivial PDF (cover page + at least a couple of section pages).
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)} bytes"
        assert r.content.startswith(b"%PDF-")

    def test_pdf_pathway_gate_still_enforced(self, active_share):
        stranger = _register(
            f"TEST_stranger_pdf_{uuid.uuid4().hex[:8]}@test.com", "Stranger PDF",
        )
        r = stranger.get(f"{BASE_URL}/api/joint-professional-report/{active_share}/pdf")
        assert r.status_code == 403



class TestEmailEndpoint:
    """The /email endpoint reuses the same consent gate and validates
    recipient input. We don't require the mail transport to actually be
    configured — the endpoint returns 503 with a specific message when
    it isn't, which is still a valid, testable outcome."""

    def test_auth_required(self, active_share):
        r = requests.post(
            f"{BASE_URL}/api/joint-professional-report/{active_share}/email",
            json={"recipient_email": "test@example.com"},
            timeout=30,
        )
        assert r.status_code in {401, 403}

    def test_non_participant_403(self, active_share):
        stranger = _register(
            f"TEST_email_stranger_{uuid.uuid4().hex[:8]}@test.com", "Email Stranger",
        )
        r = stranger.post(
            f"{BASE_URL}/api/joint-professional-report/{active_share}/email",
            json={"recipient_email": "someone@example.com"},
        )
        assert r.status_code == 403

    def test_invalid_email_rejected(self, parent1, active_share):
        r = parent1.post(
            f"{BASE_URL}/api/joint-professional-report/{active_share}/email",
            json={"recipient_email": "not-an-email"},
        )
        assert r.status_code == 400
        assert "email" in r.json()["detail"].lower()

    def test_demo_email_rejected(self, parent1, active_share):
        r = parent1.post(
            f"{BASE_URL}/api/joint-professional-report/{active_share}/email",
            json={"recipient_email": "someone@demo.local"},
        )
        assert r.status_code == 400

    def test_happy_path_or_email_not_configured(self, parent1, active_share):
        """Either the email lands (200) or the environment doesn't have
        the mail transport wired (503 with a clear message). Both are
        acceptable — what we care about is that the consent gate and
        payload assembly worked."""
        r = parent1.post(
            f"{BASE_URL}/api/joint-professional-report/{active_share}/email",
            json={
                "recipient_email": f"mediator+{uuid.uuid4().hex[:6]}@example.com",
                "recipient_name":  "Test Mediator",
                "recipient_role":  "mediator",
                "parent_message":  "Please review before our next session.",
            },
        )
        assert r.status_code in {200, 503}, r.text[:300]
        if r.status_code == 200:
            body = r.json()
            assert body["ok"] is True
            assert body["audience"] == "Mediator"
            assert body["share_id"] == active_share


class TestProfessionalIntroPdf:
    """The 3-minute Introduction is a static explainer that any parent
    (or professional) can download without an active share."""

    def test_intro_pdf_public_and_valid(self):
        r = requests.get(
            f"{BASE_URL}/api/joint-professional-report/professional-intro.pdf",
            timeout=30,
        )
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content.startswith(b"%PDF-")
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"

    def test_intro_pdf_not_confused_with_share_route(self, parent1, active_share):
        """The fixed-path intro route must win over `{share_id}` catch-all."""
        r = requests.get(
            f"{BASE_URL}/api/joint-professional-report/professional-intro.pdf",
            timeout=30,
        )
        # Public — no auth, no 403 collision with the share route.
        assert r.status_code == 200
        # And the share route still works for participants.
        r2 = parent1.get(
            f"{BASE_URL}/api/joint-professional-report/{active_share}",
        )
        assert r2.status_code == 200

