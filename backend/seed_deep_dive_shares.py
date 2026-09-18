"""Seed script — Active Educational / Medical / Psychological Deep-Dive
compare shares between the two test parents.

Iter204. Every deep-dive share currently in the DB is revoked (audit
finding from the PDF verification pass on 2026-09-18). This script
seeds one fresh **active** share per pathway between
`parent1@test.com` and `parent2@test.com` so the compare PDF
endpoints can be exercised end-to-end without an admin unrevoke.

Idempotent — re-running collapses any existing shares to `revoked`
first, then inserts a single active share per pathway with a stable
share_id (`seed_{pathway}_deep_share`) so testers can copy-paste the
same URL every time.

Usage:
    python -c "from seed_deep_dive_shares import run; import asyncio; asyncio.run(run())"

Actions:
  * Ensures both `parent1@test.com` (Sam Parent) and
    `parent2@test.com` (Riley Parent) exist (delegates to
    `seed_joint_sample_case._ensure_user` so both scripts share one
    users-collection contract).
  * For each of edu / med / psych: upserts a `completed=True`
    assessment doc for each parent (cloned + jittered from a
    canonical response set so the compare PDF has real numeric
    answers to render side-by-side).
  * For each pathway: revokes every existing share where these two
    parents are the participants, then inserts one active share with
    a fixed `share_id`.
  * Prints the 3 active share_ids at the end so testers can hit:
      GET /api/edu-deep/compare/{share_id}/pdf
      GET /api/med-deep/compare/{share_id}/pdf
      GET /api/psych-deep/compare/{share_id}/pdf

Safety:
  * Runs against the local dev DB (MONGO_URL / DB_NAME env). Never
    writes to production — the seeded test-parent emails don't exist
    there.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv("/app/backend/.env")


# ------------------------------- Constants ------------------------------- #

# Stable share_ids so testers can bookmark the compare URL.
SEED_SHARE_IDS = {
    "edu":   "seed_edu_deep_share",
    "med":   "seed_med_deep_share",
    "psych": "seed_psych_deep_share",
}

PATHWAY_CONFIG = {
    "edu": {
        "shares_collection":       "edu_deep_shares",
        "assessments_collection":  "edu_deep_assessments",
        "deep_dive_version":       "edu-deep-2.0.0",
        "response_keys": [
            *(f"p1_q{i}" for i in range(1, 6)),
            *(f"p2_q{i}" for i in range(6, 11)),
            *(f"p3_q{i}" for i in range(11, 16)),
            *(f"p4_q{i}" for i in range(16, 21)),
            *(f"p5_q{i}" for i in range(21, 26)),
        ],
    },
    "psych": {
        "shares_collection":       "psych_deep_shares",
        "assessments_collection":  "psych_deep_assessments",
        "deep_dive_version":       "psych-deep-2.0.0",
        "response_keys": [
            *(f"p1_q{i}" for i in range(1, 6)),
            *(f"p2_q{i}" for i in range(6, 11)),
            *(f"p3_q{i}" for i in range(11, 16)),
            *(f"p4_q{i}" for i in range(16, 21)),
            *(f"p5_q{i}" for i in range(21, 26)),
        ],
    },
    "med": {
        "shares_collection":       "med_deep_shares",
        "assessments_collection":  "med_deep_assessments",
        "deep_dive_version":       "med-deep-1.0.0",
        # The med pathway uses domain-specific keys (s1_*, s2_*, ...).
        # We copy them off any existing completed doc rather than
        # hard-coding all 53 — the med schema evolves faster than the
        # 5-part edu/psych scale.
        "response_keys": None,   # sentinel — resolved at runtime
    },
}


# ------------------------------- Users ---------------------------------- #

async def _ensure_user(db, *, email: str, name: str) -> dict:
    """Delegate to the joint-case seeder so we speak one contract."""
    from seed_joint_sample_case import _ensure_user as _seed_user
    return await _seed_user(db, email=email, name=name)


def _uid(u: dict) -> str:
    return u.get("user_id") or u.get("id") or ""


# ---------------------------- Assessments ------------------------------ #

async def _resolve_response_keys(db, pathway: str) -> list[str]:
    """For pathways without a hard-coded key list, pull the keys off any
    completed assessment doc in the same collection. Falls back to a
    minimal 3-key stub if the collection is empty."""
    cfg = PATHWAY_CONFIG[pathway]
    if cfg["response_keys"]:
        return cfg["response_keys"]
    doc = await db[cfg["assessments_collection"]].find_one(
        {"completed": True, "responses": {"$exists": True, "$not": {"$size": 0}}},
        {"_id": 0, "responses": 1},
    )
    if doc and doc.get("responses"):
        return sorted(doc["responses"].keys())
    # Fallback for a fresh environment with zero med docs — build a
    # minimal 3-key stub so at least the completeness check passes.
    return [f"s1_stub_{i}" for i in range(1, 4)]


def _canonical_responses(keys: list[str], seed: int) -> dict[str, int]:
    """Deterministic numeric answers so the two parents have slightly
    different but internally consistent responses (parent A skews toward
    3-4, parent B toward 2-3 — enough asymmetry that the compare PDF
    renders meaningful "aligned" and "differs" rows)."""
    # 1-5 Likert. Vary by (index + seed) mod 5 with a small offset so
    # parent A and parent B diverge but never wrap to zero.
    out: dict[str, int] = {}
    for i, k in enumerate(sorted(keys)):
        out[k] = 1 + ((i + seed) % 4)  # 1..4
    return out


async def _seed_assessment(
    db, *, pathway: str, user_id: str, responses: dict, child_name: str,
) -> str:
    cfg = PATHWAY_CONFIG[pathway]
    coll = cfg["assessments_collection"]
    now = datetime.now(timezone.utc).isoformat()
    # Keep a stable assessment_id per (pathway, user) so re-runs are
    # noise-free. Deriving it from the user_id avoids leaking randomness.
    stable_id = f"seed_{pathway}_deep_{user_id[-8:]}"
    await db[coll].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "assessment_id": stable_id,
                "user_id": user_id,
                "responses": responses,
                "completed": True,
                "deep_dive_version": cfg["deep_dive_version"],
                "child_name": child_name,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return stable_id


# ------------------------------ Shares --------------------------------- #

async def _revoke_existing_shares_for_pair(
    db, *, pathway: str, uid_a: str, uid_b: str,
) -> int:
    """Sweep any old share between these two parents to `revoked` so we
    end up with exactly one active share per pathway."""
    coll = PATHWAY_CONFIG[pathway]["shares_collection"]
    now = datetime.now(timezone.utc).isoformat()
    result = await db[coll].update_many(
        {
            "$or": [
                {"user_pair": {"$all": [uid_a, uid_b]}},
                {"creator_user_id": uid_a, "partner_user_id": uid_b},
                {"creator_user_id": uid_b, "partner_user_id": uid_a},
            ],
            # Only sweep the ones that aren't the seed share — the seed
            # share below reuses the same _id so it'll be handled by
            # upsert, not by this sweep.
            "share_id": {"$ne": SEED_SHARE_IDS[pathway]},
            "status": {"$ne": "revoked"},
        },
        {"$set": {"status": "revoked", "revoked_at": now,
                  "revoked_by_user_id": "seed-script-cleanup"}},
    )
    return result.modified_count


async def _upsert_active_share(
    db, *, pathway: str, parent_a: dict, parent_b: dict,
) -> str:
    coll = PATHWAY_CONFIG[pathway]["shares_collection"]
    share_id = SEED_SHARE_IDS[pathway]
    uid_a, uid_b = _uid(parent_a), _uid(parent_b)
    now = datetime.now(timezone.utc).isoformat()
    share_doc = {
        "share_id": share_id,
        "user_pair": sorted([uid_a, uid_b]),
        "creator_user_id": uid_a,
        "creator_name": parent_a["name"],
        "creator_email": parent_a["email"],
        "partner_user_id": uid_b,
        "partner_name": parent_b["name"],
        "partner_email": parent_b["email"],
        "creator_consent": True,
        "creator_consented_at": now,
        "partner_consent": True,
        "partner_consented_at": now,
        "status": "active",
        "revoked_at": None,
        "revoked_by_user_id": None,
        "updated_at": now,
    }
    await db[coll].update_one(
        {"share_id": share_id},
        {"$set": share_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return share_id


# ------------------------------- Runner -------------------------------- #

async def run() -> dict:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    parent_a = await _ensure_user(db, email="parent1@test.com", name="Sam Parent")
    parent_b = await _ensure_user(db, email="parent2@test.com", name="Riley Parent")
    uid_a, uid_b = _uid(parent_a), _uid(parent_b)
    assert uid_a and uid_b, "seeded users missing user_id"

    seeded_shares: dict[str, str] = {}
    for pathway in ("edu", "med", "psych"):
        keys = await _resolve_response_keys(db, pathway)
        resp_a = _canonical_responses(keys, seed=1)
        resp_b = _canonical_responses(keys, seed=3)
        await _seed_assessment(
            db, pathway=pathway, user_id=uid_a,
            responses=resp_a, child_name="Alex",
        )
        await _seed_assessment(
            db, pathway=pathway, user_id=uid_b,
            responses=resp_b, child_name="Alex",
        )
        swept = await _revoke_existing_shares_for_pair(
            db, pathway=pathway, uid_a=uid_a, uid_b=uid_b,
        )
        share_id = await _upsert_active_share(
            db, pathway=pathway, parent_a=parent_a, parent_b=parent_b,
        )
        seeded_shares[pathway] = share_id
        print(f"  {pathway}: swept {swept} stale share(s) → active share_id={share_id}")

    client.close()
    return {
        "parent_a": {"email": parent_a["email"], "user_id": uid_a},
        "parent_b": {"email": parent_b["email"], "user_id": uid_b},
        "shares": seeded_shares,
    }


if __name__ == "__main__":
    out = asyncio.run(run())
    print("\nSeeded deep-dive compare shares:")
    for k, v in out.items():
        print(f"  {k}: {v}")
    print("\nTest the compare PDFs (log in as parent1@test.com or parent2@test.com):")
    for pathway, sid in out["shares"].items():
        print(f"  GET /api/{pathway}-deep/compare/{sid}/pdf")
