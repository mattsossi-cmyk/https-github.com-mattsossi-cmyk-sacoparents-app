"""Iter 103 — "Regenerate AI summaries" button endpoint.

Locks the behaviour of `POST /api/safety-assessment/{assessment_id}/regenerate-summaries`:
    * Unauthenticated → 401.
    * Owner can regenerate their own assessment; the cache is cleared
      and re-populated with fresh Claude Sonnet 4.5 output.
    * A second regenerate within the cooldown window → 429.
    * Admin bypasses the cooldown AND can force-regenerate another
      parent's assessment.
    * 404 when the assessment_id doesn't exist.

Tests hit the live backend via HTTP (same pattern as iter99). Skipped
gracefully when the backend URL / credentials aren't reachable so this
file doesn't red-line unrelated CI runs.
"""
from __future__ import annotations

import os
import sys
import time
import uuid

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


def _submit_stub_assessment(headers: dict) -> str | None:
    """Submit a small Safety Assessment so we have a real assessment_id
    to exercise the regenerate endpoint against. Returns the id or
    None if the submit surface is unavailable in this environment."""
    payload = {
        "name": "Regen Test",
        "section_1": {f"s1_q{i}": ("Yes" if i == 2 else "No") for i in range(1, 11)},
        "section_2": {f"s2_q{i}": "Yes" for i in range(1, 11)},
    }
    r = requests.post(
        f"{API}/safety-assessment", json=payload, headers=headers, timeout=20,
    )
    if r.status_code != 200:
        return None
    return (r.json() or {}).get("assessment_id")


# ---------- Auth gating ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_regenerate_requires_auth():
    r = requests.post(
        f"{API}/safety-assessment/does-not-matter/regenerate-summaries",
        timeout=10,
    )
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_regenerate_404_when_assessment_missing():
    tok = _login(PARENT_EMAIL, PARENT_PASSWORD)
    if not tok:
        pytest.skip("parent1 login unavailable")
    r = requests.post(
        f"{API}/safety-assessment/{uuid.uuid4().hex}/regenerate-summaries",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404


# ---------- Happy path + cooldown ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_owner_can_regenerate_then_hits_cooldown():
    """Set the cooldown to a very short value via env for this test so
    we can observe both the first (200) and cooldown (429) response
    without waiting 10 minutes."""
    # We can't mutate the running backend's env from here, so instead
    # we verify the happy path (200) and then verify the 429 path by
    # calling immediately after — if the cooldown is at its default
    # of 600s, a second call within a few seconds must be blocked.
    tok = _login(PARENT_EMAIL, PARENT_PASSWORD)
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    assessment_id = _submit_stub_assessment(headers)
    if not assessment_id:
        pytest.skip("safety-assessment submit unavailable")

    r1 = requests.post(
        f"{API}/safety-assessment/{assessment_id}/regenerate-summaries",
        headers=headers, timeout=60,
    )
    # 200 on happy path, or 503 if the LLM key isn't configured in this
    # environment — both are acceptable outcomes; the endpoint itself
    # is behaving.
    assert r1.status_code in (200, 503), r1.text
    if r1.status_code == 200:
        body = r1.json()
        assert body["assessment_id"] == assessment_id
        assert set(body.get("ai_summaries", {}).keys()) >= {
            "overall", "pathway", "section_1", "section_2",
        }
        assert body.get("ai_summaries_generated_at")

        # Immediate second call — must hit the cooldown.
        time.sleep(0.5)
        r2 = requests.post(
            f"{API}/safety-assessment/{assessment_id}/regenerate-summaries",
            headers=headers, timeout=10,
        )
        assert r2.status_code == 429, r2.text
        assert "wait" in (r2.json().get("detail") or "").lower()


# ---------- Admin bypass ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_admin_bypasses_cooldown_on_other_parents_assessment():
    parent_tok = _login(PARENT_EMAIL, PARENT_PASSWORD)
    admin_tok = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not parent_tok or not admin_tok:
        pytest.skip("credentials unavailable")

    parent_headers = {"Authorization": f"Bearer {parent_tok}"}
    admin_headers = {"Authorization": f"Bearer {admin_tok}"}

    assessment_id = _submit_stub_assessment(parent_headers)
    if not assessment_id:
        pytest.skip("safety-assessment submit unavailable")

    # Warm the cache as the owner (this also sets the cooldown clock).
    warm = requests.post(
        f"{API}/safety-assessment/{assessment_id}/regenerate-summaries",
        headers=parent_headers, timeout=60,
    )
    assert warm.status_code in (200, 503), warm.text
    # If LLM is unavailable in this env we can't assert admin bypass
    # cleanly (the 503 comes back regardless of who called).
    if warm.status_code != 200:
        pytest.skip("LLM unavailable in this environment")

    # Admin call immediately after — cooldown bypass expected.
    admin_call = requests.post(
        f"{API}/safety-assessment/{assessment_id}/regenerate-summaries",
        headers=admin_headers, timeout=60,
    )
    assert admin_call.status_code == 200, admin_call.text
    body = admin_call.json()
    # forced_by_admin=True when the admin's own user_id != the assessment owner's.
    assert body.get("forced_by_admin") is True
