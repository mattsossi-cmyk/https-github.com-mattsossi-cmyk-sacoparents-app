# Helper for iter144 UI test: `setup` creates two linked TEST parents in a restricted/auto_red case; `cleanup` removes them.
import json
import sys
import time
import uuid

import requests
from test_safety_gate_iter144_full import BASE_URL, DB, sign, register

STATE_FILE = "/tmp/ui_seed_iter144.json"


def setup():
    pro, _, epro = register("uipro")
    a, ua, ea = register("uia")
    b, ub, eb = register("uib")
    r = pro.post(f"{BASE_URL}/api/professional/joint-alignment/cases", json={
        "assessment_type": "co-parenting", "parents": [{"email": ea}, {"email": eb}], "professional_name": "Dr TESTPRO Zed"})
    case_id = r.json()["case_id"]
    for s in (a, b):
        assert s.post(f"{BASE_URL}/api/joint-alignment/manual-code", json={"code": case_id}).status_code == 200
    raw = json.dumps({"case_id": case_id, "safety_mode": "restricted", "set_by": "auto_red", "professional_name": "Dr TESTPRO Zed",
                      "referral": "parallel_parenting", "screening_offered": False, "version": 1,
                      "timestamp": int(time.time())}).encode()
    resp = requests.post(f"{BASE_URL}/api/internal/safety-status", data=raw,
                         headers={"Content-Type": "application/json", "X-Align-Signature": sign(raw)})
    json.dump({"case_id": case_id, "emails": [ea, eb, epro], "uids": [ua, ub]}, open(STATE_FILE, "w"))
    print("seeded", case_id, ea, eb, "webhook", resp.status_code)


def cleanup():
    st = json.load(open(STATE_FILE))
    for c in ("joint_alignment_cases", "case_safety", "safety_audit_log"):
        DB[c].delete_many({"case_id": st["case_id"]})
    DB.plan_option_picks.delete_many({"user_id": {"$in": st["uids"]}})
    print("users removed", DB.users.delete_many({"email": {"$in": st["emails"]}}).deleted_count)


if __name__ == "__main__":
    {"setup": setup, "cleanup": cleanup}[sys.argv[1]]()
