"""Iter 106 — Safety-screen gap closure.

Adds structured items covering: strangulation pattern, firearms access,
sexual coercion (non-force), digital surveillance, financial abuse,
substance use during incidents, distinct homicide/suicide threats, and
protective-order status.

Locks the contract:
    * `/api/safety-assessment/questions` now returns 28 Section 1 items.
    * Each new item carries a `gap_domain` tag so a court report / audit
      can enumerate which specific gap it addresses.
    * A `yes` on any of the high-concern gap items pushes the assessment
      to a level ≤ 2 (never soft-pedals a real safety indicator).
    * The two protective-order items are informational (`high_concern=False`)
      — they DO NOT by themselves shift the level, so declining to
      pursue an order isn't punished by the score.
"""
import pytest
pytest.skip("In-app safety screen turned off (2026-10); screening now happens on SACOparentsAlign.", allow_module_level=True)

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


REQUIRED_GAP_DOMAINS = {
    "strangulation",
    "firearms",
    "sexual_coercion",
    "digital_surveillance",
    "financial_abuse",
    "substance_during_incidents",
    "homicide_threat",
    "suicide_threat",
    "protective_order_current",
    "protective_order_advised",
}


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_questions_endpoint_exposes_all_gap_items():
    r = requests.get(f"{API}/safety-assessment/questions", timeout=10)
    assert r.status_code == 200
    data = r.json()
    s1 = data.get("section_1") or []
    # Total Section 1 items after the gap closure.
    ids = {q["id"] for q in s1}
    assert "s1_q19" in ids and "s1_q28" in ids
    assert len(s1) >= 28
    # Every required gap domain must be represented.
    present = {q.get("gap_domain") for q in s1 if q.get("gap_domain")}
    missing = REQUIRED_GAP_DOMAINS - present
    assert not missing, f"gap domains missing from Section 1: {missing}"


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_gap_high_concern_items_escalate_level():
    """A `yes` on any structured gap-closure high-concern item must
    escalate the level so the safety indicator isn't soft-pedalled."""
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    high_concern_gap_qs = [
        "s1_q19",  # strangulation
        "s1_q20",  # firearms
        "s1_q21",  # sexual coercion
        "s1_q22",  # digital surveillance
        "s1_q23",  # financial abuse
        "s1_q24",  # substance during incidents
        "s1_q25",  # homicide threat
        "s1_q26",  # suicide threat
    ]
    for qid in high_concern_gap_qs:
        s1 = {f"s1_q{i}": "no" for i in range(1, 29)}
        s1[qid] = "yes"
        s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
        s2["s2_q8"] = "no"
        r = requests.post(
            f"{API}/safety-assessment",
            json={"section_1": s1, "section_2": s2},
            headers=headers, timeout=20,
        )
        assert r.status_code == 200, r.text
        lvl = r.json()["result"]["level"]
        assert lvl <= 2, f"{qid} should escalate to level ≤ 2, got level {lvl}"


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_protective_order_items_are_informational_only():
    """Answering `yes` to the two protective-order items alone must NOT
    push the level — those items are informational, not deterministic."""
    tok = _login(*PARENT)
    if not tok:
        pytest.skip("parent1 login unavailable")
    headers = {"Authorization": f"Bearer {tok}"}
    s1 = {f"s1_q{i}": "no" for i in range(1, 29)}
    s1["s1_q27"] = "yes"  # currently has a protective order
    s1["s1_q28"] = "yes"  # was advised to seek one
    s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    s2["s2_q8"] = "no"
    r = requests.post(
        f"{API}/safety-assessment",
        json={"section_1": s1, "section_2": s2},
        headers=headers, timeout=20,
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["level"] == 4


import pytest as _pytest  # noqa: E402
pytestmark = _pytest.mark.skip(reason="In-app safety assessment routes are removed (404). Stored answers kept, hidden.")
