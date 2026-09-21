"""One-off: set credentials on a provider directory entry (preview DB)."""
import asyncio, os, sys
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    r = await db.providers.update_one({"name": sys.argv[1]}, {"$set": {sys.argv[2]: sys.argv[3], "updated_at": datetime.now(timezone.utc).isoformat()}})
    print("matched", r.matched_count, await db.providers.find_one({"name": sys.argv[1]}, {"_id": 0, "name": 1, "degrees": 1, "specialty": 1, "phone": 1, "email": 1, "website": 1}))

asyncio.run(main())
