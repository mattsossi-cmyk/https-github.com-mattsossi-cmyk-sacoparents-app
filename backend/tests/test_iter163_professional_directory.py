"""Iteration 163 — sacoparentsalign.com professional directory + invite.

Covers the sibling-directory integration:
  * Public shape of `list_directory()` matches the sibling contract
    documented in INTEGRATION_TODO_sacoparentsalign.md.
  * `GET /api/professional/directory` filters by q + specialty.
  * `POST /api/professional/directory/invite` mints an invitation
    email, logs an audit row, enforces the 24-hour duplicate guard.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Tuple

import requests

sys.path.insert(0, "/app/backend")

import professional_directory as pd  # noqa: E402
from tests.conftest import BASE_URL  # noqa: E402


# ---------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------

def test_directory_mock_has_5_rows_and_required_fields():
    rows = pd._MOCK_DIRECTORY
    assert len(rows) >= 5
    required = ("id", "name", "title", "city", "specialties", "bio", "contact_email")
    for row in rows:
        for key in required:
            assert key in row, f"row {row.get('id')} missing `{key}`"
        assert row["contact_email"].endswith("@sacoparentsalign.com")


def test_list_directory_filters_by_query_and_specialty():
    async def run():
        # Query "Cape" — matches Adele in Cape Town.
        rows_cape = await pd.list_directory(query="Cape")
        assert len(rows_cape) == 1
        assert rows_cape[0]["id"] == "sacpa-001"
        # Query "attorney" — matches Kagiso's title.
        rows_atty = await pd.list_directory(query="attorney")
        assert len(rows_atty) == 1
        assert rows_atty[0]["id"] == "sacpa-003"
        # specialty=parenting coordinator — Nomsa only.
        rows_pc = await pd.list_directory(specialty="parenting coordinator")
        assert len(rows_pc) == 1
        assert rows_pc[0]["id"] == "sacpa-002"
    asyncio.run(run())


def test_get_professional_returns_none_for_unknown():
    async def run():
        assert await pd.get_professional("nope") is None
        row = await pd.get_professional("sacpa-004")
        assert row and row["name"] == "Priya Naidoo"
    asyncio.run(run())


def test_align_join_url_binds_case_when_present():
    url = pd.align_join_url_for(case_id="SA-XXXXXX", token="abc123")
    assert "case=SA-XXXXXX" in url and "token=abc123" in url
    assert url.startswith("https://sacoparentsalign.com/join?")
    url2 = pd.align_join_url_for(case_id=None, token="abc123")
    assert "case=" not in url2


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _register(prefix: str) -> Tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"Pro Dir {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------
# Live-server API tests
# ---------------------------------------------------------------------

def test_directory_endpoint_requires_auth():
    r = requests.get(f"{BASE_URL}/api/professional/directory", timeout=30)
    assert r.status_code == 401


def test_directory_endpoint_returns_full_roster():
    _email, tok = _register("dir1")
    r = requests.get(
        f"{BASE_URL}/api/professional/directory",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    rows = r.json()["professionals"]
    assert len(rows) >= 5
    assert all("contact_email" in p for p in rows)


def test_directory_endpoint_supports_q_and_specialty():
    _email, tok = _register("dir2")
    r = requests.get(
        f"{BASE_URL}/api/professional/directory?q=Cape",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    assert len(r.json()["professionals"]) == 1

    r = requests.get(
        f"{BASE_URL}/api/professional/directory?specialty=family+law",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    assert len(r.json()["professionals"]) == 1


def test_invite_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-001"}, timeout=30,
    )
    assert r.status_code == 401


def test_invite_happy_path_returns_delivered_to_and_join_url():
    _email, tok = _register("inv1")
    r = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-004", "personal_note": "Hi Priya"},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["delivered_to"] == "priya@sacoparentsalign.com"
    assert data["join_url"].startswith("https://sacoparentsalign.com/join?")
    assert data["case_id"] is None  # no case bound
    assert isinstance(data["remaining_this_hour"], int)
    assert data["invite_id"]


def test_invite_404_for_unknown_professional_id():
    _email, tok = _register("inv2")
    r = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "nope-xxx"},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 404


def test_invite_409_when_duplicate_within_24h():
    _email, tok = _register("inv3")
    first = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-005"},
        headers=_headers(tok), timeout=30,
    )
    assert first.status_code == 200
    second = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-005"},
        headers=_headers(tok), timeout=30,
    )
    assert second.status_code == 409
    assert "24 hours" in second.json()["detail"]


def test_invite_404_when_case_id_not_owned():
    _email_a, tok_a = _register("invcaseA")
    _email_b, tok_b = _register("invcaseB")
    # Register a case under user A.
    case_body = {
        "assessment_type": "communication",
        "parents": [
            {"email": f"pa-{uuid.uuid4().hex[:6]}@example.com", "name": "PA"},
            {"email": f"pb-{uuid.uuid4().hex[:6]}@example.com", "name": "PB"},
        ],
    }
    case_res = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json=case_body, headers=_headers(tok_a), timeout=30,
    ).json()
    case_id = case_res["case_id"]
    # User B tries to invite bound to user A's case → 404.
    r = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-001", "case_id": case_id},
        headers=_headers(tok_b), timeout=30,
    )
    assert r.status_code == 404


def test_invite_with_case_id_binds_join_url_to_case():
    _email, tok = _register("invcasebind")
    case_body = {
        "assessment_type": "co-parenting",
        "parents": [
            {"email": f"pcb-a-{uuid.uuid4().hex[:6]}@example.com", "name": "A"},
            {"email": f"pcb-b-{uuid.uuid4().hex[:6]}@example.com", "name": "B"},
        ],
    }
    case_res = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json=case_body, headers=_headers(tok), timeout=30,
    ).json()
    case_id = case_res["case_id"]
    inv = requests.post(
        f"{BASE_URL}/api/professional/directory/invite",
        json={"professional_id": "sacpa-003", "case_id": case_id},
        headers=_headers(tok), timeout=30,
    )
    assert inv.status_code == 200
    data = inv.json()
    assert data["case_id"] == case_id
    assert f"case={case_id}" in data["join_url"]
