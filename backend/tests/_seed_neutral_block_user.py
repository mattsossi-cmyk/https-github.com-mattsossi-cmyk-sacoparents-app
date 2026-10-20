# Helper: create/cleanup a fresh user with a legacy level-1 safety_assessments row (neutral-block UI test)
import os
import sys
import uuid
import asyncio
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].rstrip("/")
STATE = "/tmp/neutral_user.txt"


async def main(mode):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    if mode == "create":
        email = f"test_neutral_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{BASE}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": "TEST Neutral",
                                                             "ack_privacy_notice": True, "consent_sensitive_info": True})
        print("register", r.status_code)
        u = await db.users.find_one({"email": email}, {"_id": 0, "user_id": 1})
        aid = f"sa_x_{uuid.uuid4().hex[:8]}"
        await db.safety_assessments.insert_one({"assessment_id": aid, "user_id": u["user_id"],
                                                "created_at": datetime.now(timezone.utc).isoformat(), "answers": {}, "result": {"level": 1}})
        open(STATE, "w").write(f"{email} {u['user_id']} {aid}")
        print("EMAIL", email)
    else:
        email, uid, aid = open(STATE).read().split()
        await db.safety_assessments.delete_many({"user_id": uid})
        n = 0
        for c in await db.list_collection_names():
            res = await db[c].delete_many({"user_id": uid})
            n += res.deleted_count
        await db.users.delete_many({"email": email})
        print("cleaned", n)


asyncio.run(main(sys.argv[1]))
