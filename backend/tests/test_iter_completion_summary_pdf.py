"""Tests for GET /api/court-path/completion-summary.pdf (parent completion summary)."""
import io
import os
import subprocess
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

CCALERT = {"email": "ccalert@test.com", "password": "TestPass123!"}
CCPARENT = {"email": "ccparent@test.com", "password": "TestPass123!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["access_token"]


def _pdftotext(pdf_bytes: bytes) -> str:
    p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf_bytes,
                       capture_output=True, timeout=20)
    assert p.returncode == 0, p.stderr.decode()
    return p.stdout.decode("utf-8", errors="replace")


def _pdfinfo(pdf_bytes: bytes) -> str:
    p = subprocess.run(["pdfinfo", "-"], input=pdf_bytes, capture_output=True, timeout=20)
    assert p.returncode == 0, p.stderr.decode()
    return p.stdout.decode("utf-8", errors="replace")


class TestCompletionSummaryPdf:
    def test_no_auth_returns_401(self):
        r = requests.get(f"{API}/court-path/completion-summary.pdf", timeout=15)
        assert r.status_code in (401, 403), r.text

    def test_ccalert_all_done_returns_pdf(self):
        tok = _login(CCALERT)
        r = requests.get(f"{API}/court-path/completion-summary.pdf",
                         headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "SA_CoParents_Completion_Summary.pdf" in cd, cd

        body = r.content
        assert body[:4] == b"%PDF", "not a pdf"
        info = _pdfinfo(body)
        pages_line = [l for l in info.splitlines() if l.strip().startswith("Pages:")]
        assert pages_line and pages_line[0].strip().split()[-1] == "1", info

        text = _pdftotext(body)
        print("PDF TEXT:\n" + text)
        assert "Completion Summary" in text
        assert "You" in text and "finished what your professional asked for" in text
        # Case line should include court key for ccalert (CC-AKDYZ5)
        assert "CC-AKDYZ5" in text or "Case" in text
        # legal name / N of N done
        assert "done" in text.lower()
        # Each done item should include "Done"
        assert "Done" in text
        # Closing / disclaimer language
        low = text.lower()
        assert "does not include" in low and "answers" in low
        # No raw answer content: there should be no scores/reflections leaked.
        # Simple negative check: words like "score", "reflection" should not appear
        for bad in ["score:", "reflection:", "my answer", "i feel", "i answered"]:
            assert bad.lower() not in low, f"leaked answer-ish token: {bad}"

    def test_ccparent_incomplete_returns_409(self):
        tok = _login(CCPARENT)
        r = requests.get(f"{API}/court-path/completion-summary.pdf",
                         headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 409, f"{r.status_code} {r.text}"
        detail = r.json().get("detail", "")
        assert "unlocks once everything your professional asked for is finished" in detail

    def test_fresh_parent_nothing_requested_returns_409(self):
        # Register a brand new parent (no court link, nothing requested)
        email = f"TEST_cs_{uuid.uuid4().hex[:10]}@test.com"
        payload = {"email": email, "password": "TestPass123!", "name": "TEST CS Parent"}
        r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        tok = r.json().get("access_token")
        if not tok:
            tok = _login({"email": email, "password": "TestPass123!"})
        r2 = requests.get(f"{API}/court-path/completion-summary.pdf",
                          headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r2.status_code == 409, f"{r2.status_code} {r2.text}"
