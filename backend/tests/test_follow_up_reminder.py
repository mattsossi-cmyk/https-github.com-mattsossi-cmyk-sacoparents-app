"""Follow-up reminder: outcome stores a check-in date; daily cron emails the pro that day (once)."""
import os

import pymongo
import pytest
import requests

from casekit import completed_case

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
CRON_HEADERS = {"Authorization": f"Bearer {os.environ['WEBHOOK_CRON_SECRET']}", "Content-Type": "application/json"}


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def case_with_followup():
    pro, _pa, _pb, d, _detail = completed_case(API)
    rid = d["id"]
    r = pro.put(f"{API}/joint/reports/{rid}/session-outcome", json={"chosen_steps": ["Continue Parent Discussion"], "summary": "x", "follow_up_date": "2026-01-05"})
    assert r.status_code == 200, r.text
    return pro, rid


def test_follow_up_date_saved_and_validated(case_with_followup) -> None:
    pro, rid = case_with_followup
    assert pro.get(f"{API}/joint/reports/{rid}").json()["session_outcome"]["follow_up_date"] == "2026-01-05"
    bad = pro.put(f"{API}/joint/reports/{rid}/session-outcome", json={"chosen_steps": [], "follow_up_date": "05/01/2026"})
    assert bad.status_code == 400


def test_cron_requires_secret() -> None:
    assert requests.post(f"{API}/cron/follow-up-reminder", json={"run_id": "x"}).status_code == 401


def test_cron_sends_reminder_once(case_with_followup) -> None:
    import time, uuid
    pro, rid = case_with_followup
    r = requests.post(f"{API}/cron/follow-up-reminder", json={"run_id": f"t-{uuid.uuid4().hex}"}, headers=CRON_HEADERS)
    assert r.status_code == 200 and r.json().get("ok")
    doc = None
    for _ in range(20):
        time.sleep(0.5)
        doc = _db().joint_reports.find_one({"id": rid}, {"follow_up_reminder_sent": 1})
        if doc and doc.get("follow_up_reminder_sent"):
            break
    assert doc and doc.get("follow_up_reminder_sent"), "reminder was not marked sent"
    act = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    assert any("Follow-up reminder emailed" in e["action"] for e in act["lifecycle"])
    # second run must not send again
    requests.post(f"{API}/cron/follow-up-reminder", json={"run_id": f"t-{uuid.uuid4().hex}"}, headers=CRON_HEADERS)
    time.sleep(1.5)
    act2 = pro.get(f"{API}/joint/reports/{rid}/activity").json()
    assert sum(1 for e in act2["lifecycle"] if "Follow-up reminder emailed" in e["action"]) == 1
