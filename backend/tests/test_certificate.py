"""Backend tests for Certificate of Completion endpoints.

Covers:
- GET /api/mediation/certificate/eligibility (guests always eligible;
  JWT users need 5/6 core steps)
- GET /api/mediation/certificate/preview (image/png)
- POST /api/mediation/certificate/download (application/pdf)
- Auth gating (401 without token)
- Fallback name for blank display_name
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def guest_token():
    r = requests.post(f"{API}/auth/guest", json={"name": "TEST_Sam Parent"})
    assert r.status_code in (200, 201), r.text
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"guest response missing token: {data}"
    return tok


@pytest.fixture(scope="module")
def jwt_token():
    # Try login first with seeded creds
    email = "parent1@test.com"
    password = "TestPass123!"
    login = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    if login.status_code == 200:
        j = login.json()
        return j.get("access_token") or j.get("token")
    # Register if not present
    reg = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "name": "Sam Parent"},
    )
    if reg.status_code in (200, 201):
        j = reg.json()
        return j.get("access_token") or j.get("token")
    # Last resort: create a unique test user
    unique = f"TEST_cert_{uuid.uuid4().hex[:8]}@test.com"
    reg2 = requests.post(
        f"{API}/auth/register",
        json={"email": unique, "password": "TestPass123!", "name": "TEST Cert User"},
    )
    assert reg2.status_code in (200, 201), reg2.text
    j = reg2.json()
    return j.get("access_token") or j.get("token")


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Auth gating ----------
class TestCertificateAuth:
    def test_eligibility_requires_auth(self):
        r = requests.get(f"{API}/mediation/certificate/eligibility")
        assert r.status_code == 401

    def test_preview_requires_auth(self):
        r = requests.get(f"{API}/mediation/certificate/preview")
        assert r.status_code == 401

    def test_download_requires_auth(self):
        r = requests.post(f"{API}/mediation/certificate/download", json={})
        assert r.status_code == 401


# ---------- Eligibility ----------
class TestCertificateEligibility:
    def test_guest_always_eligible(self, guest_token):
        r = requests.get(f"{API}/mediation/certificate/eligibility", headers=_h(guest_token))
        assert r.status_code == 200
        data = r.json()
        for key in ("eligible", "is_guest", "completed_steps", "required_steps", "threshold", "display_name"):
            assert key in data, f"missing key {key}: {data}"
        assert data["is_guest"] is True
        assert data["eligible"] is True
        assert data["threshold"] == 5
        assert isinstance(data["required_steps"], list) and len(data["required_steps"]) == 6
        assert isinstance(data["completed_steps"], list)

    def test_jwt_new_user_not_eligible(self, jwt_token):
        # A brand new registered JWT user has 0 completed steps → not eligible
        # (parent1@test.com may have data; use it, but validate the eligibility
        # logic returns bool aligned with completed count.)
        r = requests.get(f"{API}/mediation/certificate/eligibility", headers=_h(jwt_token))
        assert r.status_code == 200
        data = r.json()
        assert data["is_guest"] is False
        assert data["threshold"] == 5
        # Eligible must match: >= threshold completed
        expected_eligible = len(data["completed_steps"]) >= data["threshold"]
        assert data["eligible"] == expected_eligible


# ---------- Preview PNG ----------
class TestCertificatePreview:
    def test_preview_returns_png(self, guest_token):
        r = requests.get(f"{API}/mediation/certificate/preview", headers=_h(guest_token))
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("image/png")
        # PNG magic bytes
        assert r.content.startswith(b"\x89PNG"), "response is not a valid PNG"
        assert len(r.content) > 5000, "PNG suspiciously small"

    def test_preview_with_name_override(self, guest_token):
        r = requests.get(
            f"{API}/mediation/certificate/preview",
            headers=_h(guest_token),
            params={"name": "TEST_Preview Override Name"},
        )
        assert r.status_code == 200
        assert r.content.startswith(b"\x89PNG")

    def test_preview_with_empty_name_falls_back(self, guest_token):
        r = requests.get(
            f"{API}/mediation/certificate/preview",
            headers=_h(guest_token),
            params={"name": "   "},
        )
        assert r.status_code == 200
        assert r.content.startswith(b"\x89PNG")


# ---------- Download PDF ----------
class TestCertificateDownload:
    def test_download_returns_pdf(self, guest_token):
        r = requests.post(
            f"{API}/mediation/certificate/download",
            headers=_h(guest_token),
            json={"name": "TEST_Downloader"},
        )
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF"), "response is not a valid PDF"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "TEST_Downloader" in cd, f"filename missing sanitised name: {cd}"

    def test_download_filename_sanitised(self, guest_token):
        r = requests.post(
            f"{API}/mediation/certificate/download",
            headers=_h(guest_token),
            json={"name": "TEST/Bad*Name?<>"},
        )
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "")
        # No special chars should be present in the filename (all replaced with _)
        for ch in "/*?<>":
            assert ch not in cd

    def test_download_blank_name_uses_fallback(self, guest_token):
        r = requests.post(
            f"{API}/mediation/certificate/download",
            headers=_h(guest_token),
            json={"name": "   "},
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
        cd = r.headers.get("content-disposition", "")
        # Fallback becomes "Committed Co-Parent" → sanitised => "Committed_Co_Parent"
        assert "Committed_Co_Parent" in cd, cd

    def test_download_no_body_name(self, guest_token):
        r = requests.post(
            f"{API}/mediation/certificate/download",
            headers=_h(guest_token),
            json={},
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
