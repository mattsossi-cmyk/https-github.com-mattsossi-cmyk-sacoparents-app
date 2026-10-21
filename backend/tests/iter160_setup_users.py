# Iter160 UI fixture: creates unlinked / linked+case / linked-no-case parents; `cleanup` arg removes them.
import json
import os
import sys
import uuid

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
KEY = {"X-Integration-Key": os.environ["INTEGRATION_SHARED_SECRET"]}
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
OUT = "/tmp/iter160_users.json"


def make(kind):
    email = f"test_iter160ui_{kind}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": f"UI {kind}",
                                                    "ack_privacy_notice": True, "consent_sensitive_info": True})
    r.raise_for_status()
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    uid = r.json()["user"]["user_id"]
    if kind != "unlinked":
        code = requests.post(f"{API}/link-codes", headers=h, json={}).json()["code"]
        assert requests.post(f"{API}/integrations/verify-link-code", headers=KEY, json={"code": code}).status_code == 200
    case = None
    if kind == "case":
        case = "SA-T160" + uuid.uuid4().hex[:4].upper()
        db.joint_alignment_cases.insert_one({"case_id": case, "parents": [{"user_id": uid, "email": email}], "test_iter160": True})
    return {"email": email, "user_id": uid, "case": case}


if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    users = json.load(open(OUT))
    for u in users.values():
        for coll in ("users", "prep_data", "align_links", "align_access_log", "align_share_choices", "link_codes", "portal_state", "legal_acknowledgments"):
            db[coll].delete_many({"user_id": u["user_id"]})
    db.joint_alignment_cases.delete_many({"test_iter160": True})
    print("cleaned", len(users))
else:
    users = {k: make(k) for k in ("unlinked", "case", "nocase")}
    json.dump(users, open(OUT, "w"))
    print(json.dumps(users, indent=1))
