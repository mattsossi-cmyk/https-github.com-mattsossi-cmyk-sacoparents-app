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
