"""Iter-65 FRONTEND setup for safety-gate UI test.
Emits JSON with data needed to drive the browser test."""
import json
import os
import sys
import uuid

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

sys.path.insert(0, os.path.dirname(__file__))
from casekit import complete_both, new_user  # noqa: E402
from test_iter64_agreement_to_court import AGR_FIELDS, _agreement_answers  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "testpass123"
SAFE = {"fear": False, "threats": False, "control": False}


def _approve(email: str) -> None:
    c = pymongo.MongoClient(os.environ["MONGO_URL"])
    c[os.environ["DB_NAME"]].users.update_one({"email": email.lower()}, {"$set": {"approved": True}})
    c.close()


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_uij65_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Judge UI 65", "email": e, "password": PASSWORD,
                                              "role": "judge", "agreements_accepted": True,
                                              "organization": "Court", "pro_role": "Judge"})
    r.raise_for_status()
    _approve(e)
    s.email = e
    return s


def main() -> None:
    # ============== Scenario 1: parent-facing safety gate on /foundation and /joint ==============
    judge = _judge()
    pro = new_user(API, "professional", "Pro65 UI")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"],
        "cause_number": f"2026-CI-U65{uuid.uuid4().hex[:4]}",
        "requested_reports": ["education"]}).json()
    pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").raise_for_status()
    ea = f"t_a{uuid.uuid4().hex[:6]}@example.com"
    eb = f"t_b{uuid.uuid4().hex[:6]}@example.com"
    case = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "education", "child_name": "Kai",
        "parent_a_name": "A", "parent_a_email": ea,
        "parent_b_name": "B", "parent_b_email": eb,
        "court_referral_id": ref["id"]}).json()
    rid = case["id"]
    pa, pb = complete_both(API, pro, rid, case["invitations"])

    # ============== Scenario 2: agreement + high-risk Legal Lens for pro submit-to-court + judge card ==============
    judge2 = _judge()
    pro2 = new_user(API, "professional", "Pro65 UI2")
    me2 = pro2.get(f"{API}/auth/me").json()
    ref2 = judge2.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me2["id"],
        "cause_number": f"2026-CI-U65{uuid.uuid4().hex[:4]}",
        "requested_reports": ["education"]}).json()
    pro2.post(f"{API}/professional/court-referrals/{ref2['id']}/accept").raise_for_status()
    ea2 = f"t_a{uuid.uuid4().hex[:6]}@example.com"
    eb2 = f"t_b{uuid.uuid4().hex[:6]}@example.com"
    case2 = pro2.post(f"{API}/joint/reports/professional", json={
        "subject": "education", "child_name": "Emma",
        "parent_a_name": "A", "parent_a_email": ea2,
        "parent_b_name": "B", "parent_b_email": eb2,
        "court_referral_id": ref2["id"]}).json()
    rid2 = case2["id"]
    pa2, pb2 = complete_both(API, pro2, rid2, case2["invitations"])

    # agreement for the same parent emails on case2
    emails = {i["role"]: i["invitee_email"] for i in case2["invitations"]}
    ag = pro2.post(f"{API}/joint/agreements", json={
        "child_name": "Emma", "parent_a_name": "Parent A", "parent_a_email": emails["a"],
        "parent_b_name": "Parent B", "parent_b_email": emails["b"]}).json()
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in ag["invitations"]}
    answers = _agreement_answers()
    for s, role in ((pa2, "a"), (pb2, "b")):
        s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]}).raise_for_status()
        s.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS, "safety": SAFE}).raise_for_status()
        r = s.put(f"{API}/joint/reports/{ag['id']}/responses", json={"answers": answers})
        r.raise_for_status()

    # High-risk Legal Lens for the joint case
    pro2.get(f"{API}/cases/{rid2}/professional-report").raise_for_status()
    pro2.put(f"{API}/cases/{rid2}/professional-report", json={
        "fields": {"risk_screening": {"threats": {"level": "High Risk", "note": "documented threats"}},
                   "joint_process_appropriate": "No — safety concerns"}}).raise_for_status()

    # pro statement ready
    base = {"role": "Mediator", "role_basis": "Court referral",
            "process_summary": "x", "observations": "y", "next_steps": "z",
            "status": "ready", "dynamic_score": 3}
    pro2.put(f"{API}/joint/reports/{rid2}/professional-statement", json=base).raise_for_status()

    print(json.dumps({
        "api": API,
        "base": BASE_URL,
        # Scenario 1
        "rid_s1": rid,
        "pa_email": pa.email,
        "pb_email": pb.email,
        # Scenario 2
        "rid_s2": rid2,
        "refId_s2": ref2["id"],
        "agreement_id": ag["id"],
        "pro2_email": pro2.email,
        "judge2_email": judge2.email,
        "password": PASSWORD,
    }, indent=2))


if __name__ == "__main__":
    main()
