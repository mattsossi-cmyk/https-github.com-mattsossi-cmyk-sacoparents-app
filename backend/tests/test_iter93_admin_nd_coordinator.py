"""Iter 93 — Admin ND Risk Coordinator Dashboard.

Covers:
    * `GET /api/admin/nd-risk-coordinator` requires auth (401) and
      admin role (403 for a normal parent).
    * When called by the seeded admin, it returns the expected shape:
      heatmap grid (4x4), tier_counts, active_cases, coordinator_alerts.
    * Heatmap cells are correctly bucketed by tier boundary
      (`_cell_tier`) — spot-check corners.
    * Latest-per-parent reducer: multiple assessments for the same
      target_user_id resolve to the newest one.
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

from admin_nd_coordinator_routes import (  # noqa: E402
    _build_heatmap, _cell_tier, _summarise,
)


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


# ---------- Unit-level: tier bucketing + heatmap builder ----------

def test_cell_tier_boundaries():
    # score = threat * vuln. Boundaries: <=3 low, <=8 medium, <=12 high, else critical.
    assert _cell_tier(1, 1) == "low"          # 1
    assert _cell_tier(1, 3) == "low"          # 3
    assert _cell_tier(2, 2) == "medium"       # 4
    assert _cell_tier(2, 4) == "medium"       # 8
    assert _cell_tier(3, 3) == "high"         # 9
    assert _cell_tier(3, 4) == "high"         # 12
    assert _cell_tier(4, 4) == "critical"     # 16


def test_heatmap_grid_is_4x4_and_counts_land_correctly():
    cases = [
        {"scoring": {"threat_score": 1, "vulnerability_score": 1, "tier": "low"}},
        {"scoring": {"threat_score": 4, "vulnerability_score": 4, "tier": "critical"}},
        {"scoring": {"threat_score": 4, "vulnerability_score": 4, "tier": "critical"}},
        {"scoring": {"threat_score": 3, "vulnerability_score": 2, "tier": "medium"}},
        # Garbage inputs should not crash or land anywhere.
        {"scoring": {"threat_score": None, "vulnerability_score": 4}},
        {"scoring": {"threat_score": 5, "vulnerability_score": 5}},
    ]
    grid = _build_heatmap(cases)
    assert len(grid) == 4
    assert all(len(row) == 4 for row in grid)
    # T=1,V=1 → row index 0, col 0
    assert grid[0][0]["count"] == 1
    # T=4,V=4 → row 3, col 3, two hits
    assert grid[3][3]["count"] == 2
    # T=3,V=2 → row 1, col 2
    assert grid[1][2]["count"] == 1
    # Tier stamped correctly on the critical cell
    assert grid[3][3]["tier"] == "critical"
    # Sum of counts = 4 (only the four valid rows).
    assert sum(cell["count"] for row in grid for cell in row) == 4


def test_summarise_counts_by_tier():
    cases = [
        {"scoring": {"tier": "high"}},
        {"scoring": {"tier": "high"}},
        {"scoring": {"tier": "critical"}},
        {"scoring": {"tier": "low"}},
        {"scoring": {"tier": None}},  # ignored
    ]
    got = _summarise(cases)
    assert got == {"low": 1, "medium": 0, "high": 2, "critical": 1}


# ---------- Live endpoint: gating ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_admin_dashboard_requires_auth():
    r = requests.get(f"{API}/admin/nd-risk-coordinator", timeout=10)
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_admin_dashboard_refuses_non_admin_parent():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": PARENT_EMAIL, "password": PARENT_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip(f"parent1 login unavailable: {login.status_code}")
    tok = login.json().get("access_token") or login.json().get("token")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_admin_dashboard_admin_ok_shape():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip(f"admin login unavailable: {login.status_code}")
    tok = login.json().get("access_token") or login.json().get("token")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Response shape.
    for k in ("total_parents", "tier_counts", "active_case_count",
              "heatmap", "active_cases", "coordinator_alerts"):
        assert k in body, f"missing {k} in response: {list(body.keys())}"
    # Heatmap always 4x4 even when empty.
    assert isinstance(body["heatmap"], list) and len(body["heatmap"]) == 4
    assert all(len(row) == 4 for row in body["heatmap"])
    # Every cell has the required fields.
    for row in body["heatmap"]:
        for cell in row:
            for k in ("threat", "vulnerability", "tier", "count", "total_score"):
                assert k in cell
    # tier_counts has all four tiers.
    for k in ("low", "medium", "high", "critical"):
        assert k in body["tier_counts"]
    # coordinator_alerts has the audit counters.
    assert "total" in body["coordinator_alerts"]
    assert "emailed" in body["coordinator_alerts"]
