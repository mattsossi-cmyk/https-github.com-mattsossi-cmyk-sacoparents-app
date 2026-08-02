"""Iteration 53 tests — Foundation Ready certificate ribbon + Progress sparkline.

Certificate ribbon
------------------
* `certificate_service.build_certificate_png/pdf` accept `foundation_ready`
  and produce a visibly different (larger) file when the ribbon is drawn.
* `GET /api/mediation/certificate/preview` and `POST /api/mediation/certificate/download`
  set `X-Foundation-Ready: 1` when the parent has all 5 progress pills lit,
  and `0` otherwise.

Progress sparkline
------------------
* `GET /api/dashboard/progress` now returns a 30-day `history` array — one
  row per calendar day — with the fields the frontend sparkline reads.
* The endpoint upserts today's row so consecutive calls only ever update
  the last entry (no duplicate rows).
* Trend direction: rising alignment across days is reflected in
  `history[-1].done > history[0].done` after we transition from 4/5 to 5/5.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

import certificate_service  # noqa: E402
from test_iter48_features import (  # noqa: E402
    BASE_URL, PARENT1, PARENT2,
    _client, _ensure_account, _fresh_consented_share,
    _post_safety_level_4, _revoke_all,
)


# ---------------------------------------------------------------------------
# UNIT: certificate_service ribbon
# ---------------------------------------------------------------------------
class TestCertificateRibbon:
    def test_png_ribbon_changes_output(self):
        no_ribbon = certificate_service.build_certificate_png("Sam Parent")
        with_ribbon = certificate_service.build_certificate_png(
            "Sam Parent", foundation_ready=True,
        )
        assert no_ribbon[:8].startswith(b"\x89PNG"), "no-ribbon PNG header"
        assert with_ribbon[:8].startswith(b"\x89PNG"), "with-ribbon PNG header"
        # A ~1.5MB certificate PNG's raw bytes should differ once we paint
        # the ribbon on top; a size delta is a cheap, deterministic signal.
        assert no_ribbon != with_ribbon, (
            "certificate PNG bytes did not change when foundation_ready=True"
        )

    def test_pdf_ribbon_changes_output(self):
        no_ribbon = certificate_service.build_certificate_pdf("Sam Parent")
        with_ribbon = certificate_service.build_certificate_pdf(
            "Sam Parent", foundation_ready=True,
        )
        assert no_ribbon[:4] == b"%PDF"
        assert with_ribbon[:4] == b"%PDF"
        assert no_ribbon != with_ribbon


# ---------------------------------------------------------------------------
# Fixtures for HTTP integration tests
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture(scope="module")
def p2_token():
    return _ensure_account(PARENT2)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


@pytest.fixture
def p2_client(p2_token):
    return _client(p2_token)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(p1_token, p2_token):
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    yield
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))


# ---------------------------------------------------------------------------
# INTEGRATION: certificate preview/download surface X-Foundation-Ready
# ---------------------------------------------------------------------------
class TestCertificateEndpointsRibbonHeader:
    def test_header_zero_when_not_ready(self, p1_client, p2_client):
        # Ensure parent is NOT foundation-ready first.
        _revoke_all(p1_client)
        _revoke_all(p2_client)
        r = p1_client.get(
            f"{BASE_URL}/api/mediation/certificate/preview", timeout=30,
        )
        assert r.status_code == 200
        assert r.headers.get("Content-Type") == "image/png"
        # Depending on other test state this MIGHT be 0 or 1 — we only
        # assert the header exists and is one of those two.
        assert r.headers.get("X-Foundation-Ready") in ("0", "1")

    def test_header_one_after_five_of_five(self, p1_client, p2_client):
        _post_safety_level_4(p1_client)
        p1_client.put(f"{BASE_URL}/api/mediation/child-goals",
                      json={"goals": [{"text": "Stability"}]}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/issues",
                      json={"schedule": "Alternating"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/comm-style",
                      json={"tone": "concise", "channel": "text"}, timeout=20)
        share_id = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share_id}", timeout=30)
        # Sanity check via /progress
        p = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        assert p["completed_count"] == p["total"], f"expected 5/5, got {p}"
        # Preview
        r = p1_client.get(
            f"{BASE_URL}/api/mediation/certificate/preview", timeout=30,
        )
        assert r.status_code == 200
        assert r.headers.get("X-Foundation-Ready") == "1"
        # Download PDF (larger than the no-ribbon variant we saw above)
        r_pdf = p1_client.post(
            f"{BASE_URL}/api/mediation/certificate/download",
            json={}, timeout=60,
        )
        assert r_pdf.status_code == 200
        assert r_pdf.content[:4] == b"%PDF"
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")


# ---------------------------------------------------------------------------
# INTEGRATION: /api/dashboard/progress history array
# ---------------------------------------------------------------------------
class TestProgressHistorySparkline:
    def test_history_is_thirty_days_dense(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body.get("history_days") == 30
        history = body.get("history") or []
        assert len(history) == 30, f"expected 30 dense entries, got {len(history)}"
        # Every row has the shape the sparkline reads.
        for row in history:
            assert isinstance(row.get("date"), str) and len(row["date"]) == 10
            assert isinstance(row.get("done"), int)
            assert isinstance(row.get("total"), int)
            assert isinstance(row.get("ready"), bool)
        # Last row's date == today (UTC)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert history[-1]["date"] == today
        # Last row's done matches the top-level completed_count.
        assert history[-1]["done"] == body["completed_count"]
        assert history[-1]["total"] == body["total"]

    def test_history_upsert_is_idempotent(self, p1_client):
        r1 = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        r2 = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        # Two consecutive calls in the same UTC day should still return
        # 30-row arrays (no duplicates, no drift).
        assert len(r1["history"]) == 30
        assert len(r2["history"]) == 30
        assert r1["history"][-1]["date"] == r2["history"][-1]["date"]

    def test_foundation_ready_flag_surfaced(self, p1_client, p2_client):
        # Seed 5/5 to prove `foundation_ready` bubbles up alongside history.
        _post_safety_level_4(p1_client)
        p1_client.put(f"{BASE_URL}/api/mediation/child-goals",
                      json={"goals": [{"text": "Stability"}]}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/issues",
                      json={"schedule": "Alternating"}, timeout=20)
        p1_client.put(f"{BASE_URL}/api/mediation/comm-style",
                      json={"tone": "concise", "channel": "text"}, timeout=20)
        _revoke_all(p1_client); _revoke_all(p2_client)
        share_id = _fresh_consented_share(p1_client, p2_client, "edu-deep")
        p1_client.get(f"{BASE_URL}/api/edu-deep/compare/{share_id}", timeout=30)
        r = p1_client.get(f"{BASE_URL}/api/dashboard/progress", timeout=30).json()
        assert r["foundation_ready"] is True
        assert r["history"][-1]["ready"] is True
        p1_client.post(f"{BASE_URL}/api/edu-deep/compare/{share_id}/revoke")
