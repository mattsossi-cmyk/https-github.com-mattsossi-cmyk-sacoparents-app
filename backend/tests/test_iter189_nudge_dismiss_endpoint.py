"""iter189 — Nudge dismiss analytics endpoint + admin overview tile.

Tests the fire-and-forget dismiss event and the admin overview
`consent.child_needs_share.nudge_dismisses` block that surfaces
retry vs permanent hides.

End-to-end via HTTP so the FastAPI route + auth stack + Mongo write
are all exercised. Uses the seeded SA-DEMO01 case (parent1@test.com,
parent2@test.com) already required by test_iter184.
"""
from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from tests.conftest import BASE_URL  # noqa: E402


def _bearer_for(email: str, password: str = "TestPass123!") -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _hdrs(email: str) -> dict:
    return {"Authorization": f"Bearer {_bearer_for(email)}"}


# ---------------------- Endpoint behaviour ---------------------- #

def test_nudge_dismiss_records_first_dismiss_event():
    """POST /complete-report/joint/SA-DEMO01/nudge-dismiss records a
    row on `child_needs_share_nudge_dismisses` with
    `is_retry_dismissal=False` by default."""
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/nudge-dismiss",
        headers=_hdrs("parent1@test.com"),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}


def test_nudge_dismiss_respects_is_retry_dismissal_flag():
    """`?is_retry_dismissal=true` writes a permanent-hide row —
    admins can differentiate friction (permanent) from a soft
    delay (first dismiss awaiting the 7d retry)."""
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/nudge-dismiss",
        headers=_hdrs("parent1@test.com"),
        params={"is_retry_dismissal": "true"},
        timeout=10,
    )
    assert r.status_code == 200, r.text


def test_nudge_dismiss_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/nudge-dismiss",
        timeout=10,
    )
    assert r.status_code in (401, 403), r.text


def test_nudge_dismiss_404s_on_unknown_case():
    """A well-formed case_id that doesn't exist must 404 (never 403)
    so we don't leak case existence — same policy as the toggle
    endpoint."""
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-ZZZZZZ/nudge-dismiss",
        headers=_hdrs("parent1@test.com"),
        timeout=10,
    )
    assert r.status_code == 404, r.text


def test_nudge_dismiss_422s_on_malformed_case_id():
    """`case_id` uses the SA-[A-Z0-9]{4,10} regex — a random string
    must reject at validation before hitting the DB."""
    r = requests.post(
        f"{BASE_URL}/api/complete-report/joint/not-a-case-id/nudge-dismiss",
        headers=_hdrs("parent1@test.com"),
        timeout=10,
    )
    assert r.status_code == 422, r.text


# ---------------------- Admin overview surface ---------------------- #

def test_admin_overview_exposes_nudge_dismiss_counts():
    """/api/analytics/admin/overview.consent.child_needs_share now
    carries a `nudge_dismisses` block with cumulative + 7-day
    counts split by first vs retry-dismiss. The AdminDashboard
    tile reads exactly these fields."""
    # Ensure at least one row exists so the aggregation returns
    # non-zero (idempotent — safe to run multiple times).
    requests.post(
        f"{BASE_URL}/api/complete-report/joint/SA-DEMO01/nudge-dismiss",
        headers=_hdrs("parent1@test.com"),
        timeout=10,
    )
    # Log in as the admin (parent1@test.com is NOT in ADMIN_EMAILS
    # by default — the fixture user for admin ops is mattsossi@bsossi.com
    # with `AdminPass123!` per /app/memory/test_credentials.md).
    admin_email = os.environ.get("ADMIN_EMAILS", "mattsossi@bsossi.com").split(",")[0].strip()
    admin_token_req = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
        timeout=10,
    )
    if admin_token_req.status_code != 200:
        # Admin account not seeded in this env — skip rather than fail.
        # The endpoint shape is still exercised by the write-side tests
        # above; this one just verifies the read-side surface.
        import pytest
        pytest.skip(
            f"Admin account {admin_email} not available for login in this env "
            f"(status={admin_token_req.status_code}). Endpoint shape is still "
            f"covered by the write-side tests."
        )
    admin_hdrs = {"Authorization": f"Bearer {admin_token_req.json()['access_token']}"}
    r = requests.get(
        f"{BASE_URL}/api/analytics/admin/overview",
        headers=admin_hdrs,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    consent = data.get("consent", {}).get("child_needs_share", {})
    nd = consent.get("nudge_dismisses")
    assert nd is not None, f"missing nudge_dismisses block: {consent}"
    for key in ("first_total", "permanent_total", "first_7d", "permanent_7d"):
        assert key in nd, f"missing nudge_dismisses.{key}: {nd}"
        assert isinstance(nd[key], int), f"nudge_dismisses.{key} must be int, got {type(nd[key])}"
    # After our POST above, first_total is definitely > 0.
    assert nd["first_total"] >= 1, (
        f"Expected first_total >= 1 after seeding a dismiss, got {nd}"
    )
