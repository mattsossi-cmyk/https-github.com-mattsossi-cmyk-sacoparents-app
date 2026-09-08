"""Tests for GET /api/external/assessments (private-assessment prefill source)
and the external link flow guards.
"""
import os
import uuid
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _reg(prefix="ext"):
    email = f"TEST_{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": f"Test {prefix}", "email": email, "password": "testpass123", "role": "professional", "agreements_accepted": True,
    })
    assert r.status_code == 200, r.text
    return s, email


class TestExternalAssessments:
    def test_requires_auth(self) -> None:
        r = requests.get(f"{API}/external/assessments")
        assert r.status_code in (401, 403)

    def test_fresh_link_status_false(self) -> None:
        s, _ = _reg()
        r = s.get(f"{API}/external/link")
        assert r.status_code == 200, r.text
        assert r.json() == {"linked": False}

    def test_unlinked_assessments_400(self) -> None:
        s, _ = _reg()
        r = s.get(f"{API}/external/assessments")
        assert r.status_code == 400, r.text
        assert "link" in r.json()["detail"].lower()

    def test_bogus_link_code_400(self) -> None:
        s, _ = _reg()
        r = s.post(f"{API}/external/link", json={"code": "ZZZZZZZZ"})
        assert r.status_code in (400, 502), r.text

    def test_unlink_ok(self) -> None:
        s, _ = _reg()
        r = s.delete(f"{API}/external/link")
        assert r.status_code == 200, r.text
        assert s.get(f"{API}/external/link").json() == {"linked": False}
