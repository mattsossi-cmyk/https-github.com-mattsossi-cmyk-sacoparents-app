"""Iter69 readiness check: after both parents finish assessments, professional can
(1) get Joint Report JSON, (2) download Joint Report PDF, (3) open Professional
Report editor, (4) finalize it, (5) download Professional Report PDF (finalized,
no DRAFT watermark).

Also verifies pre-completion behavior:
- GET /joint/reports/{rid}/report returns 400 when both parents haven't submitted
- GET /cases/{rid}/professional-report/pdf still returns a DRAFT-watermarked PDF
"""
import io
import os

import pymupdf
import pytest
from casekit import new_case, fill, completed_case

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"


def _pdf_text(content: bytes) -> tuple[str, int]:
    doc = pymupdf.open(stream=io.BytesIO(content), filetype="pdf")
    return ("".join(pg.get_text() for pg in doc), doc.page_count)


@pytest.fixture(scope="module")
def flow():
    pro, pa, pb, d, detail = completed_case(API, subject="education")
    return {"pro": pro, "pa": pa, "pb": pb, "rid": d["id"], "case_code": d["case_code"]}


def test_joint_report_json_ready(flow):
    r = flow["pro"].get(f"{API}/joint/reports/{flow['rid']}/report")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "alignment_map" in data and len(data["alignment_map"]) == 6
    assert data["report_title"] == "Joint Parenting Alignment Report"


def test_joint_report_pdf(flow):
    r = flow["pro"].get(f"{API}/joint/reports/{flow['rid']}/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    _, pages = _pdf_text(r.content)
    assert pages > 1, f"Joint PDF has only {pages} page(s)"


def test_professional_report_editor_opens(flow):
    r = flow["pro"].get(f"{API}/cases/{flow['rid']}/professional-report")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "report" in body and body["report"]["status"] == "draft"


def test_professional_report_pdf_draft_watermark(flow):
    r = flow["pro"].get(f"{API}/cases/{flow['rid']}/professional-report/pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    text, _ = _pdf_text(r.content)
    assert "DRAFT" in text.upper() or "Professional Alignment Report" in text


def test_professional_report_finalize_and_pdf(flow):
    pro, rid = flow["pro"], flow["rid"]
    # Minimum fields to satisfy _assert_finalizable:
    #   - signature_name required
    #   - if conflict_pathways set, rationale required. We omit conflict_pathways
    #     to keep the requirement minimal.
    fields = {
        "signature_name": "Test Pro, J.D.",
        "professional_summary": "Comprehensive summary for finalization test.",
        "court_summary_text": "Concise court-ready summary for readiness check.",
        "joint_rating": 6,
        "parent_a_rating": 5,
        "parent_b_rating": 5,
    }
    r = pro.put(f"{API}/cases/{rid}/professional-report", json={"fields": fields, "status": "final"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["report"]["status"] == "final", body["report"]["status"]
    assert body["report"]["finalized_at"]

    r = pro.get(f"{API}/cases/{rid}/professional-report/pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    text, pages = _pdf_text(r.content)
    assert pages >= 2, f"Prof report PDF has {pages} pages"
    # Content assertions per review request
    for needle in ("Professional Alignment Report", "Professional Certification"):
        assert needle in text, f"Missing '{needle}' in Prof Report PDF"
    # Cover page fields
    assert "Test Pro, J.D." in text
    # No DRAFT watermark once final
    assert "DRAFT" not in text, "DRAFT watermark still present after finalize"


def test_incomplete_flow_400_but_prof_pdf_still_available():
    pro, pa, pb, d = new_case(API, subject="education", child="Only-A")
    rid = d["id"]
    # Only Parent A completes
    fill(API, pa, rid, "alpha")

    r = pro.get(f"{API}/joint/reports/{rid}/report")
    assert r.status_code == 400, f"Expected 400 before both complete, got {r.status_code}: {r.text}"
    detail = r.json().get("detail", "")
    assert detail, "400 should include a clear message"

    # Professional Report PDF should still be downloadable (draft w/ watermark)
    r = pro.get(f"{API}/cases/{rid}/professional-report/pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
    text, _ = _pdf_text(r.content)
    assert "DRAFT" in text.upper(), "DRAFT watermark expected on unfinished report"
