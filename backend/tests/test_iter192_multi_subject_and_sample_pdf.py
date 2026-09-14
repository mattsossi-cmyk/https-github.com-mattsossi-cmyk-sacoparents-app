"""Iter 192 — Multi-Subject Alignment Reports + Sample PDF.

Locks:
  * Five subjects in the SUBJECTS registry with the same 6-prompt shape.
  * Safety flagged `sensitive`; `is_sensitive_subject("safety")` is True.
  * `/subjects` public endpoint surfaces every subject with the
    `sensitive` flag exposed so the frontend can render the disclosure.
  * `/compare` for safety returns 428 unless
    `safety_dual_consent_acknowledged: true` is sent.
  * `_load_reflection_answers` in `joint_agreement_routes` refuses to
    load Safety data so a joint report never auto-merges Safety.
  * Public sample PDF renders end-to-end via
    `/api/insights/samples/co-parenting-alignment-report.pdf`.
"""
from __future__ import annotations

import io
import os
import sys

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alignment_reflection_questions import (  # noqa: E402
    SUBJECT_CO_PARENTING,
    SUBJECT_COMMUNICATION,
    SUBJECT_EDUCATIONAL,
    SUBJECT_MEDICAL,
    SUBJECT_SAFETY,
    SUBJECTS,
    is_known_subject,
    is_sensitive_subject,
    prompt_ids_for,
    prompts_for,
)


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------------------------------------------------------------------------
# Subject registry contract.
# ---------------------------------------------------------------------------

def test_five_subjects_registered_in_locked_order():
    """The subject picker shows these five in this exact order."""
    assert list(SUBJECTS.keys()) == [
        SUBJECT_CO_PARENTING,
        SUBJECT_COMMUNICATION,
        SUBJECT_MEDICAL,
        SUBJECT_EDUCATIONAL,
        SUBJECT_SAFETY,
    ]


@pytest.mark.parametrize("subject", [
    SUBJECT_CO_PARENTING, SUBJECT_COMMUNICATION, SUBJECT_MEDICAL,
    SUBJECT_EDUCATIONAL, SUBJECT_SAFETY,
])
def test_every_subject_has_six_prompts_with_matching_ids(subject):
    """Every subject reuses the same 6 prompt IDs so the analysis
    engine stays subject-agnostic."""
    ids = prompt_ids_for(subject)
    assert ids == [
        "primary_need", "whats_working", "concerns",
        "desired_improvements", "options", "other_parent_concerns",
    ]


def test_only_safety_is_flagged_sensitive():
    assert is_sensitive_subject(SUBJECT_SAFETY) is True
    for subj in (SUBJECT_CO_PARENTING, SUBJECT_COMMUNICATION,
                 SUBJECT_MEDICAL, SUBJECT_EDUCATIONAL):
        assert is_sensitive_subject(subj) is False, subj


def test_safety_subject_carries_dual_consent_blurb():
    """The Safety blurb must EXPLICITLY name the dual-consent
    guardrail so parents cannot miss it when the subject card is
    rendered — the frontend keys the disclosure banner on the
    `sensitive` flag, but the blurb is the last line of defence."""
    blurb = SUBJECTS[SUBJECT_SAFETY]["blurb"].lower()
    assert "safety" in blurb
    assert "opt in" in blurb or "dual" in blurb or "consent" in blurb


# ---------------------------------------------------------------------------
# API — subject listing + safety-sensitive compare.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from server import app as _app
    _app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe_iter192_rows():
    import asyncio
    async def _run():
        c = AsyncIOMotorClient(MONGO_URL)
        try:
            db = c[DB_NAME]
            emails = ["iter192_a@test.com", "iter192_b@test.com"]
            users = await db.users.find(
                {"email": {"$in": emails}}, {"user_id": 1}
            ).to_list(None)
            uids = [u["user_id"] for u in users]
            if uids:
                await db.alignment_reflections.delete_many({"user_id": {"$in": uids}})
        finally:
            c.close()
    try:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        loop.run_until_complete(_run())
        loop.close()
    except Exception:  # noqa: BLE001
        pass
    yield


def _register(client, email, name):
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass192!", "name": name},
    )
    if r.status_code == 400:
        r = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass192!"},
        )
    assert r.status_code == 200, r.text
    token = r.json().get("access_token") or r.json().get("token")
    return {"Authorization": f"Bearer {token}"}


def test_subjects_listing_endpoint_exposes_all_five(client):
    r = client.get("/api/alignment-reflection/subjects")
    assert r.status_code == 200
    subjects = r.json()["subjects"]
    ids = [s["id"] for s in subjects]
    assert ids == [
        "co_parenting", "communication", "medical", "educational", "safety",
    ]
    # Safety must expose the sensitive flag so the frontend can render
    # the "Dual-consent only" badge.
    safety = next(s for s in subjects if s["id"] == "safety")
    assert safety["sensitive"] is True
    # And no other subject leaks a sensitive flag.
    for s in subjects:
        if s["id"] != "safety":
            assert s["sensitive"] is False


def test_schema_endpoint_works_for_every_new_subject(client):
    for subject in ("communication", "medical", "educational", "safety"):
        r = client.get(f"/api/alignment-reflection/schema/{subject}")
        assert r.status_code == 200, subject
        body = r.json()
        assert body["id"] == subject
        assert len(body["prompts"]) == 6


def test_safety_compare_requires_explicit_dual_consent(client):
    """The primary safety guardrail: hitting `/compare` on the safety
    subject WITHOUT `safety_dual_consent_acknowledged: true` must
    return 428 — never leak safety reflections implicitly."""
    a_hdrs = _register(client, "iter192_a@test.com", "Parent A Iter192")
    b_hdrs = _register(client, "iter192_b@test.com", "Parent B Iter192")

    # Both parents save safety answers.
    for hdrs in (a_hdrs, b_hdrs):
        r = client.put(
            "/api/alignment-reflection/safety",
            headers=hdrs,
            json={"answers": {"primary_need": "Feeling safe expressing feelings."}},
        )
        assert r.status_code == 200

    # Without dual-consent flag — MUST 428.
    r = client.post(
        "/api/alignment-reflection/safety/compare",
        headers=a_hdrs,
        json={"coparent_email": "iter192_b@test.com"},
    )
    assert r.status_code == 428, r.text
    assert "dual" in r.json()["detail"].lower() or "consent" in r.json()["detail"].lower()

    # With dual-consent flag — succeeds.
    r = client.post(
        "/api/alignment-reflection/safety/compare",
        headers=a_hdrs,
        json={
            "coparent_email": "iter192_b@test.com",
            "safety_dual_consent_acknowledged": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"


def test_non_sensitive_compare_does_not_require_the_flag(client):
    """Communication / Medical / Educational / Co-parenting must NOT
    require the safety dual-consent flag — it's a safety-only ceremony."""
    a_hdrs = _register(client, "iter192_a@test.com", "Parent A Iter192")
    b_hdrs = _register(client, "iter192_b@test.com", "Parent B Iter192")

    for hdrs in (a_hdrs, b_hdrs):
        client.put(
            "/api/alignment-reflection/communication",
            headers=hdrs,
            json={"answers": {"primary_need": "Predictable weekly updates."}},
        )

    r = client.post(
        "/api/alignment-reflection/communication/compare",
        headers=a_hdrs,
        json={"coparent_email": "iter192_b@test.com"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# Joint-agreement safety guard — Safety reflections must NEVER
# auto-merge into `build_joint_agreement`.
# ---------------------------------------------------------------------------

def test_joint_agreement_load_reflection_answers_refuses_safety():
    """Direct unit test of the safety guard inside `_load_reflection_answers`."""
    import asyncio
    from joint_agreement_routes import _load_reflection_answers

    class _FakeColl:
        async def find_one(self, *a, **kw):  # pragma: no cover — never called for safety
            raise AssertionError("Safety reflections must never hit the DB via this loader")

    class _FakeDB:
        def __getitem__(self, name):
            return _FakeColl()

    async def _run():
        # Non-sensitive subject would call find_one (and raise). Instead,
        # verify the safety subject short-circuits BEFORE the DB call.
        got = await _load_reflection_answers(_FakeDB(), "user_x", subject="safety")
        return got

    result = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_run())
    assert result == {}


# ---------------------------------------------------------------------------
# Sample PDF contract.
# ---------------------------------------------------------------------------

def test_sample_pdf_module_produces_a_valid_pdf():
    from coparenting_alignment_sample import build_sample_pdf_bytes
    pdf = build_sample_pdf_bytes()
    assert pdf[:5] == b"%PDF-"
    # Reasonable file size — a sample under 100kB probably didn't
    # render the reflection section, over 3MB is a regression.
    assert 100_000 < len(pdf) < 3_000_000


def test_sample_pdf_contains_full_ten_section_flow():
    from coparenting_alignment_sample import build_sample_pdf_bytes
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    pdf = build_sample_pdf_bytes()
    r = PdfReader(io.BytesIO(pdf))
    text = "\n".join((p.extract_text() or "") for p in r.pages)
    for heading in [
        "1. Purpose of This Report",
        "2. What Both Parents Agree About",
        "5. Alignment Map",
        "10. Possible Next Steps",
    ]:
        assert heading in text, f"Missing section heading in sample PDF: {heading}"
    # Reflection-driven section must land on the sample.
    assert "Shared themes from your reflection prompts" in text
    assert "Both parents mentioned" in text


def test_sample_pdf_route_serves_pdf_bytes(client):
    r = client.get("/api/insights/samples/co-parenting-alignment-report.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    # Cached — mediators refreshing the sample repeatedly should not
    # burn CPU regenerating byte-identical PDFs.
    assert "max-age" in r.headers.get("cache-control", "")


def test_sample_pdf_route_is_public_no_auth_required(client):
    """No Authorization header — mediators previewing the sample from
    a marketing email must not need to sign in first."""
    r = client.get("/api/insights/samples/co-parenting-alignment-report.pdf")
    assert r.status_code == 200
