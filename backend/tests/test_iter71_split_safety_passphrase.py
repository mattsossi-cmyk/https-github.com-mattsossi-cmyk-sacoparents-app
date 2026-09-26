"""Iter71 backend tests — Passphrase + TTL on Share endpoint,
plus regression on foundation/legal/weekly share (no-gate) and direct PDF endpoints.
"""
import os
import re
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _health_index():
    return {"s1": 7, "s2": 6, "s3": 5}


def _legal_payload():
    return {
        "health_index": _health_index(),
        "foundation_text": "Our shared foundation focuses on the child.",
        "signatures": {"sigA": "Alice A", "sigB": "Bob B", "sigMed": "Matt Sossi"},
        "case_ref": "ALIGN-SA-2026",
    }


def _foundation_payload():
    return {"foundation_text": "Our foundation statement.", "case_ref": "ALIGN-SA-2026"}


def _weekly_payload():
    return {
        "health_index": _health_index(),
        "biff_logs": [],
        "milestones": [],
        "reassessments": [],
        "foundation_text": "Foundation for weekly.",
        "case_ref": "ALIGN-SA-2026",
    }


# --- Passphrase + TTL flow ---
class TestShareLegalPassphraseTTL:
    def test_share_legal_with_passphrase_and_ttl7(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "legal",
            "payload": _legal_payload(),
            "passphrase": "test123",
            "ttl_days": 7,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["requires_passphrase"] is True
        assert data["ttl_days"] == 7
        assert "url" in data and data["url"].endswith(".pdf")
        share_id = data["share_id"]

        # (a) No passphrase -> HTML gate 200
        r_no = requests.get(f"{API}/portal/share/{share_id}.pdf")
        assert r_no.status_code == 200
        assert "text/html" in r_no.headers.get("content-type", "")
        assert "Enter passphrase" in r_no.text or "Passphrase required" in r_no.text

        # (b) Wrong passphrase -> HTML with error
        r_wrong = requests.get(f"{API}/portal/share/{share_id}.pdf", params={"p": "wrongp"})
        assert r_wrong.status_code == 200
        assert "text/html" in r_wrong.headers.get("content-type", "")
        assert "did not match" in r_wrong.text

        # (c) Correct passphrase -> application/pdf
        r_ok = requests.get(f"{API}/portal/share/{share_id}.pdf", params={"p": "test123"})
        assert r_ok.status_code == 200
        assert r_ok.headers.get("content-type", "").startswith("application/pdf")
        assert r_ok.content[:4] == b"%PDF"

    def test_share_legal_ttl30_default(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "legal",
            "payload": _legal_payload(),
            "passphrase": "abc",
            "ttl_days": 30,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ttl_days"] == 30
        assert data["requires_passphrase"] is True

    def test_share_legal_no_passphrase_no_gate(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "legal",
            "payload": _legal_payload(),
        })
        assert r.status_code == 200
        data = r.json()
        assert data["requires_passphrase"] is False
        share_id = data["share_id"]
        r_pdf = requests.get(f"{API}/portal/share/{share_id}.pdf")
        assert r_pdf.status_code == 200
        assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
        assert r_pdf.content[:4] == b"%PDF"


# --- Regression: foundation/weekly share (no gate ever) ---
class TestShareFoundationWeeklyNoGate:
    def test_share_foundation_direct_pdf(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "foundation",
            "payload": _foundation_payload(),
        })
        assert r.status_code == 200
        share_id = r.json()["share_id"]
        r_pdf = requests.get(f"{API}/portal/share/{share_id}.pdf")
        assert r_pdf.status_code == 200
        assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
        assert r_pdf.content[:4] == b"%PDF"

    def test_share_weekly_direct_pdf(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "weekly",
            "payload": _weekly_payload(),
        })
        assert r.status_code == 200
        share_id = r.json()["share_id"]
        r_pdf = requests.get(f"{API}/portal/share/{share_id}.pdf")
        assert r_pdf.status_code == 200
        assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
        assert r_pdf.content[:4] == b"%PDF"


# --- Regression: direct PDF endpoints ---
class TestDirectPdfEndpoints:
    def test_foundation_pdf(self):
        r = requests.post(f"{API}/portal/foundation-pdf", json=_foundation_payload())
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_legal_report_pdf(self):
        r = requests.post(f"{API}/portal/legal-report-pdf", json=_legal_payload())
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_weekly_progress_pdf(self):
        r = requests.post(f"{API}/portal/weekly-progress-pdf", json=_weekly_payload())
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"


# --- Court key verify ---
class TestCourtKeyVerify:
    def test_verify_align_sa_2026(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "ALIGN-SA-2026"})
        assert r.status_code == 200
        data = r.json()
        assert data["verified"] is True
        assert data["case_id"] == "ALIGN-SA-2026"

    def test_verify_unknown_key(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "NOT-A-REAL-KEY-9999"})
        assert r.status_code == 200
        assert r.json()["verified"] is False


# --- Passphrase field constraints ---
class TestShareValidation:
    def test_passphrase_too_long_rejected(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "legal",
            "payload": _legal_payload(),
            "passphrase": "x" * 41,
        })
        assert r.status_code == 422

    def test_ttl_days_out_of_range(self):
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "legal",
            "payload": _legal_payload(),
            "ttl_days": 100,
        })
        assert r.status_code == 422

    def test_ttl_days_non_allowed_falls_back_to_30(self):
        # ttl_days=15 is inside 1..90 but not in _ALLOWED_TTL_DAYS -> falls back to 30
        r = requests.post(f"{API}/portal/share", json={
            "artefact_type": "legal",
            "payload": _legal_payload(),
            "ttl_days": 15,
        })
        assert r.status_code == 200
        assert r.json()["ttl_days"] == 30
