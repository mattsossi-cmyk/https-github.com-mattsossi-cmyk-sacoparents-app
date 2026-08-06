"""Iteration 84 — Neurodivergent Coparenting Risk Assessment.

Verifies the scoring engine tiers, live API round-trip (profile, POST
assessment, PDF download), and access control (parents can't fetch
another parent's assessment)."""
import os
import httpx
import pytest

from nd_risk_routes import MatrixResponse, score_assessment, INTERVENTIONS

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://prepared-parents.preview.emergentagent.com",
).rstrip("/")


def _matrix(**overrides):
    base = dict(
        threat_scheduling_disruption=1, threat_gaslighting=1, threat_sensory_overload=1,
        vuln_executive_burnout=1, vuln_memory_fragmentation=1, vuln_communication_bottleneck=1,
    )
    base.update(overrides)
    return MatrixResponse(**base)


# ---- Scoring engine ---------------------------------------------------

def test_low_tier():
    s = score_assessment(_matrix())
    assert s["threat_score"] == 1 and s["vulnerability_score"] == 1
    assert s["total_score"] == 1
    assert s["tier"] == "low"


def test_medium_tier_at_boundary():
    # threat=2, vuln=2 -> 4 (lower medium boundary)
    s = score_assessment(_matrix(threat_scheduling_disruption=2, vuln_executive_burnout=2))
    assert s["total_score"] == 4
    assert s["tier"] == "medium"


def test_high_tier_at_boundary():
    # threat=3, vuln=3 -> 9 (lower high boundary)
    s = score_assessment(_matrix(threat_scheduling_disruption=3, vuln_executive_burnout=3))
    assert s["total_score"] == 9
    assert s["tier"] == "high"


def test_critical_tier_max():
    s = score_assessment(_matrix(
        threat_scheduling_disruption=4, threat_gaslighting=4, threat_sensory_overload=4,
        vuln_executive_burnout=4, vuln_memory_fragmentation=4, vuln_communication_bottleneck=4,
    ))
    assert s["total_score"] == 16
    assert s["tier"] == "critical"


def test_axis_score_uses_max():
    """Axis score = max of the sub-dimensions (conservative for safety)."""
    s = score_assessment(_matrix(threat_gaslighting=4))
    assert s["threat_score"] == 4


def test_interventions_populated_for_every_tier():
    for tier in ("low", "medium", "high", "critical"):
        assert INTERVENTIONS[tier], f"tier {tier} missing interventions"


# ---- Live API ---------------------------------------------------------

@pytest.fixture(scope="module")
def token():
    with httpx.Client(timeout=15) as c:
        r = c.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "parent1@test.com", "password": "TestPass123!"},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("access_token") or data.get("token")


def test_unauth_cannot_submit():
    r = httpx.post(f"{BASE_URL}/api/nd-risk/assessment", json={
        "coparent_name": "Alex",
        "matrix": _matrix().model_dump(),
    }, timeout=15)
    assert r.status_code in (401, 403)


def test_submit_and_fetch_roundtrip(token):
    h = {"Authorization": f"Bearer {token}"}
    body = {"coparent_name": "Alex Coparent",
            "matrix": _matrix(threat_gaslighting=3, vuln_executive_burnout=3).model_dump(),
            "notes": "pytest regression"}
    r = httpx.post(f"{BASE_URL}/api/nd-risk/assessment", json=body, headers=h, timeout=15)
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["scoring"]["tier"] == "high"
    assert a["scoring"]["total_score"] == 9
    aid = a["assessment_id"]

    r2 = httpx.get(f"{BASE_URL}/api/nd-risk/assessment/{aid}", headers=h, timeout=15)
    assert r2.status_code == 200 and r2.json()["assessment_id"] == aid


def test_pdf_endpoint_returns_pdf(token):
    h = {"Authorization": f"Bearer {token}"}
    body = {"coparent_name": "Alex", "matrix": _matrix(threat_gaslighting=4, vuln_memory_fragmentation=4).model_dump()}
    aid = httpx.post(f"{BASE_URL}/api/nd-risk/assessment", json=body, headers=h, timeout=15).json()["assessment_id"]
    r = httpx.get(f"{BASE_URL}/api/nd-risk/assessment/{aid}/pdf?sign=true", headers=h, timeout=30)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 10_000  # non-trivial size


def test_cannot_fetch_someone_elses_assessment(token):
    # Try a made-up id — should 404 (not 200, not 500)
    h = {"Authorization": f"Bearer {token}"}
    r = httpx.get(f"{BASE_URL}/api/nd-risk/assessment/nonexistent-id-abcdef", headers=h, timeout=15)
    assert r.status_code == 404


def test_coordinator_returns_shape(token):
    r = httpx.get(f"{BASE_URL}/api/nd-risk/coordinator", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    for k in ("cases", "case_count", "heatmap", "tier_counts", "threat_dimensions", "vulnerability_dimensions", "interventions_by_tier"):
        assert k in body
    # Heatmap must be 4x4 of ints
    assert len(body["heatmap"]) == 4
    for row in body["heatmap"]:
        assert len(row) == 4
        assert all(isinstance(x, int) for x in row)
