"""Journey Summary (celebrated flag + combined PDF) backend tests."""
import os
import subprocess
import tempfile
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prepared-parents.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _register_fresh():
    email = f"TEST_js_{uuid.uuid4().hex[:10]}@test.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "Fresh Parent"})
    assert r.status_code in (200, 201), r.text
    return email, r.json().get("access_token") or _login(email, "TestPass123!")


@pytest.fixture(scope="module")
def parent1_token():
    return _login("parent1@test.com", "TestPass123!")


@pytest.fixture(scope="module")
def fresh():
    email, tok = _register_fresh()
    return {"email": email, "token": tok}


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# --- celebrated flag -------------------------------------------------
class TestCelebratedFlag:
    def test_get_unauth_401(self):
        assert requests.get(f"{API}/journey-summary/celebrated").status_code in (401, 403)

    def test_post_unauth_401(self):
        assert requests.post(f"{API}/journey-summary/celebrated").status_code in (401, 403)

    def test_fresh_user_celebrated_false(self, fresh):
        r = requests.get(f"{API}/journey-summary/celebrated", headers=_h(fresh["token"]))
        assert r.status_code == 200, r.text
        assert r.json() == {"celebrated": False}

    def test_post_sets_true_idempotent(self, fresh):
        r1 = requests.post(f"{API}/journey-summary/celebrated", headers=_h(fresh["token"]))
        assert r1.status_code == 200
        assert r1.json() == {"celebrated": True}
        # idempotent
        r2 = requests.post(f"{API}/journey-summary/celebrated", headers=_h(fresh["token"]))
        assert r2.status_code == 200
        assert r2.json() == {"celebrated": True}
        # GET reflects
        r3 = requests.get(f"{API}/journey-summary/celebrated", headers=_h(fresh["token"]))
        assert r3.json() == {"celebrated": True}


# --- PDF endpoint ----------------------------------------------------
def _pdf_text(blob: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(blob)
        path = f.name
    out = subprocess.run(["/usr/bin/pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True)
    return out.stdout


class TestJourneySummaryPdf:
    def test_unauth_401(self):
        assert requests.get(f"{API}/journey-summary/pdf").status_code in (401, 403)

    def test_fresh_user_pdf_structure(self, fresh):
        r = requests.get(f"{API}/journey-summary/pdf", headers=_h(fresh["token"]))
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert "SA_CoParents_Journey_Summary.pdf" in r.headers.get("content-disposition", "")
        assert r.content[:4] == b"%PDF"
        text = _pdf_text(r.content)
        assert "Journey Summary" in text
        assert "Progress: 0 of 5 assessments completed" in text
        assert "If you have safety concerns, speak with a qualified professional" in text
        assert "1. Self-Assessment" in text
        assert "2. Co-Parenting" in text
        assert "3." in text and "Educational" in text
        assert "4." in text and "Medical" in text
        assert "5." in text and "Psychological" in text
        # Fresh → all five not completed
        assert text.count("Not completed yet.") == 5
        assert "not legal advice" in text.lower()

    def test_parent1_pdf_has_progress(self, parent1_token):
        r = requests.get(f"{API}/journey-summary/pdf", headers=_h(parent1_token))
        assert r.status_code == 200
        text = _pdf_text(r.content)
        assert "Journey Summary" in text
        # parent1 has at least some assessments completed per prior iteration state
        import re
        m = re.search(r"Progress:\s+(\d) of 5 assessments completed", text)
        assert m, text[:400]
        assert 0 <= int(m.group(1)) <= 5
        assert "1. Self-Assessment" in text
        assert "5." in text
