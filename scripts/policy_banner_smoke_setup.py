"""One-shot helper for the policy-refresh banner smoke test.

Registers a user, back-dates created_at, prints the token + user_id.
Run as: python /app/scripts/policy_banner_smoke_setup.py
"""
import asyncio
import os
import uuid
from pathlib import Path

import requests
from motor.motor_asyncio import AsyncIOMotorClient


BASE = None
MU = None
DB = None
for line in Path("/app/frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        BASE = line.split("=", 1)[1].strip().rstrip("/")
for line in Path("/app/backend/.env").read_text().splitlines():
    if line.startswith("MONGO_URL="):
        MU = line.split("=", 1)[1].strip().strip('"')
    if line.startswith("DB_NAME="):
        DB = line.split("=", 1)[1].strip().strip('"')


email = f"policy_banner_{uuid.uuid4().hex[:8]}@sacoparents-drill.com"
r = requests.post(
    f"{BASE}/api/auth/register",
    json={"email": email, "password": "TestPass123!", "name": "Returning Parent"},
    timeout=30,
)
r.raise_for_status()
data = r.json()

async def backdate():
    c = AsyncIOMotorClient(MU)
    await c[DB].users.update_one(
        {"user_id": data["user"]["user_id"]},
        {"$set": {"created_at": "2025-11-01T12:00:00+00:00"}},
    )
    c.close()

asyncio.run(backdate())

print(f"USER_ID={data['user']['user_id']}")
print(f"TOKEN={data['access_token']}")
