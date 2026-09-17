"""Seed data for iteration 49 frontend tests (level change note + org library).
Creates: judge referral → pro accept → parents complete → statement ready (score 3) → submit-to-court v1.
Sets pro's profile.organization to 'Alamo Test Org'.
Creates colleague pro with same org lowercased and stranger pro with no organization.
Prints JSON with credentials + IDs."""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from casekit import complete_both, new_user  # noqa: E402
import pymongo  # noqa: E402
import requests  # noqa: E402

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ORG = "Alamo Test Org"


def _judge():
    s = requests.Session()
    e = f"t_pjudge_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Judge Iter49", "email": e, "password": "testpass123",
                                             "role": "judge", "agreements_accepted": True,
                                             "organization": "Court", "pro_role": "Judge"})
    assert r.status_code == 200, r.text
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": e}, {"$set": {"approved": True}})
    s.email = e
    return s


def scenario():
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    judge = _judge()
    pro = new_user(API, "professional", "Portal Pro")
    me = pro.get(f"{API}/auth/me").json()
    cause = f"2026-CI-P{uuid.uuid4().hex[:4]}"
    ref = judge.post(f"{API}/court-dashboard/referrals",
                     json={"professional_id": me["id"], "cause_number": cause, "requested_reports": ["education"]}).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").status_code == 200
    case = pro.post(f"{API}/joint/reports/professional",
                    json={"subject": "education", "child_name": "Kai",
                          "parent_a_name": "A", "parent_a_email": f"t_a{uuid.uuid4().hex[:6]}@example.com",
                          "parent_b_name": "B", "parent_b_email": f"t_b{uuid.uuid4().hex[:6]}@example.com",
                          "court_referral_id": ref["id"]}).json()
    rid = case["id"]
    complete_both(API, pro, rid, case["invitations"])

    # Set org on pro profile
    db.users.update_one({"_id": me["id"]}, {"$set": {"profile.organization": ORG}})

    # Ready statement at score 3 and submit to court (v1)
    body = {"role": "Mediator", "role_basis": "Court referral basis.",
            "process_summary": "Both parents completed intake.",
            "observations": "Neutral observations.",
            "next_steps": "Continue facilitation.", "status": "ready", "dynamic_score": 3}
    r = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=body)
    assert r.status_code == 200, r.text
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True})
    assert r.status_code == 200, r.text

    # Colleague with same org lowercased, plus one ready case to view org library
    colleague = new_user(API, "professional", "Colleague Pro")
    cme = colleague.get(f"{API}/auth/me").json()
    db.users.update_one({"_id": cme["id"]}, {"$set": {"profile.organization": ORG.lower()}})

    # Stranger with no organization
    stranger = new_user(API, "professional", "Stranger Pro")

    return {"judge_email": judge.email, "pro_email": pro.email, "rid": rid, "refId": ref["id"],
            "case_code": case.get("case_code"), "cause_number": cause, "organization": ORG,
            "colleague_email": colleague.email, "stranger_email": stranger.email}


if __name__ == "__main__":
    print(json.dumps(scenario(), indent=2))
