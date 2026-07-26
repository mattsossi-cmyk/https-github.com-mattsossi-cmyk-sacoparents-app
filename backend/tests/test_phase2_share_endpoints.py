"""Phase 2 HTTP integration tests — selective section sharing across the 4 reports.

Seeds documents directly in MongoDB (fast, no LLM), then exercises:
  - GET  /api/mediation/reports/sections/{report_type}
  - PATCH /api/mediation/summary/{id}/visibility
  - PATCH /api/mediation/agreement/{id}/visibility
  - PATCH /api/neurodivergent/report/visibility
  - PATCH /api/safety-assessment/{id}/visibility  (locked keys stripped)
  - GET  /api/mediation/summary/{id}/pdf         (persisted + ?excluded= override)
  - GET  /api/mediation/agreement/{id}/pdf
  - GET  /api/neurodivergent/report/pdf
  - GET  /api/safety-assessment/{id}/pdf         (locked stays)
  - POST /api/mediation/summary/{id}/share-link  + GET /api/mediation/shared/{token}
  - POST /api/mediation/agreement/{id}/share-link + shared/{token}
  - POST /api/neurodivergent/report/{id}/share-link + shared/{token} (?format=json)
  - POST /api/safety-assessment/{id}/share-link  + shared/{token}
  - share-link without body seeds excluded from persisted visibility.
"""
from __future__ import annotations
import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

# Load backend env (MONGO_URL / DB_NAME)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


# ----------------------- Fixtures -----------------------
@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def auth_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Try login
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        # Try register
        rr = s.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "name": "Sam Parent"},
        )
        if rr.status_code not in (200, 201):
            pytest.skip(f"Cannot authenticate: login={r.status_code} register={rr.status_code}")
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200, r.text
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    # Attach user id (from /api/auth/me)
    me = s.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 200, me.text
    s.user_id = me.json().get("user_id") or me.json().get("id")
    return s


@pytest.fixture
def seeded_summary(db, auth_client):
    sid = f"sum_TEST_{uuid.uuid4().hex[:8]}"
    doc = {
        "summary_id": sid,
        "user_id": auth_client.user_id,
        "readiness_label": "Preparing",
        "readiness_score": 60,
        "child_goals_summary": "keep kids first",
        "top_concerns": ["schedule", "communication"],
        "priority_agenda": [{"rank": 1, "topic": "school pickup", "category": "logistics"}],
        "flexibility_areas": ["holidays"],
        "communication_goals": ["clear, kid-focused messages"],
        "notes_for_mediator": "Please help us stay child-focused.",
        "changes_since_last": "improved comms",
        "generated_at": "2026-01-01T00:00:00Z",
    }
    db.summaries.insert_one(doc.copy())
    yield sid
    db.summaries.delete_one({"summary_id": sid})


@pytest.fixture
def seeded_agreement(db, auth_client):
    aid = f"agr_TEST_{uuid.uuid4().hex[:8]}"
    doc = {
        "agreement_id": aid,
        "user_id": auth_client.user_id,
        "shared_goals": ["safe, stable childhood"],
        "communication": [{"area": "texts", "agreement": "polite tone"}],
        "child_needs": [{"area": "school", "agreement": "shared calendar"}],
        "household_rules": [{"area": "bedtime", "agreement": "9pm"}],
        "priority_items": [{"rank": 1, "topic": "medical decisions"}],
        "open_for_discussion": ["holiday sched"],
        "closing_note": "we're aligned",
        "changes_since_last": "small tweaks",
        "generated_at": "2026-01-01T00:00:00Z",
    }
    db.agreements.insert_one(doc.copy())
    yield aid
    db.agreements.delete_one({"agreement_id": aid})


@pytest.fixture
def seeded_sn_report(db, auth_client):
    rid = f"sn_TEST_{uuid.uuid4().hex[:8]}"
    doc = {
        "report_id": rid,
        "user_id": auth_client.user_id,
        "child_name": "TestChild",
        "generated_at": "2026-01-01T00:00:00Z",
        "scores": {"cooperation": 70},
        "report": {
            "child_profile": {"summary": "kind", "strengths": ["curious"], "what_helps": ["routine"], "support_needs": ["quiet space"]},
            "agreement_areas": [{"title": "diet", "detail": "no dairy"}],
            "coordination_gaps": [{"title": "meds", "detail": "who logs"}],
            "priorities": {"immediate": ["med log"], "thirty_day": [], "longer_term": []},
            "structure_reasoning": "cooperative",
            "action_plan": [{"need": "med log", "action": "shared sheet", "responsible": "both", "channel": "app", "review": "monthly"}],
            "disclaimer": "Not clinical advice.",
        },
    }
    # Upsert (one report per user)
    db.sn_v2_reports.delete_many({"user_id": auth_client.user_id})
    db.sn_v2_reports.insert_one(doc.copy())
    yield rid
    db.sn_v2_reports.delete_many({"user_id": auth_client.user_id})


@pytest.fixture
def created_safety(auth_client):
    """Create a safety assessment via the real POST endpoint."""
    r = auth_client.post(
        f"{BASE_URL}/api/safety-assessment",
        json={
            "section_1": {"q1": "no", "q2": "no", "q3": "no"},
            "section_2": {"q1": "yes", "q2": "yes"},
        },
    )
    assert r.status_code == 200, r.text
    aid = r.json()["assessment_id"]
    yield aid
    # cleanup handled by user data isolation


# ----------------------- Catalog -----------------------
class TestSectionCatalog:
    @pytest.mark.parametrize("rt", ["summary", "agreement", "sn_report", "safety"])
    def test_catalog_returns_sections(self, auth_client, rt):
        r = auth_client.get(f"{BASE_URL}/api/mediation/reports/sections/{rt}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["report_type"] == rt
        assert isinstance(data["sections"], list) and len(data["sections"]) > 0
        for s in data["sections"]:
            assert "key" in s and "label" in s and "description" in s

    def test_catalog_safety_has_locked(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/mediation/reports/sections/safety")
        assert r.status_code == 200
        keys_locked = {s["key"]: s.get("locked") for s in r.json()["sections"]}
        assert keys_locked.get("pathway") == "true"
        assert keys_locked.get("texas_resources") == "true"

    def test_catalog_unknown_returns_404(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/mediation/reports/sections/bogus")
        assert r.status_code == 404


# ----------------------- Summary visibility + PDF + share -----------------------
class TestSummaryVisibility:
    def test_patch_visibility_strips_unknown_and_persists(self, auth_client, seeded_summary, db):
        r = auth_client.patch(
            f"{BASE_URL}/api/mediation/summary/{seeded_summary}/visibility",
            json={"excluded": ["top_concerns", "bogus_key", "notes_for_mediator"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["excluded"] == ["notes_for_mediator", "top_concerns"]
        # Persisted
        doc = db.summaries.find_one({"summary_id": seeded_summary})
        assert doc["visibility"]["excluded"] == ["notes_for_mediator", "top_concerns"]

    def test_patch_unknown_summary_404(self, auth_client):
        r = auth_client.patch(
            f"{BASE_URL}/api/mediation/summary/sum_does_not_exist/visibility",
            json={"excluded": []},
        )
        assert r.status_code == 404

    def test_pdf_honors_persisted_visibility(self, auth_client, seeded_summary):
        # Full PDF
        r1 = auth_client.get(f"{BASE_URL}/api/mediation/summary/{seeded_summary}/pdf")
        assert r1.status_code == 200 and r1.content.startswith(b"%PDF-")
        full_size = len(r1.content)
        # Persist excluded
        auth_client.patch(
            f"{BASE_URL}/api/mediation/summary/{seeded_summary}/visibility",
            json={"excluded": ["top_concerns", "priority_agenda", "notes_for_mediator"]},
        )
        r2 = auth_client.get(f"{BASE_URL}/api/mediation/summary/{seeded_summary}/pdf")
        assert r2.status_code == 200 and r2.content.startswith(b"%PDF-")
        assert len(r2.content) < full_size, "Filtered PDF should be smaller than full PDF"

    def test_pdf_query_override(self, auth_client, seeded_summary):
        r1 = auth_client.get(f"{BASE_URL}/api/mediation/summary/{seeded_summary}/pdf")
        full = len(r1.content)
        r2 = auth_client.get(
            f"{BASE_URL}/api/mediation/summary/{seeded_summary}/pdf",
            params={"excluded": "top_concerns,priority_agenda,notes_for_mediator,flexibility_areas"},
        )
        assert r2.status_code == 200 and r2.content.startswith(b"%PDF-")
        assert len(r2.content) < full

    def test_share_link_with_body(self, auth_client, seeded_summary):
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/summary/{seeded_summary}/share-link",
            json={"excluded": ["top_concerns", "notes_for_mediator", "bogus_key"]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["excluded"] == ["notes_for_mediator", "top_concerns"]
        token = data["token"]
        # Public shared PDF
        pub = requests.get(f"{BASE_URL}/api/mediation/shared/{token}")
        assert pub.status_code == 200 and pub.content.startswith(b"%PDF-")

    def test_share_link_no_body_falls_back_to_persisted(self, auth_client, seeded_summary):
        auth_client.patch(
            f"{BASE_URL}/api/mediation/summary/{seeded_summary}/visibility",
            json={"excluded": ["top_concerns"]},
        )
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/summary/{seeded_summary}/share-link",
            json={},  # no excluded
        )
        assert r.status_code == 200
        # Fallback to persisted
        assert r.json()["excluded"] == ["top_concerns"]


# ----------------------- Agreement visibility + PDF + share -----------------------
class TestAgreementVisibility:
    def test_patch_visibility(self, auth_client, seeded_agreement, db):
        r = auth_client.patch(
            f"{BASE_URL}/api/mediation/agreement/{seeded_agreement}/visibility",
            json={"excluded": ["communication", "closing_note", "bogus"]},
        )
        assert r.status_code == 200
        assert r.json()["excluded"] == ["closing_note", "communication"]
        assert db.agreements.find_one({"agreement_id": seeded_agreement})["visibility"]["excluded"] == \
            ["closing_note", "communication"]

    def test_pdf_and_query_override(self, auth_client, seeded_agreement):
        r1 = auth_client.get(f"{BASE_URL}/api/mediation/agreement/{seeded_agreement}/pdf")
        assert r1.status_code == 200 and r1.content.startswith(b"%PDF-")
        r2 = auth_client.get(
            f"{BASE_URL}/api/mediation/agreement/{seeded_agreement}/pdf",
            params={"excluded": "communication,closing_note,shared_goals,child_needs"},
        )
        assert r2.status_code == 200 and r2.content.startswith(b"%PDF-")
        assert len(r2.content) < len(r1.content)

    def test_share_link(self, auth_client, seeded_agreement):
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/agreement/{seeded_agreement}/share-link",
            json={"excluded": ["communication"]},
        )
        assert r.status_code == 200
        token = r.json()["token"]
        pub = requests.get(f"{BASE_URL}/api/mediation/shared/{token}")
        assert pub.status_code == 200 and pub.content.startswith(b"%PDF-")


# ----------------------- SN report visibility + PDF + share -----------------------
class TestSNReportVisibility:
    def test_patch_visibility_persists(self, auth_client, seeded_sn_report, db):
        r = auth_client.patch(
            f"{BASE_URL}/api/neurodivergent/report/visibility",
            json={"excluded": ["coordination_gaps", "bogus", "action_plan"]},
        )
        assert r.status_code == 200
        assert r.json()["excluded"] == ["action_plan", "coordination_gaps"]
        assert db.sn_v2_reports.find_one({"report_id": seeded_sn_report})["visibility"]["excluded"] == \
            ["action_plan", "coordination_gaps"]

    def test_pdf_honors_persisted(self, auth_client, seeded_sn_report):
        r1 = auth_client.get(f"{BASE_URL}/api/neurodivergent/report/pdf")
        assert r1.status_code == 200 and r1.content.startswith(b"%PDF-")
        full = len(r1.content)
        auth_client.patch(
            f"{BASE_URL}/api/neurodivergent/report/visibility",
            json={"excluded": ["coordination_gaps", "action_plan", "agreement_areas"]},
        )
        r2 = auth_client.get(f"{BASE_URL}/api/neurodivergent/report/pdf")
        assert r2.status_code == 200 and r2.content.startswith(b"%PDF-")
        assert len(r2.content) < full

    def test_pdf_query_override(self, auth_client, seeded_sn_report):
        r1 = auth_client.get(f"{BASE_URL}/api/neurodivergent/report/pdf")
        r2 = auth_client.get(
            f"{BASE_URL}/api/neurodivergent/report/pdf",
            params={"excluded": "coordination_gaps,action_plan,agreement_areas,priorities"},
        )
        assert r2.status_code == 200
        assert len(r2.content) < len(r1.content)

    def test_share_link_pdf_and_json(self, auth_client, seeded_sn_report):
        r = auth_client.post(
            f"{BASE_URL}/api/neurodivergent/report/{seeded_sn_report}/share-link",
            json={"excluded": ["coordination_gaps", "action_plan"]},
        )
        assert r.status_code == 200
        token = r.json()["token"]
        # Public JSON
        j = requests.get(f"{BASE_URL}/api/neurodivergent/report/shared/{token}", params={"format": "json"})
        assert j.status_code == 200, j.text
        body = j.json()
        assert body["excluded_sections"] == ["action_plan", "coordination_gaps"]
        assert body["report"]["coordination_gaps"] == []
        assert body["report"]["action_plan"] == []
        # Public PDF
        p = requests.get(f"{BASE_URL}/api/neurodivergent/report/shared/{token}")
        assert p.status_code == 200 and p.content.startswith(b"%PDF-")


# ----------------------- Safety visibility + PDF + share (locked!) -----------------------
class TestSafetyVisibility:
    def test_patch_visibility_strips_locked(self, auth_client, created_safety, db):
        r = auth_client.patch(
            f"{BASE_URL}/api/safety-assessment/{created_safety}/visibility",
            json={"excluded": ["section_1", "pathway", "texas_resources", "section_2"]},
        )
        assert r.status_code == 200
        # locked keys stripped
        assert set(r.json()["excluded"]) == {"section_1", "section_2"}
        persisted = db.safety_assessments.find_one({"assessment_id": created_safety})["visibility"]["excluded"]
        assert "pathway" not in persisted and "texas_resources" not in persisted

    def test_pdf_honors_persisted_locked_stays(self, auth_client, created_safety):
        r1 = auth_client.get(f"{BASE_URL}/api/safety-assessment/{created_safety}/pdf")
        assert r1.status_code == 200 and r1.content.startswith(b"%PDF-")
        full = len(r1.content)
        auth_client.patch(
            f"{BASE_URL}/api/safety-assessment/{created_safety}/visibility",
            json={"excluded": ["section_1", "section_2"]},
        )
        r2 = auth_client.get(f"{BASE_URL}/api/safety-assessment/{created_safety}/pdf")
        assert r2.status_code == 200 and r2.content.startswith(b"%PDF-")
        assert len(r2.content) < full

    def test_pdf_query_override(self, auth_client, created_safety):
        r1 = auth_client.get(f"{BASE_URL}/api/safety-assessment/{created_safety}/pdf")
        r2 = auth_client.get(
            f"{BASE_URL}/api/safety-assessment/{created_safety}/pdf",
            params={"excluded": "section_1,section_2,pathway,texas_resources"},
        )
        assert r2.status_code == 200 and r2.content.startswith(b"%PDF-")
        # locked keys still there; excluded only removes section_1 & section_2
        assert len(r2.content) < len(r1.content)

    def test_share_link_public(self, auth_client, created_safety):
        r = auth_client.post(
            f"{BASE_URL}/api/safety-assessment/{created_safety}/share-link",
            json={"excluded": ["section_1", "pathway"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert "pathway" not in data["excluded"]
        token = data["token"]
        pub = requests.get(f"{BASE_URL}/api/safety-assessment/shared/{token}")
        assert pub.status_code == 200 and pub.content.startswith(b"%PDF-")

    def test_share_link_no_body_fallback(self, auth_client, created_safety):
        auth_client.patch(
            f"{BASE_URL}/api/safety-assessment/{created_safety}/visibility",
            json={"excluded": ["section_2"]},
        )
        r = auth_client.post(f"{BASE_URL}/api/safety-assessment/{created_safety}/share-link", json={})
        assert r.status_code == 200
        assert r.json()["excluded"] == ["section_2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
