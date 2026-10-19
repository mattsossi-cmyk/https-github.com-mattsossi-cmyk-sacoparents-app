# Helper for iter145 UI test: `setup` links two TEST parents; `set true|false` sends a signed update; `cleanup` removes all.
import json
import sys
import time

import requests
from test_safety_gate_iter144_full import BASE_URL, DB, sign, register

STATE_FILE = "/tmp/ui_seed_iter145.json"


def setup():
    pro, upro, epro = register("uifcpro")
    a, ua, ea = register("uifca")
    b, ub, eb = register("uifcb")
    r = pro.post(f"{BASE_URL}/api/professional/joint-alignment/cases", json={
        "assessment_type": "co-parenting", "parents": [{"email": ea}, {"email": eb}], "professional_name": "Dr TESTPRO Zed"})
    case_id = r.json()["case_id"]
    for s in (a, b):
        assert s.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": case_id}).status_code == 200
    json.dump({"case_id": case_id, "emails": [ea, eb, epro], "uids": [ua, ub, upro], "v": 0}, open(STATE_FILE, "w"))
    print("seeded", case_id, ea, eb)


def set_flag(val):
    st = json.load(open(STATE_FILE))
    st["v"] += 1
    raw = json.dumps({"case_id": st["case_id"], "safety_mode": "standard", "set_by": "professional", "professional_name": "Dr TESTPRO Zed",
                      "referral": "none", "screening_offered": val == "true", "version": st["v"],
                      "timestamp": int(time.time())}).encode()
    r = requests.post(f"{BASE_URL}/api/internal/safety-status", data=raw,
                      headers={"Content-Type": "application/json", "X-Align-Signature": sign(raw)})
    json.dump(st, open(STATE_FILE, "w"))
    print("webhook", r.status_code, r.json().get("status") if r.ok else "")


def cleanup():
    st = json.load(open(STATE_FILE))
    for c in ("joint_alignment_cases", "case_safety", "safety_audit_log"):
        DB[c].delete_many({"case_id": st["case_id"]})
    for c in ("plan_option_picks", "portal_state", "court_requested"):
        DB[c].delete_many({"user_id": {"$in": st["uids"]}})
    print("users removed", DB.users.delete_many({"email": {"$in": st["emails"]}}).deleted_count)


if __name__ == "__main__":
    {"setup": setup, "set": lambda: set_flag(sys.argv[2]), "cleanup": cleanup}[sys.argv[1]]()
