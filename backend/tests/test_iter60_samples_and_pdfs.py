"""Iter-60: Sample Legal Lens PDF restyled, Sample Co-Parenting Agreement (new), Section 7 success_indicators, static template regression."""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
except Exception:
    pass
import io
import re
import requests
import pymupdf
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN = ("mattsossi@bsossi.com", "CoParents2026!")
PRO = ("approval.test.pro1@gmail.com", "TestPass2026!")


def _extract_text(pdf_bytes: bytes):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages = [p.get_text() for p in doc]
    return pages, "\n".join(pages)


# ---- Sample Legal Lens PDF ----
class TestSampleLegalLensPDF:
    def test_pdf_200_and_content(self):
        r = requests.get(f"{BASE}/api/joint/sample-legal-lens/pdf", timeout=60)
        assert r.status_code == 200, r.text[:500]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        pages, text = _extract_text(r.content)
        assert len(pages) >= 2
        expected = [
            "Case & Assessment Snapshot",
            "Current Alignment Levels",
            "Safety Status",
            "2. Individual Parent Perspectives",
            "Next developmental goal",
            "3. Joint Co-Parenting Assessment",
            "4. Child-Focused Issues",
            "5. Options & Resources",
            "6. Conflict-Resolution Pathway",
            "SELECTED",
            "Safety Override",
            "7. Professional Observation & Action Plan",
            "90-Day Action Plan",
            "Fewer transition disputes",
            "8. Concise Court / Referral Summary",
            "Professional Certification",
        ]
        missing = [e for e in expected if e not in text]
        assert not missing, f"Missing strings in Legal Lens PDF: {missing}"

    def test_brand_header_on_every_page(self):
        r = requests.get(f"{BASE}/api/joint/sample-legal-lens/pdf", timeout=60)
        pages, _ = _extract_text(r.content)
        brand = "Starting With Alignment, Ending With Agreement"
        missing_pages = [i for i, p in enumerate(pages) if brand not in p]
        assert not missing_pages, f"Brand header missing on pages: {missing_pages}"


# ---- Sample Co-Parenting Agreement (JSON + PDF) ----
class TestSampleAgreement:
    def test_json_structure(self):
        r = requests.get(f"{BASE}/api/joint/sample-agreement", timeout=30)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert data.get("report_title") == "SA CoParents Co-Parenting Agreement", data.get("report_title")
        sections = data.get("sections") or []
        assert len(sections) == 10, f"Expected 10 sections, got {len(sections)}"
        summary = data.get("summary") or {}
        for k in ("alignment", "specific", "resolution"):
            assert k in summary and isinstance(summary[k], list), f"summary.{k} missing/list"

    def test_pdf_200_content_and_headers(self):
        r = requests.get(f"{BASE}/api/joint/sample-agreement/pdf", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert len(r.content) > 20_000, f"PDF too small: {len(r.content)} bytes"
        pages, text = _extract_text(r.content)
        for s in ["At a Glance", "Agreement Sections", "Signatures", "Alignment Before Agreement"]:
            assert s in text, f"Missing '{s}' in agreement PDF"
        brand = "Starting With Alignment, Ending With Agreement"
        missing_pages = [i for i, p in enumerate(pages) if brand not in p]
        assert not missing_pages, f"Brand header missing on pages: {missing_pages}"

    def test_pdf_inline_disposition(self):
        r = requests.get(f"{BASE}/api/joint/sample-agreement/pdf?inline=1", timeout=60)
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "").lower()
        assert "inline" in cd, f"Expected inline disposition, got: {cd}"


# ---- Static template regression ----
class TestStaticTemplate:
    def test_v8_static(self):
        r = requests.get(f"{BASE}/legal-lens-report-to-court-v8.html", timeout=30)
        assert r.status_code == 200, r.status_code
        html = r.text
        assert "Starting With Alignment, Ending With Agreement" in html
        cnt_dq = html.count('class="page"')
        cnt_sq = html.count("class='page'")
        assert cnt_dq >= 6 or cnt_sq >= 6, f"Expected 6 .page sections, got dq={cnt_dq} sq={cnt_sq}"


# ---- Professional login + case report success_indicators ----
class TestProfessionalReportSuccessIndicators:
    @pytest.fixture(scope="class")
    def pro_session(self):
        s = requests.Session()
        r = s.post(f"{BASE}/api/auth/login", json={"email": PRO[0], "password": PRO[1]}, timeout=30)
        if r.status_code != 200:
            pytest.skip(f"Pro login failed: {r.status_code} {r.text[:200]}")
        return s

    def test_list_cases_and_pdf(self, pro_session):
        # Find an existing case for this pro
        r = pro_session.get(f"{BASE}/api/professional-report/cases", timeout=30)
        if r.status_code != 200:
            pytest.skip(f"list cases: {r.status_code} {r.text[:200]}")
        cases = r.json() if isinstance(r.json(), list) else r.json().get("cases", [])
        if not cases:
            pytest.skip("No cases for this professional")
        rid = cases[0].get("id") or cases[0].get("ref_id") or cases[0].get("case_id")
        assert rid, f"No case id in {cases[0]}"

        # Save success_indicators
        payload = {"fields": {"success_indicators": "Fewer transition disputes; on-time exchanges; child sleeping through night."}}
        rr = pro_session.put(f"{BASE}/api/cases/{rid}/professional-report", json=payload, timeout=30)
        assert rr.status_code == 200, f"PUT failed: {rr.status_code} {rr.text[:300]}"

        r3 = pro_session.get(f"{BASE}/api/cases/{rid}/professional-report", timeout=30)
        assert r3.status_code == 200
        body = r3.json()
        found = body.get("success_indicators") or (body.get("report") or {}).get("success_indicators") or (body.get("fields") or {}).get("success_indicators")
        assert found and "transition disputes" in found, f"success_indicators not persisted: keys={list(body.keys())}"

        # Regression: professional-report/pdf works
        r4 = pro_session.get(f"{BASE}/api/cases/{rid}/professional-report/pdf", timeout=60)
        assert r4.status_code == 200, r4.text[:300]
        assert r4.headers.get("content-type", "").startswith("application/pdf")
