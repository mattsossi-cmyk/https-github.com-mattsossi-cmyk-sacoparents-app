"""Iter 86 — Intervention Compliance Log.

Covers:
    * Week-Monday computation (UTC)
    * Aggregation across Safety + ND Risk + Companion
    * Idempotent upsert of a single log entry
    * Weekly compliance history endpoint
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

from datetime import datetime, timezone  # noqa: E402

from intervention_compliance_routes import _key, _week_start  # noqa: E402


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


TEST_EMAIL = "parent1@test.com"
TEST_PASSWORD = "TestPass123!"


# ---- Pure unit tests ----

def test_week_start_returns_monday():
    # Wed 2026-08-05 UTC → Monday 2026-08-03
    wed = datetime(2026, 8, 5, 15, 30, tzinfo=timezone.utc)
    assert _week_start(wed) == "2026-08-03"
    # Monday itself → same day
    mon = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
    assert _week_start(mon) == "2026-08-03"
    # Sunday → previous Monday
    sun = datetime(2026, 8, 9, 23, 59, tzinfo=timezone.utc)
    assert _week_start(sun) == "2026-08-03"


def test_intervention_key_is_stable_and_source_scoped():
    """Same source + same text → same key. Different source → different key."""
    a = _key("safety", "Use written-only communication.")
    b = _key("safety", "Use written-only communication.")
    c = _key("nd_risk", "Use written-only communication.")
    d = _key("safety", "Use written only communication.")  # different wording
    assert a == b
    assert a != c
    assert a != d
    assert len(a) == 16


# ---- HTTP round trip ----

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_log_lifecycle_live():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(f"parent1 login not available: {r.status_code}")
    tok = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}

    log = requests.get(f"{API}/interventions/log", headers=headers, timeout=10).json()
    assert "week_start" in log
    assert "summary" in log and "compliance_pct" in log["summary"]
    total = log["summary"]["total"]

    if total == 0:
        pytest.skip("parent1 has no interventions catalog yet")

    first = log["items"][0]

    # Tick it
    resp = requests.post(
        f"{API}/interventions/log",
        headers=headers,
        json={
            "intervention_key": first["key"],
            "source":           first["source"],
            "text":             first["text"],
            "group":            first["group"],
            "followed":         True,
            "notes":            "Auto-test tick.",
        },
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    # Re-GET should reflect it
    log2 = requests.get(f"{API}/interventions/log", headers=headers, timeout=10).json()
    matched = next((it for it in log2["items"] if it["key"] == first["key"]), None)
    assert matched is not None
    assert matched["followed"] is True
    assert matched["notes"] == "Auto-test tick."

    # Untick — same key, followed=false
    requests.post(
        f"{API}/interventions/log",
        headers=headers,
        json={
            "intervention_key": first["key"],
            "source":           first["source"],
            "text":             first["text"],
            "followed":         False,
        },
        timeout=10,
    )
    log3 = requests.get(f"{API}/interventions/log", headers=headers, timeout=10).json()
    matched = next(it for it in log3["items"] if it["key"] == first["key"])
    assert matched["followed"] is False


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_history_endpoint_shape():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip("login unavailable")
    tok = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}

    hist = requests.get(
        f"{API}/interventions/log/history?weeks=4",
        headers=headers,
        timeout=10,
    ).json()
    assert "weeks" in hist
    assert len(hist["weeks"]) == 4
    for w in hist["weeks"]:
        assert set(w.keys()) >= {"week_start", "total", "followed", "compliance_pct"}
