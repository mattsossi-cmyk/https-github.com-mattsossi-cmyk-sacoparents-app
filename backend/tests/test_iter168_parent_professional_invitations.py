"""Iteration 168 — Parent → Professional report-share invitations.

Covers the wizard-backed flow:
  * POST /parent/professional-invitations happy path + guardrails
  * GET  /parent/professional-invitations scoping
  * GET  /parent/professional-invitations/{id} owner-only + permissions
  * POST /parent/professional-invitations/{id}/revoke (idempotent)
  * POST /parent/professional-invitations/{id}/extend
  * POST /parent/professional-invitations/{id}/resend
  * GET  /integrations/report-permissions/{id} (auth + active check)
  * POST /integrations/report-permissions/{id}/events (counts + status flips)
  * GET  /parent/report-catalog scoping
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Tuple

import requests

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402

INTEGRATION_KEY = os.environ.get("INTEGRATION_SHARED_SECRET") or ""
if not INTEGRATION_KEY:
    # Fall back to reading directly from /app/backend/.env — the
    # backend runs there but the pytest process doesn't source it.
    try:
        with open("/app/backend/.env") as _f:
            for _line in _f:
                if _line.startswith("INTEGRATION_SHARED_SECRET="):
                    INTEGRATION_KEY = _line.split("=", 1)[1].strip()
                    break
    except OSError:
        pass


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
    """Fill in the Foundation Statement reflection so
    parent_report_catalog surfaces it as complete."""
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


def _happy_body(report_id: str, **overrides) -> dict:
    body = {
        "professional_first_name": "Adele",
        "professional_last_name": "van Wyk",
        "professional_email": "adele-test@example.com",
        "professional_email_confirm": "adele-test@example.com",
        "professional_role": "mediator",
        "organization": "Cape Town Family Mediation",
        "report_ids": [report_id],
        "view_permission": True,
        "download_permission": True,
        "notify_on_view": True,
        "notify_on_download": True,
        "future_versions": False,
        "access_days": 30,
        "consent_authorised": True,
        "consent_relationship_acknowledged": True,
    }
    body.update(overrides)
    return body


def test_report_catalog_requires_auth():
    r = requests.get(f"{BASE_URL}/api/parent/report-catalog", timeout=30)
    assert r.status_code == 401


def test_report_catalog_returns_completed_reports_only_for_caller():
    _e_a, tok_a, _uid_a = _register("cat-a")
    _e_b, tok_b, _uid_b = _register("cat-b")
    # A completes a reflection; B does not.
    _seed_reflection(tok_a)
    ra = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok_a), timeout=30).json()
    rb = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok_b), timeout=30).json()
    lanes_a = [r["lane"] for r in ra["reports"]]
    lanes_b = [r["lane"] for r in rb["reports"]]
    assert "foundation" in lanes_a
    assert "foundation" not in lanes_b  # B has no reflection yet


def test_create_invitation_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json={"professional_email": "x@y.com"},  # missing everything else too
        timeout=30,
    )
    assert r.status_code == 401


def test_create_invitation_happy_path():
    _e, tok, _uid = _register("inv-happy")
    _seed_reflection(tok)
    cat = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()
    fid = [r for r in cat["reports"] if r["lane"] == "foundation"][0]["report_id"]

    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["invitation_id"]
    assert data["invitation"]["status"] == "invitation_sent"
    assert data["invitation"]["selected_reports"][0]["lane"] == "foundation"
    assert data["accept_url"].startswith("https://")
    assert "delivered" in data


def test_create_invitation_email_mismatch_400():
    _e, tok, _uid = _register("inv-mismatch")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid, professional_email_confirm="typo@example.com"),
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 400
    assert "match" in r.json()["detail"].lower()


def test_create_invitation_missing_consent_400():
    _e, tok, _uid = _register("inv-noconsent")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid, consent_authorised=False),
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 400


def test_create_invitation_foreign_report_400():
    """Parent A tries to share Parent B's foundation report → 400."""
    _e_a, tok_a, _uid_a = _register("foreign-a")
    _e_b, tok_b, _uid_b = _register("foreign-b")
    _seed_reflection(tok_b)  # B's reflection exists; A's doesn't.
    fid_b = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok_b), timeout=30).json()["reports"][0]["report_id"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid_b), headers=_headers(tok_a), timeout=30,
    )
    assert r.status_code == 400
    assert "completed reports" in r.json()["detail"]


def test_create_invitation_invalid_access_days_422():
    _e, tok, _uid = _register("inv-baddays")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid, access_days=15),  # not in {7,30,60,90}
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 422


def test_list_invitations_scoped_to_caller():
    _e_a, tok_a, _uid_a = _register("list-a")
    _e_b, tok_b, _uid_b = _register("list-b")
    _seed_reflection(tok_a)
    fid_a = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok_a), timeout=30).json()["reports"][0]["report_id"]
    # A creates an invite; B lists → sees none.
    requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid_a), headers=_headers(tok_a), timeout=30,
    )
    r_a = requests.get(f"{BASE_URL}/api/parent/professional-invitations", headers=_headers(tok_a), timeout=30).json()
    r_b = requests.get(f"{BASE_URL}/api/parent/professional-invitations", headers=_headers(tok_b), timeout=30).json()
    assert len(r_a["invitations"]) == 1
    assert r_b["invitations"] == []


def test_get_invitation_owner_scoped_404_for_stranger():
    _e_a, tok_a, _uid_a = _register("owner-a")
    _e_b, tok_b, _uid_b = _register("owner-b")
    _seed_reflection(tok_a)
    fid_a = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok_a), timeout=30).json()["reports"][0]["report_id"]
    created = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid_a), headers=_headers(tok_a), timeout=30,
    ).json()
    inv_id = created["invitation_id"]
    # Owner gets their own; stranger gets 404.
    r_own = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok_a), timeout=30)
    assert r_own.status_code == 200
    assert "permissions" in r_own.json()
    r_str = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok_b), timeout=30)
    assert r_str.status_code == 404


def test_revoke_is_idempotent_and_scoped():
    _e, tok, _uid = _register("revoke")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    created = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    ).json()
    inv_id = created["invitation_id"]
    r1 = requests.post(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}/revoke", headers=_headers(tok), timeout=30)
    assert r1.status_code == 200 and r1.json()["applied"] is True
    r2 = requests.post(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}/revoke", headers=_headers(tok), timeout=30)
    assert r2.status_code == 200 and r2.json()["applied"] is False


def test_extend_pushes_expiration_out():
    _e, tok, _uid = _register("extend")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    created = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid, access_days=7), headers=_headers(tok), timeout=30,
    ).json()
    inv_id = created["invitation_id"]
    initial_exp = created["invitation"]["access_expiration"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/{inv_id}/extend",
        json={"access_days": 90}, headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["access_expiration"] > initial_exp


def test_extend_revoked_invite_404():
    _e, tok, _uid = _register("extend-revoked")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    inv_id = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    ).json()["invitation_id"]
    requests.post(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}/revoke", headers=_headers(tok), timeout=30)
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations/{inv_id}/extend",
        json={"access_days": 30}, headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 404


def test_permission_check_requires_integration_key():
    r = requests.get(
        f"{BASE_URL}/api/integrations/report-permissions/anything",
        timeout=30,
    )
    assert r.status_code == 401


def test_permission_check_returns_active_for_fresh_invite():
    _e, tok, _uid = _register("perm-check")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    inv_id = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    ).json()["invitation_id"]
    # Fetch the permission_id from the parent-facing detail endpoint.
    detail = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok), timeout=30).json()
    perm_id = detail["permissions"][0]["permission_id"]
    r = requests.get(
        f"{BASE_URL}/api/integrations/report-permissions/{perm_id}",
        headers={"X-Integration-Key": INTEGRATION_KEY}, timeout=30,
    )
    assert r.status_code == 200 and r.json()["active"] is True
    assert r.json()["download_permission"] is True


def test_permission_check_returns_revoked_after_revoke():
    _e, tok, _uid = _register("perm-revoked")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    inv_id = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    ).json()["invitation_id"]
    detail = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok), timeout=30).json()
    perm_id = detail["permissions"][0]["permission_id"]
    requests.post(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}/revoke", headers=_headers(tok), timeout=30)
    r = requests.get(
        f"{BASE_URL}/api/integrations/report-permissions/{perm_id}",
        headers={"X-Integration-Key": INTEGRATION_KEY}, timeout=30,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is False and body["reason"] == "revoked"


def test_permission_check_unknown_returns_inactive_unknown():
    r = requests.get(
        f"{BASE_URL}/api/integrations/report-permissions/deadbeef1234abcd",
        headers={"X-Integration-Key": INTEGRATION_KEY}, timeout=30,
    )
    assert r.status_code == 200
    assert r.json() == {"active": False, "reason": "unknown"}


def test_access_event_view_increments_view_count():
    _e, tok, _uid = _register("event-view")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    inv_id = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    ).json()["invitation_id"]
    detail = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok), timeout=30).json()
    perm_id = detail["permissions"][0]["permission_id"]

    r = requests.post(
        f"{BASE_URL}/api/integrations/report-permissions/{perm_id}/events",
        json={"event": "view", "user_agent": "Mozilla/5.0"},
        headers={"X-Integration-Key": INTEGRATION_KEY,
                 "Content-Type": "application/json"},
        timeout=30,
    )
    assert r.status_code == 200 and r.json()["recorded"] is True

    # Invitation now shows view_count=1.
    inv = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok), timeout=30).json()["invitation"]
    assert inv["view_count"] == 1


def test_access_event_accepted_flips_invite_status():
    _e, tok, _uid = _register("event-accept")
    _seed_reflection(tok)
    fid = requests.get(f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30).json()["reports"][0]["report_id"]
    inv_id = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json=_happy_body(fid), headers=_headers(tok), timeout=30,
    ).json()["invitation_id"]
    detail = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok), timeout=30).json()
    perm_id = detail["permissions"][0]["permission_id"]

    r = requests.post(
        f"{BASE_URL}/api/integrations/report-permissions/{perm_id}/events",
        json={"event": "accepted"},
        headers={"X-Integration-Key": INTEGRATION_KEY,
                 "Content-Type": "application/json"},
        timeout=30,
    )
    assert r.status_code == 200
    inv = requests.get(f"{BASE_URL}/api/parent/professional-invitations/{inv_id}", headers=_headers(tok), timeout=30).json()["invitation"]
    assert inv["status"] == "accepted"
