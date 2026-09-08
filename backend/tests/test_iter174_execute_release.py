"""Iteration 174 — Preview → Release consent execution.

Covers:
  * POST /joint-alignment/cases/{id}/release-consent enhanced
    response (release_eligible, release_professional_name)
  * POST /joint-alignment/cases/{id}/execute-release
      - 401 without auth
      - 404 unknown case
      - 403 stranger
      - 409 when release_eligible is false (only one parent, or
        mismatched professional_name)
      - 200 happy path flips case to `released` + records webhook
        payload metadata
      - Idempotent — second call returns applied=false
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Tuple

import requests
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402

MONGO_URL = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME") or "test_database"


def _headers(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _register(prefix: str, email: str = None) -> Tuple[str, str, str]:
    email = email or f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"P {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"], r.json()["user"]["user_id"]


async def _seed_case(prefix: str) -> dict:
    med_email, med_tok, _ = _register(f"{prefix}-med")
    a_email = f"pa-{prefix}-{uuid.uuid4().hex[:6]}@example.com"
    b_email = f"pb-{prefix}-{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "co-parenting",
            "parents": [
                {"email": a_email, "name": "Parent A"},
                {"email": b_email, "name": "Parent B"},
            ],
        },
        headers=_headers(med_tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    case_id = r.json()["case_id"]
    _e, a_tok, a_uid = _register(f"{prefix}-a", email=a_email)
    _e, b_tok, b_uid = _register(f"{prefix}-b", email=b_email)
    # Wire user_ids on the case so `execute-release` party-check works.
    client = AsyncIOMotorClient(MONGO_URL)
    await client[DB_NAME]["joint_alignment_cases"].update_one(
        {"case_id": case_id, "parents.email": a_email},
        {"$set": {"parents.$.user_id": a_uid}},
    )
    await client[DB_NAME]["joint_alignment_cases"].update_one(
        {"case_id": case_id, "parents.email": b_email},
        {"$set": {"parents.$.user_id": b_uid}},
    )
    client.close()
    return {
        "case_id": case_id,
        "parent_a_email": a_email, "parent_a_tok": a_tok,
        "parent_b_email": b_email, "parent_b_tok": b_tok,
    }


# ---------------------------------------------------------------------
# Release-consent response rollup
# ---------------------------------------------------------------------

def test_release_consent_response_reports_eligibility_false_after_first_parent():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("rc-first"))
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["release_eligible"] is False
    assert body["release_professional_name"] is None
    assert body["already_released"] is False


def test_release_consent_response_reports_eligibility_true_when_both_agree():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("rc-both"))
    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(ctx["parent_b_tok"]), timeout=30,
    )
    body = r.json()
    assert body["release_eligible"] is True
    assert body["release_professional_name"] == "Adele van Wyk"
    assert body["already_released"] is False


# ---------------------------------------------------------------------
# execute-release
# ---------------------------------------------------------------------

def test_execute_release_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/SA-000001/execute-release",
        timeout=30,
    )
    assert r.status_code == 401


def test_execute_release_404_unknown_case():
    _e, tok, _uid = _register("exec-404")
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/SA-999999/execute-release",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 404


def test_execute_release_403_stranger():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("exec-403"))
    _e, stranger_tok, _ = _register("exec-stranger")
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(stranger_tok), timeout=30,
    )
    assert r.status_code == 403


def test_execute_release_409_when_only_one_parent_consents():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("exec-half"))
    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 409


def test_execute_release_409_when_pros_mismatch():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("exec-mismatch"))
    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
        json={"consented": True, "professional_name": "A DIFFERENT MEDIATOR"},
        headers=_headers(ctx["parent_b_tok"]), timeout=30,
    )
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 409


def test_execute_release_happy_path_flips_case_status():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("exec-happy"))
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        requests.post(
            f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
            json={"consented": True, "professional_name": "Adele van Wyk"},
            headers=_headers(tok), timeout=30,
        )
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["applied"] is True
    assert body["released_at"]
    assert body["released_professional_name"] == "Adele van Wyk"

    # Verify DB flipped status.
    async def _check():
        client = AsyncIOMotorClient(MONGO_URL)
        doc = await client[DB_NAME]["joint_alignment_cases"].find_one(
            {"case_id": ctx["case_id"]},
        )
        client.close()
        return doc
    doc = asyncio.new_event_loop().run_until_complete(_check())
    assert doc["status"] == "released"
    assert doc["released_at"] is not None


def test_execute_release_is_idempotent():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("exec-idem"))
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        requests.post(
            f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/release-consent",
            json={"consented": True, "professional_name": "Adele van Wyk"},
            headers=_headers(tok), timeout=30,
        )
    r1 = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r1.json()["applied"] is True
    r2 = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_b_tok"]), timeout=30,
    )
    assert r2.status_code == 200
    assert r2.json()["applied"] is False
    # Timestamp is preserved from the first call (Mongo truncates
    # datetime precision to milliseconds so match on first 23 chars).
    assert r2.json()["released_at"][:23] == r1.json()["released_at"][:23]
