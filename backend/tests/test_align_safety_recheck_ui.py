# Quick recheck: old Safety Assessment routes gone, share/secure-docs lists clean, complete report step line
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "parent1@test.com", "password": "TestPass123!"})
    if r.status_code != 200:
        pytest.skip("login failed")
    d = r.json()
    return d.get("access_token") or d.get("token")


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


GET_ROUTES = ["questions", "me", "me/history", "x/pdf", "shared/abc", "x/court-report", "x/one-pager"]
POST_ROUTES = ["", "x/email", "x/email-mediator", "x/share-link", "x/regenerate-summaries"]


@pytest.mark.parametrize("p", GET_ROUTES)
def test_old_get_routes_gone(h, p):
    r = requests.get(f"{BASE_URL}/api/safety-assessment/{p}".rstrip("/"), headers=h)
    assert r.status_code in (404, 405), (p, r.status_code)


@pytest.mark.parametrize("p", POST_ROUTES)
def test_old_post_routes_gone(h, p):
    r = requests.post(f"{BASE_URL}/api/safety-assessment/{p}".rstrip("/"), headers=h, json={})
    assert r.status_code in (404, 405), (p, r.status_code)


def test_next_steps_safety_gone(h):
    assert requests.get(f"{BASE_URL}/api/next-steps/safety", headers=h).status_code == 404


def test_verify_court_report_gone():
    assert requests.get(f"{BASE_URL}/api/verify/court-report/x").status_code == 404


def test_share_mine_no_safety(h):
    r = requests.get(f"{BASE_URL}/api/share/mine", headers=h)
    assert r.status_code == 200
    data = r.json()
    items = data if isinstance(data, list) else (data.get("links") or data.get("items") or data.get("shares") or [])
    assert all((i.get("doc_type") != "safety") for i in items)


def test_secure_docs_sent_no_safety(h):
    r = requests.get(f"{BASE_URL}/api/secure-docs/sent", headers=h)
    assert r.status_code == 200
    assert "safety assessment" not in r.text.lower()


def test_complete_report_pdf_step_line(h):
    r = requests.post(f"{BASE_URL}/api/portal/complete-report-pdf", headers=h, json={})
    assert r.status_code == 200, r.text[:300]
    from pypdf import PdfReader
    text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Safety step: see SACOparentsAlign" in text and "Safety step: not started" not in text
    assert "Flagged" not in text
