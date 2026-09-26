"""Iter78 — Complete Coparenting Report PDF endpoint + share regressions."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# -------- POST /api/portal/complete-report-pdf --------

def test_complete_report_pdf_rich_payload():
    payload = {
        "safety_ack": {"flagged": False, "confidence": "high", "answers": {"q1": "safe"}},
        "cop_assessment": {"communication": 7, "trust": 6, "conflict": 4},
        "align_records": [
            {"category": "Medical", "title": "Pediatrician plan", "body": "Dr X, monthly visit."},
            {"category": "Educational", "title": "School plan", "body": "Grade 4"},
            {"category": "Psychological", "title": "Therapy", "body": "weekly"},
        ],
        "joint_records": [{"category": "Medical", "title": "Joint plan", "body": "Agreed."}],
        "foundation_text": "Our foundation statement " * 20,
        "case_ref": "SA-DEMO01",
        "author_name": "Sam Parent",
    }
    r = requests.post(f"{API}/portal/complete-report-pdf", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF-")
    assert len(r.content) > 500


def test_complete_report_pdf_empty_payload():
    r = requests.post(f"{API}/portal/complete-report-pdf", json={}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF-")


def test_complete_report_pdf_foundation_text_max_length():
    payload = {"foundation_text": "x" * 8001}
    r = requests.post(f"{API}/portal/complete-report-pdf", json=payload, timeout=30)
    assert r.status_code == 422, r.text


# -------- POST /api/portal/share with artefact_type='complete' --------

def test_share_complete_no_passphrase_then_fetch_pdf():
    body = {
        "artefact_type": "complete",
        "payload": {
            "safety_ack": {"flagged": False},
            "foundation_text": "Foundation content.",
        },
    }
    r = requests.post(f"{API}/portal/share", json=body, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "share_id" in data
    assert "url" in data
    assert data.get("requires_passphrase") is False
    assert data.get("ttl_days") == 30

    # Fetch the PDF via the returned share_id
    share_id = data["share_id"]
    r2 = requests.get(f"{API}/portal/share/{share_id}.pdf", timeout=30)
    assert r2.status_code == 200, r2.text
    assert r2.headers.get("content-type", "").startswith("application/pdf")
    assert r2.content.startswith(b"%PDF-")


def test_share_complete_with_passphrase_gate():
    body = {
        "artefact_type": "complete",
        "payload": {"foundation_text": "Guarded content"},
        "passphrase": "letmein",
        "ttl_days": 7,
    }
    r = requests.post(f"{API}/portal/share", json=body, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("requires_passphrase") is True
    assert data.get("ttl_days") == 7
    share_id = data["share_id"]

    # No passphrase → HTML gate
    r_gate = requests.get(f"{API}/portal/share/{share_id}.pdf", timeout=30, allow_redirects=False)
    assert r_gate.status_code == 200
    assert "text/html" in r_gate.headers.get("content-type", "")

    # With passphrase → PDF
    r_pdf = requests.get(f"{API}/portal/share/{share_id}.pdf?p=letmein", timeout=30)
    assert r_pdf.status_code == 200
    assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
    assert r_pdf.content.startswith(b"%PDF-")


# -------- Regression: legacy artefact_types still work --------

@pytest.mark.parametrize("artefact_type,payload", [
    ("foundation", {"foundation_text": "hello foundation"}),
    ("legal", {"court_key": "ALIGN-SA-2026", "notes": "n/a"}),
    ("weekly", {"week_of": "2026-01-12", "wins": ["a"], "frictions": ["b"]}),
])
def test_share_legacy_artefact_types_regression(artefact_type, payload):
    body = {"artefact_type": artefact_type, "payload": payload}
    r = requests.post(f"{API}/portal/share", json=body, timeout=30)
    assert r.status_code == 200, f"{artefact_type}: {r.text}"
    data = r.json()
    assert "share_id" in data
    share_id = data["share_id"]
    r2 = requests.get(f"{API}/portal/share/{share_id}.pdf", timeout=30)
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("application/pdf")
    assert r2.content.startswith(b"%PDF-")
