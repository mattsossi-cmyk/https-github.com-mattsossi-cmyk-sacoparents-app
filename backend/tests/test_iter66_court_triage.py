"""Iteration 66: court/professional message triage - each posted message should
receive a 'triage' object with category in {procedural, scheduling, urgent_safety}.
Urgent safety text should be categorized as urgent_safety."""
import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE_URL}/api"

ALLOWED = {"procedural", "scheduling", "urgent_safety"}


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_j_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={
        "name": "Judge Triage", "email": e, "password": "testpass123",
        "role": "judge", "agreements_accepted": True,
        "organization": "Court", "pro_role": "Judge"
    }).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one(
        {"email": e}, {"$set": {"approved": True}}
    )
    return s


def _setup_referral() -> tuple:
    judge = _judge()
    pro = new_user(API, "professional", "Triage Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={
        "professional_id": me["id"],
        "cause_number": f"2026-CI-T{uuid.uuid4().hex[:4]}",
        "requested_reports": ["education"]
    }).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept").status_code == 200
    return judge, pro, ref


def test_professional_message_triage_shape() -> None:
    judge, pro, ref = _setup_referral()
    r = pro.post(f"{API}/professional/court-referrals/{ref['id']}/messages",
                 json={"text": "Both parents have completed their assessments."})
    assert r.status_code == 200, r.text
    msg = r.json()["message"]
    assert "triage" in msg and isinstance(msg["triage"], dict), msg
    assert msg["triage"].get("category") in ALLOWED, msg["triage"]


def test_court_urgent_safety_message_is_urgent_safety() -> None:
    judge, pro, ref = _setup_referral()
    r = judge.post(f"{API}/court-dashboard/cases/{ref['id']}/messages", json={
        "text": "URGENT: the child disclosed a threat of physical harm at exchange today; protective order requested."
    })
    assert r.status_code == 200, r.text
    msg = r.json()["message"]
    assert msg.get("triage", {}).get("category") == "urgent_safety", msg["triage"]


def test_scheduling_message_triage() -> None:
    judge, pro, ref = _setup_referral()
    r = judge.post(f"{API}/court-dashboard/cases/{ref['id']}/messages",
                   json={"text": "Please confirm your availability for a status hearing on Tuesday at 10am."})
    assert r.status_code == 200, r.text
    cat = r.json()["message"].get("triage", {}).get("category")
    assert cat in ALLOWED, cat
