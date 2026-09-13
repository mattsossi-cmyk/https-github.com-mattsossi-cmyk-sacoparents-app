"""iter189e — Nudge copy revision history.

Locks the behaviour of the new `nudge_copy_history` collection:
  * Every successful admin save appends exactly ONE row.
  * `GET /api/admin/nudge-copy/child-needs-share/history` returns
    the last N rows newest-first.
  * `updated_by` (an admin email) is surfaced under admin gate only.
  * `limit` is bounded to 1-20.
  * Reset does NOT delete history rows — the admin can still
    restore a prior version after nuking the override.
"""
from __future__ import annotations

import os
import sys
import time
import uuid

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
            f"Login as {email} failed ({r.status_code}); env may not have "
            f"the seeded account. {r.text[:200]}"
        )
    return r.json()["access_token"]


def _admin_hdrs() -> dict:
    return {"Authorization": f"Bearer {_bearer(ADMIN_EMAIL, ADMIN_PASSWORD)}"}


def _parent_hdrs() -> dict:
    return {"Authorization": f"Bearer {_bearer('parent1@test.com', 'TestPass123!')}"}


def _unique_headline(prefix: str = "hist test") -> str:
    return f"{prefix} · {uuid.uuid4().hex[:8]}"


# ---------------------- Endpoint auth + shape ---------------------- #

def test_history_requires_admin():
    r = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        timeout=10,
    )
    assert r.status_code in (401, 403), r.text
    r = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=_parent_hdrs(),
        timeout=10,
    )
    assert r.status_code == 403, r.text


def test_history_limit_bounded_1_to_20():
    # 0 → 422 (below min)
    r = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=_admin_hdrs(),
        params={"limit": 0},
        timeout=10,
    )
    assert r.status_code == 422, r.text
    # 21 → 422 (above max)
    r = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=_admin_hdrs(),
        params={"limit": 21},
        timeout=10,
    )
    assert r.status_code == 422, r.text


# ---------------------- Save → history append ---------------------- #

def test_save_appends_history_row_and_history_is_newest_first():
    hdrs = _admin_hdrs()
    # Baseline count so we don't collide with other test runs.
    r0 = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=hdrs,
        params={"limit": 20},
        timeout=10,
    )
    assert r0.status_code == 200, r0.text
    before = len(r0.json().get("entries") or [])

    # Save two versions in quick succession.
    a_headline = _unique_headline("version A")
    b_headline = _unique_headline("version B")
    subhead = (
        "iter189e regression payload — verifies history append + newest-first "
        "ordering. Aggregate telemetry only, no verbatim answers."
    )
    for headline in (a_headline, b_headline):
        r = requests.post(
            f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
            headers=hdrs,
            json={"headline": headline, "subhead": subhead,
                  "note": "iter189e history test"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        time.sleep(0.05)  # ensure distinct `updated_at` timestamps

    r1 = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=hdrs,
        params={"limit": 20},
        timeout=10,
    )
    assert r1.status_code == 200, r1.text
    entries = r1.json().get("entries") or []
    assert len(entries) == before + 2, (
        f"Expected {before + 2} entries after 2 saves; got {len(entries)}"
    )
    # Newest-first: the two we just saved must be entries[0] and entries[1],
    # with B (most recent) before A.
    assert entries[0]["headline"] == b_headline, entries[0]
    assert entries[1]["headline"] == a_headline, entries[1]
    # `updated_by` reflects the admin email.
    assert entries[0]["updated_by"] == ADMIN_EMAIL
    # `updated_at` is a valid ISO-ish string.
    assert isinstance(entries[0]["updated_at"], str) and entries[0]["updated_at"]
    # Note field round-trips.
    assert entries[0]["note"] == "iter189e history test"


def test_history_limit_defaults_to_five():
    hdrs = _admin_hdrs()
    # Seed 6 rapid saves so we know there are enough entries to test capping.
    subhead = (
        "limit-cap regression payload — 6 rapid saves to prove the default "
        "cap. Aggregate telemetry only, no verbatim answers."
    )
    for _ in range(6):
        r = requests.post(
            f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
            headers=hdrs,
            json={"headline": _unique_headline("cap test"), "subhead": subhead},
            timeout=10,
        )
        assert r.status_code == 200, r.text
    r = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=hdrs,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    entries = r.json().get("entries") or []
    assert len(entries) == 5, f"default limit should cap at 5; got {len(entries)}"


def test_reset_does_not_wipe_history():
    """A reset clears the live override but NOT the revision log —
    an admin who resets and regrets it can still restore a version."""
    hdrs = _admin_hdrs()
    # Save one, capture its headline.
    headline = _unique_headline("pre-reset")
    subhead = (
        "reset-preservation payload — proves reset preserves history. "
        "Aggregate telemetry only, no verbatim answers."
    )
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share",
        headers=hdrs,
        json={"headline": headline, "subhead": subhead},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    # Reset the override.
    r = requests.post(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/reset",
        headers=hdrs,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    # History must STILL carry the saved headline.
    r = requests.get(
        f"{BASE_URL}/api/admin/nudge-copy/child-needs-share/history",
        headers=hdrs,
        params={"limit": 20},
        timeout=10,
    )
    entries = r.json().get("entries") or []
    assert any(e["headline"] == headline for e in entries), (
        f"Reset wiped a history row it shouldn't have. Looking for "
        f"{headline!r} in {[e['headline'] for e in entries]}"
    )
