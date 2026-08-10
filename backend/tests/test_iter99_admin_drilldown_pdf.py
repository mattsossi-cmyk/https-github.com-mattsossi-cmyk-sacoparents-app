"""Iter 99 — Admin Drilldown PDF Export (court-ready case history).

Covers `GET /api/admin/nd-risk-coordinator/case/{target_user_id}/pdf`:
    * Auth: unauthenticated → 401, non-admin parent → 403.
    * Unknown target_user_id → 404 (same as the JSON endpoint).
    * Admin call returns a `%PDF-` blob with a
      Content-Disposition: attachment header and a filename that
      includes the target_user_id.
    * The builder produces valid PDF bytes for the empty-history edge
      case (called directly with no history rows) — proves the safety
      guard on the "no assessments on file" branch doesn't crash.
    * The builder produces valid PDF bytes for a realistic multi-row
      case with sub-scores + alerts + notes.
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

from admin_nd_case_pdf import build_admin_case_history_pdf  # noqa: E402


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


# ---------- Unit-level: PDF builder edge cases ----------

def test_pdf_builder_handles_empty_history():
    """If a parent somehow ends up with an empty history list the PDF
    still renders cleanly (no crash). Endpoint layer guards with 404
    but the builder should be defensive too."""
    payload = {
        "target_user_id":   "tst_iter99_empty",
        "target_name":      "Empty Case",
        "assessment_count": 0,
        "history":          [],
        "alerts":           [],
    }
    out = build_admin_case_history_pdf(case=payload)
    assert out.startswith(b"%PDF-")
    assert len(out) > 1000  # cover page + summary strip alone still substantial


def test_pdf_builder_handles_full_case():
    """Realistic multi-assessment case with sub-scores, alerts, and
    notes must all render into a valid PDF."""
    payload = {
        "target_user_id":   "tst_iter99_full",
        "target_name":      "Full Case Parent",
        "assessment_count": 2,
        "history": [
            {
                "assessment_id":       "asmt_new",
                "created_at":          "2026-02-01T10:00:00Z",
                "status":              "complete",
                "coparent_name":       "Ex-Partner",
                "tier":                "critical",
                "tier_label":          "Critical",
                "threat_score":        4,
                "vulnerability_score": 4,
                "total_score":         16,
                "sub_scores": {
                    "threat": {
                        "threat_scheduling_disruption": 4,
                        "threat_gaslighting": 4,
                        "threat_sensory_overload": 3,
                    },
                    "vulnerability": {
                        "vuln_executive_burnout": 4,
                        "vuln_memory_fragmentation": 4,
                        "vuln_communication_bottleneck": 3,
                    },
                },
                "notes": "Long-form parent notes describing the escalation.",
            },
            {
                "assessment_id":       "asmt_old",
                "created_at":          "2026-01-01T10:00:00Z",
                "status":              "complete",
                "coparent_name":       "Ex-Partner",
                "tier":                "medium",
                "tier_label":          "Medium",
                "threat_score":        2,
                "vulnerability_score": 3,
                "total_score":         6,
                "sub_scores": {
                    "threat": {"threat_gaslighting": 2},
                    "vulnerability": {"vuln_executive_burnout": 3},
                },
                "notes": "",
            },
        ],
        "alerts": [
            {
                "assessment_id": "asmt_new",
                "tier":          "critical",
                "email_ok":      True,
                "created_at":    "2026-02-01T10:05:00Z",
            },
        ],
    }
    out = build_admin_case_history_pdf(
        case=payload, admin_display_name="Coordinator",
    )
    assert out.startswith(b"%PDF-")
    # Multi-assessment case should be larger than the empty case.
    empty = build_admin_case_history_pdf(case={
        "target_user_id": "tst_iter99_empty",
        "target_name":    "Empty",
        "assessment_count": 0,
        "history": [],
        "alerts":  [],
    })
    assert len(out) > len(empty)


# ---------- Live endpoint: gating ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pdf_endpoint_requires_auth():
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/anything/pdf", timeout=10,
    )
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pdf_endpoint_refuses_non_admin_parent():
    tok = _login(PARENT_EMAIL, PARENT_PASSWORD)
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/anything/pdf",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 403


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pdf_endpoint_unknown_target_returns_404():
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/no-such-user-abc/pdf",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pdf_endpoint_admin_returns_pdf_blob():
    tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not tok:
        pytest.skip("admin login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}

    # Pull the dashboard to find an active target_user_id.
    dash = requests.get(
        f"{API}/admin/nd-risk-coordinator", headers=headers, timeout=15,
    )
    assert dash.status_code == 200
    active = dash.json().get("active_cases") or []
    if not active:
        pytest.skip("no active cases in this environment")
    target_id = active[0]["target_user_id"]

    r = requests.get(
        f"{API}/admin/nd-risk-coordinator/case/{target_id}/pdf",
        headers=headers, timeout=30,
    )
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF-")
    # Content-Disposition includes the target id so filenames don't collide.
    disp = r.headers.get("content-disposition", "").lower()
    assert "attachment" in disp
    assert target_id.lower() in disp
    # Sanity: multi-KB, not an empty stub.
    assert len(r.content) > 5000
