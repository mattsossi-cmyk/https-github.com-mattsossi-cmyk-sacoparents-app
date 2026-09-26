"""Iteration 72: urgent-safety professional messages email the judge immediately with an URGENT subject."""
import os

import pymongo
from casekit import complete_both
from test_judicial_portal import _flow
from test_legal_report import API


def test_urgent_message_sends_immediate_urgent_email() -> None:
    judge, pro, ref, case = _flow()
    complete_both(API, pro, case["id"], case["invitations"])
    r = pro.post(f"{API}/professional/court-referrals/{ref['id']}/messages", json={"text": "URGENT: the child disclosed a credible threat of physical harm at today's exchange; a protective order is being requested immediately."})
    assert r.status_code == 200, r.text
    m = r.json()["message"]
    assert m["triage"]["category"] == "urgent_safety" and m.get("urgent_alert_sent_at")
    c = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    log = c.communications.find_one({"kind": "court_urgent_safety", "case_id": case["id"]}, sort=[("at", -1)])
    assert log and log["subject"].startswith("URGENT") and log["to_role"] == "Court"
    r2 = pro.post(f"{API}/professional/court-referrals/{ref['id']}/messages", json={"text": "Attaching the completed Joint Report for the file; no further action requested."})
    assert r2.status_code == 200 and not r2.json()["message"].get("urgent_alert_sent_at")
