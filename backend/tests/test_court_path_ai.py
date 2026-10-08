"""Regression tests for /api/portal/court-keys/verify and the Self-Assessment framing AI."""
import os
import pytest
import requests
from pathlib import Path


def _base_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if url:
        return url.rstrip("/")
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _base_url()
API = f"{BASE_URL}/api"



class TestCourtKeyVerify:
    def test_valid_court_8842(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "COURT-8842"}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("verified") is True
        assert data.get("case_id")
        assert data.get("mediator_name")

    def test_valid_align_sa_2026(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "ALIGN-SA-2026"}, timeout=20)
        assert r.status_code == 200
        assert r.json().get("verified") is True

    def test_unknown_key(self):
        r = requests.post(f"{API}/portal/court-keys/verify", json={"key": "NOPE-123"}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data.get("verified") is False
        assert data.get("reason") == "unknown_key"


# ---------- Regression: /self-assessment/ai ----------

class TestSelfAssessmentAiRegression:
    def test_framing_short_text_422(self):
        r = requests.post(f"{API}/self-assessment/ai/framing", json={"text": "x"}, timeout=20)
        assert r.status_code == 422

    def test_framing_valid(self):
        r = requests.post(
            f"{API}/self-assessment/ai/framing",
            json={"text": "You never bring the kids on time and I'm sick of it."},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("advice"), str) and data["advice"]
        assert isinstance(data.get("suggested"), str) and data["suggested"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
