"""Tests for joint report PDF generation endpoint. Self-contained: builds its own
report each run (no shared fixtures), so it survives test-data cleanup."""
import io
import os
import pytest
import requests
from pypdf import PdfReader

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0]).rstrip("/")
ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]


def _register(name, email):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "name": name, "email": email, "password": "testpass123", "role": "parent",
    }, timeout=30)
    assert r.status_code in (200, 201), r.text
    return s


@pytest.fixture(scope="module")
def ready_report():
    sfx = os.urandom(4).hex()
    a = _register("Ann", f"TEST_pdfa_{sfx}@example.com")
    b = _register("Jordan", f"TEST_pdfb_{sfx}@example.com")
    inv = a.post(f"{BASE_URL}/api/joint/reports", json={
        "subject": "education", "child_name": "Sam",
        "co_parent_name": "Jordan", "co_parent_email": f"TEST_pdfb_{sfx}@example.com",
    }, timeout=30)
    assert inv.status_code in (200, 201), inv.text
    rid = inv.json()["id"]
    code = inv.json()["invitation"]["code"]
    acc = b.post(f"{BASE_URL}/api/joint/invitations/accept", json={"code": code}, timeout=30)
    assert acc.status_code == 200, acc.text
    for s, name in ((a, "Ann"), (b, "Jordan")):
        r = s.put(f"{BASE_URL}/api/joint/reports/{rid}/responses", json={
            "answers": {k: f"{name} believes Sam needs consistent school routines and calm handoffs between homes." for k in ANSWER_KEYS},
        }, timeout=30)
        assert r.status_code == 200, r.text
    return {"a": a, "b": b, "rid": rid}


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


class TestPdfDownload:
    def test_parent_a_gets_pdf(self, ready_report):
        r = ready_report["a"].get(f"{BASE_URL}/api/joint/reports/{ready_report['rid']}/pdf", timeout=60)
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
        assert "Ann" in text and "Jordan" in text

    def test_parent_b_gets_pdf(self, ready_report):
        r = ready_report["b"].get(f"{BASE_URL}/api/joint/reports/{ready_report['rid']}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 3000

    def test_unauthenticated_401(self, ready_report):
        r = requests.get(f"{BASE_URL}/api/joint/reports/{ready_report['rid']}/pdf", timeout=30)
        assert r.status_code == 401

    def test_non_participant_404(self, ready_report):
        s = _register("NP", f"TEST_nonpart_{os.urandom(4).hex()}@example.com")
        r = s.get(f"{BASE_URL}/api/joint/reports/{ready_report['rid']}/pdf", timeout=30)
        assert r.status_code == 404

    def test_incomplete_report_400(self):
        """Only Parent A completes - PDF should 400."""
        sfx = os.urandom(4).hex()
        s = _register("Solo", f"TEST_pdfsolo_{sfx}@example.com")
        inv = s.post(f"{BASE_URL}/api/joint/reports", json={
            "subject": "education", "child_name": "TestKid",
            "co_parent_name": "Test Coparent",
            "co_parent_email": f"TEST_incomplete_{sfx}@example.com",
        }, timeout=30)
        assert inv.status_code in (200, 201), inv.text
        rid = inv.json()["id"]
        r = s.get(f"{BASE_URL}/api/joint/reports/{rid}/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"


class TestCasePdf:
    """Server-generated PDF for the 10-page individual assessment report (incl. IPV/family violence)."""

    def _ipv_case(self):
        sfx = os.urandom(4).hex()
        s = _register("CasePDF", f"TEST_casepdf_{sfx}@example.com")
        c = s.post(f"{BASE_URL}/api/cases", json={
            "type": "ipv", "child_name": "PDFKid",
            "parent_a_name": "Ann", "parent_b_name": "Jordan",
        }, timeout=30)
        assert c.status_code in (200, 201), c.text
        cid = c.json()["id"]
        d = s.post(f"{BASE_URL}/api/cases/{cid}/demo", timeout=30)
        assert d.status_code == 200, d.text
        return s, cid

    def test_ipv_case_pdf_full_content(self):
        s, cid = self._ipv_case()
        r = s.get(f"{BASE_URL}/api/cases/{cid}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "alignment-report-pdfkid.pdf" in r.headers.get("content-disposition", "")
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"
        text = _pdf_text(r.content)
        for marker in ["SA CoParents", "Child: PDFKid", "Ann", "Jordan",
                       "Alignment Before Agreement", "Options", "Conversation"]:
            assert marker in text, f"missing marker: {marker!r}"

    def test_case_pdf_incomplete_400(self):
        sfx = os.urandom(4).hex()
        s = _register("CasePDFInc", f"TEST_casepdfinc_{sfx}@example.com")
        c = s.post(f"{BASE_URL}/api/cases", json={
            "type": "ipv", "child_name": "Kid", "parent_a_name": "A", "parent_b_name": "B",
        }, timeout=30)
        cid = c.json()["id"]
        r = s.get(f"{BASE_URL}/api/cases/{cid}/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}"

    def test_case_pdf_unauthenticated_401(self):
        r = requests.get(f"{BASE_URL}/api/cases/whatever/pdf", timeout=30)
        assert r.status_code in (401, 403)


class TestCompletePdf:
    """Server-generated PDF for the aggregated Complete Joint Alignment Report."""

    def test_complete_pdf_with_data(self):
        sfx = os.urandom(4).hex()
        s = _register("CompletePDF", f"TEST_completepdf_{sfx}@example.com")
        c = s.post(f"{BASE_URL}/api/cases", json={
            "type": "educational", "child_name": "Sam",
            "parent_a_name": "Ann", "parent_b_name": "Jordan",
        }, timeout=30)
        assert c.status_code in (200, 201), c.text
        d = s.post(f"{BASE_URL}/api/cases/{c.json()['id']}/demo", timeout=30)
        assert d.status_code == 200, d.text
        r = s.get(f"{BASE_URL}/api/reports/complete/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "complete-alignment-report.pdf" in r.headers.get("content-disposition", "")
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"
        text = _pdf_text(r.content)
        for marker in ["Complete Joint Alignment Report", "SA CoParents", "Child: Sam",
                       "Alignment Before Agreement", "Educational"]:
            assert marker in text, f"missing marker: {marker!r}"

    def test_complete_pdf_empty_400(self):
        sfx = os.urandom(4).hex()
        s = _register("CompleteEmpty", f"TEST_completeempty_{sfx}@example.com")
        r = s.get(f"{BASE_URL}/api/reports/complete/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}"

    def test_complete_pdf_unauthenticated_401(self):
        r = requests.get(f"{BASE_URL}/api/reports/complete/pdf", timeout=30)
        assert r.status_code in (401, 403)
