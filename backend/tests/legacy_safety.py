"""The old in-app Safety Assessment API is gone; tests that need a saved old result write it straight to the database."""
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
NOT_AVAILABLE = "This isn't available right now. Your Family check-in on SACOparentsAlign is the next step."


def save_old_result(client, base_url, level=4):
    """Saves an old result as this parent's latest (level 4 = clear, 1-2 = concerning)."""
    uid = client.get(f"{base_url}/api/auth/me", timeout=30).json()["user_id"]
    aid = f"sa_test_{uuid.uuid4().hex[:10]}"
    _db.safety_assessments.insert_one({"assessment_id": aid, "user_id": uid, "created_at": datetime.now(timezone.utc).isoformat(),
                                       "answers": {}, "result": {"level": level}, "source": "test_fixture"})
    return {"assessment_id": aid, "result": {"level": level}}
