"""Case Communications Log: every outbound email is recorded per case and listed to the professional (and court-facing ones to the judge)."""
import os
import uuid

import pymongo
import requests

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_cjudge_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={"name": "Judge Comms", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "Court", "pro_role": "Judge"}).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


def test_invitations_are_logged_and_visible_to_creator_only() -> None:
    pro, _pa, _pb, d = new_case(API)
    rid = d["id"]
    log = pro.get(f"{API}/joint/reports/{rid}/communications")
    assert log.status_code == 200, log.text
    kinds = [c["kind"] for c in log.json()]
    assert kinds.count("invitation") == 2
    assert all(set(c) == {"id", "at", "kind", "to", "to_role", "subject", "provider"} for c in log.json())
    other = new_user(API, "professional", "Other Pro")
    assert other.get(f"{API}/joint/reports/{rid}/communications").status_code in (403, 404)


def test_court_referral_logged_for_judge_and_pro() -> None:
    judge = _judge()
    pro = new_user(API, "professional", "Referral Pro")
    me = pro.get(f"{API}/auth/me").json()
    ref = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-C{uuid.uuid4().hex[:4]}", "hearing_date": ""}).json()
    r = judge.get(f"{API}/court-dashboard/referrals/{ref['id']}/communications")
    assert r.status_code == 200, r.text
    assert [c["kind"] for c in r.json()] == ["court_referral"]
    assert pro.get(f"{API}/court-dashboard/referrals/{ref['id']}/communications").status_code == 403
