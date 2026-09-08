"""Verify demo report output shape - refactor byte-equivalence checks."""
import os
import uuid
import requests
import pytest
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend .env
    load_dotenv("/app/frontend/.env")
    BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

REQUIRED_KEYS = {
    "snapshot", "alignments", "differences", "child_needs", "options",
    "conversation_questions", "professional_map", "action_plan", "summary",
    "court_map", "page_titles", "philosophy",
}


@pytest.fixture(scope="module")
def admin_session() -> requests.Session:
    """Self-contained authenticated session (no dependence on a real user account)."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Shape Fixture", "email": f"shape_{uuid.uuid4().hex[:8]}@example.com",
        "password": "testpass123", "role": "professional", "agreements_accepted": True,
    })
    assert r.status_code == 200, r.text
    return s


def _make_and_report(session: requests.Session, case_type: str) -> dict:
    r = session.post(f"{BASE_URL}/api/cases", json={"type": case_type})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r = session.post(f"{BASE_URL}/api/cases/{cid}/demo")
    assert r.status_code == 200, r.text
    r = session.get(f"{BASE_URL}/api/cases/{cid}/report")
    assert r.status_code == 200, r.text
    return r.json()


def _assert_snapshot_and_summary(data: dict) -> None:
    snap = data["snapshot"]
    for k in ("total", "aligned", "different", "info"):
        assert k in snap, f"snapshot missing {k}"
    summary = data["summary"]
    for k in ("aligned", "info", "conversation", "options", "priority"):
        assert k in summary, f"summary missing {k}"


def test_educational_report_shape(admin_session) -> None:
    data = _make_and_report(admin_session, "educational")
    missing = REQUIRED_KEYS - set(data.keys())
    assert not missing, f"missing keys: {missing}"
    _assert_snapshot_and_summary(data)
    assert data["court_map"] is None, "educational court_map should be null"
    assert isinstance(data["page_titles"], list) and len(data["page_titles"]) == 10
    assert isinstance(data["conversation_questions"], list) and len(data["conversation_questions"]) > 0


def test_court_report_has_court_map(admin_session: requests.Session) -> None:
    data = _make_and_report(admin_session, "court")
    assert data["court_map"] is not None, "court type must have court_map"
    cm = data["court_map"]
    for bucket in ("agreed", "close", "discussion", "info"):
        assert bucket in cm, f"court_map missing {bucket}"


def test_conversation_questions_no_duplicates(admin_session: requests.Session) -> None:
    """Intentional fix: central question no longer appended twice when 0 differing topics."""
    data = _make_and_report(admin_session, "educational")
    qs = data["conversation_questions"]
    assert len(qs) == len(set(qs)), f"duplicates found: {qs}"
