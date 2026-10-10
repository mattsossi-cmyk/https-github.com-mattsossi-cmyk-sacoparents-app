"""Seed journey6@test.com with all 6 Individual Journey steps finished (for the "6 of 6 finished" banner + sparkle).
Copies parent1's assessments, then marks Psychological, Parallel Parenting and Communication Builder done.
Resets the one-time sparkle flag so it plays again. Idempotent: re-run any time."""
import asyncio
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
EMAIL, PASSWORD, NAME = "journey6@test.com", "TestPass123!", "Jordan Six"
SOURCE = "parent1@test.com"
CO_EMAIL = "delivered+j6coparent@resend.dev"
CASE_KEY = "J6-CASE-TEST"
COPY = ("self_assessment_history", "cp_assessments", "child_needs_assessments", "foundation_builder", "parallel_parenting_plans")


async def run() -> str:
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    if not await db.users.find_one({"email": EMAIL}, {"_id": 1}):
        async with httpx.AsyncClient() as c:
            r = await c.post("http://localhost:8001/api/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": NAME})
            r.raise_for_status()
    uid = (await db.users.find_one({"email": EMAIL}, {"user_id": 1}))["user_id"]
    src = (await db.users.find_one({"email": SOURCE}, {"user_id": 1}))["user_id"]
    now = datetime.now(timezone.utc).isoformat()

    for coll in COPY:
        await db[coll].delete_many({"user_id": uid})
        async for doc in db[coll].find({"user_id": src}, {"_id": 0}):
            await db[coll].insert_one({**doc, "user_id": uid})
    needs = await db.child_needs_assessments.find_one({"user_id": uid}, {"answers": 1}) or {}
    answers = needs.get("answers") or {}
    await db.child_needs_assessments.update_one(
        {"user_id": uid},
        {"$set": {"answers.psychological": answers.get("psychological") or answers.get("medical") or {}, "completed_at.psychological": now}},
        upsert=True,
    )
    await db.parallel_parenting_plans.update_one({"user_id": uid}, {"$set": {"completed_at": now, "step": 6}}, upsert=True)
    logs = [
        {"id": i, "timestamp": "2026-06-01 10:00", "category": "Schedule", "original": "You never tell me anything.", "biff": "Could you share the pickup time by Friday? Thanks."}
        for i in (1, 2, 3)
    ]
    await db.portal_state.update_one({"user_id": uid}, {"$set": {"user_id": uid, "biff_logs": logs, "last_door": "self"}}, upsert=True)
    await db.journey_celebrations.update_one({"user_id": uid}, {"$setOnInsert": {"celebrated_at": now}}, upsert=True)
    await db.journey_step_celebrations.delete_many({"user_id": uid})

    # Certificate-share recipients: an accepted professional + a co-parent linked by case code (Resend test inboxes).
    prov = await db.parent_professional_invitations.find_one({"invitation_id": "cnprovdemo01"}, {"_id": 0})
    if prov:
        await db.parent_professional_invitations.update_one(
            {"invitation_id": "j6provdemo01"},
            {"$set": {**prov, "invitation_id": "j6provdemo01", "inviting_parent_id": uid, "inviting_parent_email": EMAIL,
                      "professional_first_name": "Dana", "professional_last_name": "Reyes (test)", "professional_role": "attorney"}},
            upsert=True,
        )
    if not await db.users.find_one({"email": CO_EMAIL}, {"_id": 1}):
        async with httpx.AsyncClient() as c:
            r = await c.post("http://localhost:8001/api/auth/register", json={"email": CO_EMAIL, "password": PASSWORD, "name": "Casey Six (test co-parent)"})
            r.raise_for_status()
    co_uid = (await db.users.find_one({"email": CO_EMAIL}, {"user_id": 1}))["user_id"]
    for who in (uid, co_uid):
        await db.portal_state.update_one({"user_id": who}, {"$set": {"user_id": who, "court_key": CASE_KEY}}, upsert=True)
    await db.journey_certificate_shares.delete_many({"user_id": uid})
    return f"seeded {EMAIL} ({uid}): 6 of 6 steps done, sparkle reset"


if __name__ == "__main__":
    print(asyncio.run(run()))
