"""Iteration 18 regression tests:
- Guest auth + Section-coaching endpoint (all 4 sections + invalid rejection)
- The old Safety Assessment is gone; the "safety" coaching section is rejected
- Static video assets HEAD 200 with video/mp4
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def guest_token():
    r = requests.post(f"{API}/auth/guest", json={}, timeout=15)
    assert r.status_code == 200, f"guest auth failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token")
    assert tok, f"no access_token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(guest_token):
    return {"Authorization": f"Bearer {guest_token}", "Content-Type": "application/json"}


# ------------------------------------------------------------------
# Section coaching endpoint
# ------------------------------------------------------------------
class TestSectionCoaching:
    def test_readiness_coaching(self, auth_headers):
        payload = {
            "section": "readiness",
            "data": {
                "pct": 62,
                "sections": {
                    "emotional": 3, "practical": 4, "communication": 3,
                    "child_focused": 4, "mediation_readiness": 3,
                },
            },
        }
        r = requests.post(f"{API}/mediation/section-coaching", json=payload,
                          headers=auth_headers, timeout=45)
        assert r.status_code == 200, f"readiness coaching failed: {r.status_code} {r.text}"
        body = r.json()
        for k in ("opener", "strengths", "attention", "next_step"):
            assert k in body, f"missing key {k} in {body.keys()}"
            assert isinstance(body[k], str) and body[k].strip(), f"key {k} not a non-empty string: {body[k]!r}"

    def test_comm_style_coaching(self, auth_headers):
        payload = {
            "section": "comm-style",
            "data": {
                "style_label": "Escalator", "score": 5,
                "strengths": ["Passionate advocate for my child"],
                "growth_areas": ["Cool-down before responding"],
            },
        }
        r = requests.post(f"{API}/mediation/section-coaching", json=payload,
                          headers=auth_headers, timeout=45)
        assert r.status_code == 200, f"comm-style coaching failed: {r.status_code} {r.text}"
        body = r.json()
        for k in ("opener", "strengths", "attention", "next_step"):
            assert k in body and isinstance(body[k], str) and body[k].strip()

    def test_safety_section_rejected(self, auth_headers):
        payload = {"section": "safety", "data": {"level": "Yellow"}}
        r = requests.post(f"{API}/mediation/section-coaching", json=payload, headers=auth_headers, timeout=15)
        assert 400 <= r.status_code < 500, f"expected 4xx, got {r.status_code} {r.text}"

    def test_overall_coaching(self, auth_headers):
        payload = {
            "section": "overall",
            "data": {
                "child_goals": ["safe environment", "stable schedule"],
                "issues": ["schedule conflicts"],
                "priorities": ["consistency"],
                "comm_style": {"style_label": "Balanced", "score": 8},
                "foundation": "Our shared goal is a stable, loving environment.",
                "readiness_pct": 78,
                "safety_level": "Green",
            },
        }
        r = requests.post(f"{API}/mediation/section-coaching", json=payload,
                          headers=auth_headers, timeout=45)
        assert r.status_code == 200, f"overall coaching failed: {r.status_code} {r.text}"
        body = r.json()
        for k in ("opener", "strengths", "attention", "next_step"):
            assert k in body and isinstance(body[k], str) and body[k].strip()

    def test_invalid_section_rejected(self, auth_headers):
        payload = {"section": "not-a-section", "data": {"foo": 1}}
        r = requests.post(f"{API}/mediation/section-coaching", json=payload,
                          headers=auth_headers, timeout=15)
        assert 400 <= r.status_code < 500, f"expected 4xx, got {r.status_code} {r.text}"

    def test_unauth_rejected(self):
        r = requests.post(f"{API}/mediation/section-coaching",
                          json={"section": "readiness", "data": {"pct": 50}},
                          timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# ------------------------------------------------------------------
# The old in-app Safety Assessment is hidden (Align safety step)
# ------------------------------------------------------------------
def test_old_safety_questions_are_gone(auth_headers):
    r = requests.get(f"{API}/safety-assessment/questions", headers=auth_headers, timeout=15)
    assert r.status_code == 404


# ------------------------------------------------------------------
class TestVideoAssets:
    @pytest.mark.parametrize("name", [
        "facebook-intro.mp4",
        "social-journey.mp4",
        "app-showcase.mp4",
        "summary-journey.mp4",
    ])
    def test_video_head_200(self, name):
        url = f"{BASE_URL}/videos/{name}"
        # HEAD
        r = requests.head(url, timeout=15, allow_redirects=True)
        assert r.status_code == 200, f"{name} HEAD -> {r.status_code}"
        ctype = r.headers.get("Content-Type", "")
        assert "video/mp4" in ctype.lower(), f"{name} Content-Type={ctype!r}"
