"""Tests for joint report PDF generation endpoint."""
import io
import os
import pytest
import requests
from pypdf import PdfReader

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0]).rstrip("/")
REPORT_ID = "51e696e1-8dfb-43b3-9735-affcf2ecf33e"
PARENT_A = {"email": "pdfa_1788368801@example.com", "password": "testpass123"}
PARENT_B = {"email": "pdfb_1788368801@example.com", "password": "testpass123"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


class TestPdfDownload:
    def test_parent_a_gets_pdf(self):
        s = _login(PARENT_A)
        r = s.get(f"{BASE_URL}/api/joint/reports/{REPORT_ID}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"
        text = _pdf_text(r.content)
        for marker in [
            "Joint Parenting Alignment Report",
            "Child: Sam",
            "School / Education",
            "Purpose of This Report",
            "Alignment Map",
            "Options and Resources",
            "Alignment Before Agreement",
        ]:
            assert marker in text, f"missing marker: {marker!r}"
        # participants Ann / Jordan (in either order)
        assert "Ann" in text and "Jordan" in text

    def test_parent_b_gets_pdf(self):
        s = _login(PARENT_B)
        r = s.get(f"{BASE_URL}/api/joint/reports/{REPORT_ID}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 3000

    def test_unauthenticated_401(self):
        r = requests.get(f"{BASE_URL}/api/joint/reports/{REPORT_ID}/pdf", timeout=30)
        assert r.status_code == 401

    def test_non_participant_404(self):
        # register a random non-participant
        s = requests.Session()
        email = f"TEST_nonpart_{os.urandom(4).hex()}@example.com"
        reg = s.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "testpass123", "name": "NP"
        }, timeout=30)
        assert reg.status_code in (200, 201), reg.text
        r = s.get(f"{BASE_URL}/api/joint/reports/{REPORT_ID}/pdf", timeout=30)
        assert r.status_code == 404

    def test_incomplete_report_400(self):
        """Create a fresh joint report where only Parent A completes - PDF should 400."""
        s = _login(PARENT_A)
        cfg = s.get(f"{BASE_URL}/api/joint/config", timeout=30)
        if cfg.status_code != 200:
            pytest.skip("no joint config")
        subjects = cfg.json().get("subjects", [])
        subject = next((x["key"] for x in subjects if x["key"] != "custom"), None)
        if not subject:
            pytest.skip("no subjects")
        other_email = f"TEST_incomplete_{os.urandom(4).hex()}@example.com"
        inv = s.post(f"{BASE_URL}/api/joint/reports", json={
            "subject": subject,
            "child_name": "TestKid",
            "co_parent_name": "Test Coparent",
            "co_parent_email": other_email,
        }, timeout=30)
        assert inv.status_code in (200, 201), inv.text
        rid = inv.json().get("id") or inv.json().get("report_id")
        assert rid, f"no report id: {inv.json()}"
        r = s.get(f"{BASE_URL}/api/joint/reports/{rid}/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
