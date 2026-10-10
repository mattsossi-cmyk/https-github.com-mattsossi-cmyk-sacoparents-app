"""Iteration 114 — Backend tests for:

A1/A2 — Child alignment-records removal (portal state, complete-report PDF, share).
D1   — Self-Assessment goal/reached endpoint.
"""
from __future__ import annotations

import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

TEST_PASS = "TestPass123!"


# ------------------------------------------------------------------ #
# Session-scoped login against the fixed parent1 account.             #
# ------------------------------------------------------------------ #
@pytest.fixture(scope="module")
def parent1_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "parent1@test.com", "password": TEST_PASS},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(parent1_token):
    return {"Authorization": f"Bearer {parent1_token}", "Content-Type": "application/json"}


# ------------------------------------------------------------------ #
# A1 — portal state never stores child alignment records              #
# ------------------------------------------------------------------ #
def test_a1_put_state_strips_align_records(auth_headers):
    body = {
        "align_records": [
            {"title": "Pediatrician plan", "category": "medical", "detail": "x"}
        ],
        "updated_at": "2026-01-01T00:00:00Z",
    }
    r = requests.put(f"{BASE_URL}/api/portal/state", json=body, headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text

    g = requests.get(f"{BASE_URL}/api/portal/state", headers=auth_headers, timeout=30)
    assert g.status_code == 200
    data = g.json()
    state = data.get("state", data)
    assert state.get("align_records") == [], \
        f"align_records should be []: {state.get('align_records')}"


# ------------------------------------------------------------------ #
# A2 — Complete-report PDF strips align_records                       #
# ------------------------------------------------------------------ #
def test_a2_complete_report_pdf_strips_records(auth_headers):
    body = {
        "safety_ack": {"flagged": False},
        "align_records": [
            {"title": "Pediatrician plan", "category": "medical",
             "detail": "visited Dr Secret"},
        ],
        "author_name": "Sam Parent",
    }
    r = requests.post(
        f"{BASE_URL}/api/portal/complete-report-pdf",
        json=body, headers=auth_headers, timeout=60,
    )
    assert r.status_code == 200, r.text[:300]
    assert r.headers.get("content-type", "").startswith("application/pdf")
    pdf_bytes = r.content

    # Decode raw bytes (text extraction via pypdf is more reliable but
    # the privacy note + absent 'Pediatrician' is easily detectable in
    # the raw stream too).
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        text = pdf_bytes.decode("latin-1", errors="ignore")

    assert "Pediatrician" not in text, "record title must not leak into PDF"
    assert "Dr Secret" not in text, "record detail must not leak into PDF"
    assert "SA CoParents does not keep" in text, \
        "privacy note missing from Complete Report PDF"


# ------------------------------------------------------------------ #
# A2b — /portal/share strips align_records from payload               #
# ------------------------------------------------------------------ #
def test_a2b_portal_share_strips_align_records(auth_headers):
    # /portal/share is IP rate-limited; space out from other tests.
    time.sleep(2)
    body = {
        "artefact_type": "complete",
        "payload": {
            "safety_ack": {"flagged": False},
            "align_records": [
                {"title": "Pediatrician plan", "category": "medical", "detail": "x"}
            ],
            "foundation_text": "Short foundation.",
        },
    }
    r = requests.post(
        f"{BASE_URL}/api/portal/share", json=body, headers=auth_headers, timeout=30,
    )
    if r.status_code == 429:
        pytest.skip("portal/share rate-limited")
    assert r.status_code in (200, 201), r.text[:300]
    data = r.json()
    token = data.get("share_id") or data.get("token")
    assert token, f"share response missing share_id: {data}"

    # Fetch share PDF and confirm no record text
    pdf_r = requests.get(f"{BASE_URL}/api/portal/share/{token}.pdf", timeout=60)
    if pdf_r.status_code == 200:
        try:
            from pypdf import PdfReader
            import io
            text = "\n".join(
                (p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf_r.content)).pages
            )
        except Exception:
            text = pdf_r.content.decode("latin-1", errors="ignore")
        assert "Pediatrician" not in text
        assert "SA CoParents does not keep" in text


# ------------------------------------------------------------------ #
# D1 — Self-Assessment goal/reached endpoint                          #
# ------------------------------------------------------------------ #
def _journey6_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "journey6@test.com", "password": TEST_PASS},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def journey6_headers():
    return {
        "Authorization": f"Bearer {_journey6_token()}",
        "Content-Type": "application/json",
    }


def test_d1_history_includes_reached_at(journey6_headers):
    r = requests.get(f"{BASE_URL}/api/self-assessment/history", headers=journey6_headers, timeout=30)
    assert r.status_code == 200
    data = r.json()
    entries = data.get("entries", [])
    assert len(entries) >= 1, "journey6 should have Self-Assessment history"
    for e in entries:
        assert "reached_at" in e, "SAEntry must expose reached_at"


def test_d1_goal_reached_flow(journey6_headers):
    r = requests.get(f"{BASE_URL}/api/self-assessment/history", headers=journey6_headers, timeout=30)
    entries = r.json().get("entries", [])
    with_goal = [e for e in entries if (e.get("goal") or "").strip()]
    if not with_goal:
        pytest.skip("journey6 has no entry with a goal")
    entry_id = with_goal[0]["id"]
    original = with_goal[0].get("reached_at")

    # Mark reached
    rr = requests.post(
        f"{BASE_URL}/api/self-assessment/goal/reached",
        json={"entry_id": entry_id, "reached": True},
        headers=journey6_headers, timeout=30,
    )
    assert rr.status_code == 200, rr.text
    body = rr.json()
    assert body.get("reached_at"), "reached_at should be set"
    assert "T" in body["reached_at"], "reached_at should be ISO datetime"

    # Verify persisted via GET history
    r2 = requests.get(f"{BASE_URL}/api/self-assessment/history", headers=journey6_headers, timeout=30)
    e2 = next(e for e in r2.json()["entries"] if e["id"] == entry_id)
    assert e2.get("reached_at")

    # Undo (restore original state — leave journey6 un-reached as spec requires)
    ru = requests.post(
        f"{BASE_URL}/api/self-assessment/goal/reached",
        json={"entry_id": entry_id, "reached": False},
        headers=journey6_headers, timeout=30,
    )
    assert ru.status_code == 200
    assert ru.json().get("reached_at") is None


def test_d1_unknown_entry_returns_404(journey6_headers):
    r = requests.post(
        f"{BASE_URL}/api/self-assessment/goal/reached",
        json={"entry_id": f"missing-{uuid.uuid4().hex[:8]}", "reached": True},
        headers=journey6_headers, timeout=30,
    )
    assert r.status_code == 404


def test_d1_no_auth_returns_401():
    r = requests.post(
        f"{BASE_URL}/api/self-assessment/goal/reached",
        json={"entry_id": "x", "reached": True},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


def test_d1_entry_without_goal_returns_422(journey6_headers):
    """Find an entry without a goal (if any) and expect 422."""
    r = requests.get(f"{BASE_URL}/api/self-assessment/history", headers=journey6_headers, timeout=30)
    entries = r.json().get("entries", [])
    no_goal = [e for e in entries if not (e.get("goal") or "").strip()]
    if not no_goal:
        pytest.skip("journey6 has no entries without a goal (all 4 have goals in some seeds)")
    rr = requests.post(
        f"{BASE_URL}/api/self-assessment/goal/reached",
        json={"entry_id": no_goal[0]["id"], "reached": True},
        headers=journey6_headers, timeout=30,
    )
    assert rr.status_code == 422


# ------------------------------------------------------------------ #
# C1 — Public /what-professionals-see page accessible without login   #
# ------------------------------------------------------------------ #
def test_c1_what_pros_see_public_page_served():
    """Frontend route — just confirm the SPA shell responds 200."""
    r = requests.get(f"{BASE_URL}/what-professionals-see", timeout=30)
    assert r.status_code == 200
    # SPA returns index.html — a bare HTML shell is fine, the content
    # is rendered client-side.
    assert "<html" in r.text.lower()
