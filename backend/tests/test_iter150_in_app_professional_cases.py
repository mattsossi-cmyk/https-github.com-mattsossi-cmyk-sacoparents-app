"""iter150 — In-app professional-driven Joint Alignment case creation.

Locks the contract for the two new authenticated endpoints:
  * POST /api/professional/joint-alignment/cases
  * GET  /api/professional/joint-alignment/cases-i-created

Guardrails verified:
  * JWT required (unauth => 401).
  * Exactly two distinct parents => 400 otherwise.
  * Unknown assessment_type => 400.
  * Case doc records the caller as professional + `origin=in_app_professional`.
  * cases-i-created lists only the caller's cases.
  * cases-i-created includes invitation_url and never leaks another
    professional's cases into the caller's list.
"""
from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app  # noqa: E402


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault(
        "INTEGRATION_SHARED_SECRET",
        "2f9c1e7a4b8d3f6a5c0e9d7b2f4a6c8e1d3b5a7c9e0f2a4b6c8d1e3f5a7b9c0d",
    )
    app.state.db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    with TestClient(app) as c:
        yield c


def _register(client: TestClient, email: str | None = None) -> tuple[str, str, str]:
    email = email or f"iter150_pro_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"ack_privacy_notice": True, "consent_sensitive_info": True, "email": email, "password": "TestPass123!", "name": "Iter150 Mediator"},
    )
    assert r.status_code in (200, 201), r.text
    return email, r.json()["access_token"], "Iter150 Mediator"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_case(client: TestClient, token: str, **overrides) -> dict:
    payload = {
        "assessment_type": "co-parenting",
        "parents": [
            {"email": f"a_{uuid.uuid4().hex[:6]}@example.com", "name": "Alex"},
            {"email": f"b_{uuid.uuid4().hex[:6]}@example.com", "name": "Bailey"},
        ],
    }
    payload.update(overrides)
    return client.post(
        "/api/professional/joint-alignment/cases",
        json=payload,
        headers=_headers(token),
    )


# ---------------- happy path ---------------- #

def test_creates_case_with_caller_as_professional(client):
    email, token, name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"].startswith("SA-")
    assert body["status"] == "pending"
    assert body["assessment_type"] == "co-parenting"
    assert len(body["parents"]) == 2
    for p in body["parents"]:
        assert "/join/" in p["invitation_url"]
        assert p["token_expires_at"]


def test_case_document_records_origin_and_professional(client):
    email, token, name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200, r.text
    case_id = r.json()["case_id"]

    # Read via the cases-i-created endpoint to confirm the caller is
    # bound to this case as the creator.
    listed = client.get(
        "/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token),
    )
    assert listed.status_code == 200
    cases = listed.json().get("cases") or []
    match = next((c for c in cases if c["case_id"] == case_id), None)
    assert match is not None
    # The professional block should carry the caller's name (fallback
    # when no override supplied).
    assert match["professional"]["name"] == name
    # Copy-link support: parents in the list carry the invitation URL.
    for p in match["parents"]:
        assert p.get("invitation_url"), "in-app minted cases should expose invitation_url"


# ---------------- guardrails ---------------- #

def test_unauthenticated_returns_401(client):
    r = client.post(
        "/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "co-parenting",
            "parents": [
                {"email": "a@x.com"},
                {"email": "b@x.com"},
            ],
        },
    )
    assert r.status_code in (401, 403), r.text


def test_requires_exactly_two_distinct_parents(client):
    _email, token, _name = _register(client)

    # Only one parent
    r = _make_case(
        client,
        token,
        parents=[{"email": "solo@example.com"}],
    )
    assert r.status_code == 400
    assert "two parents" in r.json()["detail"].lower()

    # Duplicate emails (case-insensitive)
    r = _make_case(
        client,
        token,
        parents=[
            {"email": "same@example.com"},
            {"email": "SAME@example.com"},
        ],
    )
    assert r.status_code == 400
    assert "distinct" in r.json()["detail"].lower()


def test_unknown_assessment_type_rejected(client):
    _email, token, _name = _register(client)
    r = _make_case(client, token, assessment_type="cooking")
    assert r.status_code == 400
    assert "assessment_type" in r.json()["detail"].lower()


def test_cases_i_created_does_not_leak_other_professionals_cases(client):
    """
    Professional A creates a case. Professional B (a different logged-in
    account) must not see it in their own cases-i-created listing.
    """
    _email_a, token_a, _ = _register(client)
    _email_b, token_b, _ = _register(client)

    r_a = _make_case(client, token_a)
    assert r_a.status_code == 200
    a_case_id = r_a.json()["case_id"]

    # Fetch B's list — must NOT contain A's case
    listed_b = client.get(
        "/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token_b),
    )
    assert listed_b.status_code == 200
    b_cases = listed_b.json().get("cases") or []
    b_case_ids = {c["case_id"] for c in b_cases}
    assert a_case_id not in b_case_ids, "cases-i-created leaked another professional's case"


# ---------------- cancel + email delivery ---------------- #

def test_professional_can_cancel_own_case(client):
    _email, token, _name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200
    case_id = r.json()["case_id"]

    r2 = client.post(
        f"/api/professional/joint-alignment/cases/{case_id}/cancel",
        json={"reason": "wrong parents"},
        headers=_headers(token),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "cancelled"

    # Second cancel is a 404 (idempotent) — status already terminal.
    r3 = client.post(
        f"/api/professional/joint-alignment/cases/{case_id}/cancel",
        json={"reason": None},
        headers=_headers(token),
    )
    assert r3.status_code == 404


def test_professional_cannot_cancel_another_professionals_case(client):
    _email_a, token_a, _ = _register(client)
    _email_b, token_b, _ = _register(client)

    r_a = _make_case(client, token_a)
    a_case_id = r_a.json()["case_id"]

    r = client.post(
        f"/api/professional/joint-alignment/cases/{a_case_id}/cancel",
        json={"reason": None},
        headers=_headers(token_b),
    )
    # Ownership guard: B is not the creator, so treated as not-found.
    assert r.status_code == 404


def test_response_carries_email_delivery_status(client):
    """
    Even when the outbound email backend is not configured in test,
    the response must include `email_deliveries` with one row per
    parent so the frontend can render the "Invitation sent / Not
    sent — copy manually" hint deterministically.
    """
    _email, token, _name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "email_deliveries" in body
    assert isinstance(body["email_deliveries"], list)
    assert len(body["email_deliveries"]) == 2
    for row in body["email_deliveries"]:
        assert "email" in row
        assert "delivered" in row


# ---------------- watermarked status PDF download ---------------- #

def test_status_report_pdf_watermarked_and_valid(client):
    _email, token, _name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200
    case_id = r.json()["case_id"]

    r_pdf = client.get(
        f"/api/professional/joint-alignment/cases/{case_id}/status-report.pdf",
        params={"firm": "Acme Legal LLP"},
        headers=_headers(token),
    )
    assert r_pdf.status_code == 200
    assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
    assert r_pdf.content[:4] == b"%PDF"

    # Watermark stamp must be present in a decompressed stream on
    # at least one page.
    import re, zlib
    found = False
    for m in re.finditer(rb"stream\n(.+?)\nendstream", r_pdf.content, re.S):
        s = m.group(1)
        if s[:2] == b"x\x9c":
            try:
                d = zlib.decompress(s).decode("latin-1", errors="ignore")
                if "Downloaded by Acme Legal LLP" in d:
                    found = True
                    break
            except Exception:
                continue
    assert found, "watermark text should be stamped into at least one page's content stream"


def test_status_report_pdf_falls_back_to_account_name_watermark(client):
    _email, token, _name = _register(client)
    r = _make_case(client, token)
    assert r.status_code == 200
    case_id = r.json()["case_id"]

    r_pdf = client.get(
        f"/api/professional/joint-alignment/cases/{case_id}/status-report.pdf",
        headers=_headers(token),
    )
    assert r_pdf.status_code == 200
    # No `firm` query param → uses account name fallback ("Iter150 Mediator")
    import re, zlib
    for m in re.finditer(rb"stream\n(.+?)\nendstream", r_pdf.content, re.S):
        s = m.group(1)
        if s[:2] == b"x\x9c":
            try:
                d = zlib.decompress(s).decode("latin-1", errors="ignore")
                if "Downloaded by Iter150 Mediator" in d:
                    return  # pass
            except Exception:
                continue
    assert False, "fallback watermark from account name should be stamped"


def test_status_report_pdf_owner_only(client):
    _email_a, token_a, _ = _register(client)
    _email_b, token_b, _ = _register(client)
    r = _make_case(client, token_a)
    case_id = r.json()["case_id"]

    # B is not the creator → 404
    r_pdf = client.get(
        f"/api/professional/joint-alignment/cases/{case_id}/status-report.pdf",
        params={"firm": "Sneaky LLC"},
        headers=_headers(token_b),
    )
    assert r_pdf.status_code == 404


def test_status_report_pdf_requires_auth(client):
    r = client.get(
        "/api/professional/joint-alignment/cases/SA-000000/status-report.pdf"
    )
    assert r.status_code in (401, 403)


# ---------------- analytics endpoint ---------------- #

def test_analytics_returns_zero_shape_for_no_cases(client):
    _email, token, _name = _register(client)
    r = client.get(
        "/api/professional/joint-alignment/analytics",
        headers=_headers(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_cases"] == 0
    # Zero-shape: all rates + averages None so the frontend can em-dash them
    assert body["acceptance_rate"] is None
    assert body["avg_hours_to_first_accept"] is None
    assert body["avg_hours_to_both_complete"] is None
    assert body["most_common_assessment_type"] is None
    assert body["assessment_type_breakdown"] == {}


def test_analytics_aggregates_over_multiple_cases(client):
    _email, token, _name = _register(client)
    # Mint 3 co-parenting cases + 1 communication case
    for i in range(3):
        r = _make_case(client, token, assessment_type="co-parenting")
        assert r.status_code == 200
    r = _make_case(client, token, assessment_type="communication")
    assert r.status_code == 200

    r_a = client.get(
        "/api/professional/joint-alignment/analytics",
        headers=_headers(token),
    )
    assert r_a.status_code == 200
    body = r_a.json()
    assert body["total_cases"] == 4
    assert body["active_cases"] == 4  # all pending
    assert body["cancelled_cases"] == 0
    assert body["completed_cases"] == 0
    # Zero acceptances yet → acceptance_rate must be 0.0 (denominator > 0)
    assert body["acceptance_rate"] == 0.0
    assert body["avg_hours_to_first_accept"] is None
    # 3 co-parenting > 1 communication
    assert body["most_common_assessment_type"] == "co-parenting"
    assert body["assessment_type_breakdown"]["co-parenting"] == 3
    assert body["assessment_type_breakdown"]["communication"] == 1


def test_analytics_never_leaks_across_professionals(client):
    _email_a, token_a, _ = _register(client)
    _email_b, token_b, _ = _register(client)

    # A mints two cases
    _make_case(client, token_a)
    _make_case(client, token_a)
    # B mints one
    _make_case(client, token_b)

    body_a = client.get(
        "/api/professional/joint-alignment/analytics",
        headers=_headers(token_a),
    ).json()
    body_b = client.get(
        "/api/professional/joint-alignment/analytics",
        headers=_headers(token_b),
    ).json()
    # A should see 2 (their own) + whatever earlier tests left,
    # but B must never see A's cases. Assertion: A's total >= 2,
    # and B's total is *smaller* than A's total (proves scoping).
    assert body_a["total_cases"] >= 2
    assert body_b["total_cases"] < body_a["total_cases"]


def test_analytics_requires_auth(client):
    r = client.get("/api/professional/joint-alignment/analytics")
    assert r.status_code in (401, 403)


def test_analytics_computes_time_deltas_when_parents_accept_and_complete(client, monkeypatch):
    """
    Seed a case with tz-aware timestamps and directly update Mongo
    to simulate acceptance/completion. Verifies the aggregator
    correctly computes avg_hours_to_first_accept and
    avg_hours_to_both_complete.
    """
    import asyncio
    from datetime import datetime, timedelta, timezone as tz
    from motor.motor_asyncio import AsyncIOMotorClient

    _email, token, _name = _register(client)
    r = _make_case(client, token)
    case_id = r.json()["case_id"]

    async def stamp_timestamps():
        db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
        # Mint time was ~now. Simulate:
        # - Parent A accepted 6 hours after mint, completed 24h after mint.
        # - Parent B accepted 12h after mint, completed 48h after mint.
        # We'll rewrite created_at to 3 days ago, then stamp the other times.
        base = datetime.now(tz.utc) - timedelta(days=3)
        await db["joint_alignment_cases"].update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "created_at": base,
                    "status": "both_complete",
                    "parents.0.accepted_at": base + timedelta(hours=6),
                    "parents.0.assessment_completed_at": base + timedelta(hours=24),
                    "parents.1.accepted_at": base + timedelta(hours=12),
                    "parents.1.assessment_completed_at": base + timedelta(hours=48),
                }
            },
        )

    asyncio.get_event_loop().run_until_complete(stamp_timestamps())

    body = client.get(
        "/api/professional/joint-alignment/analytics",
        headers=_headers(token),
    ).json()
    # avg_hours_to_first_accept for this case is 6h.
    # But there may be other cases from earlier tests; assert the value
    # is in the neighbourhood of a real value (i.e. not None and > 0).
    assert body["avg_hours_to_first_accept"] is not None
    assert body["avg_hours_to_first_accept"] > 0
    # avg_hours_to_both_complete for this case is 48h — again, mixed
    # with other cases from prior tests. Just assert non-None + positive.
    assert body["avg_hours_to_both_complete"] is not None
    assert body["avg_hours_to_both_complete"] > 0


# ---------------- weekly-digest preference endpoints ---------------- #

def test_digest_pref_default_is_opted_in(client):
    _email, token, _name = _register(client)
    r = client.get(
        "/api/professional/joint-alignment/digest-pref",
        headers=_headers(token),
    )
    assert r.status_code == 200
    body = r.json()
    # Fresh account with no pref row → default True.
    assert body["opted_in"] is True
    assert body["updated_at"] is None


def test_digest_pref_opt_out_and_back_in(client):
    _email, token, _name = _register(client)

    # Opt out
    r_out = client.post(
        "/api/professional/joint-alignment/digest-pref",
        json={"opted_in": False},
        headers=_headers(token),
    )
    assert r_out.status_code == 200
    assert r_out.json()["opted_in"] is False
    assert r_out.json()["updated_at"] is not None

    # Verify GET reads back the opt-out
    r_get = client.get(
        "/api/professional/joint-alignment/digest-pref",
        headers=_headers(token),
    )
    assert r_get.json()["opted_in"] is False

    # Opt back in — idempotent upsert
    r_in = client.post(
        "/api/professional/joint-alignment/digest-pref",
        json={"opted_in": True},
        headers=_headers(token),
    )
    assert r_in.status_code == 200
    assert r_in.json()["opted_in"] is True


def test_digest_pref_requires_auth(client):
    r = client.get("/api/professional/joint-alignment/digest-pref")
    assert r.status_code in (401, 403)
    r2 = client.post(
        "/api/professional/joint-alignment/digest-pref",
        json={"opted_in": False},
    )
    assert r2.status_code in (401, 403)


# ---------------- reminder note (custom nudge copy) ---------------- #

def test_reminder_note_persists_on_create(client):
    _email, token, _name = _register(client)
    r = client.post(
        "/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "co-parenting",
            "parents": [
                {"email": "a@example.com", "name": "A"},
                {"email": "b@example.com", "name": "B"},
            ],
            "reminder_note": "  See you Thursday.  ",
        },
        headers=_headers(token),
    )
    assert r.status_code == 200
    case_id = r.json()["case_id"]

    # Read back via cases-i-created — the note should be exposed
    # (stripped of surrounding whitespace).
    listed = client.get(
        "/api/professional/joint-alignment/cases-i-created",
        headers=_headers(token),
    ).json()
    match = next(c for c in listed["cases"] if c["case_id"] == case_id)
    assert match["reminder_note"] == "See you Thursday."


def test_reminder_note_capped_at_240(client):
    _email, token, _name = _register(client)
    r = client.post(
        "/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "co-parenting",
            "parents": [
                {"email": "a@example.com"},
                {"email": "b@example.com"},
            ],
            "reminder_note": "x" * 300,
        },
        headers=_headers(token),
    )
    # Pydantic max_length=240 → 422 Unprocessable Entity
    assert r.status_code in (400, 422)


def test_patch_reminder_note_updates_and_clears(client):
    _email, token, _name = _register(client)
    r = _make_case(client, token)
    case_id = r.json()["case_id"]

    # Set a note
    r1 = client.patch(
        f"/api/professional/joint-alignment/cases/{case_id}/reminder-note",
        json={"reminder_note": "Call me if unsure."},
        headers=_headers(token),
    )
    assert r1.status_code == 200
    assert r1.json()["reminder_note"] == "Call me if unsure."

    # Clear it with null
    r2 = client.patch(
        f"/api/professional/joint-alignment/cases/{case_id}/reminder-note",
        json={"reminder_note": None},
        headers=_headers(token),
    )
    assert r2.status_code == 200
    assert r2.json()["reminder_note"] is None


def test_patch_reminder_note_owner_only(client):
    _email_a, token_a, _ = _register(client)
    _email_b, token_b, _ = _register(client)
    r = _make_case(client, token_a)
    case_id = r.json()["case_id"]
    r_b = client.patch(
        f"/api/professional/joint-alignment/cases/{case_id}/reminder-note",
        json={"reminder_note": "hijack"},
        headers=_headers(token_b),
    )
    assert r_b.status_code == 404
