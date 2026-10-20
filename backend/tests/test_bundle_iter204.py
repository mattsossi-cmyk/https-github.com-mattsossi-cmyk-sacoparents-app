"""Iter204 - Bundle Download endpoint tests + PDF regression."""
import os
import io
import zipfile
import uuid
import time
import pytest
import requests

def _read_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env() or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def parent1_token():
    return _login("parent1@test.com", "TestPass123!")


@pytest.fixture(scope="module")
def parent2_token():
    return _login("parent2@test.com", "TestPass123!")


@pytest.fixture(scope="module")
def fresh_parent_token():
    email = f"TEST_bundle_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": "TestPass123!",
                            "name": "Fresh Bundle Test"}, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if not tok:
        tok = _login(email, "TestPass123!")
    return tok


# ----------------- Bundle endpoint tests -----------------

class TestBundleEndpoint:

    def test_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/bundle/my-completed.zip", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_parent1_receives_valid_zip(self, parent1_token):
        r = requests.get(
            f"{BASE_URL}/api/bundle/my-completed.zip",
            headers={"Authorization": f"Bearer {parent1_token}"},
            timeout=90,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:400]}"
        assert r.headers.get("content-type", "").startswith("application/zip"), \
            f"unexpected content-type: {r.headers.get('content-type')}"
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert "MANIFEST.txt" in names, f"no MANIFEST in ZIP: {names}"
            manifest = zf.read("MANIFEST.txt").decode()
            print("MANIFEST parent1:\n", manifest)
            pdfs = [n for n in names if n.endswith(".pdf")]
            assert len(pdfs) >= 1, f"no PDFs in ZIP: {names}"
            for p in pdfs:
                data = zf.read(p)
                assert data[:4] == b"%PDF", f"{p} is not a valid PDF"
        # Headers should note included/skipped counts
        assert r.headers.get("X-SACoParents-Bundle-Included")

    def test_manifest_lists_skipped(self, parent1_token):
        r = requests.get(
            f"{BASE_URL}/api/bundle/my-completed.zip",
            headers={"Authorization": f"Bearer {parent1_token}"},
            timeout=90,
        )
        assert r.status_code == 200
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            manifest = zf.read("MANIFEST.txt").decode()
        # Not-yet section may or may not exist depending on parent1's state,
        # but if any skipped >0 header, section must be present.
        skipped_ct = int(r.headers.get("X-SACoParents-Bundle-Skipped", "0"))
        if skipped_ct > 0:
            assert "Not yet completed" in manifest

    def test_fresh_parent_gets_409(self, fresh_parent_token):
        r = requests.get(
            f"{BASE_URL}/api/bundle/my-completed.zip",
            headers={"Authorization": f"Bearer {fresh_parent_token}"},
            timeout=60,
        )
        assert r.status_code == 409, f"expected 409 for empty parent, got {r.status_code}: {r.text[:400]}"
        try:
            detail = r.json().get("detail", "")
        except Exception:
            detail = r.text
        assert "assessment" in detail.lower() or "complete" in detail.lower(), \
            f"detail not friendly: {detail}"

    def test_parent1_vs_parent2_different(self, parent1_token, parent2_token):
        r1 = requests.get(
            f"{BASE_URL}/api/bundle/my-completed.zip",
            headers={"Authorization": f"Bearer {parent1_token}"}, timeout=90)
        r2 = requests.get(
            f"{BASE_URL}/api/bundle/my-completed.zip",
            headers={"Authorization": f"Bearer {parent2_token}"}, timeout=90)
        if r1.status_code == 200 and r2.status_code == 200:
            assert r1.content != r2.content, \
                "parent1 and parent2 bundles are byte-identical - auth may not be forwarding"
        elif r1.status_code == 200 and r2.status_code == 409:
            pass  # parent2 has nothing → distinct outcome, still valid
        else:
            pytest.skip(f"unusual combo: p1={r1.status_code} p2={r2.status_code}")


# ----------------- PDF regression tests -----------------

PDF_ENDPOINTS = [
    "/api/mediation/foundation-statement.pdf",
    "/api/snc2/report/pdf",
    "/api/edu-deep/report/pdf",
    "/api/med-deep/report/pdf",
    "/api/psych-deep/report/pdf",
    "/api/coparenting/report/pdf",
    "/api/complete-report/mine.pdf",
    "/api/pathway-report/preview/pdf",
]


class TestPdfRegression:
    @pytest.mark.parametrize("path", PDF_ENDPOINTS)
    def test_pdf_endpoint_responds(self, parent1_token, path):
        r = requests.get(f"{BASE_URL}{path}",
                         headers={"Authorization": f"Bearer {parent1_token}"},
                         timeout=60)
        # Valid outcomes: 200 with PDF, 404/409 empty-state
        assert r.status_code in (200, 404, 409), \
            f"{path} unexpected status {r.status_code}: {r.text[:200]}"
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            assert "pdf" in ct.lower(), f"{path} not PDF content-type: {ct}"
            assert r.content[:4] == b"%PDF", f"{path} content not %PDF"

    def test_old_safety_assessment_pdf_is_gone(self, parent1_token):
        r = requests.get(f"{BASE_URL}/api/safety-assessment/me",
                         headers={"Authorization": f"Bearer {parent1_token}"}, timeout=30)
        assert r.status_code == 404
