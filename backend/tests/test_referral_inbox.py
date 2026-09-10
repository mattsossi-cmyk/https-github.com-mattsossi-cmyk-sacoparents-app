"""Referral inbox: received/sent lists and accept/decline responses."""
import os

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_referral_inbox_roundtrip() -> None:
    pro, _pa, _pb, d = new_case(API)
    colleague = new_user(API, "professional", "Inbox Colleague")
    them = next(r for r in pro.get(f"{API}/professionals/directory").json() if r["email"] == colleague.email.lower())
    assert pro.post(f"{API}/professionals/{them['id']}/refer", json={"message": "Please take this one", "report_id": d["id"]}).status_code == 200

    sent = pro.get(f"{API}/professionals/referrals").json()
    assert sent["received"] == [] and len(sent["sent"]) == 1
    ref = sent["sent"][0]
    assert ref["status"] == "pending" and ref["case_code"] == d["case_code"] and ref["to_name"] == colleague.name

    inbox = colleague.get(f"{API}/professionals/referrals").json()
    assert [r["id"] for r in inbox["received"]] == [ref["id"]] and inbox["sent"] == []
    assert inbox["received"][0]["from_name"] == pro.name

    assert pro.post(f"{API}/professionals/referrals/{ref['id']}/respond", json={"accept": True}).status_code == 404
    r = colleague.post(f"{API}/professionals/referrals/{ref['id']}/respond", json={"accept": True, "note": "Happy to help"})
    assert r.status_code == 200 and r.json()["status"] == "accepted"
    assert colleague.post(f"{API}/professionals/referrals/{ref['id']}/respond", json={"accept": False}).status_code == 400
    after = pro.get(f"{API}/professionals/referrals").json()["sent"][0]
    assert after["status"] == "accepted" and after["response_note"] == "Happy to help" and after["responded_at"]
