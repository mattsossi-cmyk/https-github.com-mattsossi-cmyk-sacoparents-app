"""Iter162: guided Self Journey /api/self-journey/me (stage) + PDF 'Your path:' line, against the public preview URL."""
import io
import os
import re
import uuid

import pytest
import requests
from dotenv import dotenv_values

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _pdf_text(raw: bytes) -> str:
    from pypdf import PdfReader
    return re.sub(r"\s+", " ", "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages))


@pytest.fixture(scope="module")
def parent():
    email = f"test_sj162_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST Sj162",
                                                    "ack_privacy_notice": True, "consent_sensitive_info": True})
    assert r.status_code in (200, 201), r.text
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


# auth
def test_me_requires_auth():
    assert requests.get(f"{API}/self-journey/me").status_code == 401


# parent1 can still read their journey
def test_parent1_get_me():
    r = requests.post(f"{API}/auth/login", json={"email": "parent1@test.com", "password": "TestPass123!"})
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token")
    g = requests.get(f"{API}/self-journey/me", headers={"Authorization": f"Bearer {tok}"})
    assert g.status_code == 200
    assert "progress" in g.json()


# stage accepted + persisted
def test_stage_saved_and_reloaded(parent):
    body = {"maxStepReached": 2, "stage": "highConflict", "safety": {"status": "clear"}}
    r = parent.put(f"{API}/self-journey/me", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["progress"]["stage"] == "highConflict"
    g = parent.get(f"{API}/self-journey/me").json()["progress"]
    assert g["stage"] == "highConflict"
    assert g["maxStepReached"] == 2


# bad stage rejected
def test_bad_stage_rejected(parent):
    r = parent.put(f"{API}/self-journey/me", json={"stage": "nope"})
    assert r.status_code == 422


# null stage allowed (skip)
def test_null_stage_allowed(parent):
    r = parent.put(f"{API}/self-journey/me", json={"maxStepReached": 2, "stage": None})
    assert r.status_code == 200
    assert r.json()["progress"]["stage"] is None


# PDF includes path line on non-safety path
def test_pdf_has_path_line(parent):
    body = {"maxStepReached": 7, "stage": "communication", "safety": {"status": "clear"},
            "coparenting": {"approach": "parallel"}}
    assert parent.put(f"{API}/self-journey/me", json=body).status_code == 200
    r = parent.get(f"{API}/self-journey/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    text = _pdf_text(r.content)
    assert "Your path:" in text, text[:800]


# PDF omits path line on safety concern
def test_pdf_omits_path_line_on_concern(parent):
    body = {"maxStepReached": 7, "stage": "highConflict", "safety": {"status": "concern"},
            "coparenting": {"approach": "parallel"}}
    assert parent.put(f"{API}/self-journey/me", json=body).status_code == 200
    r = parent.get(f"{API}/self-journey/pdf")
    assert r.status_code == 200
    text = _pdf_text(r.content)
    assert "Your path:" not in text
    assert "concern" not in text.lower()


# concern strips cooperative approach
def test_concern_strips_cooperative(parent):
    body = {"maxStepReached": 3, "safety": {"status": "concern"}, "coparenting": {"approach": "cooperative"}}
    r = parent.put(f"{API}/self-journey/me", json=body)
    assert r.status_code == 200
    assert r.json()["progress"]["coparenting"]["approach"] is None
