"""Backend tests for iteration 22: matter notes privacy + invitation expiry."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

PRO1 = ("approval.test.pro1@gmail.com", "TestPass2026!")
PRO2 = ("approval.test.pro2@gmail.com", "TestPass2026!")
MATTER_CASE_CODE = "SA-EDU-642310"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def sess_pro1():
    return _login(*PRO1)


@pytest.fixture(scope="module")
def sess_pro2():
    return _login(*PRO2)


@pytest.fixture(scope="module")
def matter_pro1(sess_pro1):
    r = sess_pro1.get(f"{API}/joint/reports", timeout=15)
    assert r.status_code == 200
    reports = r.json()
    m = next((x for x in reports if x.get("case_code") == MATTER_CASE_CODE), None)
    assert m is not None, f"Matter {MATTER_CASE_CODE} not found for pro1"
    return m


def test_lookup_invalid_token_404():
    r = requests.get(f"{API}/joint/invitations/lookup/definitely-not-a-real-token-xyz", timeout=10)
    assert r.status_code == 404, f"expected 404 got {r.status_code} {r.text}"


def test_matter_pending_invites_expose_expiry_fields(matter_pro1):
    pending = matter_pro1.get("pending_invitations") or []
    b = [p for p in pending if p.get("role") == "b"]
    assert b, f"No pending invites for role b: {pending}"
    for p in b:
        assert p.get("expires_at"), f"expires_at missing: {p}"
        assert isinstance(p.get("expired"), bool), f"expired flag missing: {p}"


def test_notes_privacy_pro2_cannot_read(sess_pro2, matter_pro1):
    rid = matter_pro1["id"]
    r = sess_pro2.get(f"{API}/joint/reports/{rid}/notes", timeout=15)
    assert r.status_code in (403, 404), f"pro2 got unexpected {r.status_code}: {r.text}"


def test_pro1_can_read_notes(sess_pro1, matter_pro1):
    rid = matter_pro1["id"]
    r = sess_pro1.get(f"{API}/joint/reports/{rid}/notes", timeout=15)
    assert r.status_code == 200
    notes = r.json()
    assert isinstance(notes, list)
    # per problem statement, at least 1 existing note
    assert len(notes) >= 1, f"expected >=1 existing note, got {notes}"
