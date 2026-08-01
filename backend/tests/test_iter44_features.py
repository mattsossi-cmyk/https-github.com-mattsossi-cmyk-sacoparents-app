"""Iteration 44 backend regression tests.

Covers GET /api/deep-dives/compare-status.
- Empty state returns zero counts for all three pathways.
- Creating a share bumps that pathway's `active` count.
- Revoking all shares resets counts to zero.
- Existing GET /api/deep-dives/status still works (regression).
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

PARENT1 = {"email": "parent1@test.com", "password": "TestPass123!", "name": "Sam Parent"}
PARENT2 = {"email": "parent2@test.com", "password": "TestPass123!", "name": "Riley Parent"}

PATHWAY_PREFIXES = [
    ("educational", "edu-deep", "edu_deep_share_"),
    ("psychological", "psych-deep", "psych_deep_share_"),
    ("medical", "med-deep", "med_deep_share_"),
]


def _ensure_account(creds):
    requests.post(f"{BASE_URL}/api/auth/register", json={
        **creds, "children": [], "custody_situation": "50/50 shared",
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": creds["email"], "password": creds["password"],
    }, timeout=30)
    assert r.status_code == 200, f"login {creds['email']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture(scope="module")
def p2_token():
    return _ensure_account(PARENT2)


def _client(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {token}"})
    return s


def _post_safety_level_4(client):
    payload = {"section_1": {}, "section_2": {"s2_q%d" % i: "yes" for i in range(1, 12)}}
    payload["section_2"]["s2_q8"] = "no"
    r = client.post(f"{BASE_URL}/api/safety-assessment", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _revoke_all(client):
    """Revoke all non-revoked shares in all 3 pathways for the client's user."""
    for _pid, prefix, _sp in PATHWAY_PREFIXES:
        r = client.get(f"{BASE_URL}/api/{prefix}/compare/me")
        if r.status_code != 200:
            continue
        for share in r.json().get("shares", []):
            if share.get("status") != "revoked":
                client.post(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/revoke")


@pytest.fixture(scope="module", autouse=True)
def cleanup_all_shares(p1_token, p2_token):
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    yield
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


@pytest.fixture
def p2_client(p2_token):
    return _client(p2_token)


# ============================================================
# 1) Compare-status endpoint
# ============================================================
class TestCompareStatus:
    def test_empty_state_all_zero(self, p1_client):
        _revoke_all(p1_client)
        r = p1_client.get(f"{BASE_URL}/api/deep-dives/compare-status")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_active"] == 0
        assert data["total_ready_to_view"] == 0
        assert isinstance(data.get("pathways"), list)
        assert len(data["pathways"]) == 3
        ids = {p["id"] for p in data["pathways"]}
        assert ids == {"educational", "psychological", "medical"}
        for p in data["pathways"]:
            assert p["active"] == 0
            assert p["ready_to_view"] == 0
            assert "compare_route" in p
            assert p["compare_route"].endswith("/compare")

    def test_pathway_compare_routes_correct(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/deep-dives/compare-status")
        assert r.status_code == 200
        routes = {p["id"]: p["compare_route"] for p in r.json()["pathways"]}
        assert routes["educational"] == "/special-needs-v2/educational-deep-dive/compare"
        assert routes["psychological"] == "/special-needs-v2/psychological-deep-dive/compare"
        assert routes["medical"] == "/special-needs-v2/medical-deep-dive/compare"

    def test_active_increments_per_pathway(self, p1_client, p2_client):
        _revoke_all(p1_client)
        _post_safety_level_4(p1_client)

        # Create a share in each pathway.
        for _pid, prefix, share_prefix in PATHWAY_PREFIXES:
            r = p1_client.post(
                f"{BASE_URL}/api/{prefix}/compare/link",
                json={"email": PARENT2["email"]},
            )
            assert r.status_code == 200, f"{prefix}: {r.text}"
            assert r.json()["share"]["share_id"].startswith(share_prefix)

        r = p1_client.get(f"{BASE_URL}/api/deep-dives/compare-status")
        assert r.status_code == 200
        data = r.json()
        assert data["total_active"] == 3, data
        per = {p["id"]: p for p in data["pathways"]}
        for pid, _pref, _sp in PATHWAY_PREFIXES:
            assert per[pid]["active"] == 1, f"{pid}: {per[pid]}"

        # Parent2 also sees the shares from their side (partner_user_id).
        r2 = p2_client.get(f"{BASE_URL}/api/deep-dives/compare-status")
        assert r2.status_code == 200
        assert r2.json()["total_active"] == 3

        # ready_to_view is 0 because partner hasn't consented yet.
        assert data["total_ready_to_view"] == 0

    def test_revoke_all_returns_to_zero(self, p1_client):
        # Preconditions from previous test: shares exist. Revoke them.
        _revoke_all(p1_client)
        r = p1_client.get(f"{BASE_URL}/api/deep-dives/compare-status")
        assert r.status_code == 200
        data = r.json()
        assert data["total_active"] == 0
        assert data["total_ready_to_view"] == 0
        for p in data["pathways"]:
            assert p["active"] == 0

    def test_requires_auth(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/deep-dives/compare-status")
        assert r.status_code in (401, 403), r.status_code


# ============================================================
# 2) Regression — /api/deep-dives/status still works
# ============================================================
class TestDeepDivesStatusRegression:
    def test_status_shape(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/deep-dives/status")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "deep_dives" in data
        assert data["total"] == 3
        assert len(data["deep_dives"]) == 3
        ids = {d["id"] for d in data["deep_dives"]}
        assert ids == {"educational", "psychological", "medical"}
        for d in data["deep_dives"]:
            assert "route" in d and "report_route" in d
            assert "has_assessment" in d and "completed" in d
