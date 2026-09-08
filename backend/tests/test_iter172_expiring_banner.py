"""Iteration 172 — Access-Expiring In-App Banner.

Covers the new endpoint that powers the amber banner on
`/shared-with-professionals`:

  * GET  /parent/professional-invitations/expiring-soon
      - 401 without auth
      - Empty when the caller has no imminently-expiring invites
      - Returns invites with access_expiration inside next 7d
      - Filters out revoked invites
      - Scoped to the caller (never leaks another parent's invites)
      - Advertises `default_extend_days=14` and allowed extend days

  * POST /parent/professional-invitations/{id}/extend
      - Accepts the new 14-day slot
      - Rejects 15 (still not an allowed value)
      - Extending pushes the invite out of the "expiring soon" list
"""
from __future__ import annotations

import sys
import uuid
from typing import Tuple

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402


def _register(prefix: str) -> Tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"P {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"], r.json()["user"]["user_id"]


def _headers(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _seed_reflection(tok: str) -> None:
    r = requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={
            "child_lens": "Through my child's eyes I want peace.",
            "own_part": "I need to reply on time.",
            "best_outcome": "A working schedule.",
            "coparent_feedback": "We can be cordial.",
        },
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text


def _get_first_report_id(tok: str) -> str:
    cat = requests.get(
        f"{BASE_URL}/api/parent/report-catalog",
        headers=_headers(tok), timeout=30,
    ).json()
    return cat["reports"][0]["report_id"]


def _create_invite(tok: str, report_id: str, access_days: int = 30) -> dict:
    body = {
        "professional_first_name": "Adele",
        "professional_last_name": "van Wyk",
        "professional_email": f"pro-{uuid.uuid4().hex[:6]}@example.com",
        "professional_email_confirm": None,   # filled below
        "professional_role": "mediator",
        "organization": "Cape Town Family Mediation",
        "report_ids": [report_id],
        "view_permission": True,
        "download_permission": True,
        "notify_on_view": True,
        "notify_on_download": True,
        "future_versions": False,
        "access_days": access_days,
        "consent_authorised": True,
        "consent_relationship_acknowledged": True,
    }
    body["professional_email_confirm"] = body["professional_email"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=body, headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------
# GET /expiring-soon
# ---------------------------------------------------------------------

def test_expiring_soon_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        timeout=30,
    )
    assert r.status_code == 401


def test_expiring_soon_empty_when_no_invites():
    _e, tok, _uid = _register("exp-empty")
    r = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["invitations"] == []
    assert data["default_extend_days"] == 14
    assert 14 in data["allowed_extend_days"]
    assert data["window_days"] == 7


def test_expiring_soon_returns_7d_invites_only():
    _e, tok, _uid = _register("exp-7d")
    _seed_reflection(tok)
    fid = _get_first_report_id(tok)
    # One invite that WILL expire in the window (7d).
    soon = _create_invite(tok, fid, access_days=7)
    # One invite that will NOT (30d out).
    far = _create_invite(tok, fid, access_days=30)

    r = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    ids = [inv["invitation_id"] for inv in r.json()["invitations"]]
    assert soon["invitation_id"] in ids
    assert far["invitation_id"] not in ids
    # Countdown surfaces on each row.
    row = next(
        inv for inv in r.json()["invitations"]
        if inv["invitation_id"] == soon["invitation_id"]
    )
    assert row["days_until_expiration"] is not None
    assert 0 <= row["days_until_expiration"] <= 7


def test_expiring_soon_excludes_revoked():
    _e, tok, _uid = _register("exp-revoke")
    _seed_reflection(tok)
    fid = _get_first_report_id(tok)
    inv = _create_invite(tok, fid, access_days=7)
    rr = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/"
        f"{inv['invitation_id']}/revoke",
        headers=_headers(tok), timeout=30,
    )
    assert rr.status_code == 200

    r = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        headers=_headers(tok), timeout=30,
    )
    ids = [row["invitation_id"] for row in r.json()["invitations"]]
    assert inv["invitation_id"] not in ids


def test_expiring_soon_scoped_to_caller():
    _e_a, tok_a, _uid_a = _register("exp-scope-a")
    _e_b, tok_b, _uid_b = _register("exp-scope-b")
    _seed_reflection(tok_a)
    fid_a = _get_first_report_id(tok_a)
    a_inv = _create_invite(tok_a, fid_a, access_days=7)
    # B lists → cannot see A's invitation.
    r_b = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        headers=_headers(tok_b), timeout=30,
    )
    assert r_b.status_code == 200
    b_ids = [row["invitation_id"] for row in r_b.json()["invitations"]]
    assert a_inv["invitation_id"] not in b_ids


# ---------------------------------------------------------------------
# POST /extend — 14d support
# ---------------------------------------------------------------------

def test_extend_accepts_14_days():
    _e, tok, _uid = _register("ext-14")
    _seed_reflection(tok)
    fid = _get_first_report_id(tok)
    inv = _create_invite(tok, fid, access_days=7)

    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/"
        f"{inv['invitation_id']}/extend",
        json={"access_days": 14},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    assert r.json()["invitation_id"] == inv["invitation_id"]
    assert r.json()["access_expiration"]


def test_extend_uses_14_as_default_when_no_body():
    _e, tok, _uid = _register("ext-default")
    _seed_reflection(tok)
    fid = _get_first_report_id(tok)
    inv = _create_invite(tok, fid, access_days=7)

    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/"
        f"{inv['invitation_id']}/extend",
        json={},   # no access_days → default 14
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text


def test_extend_still_rejects_15_days():
    _e, tok, _uid = _register("ext-15")
    _seed_reflection(tok)
    fid = _get_first_report_id(tok)
    inv = _create_invite(tok, fid, access_days=7)
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/"
        f"{inv['invitation_id']}/extend",
        json={"access_days": 15},
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 422


def test_extend_moves_invite_out_of_expiring_soon_window():
    _e, tok, _uid = _register("ext-out")
    _seed_reflection(tok)
    fid = _get_first_report_id(tok)
    inv = _create_invite(tok, fid, access_days=7)
    # Pre-check: in the window.
    pre = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        headers=_headers(tok), timeout=30,
    ).json()
    assert inv["invitation_id"] in [
        r["invitation_id"] for r in pre["invitations"]
    ]
    # Extend by 60d → beyond the 7d window.
    requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/"
        f"{inv['invitation_id']}/extend",
        json={"access_days": 60},
        headers=_headers(tok), timeout=30,
    )
    # Post-check: not in the window anymore.
    post = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/expiring-soon",
        headers=_headers(tok), timeout=30,
    ).json()
    assert inv["invitation_id"] not in [
        r["invitation_id"] for r in post["invitations"]
    ]
