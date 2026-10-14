"""Backend tests for professional tools:
 - POST /professional/archive/finished + PUT /professional/archive/bulk restore
 - GET /professional/joint-alignment/cases/{case_id}/progress.pdf?include_notes=true
 - GET/PUT /professional/digest and /professional/digest/unsubscribe
"""
import os
import subprocess
import tempfile

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password="TestPass123!"):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def tok_parent1():
    return _login("parent1@test.com")


@pytest.fixture(scope="module")
def tok_parent2():
    return _login("parent2@test.com")


@pytest.fixture(scope="module")
def tok_ccparent():
    return _login("ccparent@test.com")


# ---------- Archive finished + bulk restore ----------

def test_archive_finished_codes_and_cases_roundtrip(tok_parent1, tok_parent2):
    h1 = _hdr(tok_parent1)

    # Invalid kind -> 422
    bad = requests.post(f"{API}/professional/archive/finished", json={"kind": "bogus"}, headers=h1)
    assert bad.status_code == 422, bad.text

    # Unauth -> 401
    unauth = requests.post(f"{API}/professional/archive/finished", json={"kind": "codes"})
    assert unauth.status_code == 401

    # Archive codes
    rc = requests.post(f"{API}/professional/archive/finished", json={"kind": "codes"}, headers=h1)
    assert rc.status_code == 200, rc.text
    code_refs = rc.json()["refs"]
    assert isinstance(code_refs, list)
    print(f"finished code refs: {len(code_refs)}")

    # Archive cases
    rs = requests.post(f"{API}/professional/archive/finished", json={"kind": "cases"}, headers=h1)
    assert rs.status_code == 200, rs.text
    case_refs = rs.json()["refs"]
    print(f"finished case refs: {len(case_refs)}")

    all_refs = code_refs + case_refs
    assert len(all_refs) > 0, "expected some finished items"

    try:
        # parent2 bulk with parent1 refs -> count 0 (ownership check)
        if all_refs:
            r = requests.put(f"{API}/professional/archive/bulk",
                             json={"refs": all_refs, "archived": False},
                             headers=_hdr(tok_parent2))
            assert r.status_code == 200, r.text
            assert r.json()["count"] == 0

        # Unauth
        u = requests.put(f"{API}/professional/archive/bulk", json={"refs": all_refs, "archived": False})
        assert u.status_code == 401
    finally:
        # Always restore
        if all_refs:
            restore = requests.put(f"{API}/professional/archive/bulk",
                                   json={"refs": all_refs, "archived": False},
                                   headers=h1)
            assert restore.status_code == 200, restore.text
            assert restore.json()["count"] == len(all_refs), restore.json()


# ---------- Progress PDF include_notes ----------

def _pdf_text(pdf_bytes):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
    return out.stdout


def test_progress_pdf_include_notes(tok_parent1, tok_parent2):
    url = f"{API}/professional/joint-alignment/cases/SA-460316/progress.pdf"
    with_notes = requests.get(url, params={"include_notes": "true"}, headers=_hdr(tok_parent1))
    assert with_notes.status_code == 200, with_notes.text
    assert with_notes.headers["content-type"].startswith("application/pdf")
    txt = _pdf_text(with_notes.content)
    assert "Private professional notes, not shared with parents" in txt, txt[:500]

    without = requests.get(url, headers=_hdr(tok_parent1))
    assert without.status_code == 200
    txt2 = _pdf_text(without.content)
    assert "Private professional notes, not shared with parents" not in txt2

    # Non-owner -> 404
    nope = requests.get(url, params={"include_notes": "true"}, headers=_hdr(tok_parent2))
    assert nope.status_code == 404


# ---------- Digest preferences + unsubscribe ----------

def test_digest_pref_and_unsubscribe(tok_parent1, tok_ccparent):
    h1 = _hdr(tok_parent1)
    hc = _hdr(tok_ccparent)

    r = requests.get(f"{API}/professional/digest", headers=h1)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["eligible"] is True

    rc = requests.get(f"{API}/professional/digest", headers=hc)
    assert rc.status_code == 200
    assert rc.json()["eligible"] is False

    # Bad token -> 400 HTML
    bad = requests.get(f"{API}/professional/digest/unsubscribe", params={"token": "nope"})
    assert bad.status_code == 400
    assert "html" in bad.headers.get("content-type", "").lower()

    # Valid token via make_unsubscribe_token
    import sys
    sys.path.insert(0, "/app/backend")
    from professional_digest import make_unsubscribe_token  # noqa
    # Need parent1 user_id -- fetch via /auth/me
    me = requests.get(f"{API}/auth/me", headers=h1).json()
    uid = me.get("user_id") or me.get("id")
    assert uid, me

    tok = make_unsubscribe_token(uid)
    ok = requests.get(f"{API}/professional/digest/unsubscribe", params={"token": tok})
    assert ok.status_code == 200
    assert "unsubscribed" in ok.text.lower()

    # enabled now false
    r2 = requests.get(f"{API}/professional/digest", headers=h1)
    assert r2.json()["enabled"] is False

    # Restore enabled=True
    put = requests.put(f"{API}/professional/digest", json={"enabled": True}, headers=h1)
    assert put.status_code == 200
    assert put.json()["enabled"] is True

    # Final state check
    final = requests.get(f"{API}/professional/digest", headers=h1).json()
    assert final["enabled"] is True
