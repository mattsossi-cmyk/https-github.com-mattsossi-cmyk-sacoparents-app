"""Iter-113: supervisor admin toggle, reminder dashboard, webhook live check."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pymongo
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
from test_iter108_required_step import _case  # noqa: E402

import safety_status_webhook as wh  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_reminder_dashboard_lists_unopened_with_next_reminder_and_reissue():
    pro, pa, pb, rid = _case()
    assert pa.get(f"{API}/professional/invitations").status_code == 403
    assert pro.get(f"{API}/professional/invitations").json()["count"] == 0  # both accepted
    now = datetime.now(timezone.utc)
    iid = str(uuid.uuid4())
    _db.invitations.insert_one({"id": iid, "report_id": rid, "role": "b", "invitee_name": "Pat", "invitee_email": f"t_p_{iid[:6]}@example.com", "inviter_name": "Pro", "token": "tk" + iid[:10], "code": "ZZZZ0001", "status": "pending", "created_at": (now - timedelta(days=1)).isoformat(), "reminders_sent": 0})
    d = pro.get(f"{API}/professional/invitations").json()
    assert d["count"] == 1
    inv = d["invitations"][0]
    assert inv["id"] == iid and inv["parent_label"] == "Parent B" and inv["reminders_sent"] == 0 and inv["max_reminders"] == 2 and inv["can_reissue"] is True and inv["expired"] is False
    assert inv["next_reminder_at"][:10] == (now + timedelta(days=2)).isoformat()[:10] and inv["expires_at"][:10] == (now + timedelta(days=6)).isoformat()[:10]
    assert "token" not in inv
    # one-click fresh link: old → expired, a new pending one appears with a fresh 7-day window
    r = pro.post(f"{API}/joint/invitations/{iid}/reissue")
    assert r.status_code == 200
    assert _db.invitations.find_one({"id": iid})["status"] == "expired"
    d = pro.get(f"{API}/professional/invitations").json()
    fresh = [i for i in d["invitations"] if i["role"] == "b" and i["id"] != iid]
    assert len(fresh) == 1 and fresh[0]["expires_at"][:10] == (now + timedelta(days=7)).isoformat()[:10] and fresh[0]["reminders_sent"] == 0
    _db.invitations.delete_many({"report_id": rid, "status": {"$in": ["pending", "expired"]}, "role": "b", "id": {"$ne": None}, "code": {"$in": ["ZZZZ0001"]}})


def test_webhook_test_ping_is_admin_only_and_payload_shape():
    pro, pa, pb, rid = _case()
    assert pro.post(f"{API}/admin/safety-status-webhook/test").status_code == 403
    assert pa.post(f"{API}/admin/safety-status-webhook/test").status_code == 403
    p = wh.build_payload(wh.TEST_CASE_ID, "standard", "Align admin test ping")
    assert set(p) == wh.ALLOWED_KEYS and p["case_id"] == "ALIGN-TEST-PING"


def test_supervisor_patch_reflected_in_admin_list_shape():
    pro, pa, pb, rid = _case()
    assert pro.patch(f"{API}/admin/professionals/{uuid.uuid4()}/supervisor", json={"is_supervisor": True}).status_code == 403
    import inspect

    import admin_routes
    assert '"is_supervisor": bool(u.get("is_supervisor"))' in inspect.getsource(admin_routes.list_approved_professionals)
