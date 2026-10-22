"""Owner 2026-10-22 (a): parent app pushes Communication Style results to POST /integrations/case-update (readiness block)."""
import os
import sys

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(__file__))
from casekit import completed_case  # noqa: E402

API = dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
ENV = dotenv_values("/app/backend/.env")
KEY = ENV["INTEGRATION_SHARED_SECRET"]
MONGO = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]


def _push(body, key=KEY):
    return requests.post(f"{API}/integrations/case-update", headers={"X-Integration-Key": key}, json=body, timeout=20)


def test_case_update_readiness_push():
    pro, pa, pb, d, _ = completed_case(API)
    rid = d["id"]
    inv_a = MONGO.invitations.find_one({"report_id": rid, "role": "a"})
    tok = inv_a["token"]
    before = MONGO.joint_reports.find_one({"id": rid}, {"responses": 1, "status": 1})

    assert _push({"token": tok, "communication_readiness": {"responses": {"cr_conflict": "High"}}}, key="nope").status_code == 401
    # unknown keys and bad option values are dropped; only the four ids are kept
    payload = {"token": tok, "status": "readiness", "communication_readiness": {
        "completed_at": "2026-10-22T15:04:05Z",
        "responses": {"cr_conflict": "High", "cr_direct": "Only in writing", "cr_channel": "nonsense value", "cr_child": "  Keep handoffs at school.  ", "style_label": "Avoider", "score": 42}}}
    r = _push(payload)
    assert r.status_code == 200, r.text

    after = MONGO.joint_reports.find_one({"id": rid})
    rec = after["communication_readiness"]["a"]
    assert rec["responses"] == {"cr_conflict": "High", "cr_direct": "Only in writing", "cr_child": "Keep handoffs at school."}
    assert rec["source"] == "sacoparentsapp.online" and rec["completed_at"].startswith("2026-10-22") and rec["flag_for_professional"] is True
    assert "style_label" not in str(rec) and "42" not in str(rec)
    # joint-report answers and case status untouched by a readiness push
    assert after["responses"] == before["responses"] and after["status"] == before["status"]
    assert after.get("communication_readiness", {}).get("b") is None

    # no recognised answers → 400, nothing stored
    assert _push({"token": tok, "communication_readiness": {"responses": {"style_label": "Avoider"}}}).status_code == 400
    assert _push({"token": tok, "communication_readiness": {}}).status_code == 400

    # professional sees it on the Safety Responses screen; parents never receive it
    pr = pro.get(f"{API}/joint/reports/{rid}/safety-screening/a/responses")
    assert pr.status_code == 200 and "Keep handoffs at school." in pr.text
    for s in (pa, pb):
        assert "Keep handoffs at school." not in s.get(f"{API}/joint/reports/{rid}").text
        assert "Keep handoffs at school." not in s.get(f"{API}/joint/reports/{rid}/report").text
    overview = pro.get(f"{API}/joint/reports/{rid}/safety-screening").json()
    assert overview["roles"]["a"]["communication_received"] is True and overview["roles"]["b"]["communication_received"] is False
