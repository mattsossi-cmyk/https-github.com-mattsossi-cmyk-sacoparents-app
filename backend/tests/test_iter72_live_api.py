"""
Iteration 72 — live API integration tests against REACT_APP_BACKEND_URL.

Adapted to actual server routes (edu_deep_routes.py / psych_deep_routes.py /
signature_verify_routes.py). Covers:
  - Narrative fields (parts_narrative/opening_story/closing_story) in
    edu-deep + psych-deep generated reports
  - Signature verify endpoint (valid + tampered + missing fields)
  - Signed PDF smoke (edu + psych)
"""
import os
import hashlib
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

EMAIL = "parent1@test.com"
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": EMAIL, "password": PASSWORD,
                            "name": "Sam Parent"}, timeout=30)
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    return body.get("access_token") or body.get("token")


@pytest.fixture(scope="module")
def H(token):
    return {"Authorization": f"Bearer {token}"}


def _all_3s():
    return {f"p{p}_q{5*(p-1)+i}": 3 for p in range(1, 6) for i in range(1, 6)}


def _seed(prefix, H):
    # Set profile then bulk-answer 25 items using the actual schema keys
    requests.post(f"{BASE_URL}/api/{prefix}/profile",
                  headers=H, json={"child_name": "Alex"}, timeout=30)
    r = requests.post(f"{BASE_URL}/api/{prefix}/answers/bulk",
                     headers=H, json={"answers": _all_3s()}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("answered", 0) >= 25, body
    r2 = requests.post(f"{BASE_URL}/api/{prefix}/complete", headers=H, timeout=30)
    assert r2.status_code == 200, r2.text


# ---- Narrative fields ----
@pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep"])
def test_report_has_narrative(prefix, H):
    _seed(prefix, H)
    r = requests.post(f"{BASE_URL}/api/{prefix}/report/generate",
                      headers=H, timeout=120)
    assert r.status_code == 200, r.text[:600]
    body = r.json()
    report = body.get("report") or {}
    assert isinstance(report.get("parts_narrative"), list)
    assert len(report["parts_narrative"]) == 5, report["parts_narrative"]
    assert report.get("opening_story"), "opening_story empty"
    assert report.get("closing_story"), "closing_story empty"
    # Verify per-part shape
    for p in report["parts_narrative"]:
        assert p.get("band") in ("high", "moderate", "low", "unrated")
        assert "narrative" in p
        assert isinstance(p.get("strengths", []), list)
        assert isinstance(p.get("growth", []), list)


# ---- Verify endpoint ----
def _compute_sig(name, ts, note):
    secret = os.environ.get("SIGNATURE_VERIFY_SECRET",
                            "sacop-signature-verify-secret-dev-only")
    return hashlib.sha256(
        f"{secret}|{name}|{ts}|{note}".encode("utf-8")
    ).hexdigest()[:16]


def test_verify_valid():
    name, ts, note = "Sam Parent", "2026-02-06T12:34:56+00:00", "hi"
    sig = _compute_sig(name, ts, note)
    r = requests.get(f"{BASE_URL}/api/verify/{sig}",
                     params={"n": name, "t": ts, "note": note}, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["untampered"] is True, b
    assert b["signed_by"] == name
    assert b["signed_at"] == ts
    assert b["signed_note"] == note


def test_verify_tampered():
    name, ts, note = "Sam Parent", "2026-02-06T12:34:56+00:00", "hi"
    sig = _compute_sig(name, ts, note)
    r = requests.get(f"{BASE_URL}/api/verify/{sig}",
                     params={"n": "Someone Else", "t": ts, "note": note},
                     timeout=30)
    assert r.status_code == 200
    b = r.json()
    assert b["untampered"] is False
    assert b.get("reason") == "hash_mismatch"


def test_verify_missing_fields():
    r = requests.get(f"{BASE_URL}/api/verify/deadbeefdeadbeef", timeout=30)
    assert r.status_code == 200
    b = r.json()
    assert b["untampered"] is False
    assert b.get("reason") == "missing_signature_fields"


# ---- Signed PDF smoke (GET /{prefix}/report/pdf?sign=true&note=hi) ----
@pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep"])
def test_signed_pdf_smoke(prefix, H):
    _seed(prefix, H)
    # ensure report exists
    requests.post(f"{BASE_URL}/api/{prefix}/report/generate", headers=H, timeout=120)
    r = requests.get(f"{BASE_URL}/api/{prefix}/report/pdf",
                     params={"sign": "true", "note": "hi"},
                     headers=H, timeout=60)
    assert r.status_code == 200, r.text[:400]
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 5000
