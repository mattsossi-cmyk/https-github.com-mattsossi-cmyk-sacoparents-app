"""Iter-64 FRONTEND setup: create the artifacts needed to exercise the UI.
Emits JSON on stdout with: {rid_with, refId_with, rid_no, refId_no,
pro_email, pro_password, judge_email, judge_password}.
Mirrors backend/tests/test_iter64_agreement_to_court.py without asserting UI-only bits."""
import json
import os
import secrets
import sys
import uuid

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

PASSWORD = os.environ.get("TEST_FIXTURE_PASSWORD") or "T!" + secrets.token_urlsafe(12)

AGR_FIELDS = {"child_name": "Emma64UI", "shared_purpose": "Calm.", "vision": "Safe.",
              "priorities": ["Protect Emma"], "strengths": "Curious and kind.",
              "needs": ["Calm transitions"], "commitments": ["Stay calm"],
              "goals": ["Fewer disputes"], "parent_commitment": "Emma first."}


def _approve(email: str) -> None:
    c = pymongo.MongoClient(os.environ["MONGO_URL"])
    c[os.environ["DB_NAME"]].users.update_one({"email": email.lower()}, {"$set": {"approved": True}})
    c.close()


def new_user(role: str, name: str = "T", email: str | None = None, invite: str = "") -> requests.Session:
    s = requests.Session()
    email = email or f"t_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": name, "email": email, "password": PASSWORD,
                                             "role": role, "invite": invite,
                                             "agreements_accepted": role != "parent",
                                             "organization": "Court" if role == "judge" else "",
                                             "pro_role": "Judge" if role == "judge" else ""})
    r.raise_for_status()
    if role in ("professional", "judge"):
        _approve(email)
    s.email = email
    return s


def _answers() -> dict:
    secs = requests.get(f"{API}/joint/config").json().get("agreement_sections") or []
    out = {}
    for s in secs:
        out[s["key"]] = f"Clear child-focused plan for {s['label'].lower()} using the app with 24-hour notice."
        for fu in s.get("follow_ups") or []:
            out[fu["key"]] = "Use the SA CoParents app with 24-hour notice; exchanges at school."
    return out


def _make_ready_case(pro: requests.Session, judge: requests.Session, judge_email: str):
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"], "cause_number": f"2026-CI-UI{uuid.uuid4().hex[:4]}",
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
    toks = {i["role"]: i["link"].split("invite=")[-1] for i in case["invitations"]}
    for role, em in (("a", ea), ("b", eb)):
        s = new_user("parent", f"Parent {role.upper()}", email=em, invite=toks[role])
        s.post(f"{API}/joint/invitations/accept", json={"code": toks[role]})
        s.put(f"{API}/joint/reports/{rid}/responses", json={"answers": {
            "needs_most": "x", "working_well": "y", "concerns": "z",
            "improve": "w", "options": "o", "other_parent": "p"}}).raise_for_status()
    # pro statement ready
    base = {"role": "Mediator", "role_basis": "Court referral",
            "process_summary": "x", "observations": "y", "next_steps": "z",
            "status": "ready", "dynamic_score": 5}
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json=base).raise_for_status()
    return rid, ref, ea, eb


def main() -> None:
    judge = new_user("judge", "Judge UI")
    pro = new_user("professional", "Pro UI")

    # Case WITH agreement
    rid_with, ref_with, ea, eb = _make_ready_case(pro, judge, judge.email)

    # Create agreement for the same parent emails
    ag = pro.post(f"{API}/joint/agreements", json={
        "child_name": "Emma", "parent_a_name": "Parent A", "parent_a_email": ea,
        "parent_b_name": "Parent B", "parent_b_email": eb}).json()
    ag_toks = {i["role"]: i["link"].split("invite=")[-1] for i in ag["invitations"]}
    ans = _answers()
    for role, em in (("a", ea), ("b", eb)):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": em, "password": PASSWORD})
        r.raise_for_status()
        s.post(f"{API}/joint/invitations/accept", json={"code": ag_toks[role]}).raise_for_status()
        s.put(f"{API}/foundation/mine", json={"fields": AGR_FIELDS, "safety": {"fear": False, "threats": False, "control": False}}).raise_for_status()
        s.post(f"{API}/joint/reports/{ag['id']}/foundation/share").raise_for_status()
        r = s.put(f"{API}/joint/reports/{ag['id']}/responses", json={"answers": ans})
        r.raise_for_status()
    assert pro.get(f"{API}/joint/reports/{ag['id']}").json()["status"] == "ready"

    # Case WITHOUT agreement (submitted via API to test judge sees no card)
    rid_no, ref_no, _, _ = _make_ready_case(pro, judge, judge.email)
    sub = pro.post(f"{API}/joint/reports/{rid_no}/submit-to-court", json={"attest": True})
    sub.raise_for_status()

    print(json.dumps({
        "api": API,
        "base": BASE_URL,
        "rid_with": rid_with,
        "refId_with": ref_with["id"],
        "cause_with": ref_with["cause_number"],
        "agreement_id": ag["id"],
        "agreement_case_code": ag.get("case_code"),
        "rid_no": rid_no,
        "refId_no": ref_no["id"],
        "cause_no": ref_no["cause_number"],
        "pro_email": pro.email,
        "judge_email": judge.email,
        "password": PASSWORD,
    }, indent=2))


if __name__ == "__main__":
    main()
