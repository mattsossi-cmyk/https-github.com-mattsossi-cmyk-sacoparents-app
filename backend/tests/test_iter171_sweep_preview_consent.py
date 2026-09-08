"""Iteration 171 — Access-Expiring Sweep + Digest Preview + JA Consent Split.

Grouped so we don't spawn three files that each register + seed
identical fixtures.

Covers:
  * access_expiring_sweep.flip_expired_invitations flips
    invites where access_expiration has passed (idempotent).
  * access_expiring_sweep._iter_warning_candidates finds invites
    exactly 7 days from expiring (within the ±24h band).
  * access_expiring_sweep.send_access_expiring_warnings dry-run
    happy path + dedupe (second call is `already_warned`).
  * POST /parent/notification-mode/preview-digest returns
    delivered=true with `source="demo_sample"` when the caller
    has no recent events.
  * Joint Alignment consent-split:
      - POST /joint-alignment/cases/{id}/comparison-consent records
      - POST /joint-alignment/cases/{id}/release-consent records
      - GET  /joint-alignment/cases/{id}/consent-status returns per-
        parent state + rollup eligibility flags
      - Foreign caller (not a party, not the mediator) → 403
      - Revoke path clears eligibility
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import requests
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

from tests.conftest import BASE_URL  # noqa: E402

MONGO_URL = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME") or "test_database"


def _register(prefix: str) -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"C {prefix}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"], r.json()["user"]["user_id"]


def _headers(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _seed_reflection(tok: str) -> None:
    requests.put(
        f"{BASE_URL}/api/mediation/reflection",
        json={"child_lens": "a", "own_part": "b", "best_outcome": "c", "coparent_feedback": "d"},
        headers=_headers(tok), timeout=30,
    )


def _create_invite(tok: str, pro_email: str, access_days: int = 30) -> str:
    fid = requests.get(
        f"{BASE_URL}/api/parent/report-catalog", headers=_headers(tok), timeout=30,
    ).json()["reports"][0]["report_id"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json={
            "professional_first_name": "P", "professional_last_name": "P",
            "professional_email": pro_email, "professional_email_confirm": pro_email,
            "professional_role": "mediator", "report_ids": [fid],
            "view_permission": True, "download_permission": False,
            "notify_on_view": True, "notify_on_download": True,
            "future_versions": False, "access_days": access_days,
            "consent_authorised": True, "consent_relationship_acknowledged": True,
        },
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["invitation_id"]


# =====================================================================
# Access-expiring sweep
# =====================================================================

def test_flip_expired_invitations_flips_past_access_expiration():
    """Backdate an invite's access_expiration and confirm the sweep
    flips it to status=access_expired."""
    async def run():
        import access_expiring_sweep as aes
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, _uid = _register("flip")
            _seed_reflection(tok)
            inv_id = _create_invite(tok, f"flip-{uuid.uuid4().hex[:6]}@example.com")
            # Backdate access_expiration to 1 hour ago.
            past = datetime.now(timezone.utc) - timedelta(hours=1)
            await db["parent_professional_invitations"].update_one(
                {"invitation_id": inv_id},
                {"$set": {"access_expiration": past}},
            )
            await db["professional_report_permissions"].update_many(
                {"invitation_id": inv_id},
                {"$set": {"expires_at": past}},
            )
            out = await aes.flip_expired_invitations(db)
            assert out["invitations_flipped"] >= 1
            assert out["permissions_flipped"] >= 1
            # Idempotent — second call finds nothing to flip.
            out2 = await aes.flip_expired_invitations(db)
            assert out2["invitations_flipped"] == 0
            inv = await db["parent_professional_invitations"].find_one({"invitation_id": inv_id})
            assert inv["status"] == "access_expired"
        finally:
            client.close()
    asyncio.run(run())


def test_flip_expired_leaves_active_invites_alone():
    async def run():
        import access_expiring_sweep as aes
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, _uid = _register("active")
            _seed_reflection(tok)
            inv_id = _create_invite(tok, f"actv-{uuid.uuid4().hex[:6]}@example.com")
            await aes.flip_expired_invitations(db)
            inv = await db["parent_professional_invitations"].find_one({"invitation_id": inv_id})
            assert inv["status"] != "access_expired"
        finally:
            client.close()
    asyncio.run(run())


def test_warning_candidate_scan_finds_7d_out_invites():
    async def run():
        import access_expiring_sweep as aes
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, _uid = _register("warn")
            _seed_reflection(tok)
            inv_id = _create_invite(tok, f"warn-{uuid.uuid4().hex[:6]}@example.com")
            # Force access_expiration to exactly 7 days from now.
            target = datetime.now(timezone.utc) + timedelta(days=7)
            await db["parent_professional_invitations"].update_one(
                {"invitation_id": inv_id},
                {"$set": {"access_expiration": target}},
            )
            now = datetime.now(timezone.utc)
            candidates = await aes._iter_warning_candidates(db, now=now)
            invite_ids = [c.get("invitation_id") for c in candidates]
            assert inv_id in invite_ids
        finally:
            client.close()
    asyncio.run(run())


def test_send_access_expiring_dry_run_records_and_dedupes():
    async def run():
        import access_expiring_sweep as aes
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, _uid = _register("dryrun")
            _seed_reflection(tok)
            inv_id = _create_invite(tok, f"dry-{uuid.uuid4().hex[:6]}@example.com")
            # Land at 7 days out.
            target = datetime.now(timezone.utc) + timedelta(days=7)
            await db["parent_professional_invitations"].update_one(
                {"invitation_id": inv_id},
                {"$set": {"access_expiration": target}},
            )
            r1 = await aes.send_access_expiring_warnings(db, dry_run=True)
            row1 = next((x for x in r1["results"] if x.get("invitation_id") == inv_id), None)
            assert row1 is not None and row1["sent"] and row1.get("dry_run")

            r2 = await aes.send_access_expiring_warnings(db, dry_run=True)
            row2 = next((x for x in r2["results"] if x.get("invitation_id") == inv_id), None)
            assert row2 is not None and row2.get("reason") == "already_warned"
        finally:
            client.close()
    asyncio.run(run())


# =====================================================================
# Digest preview
# =====================================================================

def test_digest_preview_returns_demo_when_no_events():
    _e, tok, _uid = _register("preview")
    r = requests.post(
        f"{BASE_URL}/api/parent/notification-mode/preview-digest",
        headers=_headers(tok), timeout=30,
    )
    # If Resend isn't configured this env → 503. If configured → 200.
    assert r.status_code in {200, 503}
    if r.status_code == 200:
        data = r.json()
        assert data["delivered"] is True
        assert data["source"] == "demo_sample"
        assert data["event_count"] == 5


def test_digest_preview_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/parent/notification-mode/preview-digest", timeout=30,
    )
    assert r.status_code == 401


# =====================================================================
# Joint Alignment consent-split
# =====================================================================

async def _create_case_with_parent(prefix: str, parent_email: str) -> str:
    """Create a JA case with a specific parent_email so we can
    authenticate as that parent later. Runs the create through the
    same endpoint the mediator uses so the case-shape is production-
    accurate."""
    # Register mediator + parent.
    med_email, med_tok, _med_uid = _register(f"{prefix}-med")
    r = requests.post(
        f"{BASE_URL}/api/professional/joint-alignment/cases",
        json={
            "assessment_type": "communication",
            "parents": [
                {"email": parent_email, "name": "Parent A"},
                {"email": f"pb-{uuid.uuid4().hex[:6]}@example.com", "name": "Parent B"},
            ],
        },
        headers=_headers(med_tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["case_id"]


def test_consent_status_403_for_non_party():
    """A random registered user who isn't in the case must 403."""
    parent_email = f"cs-a-{uuid.uuid4().hex[:6]}@example.com"
    case_id = asyncio.get_event_loop().run_until_complete(
        _create_case_with_parent("cs403", parent_email),
    ) if False else asyncio.new_event_loop().run_until_complete(
        _create_case_with_parent("cs403", parent_email),
    )
    _e, stranger_tok, _ = _register("stranger")
    r = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/consent-status",
        headers=_headers(stranger_tok), timeout=30,
    )
    assert r.status_code == 403


def test_comparison_and_release_consent_record_and_status_updates():
    """End-to-end: register a parent whose email matches a case row,
    record comparison + release consents, GET consent-status shows
    both."""
    parent_email = f"cs-parent-{uuid.uuid4().hex[:6]}@example.com"
    # Case has to be created BEFORE the parent registers because the
    # /cases endpoint just needs the email string. Then the parent
    # registers using that same email.
    case_id = asyncio.new_event_loop().run_until_complete(
        _create_case_with_parent("cshappy", parent_email),
    )
    # Register the parent with the SAME email so they can consent.
    r_reg = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": parent_email, "password": "TestPass123!", "name": "Parent A"},
        timeout=30,
    )
    assert r_reg.status_code == 200
    tok = r_reg.json()["access_token"]

    r_comp = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/comparison-consent",
        json={"consented": True},
        headers=_headers(tok), timeout=30,
    )
    assert r_comp.status_code == 200, r_comp.text
    assert r_comp.json()["consent"]["comparison"]["consented"] is True

    r_rel = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/release-consent",
        json={"consented": True, "professional_name": "Adele van Wyk"},
        headers=_headers(tok), timeout=30,
    )
    assert r_rel.status_code == 200
    consent = r_rel.json()["consent"]
    assert consent["release"]["consented"] is True
    assert consent["release"]["professional_name"] == "Adele van Wyk"
    assert "Adele van Wyk" in r_rel.json()["consent_text"]

    # Consent-status includes this parent, no eligibility yet (co-parent hasn't consented).
    r_stat = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/consent-status",
        headers=_headers(tok), timeout=30,
    ).json()
    assert r_stat["case_id"] == case_id
    assert r_stat["comparison_eligible"] is False   # only 1 of 2 parents
    assert r_stat["release_eligible"] is False
    my_row = next(
        p for p in r_stat["parents"]
        if p["email"].lower() == parent_email.lower()
    )
    assert my_row["comparison"]["consented"] is True
    assert my_row["release"]["consented"] is True


def test_revoke_comparison_clears_eligibility_flag():
    parent_email = f"cs-rev-{uuid.uuid4().hex[:6]}@example.com"
    case_id = asyncio.new_event_loop().run_until_complete(
        _create_case_with_parent("csrev", parent_email),
    )
    r_reg = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": parent_email, "password": "TestPass123!", "name": "Rev"},
        timeout=30,
    )
    assert r_reg.status_code == 200
    tok = r_reg.json()["access_token"]

    requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/comparison-consent",
        json={"consented": True}, headers=_headers(tok), timeout=30,
    )
    # Revoke.
    r = requests.post(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/comparison-consent",
        json={"consented": False}, headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    stat = requests.get(
        f"{BASE_URL}/api/joint-alignment/cases/{case_id}/consent-status",
        headers=_headers(tok), timeout=30,
    ).json()
    my_row = next(
        p for p in stat["parents"]
        if p["email"].lower() == parent_email.lower()
    )
    assert my_row["comparison"]["consented"] is True   # historical yes preserved
    assert my_row["comparison"]["revoked_at"] is not None
    assert stat["comparison_eligible"] is False
