# Helper for UI E2E of Safety Gate: setup | send | cleanup  (never prints the secret)
import hashlib, hmac, json, sys, time, uuid
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env"); BE = dotenv_values("/app/backend/.env")
BASE = FE["REACT_APP_BACKEND_URL"].rstrip("/")
DB = MongoClient(BE["MONGO_URL"].strip('"'))[BE["DB_NAME"].strip('"')]
STATE = "/tmp/sg_e2e.json"

cmd = sys.argv[1]
if cmd == "setup":
    case_id = "SA-T" + uuid.uuid4().hex[:5].upper()
    out = {"case_id": case_id, "users": []}
    for tag in ("a", "b"):
        s = requests.Session()
        email = f"test_sgui_{tag}_{uuid.uuid4().hex[:6]}@example.com"
        r = s.post(f"{BASE}/api/auth/register", json={"email": email, "password": "TestPass123!", "name": f"TEST UI {tag.upper()}",
                                                    "ack_privacy_notice": True, "consent_sensitive_info": True})
        uid = s.get(f"{BASE}/api/auth/me").json()["user_id"]
        out["users"].append({"email": email, "user_id": uid})
    DB.joint_alignment_cases.insert_one({"case_id": case_id, "status": "pending", "parents": [
        {"parent_slot": "A", "user_id": out["users"][0]["user_id"]}, {"parent_slot": "B", "user_id": out["users"][1]["user_id"]}]})
    json.dump(out, open(STATE, "w")); print(json.dumps(out))
elif cmd == "send":
    st = json.load(open(STATE))
    b = {"case_id": st["case_id"], "safety_mode": sys.argv[2], "set_by": sys.argv[3], "professional_name": "Dr TEST",
         "referral": sys.argv[4], "screening_offered": True, "version": int(sys.argv[5]), "timestamp": int(time.time())}
    raw = json.dumps(b).encode()
    sig = hmac.new(BE["ALIGN_WEBHOOK_SECRET"].encode(), raw, hashlib.sha256).hexdigest()
    r = requests.post(f"{BASE}/api/internal/safety-status", data=raw, headers={"Content-Type": "application/json", "X-Align-Signature": sig})
    print(r.status_code, r.text)
elif cmd == "cleanup":
    st = json.load(open(STATE)); ids = [u["user_id"] for u in st["users"]]
    DB.joint_alignment_cases.delete_many({"case_id": st["case_id"]}); DB.case_safety.delete_many({"case_id": st["case_id"]})
    DB.safety_audit_log.delete_many({"case_id": st["case_id"]}); DB.plan_option_picks.delete_many({"user_id": {"$in": ids}})
    DB.users.delete_many({"user_id": {"$in": ids}}); print("cleaned")
