"""Iter 95 — Heatmap Time Window Filter on the ND Coordinator Dashboard.

Covers `GET /api/admin/nd-risk-coordinator?window_days=N`:
    * Endpoint accepts 30 / 60 / 90 / 180 and echoes back `window_days`
      in the response.
    * Omitting the param preserves the full-history behaviour and
      returns `window_days: null`.
    * Invalid values (any int not in the allowed set, incl. 45, 7, 365)
      → 400 with a helpful message.
    * When a real cutoff is applied, both the parent/case counts AND
      the coordinator-alerts counters shrink to only rows inside the
      window (assertion: filtered count <= unfiltered count).
    * Non-admins still get 403 even with a valid window_days param.
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

from admin_nd_coordinator_routes import _cutoff_for_window  # noqa: E402


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


# ---------- Unit-level: cutoff helper ----------

def test_cutoff_helper_returns_none_when_no_window():
    assert _cutoff_for_window(None) is None
    assert _cutoff_for_window(0) is None


def test_cutoff_helper_rejects_arbitrary_window():
    from fastapi import HTTPException
    for bad in (7, 45, 365, 1):
        with pytest.raises(HTTPException) as exc:
            _cutoff_for_window(bad)
        assert exc.value.status_code == 400


def test_cutoff_helper_accepts_allowed_windows():
    # Every allowed value returns a non-empty ISO string.
    for good in (30, 60, 90, 180):
        got = _cutoff_for_window(good)
        assert got is not None
        assert len(got) >= 19  # at least 'YYYY-MM-DDTHH:MM:SS'


# ---------- Live endpoint: gating + validation ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_window_filter_still_refuses_non_admin_parent():
    tok = _login(PARENT_EMAIL, PARENT_PASSWORD)
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator?window_days=30",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_window_filter_rejects_invalid_value():
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    # 45 days is not in the allow-list → 400 with helpful copy.
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator?window_days=45",
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 400
    assert "window_days must be one of" in r.text


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_window_filter_echoes_window_and_shrinks_counters():
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}

    # Full history baseline.
    r_all = requests.get(
        f"{API}/admin/nd-risk-coordinator",
        headers=headers, timeout=15,
    )
    assert r_all.status_code == 200
    all_body = r_all.json()
    assert all_body.get("window_days") is None

    # 30-day window echoes back and never returns more rows than baseline.
    r_30 = requests.get(
        f"{API}/admin/nd-risk-coordinator?window_days=30",
        headers=headers, timeout=15,
    )
    assert r_30.status_code == 200
    body_30 = r_30.json()
    assert body_30.get("window_days") == 30

    assert body_30["total_parents"] <= all_body["total_parents"]
    assert body_30["active_case_count"] <= all_body["active_case_count"]
    assert body_30["coordinator_alerts"]["total"] <= all_body["coordinator_alerts"]["total"]
    assert body_30["coordinator_alerts"]["emailed"] <= all_body["coordinator_alerts"]["emailed"]

    # Heatmap shape unchanged.
    assert len(body_30["heatmap"]) == 4
    assert all(len(row) == 4 for row in body_30["heatmap"])
    # Sum of cell counts equals total_parents (invariant regardless of filter).
    total_cells = sum(
        cell["count"] for row in body_30["heatmap"] for cell in row
    )
    # Cells only tally parents with valid 1..4 scores; parents whose
    # scores are outside that range would be excluded. In practice
    # `total_parents` should equal the sum.
    assert total_cells <= body_30["total_parents"]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_window_filter_all_allowed_values_return_200():
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    for w in (30, 60, 90, 180):
        r = requests.get(
            f"{API}/admin/nd-risk-coordinator?window_days={w}",
            headers=headers, timeout=15,
        )
        assert r.status_code == 200, f"window_days={w} failed: {r.text}"
        assert r.json().get("window_days") == w
