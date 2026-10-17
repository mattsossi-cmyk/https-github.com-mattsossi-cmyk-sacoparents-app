"""Iter-114: yearly training refresher + changes-since, case reminder settings on the case page."""
import os
from datetime import datetime, timedelta, timezone

import pymongo
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
from test_iter108_required_step import _case  # noqa: E402

import pro_training as pt  # noqa: E402

API = f"{(os.environ.get('REACT_APP_BACKEND_URL') or '').rstrip('/')}/api"
_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_training_state_reasons_never_version_yearly():
    assert pt.training_state({})["reason"] == "never"
    st = pt.training_state({"safety_training": {"version": "2025-01-01.1", "acknowledged_at": datetime.now(timezone.utc).isoformat()}})
    assert st["reason"] == "version" and st["changes_since"] and st["changes_since"][0]["version"] == pt.TRAINING_VERSION
    old = (datetime.now(timezone.utc) - timedelta(days=pt.REFRESH_DAYS + 1)).isoformat()
    st = pt.training_state({"safety_training": {"version": pt.TRAINING_VERSION, "acknowledged_at": old}})
    assert st["reason"] == "yearly" and st["changes_since"] == [] and st["refresh_due_at"] < datetime.now(timezone.utc).isoformat()
    fresh = pt.training_state({"safety_training": {"version": pt.TRAINING_VERSION, "acknowledged_at": datetime.now(timezone.utc).isoformat()}})
    assert fresh["current"] is True and fresh["reason"] is None


def test_yearly_refresher_gates_and_prompts_then_clears_on_reack():
    pro, pa, pb, rid = _case()
    uid = pro.get(f"{API}/auth/me").json()["id"]
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    _db.users.update_one({"_id": uid}, {"$set": {"safety_training": {"version": pt.TRAINING_VERSION, "acknowledged_at": old}}})
    me = pro.get(f"{API}/auth/me").json()
    assert me["safety_training_due"] == "yearly"
    t = pro.get(f"{API}/professional-training").json()
    assert t["current"] is False and t["reason"] == "yearly" and t["refresh_days"] == 365
    assert pro.get(f"{API}/joint/reports/{rid}/safety-review").status_code == 428
    assert pro.post(f"{API}/professional-training/acknowledge", json={"version": pt.TRAINING_VERSION, "acknowledged": True}).json()["ok"]
    assert pro.get(f"{API}/auth/me").json()["safety_training_due"] is None
    assert pro.get(f"{API}/joint/reports/{rid}/safety-review").status_code == 200
    assert pa.get(f"{API}/auth/me").json()["safety_training_due"] is None


def test_case_reminder_settings_roundtrip_and_validation():
    pro, pa, pb, rid = _case()
    r = pro.put(f"{API}/joint/reports/{rid}/invite-cadence", json={"reminder_days": [1, 4], "max_reminders": 1})
    assert r.status_code == 200 and r.json()["cadence"] == {"reminder_days": [1, 4], "max_reminders": 1, "expiry_days": 7}
    assert pro.get(f"{API}/joint/reports/{rid}/invite-cadence").json()["cadence"]["max_reminders"] == 1
    r = pro.put(f"{API}/joint/reports/{rid}/invite-cadence", json={"reminder_days": [0, 7, 30], "max_reminders": 2})
    assert r.json()["cadence"]["reminder_days"] == [] and r.json()["cadence"]["max_reminders"] == 0
    assert pa.put(f"{API}/joint/reports/{rid}/invite-cadence", json={"reminder_days": [3], "max_reminders": 1}).status_code == 403
    assert any(e["kind"] == "invite_cadence" for e in _db.access_events.find({"report_id": rid}))
