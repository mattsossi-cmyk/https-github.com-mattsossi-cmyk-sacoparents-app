"""Seed one accepted professional invitation for parent1 so "Send to a provider" has someone to pick.
Uses Resend's test inbox (delivered@resend.dev) so real sends never reach a person. Idempotent."""
import asyncio
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


async def run() -> str:
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    user = await db.users.find_one({"email": "parent1@test.com"}, {"_id": 0, "user_id": 1, "name": 1})
    now = datetime.now(timezone.utc)
    await db.parent_professional_invitations.update_one(
        {"invitation_id": "cnprovdemo01"},
        {"$set": {
            "invitation_id": "cnprovdemo01",
            "inviting_parent_id": user["user_id"],
            "inviting_parent_name": user.get("name"),
            "inviting_parent_email": "parent1@test.com",
            "professional_first_name": "Dana",
            "professional_last_name": "Reyes (test)",
            "professional_email": "delivered@resend.dev",
            "professional_role": "educational-professional",
            "organization": "Maple Elementary (demo)",
            "selected_reports": [],
            "view_permission": True,
            "status": "accepted",
            "created_at": now,
            "accepted_at": now,
            "access_expiration": now + timedelta(days=30),
            "revoked_at": None,
        }},
        upsert=True,
    )
    return "seeded cnprovdemo01 for parent1"


if __name__ == "__main__":
    print(asyncio.run(run()))
