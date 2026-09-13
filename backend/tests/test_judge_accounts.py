"""Judge accounts: register (unapproved) -> admin approve -> Court Dashboard lists/opens packets; transmittal PDF for pro."""
import os
import uuid

import pymongo
import pytest
import requests

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
LETTER = "Your Honor, I facilitated a structured co-parenting alignment process for this family. The enclosed report compares each parent's independent perspective."


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _admin():
    s = requests.Session()
    email = f"t_adminfix_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "Fixture Admin", "email": email, "password": "testpass123", "role": "professional", "agreements_accepted": True})
    assert r.status_code == 200, r.text
    _db().users.update_one({"email": email}, {"$set": {"role": "admin", "approved": True}})
    return s


@pytest.fixture(scope="module")
def setup():
    judge_email = f"t_judge_{uuid.uuid4().hex[:8]}@example.com"
    judge = requests.Session()
    reg = judge.post(f"{API}/auth/register", json={"name": "Judge Fixture", "email": judge_email, "password": "testpass123", "role": "judge",
                                                  "agreements_accepted": True, "organization": "285th District Court", "pro_role": "Judge"})
    assert reg.status_code == 200, reg.text
    assert reg.json()["role"] == "judge" and reg.json()["approved"] is False
    pro, _pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    p = pro.post(f"{API}/joint/reports/{rid}/court-packets", json={"judge_name": "Judge Fixture", "judge_email": judge_email, "court_name": "285th District Court",
                                                                     "cause_number": "2026-CI-00777", "cover_letter": LETTER, "attest": True})
    assert p.status_code == 200, p.text
    return judge, reg.json()["id"], pro, rid, p.json()


def test_judge_requires_court_and_agreements() -> None:
    e = f"t_j_{uuid.uuid4().hex[:6]}@example.com"
    assert requests.post(f"{API}/auth/register", json={"name": "J", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True}).status_code == 400


def test_unapproved_judge_sees_pending_and_cannot_open(setup) -> None:
    judge, _jid, _pro, _rid, p = setup
    dash = judge.get(f"{API}/court-dashboard/packets").json()
    assert dash["approved"] is False and dash["packets"] == []
    assert judge.get(f"{API}/court-dashboard/packets/{p['id']}").status_code == 403


def test_admin_approves_then_judge_sees_and_opens(setup) -> None:
    judge, jid, pro, rid, p = setup
    admin = _admin()
    lst = admin.get(f"{API}/admin/judges").json()
    assert any(j["id"] == jid and not j["approved"] for j in lst)
    ap = admin.post(f"{API}/admin/judges/{jid}/approve")
    assert ap.status_code == 200 and ap.json()["approved"] is True
    dash = judge.get(f"{API}/court-dashboard/packets").json()
    assert dash["approved"] is True and [x["id"] for x in dash["packets"]] == [p["id"]]
    assert dash["packets"][0]["state"] == "active" and dash["packets"][0]["cause_number"] == "2026-CI-00777"
    view = judge.get(f"{API}/court-dashboard/packets/{p['id']}")
    assert view.status_code == 200 and view.json()["cover_letter"] == LETTER and len(view.json()["reports"]) == 1
    pdf = judge.get(f"{API}/court-dashboard/packets/{p['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    resp = judge.post(f"{API}/court-dashboard/packets/{p['id']}/respond", json={"kind": "acknowledged", "message": "Received."})
    assert resp.status_code == 200
    mine = pro.get(f"{API}/joint/reports/{rid}/court-packets").json()[0]
    assert mine["status"] == "acknowledged" and mine["opened_count"] == 1 and mine["download_count"] == 1


def test_other_judge_cannot_see_packet(setup) -> None:
    _judge, _jid, _pro, _rid, p = setup
    other = requests.Session()
    e = f"t_j2_{uuid.uuid4().hex[:6]}@example.com"
    other.post(f"{API}/auth/register", json={"name": "Other", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "Court"})
    _db().users.update_one({"email": e}, {"$set": {"approved": True}})
    assert other.get(f"{API}/court-dashboard/packets").json()["packets"] == []
    assert other.get(f"{API}/court-dashboard/packets/{p['id']}").status_code == 404


def test_professional_cannot_use_court_dashboard(setup) -> None:
    _judge, _jid, pro, _rid, _p = setup
    assert pro.get(f"{API}/court-dashboard/packets").status_code == 403


def test_transmittal_certificate(setup) -> None:
    _judge, _jid, pro, _rid, p = setup
    r = pro.get(f"{API}/court-packets/{p['id']}/transmittal.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and "transmittal-" in r.headers["Content-Disposition"]
    import pymupdf
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    text = doc[0].get_text()
    assert len(doc) == 1
    for needle in ("Certificate of Transmittal", "2026-CI-00777", "Receipt acknowledged", "sacoparentsalign.com"):
        assert needle in text, needle
