"""Professional invitation acceptance: one-time 72h token, email-matched, accept/decline/info/conflict."""
import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta

import pymongo

from casekit import new_user, new_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client, client[os.environ["DB_NAME"]]


def _setup():
    _seed, parent, parent2, _d = new_case(API)
    pro = new_user(API, "professional", "Pro Inv")
    rc = parent.post(f"{API}/joint/professional-requests", json={
        "professional_email": pro.email, "child_name": "TEST_Kid", "co_parent_name": "Q", "co_parent_email": parent2.email,
    })
    assert rc.status_code == 200, rc.text
    req_id = rc.json()["id"]
    client, db = _db()
    token = secrets.token_urlsafe(32)
    db.professional_requests.update_one({"id": req_id}, {"$set": {"token_hash": hashlib.sha256(token.encode()).hexdigest()}})
    client.close()
    return parent, pro, req_id, token


class TestProInviteAcceptance:
    def test_request_has_72h_expiry_and_events(self) -> None:
        parent, pro, req_id, _t = _setup()
        mine = [x for x in pro.get(f"{API}/joint/professional-requests").json() if x["id"] == req_id][0]
        assert mine["status"] == "pending"
        exp = datetime.fromisoformat(mine["expires_at"])
        created = datetime.fromisoformat(mine["created_at"])
        assert abs((exp - created) - timedelta(hours=72)) < timedelta(minutes=1)
        assert mine["events"][0]["type"] == "sent"

    def test_lookup_requires_matching_email(self) -> None:
        parent, pro, req_id, token = _setup()
        other = new_user(API, "professional", "Other Pro")
        assert other.get(f"{API}/joint/professional-requests/lookup", params={"token": token}).status_code == 403
        assert pro.get(f"{API}/joint/professional-requests/lookup", params={"token": "nope"}).status_code == 404
        ok = pro.get(f"{API}/joint/professional-requests/lookup", params={"token": token})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["id"] == req_id and body["child_name"] == "TEST_Kid"
        assert "parent_email" not in body and "co_parent_email" not in body

    def test_decline_is_one_time(self) -> None:
        parent, pro, req_id, token = _setup()
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/decline", json={"reason": "Outside my practice area"})
        assert r.status_code == 200 and r.json()["status"] == "declined"
        assert pro.get(f"{API}/joint/professional-requests/lookup", params={"token": token}).status_code == 410
        assert pro.post(f"{API}/joint/professional-requests/{req_id}/prepare").status_code == 400
        mine = [x for x in parent.get(f"{API}/joint/professional-requests").json() if x["id"] == req_id][0]
        assert mine["status"] == "declined"
        assert mine["events"][-1]["type"] == "declined"

    def test_request_info_keeps_pending(self) -> None:
        parent, pro, req_id, token = _setup()
        assert pro.post(f"{API}/joint/professional-requests/{req_id}/request-info", json={"reason": ""}).status_code == 400
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/request-info", json={"reason": "Is there a current protective order?"})
        assert r.status_code == 200 and r.json()["status"] == "pending"
        assert pro.get(f"{API}/joint/professional-requests/lookup", params={"token": token}).status_code == 200
        mine = [x for x in pro.get(f"{API}/joint/professional-requests").json() if x["id"] == req_id][0]
        assert mine["events"][-1]["type"] == "info_requested"

    def test_conflict_declines(self) -> None:
        parent, pro, req_id, token = _setup()
        r = pro.post(f"{API}/joint/professional-requests/{req_id}/conflict", json={"reason": "Prior representation"})
        assert r.status_code == 200 and r.json()["status"] == "declined_conflict"
        assert pro.post(f"{API}/joint/professional-requests/{req_id}/decline", json={}).status_code == 400

    def test_expired_invitation_blocked(self) -> None:
        parent, pro, req_id, token = _setup()
        client, db = _db()
        db.professional_requests.update_one({"id": req_id}, {"$set": {"expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}})
        client.close()
        assert pro.get(f"{API}/joint/professional-requests/lookup", params={"token": token}).status_code == 410
        assert pro.post(f"{API}/joint/professional-requests/{req_id}/prepare").status_code == 410
        mine = [x for x in pro.get(f"{API}/joint/professional-requests").json() if x["id"] == req_id][0]
        assert mine["status"] == "expired"

    def test_accept_consumes_token(self) -> None:
        parent, pro, req_id, token = _setup()
        rp = pro.post(f"{API}/joint/professional-requests/{req_id}/prepare")
        assert rp.status_code == 200, rp.text
        assert pro.get(f"{API}/joint/professional-requests/lookup", params={"token": token}).status_code == 410
        mine = [x for x in pro.get(f"{API}/joint/professional-requests").json() if x["id"] == req_id][0]
        assert mine["status"] == "prepared" and mine["events"][-1]["type"] == "accepted"
