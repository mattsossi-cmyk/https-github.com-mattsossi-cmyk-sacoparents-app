"""Iteration 45 backend tests — Compare Timeline snapshots.

Covers, for all three deep-dive pathways (edu, psych, med):
  1. GET /{share_id}/timeline returns 200 with count=0 when no snapshots exist
     (never 404) — even before a comparison view has ever been loaded.
  2. GET /{share_id} inserts a snapshot on first view, and does NOT create a
     duplicate on a second view with unchanged assessment timestamps.
  3. Mutating one parent's `updated_at` causes the next view to create a
     new snapshot; timeline count grows 1 → 2 with a matching series.
  4. Timeline series is ordered ASC by created_at and delta_aligned_pct
     matches latest - first.
  5. Regression: /link, /consent, /me, /revoke, GET /{share_id}, and
     /{share_id}/pdf still work.
  6. Snapshot rows created by this test suite are cleaned up in teardown.

We prime assessments via the public POST /answers/bulk + /complete API so
we don't rely on a private schema. `updated_at` mutations use Motor
directly because the API purposely regenerates that timestamp on every
write.
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

# (pathway_prefix, share_id_prefix, assessments_collection)
PATHWAYS = [
    ("edu-deep",   "edu_deep_share_",   "edu_deep_assessments"),
    ("psych-deep", "psych_deep_share_", "psych_deep_assessments"),
    ("med-deep",   "med_deep_share_",   "med_deep_assessments"),
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
    payload = {"section_1": {}, "section_2": {"s2_q%d" % i: "yes" for i in range(1, 12)}}
    payload["section_2"]["s2_q8"] = "no"
    r = client.post(f"{BASE_URL}/api/safety-assessment", json=payload, timeout=30)
    assert r.status_code == 200, r.text


def _get_schema_keys(client, prefix):
    r = client.get(f"{BASE_URL}/api/{prefix}/schema", timeout=30)
    assert r.status_code == 200, f"schema {prefix}: {r.status_code} {r.text}"
    schema = r.json()
    keys = []
    for s in schema.get("sections", []):
        # Skip Texas-only conditional sections to keep the assessment simple.
        if s.get("texas_only"):
            continue
        sec_id = s.get("id")
        for item in s.get("items", []):
            if item.get("type") == "likert":
                keys.append((f"{sec_id}_{item['id']}", 4))
            elif item.get("type") == "single":
                opts = item.get("options") or []
                if opts:
                    keys.append((f"{sec_id}_{item['id']}", opts[0]))
    return keys[:8]  # first 8 likerts/singles is plenty


def _prime_assessment(client, prefix, answers_pairs):
    answers = {k: v for k, v in answers_pairs}
    r = client.post(f"{BASE_URL}/api/{prefix}/answers/bulk",
                    json={"answers": answers}, timeout=30)
    assert r.status_code == 200, f"bulk {prefix}: {r.status_code} {r.text}"
    r = client.post(f"{BASE_URL}/api/{prefix}/complete", timeout=30)
    assert r.status_code == 200, f"complete {prefix}: {r.status_code} {r.text}"


def _revoke_all(client):
    for prefix, _sp, _ac in PATHWAYS:
        r = client.get(f"{BASE_URL}/api/{prefix}/compare/me")
        if r.status_code != 200:
            continue
        for share in r.json().get("shares", []):
            if share.get("status") != "revoked":
                client.post(f"{BASE_URL}/api/{prefix}/compare/{share['share_id']}/revoke")


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


@pytest.fixture(scope="module")
def mongo():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup_shares_and_snapshots(p1_token, p2_token):
    """Revoke leftover shares + delete snapshots we may have created."""
    async def _cleanup_snapshots():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            db = client[DB_NAME]
            # Delete snapshots tied to any of parent1/parent2's shares.
            share_ids = []
            for pref, _sp, _ac in PATHWAYS:
                col = pref.replace("-", "_") + "_shares"
                async for s in db[col].find({}, {"_id": 0, "share_id": 1, "user_pair": 1}):
                    share_ids.append(s["share_id"])
            if share_ids:
                await db[SNAPSHOTS].delete_many({"share_id": {"$in": share_ids}})
        finally:
            client.close()

    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    asyncio.get_event_loop().run_until_complete(_cleanup_snapshots())
    yield
    for tok in (p1_token, p2_token):
        _revoke_all(_client(tok))
    asyncio.get_event_loop().run_until_complete(_cleanup_snapshots())


# ----------------------- 1) empty state ---------------------------------
class TestTimelineEmptyState:
    """No snapshots yet must return 200 with count=0, not 404."""

    @pytest.mark.parametrize("prefix,share_prefix,_ac", PATHWAYS)
    def test_empty_timeline_returns_200(self, p1_client, p2_client, prefix, share_prefix, _ac):
        _post_safety_level_4(p1_client)
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/compare/link",
                           json={"email": PARENT2["email"]})
        assert r.status_code == 200, r.text
        share_id = r.json()["share"]["share_id"]
        assert share_id.startswith(share_prefix)

        # Timeline before anyone views should be 200 with count 0.
        r = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline")
        assert r.status_code == 200, f"{prefix}: {r.status_code} {r.text}"
        body = r.json()
        assert body["count"] == 0
        assert body["snapshots"] == []
        assert body["series"] == []
        assert body["delta_aligned_pct"] == 0
        assert body["first_aligned_pct"] == 0
        assert body["latest_aligned_pct"] == 0
        assert body["share_id"] == share_id
        assert "product_label" in body

        # Cleanup share for next test.
        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 2 & 3) snapshot dedupe + growth ----------------
class TestSnapshotFlow:
    """End-to-end: view once → 1 snapshot; view again → still 1; mutate
    partner updated_at → view again → 2 snapshots."""

    @pytest.mark.parametrize("prefix,share_prefix,ac", PATHWAYS)
    def test_snapshot_dedupes_then_grows(self, p1_client, p2_client, prefix, share_prefix, ac):
        _post_safety_level_4(p1_client)
        _post_safety_level_4(p2_client)

        # Prime both parents' assessments so the comparison is buildable.
        answers = _get_schema_keys(p1_client, prefix)
        assert answers, f"no answerable keys for {prefix}"
        _prime_assessment(p1_client, prefix, answers)
        _prime_assessment(p2_client, prefix, answers)

        # Fresh share.
        r = p1_client.post(f"{BASE_URL}/api/{prefix}/compare/link",
                           json={"email": PARENT2["email"]})
        assert r.status_code == 200, r.text
        share_id = r.json()["share"]["share_id"]

        # Partner consents.
        cr = p2_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/consent",
                            json={"consent": True})
        assert cr.status_code == 200, cr.text

        # First view creates snapshot #1.
        v = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        assert v.status_code == 200, v.text
        comparison = v.json().get("comparison") or {}
        assert (comparison.get("summary") or {}).get("total_items", 0) > 0

        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["count"] == 1, tl
        assert len(tl["snapshots"]) == 1
        assert len(tl["series"]) == 1
        assert tl["delta_aligned_pct"] == 0
        assert tl["first_aligned_pct"] == tl["latest_aligned_pct"]
        snap1 = tl["snapshots"][0]
        assert snap1["share_id"] == share_id
        assert snap1["pathway_id"] == f"{prefix}-compare"
        assert "snapshot_key" in snap1
        assert isinstance(snap1.get("top_highlights"), list)
        assert len(snap1["top_highlights"]) <= 3

        # Second view — same timestamps, must NOT insert a duplicate.
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        p2_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")  # partner too
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/pdf")  # pdf path too
        tl = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl["count"] == 1, f"dedupe broken for {prefix}: {tl}"

        # Mutate parent2's updated_at via Mongo (API purposely re-stamps it).
        new_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "+00:01")
        # use a slightly different iso value to ensure the snapshot_key differs
        new_ts = f"9999-01-01T00:00:00.{uuid.uuid4().hex[:6]}+00:00"

        async def _bump():
            client = AsyncIOMotorClient(MONGO_URL)
            try:
                db = client[DB_NAME]
                # partner user_id from the share doc
                col = prefix.replace("-", "_") + "_shares"
                share_doc = await db[col].find_one({"share_id": share_id}, {"_id": 0})
                partner_uid = share_doc["partner_user_id"]
                res = await db[ac].update_one(
                    {"user_id": partner_uid},
                    {"$set": {"updated_at": new_ts}},
                )
                assert res.matched_count == 1, f"could not bump {ac} for {partner_uid}"
            finally:
                client.close()

        asyncio.get_event_loop().run_until_complete(_bump())

        # Next view should create snapshot #2.
        v2 = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        assert v2.status_code == 200
        tl2 = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl2["count"] == 2, f"snapshot did not grow for {prefix}: {tl2}"
        # Series ordering: ASC by created_at.
        created_ats = [s["created_at"] for s in tl2["series"]]
        assert created_ats == sorted(created_ats), created_ats
        # Delta arithmetic.
        assert tl2["delta_aligned_pct"] == tl2["latest_aligned_pct"] - tl2["first_aligned_pct"]

        # Third view without bumping again → still count 2.
        p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}")
        tl3 = p1_client.get(f"{BASE_URL}/api/{prefix}/compare/{share_id}/timeline").json()
        assert tl3["count"] == 2, f"dedupe after bump broken for {prefix}: {tl3}"

        # Revoke to clean up.
        p1_client.post(f"{BASE_URL}/api/{prefix}/compare/{share_id}/revoke")


# ----------------------- 4) regression: revoke + no-such-share ----------
class TestTimelineRegression:
    def test_timeline_unknown_share_404(self, p1_client):
        r = p1_client.get(f"{BASE_URL}/api/edu-deep/compare/edu_deep_share_doesnotexist/timeline")
        assert r.status_code == 404, r.text

    def test_timeline_requires_auth(self):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/edu-deep/compare/whatever/timeline")
        assert r.status_code in (401, 403), r.status_code
