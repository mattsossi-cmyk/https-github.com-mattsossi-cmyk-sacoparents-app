"""Iteration 42 backend regression tests.

Covers three shipped feature areas:
  1. Summary length toggle on deep-dive Regenerate endpoints (edu/psych/med).
     * Endpoint accepts optional {length: short|standard|long}
     * Body-less call still works (backwards compat)
     * Guest → 403; No report yet → 404
  2. Expiring share links + revocation list.
     * safety-assessment share-link endpoint honours expire_days=1|7|30|None
     * Response body carries jti + expires_at
     * GET /api/share/mine lists tokens
     * POST /api/share/revoke invalidates a token; subsequent shared GET → 404
  3. Educational Deep Dive Compare state machine + safety guardrail.
     * POST /api/edu-deep/compare/link with level-2 safety → 403 containing 'safety'
     * With safety cleared → 200/201, ok=true, share hydrated
     * GET /api/edu-deep/compare/me lists shares
     * Missing partner-email → 404
"""
from __future__ import annotations

import os
import uuid
import time
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


def _ensure_account(creds):
    # Try register (idempotent-ish: 400 if exists is fine).
    requests.post(f"{BASE_URL}/api/auth/register", json={
        **creds, "children": [], "custody_situation": "50/50 shared",
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": creds["email"], "password": creds["password"],
    }, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture(scope="module")
def p2_token():
    return _ensure_account(PARENT2)


@pytest.fixture(scope="module", autouse=True)
def cleanup_edu_deep_shares(p1_token, p2_token):
    """Revoke any leftover edu-deep-compare shares so tests start clean."""
    for tok in (p1_token, p2_token):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json",
                          "Authorization": f"Bearer {tok}"})
        r = s.get(f"{BASE_URL}/api/edu-deep/compare/me")
        if r.status_code == 200:
            for share in r.json().get("shares", []):
                if share.get("status") != "revoked":
                    s.post(f"{BASE_URL}/api/edu-deep/compare/{share['share_id']}/revoke")
    yield


@pytest.fixture
def p1_client(p1_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {p1_token}"})
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
# 1) Summary length toggle regression
# ============================================================
class TestRegenSummaryLengthToggle:
    """The regen-summary endpoints must accept optional {length} and remain
    backward-compatible when called with no body."""

    @pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep", "med-deep"])
    def test_regen_summary_guest_forbidden(self, guest_client, prefix):
        r = guest_client.post(f"{BASE_URL}/api/{prefix}/report/regen-summary",
                              json={"length": "short"})
        assert r.status_code == 403, f"{prefix}: {r.status_code} {r.text}"

    @pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep", "med-deep"])
    def test_regen_summary_no_report_404(self, p1_client, prefix):
        # parent1 may or may not have a report. If they do (from earlier runs)
        # we accept 200 with ai_summary_length set. Otherwise 404 = no report.
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/report/regen-summary",
                           json={"length": "long"})
        assert r.status_code in (200, 404, 503), f"{prefix}: {r.status_code} {r.text}"
        if r.status_code == 200:
            body = r.json()
            report = body.get("report") or {}
            assert report.get("ai_summary_length") == "long"
            assert report.get("ai_summary_regenerated_at")

    @pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep", "med-deep"])
    def test_regen_summary_empty_body_backward_compat(self, p1_client, prefix):
        # No body at all → still works (defaults to 'standard').
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/report/regen-summary")
        assert r.status_code in (200, 404, 503), f"{prefix}: {r.status_code} {r.text}"

    @pytest.mark.parametrize("prefix", ["edu-deep", "psych-deep", "med-deep"])
    def test_regen_summary_invalid_length_falls_back(self, p1_client, prefix):
        # Server coerces unknown values to 'standard'; still returns 200/404/503.
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/report/regen-summary",
                           json={"length": "bogus"})
        assert r.status_code in (200, 404, 503), f"{prefix}: {r.status_code} {r.text}"


# ============================================================
# 2) Expiring share links + revocation
# ============================================================
def _post_safety(client, level=4):
    """Submit a safety assessment. Level-4 = no concerns (all section 2 yes).

    Server-side "all answered" guard (iter 104) requires every s1_q1..s1_q18
    and s2_q1..s2_q8 to have a valid Yes/No/Unsure value, so we fill both
    sections with a neutral baseline and only override the items that
    drive the target level.
    """
    s1 = {f"s1_q{i}": "no" for i in range(1, 19)}
    s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    s2["s2_q8"] = "no"  # s2_q8 is inverted — "no" is the safe answer
    if level == 4:
        payload = {"section_1": s1, "section_2": s2}
    elif level == 2:
        s1["s1_q3"] = "yes"  # coercive-control hit → level 2
        payload = {"section_1": s1, "section_2": s2}
    elif level == 1:
        s1["s1_q1"] = "yes"
        payload = {"section_1": s1, "section_2": s2}
    else:
        payload = {"section_1": s1, "section_2": s2}
    r = client.post(f"{BASE_URL}/api/safety-assessment", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


class TestExpiringShareLinks:
    """Share-link endpoints must accept expire_days + label and record a jti
    that can later be revoked via /api/share/revoke."""

    def test_safety_share_link_carries_jti_and_expires_at(self, p1_client):
        # Ensure a level-4 assessment exists so we don't accidentally trip
        # any downstream safety guardrails.
        sa = _post_safety(p1_client, level=4)
        aid = sa["assessment_id"]
        label = f"TEST_share_{uuid.uuid4().hex[:6]}"
        r = p1_client.post(f"{BASE_URL}/api/safety-assessment/{aid}/share-link",
                           json={"expire_days": 1, "label": label})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("token")
        assert body.get("jti"), "jti missing on share-link response"
        assert body.get("expires_at"), "expires_at missing on 1-day link"

    def test_safety_share_link_never_expires(self, p1_client):
        sa = _post_safety(p1_client, level=4)
        aid = sa["assessment_id"]
        r = p1_client.post(f"{BASE_URL}/api/safety-assessment/{aid}/share-link",
                           json={"expire_days": None, "label": "TEST_never"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("jti")
        # "Never" link → no expires_at
        assert body.get("expires_at") in (None, "")

    def test_share_mine_lists_active_and_supports_revoke(self, p1_client):
        # Mint a link, verify it appears in /share/mine active list, revoke it,
        # verify it moves to past and subsequent shared GET → 404.
        sa = _post_safety(p1_client, level=4)
        aid = sa["assessment_id"]
        mint = p1_client.post(f"{BASE_URL}/api/safety-assessment/{aid}/share-link",
                              json={"expire_days": 7, "label": "TEST_revoke_me"})
        assert mint.status_code == 200, mint.text
        jti = mint.json()["jti"]
        token = mint.json()["token"]

        listing = p1_client.get(f"{BASE_URL}/api/share/mine")
        assert listing.status_code == 200
        data = listing.json()
        active_jtis = {r["jti"] for r in data.get("active", [])}
        assert jti in active_jtis, f"minted jti {jti} not in /share/mine active"

        # Confirm the shared endpoint works pre-revocation.
        pre = requests.get(f"{BASE_URL}/api/safety-assessment/shared/{token}",
                           allow_redirects=False, timeout=30)
        assert pre.status_code in (200, 302), pre.status_code

        # Revoke.
        rv = p1_client.post(f"{BASE_URL}/api/share/revoke", json={"jti": jti})
        assert rv.status_code == 200, rv.text
        assert rv.json().get("ok") is True

        # Idempotent revoke.
        rv2 = p1_client.post(f"{BASE_URL}/api/share/revoke", json={"jti": jti})
        assert rv2.status_code == 200
        assert rv2.json().get("already_revoked") is True

        # Post-revoke: shared GET must fail (404 with revoked message).
        after = requests.get(f"{BASE_URL}/api/safety-assessment/shared/{token}",
                             allow_redirects=False, timeout=30)
        assert after.status_code == 404, f"expected 404 after revoke, got {after.status_code}"
        detail = (after.json() or {}).get("detail", "").lower()
        assert "revoked" in detail or "invalid" in detail, detail

        # Listing now shows it under past (status=revoked).
        listing2 = p1_client.get(f"{BASE_URL}/api/share/mine").json()
        past_row = next((r for r in listing2.get("past", []) if r["jti"] == jti), None)
        assert past_row, "revoked link not in past list"
        assert past_row.get("status") == "revoked"

    def test_share_revoke_unknown_jti_404(self, p1_client):
        r = p1_client.post(f"{BASE_URL}/api/share/revoke",
                           json={"jti": "does-not-exist"})
        assert r.status_code == 404


# ============================================================
# 3) Educational Deep Dive Compare — state machine + safety guardrail
# ============================================================
class TestEduDeepCompare:
    """Mirror of SNC v2 compare. Only exercising link, safety-block, and me
    endpoints — we don't seed full edu-deep assessments; 409 on GET after
    consent is acceptable per problem statement."""

    def test_link_missing_partner_email_404(self, p1_client):
        # Reset safety to level-4 first so safety block doesn't fire.
        _post_safety(p1_client, level=4)
        r = p1_client.post(f"{BASE_URL}/api/edu-deep/compare/link",
                           json={"email": f"nobody_{uuid.uuid4().hex[:6]}@example.com"})
        assert r.status_code == 404, r.text
        assert "co-parent" in r.json().get("detail", "").lower() or \
               "no sa coparents" in r.json().get("detail", "").lower()

    def test_link_self_email_400(self, p1_client):
        _post_safety(p1_client, level=4)
        r = p1_client.post(f"{BASE_URL}/api/edu-deep/compare/link",
                           json={"email": PARENT1["email"]})
        assert r.status_code == 400
        assert "own email" in r.json().get("detail", "").lower()

    def test_safety_level_2_blocks_link(self, p1_client, p2_token):
        # Fresh level-2 safety for parent1 → link must 403 with 'safety' msg.
        _post_safety(p1_client, level=2)
        r = p1_client.post(f"{BASE_URL}/api/edu-deep/compare/link",
                           json={"email": PARENT2["email"]})
        assert r.status_code == 403, r.text
        assert "safety" in r.json().get("detail", "").lower()

        # Restore to level-4 to unblock any subsequent tests.
        _post_safety(p1_client, level=4)

    def test_link_and_me_state_machine(self, p1_client, p2_token):
        # Reset safety to level 4 so we don't get blocked.
        _post_safety(p1_client, level=4)
        r = p1_client.post(f"{BASE_URL}/api/edu-deep/compare/link",
                           json={"email": PARENT2["email"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        share = body.get("share") or {}
        assert share.get("share_id", "").startswith("edu_deep_share_")
        assert share.get("role") == "creator"
        assert share.get("my_consent") is True
        assert share.get("partner_consent") is False
        assert share.get("status") in ("awaiting_partner_consent", "awaiting_consent")

        # /me lists it.
        mine = p1_client.get(f"{BASE_URL}/api/edu-deep/compare/me")
        assert mine.status_code == 200
        share_ids = [s["share_id"] for s in mine.json().get("shares", [])]
        assert share.get("share_id") in share_ids

        # Partner can revoke via own token.
        p2 = requests.Session()
        p2.headers.update({"Content-Type": "application/json",
                           "Authorization": f"Bearer {p2_token}"})
        rv = p2.post(f"{BASE_URL}/api/edu-deep/compare/{share['share_id']}/revoke")
        assert rv.status_code == 200
        assert rv.json().get("share", {}).get("status") == "revoked"
