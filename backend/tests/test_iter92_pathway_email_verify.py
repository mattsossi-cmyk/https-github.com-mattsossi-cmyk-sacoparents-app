"""Iter 92 — Pathway Report Email + QR Verify.

Covers:
    * `record_pathway_signature` writes a Mongo row + returns a
      deterministic-shape `{sig_id, verify_url}` payload.
    * `GET /api/verify/pathway/{sig_id}` returns
      `{issued: True, ...}` for a known id and `{issued: False, ...}`
      for an unknown id.
    * The pathway PDF builder accepts `pathway_sig_id` /
      `pathway_verify_url` kwargs and produces a larger PDF (QR footer).
    * Live round-trip: downloading a pathway PDF creates a row that the
      public verify endpoint recognises AND does not leak snapshot data.
    * `POST /api/pathway-report/email` validates recipient email shape
      and refuses `@demo.local` addresses.
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

from pathway_report_pdf import build_pathway_report_pdf  # noqa: E402


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
TEST_PASSWORD = "TestPass123!"  # noqa: S105  test fixture


# ---- Minimal pathway result payload for unit tests --------------------------

def _stub_result() -> dict:
    return {
        "primary_pathway_key":       "mediation",
        "primary_pathway_label":     "Mediation with a co-parenting mediator",
        "primary_pathway_summary":   "Considered a good fit given the data.",
        "hard_locked_by":            [],
        "factors_supporting_primary": ["Compare share consented"],
        "goals_before_or_during":    ["Agree on documentation channels"],
        "suitability_profile":       [
            {"key": "mediation",       "label": "Mediation",       "suitability": "high"},
            {"key": "collaborative",   "label": "Collaborative",   "suitability": "moderate"},
            {"key": "arbitration",     "label": "Arbitration",     "suitability": "low"},
            {"key": "litigation",      "label": "Litigation",      "suitability": "not_indicated"},
        ],
        "considerations":            ["Not legal advice."],
        "is_dual_party":             False,
        "generated_at":              "2026-08-09T12:00:00Z",
    }


# ---- PDF builder accepts the new kwargs -------------------------------------

def test_pathway_pdf_with_sig_id_is_larger_than_without():
    plain = build_pathway_report_pdf(result=_stub_result())
    stamped = build_pathway_report_pdf(
        result=_stub_result(),
        pathway_sig_id="abc123def4567890",
        pathway_verify_url="https://example.test/verify/pathway/abc123def4567890",
    )
    assert plain.startswith(b"%PDF-")
    assert stamped.startswith(b"%PDF-")
    assert len(stamped) > len(plain), "QR stamp should add bytes"


# ---- record_pathway_signature (unit-level, in-memory Mongo mock) -----------

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
        self.pathway_signatures = _FakeCollection()

    def __getitem__(self, name):
        return getattr(self, name)


def test_record_pathway_signature_shape():
    from pathway_verify_routes import record_pathway_signature

    db = _FakeDB()
    result = asyncio.get_event_loop().run_until_complete(
        record_pathway_signature(
            db,  # type: ignore[arg-type]
            user_id="u1",
            is_dual_party=True,
            share_id="share-abc",
            snapshot={"primary_key": "mediation", "hard_locked": False},
        )
    )
    assert set(result.keys()) == {"sig_id", "verify_url"}
    assert len(result["sig_id"]) == 16
    assert result["verify_url"].endswith(f"/verify/pathway/{result['sig_id']}")
    row = db.pathway_signatures.rows[0]
    assert row["user_id"] == "u1"
    assert row["is_dual_party"] is True
    assert row["share_id"] == "share-abc"
    assert row["sig_id"] == result["sig_id"]
    assert len(row["issued_on"]) == 10  # YYYY-MM-DD
    assert row["snapshot"]["primary_key"] == "mediation"


# ---- Live verify endpoint --------------------------------------------------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_pathway_unknown_id_is_not_issued():
    r = requests.get(f"{API}/verify/pathway/deadbeefdeadbeef", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["issued"] is False
    assert body["issued_on"] is None
    # PRIVACY: never leak snapshot fields.
    for k in ("snapshot", "primary_key", "primary_label", "hard_locked", "user_id"):
        assert k not in body


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_verify_pathway_malformed_id_is_not_issued():
    r = requests.get(f"{API}/verify/pathway/not-hex!!", timeout=10)
    assert r.status_code == 200
    assert r.json()["issued"] is False


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_pathway_preview_pdf_then_verify_round_trip():
    """After downloading a pathway preview PDF, the newest sig_id in the DB
    should be verifiable via the public endpoint."""
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

    dl = requests.get(
        f"{API}/pathway-report/preview/pdf",
        headers=headers,
        timeout=30,
    )
    assert dl.status_code == 200 and dl.content.startswith(b"%PDF-")

    async def _newest_sig():
        client = AsyncIOMotorClient(
            os.environ["MONGO_URL"].strip('"').strip("'"))
        db = client[os.environ.get("DB_NAME", "test_database")
                    .strip('"').strip("'")]
        me = requests.get(f"{API}/auth/me", headers=headers, timeout=10).json()
        uid = me.get("user_id") or me.get("id")
        assert uid, f"could not resolve user_id: {me}"
        row = await db.pathway_signatures.find_one(
            {"user_id": uid}, sort=[("generated_at", -1)],
        )
        client.close()
        return row

    row = asyncio.get_event_loop().run_until_complete(_newest_sig())
    assert row is not None, (
        "pathway_signatures row was not created on preview PDF download"
    )
    assert row["is_dual_party"] is False
    assert row["share_id"] == ""

    r = requests.get(f"{API}/verify/pathway/{row['sig_id']}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["issued"] is True
    assert body["is_dual_party"] is False
    assert body["issued_on"] == row["issued_on"]
    # Privacy again.
    assert "snapshot" not in body
    assert "primary_key" not in body
    assert "user_id" not in body


# ---- Email endpoint validation ---------------------------------------------

@pytest.mark.skipif(not API, reason="No backend URL available")
def test_email_pathway_requires_auth():
    r = requests.post(
        f"{API}/pathway-report/email",
        json={"recipient_email": "med@example.test", "recipient_role": "mediator"},
        timeout=10,
    )
    assert r.status_code in (401, 403), (
        f"expected auth challenge, got {r.status_code}: {r.text}"
    )


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_email_pathway_rejects_bad_email():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip("parent1 login unavailable")
    tok = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}
    r = requests.post(
        f"{API}/pathway-report/email",
        headers=headers,
        json={"recipient_email": "not-an-email", "recipient_role": "mediator"},
        timeout=10,
    )
    assert r.status_code == 400
    assert "valid email" in r.text.lower() or "email address" in r.text.lower()


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_email_pathway_rejects_demo_local():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip("parent1 login unavailable")
    tok = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}
    r = requests.post(
        f"{API}/pathway-report/email",
        headers=headers,
        json={"recipient_email": "mediator@demo.local", "recipient_role": "mediator"},
        timeout=10,
    )
    assert r.status_code == 400
    assert "real email" in r.text.lower()


@pytest.mark.skipif(not API, reason="No backend URL available")
def test_email_pathway_rejects_bogus_share_id():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        pytest.skip("parent1 login unavailable")
    tok = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}
    r = requests.post(
        f"{API}/pathway-report/email",
        headers=headers,
        json={
            "recipient_email": "mediator@example.com",
            "recipient_role":  "mediator",
            "share_id":        "not-a-real-share-id",
        },
        timeout=15,
    )
    # 404 (share not found) or 409 (not active) both indicate the consent
    # gate fired correctly; 500 or 200 would be regressions.
    assert r.status_code in (404, 409), (
        f"consent gate did not fire: {r.status_code}: {r.text}"
    )
