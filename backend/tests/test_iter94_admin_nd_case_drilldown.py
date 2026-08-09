"""Iter 94 — Admin ND Coordinator Case Drilldown.

Covers `GET /api/admin/nd-risk-coordinator/case/{target_user_id}`:
    * Auth: unauthenticated → 401, non-admin parent → 403.
    * Unknown target_user_id → 404 (rather than empty payload — the
      admin should get a clean "no history" signal).
    * Admin call returns full history newest-first + alerts audit.
    * Response never leaks raw matrix answers, only the derived
      scoring/sub-scores + notes for the admin's clinical review.
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
                    BACKEND = ln.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BACKEND = None
API = f"{BACKEND}/api" if BACKEND else None

PARENT_EMAIL = "parent1@test.com"
PARENT_PASSWORD = "TestPass123!"  # noqa: S105  test fixture
ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PASSWORD = "AdminPass123!"  # noqa: S105  test fixture


def _login(email: str, pw: str) -> str | None:
    r = requests.post(
        f"{API}/auth/login", json={"email": email, "password": pw}, timeout=10,
    )
    if r.status_code != 200:
        return None
    return r.json().get("access_token") or r.json().get("token")


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_drilldown_requires_auth():
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/anything", timeout=10,
    )
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_drilldown_refuses_non_admin_parent():
    tok = _login(PARENT_EMAIL, PARENT_PASSWORD)
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/anything",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_drilldown_unknown_target_returns_404():
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/no-such-user-abc",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_drilldown_admin_ok_full_history_shape():
    """End-to-end: pull the dashboard, pick the first active case, then
    drill in and validate the shape + newest-first ordering."""
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}

    dash = requests.get(
        f"{API}/admin/nd-risk-coordinator", headers=headers, timeout=15,
    )
    assert dash.status_code == 200
    active = dash.json().get("active_cases") or []
    if not active:
        pytest.skip("no active cases in this environment to drill down into")
    target_id = active[0]["target_user_id"]

    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/{target_id}",
        headers=headers,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Response shape.
    for k in ("target_user_id", "target_name", "assessment_count",
              "history", "alerts"):
        assert k in body, f"missing {k}: keys={list(body.keys())}"
    assert body["target_user_id"] == target_id
    assert body["assessment_count"] == len(body["history"])
    assert body["assessment_count"] >= 1

    # Row shape.
    row = body["history"][0]
    for k in ("assessment_id", "created_at", "status", "coparent_name",
              "tier", "tier_label", "threat_score", "vulnerability_score",
              "total_score", "sub_scores", "notes"):
        assert k in row, f"row missing {k}: keys={list(row.keys())}"

    # Newest-first ordering.
    ts = [h.get("created_at") or "" for h in body["history"]]
    assert ts == sorted(ts, reverse=True), (
        "history should be newest-first, got: " + ", ".join(ts)
    )

    # Privacy: raw matrix answers must not leak into the row payload.
    for k in ("matrix", "answers"):
        assert k not in row, f"row leaked {k}"

    # Alerts shape (if any) is compact.
    for a in body["alerts"]:
        for k in ("assessment_id", "tier", "email_ok", "created_at"):
            assert k in a, f"alert row missing {k}: keys={list(a.keys())}"
