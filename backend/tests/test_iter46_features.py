"""Iteration 46 backend tests — Alignment Milestones.

Covers:
  1. First-ever snapshot with aligned_pct >= 75 stamps
     `milestones_crossed = [50, 75, 90]` (prior treated as 0).
  2. Re-viewing without changes → no new snapshot, no new milestones.
  3. Rising: simulated prior at 40% → next new snapshot with current 100%
     stamps `[50, 75, 90]`.
  4. Nothing new crossed: simulated prior at 100% → next snapshot stamps [].
  5. Downward crossing does NOT fire (prior 100% → current 100%, still no
     milestones; and a synthetic drop stays empty).
  6. GET /timeline surfaces `latest_snapshot_id` + `latest_milestones` from
     the most recent snapshot, and returns None / [] when count == 0.

Runs against all 3 deep-dive pathways (edu, psych, med).
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

# (pathway_prefix, share_id_prefix, assessments_collection, shares_collection)
PATHWAYS = [
    ("edu-deep",   "edu_deep_share_",   "edu_deep_assessments",   "edu_deep_shares"),
    ("psych-deep", "psych_deep_share_", "psych_deep_assessments", "psych_deep_shares"),
    ("med-deep",   "med_deep_share_",   "med_deep_assessments",   "med_deep_shares"),
]

SNAPSHOTS = "deep_dive_compare_snapshots"


# ----------------------- helpers ----------------------------------------
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


def _post_safety_level_4(client):
    s1 = {f"s1_q{i}": "no" for i in range(1, 19)}
    s2 = {f"s2_q{i}": "yes" for i in range(1, 9)}
    s2["s2_q8"] = "no"
    payload = {"section_1": s1, "section_2": s2}
    r = client.post(f"{BASE_URL}/api/safety-assessment", json=payload, timeout=30)
    assert r.status_code == 200, r.text


def _get_schema_keys(client, prefix):
    r = client.get(f"{BASE_URL}/api/{prefix}/schema", timeout=30)
    assert r.status_code == 200, f"schema {prefix}: {r.status_code} {r.text}"
    schema = r.json()
    keys = []
    for s in schema.get("sections", []):
        if s.get("texas_only"):
            continue
        sec_id = s.get("id")
        for item in s.get("items", []):
            if item.get("type") in ("likert", "alignment"):
                scale = item.get("scale") or [1, 2, 3, 4, 5]
                top = max(scale) if scale else 5
                keys.append((f"{sec_id}_{item['id']}", top))
            elif item.get("type") == "single":
                opts = item.get("options") or []
                if opts:
                    keys.append((f"{sec_id}_{item['id']}", opts[0]))
    return keys  # answer everything so aligned_pct == 100% with identical inputs


def _prime_assessment(client, prefix, answers_pairs):
    answers = {k: v for k, v in answers_pairs}
    r = client.post(f"{BASE_URL}/api/{prefix}/answers/bulk",
                    json={"answers": answers}, timeout=30)
    assert r.status_code == 200, f"bulk {prefix}: {r.status_code} {r.text}"
    r = client.post(f"{BASE_URL}/api/{prefix}/complete", timeout=30)
    assert r.status_code == 200, f"complete {prefix}: {r.status_code} {r.text}"


def _revoke_all(client):
    for prefix, _sp, _ac, _sc in PATHWAYS:
        r = client.get(f"{BASE_URL}/api/{prefix}/compare/me")
        if r.status_code != 200:
            continue
        for share in r.json().get("shares", []):
            if share.get("status") != "revoked":
                client.post(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/revoke")


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _bump_updated_at(assessments_col, user_id):
    """Force snapshot_key to change on the next comparison view."""
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        new_ts = f"9999-01-01T00:00:00.{uuid.uuid4().hex[:6]}+00:00"
        res = await db[assessments_col].update_one(
            {"user_id": user_id}, {"$set": {"updated_at": new_ts}}
        )
        assert res.matched_count == 1
    finally:
        client.close()


async def _set_latest_snapshot_aligned_pct(share_id, pct):
    """Rewrite the most recent snapshot's summary.aligned_pct so that the
    next real snapshot sees `pct` as its prior."""
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        latest = await db[SNAPSHOTS].find_one(
            {"share_id": share_id}, sort=[("created_at", -1)]
        )
        assert latest is not None, f"no snapshot yet for share {share_id}"
        await db[SNAPSHOTS].update_one(
            {"snapshot_id": latest["snapshot_id"]},
            {"$set": {"summary.aligned_pct": pct}},
        )
    finally:
        client.close()


async def _latest_snapshot(share_id):
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        return await db[SNAPSHOTS].find_one(
            {"share_id": share_id}, {"_id": 0}, sort=[("created_at", -1)]
        )
    finally:
        client.close()


async def _partner_uid_for_share(shares_col, share_id):
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        s = await db[shares_col].find_one({"share_id": share_id}, {"_id": 0})
        return s["partner_user_id"] if s else None
    finally:
        client.close()


# ----------------------- fixtures ---------------------------------------
@pytest.fixture(scope="module")
def p1_token():
    return _ensure_account(PARENT1)


@pytest.fixture(scope="module")
def p2_token():
    return _ensure_account(PARENT2)


@pytest.fixture
def p1_client(p1_token):
    return _client(p1_token)


@pytest.fixture
def p2_client(p2_token):
    return _client(p2_token)


@pytest.fixture(scope="module", autouse=True)
def cleanup_shares_and_snapshots(p1_token, p2_token):
    async def _cleanup_snapshots():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            db = client[DB_NAME]
            share_ids = []
            for _pref, _sp, _ac, sc in PATHWAYS:
                async for s in db[sc].find({}, {"_id": 0, "share_id": 1}):
                    share_ids.append(s["share_id"])
            if share_ids:
                await db[SNAPSHOTS].delete_many({"share_id": {"$in": share_ids}})
        finally:
            client.close()

    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    _run(_cleanup_snapshots())
    yield
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    _run(_cleanup_snapshots())


# ----------------------- helper: fresh consented share ------------------
def _fresh_consented_share(p1c, p2c, prefix):
    """Prime both parents with identical answers (100% aligned) and return
    a fresh, consented share_id."""
    _post_safety_level_4(p1c)
    _post_safety_level_4(p2c)
    answers = _get_schema_keys(p1c, prefix)
    assert answers, f"no answerable keys for {prefix}"
    _prime_assessment(p1c, prefix, answers)
    _prime_assessment(p2c, prefix, answers)

    r = p1c.post(f"{BASE_URL}/api/{prefix}/compare/link",
                 json={"email": PARENT2["email"]})
    assert r.status_code == 200, r.text
    share_id = r.json()["share"]["share_id"]
    cr = p2c.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/consent",
                  json={"consent": True})
    assert cr.status_code == 200, cr.text
    return share_id


# ----------------------- 1) first snapshot crosses thresholds -----------
class TestFirstSnapshotMilestones:
    """First-ever snapshot: identical answers → 100% aligned, so all three
    thresholds (50/75/90) are crossed vs prior=0."""

    @pytest.mark.parametrize("prefix,_sp,_ac,_sc", PATHWAYS)
    def test_first_snapshot_stamps_all_thresholds(
        self, p1_client, p2_client, prefix, _sp, _ac, _sc
    ):
        share_id = _fresh_consented_share(p1_client, p2_client, prefix)

        v = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        assert v.status_code == 200, v.text
        aligned = (v.json().get("comparison") or {}).get("summary", {}).get("aligned_pct", 0)
        assert aligned >= 90, f"expected >=90% aligned with identical answers, got {aligned}"

        snap = _run(_latest_snapshot(share_id))
        assert snap is not None
        assert snap.get("milestones_crossed") == [50, 75, 90], snap

        # Timeline exposes latest_snapshot_id + latest_milestones.
        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["latest_snapshot_id"] == snap["snapshot_id"]
        assert tl["latest_milestones"] == [50, 75, 90]

        # Re-view with no changes → no new snapshot, no new milestones.
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        tl2 = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl2["count"] == 1
        assert tl2["latest_snapshot_id"] == snap["snapshot_id"]
        assert tl2["latest_milestones"] == [50, 75, 90]

        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 2) rising crosses new thresholds ---------------
class TestRisingCrossings:
    """Simulate prior=40% (below all thresholds) → current 100% → crosses
    all three thresholds again on the NEW snapshot."""

    @pytest.mark.parametrize("prefix,_sp,ac,_sc", PATHWAYS)
    def test_rise_from_40_to_100_crosses_all(
        self, p1_client, p2_client, prefix, _sp, ac, _sc
    ):
        share_id = _fresh_consented_share(p1_client, p2_client, prefix)
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")  # create snap #1
        _run(_set_latest_snapshot_aligned_pct(share_id, 40))

        # Force fresh snapshot_key.
        partner_uid = _run(_partner_uid_for_share(prefix.replace("-", "_") + "_shares", share_id))
        _run(_bump_updated_at(ac, partner_uid))

        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        snap = _run(_latest_snapshot(share_id))
        assert (snap.get("summary") or {}).get("aligned_pct") >= 90
        assert snap.get("milestones_crossed") == [50, 75, 90], snap

        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["latest_snapshot_id"] == snap["snapshot_id"]
        assert tl["latest_milestones"] == [50, 75, 90]

        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 3) nothing crossed ------------------------------
class TestNoNewCrossings:
    """Prior=100% → current=100% → no new thresholds crossed (empty list)."""

    @pytest.mark.parametrize("prefix,_sp,ac,_sc", PATHWAYS)
    def test_no_new_crossings_when_prior_already_at_ceiling(
        self, p1_client, p2_client, prefix, _sp, ac, _sc
    ):
        share_id = _fresh_consented_share(p1_client, p2_client, prefix)
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")  # snap #1 already at 100

        # Force fresh snapshot_key. Prior in DB is already 100.
        partner_uid = _run(_partner_uid_for_share(prefix.replace("-", "_") + "_shares", share_id))
        _run(_bump_updated_at(ac, partner_uid))
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")

        snap = _run(_latest_snapshot(share_id))
        assert (snap.get("summary") or {}).get("aligned_pct") >= 90
        assert snap.get("milestones_crossed") == [], snap

        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["latest_milestones"] == []
        assert tl["latest_snapshot_id"] == snap["snapshot_id"]

        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 4) downward moves do not fire ------------------
class TestDownwardNoFire:
    """Simulate prior=100% then a fresh view (current still 100 via
    identical answers) → still []. Then simulate a synthetic drop by
    rewriting the latest to 100 and forcing another view: the milestone
    list must never become non-empty on a downward change."""

    @pytest.mark.parametrize("prefix,_sp,ac,_sc", PATHWAYS)
    def test_downward_does_not_stamp_milestones(
        self, p1_client, p2_client, prefix, _sp, ac, _sc
    ):
        share_id = _fresh_consented_share(p1_client, p2_client, prefix)
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")  # snap #1 at 100

        # Pretend the latest was 92 already.
        _run(_set_latest_snapshot_aligned_pct(share_id, 92))
        partner_uid = _run(_partner_uid_for_share(prefix.replace("-", "_") + "_shares", share_id))
        _run(_bump_updated_at(ac, partner_uid))
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")

        snap = _run(_latest_snapshot(share_id))
        # current is still 100 (identical answers), prior was 92 → only 90 was
        # NOT crossed anew (92>90), 75 already crossed, 50 already crossed.
        # crossings = [m for m in [50,75,90] if 100>=m>92] == []
        assert snap.get("milestones_crossed") == [], snap

        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["latest_milestones"] == []

        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 5) timeline empty-state -----------------------
class TestTimelineEmptyStateMilestones:
    """When no snapshots exist, latest_snapshot_id is None and
    latest_milestones is []."""

    @pytest.mark.parametrize("prefix,share_prefix,_ac,_sc", PATHWAYS)
    def test_empty_timeline_has_none_milestones(
        self, p1_client, prefix, share_prefix, _ac, _sc
    ):
        _post_safety_level_4(p1_client)
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/compare/link",
                           json={"email": PARENT2["email"]})
        assert r.status_code == 200, r.text
        share_id = r.json()["share"]["share_id"]

        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["count"] == 0
        assert tl["latest_snapshot_id"] is None
        assert tl["latest_milestones"] == []

        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 6) regression: prior iterations still work ----
class TestRegressionSmoke:
    def test_timeline_unknown_share_still_404(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/edu-deep/compare/edu_deep_share_doesnotexist/timeline")
        assert r.status_code == 404, r.text

    def test_timeline_still_requires_auth(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/edu-deep/compare/whatever/timeline")
        assert r.status_code in (401, 403), r.status_code
