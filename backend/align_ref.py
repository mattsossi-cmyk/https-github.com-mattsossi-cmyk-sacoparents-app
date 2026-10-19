"""Per-parent align_ref: generated once with str(uuid.uuid4()), stored, never changed. Only used in the Align check-in link."""
import logging
import uuid

logger = logging.getLogger(__name__)


def new_align_ref() -> str:
    return str(uuid.uuid4())


async def missing_align_refs(db) -> dict:
    return {
        "accounts_missing": await db.users.count_documents({"align_ref": {"$exists": False}}),
        "case_entries_missing": await db.joint_alignment_cases.count_documents({"parents": {"$elemMatch": {"align_ref": {"$exists": False}}}}),
    }


async def backfill_align_refs(db) -> dict:
    """Admin-run only (after a backup). Idempotent: only fills accounts / case parent entries that have no align_ref yet."""
    await db.users.create_index("align_ref", unique=True, sparse=True)
    users = 0
    async for u in db.users.find({"align_ref": {"$exists": False}}, {"_id": 1}):
        res = await db.users.update_one({"_id": u["_id"], "align_ref": {"$exists": False}}, {"$set": {"align_ref": new_align_ref()}})
        users += res.modified_count
    entries = 0
    async for c in db.joint_alignment_cases.find({"parents": {"$elemMatch": {"align_ref": {"$exists": False}}}}, {"_id": 1, "parents": 1}):
        for i, p in enumerate(c.get("parents") or []):
            if isinstance(p, dict) and "align_ref" not in p:
                key = f"parents.{i}.align_ref"
                res = await db.joint_alignment_cases.update_one({"_id": c["_id"], key: {"$exists": False}}, {"$set": {key: new_align_ref()}})
                entries += res.modified_count
    logger.info("align_ref backfill: %s accounts, %s case parent entries", users, entries)
    return {"users": users, "case_parents": entries}
