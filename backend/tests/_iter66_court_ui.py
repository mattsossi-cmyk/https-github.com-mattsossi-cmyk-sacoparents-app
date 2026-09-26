"""Setup for court thread UI test: creates a fresh professional + judge + accepted referral,
posts one urgent_safety court message, and prints credentials + refs."""
import os
import uuid
import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
from casekit import new_user  # noqa: E402

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"


def main():
    # judge
    s = requests.Session()
    je = f"t_j_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={
        "name": "Judge UI", "email": je, "password": "testpass123",
        "role": "judge", "agreements_accepted": True,
        "organization": "Court", "pro_role": "Judge"
    }).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one(
        {"email": je}, {"$set": {"approved": True}}
    )
    # professional
    pro = new_user(API, "professional", "UI Triage Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = s.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"],
        "cause_number": f"2026-CI-U{uuid.uuid4().hex[:4]}",
        "requested_reports": ["education"]
    }).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").status_code == 200
    # Post urgent message from court
    r = s.post(f"{API}/court-dashboard/cases/{ref['id']}/messages", json={
        "text": "URGENT: the child disclosed a threat of physical harm at exchange today; protective order requested."
    })
    assert r.status_code == 200
    print(f"JUDGE_EMAIL={je}")
    print(f"REF_ID={ref['id']}")


if __name__ == "__main__":
    main()
