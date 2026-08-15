"""Iter 116 — Joint Co-Parenting Agreement Draft merger.

Locks the deterministic merge behaviour, the consent gate, and the PDF
export. Uses parent1/parent2 fixtures + the SNC v2 compare flow to reach
an active share, then seeds both parents' `agreements` collection with
overlapping-but-distinct drafts so the merger has both matched and
solo clauses to bucket.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _register(email: str, name: str, password: str = "TestPass123!") -> requests.Session:
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=30,
    )
    if r.status_code == 400:
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
    assert r.status_code == 200
    tok = r.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    return s


def _get_user_id(sess: requests.Session) -> str:
    r = sess.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


def _mongo():
    from pymongo import MongoClient
    with open("/app/backend/.env") as f:
        for line in f:
            line = line.strip()
            if line.startswith("MONGO_URL="):
                os.environ["MONGO_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("DB_NAME="):
                os.environ["DB_NAME"] = line.split("=", 1)[1].strip().strip('"').strip("'")
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _seed_agreement(user_id: str, *, communication, child_needs, shared_goals, open_for_discussion=None):
    db = _mongo()
    doc = {
        "agreement_id":       f"agr_{uuid.uuid4().hex[:12]}",
        "user_id":            user_id,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "overview":           "Test agreement.",
        "shared_goals":       shared_goals,
        "communication":      communication,
        "child_needs":        child_needs,
        "household_rules":    [],
        "priority_items":     [],
        "open_for_discussion": open_for_discussion or [],
        "closing_note":       "A living document.",
    }
    db.agreements.insert_one(doc.copy())
    return doc


@pytest.fixture(scope="module")
def parent1():
    return _register("parent1@test.com", "Sam Parent")


@pytest.fixture(scope="module")
def parent2():
    return _register("parent2@test.com", "Riley Parent")


SEED_MED = {
    "step1_medical_concern": "Chronic asthma; daily controller.",
    "step1_medical_current_impact": 4,
    "step1_medical_duration": "1 to 3 years",
    "step1_medical_urgency": "Needs attention within weeks",
    "step2_medical_current_needs": ["Chronic medical condition"],
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


@pytest.fixture(scope="module")
def active_share(parent1, parent2):
    """Fresh active SNC v2 share between parent1 and parent2."""
    r = parent1.get(f"{BASE_URL}/api/snc2/compare/me")
    if r.status_code == 200:
        for s in r.json().get("shares", []):
            if s.get("partner_email") == "parent2@test.com" and s.get("status") != "revoked":
                parent1.post(f"{BASE_URL}/api/snc2/compare/{s['share_id']}/revoke")
    for sess in (parent1, parent2):
        sess.delete(f"{BASE_URL}/api/snc2/me")
        sess.post(f"{BASE_URL}/api/snc2/select",
                  json={"pathways": ["medical"], "child_name": "Kiddo"})
        sess.post(f"{BASE_URL}/api/snc2/answers/bulk", json={"answers": SEED_MED})
        sess.post(f"{BASE_URL}/api/snc2/complete")
    r = parent1.post(f"{BASE_URL}/api/snc2/compare/link",
                     json={"email": "parent2@test.com"})
    assert r.status_code == 200
    share_id = r.json()["share"]["share_id"]
    r = parent2.post(f"{BASE_URL}/api/snc2/compare/{share_id}/consent",
                     json={"consent": True})
    assert r.status_code == 200
    return share_id


@pytest.fixture(scope="module")
def seeded_agreements(parent1, parent2):
    """Seed both parents with overlapping-but-distinct agreement drafts."""
    a_id = _get_user_id(parent1)
    b_id = _get_user_id(parent2)
    # Clean out prior test seeds.
    db = _mongo()
    db.agreements.delete_many({"user_id": {"$in": [a_id, b_id]}})

    _seed_agreement(
        a_id,
        shared_goals=[
            "Consistent bedtime routines",
            "Both parents attend medical appointments",
            "Encourage independence",
        ],
        communication=[
            {"area": "Texting", "agreement": "Reply to non-urgent texts within 24 hours."},
            {"area": "Emergency", "agreement": "Call each other immediately for any medical emergency."},
        ],
        child_needs=[
            {"area": "Medical", "agreement": "Medication travels with the child between homes."},
        ],
        open_for_discussion=["Screen time on school nights"],
    )
    _seed_agreement(
        b_id,
        shared_goals=[
            "Consistent bedtime routines across both homes",
            "Encourage independence in age-appropriate ways",
            "Prioritise homework help",
        ],
        communication=[
            {"area": "Texting", "agreement": "Reply to non-urgent messages within one day."},
            {"area": "Written", "agreement": "Use OurFamilyWizard for schedule changes."},
        ],
        child_needs=[
            {"area": "Medical", "agreement": "Medication should always travel with the child."},
            {"area": "School", "agreement": "Both parents added to school portal."},
        ],
        open_for_discussion=["Extracurricular activities on transition days"],
    )
    return {"parent_a_id": a_id, "parent_b_id": b_id}


class TestConsentGate:
    def test_auth_required(self):
        r = requests.get(
            f"{BASE_URL}/api/joint-agreement/{uuid.uuid4().hex}", timeout=30,
        )
        assert r.status_code in {401, 403}

    def test_unknown_share_404(self, parent1):
        r = parent1.get(f"{BASE_URL}/api/joint-agreement/{uuid.uuid4().hex}")
        assert r.status_code == 404

    def test_non_participant_403(self, active_share, seeded_agreements):
        stranger = _register(
            f"TEST_agr_stranger_{uuid.uuid4().hex[:8]}@test.com", "Stranger",
        )
        r = stranger.get(f"{BASE_URL}/api/joint-agreement/{active_share}")
        assert r.status_code == 403


class TestMergerShape:
    def test_all_expected_sections(self, parent1, active_share, seeded_agreements):
        r = parent1.get(f"{BASE_URL}/api/joint-agreement/{active_share}")
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        keys = [s["key"] for s in body["sections"]]
        assert keys == [
            "shared_goals", "communication", "child_needs", "household_rules",
            "priority_items", "open_for_discussion",
        ]

    def test_bucketed_correctly(self, parent1, active_share, seeded_agreements):
        r = parent1.get(f"{BASE_URL}/api/joint-agreement/{active_share}")
        body = r.json()
        by_key = {s["key"]: s for s in body["sections"]}

        # shared_goals: "Consistent bedtime routines" ~ "... across both homes"
        # should merge. "Encourage independence" vs "... in age-appropriate ways"
        # is intentionally under threshold — that's fine, it becomes a solo.
        goals = by_key["shared_goals"]
        assert goals["counts"]["both_proposed"] >= 1, goals
        assert goals["counts"]["parent_a_only"] >= 1
        assert goals["counts"]["parent_b_only"] >= 1

        # communication: "Reply to non-urgent texts within 24 hours" ~
        # "Reply to non-urgent messages within one day" should merge as "Texting".
        comm = by_key["communication"]
        assert comm["counts"]["both_proposed"] >= 1
        assert comm["counts"]["parent_a_only"] >= 1  # Emergency
        assert comm["counts"]["parent_b_only"] >= 1  # Written / OurFamilyWizard

        # child_needs: medication clause should merge.
        cn = by_key["child_needs"]
        assert cn["counts"]["both_proposed"] >= 1
        assert cn["counts"]["parent_b_only"] >= 1  # School

    def test_disclaimer_present(self, parent1, active_share, seeded_agreements):
        r = parent1.get(f"{BASE_URL}/api/joint-agreement/{active_share}")
        body = r.json()
        assert body["not_a_final_agreement"] is True
        d = body["disclaimer"].lower()
        assert "draft for discussion" in d
        assert "not a signed agreement" in d
        assert "custody" in d  # "not a custody recommendation"

    def test_summary_convergence_math(self, parent1, active_share, seeded_agreements):
        r = parent1.get(f"{BASE_URL}/api/joint-agreement/{active_share}")
        body = r.json()
        s = body["summary"]
        total = s["both_proposed"] + s["parent_a_only"] + s["parent_b_only"]
        assert s["total_clauses"] == total
        assert 0 <= s["converged_pct"] <= 100


class TestMissingAgreements:
    def test_missing_parent_a_draft(self, parent1, parent2, active_share):
        """Wipe parent1's agreements and expect a 409 pointing them at
        the individual draft flow."""
        db = _mongo()
        user_id = _get_user_id(parent1)
        # Snapshot then wipe.
        pre = list(db.agreements.find({"user_id": user_id}))
        db.agreements.delete_many({"user_id": user_id})
        try:
            r = parent1.get(f"{BASE_URL}/api/joint-agreement/{active_share}")
            assert r.status_code == 409
            assert "haven't generated" in r.json()["detail"].lower()
        finally:
            if pre:
                for row in pre:
                    row.pop("_id", None)
                    db.agreements.insert_one(row)


class TestPdf:
    def test_pdf_bytes(self, parent1, active_share, seeded_agreements):
        r = parent1.get(f"{BASE_URL}/api/joint-agreement/{active_share}/pdf")
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content.startswith(b"%PDF-")
        assert len(r.content) > 3000
