"""Iteration 47 backend tests — Milestone History Ribbon.

Validates /api/deep-dives/compare-status extension:
  * Each pathway row exposes a sorted `milestones` list (union of
    milestones_crossed across every snapshot for the pathway's non-revoked
    shares for the current user).
  * Top-level `total_milestones_unlocked` = count of distinct milestone
    tiers unlocked across ALL pathways.
  * Snapshots on REVOKED shares are ignored.

Approach: seed shares + `deep_dive_compare_snapshots` rows directly in
Mongo (avoids the full compare-flow overhead) then hit the API.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def _read_env(key):
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


MONGO_URL = _read_env("MONGO_URL")
DB_NAME = _read_env("DB_NAME")

PARENT1 = {"email": "parent1@test.com", "password": "TestPass123!", "name": "Sam Parent"}
PARENT2 = {"email": "parent2@test.com", "password": "TestPass123!", "name": "Riley Parent"}

SNAPSHOTS = "deep_dive_compare_snapshots"
# (pathway_id, share_prefix, shares_collection)
PATHWAYS = [
    ("educational",   "edu_deep_share_",   "edu_deep_shares"),
    ("psychological", "psych_deep_share_", "psych_deep_shares"),
    ("medical",       "med_deep_share_",   "med_deep_shares"),
]


# ---------- helpers ------------------------------------------------------
def _ensure_account(creds):
    requests.post(f"{BASE_URL}/api/auth/register", json={
        **creds, "children": [], "custody_situation": "50/50 shared",
    }, timeout=30)
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": creds["email"], "password": creds["password"],
    }, timeout=30)
    assert r.status_code == 200, f"login {creds['email']}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _client(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {token}"})
    return s


def _me(token):
    r = _client(token).get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _seed_share(shares_col, share_prefix, creator_uid, partner_uid,
                       status="active"):
    share_id = f"{share_prefix}iter47_{uuid.uuid4().hex[:10]}"
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        await db[shares_col].insert_one({
            "share_id": share_id,
            "creator_user_id": creator_uid,
            "partner_user_id": partner_uid,
            "user_pair": [creator_uid, partner_uid],
            "creator_consent": True,
            "partner_consent": True,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        client.close()
    return share_id


async def _seed_snapshot(share_id, milestones):
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        await db[SNAPSHOTS].insert_one({
            "snapshot_id": f"snap_iter47_{uuid.uuid4().hex[:10]}",
            "share_id": share_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "milestones_crossed": milestones,
            "summary": {"aligned_pct": 100},
            "snapshot_key": uuid.uuid4().hex,
        })
    finally:
        client.close()


async def _cleanup_all():
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        # Delete any iter47-seeded shares + their snapshots
        for _pid, _sp, sc in PATHWAYS:
            share_ids = []
            async for s in db[sc].find(
                {"share_id": {"$regex": "iter47_"}}, {"_id": 0, "share_id": 1}
            ):
                share_ids.append(s["share_id"])
            if share_ids:
                await db[SNAPSHOTS].delete_many({"share_id": {"$in": share_ids}})
                await db[sc].delete_many({"share_id": {"$in": share_ids}})
        # Also purge any lingering iter47 snapshots
        await db[SNAPSHOTS].delete_many({"snapshot_id": {"$regex": "iter47_"}})
    finally:
        client.close()


# ---------- fixtures -----------------------------------------------------
@pytest.fixture(scope="module")
def tokens():
    t1 = _ensure_account(PARENT1)
    t2 = _ensure_account(PARENT2)
    return t1, t2


@pytest.fixture(scope="module")
def uids(tokens):
    t1, t2 = tokens
    m1 = _me(t1)
    m2 = _me(t2)
    return m1.get("user_id") or m1.get("id"), m2.get("user_id") or m2.get("id")


@pytest.fixture(autouse=True)
def _cleanup_between():
    _run(_cleanup_all())
    yield
    _run(_cleanup_all())


# ---------- test cases ---------------------------------------------------
def _compare_status(token):
    r = _client(token).get(f"{BASE_URL}/api/deep-dives/compare-status", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _pathway(data, pid):
    for p in data["pathways"]:
        if p["id"] == pid:
            return p
    raise AssertionError(f"pathway {pid} missing in {data}")


class TestCompareStatusMilestones:
    """Backend contract for iter-47 milestone ribbon."""

    def test_a_fresh_user_no_snapshots(self, tokens):
        t1, _ = tokens
        data = _compare_status(t1)
        assert data.get("total_milestones_unlocked") == 0, data
        for p in data["pathways"]:
            assert p.get("milestones") == [], p

    def test_b_single_edu_snapshot_75(self, tokens, uids):
        t1, _ = tokens
        u1, u2 = uids
        share_id = _run(_seed_share("edu_deep_shares", "edu_deep_share_", u1, u2))
        _run(_seed_snapshot(share_id, [75]))

        data = _compare_status(t1)
        assert data["total_milestones_unlocked"] == 1, data
        edu = _pathway(data, "educational")
        assert edu["milestones"] == [75], edu
        # Other pathways still empty
        assert _pathway(data, "psychological")["milestones"] == []
        assert _pathway(data, "medical")["milestones"] == []

    def test_c_additional_psych_snapshot_50_90(self, tokens, uids):
        t1, _ = tokens
        u1, u2 = uids
        edu_share = _run(_seed_share("edu_deep_shares", "edu_deep_share_", u1, u2))
        _run(_seed_snapshot(edu_share, [75]))
        psych_share = _run(_seed_share("psych_deep_shares", "psych_deep_share_", u1, u2))
        _run(_seed_snapshot(psych_share, [50, 90]))

        data = _compare_status(t1)
        assert data["total_milestones_unlocked"] == 3, data
        assert _pathway(data, "educational")["milestones"] == [75]
        assert _pathway(data, "psychological")["milestones"] == [50, 90]
        assert _pathway(data, "medical")["milestones"] == []

    def test_d_revoked_shares_ignored(self, tokens, uids):
        t1, _ = tokens
        u1, u2 = uids
        active_share = _run(
            _seed_share("edu_deep_shares", "edu_deep_share_", u1, u2, status="active")
        )
        _run(_seed_snapshot(active_share, [50]))
        revoked_share = _run(
            _seed_share("edu_deep_shares", "edu_deep_share_", u1, u2, status="revoked")
        )
        _run(_seed_snapshot(revoked_share, [90]))

        data = _compare_status(t1)
        edu = _pathway(data, "educational")
        # Only [50] should surface — the [90] on the revoked share is ignored.
        assert edu["milestones"] == [50], edu
        assert data["total_milestones_unlocked"] == 1, data

    def test_e_milestones_sorted_and_deduped(self, tokens, uids):
        t1, _ = tokens
        u1, u2 = uids
        share = _run(_seed_share("med_deep_shares", "med_deep_share_", u1, u2))
        # Two snapshots on same share, overlapping tiers, out of order.
        _run(_seed_snapshot(share, [90, 50]))
        _run(_seed_snapshot(share, [75, 50]))

        data = _compare_status(t1)
        med = _pathway(data, "medical")
        assert med["milestones"] == [50, 75, 90], med
        assert data["total_milestones_unlocked"] == 3, data

    def test_f_top_level_dedupe_across_pathways(self, tokens, uids):
        """Same tier unlocked on two pathways only counts once in the top-level."""
        t1, _ = tokens
        u1, u2 = uids
        edu = _run(_seed_share("edu_deep_shares", "edu_deep_share_", u1, u2))
        psy = _run(_seed_share("psych_deep_shares", "psych_deep_share_", u1, u2))
        _run(_seed_snapshot(edu, [75]))
        _run(_seed_snapshot(psy, [75]))

        data = _compare_status(t1)
        assert _pathway(data, "educational")["milestones"] == [75]
        assert _pathway(data, "psychological")["milestones"] == [75]
        assert data["total_milestones_unlocked"] == 1, data

    def test_g_parent2_sees_own_shares_only(self, tokens, uids):
        """Snapshots for parent1's share should also be visible to parent2 (both
        parties on user_pair), but parent2's isolated pathway should stay empty
        when only edu is populated. Confirms scoping via user_pair works."""
        t1, t2 = tokens
        u1, u2 = uids
        share = _run(_seed_share("edu_deep_shares", "edu_deep_share_", u1, u2))
        _run(_seed_snapshot(share, [50]))

        data2 = _compare_status(t2)
        edu2 = _pathway(data2, "educational")
        assert edu2["milestones"] == [50], edu2
        assert data2["total_milestones_unlocked"] == 1

    def test_h_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/deep-dives/compare-status", timeout=30)
        assert r.status_code in (401, 403), r.status_code
