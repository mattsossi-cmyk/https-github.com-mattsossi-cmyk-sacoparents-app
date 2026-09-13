"""iter189c — Preview HTML + Nudge Copy config + Slack mirror + Sparkline.

Covers:
  * GET  /api/admin/consent-digest/preview.html
        Admin-gated. Returns an HTML document that includes the
        "PREVIEW · not sent" banner. Does not write a dedupe row
        or send email.
  * GET  /api/public/nudge-copy/child-needs-share
        Public. Returns default copy when no admin has customised.
  * POST /api/admin/nudge-copy/child-needs-share
        Admin-gated. Upserts. The next public GET reflects the update.
  * POST /api/admin/nudge-copy/child-needs-share/reset
        Admin-gated. Wipes override → public GET falls back to defaults.
  * `overview.consent.child_needs_share.nudge_dismisses.weekly_4w`
        Present, has 4 buckets, monotonically increasing week_start.
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

from tests.conftest import BASE_URL  # noqa: E402


ADMIN_EMAIL = "mattsossi@bsossi.com"
ADMIN_PASSWORD = "AdminPass123!"


def _bearer(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(
            f"Login as {email} failed ({r.status_code}) — env may not have "
            f"the seeded account. {r.text[:200]}"
        )
    return r.json()["access_token"]


def _admin_hdrs() -> dict:
    return {"Authorization": f"Bearer {_bearer(ADMIN_EMAIL, ADMIN_PASSWORD)}"}


def _parent_hdrs() -> dict:
    return {"Authorization": f"Bearer {_bearer('parent1@test.com', 'TestPass123!')}"}


# ---------------------- Preview HTML ---------------------- #

def test_preview_html_requires_admin():
    r = requests.get(
        f"{BASE_URL}/api/admin/consent-digest/preview.html", timeout=10,
    )
    assert r.status_code in (401, 403), r.text
    # Signed-in but non-admin parent must also 403.
    r = requests.get(
        f"{BASE_URL}/api/admin/consent-digest/preview.html",
        headers=_parent_hdrs(),
        timeout=10,
    )
    assert r.status_code == 403, r.text


def test_preview_html_renders_banner_and_digest_body():
    r = requests.get(
        f"{BASE_URL}/api/admin/consent-digest/preview.html",
        headers=_admin_hdrs(),
        timeout=15,
    )
    assert r.status_code == 200, r.text[:400]
    ct = r.headers.get("content-type", "")
    assert ct.startswith("text/html"), ct
    body = r.text
    # PREVIEW banner must be present so screenshots can't be confused
    # with a real send.
    assert "PREVIEW · not sent." in body
    # Digest headline copy — locked to the email builder.
    assert "Consent-adoption snapshot" in body
    # The cache header must include no-store so CDN doesn't cache an
    # old preview. Middleware may append additional directives.
    assert "no-store" in r.headers.get("cache-control", "").lower()


# ---------------------- Nudge Copy config ---------------------- #

def test_public_nudge_copy_returns_defaults_when_no_override():
    # Ensure baseline: reset the override first.
    requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/reset",
        headers=_admin_hdrs(),
        timeout=10,
    )
    r = requests.get(
        f"{BASE_URL}/api/public/nudge-copy/child-needs-share", timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_default"] is True
    assert "share these highlights" in data["headline"].lower()
    assert data["subhead"]
    assert "no-store" in r.headers.get("cache-control", "").lower()


def test_admin_can_update_and_reset_nudge_copy():
    new_headline = "Would you like to share these with your co-parent?"
    new_subhead = (
        "Your Child Needs highlights stay private by default. Toggling "
        "this on unlocks the joint report's section 5 only after both "
        "parents opt in. You can turn it off any time."
    )
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
        headers=_admin_hdrs(),
        json={"headline": new_headline, "subhead": new_subhead,
              "note": "softer variant · iter189c smoke test"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["headline"] == new_headline
    assert data["subhead"] == new_subhead
    assert data["is_default"] is False

    # Public GET must now reflect the override.
    r = requests.get(
        f"{BASE_URL}/api/public/nudge-copy/child-needs-share", timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["headline"] == new_headline
    assert data["is_default"] is False

    # Reset → public GET falls back to defaults.
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/reset",
        headers=_admin_hdrs(),
        timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_default"] is True

    r = requests.get(
        f"{BASE_URL}/api/public/nudge-copy/child-needs-share", timeout=10,
    )
    assert r.json()["is_default"] is True


def test_admin_nudge_copy_rejects_oversized_headline():
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
        headers=_admin_hdrs(),
        json={"headline": "x" * 200, "subhead": "y" * 300},
        timeout=10,
    )
    # Pydantic validator returns 422.
    assert r.status_code == 422, r.text


def test_admin_nudge_copy_write_requires_admin():
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
        json={"headline": "ok headline text", "subhead": "ok subhead text here"},
        timeout=10,
    )
    assert r.status_code in (401, 403), r.text
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
        headers=_parent_hdrs(),
        json={"headline": "ok headline text", "subhead": "ok subhead text here"},
        timeout=10,
    )
    assert r.status_code == 403, r.text


# ---------------------- Sparkline weekly_4w shape ---------------------- #

def test_admin_overview_ships_weekly_4w_sparkline_buckets():
    r = requests.get(
        f"{BASE_URL}/api/analytics/admin/overview",
        headers=_admin_hdrs(),
        timeout=15,
    )
    assert r.status_code == 200, r.text
    weekly = (
        r.json()
        .get("consent", {})
        .get("child_needs_share", {})
        .get("nudge_dismisses", {})
        .get("weekly_4w")
    )
    assert isinstance(weekly, list) and len(weekly) == 4, weekly
    for bucket in weekly:
        assert set(bucket.keys()) == {"week_start", "first", "permanent"}
        assert isinstance(bucket["first"], int)
        assert isinstance(bucket["permanent"], int)
    # ISO date strings, monotonically increasing (oldest → newest).
    dates = [b["week_start"] for b in weekly]
    assert dates == sorted(dates), f"weekly_4w must be oldest-first: {dates}"
