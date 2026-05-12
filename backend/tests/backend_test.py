"""End-to-end backend tests for SA Coparents Mediation Prep app."""
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


# ============ Health ============
class TestHealth:
    def test_health_ok(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_root_ok(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


# ============ Auth ============
class TestAuth:
    def test_register_login_me(self, api_client):
        email = f"TEST_auth_{uuid.uuid4().hex[:8]}@test.com".lower()
        # Register
        r = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "name": "Auth Test"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data and data["access_token"]
        assert data["user"]["email"] == email
        assert data["user"]["auth_method"] == "jwt"

        # Duplicate
        r2 = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "name": "Dup"},
            timeout=15,
        )
        assert r2.status_code == 400

        # Login
        r3 = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": "TestPass123!"},
            timeout=15,
        )
        assert r3.status_code == 200
        token = r3.json()["access_token"]

        # Login wrong password
        r4 = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": "WrongPass1!"},
            timeout=15,
        )
        assert r4.status_code == 401

        # /me with bearer
        r5 = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r5.status_code == 200
        assert r5.json()["email"] == email

    def test_me_unauthorized(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_profile_update(self, auth_client, test_user):
        r = auth_client.patch(
            f"{BASE_URL}/api/auth/profile",
            json={"name": "Updated Parent", "custody_situation": "Weekend"},
            timeout=15,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Updated Parent"
        assert body["custody_situation"] == "Weekend"

        # GET /me to confirm persistence
        r2 = auth_client.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["name"] == "Updated Parent"

    def test_logout(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ============ Mediation Save/Load ============
class TestMediationSave:
    def test_child_goals_save_and_prep(self, auth_client):
        payload = {
            "selected_goals": ["safety", "stability"],
            "consistency_text": "predictable routines",
            "feel_text": "loved and safe",
            "strength_text": "honest communication",
            "priority_order": ["safety", "stability"],
        }
        r = auth_client.put(f"{BASE_URL}/api/mediation/child-goals", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        r2 = auth_client.get(f"{BASE_URL}/api/mediation/prep", timeout=15)
        assert r2.status_code == 200
        prep = r2.json()
        assert prep["child_goals"]["selected_goals"] == ["safety", "stability"]
        assert prep["completed"]["child_goals"] is True

    def test_issues_save(self, auth_client):
        payload = {
            "parenting_schedule": {"weekday": "alternating"},
            "communication": {"channel": "app only"},
            "child_needs": {"school": "Need consistent pickup"},
            "financial": {"medical": "split 50/50"},
            "household_rules": {"screens": "1 hour max"},
            "safety_concerns": "none",
        }
        r = auth_client.put(f"{BASE_URL}/api/mediation/issues", json=payload, timeout=15)
        assert r.status_code == 200
        r2 = auth_client.get(f"{BASE_URL}/api/mediation/prep", timeout=15)
        assert r2.json()["issues"]["safety_concerns"] == "none"

    def test_priority_save(self, auth_client):
        payload = {
            "items": [
                {"id": "i1", "label": "Pickup times", "bucket": "urgent"},
                {"id": "i2", "label": "Holidays", "bucket": "compromise"},
            ]
        }
        r = auth_client.put(f"{BASE_URL}/api/mediation/priority", json=payload, timeout=15)
        assert r.status_code == 200
        r2 = auth_client.get(f"{BASE_URL}/api/mediation/prep", timeout=15)
        assert len(r2.json()["priority"]["items"]) == 2

    def test_comm_style_save(self, auth_client):
        payload = {
            "answers": {"q1": "a", "q2": "b", "q3": "c"},
            "free_text_sample": "I feel concerned about pickup times.",
        }
        r = auth_client.put(f"{BASE_URL}/api/mediation/comm-style", json=payload, timeout=15)
        assert r.status_code == 200

    def test_readiness_save(self, auth_client):
        payload = {"answers": {"q1": 4, "q2": 3, "q3": 5, "q4": 4, "q5": 4}}
        r = auth_client.put(f"{BASE_URL}/api/mediation/readiness", json=payload, timeout=15)
        assert r.status_code == 200
        r2 = auth_client.get(f"{BASE_URL}/api/mediation/prep", timeout=15)
        assert r2.json()["completed"]["readiness"] is True


# ============ Resources (no auth required) ============
class TestResources:
    def test_resources_listed(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/mediation/resources", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) == 6
        assert all("id" in i and "category" in i and "title" in i for i in items)


# ============ AI endpoints (real Claude Sonnet 4.5) ============
class TestAI:
    def test_analyze_communication(self, auth_client):
        body = {
            "text": "I'm worried about pickup consistency. Last week you were 45 min late twice.",
            "answers": {"q1": "calm", "q2": "direct", "q3": "concerned"},
        }
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/analyze-communication", json=body, timeout=60
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["style_label", "summary", "strengths", "growth_areas", "suggestions", "score"]:
            assert k in data, f"missing field {k} in {data}"
        assert isinstance(data["strengths"], list)
        assert isinstance(data["score"], int)

    def test_summary_and_pdf(self, auth_client):
        # Ensure prep has at least child_goals + issues + priority + readiness
        auth_client.put(
            f"{BASE_URL}/api/mediation/child-goals",
            json={
                "selected_goals": ["safety", "stability"],
                "consistency_text": "predictable",
                "feel_text": "loved",
                "strength_text": "honest",
                "priority_order": ["safety"],
            },
            timeout=15,
        )
        auth_client.put(
            f"{BASE_URL}/api/mediation/issues",
            json={
                "parenting_schedule": {"weekday": "alt"},
                "communication": {"channel": "app"},
                "child_needs": {"school": "pickup"},
                "financial": {"med": "50/50"},
                "household_rules": {"screens": "1h"},
                "safety_concerns": "",
            },
            timeout=15,
        )
        auth_client.put(
            f"{BASE_URL}/api/mediation/readiness",
            json={"answers": {"q1": 4, "q2": 3, "q3": 5}},
            timeout=15,
        )

        r = auth_client.post(f"{BASE_URL}/api/mediation/summary", json={}, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in [
            "summary_id",
            "child_goals_summary",
            "top_concerns",
            "priority_agenda",
            "flexibility_areas",
            "communication_goals",
            "notes_for_mediator",
            "readiness_label",
            "readiness_score",
        ]:
            assert k in data, f"missing {k} in {data}"
        summary_id = data["summary_id"]

        # List summaries
        r2 = auth_client.get(f"{BASE_URL}/api/mediation/summaries", timeout=15)
        assert r2.status_code == 200
        summaries = r2.json()
        assert any(s["summary_id"] == summary_id for s in summaries)

        # PDF download
        r3 = auth_client.get(
            f"{BASE_URL}/api/mediation/summary/{summary_id}/pdf", timeout=30
        )
        assert r3.status_code == 200
        ct = r3.headers.get("content-type", "")
        assert "application/pdf" in ct, f"got content-type {ct}"
        assert r3.content[:4] == b"%PDF", "response not a PDF"

    def test_summary_requires_prep(self, api_client):
        """User with no prep should be blocked."""
        email = f"TEST_empty_{uuid.uuid4().hex[:8]}@test.com"
        reg = api_client.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": "TestPass123!", "name": "Empty"},
            timeout=20,
        )
        token = reg.json()["access_token"]
        r = api_client.post(
            f"{BASE_URL}/api/mediation/summary",
            json={},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 400
