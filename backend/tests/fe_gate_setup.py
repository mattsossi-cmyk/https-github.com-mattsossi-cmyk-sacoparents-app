"""Helper for frontend Safety Gate testing: `setup` creates two linked parents; `send <case> <v> <mode> <set_by> <referral>` signs a webhook."""
import hashlib, hmac, json, os, sys, time, uuid
from pathlib import Path
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env"); load_dotenv(ROOT.parent / "frontend" / ".env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

if sys.argv[1] == "setup":
    ids, emails = [], []
    for _ in range(2):
        e = f"test_fe_gate_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{API}/auth/register", json={"email": e, "password": "Str0ng!Pass99", "name": "FE Gate", "ack_privacy_notice": True, "consent_sensitive_info": True}, timeout=20)
        assert r.status_code == 200, r.text
        ids.append(db.users.find_one({"email": e})["user_id"]); emails.append(e)
    cid = f"SA-F{uuid.uuid4().hex[:5].upper()}"
    db.joint_alignment_cases.insert_one({"case_id": cid, "status": "pending", "parents": [{"parent_slot": "A", "user_id": ids[0]}, {"parent_slot": "B", "user_id": ids[1]}]})
    print(json.dumps({"case": cid, "a": emails[0], "b": emails[1]}))
else:
    _, cid, v, mode, set_by, ref = sys.argv[1:]
    raw = json.dumps({"case_id": cid, "safety_mode": mode, "set_by": set_by, "professional_name": "Dr. X", "referral": ref, "screening_offered": True, "version": int(v), "timestamp": int(time.time())}).encode()
    sig = hmac.new((os.environ.get("ALIGN_WEBHOOK_SECRET") or "").encode(), raw, hashlib.sha256).hexdigest()
    print(requests.post(f"{API}/internal/safety-status", data=raw, headers={"X-Align-Signature": sig, "Content-Type": "application/json"}, timeout=20).status_code)
