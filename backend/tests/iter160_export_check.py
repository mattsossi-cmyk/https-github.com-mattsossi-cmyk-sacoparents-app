# Iter160 helper: print export communication_readiness keys for an email; `unset <user_id>` drops wording_version.
import json
import os
import sys

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
KEY = {"X-Integration-Key": os.environ["INTEGRATION_SHARED_SECRET"]}
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

if sys.argv[1] == "unset":
    print(db.align_share_choices.update_one({"user_id": sys.argv[2]}, {"$unset": {"wording_version": ""}}).modified_count)
elif sys.argv[1] == "choice":
    print(db.align_share_choices.find_one({"user_id": sys.argv[2]}, {"_id": 0}))
else:
    r = requests.get(f"{API}/integrations/export-assessments", params={"email": sys.argv[1]}, headers=KEY)
    cr = r.json().get("communication_readiness")
    print(r.status_code, json.dumps(cr, indent=1) if cr else "communication_readiness ABSENT")
