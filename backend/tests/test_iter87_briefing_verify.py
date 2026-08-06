"""Iter 87 — Signed Briefing Verify (QR-scan public verification).

Covers:
    * `record_briefing_signature` writes a Mongo row + returns a
      deterministic-shape `{sig_id, verify_url}` payload.
    * `GET /api/verify/briefing/{sig_id}` returns
      `{issued: True, issued_on: "YYYY-MM-DD"}` for a known id and
      `{issued: False, issued_on: None}` for an unknown id.
    * The PDF builder accepts `briefing_sig_id` / `briefing_verify_url`
      and produces a larger PDF (footer QR + cover ID line).
    * Live round-trip: a signed briefing download creates a row that
      the verify endpoint recognises.
    * Privacy guarantee: the public response does NOT leak snapshot
      fields (scores, tiers, follow-through %).
"""
from __future__ import annotations

import asyncio
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

from dimension_companion_routes import (  # noqa: E402
    CompanionSubmit, DimensionAnswers, score_companion,
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


# ---------- PDF builder accepts the new kwargs ----------

def test_briefing_pdf_with_sig_id_is_larger_than_without():
    """QR + cover ID line adds bytes to the PDF."""
    safety_doc = {
        "assessment_id": "sa-vt",
        "created_at":    "2026-08-06T12:00:00Z",
        "result": {"level": 4, "pathway_title": "Cooperative",
                   "pathway_headline": "OK.", "pathway_summary": "OK.",
                   "recommendations": ["Written only."]},
    }
    companion_doc = {
        "assessment_id": "co-vt",
        "created_at":    "2026-08-06T13:00:00Z",
        "scoring": score_companion(CompanionSubmit(answers=DimensionAnswers(**_answers()))),
    }
    common = dict(
        parent_name="Sam Parent",
        audience="Trial Court",
        safety_doc=safety_doc,
        companion_doc=companion_doc,
        generated_at="2026-08-06T14:00:00Z",
    )
    plain = build_four_dimension_briefing_pdf(**common)
    stamped = build_four_dimension_briefing_pdf(
        **common,
        briefing_sig_id="abc123def456",
        briefing_verify_url="https://example.test/verify/briefing/abc123def456",
    )
    assert plain.startswith(b"%PDF-") and stamped.startswith(b"%PDF-")
    assert len(stamped) > len(plain)


# ---------- record_briefing_signature (unit-level, in-memory Mongo mock) ----------

class _FakeInsertResult:
    inserted_id = "x"


class _FakeCollection:
    def __init__(self):
        self.rows: list[dict] = []

    async def insert_one(self, doc):
        self.rows.append(doc)
        return _FakeInsertResult()


class _FakeDB:
    def __init__(self):
        self.briefing_signatures = _FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name)


def test_record_briefing_signature_shape():
    from briefing_verify_routes import record_briefing_signature

    db = _FakeDB()
    result = asyncio.get_event_loop().run_until_complete(
        record_briefing_signature(
            db,  # type: ignore[arg-type]
            user_id="u1",
            parent_name="Sam",
            audience="Trial Court",
            snapshot={"safety": {"level": 4}, "follow_through_pct": 87},
        )
    )
    assert set(result.keys()) == {"sig_id", "verify_url"}
    assert len(result["sig_id"]) == 16
    assert result["verify_url"].endswith(f"/verify/briefing/{result['sig_id']}")
    row = db.briefing_signatures.rows[0]
    assert row["user_id"] == "u1"
    assert row["sig_id"] == result["sig_id"]
    assert len(row["issued_on"]) == 10  # YYYY-MM-DD
    assert row["snapshot"]["safety"]["level"] == 4


# ---------- Live verify endpoint ----------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_briefing_unknown_id_is_not_issued():
    r = requests.get(f"{API}/verify/briefing/deadbeefdeadbeef", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["issued"] is False
    assert body["issued_on"] is None
    # PRIVACY: response must not leak any snapshot-shaped fields.
    for k in ("snapshot", "safety", "dimensions", "parent_name", "audience"):
        assert k not in body


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_briefing_malformed_id_is_not_issued():
    """Non-hex or oversized id should return issued=False rather than 500."""
    r = requests.get(f"{API}/verify/briefing/not-hex!!", timeout=10)
    assert r.status_code == 200
    assert r.json()["issued"] is False


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_briefing_download_then_verify_round_trip():
    """After downloading a briefing PDF, the newest sig_id in the DB should
    be verifiable via the public endpoint."""
    from motor.motor_asyncio import AsyncIOMotorClient

    login = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip(f"parent1 login unavailable: {login.status_code}")
    tok = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}

    requests.post(
        f"{API}/dimension-companion",
        headers=headers,
        json={"answers": _answers(3, 3, 3)},
        timeout=15,
    )
    dl = requests.get(
        f"{API}/dimension-companion/four-dimension-briefing/pdf",
        headers=headers,
        timeout=30,
    )
    assert dl.status_code == 200 and dl.content.startswith(b"%PDF-")

    # Look up the sig_id the endpoint just wrote for this user.
    async def _newest_sig():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"].strip('"').strip("'"))
        db = client[os.environ.get("DB_NAME", "test_database").strip('"').strip("'")]
        # login endpoint returns user_id in payload; if not, look up by email
        me = requests.get(f"{API}/auth/me", headers=headers, timeout=10).json()
        uid = me.get("user_id") or me.get("id")
        assert uid, f"could not resolve user_id from /auth/me: {me}"
        row = await db.briefing_signatures.find_one(
            {"user_id": uid}, sort=[("generated_at", -1)],
        )
        client.close()
        return row

    row = asyncio.get_event_loop().run_until_complete(_newest_sig())
    assert row is not None, "briefing_signatures row was not created on PDF download"

    r = requests.get(f"{API}/verify/briefing/{row['sig_id']}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["issued"] is True
    assert body["issued_on"] == row["issued_on"]
    # Privacy again — snapshot never leaks.
    assert "snapshot" not in body
    assert "safety" not in body
