"""Court workflow: judge refers -> pro accepts -> case -> statement -> submit (frozen) -> judge dashboard + status summary."""
import os
import uuid

import pymongo
import pytest
import requests

from casekit import new_user, complete_both

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
STMT = {"role_basis": "Court-referred parenting facilitator.", "process_summary": "Both parents completed independent reflections.",
        "observations": "Parents align on schedule consistency; differ on communication channel.", "safety_considerations": "", "next_steps": "Two facilitated sessions."}


def _db() -> pymongo.database.Database:
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_wjudge_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Judge Flow", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "285th District Court", "pro_role": "Judge"})
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


@pytest.fixture(scope="module")
def flow() -> tuple:
    judge = _judge()
    pro = new_user(API, "professional", "Referred Pro")
    me = pro.get(f"{API}/auth/me").json()
    pros = judge.get(f"{API}/court-dashboard/professionals").json()
    assert any(p["id"] == me["id"] for p in pros)
    ref = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": "2026-CI-09090", "child_initials": "E.T.",
                                                                 "parent_a_name": "Robin", "parent_a_email": f"t_pa_{uuid.uuid4().hex[:6]}@example.com",
                                                                 "parent_b_name": "Jamie", "parent_b_email": f"t_pb_{uuid.uuid4().hex[:6]}@example.com", "note": "Hearing 10/15"})
    assert ref.status_code == 200, ref.text
    return judge, pro, ref.json()


def test_pro_sees_and_accepts_referral(flow) -> None:
    judge, pro, ref = flow
    inbox = pro.get(f"{API}/professional/court-referrals").json()
    assert inbox[0]["id"] == ref["id"] and inbox[0]["status"] == "pending"
    acc = pro.post(f"{API}/professional/court-referrals/{ref['id']}/accept")
    assert acc.status_code == 200 and acc.json()["next"].endswith(ref["id"])
    js = judge.get(f"{API}/court-dashboard/referrals").json()
    assert js[0]["status"] == "accepted" and js[0]["stage"]["index"] == 0 and js[0]["status_summary"] is None


def test_case_created_from_referral_carries_court(flow) -> None:
    judge, pro, ref = flow
    r = pro.post(f"{API}/joint/reports/professional", json={"subject": "communication", "child_name": "E.T.", "parent_a_name": "Robin", "parent_a_email": ref["parent_a_email"],
                                                            "parent_b_name": "Jamie", "parent_b_email": ref["parent_b_email"], "court_referral_id": ref["id"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["court"]["cause_number"] == "2026-CI-09090" and d["court_stage"]["index"] == 2
    ref["case_id"] = d["id"]; ref["invitations"] = d["invitations"]
    js = judge.get(f"{API}/court-dashboard/referrals").json()[0]
    assert js["case_code"] == d["case_code"] and js["stage"]["label"] == "Parents Invited"
    # unauthorized submit paths
    assert pro.post(f"{API}/joint/reports/{d['id']}/submit-to-court", json={"attest": True}).status_code == 400


def test_statement_blocks_custody_language_and_marks_ready(flow) -> None:
    _judge, pro, ref = flow
    rid = ref["case_id"]
    complete_both(API, pro, rid, ref["invitations"])
    bad = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**STMT, "next_steps": "Mother should be awarded sole custody.", "status": "ready"})
    assert bad.status_code == 400
    assert pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**STMT, "next_steps": "", "status": "ready"}).status_code == 400
    ok = pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**STMT, "status": "ready"})
    assert ok.status_code == 200 and ok.json()["stage"]["index"] == 5
    pdf = pro.get(f"{API}/joint/reports/{rid}/professional-statement.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_submit_freezes_and_judge_sees(flow) -> None:
    judge, pro, ref = flow
    rid = ref["case_id"]
    assert pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": False}).status_code == 400
    sub = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True})
    assert sub.status_code == 200, sub.text
    s = sub.json()["submission"]
    assert s["version"] == 1 and len(s["sha256"]) == 64 and sub.json()["stage"]["index"] == 6
    dash = judge.get(f"{API}/court-dashboard/packets").json()
    pk = [p for p in dash["packets"] if p["id"] == s["packet_id"]]
    assert pk and pk[0]["submission_version"] == 1 and pk[0]["frozen"]
    view = judge.get(f"{API}/court-dashboard/packets/{s['packet_id']}")
    assert view.status_code == 200 and view.json()["statement"]["observations"] == STMT["observations"] and len(view.json()["reports"]) == 1
    pdf = judge.get(f"{API}/court-dashboard/packets/{s['packet_id']}/pdf")
    import hashlib
    assert pdf.status_code == 200 and hashlib.sha256(pdf.content).hexdigest() == s["sha256"]
    # version 2 supersedes version 1
    pro.put(f"{API}/joint/reports/{rid}/professional-statement", json={**STMT, "observations": "Updated.", "status": "ready"})
    sub2 = pro.post(f"{API}/joint/reports/{rid}/submit-to-court", json={"attest": True}).json()["submission"]
    assert sub2["version"] == 2
    dash2 = {p["id"]: p for p in judge.get(f"{API}/court-dashboard/packets").json()["packets"]}
    assert dash2[s["packet_id"]]["superseded"] and dash2[sub2["packet_id"]].get("superseded") is not True
    act = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    assert sum(1 for e in act["lifecycle"] if "Submitted Joint Report" in e["action"]) == 2
    assert judge.get(f"{API}/court-dashboard/referrals").json()[0]["status"] == "submitted"


def test_status_summary_and_outdated(flow) -> None:
    judge, pro, ref = flow
    s = judge.post(f"{API}/court-dashboard/referrals/{ref['id']}/refresh-summary").json()
    assert s["current_status"] == "Ready for court review" and "Both parents completed" in s["parents"]
    assert s["professional_statement"].startswith("Submitted (version 2") and not s["outdated"]
    assert "not a legal conclusion" in s["disclaimer"]
    assert not judge.get(f"{API}/court-dashboard/referrals").json()[0]["status_summary"]["outdated"]
    # underlying change -> outdated
    judge.post(f"{API}/court-dashboard/packets/{[p for p in judge.get(f'{API}/court-dashboard/packets').json()['packets'] if not p.get('superseded')][0]['id']}/respond", json={"kind": "acknowledged"})
    assert judge.get(f"{API}/court-dashboard/referrals").json()[0]["status_summary"]["outdated"]
    # summary never contains raw answers
    raw = _db().joint_reports.find_one({"id": ref["case_id"]}, {"responses": 1})["responses"]["a"]["answers"]
    blob = " ".join(str(v) for v in s.values())
    assert not any(str(v)[:30] in blob for v in raw.values() if len(str(v)) > 12)


def test_decline_path_and_parent_blocked(flow) -> None:
    judge, pro, _ref = flow
    me = pro.get(f"{API}/auth/me").json()
    ref2 = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": "2026-CI-00001"}).json()
    assert pro.post(f"{API}/professional/court-referrals/{ref2['id']}/decline", json={"reason": ""}).status_code == 400
    assert pro.post(f"{API}/professional/court-referrals/{ref2['id']}/decline", json={"reason": "Conflict of interest"}).status_code == 200
    row = [x for x in judge.get(f"{API}/court-dashboard/referrals").json() if x["id"] == ref2["id"]][0]
    assert row["status"] == "declined" and row["stage"]["label"] == "Declined"
    parent = requests.Session()
    parent.post(f"{API}/auth/register", json={"name": "P", "email": f"t_np_{uuid.uuid4().hex[:6]}@example.com", "password": "testpass123", "role": "professional", "agreements_accepted": True})
    # unapproved professional (no judge role) is blocked from court-only endpoints
    assert parent.get(f"{API}/court-dashboard/referrals").status_code == 403
    assert parent.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": "x"}).status_code == 403
