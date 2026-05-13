"""Tests for the new Email-to-Mediator feature.

Backend env intentionally has SMTP_PASSWORD blank, so /email/status must
return {configured: false} and the actual send must return 503.
"""
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


# ============ /email/status ============
class TestEmailStatus:
    def test_status_returns_not_configured(self, auth_client):
        r = auth_client.get(f"{BASE_URL}/api/mediation/email/status", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "configured" in body
        # SMTP_PASSWORD is intentionally blank → must be False
        assert body["configured"] is False

    def test_status_requires_auth(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/mediation/email/status", timeout=15)
        assert r.status_code == 401


# ============ POST /email-mediator validations ============
class TestEmailMediatorValidation:
    def test_unauthenticated(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/mediation/email-mediator",
            json={"mediator_email": "med@x.com", "summary_id": "sum_x"},
            timeout=15,
        )
        assert r.status_code == 401

    def test_invalid_email_returns_422(self, auth_client):
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/email-mediator",
            json={"mediator_email": "not-an-email", "summary_id": "sum_x"},
            timeout=15,
        )
        assert r.status_code == 422

    def test_no_docs_returns_400(self, auth_client):
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/email-mediator",
            json={"mediator_email": "mediator@example.com"},
            timeout=15,
        )
        assert r.status_code == 400
        assert "document" in r.json().get("detail", "").lower()

    def test_bogus_summary_id_returns_404(self, auth_client):
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/email-mediator",
            json={
                "mediator_email": "mediator@example.com",
                "summary_id": "sum_doesnotexist",
            },
            timeout=15,
        )
        assert r.status_code == 404

    def test_bogus_agreement_id_returns_404(self, auth_client):
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/email-mediator",
            json={
                "mediator_email": "mediator@example.com",
                "agreement_id": "agr_doesnotexist",
            },
            timeout=15,
        )
        assert r.status_code == 404


# ============ End-to-end with real summary → expects 503 not_configured ============
class TestEmailNotConfiguredPath:
    def test_valid_summary_returns_503_when_smtp_blank(self, auth_client):
        # Ensure prep exists then generate a real summary
        auth_client.put(
            f"{BASE_URL}/api/mediation/child-goals",
            json={
                "selected_goals": ["safety"],
                "consistency_text": "x",
                "feel_text": "y",
                "strength_text": "z",
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
        r = auth_client.post(
            f"{BASE_URL}/api/mediation/summary", json={}, timeout=120
        )
        assert r.status_code == 200, r.text
        summary_id = r.json()["summary_id"]

        # Now attempt to email — SMTP is intentionally not configured
        r2 = auth_client.post(
            f"{BASE_URL}/api/mediation/email-mediator",
            json={
                "mediator_email": "mediator@example.com",
                "mediator_name": "Dr. Mediator",
                "summary_id": summary_id,
            },
            timeout=30,
        )
        assert r2.status_code == 503, r2.text
        detail = r2.json().get("detail", "")
        assert "not configured" in detail.lower()
