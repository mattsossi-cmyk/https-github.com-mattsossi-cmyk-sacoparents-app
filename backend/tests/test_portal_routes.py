"""Backend tests for /api/portal/* endpoints (iteration 68)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

from ai_ready import ai_headers  # noqa: E402

_AI = {}


def _ai():
    """Signed in with the AI notice accepted (AI endpoints need both)."""
    if not _AI:
        _AI.update(ai_headers(f"{BASE_URL}/api"))
    return _AI

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed: {r.status_code} {r.text[:200]}")
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Court key verify ----
class TestCourtKeys:
    def test_valid_key_align(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "ALIGN-SA-2026"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["verified"] is True
        assert d["case_id"] == "ALIGN-SA-2026"
        assert "Matt Sossi" in d["mediator_name"]

    def test_valid_key_court8842(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "COURT-8842"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["verified"] is True
        assert d["case_id"] == "COURT-8842"

    def test_unknown_key(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "BOGUS-0000"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["verified"] is False
        assert d.get("reason") == "unknown_key"


# ---- BIFF refine ----
class TestBiffRefine:
    def test_refine_escalated(self):
        r = requests.post(
            f"{API}/portal/biff-refine", headers=_ai(),
            json={"raw": "You were late again! You have zero respect."},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("biff"), str) and len(d["biff"]) > 0
        assert isinstance(d.get("flags"), list)
        assert d.get("risk") in {"Escalation Flag", "Low Risk"}
        # ensure not the fallback template
        assert not d["biff"].startswith("Thank you for your message. You are always")


# ---- Foundation PDF ----
class TestFoundationPdf:
    def test_valid(self):
        r = requests.post(
            f"{API}/portal/foundation-pdf",
            json={"foundation_text": "We put our child first.", "case_ref": "TEST-CASE"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 500

    def test_empty_foundation(self):
        r = requests.post(f"{API}/portal/foundation-pdf", json={"foundation_text": ""}, timeout=30)
        # Pydantic min_length=1 → 422 OR our 400
        assert r.status_code in (400, 422)


# ---- Legal report PDF ----
class TestLegalReportPdf:
    def test_valid(self):
        r = requests.post(
            f"{API}/portal/legal-report-pdf",
            json={
                "health_index": {"s1": 7, "s2": 6, "s3": 5},
                "foundation_text": "Anchor.",
                "signatures": {"sigA": "Alice", "sigB": "Bob", "sigMed": "Matt Sossi"},
                "case_ref": "TEST",
            },
            timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_out_of_range(self):
        r = requests.post(
            f"{API}/portal/legal-report-pdf",
            json={"health_index": {"s1": 11, "s2": 6, "s3": 5}},
            timeout=30,
        )
        assert r.status_code == 400, r.text


# ---- Portal state ----
class TestPortalState:
    def test_state_requires_auth(self):
        r = requests.get(f"{API}/portal/state", timeout=30)
        assert r.status_code == 401

    def test_get_state_authenticated(self, auth_headers):
        r = requests.get(f"{API}/portal/state", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "exists" in d and "state" in d

    def test_put_then_get_state(self, auth_headers):
        payload = {
            "align_records": [{"date": "2026-01-01", "note": "x"}],
            "milestones": [{"date": "2026-01-02", "note": "y"}],
            "biff_logs": [{"raw": "hi", "biff": "hello"}],
            "foundation_text": "hello",
            "legal_report": {"sigA": "A", "sigB": "B", "sigMed": "M"},
            "health_index": {"s1": 8, "s2": 7, "s3": 6},
            "court_key": "ALIGN-SA-2026",
            "reassessments": [{"date": "2026-01-05"}],
        }
        r = requests.put(f"{API}/portal/state", headers=auth_headers, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        g = requests.get(f"{API}/portal/state", headers=auth_headers, timeout=30)
        assert g.status_code == 200
        d = g.json()
        assert d["exists"] is True
        s = d["state"]
        assert s["foundation_text"] == "hello"
        assert s["health_index"] == {"s1": 8, "s2": 7, "s3": 6}
        assert s["court_key"] == "ALIGN-SA-2026"

    def test_put_clamps_and_truncates(self, auth_headers):
        payload = {
            "align_records": [{"i": i} for i in range(600)],
            "reassessments": [{"i": i} for i in range(300)],
            "biff_logs": [],
            "milestones": [],
            "foundation_text": "clamped",
            "legal_report": {"sigA": "a", "sigB": "b", "sigMed": "m"},
            "health_index": {"s1": 11, "s2": -5, "s3": 5},
            "court_key": "",
        }
        r = requests.put(f"{API}/portal/state", headers=auth_headers, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        g = requests.get(f"{API}/portal/state", headers=auth_headers, timeout=30).json()
        s = g["state"]
        assert s["align_records"] == []  # child record folders are off: never stored
        assert len(s["reassessments"]) == 200
        assert s["health_index"]["s1"] == 10
        assert s["health_index"]["s2"] == 1
