"""Iter 92 — HTTP integration tests for new features:
   - Child-needs: GET/PUT/POST pdf
   - Mediator progress PDF with include_safety / include_biff
   - Self-assessment goal/checkin recent_dates in history + checkin response
"""
import os
import io
import pytest
import requests
from pathlib import Path
from dotenv import dotenv_values
from pypdf import PdfReader

_env = dotenv_values(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"

P1 = {"email": "parent1@test.com", "password": "TestPass123!"}
P2 = {"email": "parent2@test.com", "password": "TestPass123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def s1():
    return _login(P1)


@pytest.fixture(scope="module")
def s2():
    return _login(P2)


# ------------------- CHILD NEEDS -------------------

def test_child_needs_requires_auth():
    r = requests.get(f"{API}/child-needs/me", timeout=15)
    assert r.status_code == 401


def test_child_needs_get_shape(s1):
    r = s1.get(f"{API}/child-needs/me", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "answers" in data and "completed_at" in data
    assert isinstance(data["answers"], dict) and isinstance(data["completed_at"], dict)


def test_child_needs_unknown_category(s1):
    r = s1.put(f"{API}/child-needs/me/bogus", json={"answers": {"x": "y"}}, timeout=15)
    assert r.status_code == 404


def test_child_needs_all_empty_rejected(s1):
    r = s1.put(f"{API}/child-needs/me/medical", json={"answers": {"bogus": "x", "med_goal": "  "}}, timeout=15)
    assert r.status_code == 422


def test_child_needs_put_medical_cleans_and_saves(s1):
    r = s1.put(
        f"{API}/child-needs/me/medical",
        json={"answers": {"med_provider": "  Dr. TEST_Lee  ", "med_insurance": "BOGUS_OPTION",
                           "bogus_field": "ignored", "med_goal": "TEST_regular checkups"}},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    med = data["answers"]["medical"]
    assert med["med_provider"] == "Dr. TEST_Lee"
    assert "med_insurance" not in med  # bad select dropped
    assert "bogus_field" not in med
    assert med["med_goal"] == "TEST_regular checkups"
    assert "medical" in data["completed_at"]

    # GET should reflect persistence
    g = s1.get(f"{API}/child-needs/me", timeout=15)
    assert g.status_code == 200
    assert g.json()["answers"]["medical"]["med_provider"] == "Dr. TEST_Lee"


def test_child_needs_select_valid_option(s1):
    r = s1.put(
        f"{API}/child-needs/me/medical",
        json={"answers": {"med_insurance": "Currently disputed"}},
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["answers"]["medical"].get("med_insurance") == "Currently disputed"


def test_child_needs_pdf_public_nothing_filled():
    r = requests.post(f"{API}/child-needs/pdf", json={"parent_name": "Sam", "answers": {}}, timeout=20)
    assert r.status_code == 400


def test_child_needs_pdf_only_filled_category_present():
    r = requests.post(
        f"{API}/child-needs/pdf",
        json={"parent_name": "Sam TEST",
              "answers": {"medical": {"med_provider": "Dr. Lee"},
                           "educational": {},
                           "psychological": {}}},
        timeout=25,
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
    # Section titles since the "Your Child's Specific Needs" restyle.
    assert "Medical Assessment Form" in text
    assert "Educational Assessment Form" not in text
    assert "Psychological Assessment Form" not in text


# ------------------- MEDIATOR PROGRESS PDF EXTRAS -------------------

def _progress_pdf_text(s, params=""):
    r = s.get(f"{API}/coparenting/report/progress/pdf{params}", timeout=30)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)


def test_progress_pdf_default_no_extras(s1):
    txt = _progress_pdf_text(s1)
    assert "Safety timeline" not in txt
    assert "Recent BIFF messages" not in txt


def test_progress_pdf_with_safety(s1):
    txt = _progress_pdf_text(s1, "?include_safety=true")
    assert "Safety timeline" in txt
    # Should mention grey-rock on/off language
    assert ("Grey-Rock mode turned ON" in txt) or ("Grey-Rock mode turned OFF" in txt)


def test_progress_pdf_with_biff(s1):
    txt = _progress_pdf_text(s1, "?include_biff=true")
    assert "Recent BIFF messages" in txt
    assert "Original:" in txt and "BIFF rewrite:" in txt


def test_progress_pdf_both(s1):
    txt = _progress_pdf_text(s1, "?include_safety=true&include_biff=true")
    assert "Safety timeline" in txt and "Recent BIFF messages" in txt


def test_progress_share_model_accepts_extras(s1):
    # Bad email → 400 (model validation reached). Resend sandbox may 502/503 for valid email in preview.
    r = s1.post(
        f"{API}/coparenting/report/progress/share",
        json={"to_email": "not-an-email", "include_safety": True, "include_biff": True},
        timeout=20,
    )
    assert r.status_code in (400, 422), r.text


# ------------------- SELF-ASSESSMENT GOAL recent_dates -------------------

def test_history_has_recent_dates(s1):
    r = s1.get(f"{API}/self-assessment/history", timeout=20)
    assert r.status_code == 200
    data = r.json()
    gp = data.get("goal_practice")
    assert gp is not None, "goal_practice missing"
    assert "recent_dates" in gp, gp
    assert isinstance(gp["recent_dates"], list)
    for d in gp["recent_dates"]:
        assert isinstance(d, str) and len(d) == 10 and d[4] == "-" and d[7] == "-"


def test_checkin_returns_recent_dates(s1):
    hist = s1.get(f"{API}/self-assessment/history", timeout=20).json()
    gp = hist.get("goal_practice") or {}
    entry_id = gp.get("entry_id")
    assert entry_id, "no entry_id in goal_practice; need a seeded SA entry"
    from datetime import date
    today = date.today().isoformat()
    r = s1.post(f"{API}/self-assessment/goal/checkin",
                 json={"entry_id": entry_id, "date": today}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "recent_dates" in data
    assert isinstance(data["recent_dates"], list)
    assert today in data["recent_dates"]
