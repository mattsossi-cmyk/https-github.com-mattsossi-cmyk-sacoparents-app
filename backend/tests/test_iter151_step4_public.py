# Iteration 151: public-URL checks for skip scoring, PDF "Skipped" label, quick-check safety_ack.skipped, check-in link.
import io
import os
import re
import uuid

import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
CONSENT = {"ack_privacy_notice": True, "consent_sensitive_info": True}


def _register():
    email = f"test_iter151_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "Str0ng!Pass99", "name": "TEST Iter151", **CONSENT})
    assert r.status_code in (200, 201), r.text
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    return {"Authorization": f"Bearer {tok}"}


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    if r.status_code != 200:
        pytest.skip(f"login failed for {email}: {r.status_code}")
    return {"Authorization": f"Bearer {r.json().get('access_token') or r.json().get('token')}"}


@pytest.fixture(scope="module")
def h():
    return _register()


@pytest.fixture(scope="module")
def questions(h):
    r = requests.get(f"{API}/safety-assessment/questions", headers=h)
    assert r.status_code == 200
    return r.json()


# Full assessment: skipping Section 1 danger questions never changes the level; PDF shows Skipped
def test_skip_danger_questions_level4_and_pdf(h, questions):
    s1 = {q["id"]: "no" for q in questions["section_1"]}
    s2 = {q["id"]: ("no" if q["id"] == "s2_q8" else "yes") for q in questions["section_2"]}
    for q in ("s1_q1", "s1_q2", "s1_q13"):
        s1[q] = "prefer_not"
    r = requests.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2}, headers=h)
    assert r.status_code in (200, 201), r.text
    d = r.json()
    lvl = d.get("level") or d.get("result", {}).get("level")
    assert lvl == 4, d
    blob = str(d)
    assert "skip_floor_ids" not in blob
    aid = d.get("id") or d.get("assessment_id")
    pdf = requests.get(f"{API}/safety-assessment/{aid}/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert re.search(r"skipped", text, re.I), "PDF lacks Skipped"
    assert "Prefer not" not in text and "prefer_not" not in text


# Quick check: skipped count persisted in portal safety_ack
def test_portal_safety_ack_skipped(h):
    ack = {"cleared": True, "flagged": False, "date": "2026-10-19T00:00:00Z", "skipped": 3}
    r = requests.put(f"{API}/portal/state", json={"safety_ack": ack}, headers=h)
    assert r.status_code == 200, r.text
    st = requests.get(f"{API}/portal/state", headers=h).json()
    sa = st.get("safety_ack") or st.get("state", {}).get("safety_ack")
    assert sa["skipped"] == 3 and sa["flagged"] is False and sa["cleared"] is True


# Family check-in link: linked parents share SA-TLINKDEF0; new parent unlinked
@pytest.mark.parametrize("email", ["test_linkdemo_a@example.com", "test_linkdemo_b@example.com"])
def test_checkin_linked(email):
    r = requests.get(f"{API}/family-checkin/link", headers=_login(email))
    assert r.status_code == 200 and r.json().get("case_id") == "SA-TLINKDEF0", r.text


def test_checkin_unlinked(h):
    r = requests.get(f"{API}/family-checkin/link", headers=h)
    assert r.status_code == 200 and not r.json().get("case_id"), r.text
