"""Iteration 169 — Daily parent share-notification digest.

Covers:
  * GET  /parent/notification-mode returns resolved mode + counts
  * PUT  /parent/notification-mode with digest/immediate/auto
  * parent_share_digest.get_notification_mode auto-elevates
    at ≥3 active invitations
  * parent_share_digest.set_notification_mode round-trip incl. auto reset
  * parent_share_digest._iter_candidate_parents finds explicit +
    auto-elevated parents but excludes explicit `immediate` opt-outs
  * parent_share_digest.send_parent_share_digests dry-run happy path
    (with events) + no-events-silent path
  * per-event notification is SUPPRESSED for parents in digest mode
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

INTEGRATION_KEY = os.environ.get("INTEGRATION_SHARED_SECRET") or ""
if not INTEGRATION_KEY:
    try:
        with open("/app/backend/.env") as _f:
            for _line in _f:
                if _line.startswith("INTEGRATION_SHARED_SECRET="):
                    INTEGRATION_KEY = _line.split("=", 1)[1].strip()
                    break
    except OSError:
        pass


def _register(prefix: str) -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@test.com"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": f"D {prefix}"},
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
            "child_lens": "Kids first.",
            "own_part": "I'll reply on time.",
            "best_outcome": "Steady schedule.",
            "coparent_feedback": "We can be cordial.",
        },
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200


def _create_invite(tok: str, pro_email: str) -> str:
    fid = requests.get(
        f"{BASE_URL}/api/parent/report-catalog",
        headers=_headers(tok), timeout=30,
    ).json()["reports"][0]["report_id"]
    r = requests.post(
        f"{BASE_URL}/api/parent/professional-invitations",
        json={
            "professional_first_name": "P", "professional_last_name": "P",
            "professional_email": pro_email,
            "professional_email_confirm": pro_email,
            "professional_role": "mediator",
            "report_ids": [fid],
            "view_permission": True, "download_permission": False,
            "notify_on_view": True, "notify_on_download": True,
            "future_versions": False, "access_days": 30,
            "consent_authorised": True, "consent_relationship_acknowledged": True,
        },
        headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["invitation_id"]


# ---------------------------------------------------------------------
# Notification-mode endpoints
# ---------------------------------------------------------------------

def test_notification_mode_defaults_to_immediate_with_zero_invites():
    _e, tok, _uid = _register("nm-zero")
    r = requests.get(f"{BASE_URL}/api/parent/notification-mode", headers=_headers(tok), timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j["mode"] == "immediate"
    assert j["explicit_pref"] is None
    assert j["active_invitation_count"] == 0
    assert j["auto_threshold"] == 3


def test_notification_mode_auto_elevates_at_three_active():
    _e, tok, _uid = _register("nm-auto")
    _seed_reflection(tok)
    for i in range(3):
        _create_invite(tok, f"pro-{i}-{uuid.uuid4().hex[:6]}@example.com")
    r = requests.get(f"{BASE_URL}/api/parent/notification-mode", headers=_headers(tok), timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j["mode"] == "digest"
    assert j["active_invitation_count"] == 3
    assert j["explicit_pref"] is None


def test_notification_mode_explicit_immediate_overrides_auto():
    _e, tok, _uid = _register("nm-oi")
    _seed_reflection(tok)
    for i in range(3):
        _create_invite(tok, f"pro-{i}-{uuid.uuid4().hex[:6]}@example.com")
    r = requests.put(
        f"{BASE_URL}/api/parent/notification-mode",
        json={"mode": "immediate"}, headers=_headers(tok), timeout=30,
    )
    assert r.status_code == 200
    j = r.json()
    assert j["mode"] == "immediate" and j["requested"] == "immediate"
    # GET now reflects the override.
    g = requests.get(f"{BASE_URL}/api/parent/notification-mode", headers=_headers(tok), timeout=30).json()
    assert g["mode"] == "immediate" and g["explicit_pref"] == "immediate"


def test_notification_mode_auto_clears_explicit():
    _e, tok, _uid = _register("nm-clear")
    _seed_reflection(tok)
    # explicit override first
    requests.put(f"{BASE_URL}/api/parent/notification-mode", json={"mode": "digest"}, headers=_headers(tok), timeout=30)
    # then clear
    r = requests.put(f"{BASE_URL}/api/parent/notification-mode", json={"mode": "auto"}, headers=_headers(tok), timeout=30)
    assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/api/parent/notification-mode", headers=_headers(tok), timeout=30).json()
    # No invites → auto resolves to immediate
    assert g["mode"] == "immediate" and g["explicit_pref"] is None


def test_notification_mode_rejects_bad_value():
    _e, tok, _uid = _register("nm-bad")
    r = requests.put(f"{BASE_URL}/api/parent/notification-mode", json={"mode": "nope"}, headers=_headers(tok), timeout=30)
    assert r.status_code == 422


def test_notification_mode_requires_auth():
    r = requests.get(f"{BASE_URL}/api/parent/notification-mode", timeout=30)
    assert r.status_code == 401
    r2 = requests.put(f"{BASE_URL}/api/parent/notification-mode", json={"mode": "digest"}, timeout=30)
    assert r2.status_code == 401


# ---------------------------------------------------------------------
# Digest sweep logic (via Motor)
# ---------------------------------------------------------------------

def test_iter_candidates_includes_auto_elevated_parents():
    async def run():
        import parent_share_digest as psd
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            # Register + create 3 invites so this parent is auto-eligible.
            _e, tok, uid = _register("cand-auto")
            _seed_reflection(tok)
            for i in range(3):
                _create_invite(tok, f"cand-{i}-{uuid.uuid4().hex[:6]}@example.com")
            candidates = await psd._iter_candidate_parents(db)
            assert uid in candidates
        finally:
            client.close()
    asyncio.run(run())


def test_iter_candidates_respects_immediate_opt_out():
    async def run():
        import parent_share_digest as psd
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, uid = _register("cand-opt-out")
            _seed_reflection(tok)
            for i in range(3):
                _create_invite(tok, f"opt-{i}-{uuid.uuid4().hex[:6]}@example.com")
            # Parent explicitly picks immediate → must be excluded.
            requests.put(
                f"{BASE_URL}/api/parent/notification-mode",
                json={"mode": "immediate"}, headers=_headers(tok), timeout=30,
            )
            candidates = await psd._iter_candidate_parents(db)
            assert uid not in candidates
        finally:
            client.close()
    asyncio.run(run())


def test_send_digests_dry_run_with_no_events_records_silent():
    async def run():
        import parent_share_digest as psd
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, uid = _register("digest-silent")
            _seed_reflection(tok)
            for i in range(3):
                _create_invite(tok, f"sil-{i}-{uuid.uuid4().hex[:6]}@example.com")
            # No events → silent path.
            out = await psd.send_parent_share_digests(
                db, dry_run=True, force_window=True,
            )
            row = next((r for r in out["results"] if r.get("parent_id") == uid), None)
            assert row is not None
            assert row.get("reason") == "no_events_silent"
            # Second sweep must skip due to `already_sent`.
            out2 = await psd.send_parent_share_digests(
                db, dry_run=True, force_window=True,
            )
            row2 = next((r for r in out2["results"] if r.get("parent_id") == uid), None)
            assert row2 is None or row2.get("reason") == "already_sent"
        finally:
            client.close()
    asyncio.run(run())


def test_send_digests_dry_run_with_events_rolls_up():
    async def run():
        import parent_share_digest as psd
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            _e, tok, uid = _register("digest-events")
            _seed_reflection(tok)
            invite_ids = []
            for i in range(3):
                inv_id = _create_invite(tok, f"evt-{i}-{uuid.uuid4().hex[:6]}@example.com")
                invite_ids.append(inv_id)
            # Backdate one event to YESTERDAY (which is what the
            # digest covers). Insert directly into the audit table.
            yday_start = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
                hour=12, minute=0, second=0, microsecond=0,
            )
            first_inv = invite_ids[0]
            perm = await db["professional_report_permissions"].find_one(
                {"invitation_id": first_inv},
            )
            await db["report_access_events"].insert_one({
                "event_id": uuid.uuid4().hex[:16],
                "permission_id": perm["permission_id"],
                "invitation_id": first_inv,
                "inviting_parent_id": uid,
                "event": "view",
                "occurred_at": yday_start,
                "user_agent": "test",
            })

            # Force through the send with dry_run=True.
            # Digest_day_key is derived from "yesterday UTC" of now.
            out = await psd.send_parent_share_digests(
                db, dry_run=True, force_window=True,
            )
            row = next((r for r in out["results"] if r.get("parent_id") == uid), None)
            assert row is not None
            assert row.get("sent") is True and row.get("dry_run") is True
            summary = row.get("summary")
            assert summary["total_events"] == 1
            assert summary["total_views"] == 1
        finally:
            client.close()
    asyncio.run(run())


# ---------------------------------------------------------------------
# Suppression of per-event emails in digest mode
# ---------------------------------------------------------------------

def test_event_recording_still_works_in_digest_mode():
    """When parent is in digest mode, the event endpoint STILL
    records the event and still returns 200. Only the per-event
    email is suppressed (not testable from outside; asserted here
    that the audit trail is intact)."""
    _e, tok, uid = _register("evt-digest")
    _seed_reflection(tok)
    inv_id = _create_invite(tok, f"digestp-{uuid.uuid4().hex[:6]}@example.com")
    # Opt into digest.
    requests.put(
        f"{BASE_URL}/api/parent/notification-mode",
        json={"mode": "digest"}, headers=_headers(tok), timeout=30,
    )
    # Fetch permission_id
    detail = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/{inv_id}",
        headers=_headers(tok), timeout=30,
    ).json()
    perm_id = detail["permissions"][0]["permission_id"]
    # Record a view event via the portal endpoint.
    r = requests.post(
        f"{BASE_URL}/api/integrations/report-permissions/{perm_id}/events",
        json={"event": "view"}, timeout=30,
        headers={"X-Integration-Key": INTEGRATION_KEY, "Content-Type": "application/json"},
    )
    assert r.status_code == 200 and r.json()["recorded"] is True
    # Invite view_count went up regardless of digest suppression.
    inv = requests.get(
        f"{BASE_URL}/api/parent/professional-invitations/{inv_id}",
        headers=_headers(tok), timeout=30,
    ).json()["invitation"]
    assert inv["view_count"] == 1
