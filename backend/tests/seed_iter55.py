"""Seed for iteration 55: full completed case + judge referral, ready for court submission."""
import json
import os
import sys
import uuid

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, os.path.dirname(__file__))
from casekit import complete_both, new_user  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _judge():
    s = requests.Session()
    e = f"t_pjudge_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "Judge Portal", "email": e, "password": "testpass123", "role": "judge",
        "agreements_accepted": True, "organization": "Court", "pro_role": "Judge",
    })
    assert r.status_code == 200, r.text
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one(
        {"email": e}, {"$set": {"approved": True}}
    )
    s.email = e
    return s


def main():
    judge = _judge()
    pro = new_user(API, "professional", "Portal Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"],
        "cause_number": f"2026-CI-P{uuid.uuid4().hex[:4]}",
        "requested_reports": ["education"],
    }).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").status_code == 200
    case = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "education", "child_name": "Kai", "parent_a_name": "A",
        "parent_a_email": f"t_a{uuid.uuid4().hex[:6]}@example.com",
        "parent_b_name": "B", "parent_b_email": f"t_b{uuid.uuid4().hex[:6]}@example.com",
        "court_referral_id": ref["id"],
    }).json()
    complete_both(API, pro, case["id"], case["invitations"])
    out = {
        "pro_email": pro.email,
        "judge_email": judge.email,
        "rid": case["id"],
        "case_code": case.get("case_code"),
        "referral_id": ref["id"],
        "password": "testpass123",
    }
    with open("/tmp/iter55_seed.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
