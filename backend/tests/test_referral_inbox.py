"""Referral inbox: received/sent lists and accept/decline responses."""
import os

import pytest

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def referral() -> dict:
    pro, _pa, _pb, d = new_case(API)
    colleague = new_user(API, "professional", "Inbox Colleague")
    them = next(r for r in pro.get(f"{API}/professionals/directory").json() if r["email"] == colleague.email.lower())
    assert pro.post(f"{API}/professionals/{them['id']}/refer", json={"message": "Please take this one", "report_id": d["id"]}).status_code == 200
    ref = pro.get(f"{API}/professionals/referrals").json()["sent"][0]
    return {"pro": pro, "colleague": colleague, "case": d, "ref": ref}


def test_sent_list_shows_pending_referral(referral: dict) -> None:
    sent = referral["pro"].get(f"{API}/professionals/referrals").json()
    assert sent["received"] == []
    assert len(sent["sent"]) == 1
    ref = sent["sent"][0]
    assert ref["status"] == "pending"
    assert ref["case_code"] == referral["case"]["case_code"]
    assert ref["to_name"] == referral["colleague"].name


def test_received_list_for_colleague(referral: dict) -> None:
    inbox = referral["colleague"].get(f"{API}/professionals/referrals").json()
    assert [r["id"] for r in inbox["received"]] == [referral["ref"]["id"]]
    assert inbox["sent"] == []
    assert inbox["received"][0]["from_name"] == referral["pro"].name


def test_only_recipient_can_respond(referral: dict) -> None:
    r = referral["pro"].post(f"{API}/professionals/referrals/{referral['ref']['id']}/respond", json={"accept": True})
    assert r.status_code == 404


def test_accept_once_and_referrer_sees_response(referral: dict) -> None:
    rid = referral["ref"]["id"]
    r = referral["colleague"].post(f"{API}/professionals/referrals/{rid}/respond", json={"accept": True, "note": "Happy to help"})
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    assert referral["colleague"].post(f"{API}/professionals/referrals/{rid}/respond", json={"accept": False}).status_code == 400
    after = referral["pro"].get(f"{API}/professionals/referrals").json()["sent"][0]
    assert after["status"] == "accepted"
    assert after["response_note"] == "Happy to help"
    assert after["responded_at"]
