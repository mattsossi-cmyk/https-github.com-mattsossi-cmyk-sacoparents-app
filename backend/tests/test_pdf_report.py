"""Tests for joint report PDF generation endpoint (professional-initiated model).
Self-contained: builds its own report each run via a professional case."""
import io
import os
import uuid
import pytest
import requests
from pypdf import PdfReader

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0]).rstrip("/")
API = f"{BASE_URL}/api"
ANSWER_KEYS = ["needs_most", "working_well", "concerns", "improve", "options", "other_parent"]


def _pro() -> requests.Session:
    return new_user(API, "professional", "Pro")


def _register(name: str, email: str) -> requests.Session:
    return new_user(API, "professional", name, email=email)


@pytest.fixture(scope="module")
def ready_report() -> dict:
    sfx = os.urandom(4).hex()
    pro = _pro()
    ea, eb = f"TEST_pdfa_{sfx}@example.com", f"TEST_pdfb_{sfx}@example.com"
    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "education", "child_name": "Sam",
        "parent_a_name": "Ann", "parent_a_email": ea,
        "parent_b_name": "Jordan", "parent_b_email": eb,
    }, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in d["invitations"]}
    a = new_user(API, "parent", "Ann", email=ea, invite=toks["a"])
    b = new_user(API, "parent", "Jordan", email=eb, invite=toks["b"])
    for s, tok in ((a, toks["a"]), (b, toks["b"])):
        assert s.post(f"{API}/joint/invitations/accept", json={"code": tok}, timeout=30).status_code == 200
    rid = d["id"]
    for s, name in ((a, "Ann"), (b, "Jordan")):
        r = s.put(f"{API}/joint/reports/{rid}/responses", json={
            "answers": {k: f"{name} believes Sam needs consistent school routines and calm handoffs between homes." for k in ANSWER_KEYS},
        }, timeout=30)
        assert r.status_code == 200, r.text
    return {"pro": pro, "a": a, "b": b, "rid": rid}


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


class TestPdfDownload:
    def test_parent_a_gets_pdf(self, ready_report: dict) -> None:
        r = ready_report["a"].get(f"{API}/joint/reports/{ready_report['rid']}/pdf", timeout=60)
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

    def test_parent_b_gets_pdf(self, ready_report: dict) -> None:
        r = ready_report["b"].get(f"{API}/joint/reports/{ready_report['rid']}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 3000

    def test_professional_gets_pdf(self, ready_report: dict) -> None:
        r = ready_report["pro"].get(f"{API}/joint/reports/{ready_report['rid']}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")

    def test_unauthenticated_401(self, ready_report: dict) -> None:
        r = requests.get(f"{API}/joint/reports/{ready_report['rid']}/pdf", timeout=30)
        assert r.status_code == 401

    def test_non_participant_404(self, ready_report: dict) -> None:
        s = _register("NP", f"TEST_nonpart_{os.urandom(4).hex()}@example.com")
        r = s.get(f"{API}/joint/reports/{ready_report['rid']}/pdf", timeout=30)
        assert r.status_code == 404

    def test_incomplete_report_400(self) -> None:
        pro = _pro()
        r = pro.post(f"{API}/joint/reports/professional", json={
            "subject": "education", "child_name": "TestKid",
            "parent_a_name": "A", "parent_a_email": f"TEST_inca_{uuid.uuid4().hex[:6]}@example.com",
            "parent_b_name": "B", "parent_b_email": f"TEST_incb_{uuid.uuid4().hex[:6]}@example.com",
        }, timeout=30)
        rid = r.json()["id"]
        r = pro.get(f"{API}/joint/reports/{rid}/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"


class TestCasePdf:
    """Server-generated PDF for the 10-page individual assessment report (incl. IPV/family violence)."""

    def _ipv_case(self) -> tuple:
        sfx = os.urandom(4).hex()
        s = _register("CasePDF", f"TEST_casepdf_{sfx}@example.com")
        c = s.post(f"{API}/cases", json={
            "type": "ipv", "child_name": "PDFKid",
            "parent_a_name": "Ann", "parent_b_name": "Jordan",
        }, timeout=30)
        assert c.status_code in (200, 201), c.text
        cid = c.json()["id"]
        d = s.post(f"{API}/cases/{cid}/demo", timeout=30)
        assert d.status_code == 200, d.text
        return s, cid

    def test_ipv_case_pdf_full_content(self) -> None:
        s, cid = self._ipv_case()
        r = s.get(f"{API}/cases/{cid}/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "alignment-report-pdfkid.pdf" in r.headers.get("content-disposition", "")
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"
        text = _pdf_text(r.content)
        for marker in ["SA CoParents", "Child: PDFKid", "Ann", "Jordan",
                       "Alignment Before Agreement", "Options", "Conversation"]:
            assert marker in text, f"missing marker: {marker!r}"

    def test_case_pdf_incomplete_400(self) -> None:
        sfx = os.urandom(4).hex()
        s = _register("CasePDFInc", f"TEST_casepdfinc_{sfx}@example.com")
        c = s.post(f"{API}/cases", json={
            "type": "ipv", "child_name": "Kid", "parent_a_name": "A", "parent_b_name": "B",
        }, timeout=30)
        cid = c.json()["id"]
        r = s.get(f"{API}/cases/{cid}/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}"

    def test_case_pdf_unauthenticated_401(self) -> None:
        r = requests.get(f"{API}/cases/whatever/pdf", timeout=30)
        assert r.status_code in (401, 403)


class TestCompletePdf:
    """Server-generated PDF for the aggregated Complete Joint Alignment Report."""

    def test_complete_pdf_with_data(self) -> None:
        sfx = os.urandom(4).hex()
        s = _register("CompletePDF", f"TEST_completepdf_{sfx}@example.com")
        c = s.post(f"{API}/cases", json={
            "type": "educational", "child_name": "Sam",
            "parent_a_name": "Ann", "parent_b_name": "Jordan",
        }, timeout=30)
        assert c.status_code in (200, 201), c.text
        d = s.post(f"{API}/cases/{c.json()['id']}/demo", timeout=30)
        assert d.status_code == 200, d.text
        r = s.get(f"{API}/reports/complete/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "complete-alignment-report.pdf" in r.headers.get("content-disposition", "")
        assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"
        text = _pdf_text(r.content)
        for marker in ["Complete Joint Alignment Report", "SA CoParents", "Child: Sam",
                       "Alignment Before Agreement", "Educational"]:
            assert marker in text, f"missing marker: {marker!r}"

    def test_complete_pdf_empty_400(self) -> None:
        sfx = os.urandom(4).hex()
        s = _register("CompleteEmpty", f"TEST_completeempty_{sfx}@example.com")
        r = s.get(f"{API}/reports/complete/pdf", timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}"

    def test_complete_pdf_unauthenticated_401(self) -> None:
        r = requests.get(f"{API}/reports/complete/pdf", timeout=30)
        assert r.status_code in (401, 403)
