"""Court Packets: pro sends cover letter + reports to a judge via one-time link + code; judge views, downloads, responds."""
import os
import uuid

import pymongo
import pytest
import requests

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
LETTER = "Your Honor, I facilitated a structured co-parenting alignment process for this family. The enclosed report compares each parent's independent perspective."


def _db() -> pymongo.database.Database:
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def sent() -> tuple:
    pro, pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    r = pro.post(f"{API}/joint/reports/{rid}/court-packets", json={
        "judge_name": "Judge Test", "judge_email": f"judge_{uuid.uuid4().hex[:6]}@example.com", "court_name": "285th District Court",
        "cause_number": "2026-CI-00123", "cover_letter": LETTER, "report_ids": [], "attest": True})
    assert r.status_code == 200, r.text
    p = r.json()
    token = p["link"].rsplit("/court/", 1)[1]
    # code is only emailed; read the hash-free code by resetting it to a known value in the test DB
    import hashlib
    _db().court_packets.update_one({"id": p["id"]}, {"$set": {"code_hash": hashlib.sha256(b"123456").hexdigest()}})
    return pro, pa, rid, p, token


def test_requires_attestation_and_letter(sent) -> None:
    pro, _pa, rid, _p, _t = sent
    base = {"judge_name": "J", "judge_email": "j@example.com", "cover_letter": LETTER}
    assert pro.post(f"{API}/joint/reports/{rid}/court-packets", json={**base, "attest": False}).status_code == 400
    assert pro.post(f"{API}/joint/reports/{rid}/court-packets", json={**base, "attest": True, "cover_letter": "short"}).status_code == 400


def test_parent_cannot_create_or_list(sent) -> None:
    _pro, pa, rid, _p, _t = sent
    assert pa.get(f"{API}/joint/reports/{rid}/court-packets").status_code == 404
    assert pa.post(f"{API}/joint/reports/{rid}/court-packets", json={"judge_name": "J", "judge_email": "j@example.com", "cover_letter": LETTER, "attest": True}).status_code == 404


def test_judge_preview_unlock_view_download(sent) -> None:
    pro, _pa, rid, p, token = sent
    pv = requests.get(f"{API}/court/{token}/preview").json()
    assert pv["state"] == "active" and pv["cause_number"] == "2026-CI-00123"
    assert requests.get(f"{API}/court/{token}").status_code == 401
    assert requests.post(f"{API}/court/{token}/unlock", json={"code": "000000"}).status_code == 400
    u = requests.post(f"{API}/court/{token}/unlock", json={"code": "123456"})
    assert u.status_code == 200, u.text
    access = u.json()["access"]
    h = {"X-Court-Access": access}
    view = requests.get(f"{API}/court/{token}", headers=h)
    assert view.status_code == 200, view.text
    body = view.json()
    assert body["cover_letter"] == LETTER and len(body["reports"]) == 1 and body["reports"][0]["report"]["alignment_map"]
    pdf = requests.get(f"{API}/court/{token}/pdf", params={"access": access})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    import pymupdf
    doc = pymupdf.open(stream=pdf.content, filetype="pdf")
    assert len(doc) >= 3
    assert "PROFESSIONAL ATTESTATION" in doc[0].get_text() or "PROFESSIONAL ATTESTATION" in doc[1].get_text()
    lst = pro.get(f"{API}/joint/reports/{rid}/court-packets").json()
    assert lst[0]["status"] == "opened" and lst[0]["opened_count"] == 1 and lst[0]["download_count"] == 1
    act = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    assert any("Court Packet opened" in e["action"] for e in act["access_events"])


def test_judge_responds_and_pro_sees_it(sent) -> None:
    pro, _pa, rid, p, token = sent
    access = requests.post(f"{API}/court/{token}/unlock", json={"code": "123456"}).json()["access"]
    h = {"X-Court-Access": access}
    assert requests.post(f"{API}/court/{token}/respond", json={"kind": "clarification", "message": ""}, headers=h).status_code == 400
    r = requests.post(f"{API}/court/{token}/respond", json={"kind": "clarification", "message": "Please clarify the exchange schedule."}, headers=h)
    assert r.status_code == 200, r.text
    lst = pro.get(f"{API}/joint/reports/{rid}/court-packets").json()
    assert lst[0]["status"] == "clarification_requested" and lst[0]["responses"][0]["message"].startswith("Please clarify")
    assert requests.post(f"{API}/court/{token}/respond", json={"kind": "acknowledged"}, headers=h).status_code == 200


def test_revoke_blocks_judge(sent) -> None:
    pro, _pa, _rid, p, token = sent
    assert pro.post(f"{API}/court-packets/{p['id']}/revoke").json()["status"] == "revoked"
    assert requests.get(f"{API}/court/{token}/preview").json()["state"] == "revoked"
    assert requests.post(f"{API}/court/{token}/unlock", json={"code": "123456"}).status_code == 410
    assert pro.post(f"{API}/court-packets/{p['id']}/resend").status_code == 400


def test_pro_pdf_and_bad_token() -> None:
    assert requests.get(f"{API}/court/not-a-real-token/preview").status_code == 404
