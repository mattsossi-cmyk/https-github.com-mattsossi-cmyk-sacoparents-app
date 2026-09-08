"""Iteration 177 — Released cases in /joint-alignment/mine.

Covers the enrichment of `_case_public_shape`:
  * `released_at` and `released_professional_name` are present
    on the /mine response (null when the case hasn't been
    released yet, ISO string after execute-release).
  * Case status flips to `released` after execute-release.
  * Live vs handed-off partition: a case with released_at is
    still returned in the list (just marked terminal); parent
    dashboard groups it client-side.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
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
    assert r.status_code == 200
    case_id = r.json()["case_id"]
    _e, a_tok, a_uid = _register(f"{prefix}-a", email=a_email)
    _e, b_tok, b_uid = _register(f"{prefix}-b", email=b_email)
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
        "case_id": case_id, "med_email": med_email,
        "parent_a_email": a_email, "parent_a_tok": a_tok,
        "parent_b_email": b_email, "parent_b_tok": b_tok,
    }


def _grant_release(case_id: str, tok: str) -> None:
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text


def _row_for(cases_list, case_id):
    for c in cases_list:
        if c["case_id"] == case_id:
            return c
    return None


# ---------------------------------------------------------------------

def test_mine_lists_released_at_null_for_new_case():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("mine-new"))
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/mine",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 200
    row = _row_for(r.json()["cases"], ctx["case_id"])
    assert row is not None
    assert "released_at" in row
    assert row["released_at"] is None
    assert row["released_professional_name"] is None
    assert row["status"] != "released"


def test_mine_flips_status_to_released_after_execute_release():
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("mine-flip"))
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        _grant_release(ctx["case_id"], tok)
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 200
    r2 = requests.get(
        f"{BASE_URL}/api/joint-alignment/mine",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    row = _row_for(r2.json()["cases"], ctx["case_id"])
    assert row is not None
    assert row["released_at"] is not None
    assert row["released_professional_name"] == "Adele van Wyk"
    assert row["status"] == "released"


def test_mine_returns_released_row_for_co_parent_too():
    """Both parents should see the terminal state — not just the
    one who tapped Execute."""
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("mine-both"))
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        _grant_release(ctx["case_id"], tok)
    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/execute-release",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/mine",
        headers=_headers(ctx["parent_b_tok"]), timeout=30,
    )
    row = _row_for(r.json()["cases"], ctx["case_id"])
    assert row is not None
    assert row["status"] == "released"
    assert row["released_at"] is not None


def test_mine_expired_status_still_wins_over_released():
    """A case that was killed via `expired` shouldn't suddenly read
    as `released` just because the doc was later force-set. The
    `_derived_status` precedence keeps expired/cancelled visible."""
    ctx = asyncio.new_event_loop().run_until_complete(_seed_case("mine-exp"))
    # Force the case to `expired` + set released_at post-hoc via
    # Mongo — simulates the (unlikely) race where both terminal
    # flags land on the same doc.
    async def _force():
        client = AsyncIOMotorClient(MONGO_URL)
        from datetime import datetime, timezone
        await client[DB_NAME]["joint_alignment_cases"].update_one(
            {"case_id": ctx["case_id"]},
            {"$set": {
                "status": "expired",
                "released_at": datetime.now(timezone.utc),
                "released_professional_name": "Adele van Wyk",
            }},
        )
        client.close()
    asyncio.new_event_loop().run_until_complete(_force())
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/mine",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    row = _row_for(r.json()["cases"], ctx["case_id"])
    assert row is not None
    assert row["status"] == "expired"
    # But the released_at field is still available on the shape so
    # the parent knows a receipt was generated.
    assert row["released_at"] is not None
