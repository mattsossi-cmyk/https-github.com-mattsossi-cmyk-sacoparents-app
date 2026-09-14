"""Communications Log PDF export + overdue flag on court referrals."""
import io
import os
import uuid
from datetime import date, timedelta

import pymongo
import requests

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _judge() -> requests.Session:
    s = requests.Session()
    e = f"t_ojudge_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={"name": "Judge Overdue", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "Court", "pro_role": "Judge"}).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": e}, {"$set": {"approved": True}})
    return s


def test_communications_pdf_has_footer_and_rows() -> None:
    import fitz
    pro, _pa, _pb, d = new_case(API)
    r = pro.get(f"{API}/joint/reports/{d['id']}/communications.pdf")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf"), r.text[:200]
    doc = fitz.open(stream=io.BytesIO(r.content), filetype="pdf")
    text = doc[0].get_text()
    assert "Case Communications Log" in text
    assert "Parent invitation" in text
    assert "2026 sacoparentsalign.com" in text
    assert doc.metadata["author"] == "SA CoParents Align · sacoparentsalign.com"
    other = new_user(API, "professional", "Other")
    assert other.get(f"{API}/joint/reports/{d['id']}/communications.pdf").status_code in (403, 404)


def test_overdue_flag_within_7_days_not_submitted() -> None:
    judge = _judge()
    pro = new_user(API, "professional", "Overdue Pro")
    me = pro.get(f"{API}/auth/me").json()
    soon = (date.today() + timedelta(days=3)).isoformat()
    far = (date.today() + timedelta(days=30)).isoformat()
    a = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-O{uuid.uuid4().hex[:4]}", "hearing_date": soon}).json()
    b = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-O{uuid.uuid4().hex[:4]}", "hearing_date": far}).json()
    assert a["overdue"] is True and b["overdue"] is False
    inbox = {x["id"]: x for x in pro.get(f"{API}/professional/court-referrals").json()}
    assert inbox[a["id"]]["overdue"] is True and inbox[b["id"]]["overdue"] is False
    judge_view = {x["id"]: x for x in judge.get(f"{API}/court-dashboard/referrals").json()}
    assert judge_view[a["id"]]["overdue"] is True
    assert judge.patch(f"{API}/court-dashboard/referrals/{a['id']}/hearing-date", json={"hearing_date": far}).status_code == 200
    assert pro.get(f"{API}/professional/court-referrals").json() and all(not x["overdue"] for x in pro.get(f"{API}/professional/court-referrals").json())


def test_requested_reports_on_referral() -> None:
    judge = _judge()
    pro = new_user(API, "professional", "Reports Pro")
    me = pro.get(f"{API}/auth/me").json()
    body = {"professional_id": me["id"], "cause_number": f"2026-CI-R{uuid.uuid4().hex[:4]}", "requested_reports": ["education", "agreement", "family_violence"]}
    ref = judge.post(f"{API}/court-dashboard/referrals", json=body)
    assert ref.status_code == 200, ref.text
    reqs = ref.json()["requested_reports"]
    assert [r["key"] for r in reqs] == ["education", "agreement", "family_violence"]
    assert reqs[0]["subjects"] == ["education"] and reqs[1]["subjects"] == [] and "safety" in reqs[2]["subjects"]
    inbox = pro.get(f"{API}/professional/court-referrals").json()[0]
    assert [r["label"] for r in inbox["requested_reports"]][1] == "Co-Parenting Agreement"
    for bad in (["bogus"], ["complete"], ["mediation"], ["communication"]):
        assert judge.post(f"{API}/court-dashboard/referrals", json={**body, "requested_reports": bad}).status_code == 400
