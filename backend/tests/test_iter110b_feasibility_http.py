"""Iter 110b — Coparenting Feasibility Spectrum HTTP integration.

Verifies the tier surfaces through the submit endpoint on
Finding 3 (`result.lens.findings.parenting_plan_implications.feasibility_tier`).
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

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

PARENT = ("parent1@test.com", "TestPass123!")  # noqa: S105  test fixture


def _login() -> str | None:
    r = requests.post(f"{API}/auth/login", json={"email": PARENT[0], "password": PARENT[1]}, timeout=10)
    return (r.json().get("access_token") or r.json().get("token")) if r.status_code == 200 else None


def _base() -> dict:
    return {
        "section_1": {f"s1_q{i}": "no" for i in range(1, 29)},
        "section_2": {**{f"s2_q{i}": "yes" for i in range(1, 9)}, "s2_q8": "no"},
    }


def _tier(body: dict) -> dict:
    return body["result"]["lens"]["findings"]["parenting_plan_implications"]["feasibility_tier"]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_cooperative_tier_when_everything_clean():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base()
    r = requests.post(f"{API}/safety-assessment", json=payload,
                      headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    assert r.status_code == 200
    t = _tier(r.json())
    assert t["tier"] == "cooperative_coparenting"


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_homicide_threat_escalates_to_suspended():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base()
    payload["section_1"]["s1_q25"] = "yes"  # distinct homicide threat
    r = requests.post(f"{API}/safety-assessment", json=payload,
                      headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    t = _tier(r.json())
    assert t["tier"] == "suspended_contact"
    assert t["review_point_days"] == 30


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_child_direct_harm_escalates_to_suspended():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base()
    payload["child_experience"] = {
        "ce_q1": "yes",  # child directly harmed
        "ce_q2": "no", "ce_q3": "no",
    }
    r = requests.post(f"{API}/safety-assessment", json=payload,
                      headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    t = _tier(r.json())
    assert t["tier"] == "suspended_contact"
    assert "ce_q1" in t["triggers"]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_coercive_typology_floors_at_parallel():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base()
    payload["pattern_context"] = {
        "p_q1": "yes", "p_q2": "yes", "p_q3": "yes", "p_q4": "no",
        "p_q5": "no", "p_q6": "no", "p_q7": "no", "p_q8": "yes",
    }
    r = requests.post(f"{API}/safety-assessment", json=payload,
                      headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    t = _tier(r.json())
    # Base level is 4 (clean) but coercive_controlling floor forces parallel.
    assert t["tier"] == "parallel_parenting"
    assert t["typology_floor"] == "parallel_parenting"


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_violent_resistance_typology_defaults_to_parallel():
    tok = _login()
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base()
    payload["pattern_context"] = {
        "p_q1": "no", "p_q2": "no", "p_q3": "no",
        "p_q4": "yes",  # defensive/self-protective
        "p_q5": "yes",  # ongoing OTHER-parent control
        "p_q6": "no", "p_q7": "no", "p_q8": "no",
    }
    r = requests.post(f"{API}/safety-assessment", json=payload,
                      headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    t = _tier(r.json())
    assert t["tier"] == "parallel_parenting"
    joined = " ".join(t.get("caveats") or []).lower()
    assert "violent-resistance" in joined or "self-protective" in joined
