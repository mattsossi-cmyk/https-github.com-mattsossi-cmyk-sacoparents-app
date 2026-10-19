"""Seed script — Joint Complete Alignment Report sample case.

Idempotent creation of a demonstrable joint case so the joint variant
of the Complete Alignment Report (added in iter184) can be exercised
end-to-end without waiting for real professional-created invitations.

Runs once via:
    python -c "from seed_joint_sample_case import run; import asyncio; asyncio.run(run())"

Actions:
  * Ensures both `parent1@test.com` (Sam Parent) and `parent2@test.com`
    (Riley Parent) exist in the `users` collection with a known password
    hash. Uses `auth.hash_password` so the resulting doc looks identical
    to a real signup.
  * Seeds a minimal Foundation Statement for `parent2` so the joint
    report has at least one lane in the "shared" state (parent1
    already has one via the login-flow fixture).
  * Seeds a Communication Reflection for `parent1` and NOT for `parent2`
    so we exercise the "one-side" alignment status at the same time.
  * Upserts a `joint_alignment_cases` document with the fixed
    `case_id = "SA-DEMO01"`. Both parents are pre-accepted so the
    /api/complete-report/joint/{case_id} endpoint returns 200 rather
    than 409 (both-parents-not-accepted).
  * Prints the resulting case_id + parent credentials so the tester
    knows what to log in with.

Safety:
  * Only runs against the local dev DB (uses MONGO_URL / DB_NAME from
    the same env that the server reads). Never writes to production
    databases — the test_credentials.md accounts don't exist there.
  * Idempotent — re-running the script re-syncs all rows to their
    canonical seed values without duplicating anything.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from align_ref import new_align_ref


load_dotenv("/app/backend/.env")


DEMO_CASE_ID = "SA-DEMO01"
DEMO_PROFESSIONAL_EMAIL = "sample-professional@sacoparents.demo"


async def _ensure_user(db, *, email: str, name: str) -> dict:
    """Return the user document (creating it if missing). Uses the
    project's own hash helper so the resulting row is indistinguishable
    from a real signup."""
    from auth import hash_password
    u = await db.users.find_one({"email": email})
    if u:
        return u
    import uuid
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": name,
        "hashed_password": hash_password("TestPass123!"),
        "created_at": now,
        "email_verified": True,
        "auth_method": "jwt",
        "align_ref": new_align_ref(),
    }
    await db.users.insert_one(doc)
    return doc


def _uid(u: dict) -> str:
    """Users can carry either `user_id` (canonical) or a legacy `id`.
    Normalise here so the rest of the seed script speaks one dialect."""
    return u.get("user_id") or u.get("id") or ""


async def _seed_foundation(db, *, user_id: str, prompts: dict, child_name: str) -> None:
    now = datetime.now(timezone.utc)
    await db.prep_data.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "child_name": child_name,
                "reflection": prompts,
                "updated_at": now,
            }
        },
        upsert=True,
    )


async def _seed_communication(db, *, user_id: str) -> None:
    """Insert a minimal Communication Reflection so the aggregator
    sees `lane.completed=True` for parent1's communication lane."""
    now = datetime.now(timezone.utc)
    await db.communication_reflection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "answers": {"preferred_channel": "email"},
                "updated_at": now,
                "generated_at": now,
            }
        },
        upsert=True,
    )


async def _upsert_demo_case(db, *, parent_a: dict, parent_b: dict) -> dict:
    now = datetime.now(timezone.utc)
    # Keep each slot's align_ref across re-seeds (it must never change).
    prev = await db.joint_alignment_cases.find_one({"case_id": DEMO_CASE_ID}, {"_id": 0, "parents": 1}) or {}
    kept = {p.get("parent_slot"): p.get("align_ref") for p in prev.get("parents") or [] if isinstance(p, dict)}
    parents_doc = []
    for slot, u in (("A", parent_a), ("B", parent_b)):
        parents_doc.append({
            "parent_slot": slot,
            "email": u["email"].lower(),
            "name": u["name"],
            "invitation_token": f"demo_token_{slot.lower()}",
            "token_expires_at": now + timedelta(days=30),
            "accepted_at": now,
            "user_id": _uid(u),
            "align_ref": kept.get(slot) or new_align_ref(),
            "assessment_completed_at": now,
            "assessment_ref": None,
        })
    # Fields that should NOT be rewritten on every re-seed. `created_at`
    # in particular — a stable "first seeded on" timestamp lets ops
    # audit when the sample case landed on any given environment.
    set_on_insert = {
        "created_at": now,
    }
    case_doc = {
        "case_id": DEMO_CASE_ID,
        "assessment_type": "co-parenting",
        "professional": {
            "id": _uid(parent_a),  # Sample only — parent A doubles as the
                                   # "professional who created this case" so
                                   # signing in as parent A gives access.
            "name": "Sample Professional (Demo)",
            "email": DEMO_PROFESSIONAL_EMAIL,
        },
        "professional_created_by": _uid(parent_a),
        "origin": "seed_script",
        "align_case_reference": "seed:complete-alignment-demo",
        "reminder_note": None,
        "parents": parents_doc,
        "status": "completed",
        "case_expires_at": now + timedelta(days=365),
    }
    await db.joint_alignment_cases.update_one(
        {"case_id": DEMO_CASE_ID},
        {"$set": case_doc, "$setOnInsert": set_on_insert},
        upsert=True,
    )
    # Re-read for return — includes whatever `created_at` MongoDB now
    # holds (either the freshly-inserted value or the pre-existing one).
    return await db.joint_alignment_cases.find_one({"case_id": DEMO_CASE_ID}) or case_doc


async def run() -> dict:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    parent_a = await _ensure_user(db, email="parent1@test.com", name="Sam Parent")
    parent_b = await _ensure_user(db, email="parent2@test.com", name="Riley Parent")
    parent_a_uid = _uid(parent_a)
    parent_b_uid = _uid(parent_b)
    assert parent_a_uid and parent_b_uid, "Seeded users missing user_id"

    # Parent A already tends to have a Foundation Statement via the
    # login-flow fixture, but re-assert a canonical one so re-runs
    # produce identical output.
    await _seed_foundation(
        db, user_id=parent_a_uid,
        child_name="Rian",
        prompts={
            "child_lens": "My kid would say handoffs feel rushed.",
            "own_part": "I forget to pause when I feel judged.",
            "best_outcome": "Calmer weeknight pickups within 90 days.",
            "coparent_feedback": "Their other parent would say I text too fast.",
        },
    )
    await _seed_foundation(
        db, user_id=parent_b_uid,
        child_name="Rian",
        prompts={
            "child_lens": "From Rian's side the transitions are the hardest part of the week.",
            "own_part": "I sometimes rush to explain when a pause would land better.",
            "best_outcome": "A shared Sunday-evening 15-minute check-in that both of us keep.",
            "coparent_feedback": "I'd like more heads-up on schedule changes than 24 hours.",
        },
    )
    # Communication only on Parent A → produces a "one-side" alignment row
    await _seed_communication(db, user_id=parent_a_uid)

    case = await _upsert_demo_case(db, parent_a=parent_a, parent_b=parent_b)

    result = {
        "case_id": case["case_id"],
        "parent_a": {"email": parent_a["email"], "user_id": parent_a_uid},
        "parent_b": {"email": parent_b["email"], "user_id": parent_b_uid},
    }
    client.close()
    return result


if __name__ == "__main__":
    out = asyncio.run(run())
    print("Seeded joint sample case:")
    for k, v in out.items():
        print(f"  {k}: {v}")
