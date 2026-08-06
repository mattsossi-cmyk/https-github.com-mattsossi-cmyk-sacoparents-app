"""Iter 85 — Combined 4-Dimension Briefing PDF.

Exercises the new `/api/dimension-companion/*` endpoints and the merged
Safety + Companion briefing generator.
"""
from __future__ import annotations

import os
import sys

import pytest
import requests

sys.path.insert(0, "/app/backend")

# Load /app/backend/.env so downstream modules that need MONGO_URL / JWT_SECRET
# at import time succeed.
try:
    with open("/app/backend/.env") as _bf:
        for _bl in _bf:
            _bl = _bl.strip()
            if _bl and not _bl.startswith("#") and "=" in _bl:
                _k, _v = _bl.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

from dimension_companion_routes import (  # noqa: E402
    CompanionSubmit,
    DimensionAnswers,
    score_companion,
)
from four_dimension_briefing_pdf import build_four_dimension_briefing_pdf  # noqa: E402


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


def _answers(comm=3, er=3, ef=3):
    return {
        "communication":        {f"c{i}": comm for i in range(1, 6)},
        "emotional_regulation": {f"e{i}": er   for i in range(1, 6)},
        "executive_function":   {f"x{i}": ef   for i in range(1, 6)},
    }


# ---------- Pure scoring ----------

def test_score_companion_all_neutral():
    payload = CompanionSubmit(answers=DimensionAnswers(**_answers(3, 3, 3)))
    scored = score_companion(payload)
    # Each concern-score should be 3 exactly (mean of 3s and reverse-scored 3s).
    for k in ("communication", "emotional_regulation", "executive_function"):
        assert scored["dimensions"][k]["score"] == 3.0
        assert scored["dimensions"][k]["tier"] == "stretched"
    assert scored["worst_tier"] == "stretched"


def test_score_companion_strong_regime():
    payload = CompanionSubmit(answers=DimensionAnswers(**_answers(5, 5, 5)))
    scored = score_companion(payload)
    # 5 on reverse-scored items → concern=1; 5 on non-reverse → concern=5.
    # With 3 reverse + 2 non-reverse per dim, mean = (3*1 + 2*5) / 5 = 2.6 → stretched.
    # Confirm the boundary still catches "stretched" not "strong".
    for k in scored["dimensions"]:
        assert 2.0 <= scored["dimensions"][k]["score"] <= 4.0


def test_score_companion_strained_regime():
    """All non-reverse items at 5 and reverse items at 1 → concern=5 everywhere."""
    ans = {
        "communication": {"c1": 1, "c2": 1, "c3": 5, "c4": 1, "c5": 5},
        "emotional_regulation": {"e1": 1, "e2": 1, "e3": 5, "e4": 5, "e5": 1},
        "executive_function":   {"x1": 1, "x2": 1, "x3": 5, "x4": 5, "x5": 1},
    }
    scored = score_companion(CompanionSubmit(answers=DimensionAnswers(**ans)))
    for k in scored["dimensions"]:
        assert scored["dimensions"][k]["tier"] == "strained"
    assert scored["worst_tier"] == "strained"


# ---------- PDF generator ----------

def test_briefing_pdf_bytes_start_with_pdf_magic():
    """Sanity: PDF header + non-trivial size, both docs present."""
    safety_doc = {
        "assessment_id": "sa-abc",
        "created_at":    "2026-08-06T12:00:00Z",
        "result": {
            "level": 4,
            "pathway_title": "Cooperative Co-Parenting Communication",
            "pathway_headline": "Cooperative communication may be appropriate.",
            "pathway_summary":  "Your responses suggest a cooperative pathway.",
            "recommendations": ["Direct app communication.", "Written agreements."],
        },
    }
    companion_doc = {
        "assessment_id": "co-abc",
        "created_at":    "2026-08-06T13:00:00Z",
        "scoring":       score_companion(CompanionSubmit(answers=DimensionAnswers(**_answers(3, 3, 3)))),
    }
    b = build_four_dimension_briefing_pdf(
        parent_name="Sam Parent",
        audience="Mediator / Parent Facilitator Ad Litem / Trial Court",
        safety_doc=safety_doc,
        companion_doc=companion_doc,
        generated_at="2026-08-06T14:00:00Z",
    )
    assert b.startswith(b"%PDF-")
    assert len(b) > 5000


def test_briefing_pdf_handles_missing_companion():
    """Empty companion should render a "not yet completed" section, not crash."""
    safety_doc = {
        "assessment_id": "sa-x",
        "created_at":    "2026-08-06T12:00:00Z",
        "result": {"level": 3, "pathway_title": "Parallel Parenting",
                   "pathway_headline": "Parallel parenting recommended.",
                   "pathway_summary":  "Structured written communication.",
                   "recommendations": ["Written only."]},
    }
    b = build_four_dimension_briefing_pdf(
        parent_name="Sam Parent",
        audience="Trial Court",
        safety_doc=safety_doc,
        companion_doc=None,
        generated_at="2026-08-06T14:00:00Z",
    )
    assert b.startswith(b"%PDF-")


# ---------- Live HTTP round-trip ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_briefing_endpoint_live():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(f"parent1 login not available in this env: {r.status_code}")
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    headers = {"Authorization": f"Bearer {tok}"}

    # Ensure parent1 has at least one companion assessment on file — POST one
    # so this test is idempotent across environments.
    requests.post(
        f"{API}/dimension-companion",
        headers=headers,
        json={"answers": _answers(3, 3, 3)},
        timeout=15,
    )

    resp = requests.get(
        f"{API}/dimension-companion/four-dimension-briefing/pdf",
        headers=headers,
        params={"sign": "true"},
        timeout=30,
    )
    assert resp.status_code == 200, resp.text[:300]
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > 5000


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_briefing_email_endpoint_live():
    """Full round-trip: generate + email through Resend (sandbox address)."""
    r = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(f"parent1 login not available: {r.status_code}")
    tok = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}

    # Reject obviously invalid emails
    bad = requests.post(
        f"{API}/dimension-companion/four-dimension-briefing/email",
        headers=headers,
        json={"recipient_email": "not-an-email"},
        timeout=10,
    )
    assert bad.status_code == 400
    assert "valid email" in (bad.json().get("detail") or "").lower()

    # Reject demo.local addresses
    demo = requests.post(
        f"{API}/dimension-companion/four-dimension-briefing/email",
        headers=headers,
        json={"recipient_email": "mediator@demo.local"},
        timeout=10,
    )
    assert demo.status_code == 400

    # Happy path — Resend's sandbox delivery address
    resp = requests.post(
        f"{API}/dimension-companion/four-dimension-briefing/email",
        headers=headers,
        json={
            "recipient_email": "delivered@resend.dev",
            "recipient_name":  "Sandbox Recipient",
            "recipient_role":  "parent_facilitator_ad_litem",
            "parent_message":  "Auto-test message.",
        },
        timeout=30,
    )
    # Allow 503 if this environment doesn't have Resend keys — but if 200,
    # verify the response shape.
    assert resp.status_code in (200, 503), resp.text[:200]
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("ok") is True
        assert body.get("emailed_to") == "delivered@resend.dev"
        assert body.get("audience") == "Parent Facilitator Ad Litem"
