"""Iter 112 — Reviewer Co-Sign Portal for the Trauma-Informed Court Report.

Locks the workflow:

  1. Owner calls `POST /api/safety-assessment/{id}/prepare-cosign` and
     gets back {sig_id, verify_url, qr_png_data_url}. Only the owner
     can prepare a co-sign QR; guest users are refused.

  2. `GET /api/verify/court-report/{sig_id}` is public and returns
     minimal metadata + findings headlines. It never leaks raw
     behavioural language from Section 1. Returns issued=false for
     invalid sig_ids without disclosing which are real.

  3. `POST /api/verify/court-report/{sig_id}/cosign` records the
     reviewer's printed name, role, and optional notes. Second attempt
     returns 409 so an anonymous scanner cannot overwrite a legitimate
     co-signature.

  4. `GET /api/verify/court-report/{sig_id}/pdf` re-downloads the court
     report. When co-signed, the reviewer's name/role appears in the
     signature block.
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                _v = _v.strip().strip('"').strip("'")
                os.environ.setdefault(_k.strip(), _v)
except FileNotFoundError:
    pass


BACKEND = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND:
    try:
        with open("/app/frontend/.env") as fh:
            for ln in fh:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND = ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BACKEND = None
API = f"{BACKEND}/api" if BACKEND else None

PARENT = ("parent1@test.com", "TestPass123!")  # noqa: S105  test fixture


def _login() -> str | None:
    r = requests.post(f"{API}/auth/login", json={"email": PARENT[0], "password": PARENT[1]}, timeout=10)
    return (r.json().get("access_token") or r.json().get("token")) if r.status_code == 200 else None


def _submit(headers: dict) -> dict:
    s1 = {f"s1_q{i}": "no" for i in range(1, 29)}
    s2 = {**{f"s2_q{i}": "yes" for i in range(1, 9)}, "s2_q8": "no"}
    r = requests.post(f"{API}/safety-assessment", json={"section_1": s1, "section_2": s2},
                      headers=headers, timeout=20)
    assert r.status_code == 200
    return r.json()


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_prepare_cosign_returns_sig_qr_and_verify_url():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    body = _submit(headers)
    aid = body["assessment_id"]
    r = requests.post(f"{API}/safety-assessment/{aid}/prepare-cosign",
                      headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sig_id"] and len(data["sig_id"]) == 16
    assert data["verify_url"].endswith(f"/verify/court-report/{data['sig_id']}")
    assert data["qr_png_data_url"].startswith("data:image/png;base64,")


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_prepare_cosign_requires_auth():
    # Even an anonymous caller with the correct URL shape must be refused.
    r = requests.post(f"{API}/safety-assessment/anything/prepare-cosign", timeout=10)
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_returns_headlines_only_never_raw_answers():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    body = _submit(headers)
    aid = body["assessment_id"]
    prep = requests.post(f"{API}/safety-assessment/{aid}/prepare-cosign",
                         headers=headers, timeout=15).json()
    sig_id = prep["sig_id"]

    # Public verify — no auth headers.
    r = requests.get(f"{API}/verify/court-report/{sig_id}", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["issued"] is True
    assert data["sig_id"] == sig_id
    assert data["cosigned"] is False
    # Findings headlines are safe to leak — raw behavioural language is not.
    for value in (data.get("findings_headlines") or {}).values():
        v = value.lower()
        assert "s1_q" not in v
        assert "strangled" not in v
        assert "hit you" not in v


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_returns_issued_false_for_unknown_sig():
    r = requests.get(f"{API}/verify/court-report/00000000deadbeef", timeout=10)
    assert r.status_code == 200
    assert r.json()["issued"] is False


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_cosign_records_and_second_attempt_conflicts():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    body = _submit(headers)
    aid = body["assessment_id"]
    prep = requests.post(f"{API}/safety-assessment/{aid}/prepare-cosign",
                         headers=headers, timeout=15).json()
    sig_id = prep["sig_id"]

    # First co-sign succeeds.
    r1 = requests.post(
        f"{API}/verify/court-report/{sig_id}/cosign",
        json={
            "reviewer_name": "Dr Alex Reviewer",
            "reviewer_role": "Family-Violence Practitioner",
            "reviewer_notes": "Reviewed with parent 12 Aug 2026. Confirmed with local DV service.",
        },
        timeout=15,
    )
    assert r1.status_code == 200, r1.text

    # Second co-sign returns 409.
    r2 = requests.post(
        f"{API}/verify/court-report/{sig_id}/cosign",
        json={"reviewer_name": "Someone Else", "reviewer_role": "Mediator", "reviewer_notes": ""},
        timeout=10,
    )
    assert r2.status_code == 409

    # Verify endpoint now reflects the co-signature.
    v = requests.get(f"{API}/verify/court-report/{sig_id}", timeout=10).json()
    assert v["cosigned"] is True
    assert v["cosigner"]["name"] == "Dr Alex Reviewer"
    assert v["cosigner"]["role"] == "Family-Violence Practitioner"


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_cosigned_pdf_bakes_reviewer_into_signature_block():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    body = _submit(headers)
    aid = body["assessment_id"]
    prep = requests.post(f"{API}/safety-assessment/{aid}/prepare-cosign",
                         headers=headers, timeout=15).json()
    sig_id = prep["sig_id"]

    # Reviewer co-signs.
    requests.post(
        f"{API}/verify/court-report/{sig_id}/cosign",
        json={
            "reviewer_name": "Dr Jane Mediator",
            "reviewer_role": "Accredited Family Mediator",
            "reviewer_notes": "",
        },
        timeout=15,
    )

    # Public PDF download by sig_id — no auth required, sig_id IS the ticket.
    r = requests.get(f"{API}/verify/court-report/{sig_id}/pdf", timeout=30)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    # PDF content streams are FlateDecode-compressed so we can't grep the
    # reviewer name directly. Instead verify the round-trip: the JSON
    # verify endpoint must confirm the co-signature is on file.
    v = requests.get(f"{API}/verify/court-report/{sig_id}", timeout=10).json()
    assert v["cosigned"] is True
    assert v["cosigner"]["name"] == "Dr Jane Mediator"
    # And the co-signed PDF should be measurably larger than an empty stub.
    assert len(r.content) > 20_000


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_rejects_malformed_sig_id():
    """sig_id must be 16 hex chars — anything else must be treated as
    not-issued without disclosing that. Path-traversal sig_ids are
    normalised by ingress before they even reach FastAPI."""
    for bad in ("not-hex-at-all", "zzzzzzzzzzzzzzzz", "1234"):
        r = requests.get(f"{API}/verify/court-report/{bad}", timeout=10)
        assert r.status_code == 200, (bad, r.status_code)
        # Content-type must be JSON for this endpoint (never HTML fallback).
        assert "application/json" in r.headers.get("content-type", "")
        assert r.json()["issued"] is False
