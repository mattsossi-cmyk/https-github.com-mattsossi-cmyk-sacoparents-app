"""Iter 88 — Operator-only reviewer panel CRUD.

Exercises the new POST / PATCH / DELETE endpoints that let the operator
manage `reviewer_panel.json` from an in-app admin page instead of hand-
editing the file.

The tests use the live API against the preview URL and clean up any
seeded rows so the panel returns to its baseline empty state.
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
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass


BACKEND = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND:
    try:
        with open("/app/frontend/.env") as fh:
            for ln in fh:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BACKEND = ln.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except FileNotFoundError:
        BACKEND = None

API = f"{BACKEND}/api" if BACKEND else None

OPERATOR_EMAIL = "mattsossi@bsossi.com"
OPERATOR_PASSWORD = "AdminPass123!"
NON_OP_EMAIL = "parent1@test.com"
NON_OP_PASSWORD = "TestPass123!"


def _login(email: str, password: str):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=10)
    if r.status_code != 200:
        return None
    body = r.json()
    return body.get("access_token") or body.get("token")


def _cleanup_seed_reviewers():
    """Remove any test rows we might have left behind on prior runs so this
    test is idempotent."""
    tok = _login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    if not tok:
        return
    headers = {"Authorization": f"Bearer {tok}"}
    panel = requests.get(f"{API}/reviewer-panel", timeout=10).json()
    for r in panel.get("reviewers", []):
        if r.get("name", "").startswith("__pytest_"):
            requests.delete(f"{API}/reviewer-panel/reviewers/{r['id']}",
                            headers=headers, timeout=10)


@pytest.fixture(autouse=True)
def _clean():
    _cleanup_seed_reviewers()
    yield
    _cleanup_seed_reviewers()


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_roles_endpoint_public():
    """No auth required — used by the admin form's role dropdown."""
    r = requests.get(f"{API}/reviewer-panel/reviewers/roles", timeout=10)
    assert r.status_code == 200
    keys = [x["key"] for x in r.json()["roles"]]
    assert "dv_advocate" in keys
    assert "clinician" in keys


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_non_operator_cannot_add():
    tok = _login(NON_OP_EMAIL, NON_OP_PASSWORD)
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.post(
        f"{API}/reviewer-panel/reviewers",
        headers={"Authorization": f"Bearer {tok}"},
        json={"name": "__pytest_bad", "role": "other", "review_date": "2026-02-27"},
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_operator_add_patch_delete_round_trip():
    tok = _login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    if not tok:
        pytest.skip("operator login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}

    # ADD
    added = requests.post(
        f"{API}/reviewer-panel/reviewers",
        headers=headers,
        json={
            "name":         "__pytest_Dr. Chris Reviewer, LCSW",
            "role":         "clinician",
            "org":          "Test Clinic",
            "review_date":  "2026-02-27",
            "review_scope": "Sections 1 & 2 only",
            "attestation":  "Reads carefully; scoring rules are conservative.",
        },
        timeout=10,
    )
    assert added.status_code == 200, added.text[:200]
    reviewer = added.json()["reviewer"]
    rid = reviewer["id"]
    assert len(rid) == 12
    assert reviewer["role"] == "clinician"
    assert reviewer["org"] == "Test Clinic"

    # Public panel reflects the new row.
    public = requests.get(f"{API}/reviewer-panel", timeout=10).json()
    assert any(r["id"] == rid for r in public["reviewers"])
    assert public["count"] >= 1
    assert public["status"] == "reviewed"

    # PATCH — subset of fields.
    patched = requests.patch(
        f"{API}/reviewer-panel/reviewers/{rid}",
        headers=headers,
        json={"attestation": "Updated attestation for field-testing."},
        timeout=10,
    )
    assert patched.status_code == 200
    assert patched.json()["reviewer"]["attestation"] == "Updated attestation for field-testing."
    # Untouched fields are unchanged.
    assert patched.json()["reviewer"]["name"].startswith("__pytest_Dr. Chris")

    # PATCH validates role.
    bad_role = requests.patch(
        f"{API}/reviewer-panel/reviewers/{rid}",
        headers=headers,
        json={"role": "emperor"},
        timeout=10,
    )
    assert bad_role.status_code == 400
    assert "role" in bad_role.json()["detail"].lower()

    # PATCH validates date.
    bad_date = requests.patch(
        f"{API}/reviewer-panel/reviewers/{rid}",
        headers=headers,
        json={"review_date": "not-a-date-9999-99-99"},
        timeout=10,
    )
    # Pydantic length validator will 422 an oversized string, so accept either.
    assert bad_date.status_code in (400, 422)

    # DELETE
    removed = requests.delete(
        f"{API}/reviewer-panel/reviewers/{rid}",
        headers=headers,
        timeout=10,
    )
    assert removed.status_code == 200
    assert removed.json()["removed_id"] == rid

    # DELETE nonexistent returns 404.
    missing = requests.delete(
        f"{API}/reviewer-panel/reviewers/{rid}",
        headers=headers,
        timeout=10,
    )
    assert missing.status_code == 404

    # Panel no longer includes it.
    public2 = requests.get(f"{API}/reviewer-panel", timeout=10).json()
    assert not any(r["id"] == rid for r in public2["reviewers"])


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_operator_add_rejects_bad_role_and_date():
    tok = _login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    if not tok:
        pytest.skip("operator login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    # Bad role — reaches handler, returns 400.
    bad_role = requests.post(
        f"{API}/reviewer-panel/reviewers",
        headers=headers,
        json={"name": "__pytest_valid", "role": "emperor", "review_date": "2026-02-27"},
        timeout=10,
    )
    assert bad_role.status_code == 400
    # Bad date — reaches handler, returns 400.
    bad_date = requests.post(
        f"{API}/reviewer-panel/reviewers",
        headers=headers,
        json={"name": "__pytest_valid2", "role": "other", "review_date": "2026-13-99"},
        timeout=10,
    )
    assert bad_date.status_code == 400
