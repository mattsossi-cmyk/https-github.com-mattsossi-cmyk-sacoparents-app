"""Seed data for iteration 48 frontend tests.
Creates: (1) pro-owned ready education case, (2) court-referred case with two
submissions (score 3 then 6). Prints JSON with credentials + IDs."""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case, complete_both, new_user  # noqa: E402
import pymongo  # noqa: E402
import requests  # noqa: E402

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _judge():
    s = requests.Session()
    e = f"t_pjudge_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Judge P", "email": e, "password": "testpass123",
                                             "role": "judge", "agreements_accepted": True,
                                             "organization": "Court", "pro_role": "Judge"})
    assert r.status_code == 200, r.text
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": e}, {"$set": {"approved": True}})
    s.email = e
    return s


def scenario_a_ready_case():
    """Pro-owned ready case for FrameworkPanel + ResourceLibrary UI test."""
    pro, pa, pb, case, detail = completed_case(API)
    return {"pro_email": pro.email, "rid": case["id"], "case_code": case.get("case_code")}


def scenario_b_court_two_submissions():
    """Judge referral -> pro accept -> parents complete -> two ready+submits with different scores."""
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

    body = {"role": "Mediator", "role_basis": "Court referral basis.",
            "process_summary": "Both parents completed intake independently.",
            "observations": "Neutral observations from the report.",
            "next_steps": "Continue facilitation.", "status": "ready", "dynamic_score": 3}
    r = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=body)
    assert r.status_code == 200, r.text
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True})
    assert r.status_code == 200, r.text

    body["dynamic_score"] = 6
    r = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=body)
    assert r.status_code == 200, r.text
    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True})
    assert r.status_code == 200, r.text

    return {"judge_email": judge.email, "pro_email": pro.email, "rid": rid, "refId": ref["id"],
            "case_code": case.get("case_code"), "cause_number": cause}


if __name__ == "__main__":
    out = {"scenario_a": scenario_a_ready_case(), "scenario_b": scenario_b_court_two_submissions()}
    print(json.dumps(out, indent=2))
