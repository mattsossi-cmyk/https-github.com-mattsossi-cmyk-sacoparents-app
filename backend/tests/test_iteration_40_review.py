"""Iteration 40 review-request backend spot checks.

Verifies the 4 explicit backend assertions from the review request:
  1. GET /api/health build == '2026-09-11.5'
  2. GET /api/court-dashboard/referrals as a professional -> 403
  3. PUT /api/joint/reports/<id>/professional-statement with custody language -> 400
  4. POST /api/joint/reports/<id>/submit-to-court on a NON-court case -> 400
"""
import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from casekit import new_user, new_case, CaseSpec, complete_both, fill

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_health_build_is_2026_09_11_5():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("build") == "2026-09-11.5", j


def test_pro_cannot_list_court_referrals():
    pro = new_user(API, "professional", "PRO")
    r = pro.get(f"{API}/court-dashboard/referrals")
    assert r.status_code == 403, (r.status_code, r.text)


def _register_approved_judge():
    email = f"t_judge_{uuid.uuid4().hex[:6]}@example.com"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={
        "name": "Judge T", "email": email, "password": "testpass123",
        "role": "judge", "agreements_accepted": True,
        "organization": "285th District Court", "pro_role": "Judge",
    })
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": email}, {"$set": {"approved": True}})
    s.email = email
    return s


def test_statement_custody_language_blocked_400():
    judge = _register_approved_judge()
    pro = new_user(API, "professional", "Pro")
    pro_me = pro.get(f"{API}/auth/me").json()

    r = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": pro_me["id"],
        "cause_number": f"2026-CI-{uuid.uuid4().hex[:5]}",
        "child_initials": "E.T.",
    })
    assert r.status_code == 200, r.text
    ref_id = r.json()["id"]

    r = pro.post(f"{API}/professional/court-referrals/{ref_id}/accept")
    assert r.status_code == 200, r.text

    r = pro.post(f"{API}/joint/reports/professional", json={
        "subject": "communication",
        "child_name": "TEST_Kid",
        "parent_a_name": "Parent A",
        "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
        "parent_b_name": "Parent B",
        "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com",
        "court_referral_id": ref_id,
    })
    assert r.status_code == 200, r.text
    d = r.json()
    rid = d["id"]
    complete_both(API, pro, rid, d["invitations"])

    r = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={
        "role_basis": "Court-appointed mediator",
        "process_summary": "Two joint sessions were held with both parents.",
        "observations": "Parents cooperated on schedule discussions.",
        "next_steps": "Mother should be awarded sole custody of the child.",
        "mark_ready": True,
    })
    assert r.status_code == 400, (r.status_code, r.text)
    low = r.text.lower()
    assert any(k in low for k in ("custody", "decision", "recommend", "sole")), r.text


def test_submit_to_court_on_non_court_case_400():
    pro, pa, pb, d = new_case(API, CaseSpec(subject="communication"))
    rid = d["id"]
    fill(API, pa, rid, "alpha")
    fill(API, pb, rid, "beta")

    r = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True})
    assert r.status_code == 400, (r.status_code, r.text)
    body = r.text.lower()
    assert "court" in body, r.text
