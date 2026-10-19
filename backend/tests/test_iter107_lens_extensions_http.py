"""Iter 107 — Phase 3/4/5 lens extensions HTTP integration.

Locks the extended lens contract through the wire:
    * `POST /api/safety-assessment` accepts optional
      `pattern_context`, `trauma_impact`, `child_experience` sections.
    * When enough answers are provided (>=3 per section), the returned
      `result.lens` block is enriched:
        - Finding 1 gets `pattern_typology` (coercive_controlling /
          violent_resistance / situational / separation_instigated /
          unclear).
        - Finding 2 gets `domain_signals` with per-domain intensity.
        - A NEW Finding 4 appears (`child_experience`) with concern
          domains and a protective-relationship resilience flag.
    * `GET /questions` exposes all three extension banks.
    * Submitting all three sections empty is still valid — the
      extensions are optional.
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


def _login(email: str, pw: str) -> str | None:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=10)
    if r.status_code != 200:
        return None
    return r.json().get("access_token") or r.json().get("token")


def _base_payload() -> dict:
    return {
        "section_1": {f"s1_q{i}": "no" for i in range(1, 29)},
        "section_2": {**{f"s2_q{i}": "yes" for i in range(1, 9)}, "s2_q8": "no"},
    }


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_questions_exposes_three_extension_banks():
    r = requests.get(f"{API}/safety-assessment/questions", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("pattern_context"), list) and len(data["pattern_context"]) >= 6
    assert isinstance(data.get("trauma_impact"), list) and len(data["trauma_impact"]) >= 8
    assert isinstance(data.get("child_experience"), list) and len(data["child_experience"]) >= 8


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_extensions_empty_is_still_valid():
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base_payload()  # no extensions
    r = requests.post(
        f"{API}/safety-assessment", json=payload,
        headers={"Authorization": f"Bearer {tok}"}, timeout=20,
    )
    assert r.status_code == 200
    lens = r.json()["result"]["lens"]
    # Extensions absent -> pattern_typology / domain_signals / Finding 4 all absent.
    assert "pattern_typology" not in lens["findings"]["family_violence_pattern"]
    assert "domain_signals" not in lens["findings"]["trauma_impact"]
    assert "child_experience" not in lens["findings"]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pattern_context_produces_coercive_controlling_typology():
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base_payload()
    # Answer the three coercive-control markers "yes".
    payload["pattern_context"] = {
        "p_q1": "yes",  # monitors movements / finances
        "p_q2": "yes",  # you change what you say for fear
        "p_q3": "yes",  # ongoing pattern of control
        "p_q4": "no",
        "p_q5": "no",
        "p_q6": "no",
        "p_q7": "no",
        "p_q8": "yes",  # pre-separation history
    }
    r = requests.post(
        f"{API}/safety-assessment", json=payload,
        headers={"Authorization": f"Bearer {tok}"}, timeout=20,
    )
    assert r.status_code == 200
    lens = r.json()["result"]["lens"]
    typology = lens["findings"]["family_violence_pattern"]["pattern_typology"]
    assert typology["type"] == "coercive_controlling"
    assert "coercive" in typology["label"].lower()


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pattern_context_recognises_violent_resistance():
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base_payload()
    payload["pattern_context"] = {
        "p_q1": "no", "p_q2": "no", "p_q3": "no",
        "p_q4": "yes",  # defensive/self-protective force
        "p_q5": "yes",  # ongoing pattern of THEIR control (context)
        "p_q6": "no", "p_q7": "no", "p_q8": "no",
    }
    r = requests.post(
        f"{API}/safety-assessment", json=payload,
        headers={"Authorization": f"Bearer {tok}"}, timeout=20,
    )
    lens = r.json()["result"]["lens"]
    typology = lens["findings"]["family_violence_pattern"]["pattern_typology"]
    assert typology["type"] == "violent_resistance"


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_trauma_impact_produces_domain_signals():
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base_payload()
    # High signal in hypervigilance + sleep + fear_communication.
    payload["trauma_impact"] = {
        "ti_q1": "yes", "ti_q2": "yes",   # hypervigilance high
        "ti_q3": "no", "ti_q4": "no",
        "ti_q5": "no", "ti_q6": "no",
        "ti_q7": "yes", "ti_q8": "yes",   # sleep high
        "ti_q9": "yes", "ti_q10": "yes",  # fear_communication high
    }
    r = requests.post(
        f"{API}/safety-assessment", json=payload,
        headers={"Authorization": f"Bearer {tok}"}, timeout=20,
    )
    lens = r.json()["result"]["lens"]
    ds = lens["findings"]["trauma_impact"]["domain_signals"]
    assert ds["overall_intensity"] == "high"
    assert ds["domains"]["hypervigilance"]["intensity"] == "high"
    assert ds["domains"]["avoidance"]["intensity"] == "low"
    assert set(ds["high_domains"]) >= {"Hypervigilance", "Sleep disruption", "Fear-based communication"}


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_child_experience_produces_finding_4_and_flags_high_concern():
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base_payload()
    payload["child_experience"] = {
        "ce_q1": "yes",   # direct harm — high concern
        "ce_q2": "yes",   # exposure
        "ce_q3": "yes",   # fear
        "ce_q4": "no",
        "ce_q5": "yes",   # loyalty conflict
        "ce_q6": "no",
        "ce_q7": "yes",   # protective relationship — resilience
        "ce_q8": "no",
        "ce_q9": "no",
        "ce_q10": "no",
    }
    r = requests.post(
        f"{API}/safety-assessment", json=payload,
        headers={"Authorization": f"Bearer {tok}"}, timeout=20,
    )
    lens = r.json()["result"]["lens"]
    finding4 = lens["findings"].get("child_experience")
    assert finding4, "Finding 4 should be produced when child_experience is answered"
    assert finding4["overall"] == "high"
    assert finding4["high_concern"] is True
    assert finding4["protective_relationship_present"] is True
    assert "Direct victimisation" in finding4["concern_domains"]


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_no_child_experience_no_finding_4():
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    payload = _base_payload()
    payload["child_experience"] = {"ce_q1": "no", "ce_q2": "no"}  # <3 answers -> not enough signal
    r = requests.post(
        f"{API}/safety-assessment", json=payload,
        headers={"Authorization": f"Bearer {tok}"}, timeout=20,
    )
    lens = r.json()["result"]["lens"]
    assert "child_experience" not in lens["findings"]


import pytest as _pytest  # noqa: E402
pytestmark = _pytest.mark.skip(reason="In-app safety assessment routes are removed (404). Stored answers kept, hidden.")
