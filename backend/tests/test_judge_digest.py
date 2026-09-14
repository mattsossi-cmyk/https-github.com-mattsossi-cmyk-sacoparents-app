"""Monday judge digest: per-judge email with stage, hearing date, unanswered court messages."""
import asyncio
import logging
import os
import uuid
from datetime import date, timedelta

import pymongo
import requests

from casekit import new_user

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://align-report.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _judge() -> tuple[requests.Session, str]:
    s = requests.Session()
    e = f"t_djudge_{uuid.uuid4().hex[:8]}@example.com"
    assert s.post(f"{API}/auth/register", json={"name": "Judge Digest", "email": e, "password": "testpass123", "role": "judge", "agreements_accepted": True, "organization": "Court", "pro_role": "Judge"}).status_code == 200
    pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].users.update_one({"email": e}, {"$set": {"approved": True}})
    return s, e


def test_digest_lists_cases_overdue_and_unanswered() -> None:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from judge_digest import run_judge_digests

    judge, email = _judge()
    pro = new_user(API, "professional", "Digest Pro")
    me = pro.get(f"{API}/auth/me").json()
    soon = (date.today() + timedelta(days=2)).isoformat()
    a = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-D{uuid.uuid4().hex[:4]}", "hearing_date": soon, "requested_reports": ["education"]}).json()
    b = judge.post(f"{API}/court-dashboard/referrals", json={"professional_id": me["id"], "cause_number": f"2026-CI-D{uuid.uuid4().hex[:4]}", "requested_reports": ["medical"]}).json()
    assert judge.post(f"{API}/court-dashboard/cases/{a['id']}/messages", json={"text": "Status update please."}).status_code == 200

    sent: list[dict] = []

    async def fake_send(**kw) -> None:
        sent.append(kw)

    class _DB:
        def __init__(self) -> None:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._c = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        def __getattr__(self, k: str):
            return getattr(self._c, k)

    n = asyncio.run(run_judge_digests(_DB(), fake_send, lambda: BASE_URL, "Align", logging.getLogger("t")))
    mine = [m for m in sent if m["to"] == email]
    assert n >= 1 and len(mine) == 1, [m["to"] for m in sent]
    html = mine[0]["html"]
    assert a["cause_number"] in html and b["cause_number"] in html
    assert "OVERDUE" in html and "Unanswered since" in html
    assert "2 referred cases" in mine[0]["subject"]
    assert f"/court/case/{a['id']}" in html
    assert mine[0]["kind"] == "judge_digest" and "credibility" in html


def test_cron_endpoint_acks() -> None:
    hdr = {"Authorization": f"Bearer {os.environ['WEBHOOK_CRON_SECRET']}", "Content-Type": "application/json"}
    assert requests.post(f"{API}/cron/judge-digest", headers=hdr, json={"run_id": uuid.uuid4().hex}).status_code == 200
    assert requests.post(f"{API}/cron/judge-digest", json={}).status_code in (401, 403)
