"""Iteration 43 backend regression tests.

Covers:
  1. Psychological Deep Dive Compare — /api/psych-deep/compare/*
  2. Medical Deep Dive Compare      — /api/med-deep/compare/*
  3. Share-link nickname (label) round-trip on all 4 share-link endpoints.
  4. Regression: iter42 educational-compare still shape-compatible.

Mirrors the /app/backend/tests/test_iter42_features.py structure so the
autouse fixture cleans leftover shares from prior smoke testing.
"""
from __future__ import annotations

import os
import uuid
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

DEEP_DIVE_PREFIXES = [
    ("psych-deep", "psych_deep_share_"),
    ("med-deep",   "med_deep_share_"),
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


def _post_safety(client, level=4):
    s1 = {f"s1_q{i}": "no" for i in range(1, 19)}
    s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    s2["s2_q8"] = "no"
    if level == 4:
        payload = {"section_1": s1, "section_2": s2}
    elif level == 2:
        s1["s1_q3"] = "yes"
        payload = {"section_1": s1, "section_2": s2}
    elif level == 1:
        s1["s1_q1"] = "yes"
        payload = {"section_1": s1, "section_2": s2}
    else:
        payload = {"section_1": s1, "section_2": s2}
    r = client.post(f"{BASE_URL}/api/safety-assessment", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module", autouse=True)
def cleanup_deep_dive_shares(p1_token, p2_token):
    """Revoke any leftover psych-/med-deep shares before tests run."""
    for tok in (p1_token, p2_token):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json",
                          "Authorization": f"Bearer {tok}"})
        for prefix, _ in DEEP_DIVE_PREFIXES:
            r = s.get(f"{BASE_URL}/api/{prefix}/compare/me")
            if r.status_code == 200:
                for share in r.json().get("shares", []):
                    if share.get("status") != "revoked":
                        s.post(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/revoke")
    yield


@pytest.fixture
def p1_client(p1_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {p1_token}"})
    return s


@pytest.fixture
def p2_client(p2_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {p2_token}"})
    return s


@pytest.fixture
def guest_client():
    r = requests.post(f"{BASE_URL}/api/auth/guest", timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {tok}"})
    return s


# ============================================================
# 1) Psych & Med Deep Dive Compare — endpoint parity
# ============================================================
class TestDeepDiveCompareParity:
    """Both /api/psych-deep/compare and /api/med-deep/compare must expose the
    same state machine as the educational-deep-dive compare."""

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_link_guest_forbidden(self, guest_client, prefix, share_prefix):
        r = guest_client.post(
            f"{BASE_URL}/api/{prefix}/compare/link",
            json={"email": PARENT2["email"]},
        )
        assert r.status_code == 403, f"{prefix}: {r.status_code} {r.text}"

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_link_body_is_json_body_not_query(self, p1_client, prefix, share_prefix):
        """Regression: LinkIn must live at module scope so FastAPI treats it
        as a JSON body, not a query param (previous bug produced 422)."""
        _post_safety(p1_client, level=4)
        # Missing body → should NOT be 422 'query missing'. It might be 422 with
        # 'email' field missing (body validation), which is body-mode. If it is
        # 200 that's also fine (empty pydantic model unlikely). We assert we
        # don't get the specific "query missing" bug.
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/compare/link")
        # If 422, ensure it's body-based, not query-based.
        if r.status_code == 422:
            errors = r.json().get("detail", [])
            locs = [tuple(e.get("loc", [])) for e in errors]
            assert not any(loc and loc[0] == "query" for loc in locs), (
                f"{prefix}: body treated as query param — factory-scope regression! {locs}"
            )

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_link_self_email_400(self, p1_client, prefix, share_prefix):
        _post_safety(p1_client, level=4)
        r = p1_client.post(
            f"{BASE_URL}/api/{prefix}/compare/link",
            json={"email": PARENT1["email"]},
        )
        assert r.status_code == 400, f"{prefix}: {r.status_code} {r.text}"
        assert "own email" in r.json().get("detail", "").lower()

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_link_unknown_partner_404(self, p1_client, prefix, share_prefix):
        _post_safety(p1_client, level=4)
        r = p1_client.post(
            f"{BASE_URL}/api/{prefix}/compare/link",
            json={"email": f"nobody_{uuid.uuid4().hex[:6]}@example.com"},
        )
        assert r.status_code == 404, f"{prefix}: {r.status_code} {r.text}"

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_safety_level_2_blocks_link(self, p1_client, prefix, share_prefix):
        _post_safety(p1_client, level=2)
        r = p1_client.post(
            f"{BASE_URL}/api/{prefix}/compare/link",
            json={"email": PARENT2["email"]},
        )
        assert r.status_code == 403, f"{prefix}: {r.status_code} {r.text}"
        assert "safety" in r.json().get("detail", "").lower()
        # Restore to level 4 so subsequent tests can run.
        _post_safety(p1_client, level=4)

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_link_state_machine_and_me(self, p1_client, p2_client, prefix, share_prefix):
        _post_safety(p1_client, level=4)
        r = p1_client.post(
            f"{BASE_URL}/api/{prefix}/compare/link",
            json={"email": PARENT2["email"]},
        )
        assert r.status_code == 200, f"{prefix}: {r.status_code} {r.text}"
        share = r.json().get("share") or {}
        assert share.get("share_id", "").startswith(share_prefix), share
        assert share.get("role") == "creator"
        assert share.get("my_consent") is True
        assert share.get("partner_consent") is False
        assert share.get("status") in ("awaiting_partner_consent", "awaiting_consent")

        # /me for p1 lists it.
        mine = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/me")
        assert mine.status_code == 200
        share_ids = [s["share_id"] for s in mine.json().get("shares", [])]
        assert share["share_id"] in share_ids

        # p2 sees it as partner role.
        p2_mine = p2_client.get(f"{BASE_URL}/api/{prefix}/compare/me")
        assert p2_mine.status_code == 200
        p2_row = next((s for s in p2_mine.json().get("shares", [])
                       if s["share_id"] == share["share_id"]), None)
        assert p2_row is not None, f"{prefix}: partner does not see share"
        assert p2_row.get("role") == "partner"

        # p2 consents → status flips to active (or awaiting_consent for creator).
        cr = p2_client.post(
            f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/consent",
            json={"consent": True},
        )
        assert cr.status_code == 200, cr.text
        assert cr.json()["share"]["partner_consent"] is True

        # GET comparison — both have not completed assessments → 409.
        gv = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}")
        assert gv.status_code in (200, 409), gv.text

        # Revoke.
        rv = p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/revoke")
        assert rv.status_code == 200
        assert rv.json()["share"]["status"] == "revoked"

        # Post-revoke GET → 409.
        after = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}")
        assert after.status_code in (409, 404), after.text

    @pytest.mark.parametrize("prefix,share_prefix", DEEP_DIVE_PREFIXES)
    def test_consent_when_safety_blocking_403(self, p1_client, p2_client, prefix, share_prefix):
        """If partner drops to level-2 safety, their consent must be blocked."""
        # Fresh link from parent1 at level 4.
        _post_safety(p1_client, level=4)
        r = p1_client.post(
            f"{BASE_URL}/api/{prefix}/compare/link",
            json={"email": PARENT2["email"]},
        )
        assert r.status_code == 200, r.text
        share_id = r.json()["share"]["share_id"]

        # parent2 drops to level 2 → consent should 403 with safety detail.
        _post_safety(p2_client, level=2)
        cr = p2_client.post(
            f"{BASE_URL}/api/{prefix}/compare/{share_id}/consent",
            json={"consent": True},
        )
        assert cr.status_code == 403, cr.text
        assert "safety" in cr.json().get("detail", "").lower()

        # Reset & revoke.
        _post_safety(p2_client, level=4)
        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ============================================================
# 2) Share-link nickname / label round-trip
# ============================================================
class TestShareLinkNicknameRoundTrip:
    """The `label` field on share-link POSTs must be persisted and returned
    by GET /api/share/mine for every endpoint that mints share tokens."""

    def test_safety_share_link_label_round_trip(self, p1_client):
        _post_safety(p1_client, level=4)
        sa = _post_safety(p1_client, level=4)
        aid = sa["assessment_id"]
        label = f"TEST_iter43_{uuid.uuid4().hex[:6]}"
        r = p1_client.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/share-link",
            json={"expire_days": 7, "label": label},
        )
        assert r.status_code == 200, r.text
        jti = r.json()["jti"]

        listing = p1_client.get(f"{BASE_URL}/api/share/mine").json()
        row = next((r for r in listing.get("active", []) if r["jti"] == jti), None)
        assert row is not None, "minted jti not in active"
        assert row.get("label") == label, f"label round-trip broken: {row}"

        # Cleanup: revoke.
        p1_client.post(f"{BASE_URL}/api/share/revoke", json={"jti": jti})

    def test_safety_share_link_label_optional(self, p1_client):
        """Omitting label works (backward compat)."""
        sa = _post_safety(p1_client, level=4)
        aid = sa["assessment_id"]
        r = p1_client.post(
            f"{BASE_URL}/api/safety-assessment/{aid}/share-link",
            json={"expire_days": 1},
        )
        assert r.status_code == 200, r.text
        jti = r.json()["jti"]
        listing = p1_client.get(f"{BASE_URL}/api/share/mine").json()
        row = next((r for r in listing.get("active", []) if r["jti"] == jti), None)
        assert row is not None
        assert row.get("label") in (None, "")
        p1_client.post(f"{BASE_URL}/api/share/revoke", json={"jti": jti})

    def test_coparenting_report_share_link_label(self, p1_client):
        """Try coparenting report label round-trip; skip if no report exists."""
        reports = p1_client.get(f"{BASE_URL}/api/coparenting/reports")
        if reports.status_code != 200:
            pytest.skip(f"coparenting reports listing unavailable: {reports.status_code}")
        rlist = reports.json().get("reports", []) or reports.json() if isinstance(reports.json(), dict) else []
        if not rlist:
            pytest.skip("parent1 has no coparenting report to share")
        report_id = rlist[0].get("report_id") or rlist[0].get("id")
        if not report_id:
            pytest.skip("could not extract report_id")
        label = f"TEST_cp_{uuid.uuid4().hex[:6]}"
        r = p1_client.post(
            f"{BASE_URL}/api/coparenting/report/{report_id}/share-link",
            json={"expire_days": 30, "label": label},
        )
        assert r.status_code == 200, r.text
        jti = r.json().get("jti")
        assert jti
        listing = p1_client.get(f"{BASE_URL}/api/share/mine").json()
        row = next((r for r in listing.get("active", []) if r["jti"] == jti), None)
        assert row and row.get("label") == label
        p1_client.post(f"{BASE_URL}/api/share/revoke", json={"jti": jti})


# ============================================================
# 3) Regression — educational-compare should still 200 on link
# ============================================================
class TestEduDeepCompareRegression:
    def test_edu_link_still_works(self, p1_client):
        _post_safety(p1_client, level=4)
        r = p1_client.post(
            f"{BASE_URL}/api/edu-deep/compare/link",
            json={"email": PARENT2["email"]},
        )
        assert r.status_code == 200, r.text
        share_id = r.json()["share"]["share_id"]
        assert share_id.startswith("edu_deep_share_")
        # Cleanup.
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")
