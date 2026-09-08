"""Iteration 173 — Joint Alignment on-screen preview.

Covers `GET /api/joint-alignment/cases/{case_id}/preview`:
  * 401 without auth
  * 404 for unknown case
  * 403 for a stranger (not a party)
  * 403 when either parent hasn't recorded comparison_consent
  * 409 when either parent hasn't completed assessment
  * 200 happy path with agreement-flag topics + summary
  * Content minimisation — response NEVER exposes raw payload
    keys like `foundation_statement.child_lens`
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


def _seed_reflection(tok: str) -> None:
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={
            "child_lens": "Through my child's eyes I want peace.",
            "own_part": "I need to reply on time.",
            "best_outcome": "A working schedule.",
            "coparent_feedback": "We can be cordial.",
        },
        headers=_headers(tok), timeout=30,
    )


async def _seed_case_and_parents(
    prefix: str, seeded_data: bool = False, same_data: bool = True,
) -> dict:
    """Register a mediator + two parents, create a case, set both
    parents' user_id + assessment_completed_at directly on the doc.
    Returns {case_id, parent_a_tok, parent_b_tok, parent_a_email,
    parent_b_email}.
    """
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

    _a_email, a_tok, a_uid = _register(f"{prefix}-a", email=a_email)
    _b_email, b_tok, b_uid = _register(f"{prefix}-b", email=b_email)

    if seeded_data:
        _seed_reflection(a_tok)
        if same_data:
            _seed_reflection(b_tok)
        else:
            requests.put(
                f"{BASE_URL}/api/mediation/reflection",
                json={
                    "child_lens": "A completely different perspective.",
                    "own_part": "Different self-reflection here.",
                    "best_outcome": "Different desired outcome.",
                    "coparent_feedback": "Different assessment.",
                },
                headers=_headers(b_tok), timeout=30,
            )

    # Directly set the two parents' user_id + completed timestamps
    # so we don't have to replay a full assessment completion. The
    # actual completion endpoints are covered elsewhere.
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)
    await db["joint_alignment_cases"].update_one(
        {"case_id": case_id, "parents.email": a_email},
        {"$set": {
            "parents.$.user_id": a_uid,
            "parents.$.assessment_completed_at": now,
        }},
    )
    await db["joint_alignment_cases"].update_one(
        {"case_id": case_id, "parents.email": b_email},
        {"$set": {
            "parents.$.user_id": b_uid,
            "parents.$.assessment_completed_at": now,
        }},
    )
    client.close()

    return {
        "case_id": case_id,
        "parent_a_email": a_email, "parent_a_tok": a_tok,
        "parent_b_email": b_email, "parent_b_tok": b_tok,
    }


# ---------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------

def test_preview_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/SA-000001/preview",
        timeout=30,
    )
    assert r.status_code == 401


def test_preview_404_for_unknown_case():
    _e, tok, _uid = _register("prev-404")
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/SA-999999/preview",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 404


def test_preview_403_for_stranger():
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-str", seeded_data=False),
    )
    _e, stranger_tok, _ = _register("stranger")
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(stranger_tok), timeout=30,
    )
    assert r.status_code == 403


def test_preview_403_when_no_comparison_consent():
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-noconsent", seeded_data=True, same_data=True),
    )
    # Neither parent has recorded comparison_consent yet.
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 403
    assert "comparison consent" in r.json()["detail"].lower()


def test_preview_403_when_only_one_parent_consents():
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-halfconsent", seeded_data=True, same_data=True),
    )
    # Only Parent A records comparison consent.
    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/comparison-consent",
        json={"consented": True},
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 403


def test_preview_409_when_completion_missing():
    """A case with both parents' compare-consent but where one
    parent's `assessment_completed_at` was cleared should 409."""
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-nocomp", seeded_data=True, same_data=True),
    )
    # Both compare-consent.
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        requests.post(
            f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}"
            "/comparison-consent",
            json={"consented": True},
            headers=_headers(tok), timeout=30,
        )
    # Clear one parent's assessment_completed_at to simulate not done.
    async def _clear():
        client = AsyncIOMotorClient(MONGO_URL)
        await client[DB_NAME]["joint_alignment_cases"].update_one(
            {"case_id": ctx["case_id"], "parents.email": ctx["parent_b_email"]},
            {"$set": {"parents.$.assessment_completed_at": None}},
        )
        client.close()
    asyncio.new_event_loop().run_until_complete(_clear())
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------

def test_preview_happy_path_agree_when_data_identical():
    """Both parents seeded with SAME reflection → foundation_statement
    topic should read 'agree'."""
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-agree", seeded_data=True, same_data=True),
    )
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        requests.post(
            f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}"
            "/comparison-consent",
            json={"consented": True},
            headers=_headers(tok), timeout=30,
        )
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"] == ctx["case_id"]
    assert body["assessment_type"] == "co-parenting"
    assert "preview_notice" in body
    assert "summary" in body
    foundation = next(
        (t for t in body["topics"] if t["topic_key"] == "foundation_statement"),
        None,
    )
    assert foundation is not None
    assert foundation["alignment"] == "agree"
    assert foundation["parent_a_completed"] and foundation["parent_b_completed"]


def test_preview_happy_path_differ_when_data_differs():
    """Both parents seeded with DIFFERENT reflection → foundation_statement
    reads 'differ'."""
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-differ", seeded_data=True, same_data=False),
    )
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        requests.post(
            f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}"
            "/comparison-consent",
            json={"consented": True},
            headers=_headers(tok), timeout=30,
        )
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    foundation = next(
        (t for t in body["topics"] if t["topic_key"] == "foundation_statement"),
        None,
    )
    assert foundation is not None
    assert foundation["alignment"] == "differ"


def test_preview_response_never_leaks_raw_content():
    """Guardrail: response body must not include any of the raw
    reflection strings — only agreement flags."""
    ctx = asyncio.new_event_loop().run_until_complete(
        _seed_case_and_parents("prev-min", seeded_data=True, same_data=True),
    )
    for tok in (ctx["parent_a_tok"], ctx["parent_b_tok"]):
        requests.post(
            f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}"
            "/comparison-consent",
            json={"consented": True},
            headers=_headers(tok), timeout=30,
        )
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{ctx['case_id']}/preview",
        headers=_headers(ctx["parent_a_tok"]), timeout=30,
    )
    body_text = r.text
    # The reflection text used in seeding.
    assert "Through my child's eyes I want peace." not in body_text
    assert "reply on time" not in body_text
